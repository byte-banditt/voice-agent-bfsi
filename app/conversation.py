from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from app.guardrails import enforce_conduct, enforce_grounding
from app.tools import BFSIToolExecutor

_ROOT = Path(__file__).resolve().parent.parent
_TOOL_SCHEMAS: dict[str, dict[str, object]] = {
    "verify_identity": {"type": "function", "function": {"name": "verify_identity", "description": "Verify the caller using date of birth and phone last four digits", "parameters": {"type": "object", "properties": {"dob": {"type": "string"}, "phone_last4": {"type": "string"}}, "required": ["dob", "phone_last4"]}}},
    "get_customer": {"type": "function", "function": {"name": "get_customer", "description": "Get verified customer information", "parameters": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}}},
    "get_loan_status": {"type": "function", "function": {"name": "get_loan_status", "description": "Get verified loan status", "parameters": {"type": "object", "properties": {"loan_id": {"type": "string"}}, "required": ["loan_id"]}}},
    "schedule_callback": {"type": "function", "function": {"name": "schedule_callback", "description": "Schedule a callback", "parameters": {"type": "object", "properties": {"requested_at": {"type": "string"}}, "required": ["requested_at"]}}},
    "create_payment_link": {"type": "function", "function": {"name": "create_payment_link", "description": "Create a mock payment link", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
    "escalate_to_human": {"type": "function", "function": {"name": "escalate_to_human", "description": "Escalate the call to a human", "parameters": {"type": "object", "properties": {}}}},
    "log_call_outcome": {"type": "function", "function": {"name": "log_call_outcome", "description": "Record a call outcome", "parameters": {"type": "object", "properties": {"outcome": {"type": "string"}}, "required": ["outcome"]}}},
}


def _validate_tool_arguments(name: str, arguments: dict[str, Any]) -> None:
    function = _TOOL_SCHEMAS[name]["function"]
    schema = function["parameters"]
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    if set(arguments) - set(properties):
        raise ValueError("unexpected tool argument")
    if set(required) - set(arguments):
        raise ValueError("missing tool argument")
    if any(not isinstance(value, str) or not value.strip() for value in arguments.values()):
        raise ValueError("tool arguments must be nonempty strings")


class ConversationEngine:
    """One flow and tool executor per call; tool permissions come from the active flow state."""

    def __init__(self, flow_name: str, executor: BFSIToolExecutor) -> None:
        self.flow = yaml.safe_load((_ROOT / "flows" / f"{flow_name}.yaml").read_text())
        self.name = flow_name
        self.executor = executor
        self.state = "identity_check"
        self.prompt_version = self.flow["states"][self.state]["prompt_version"]
        prompt_name = f"{flow_name}-v{self.prompt_version.rsplit('-', 1)[-1]}.txt"
        self.system_prompt = (_ROOT / "prompts" / prompt_name).read_text()
        self.tool_results: list[dict[str, object]] = []
        self.end_call = False

    def allowed_tools(self) -> list[dict[str, object]]:
        names = self.flow["states"][self.state]["allowed_tools"]
        return [_TOOL_SCHEMAS[name] for name in names if name in _TOOL_SCHEMAS]

    async def respond(self, llm: Any, text: str, trace: dict[str, Any]) -> str:
        if re.search(r"\b(?:goodbye|bye|stop (?:calling|now|the call)|end (?:the )?call|do not call|don't call)\b", text, re.IGNORECASE):
            self.end_call = True
            return "Understood. I will end the call now."
        if re.search(r"\b(?:useless|idiot|stupid|fuck(?:ing)?|hate you)\b", text, re.IGNORECASE):
            trace["guardrail_events"].append("conduct_escalation")
            return "I am sorry this is frustrating. I can connect you with a human agent or end the call."
        if re.search(r"\b(?:human|agent|representative|real person)\b", text, re.IGNORECASE):
            tools = self.allowed_tools()
            allowed = {item["function"]["name"] for item in tools}
            if "escalate_to_human" not in allowed:
                return "I cannot complete that request right now."
            state_before = self.state
            output = await self.executor.execute("escalate_to_human", {})
            trace["tool_calls"].append({"name": "escalate_to_human", "arguments": {}, "result": output,
                                        "state": self.state, "state_before": state_before,
                                        "state_after": self.state, "allowed_tools": sorted(allowed),
                                        "arguments_valid": True})
            self.tool_results.append(output)
            return "I will connect you with a human agent."
        chat = getattr(llm, "chat_with_tools", None)
        if chat is None:
            reply = "".join([part async for part in llm.stream_reply(text)]).strip()
            reply, violated = enforce_grounding(reply, self.tool_results)
            if violated:
                trace["guardrail_events"].append("grounding_violation")
            reply, violated = enforce_conduct(reply)
            if violated:
                trace["guardrail_events"].append("conduct_violation")
            return reply
        messages: list[dict[str, object]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": text},
        ]
        for _ in range(5):
            tools = self.allowed_tools()
            result = await chat(messages, tools)
            message = {"role": "assistant", "content": result.get("content", ""), "tool_calls": result.get("tool_calls", [])}
            calls = result.get("tool_calls", [])
            if not calls:
                reply, violation = enforce_grounding(str(message["content"]), self.tool_results)
                if violation:
                    trace["guardrail_events"].append("grounding_violation")
                reply, violation = enforce_conduct(reply)
                if violation:
                    trace["guardrail_events"].append("conduct_violation")
                return reply
            messages.append(message)
            for call in calls:
                function = call.get("function", {})
                name = str(function.get("name", ""))
                args: dict[str, Any] = {}
                state_before = self.state
                allowed_names = {item["function"]["name"] for item in tools}
                arguments_valid = True
                try:
                    raw_args = function.get("arguments", {})
                    if isinstance(raw_args, str):
                        raw_args = json.loads(raw_args)
                    if not isinstance(raw_args, dict):
                        raise ValueError("tool arguments must be an object")
                    args = raw_args
                    if name not in allowed_names:
                        output = {"error": "tool not allowed in current state"}
                    else:
                        _validate_tool_arguments(name, args)
                        output = await self.executor.execute(name, args)
                        if name == "verify_identity" and output.get("verified"):
                            self.state = "verified"
                    self.tool_results.append(output)
                except (ValueError, TypeError, KeyError, json.JSONDecodeError):
                    arguments_valid = False
                    output = {"error": "invalid tool arguments"}
                trace["tool_calls"].append({"name": name, "arguments": args, "result": output,
                                            "state": self.state, "state_before": state_before,
                                            "state_after": self.state, "allowed_tools": sorted(allowed_names),
                                            "arguments_valid": arguments_valid})
                messages.append({"role": "tool", "content": json.dumps(output), "tool_name": name})
        return "I cannot complete that request right now. I can connect you with a human agent."
