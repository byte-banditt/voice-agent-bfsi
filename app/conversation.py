from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from app.guardrails import enforce_action_claims, enforce_conduct, enforce_grounding
from app.tools import BFSIToolExecutor, _normalize_dob

_ROOT = Path(__file__).resolve().parent.parent
_TOOL_SCHEMAS: dict[str, dict[str, object]] = {
    "verify_identity": {"type": "function", "function": {"name": "verify_identity", "description": "Verify the caller using date of birth (ISO YYYY-MM-DD or a clearly spoken English month, day, and year) and phone last four digits", "parameters": {"type": "object", "properties": {"dob": {"type": "string"}, "phone_last4": {"type": "string"}}, "required": ["dob", "phone_last4"]}}},
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
        self.action_results: list[dict[str, object]] = []
        self.end_call = False
        self.status_requested = False
        self._executed_tool_keys: set[str] = set()
        self._tool_result_cache: dict[str, dict[str, Any]] = {}
        self._current_status_result: dict[str, Any] | None = None

    @staticmethod
    def _identity_arguments_grounded(arguments: dict[str, Any], caller_text: str) -> bool:
        """Require model-supplied verification factors to appear in this caller turn."""
        dob = _normalize_dob(str(arguments.get("dob", "")))
        dob_label = re.search(r"\b(?:dob|date of birth|born on)\b", caller_text, re.IGNORECASE)
        dob_context = caller_text[dob_label.end():dob_label.end() + 60] if dob_label else ""
        caller_dates = re.findall(
            r"(?<!\d)(?:\d{4}-\d{1,2}-\d{1,2}|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?[,]?\s+\d{4})(?!\d)",
            dob_context, re.IGNORECASE,
        )
        date_grounded = dob is not None and any(_normalize_dob(value) == dob for value in caller_dates)
        phone = re.sub(r"\D", "", str(arguments.get("phone_last4", "")))
        phone_pattern = re.compile(
            r"\b(?:phone(?: number)?(?:\s+(?:last\s+(?:four|4)(?:\s+digits?)?|ends?\s+in|is))?|"
            r"last\s+(?:four|4)\s+digits?(?:\s+of\s+(?:my\s+)?phone))\s*(?:are|is|in|:|=)?\s*((?:\d[ -]?){3}\d)(?!\d)",
            re.IGNORECASE,
        )
        caller_phone_digits = [match.group(1) for match in phone_pattern.finditer(caller_text)]
        phone_grounded = len(phone) == 4 and any(
            re.sub(r"\D", "", value) == phone for value in caller_phone_digits
        )
        return date_grounded and phone_grounded

    @staticmethod
    def _callback_arguments_grounded(arguments: dict[str, Any], caller_text: str) -> bool:
        requested_at = str(arguments.get("requested_at", ""))
        try:
            requested = datetime.fromisoformat(requested_at)
        except ValueError:
            return False
        timezone_match = re.search(r"Z(?=$|[.,!?\s])|\bUTC\b|\bGMT\b|[+-]\d{2}:\d{2}", caller_text, re.IGNORECASE)
        if requested.tzinfo is None or timezone_match is None:
            return False
        expected_offset = timezone_match.group(0)
        actual_offset = requested.strftime("%z")
        if expected_offset.upper() in {"Z", "UTC", "GMT"}:
            if actual_offset not in {"+0000", "-0000"}:
                return False
        elif actual_offset != expected_offset.replace(":", ""):
            return False
        caller_dates = re.findall(
            r"(?<!\d)(?:\d{4}-\d{1,2}-\d{1,2}|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?[,]?\s+\d{4})(?!\d)",
            caller_text, re.IGNORECASE,
        )
        if not any(_normalize_dob(value) == requested.date().isoformat() for value in caller_dates):
            return False
        caller_times = [
            (int(hour), int(minute))
            for hour, minute in re.findall(r"(?:T|\b)([01]?\d|2[0-3]):([0-5]\d)\b", caller_text, re.IGNORECASE)
        ]
        for hour, minute, meridiem in re.findall(r"\b(1[0-2]|0?[1-9])(?::([0-5]\d))?\s*(AM|PM)\b", caller_text, re.IGNORECASE):
            hour_value = int(hour) % 12 + (12 if meridiem.casefold() == "pm" else 0)
            caller_times.append((hour_value, int(minute or 0)))
        return (requested.hour, requested.minute) in caller_times

    @staticmethod
    def _loan_id_grounded(arguments: dict[str, Any], caller_text: str) -> bool:
        loan_id = str(arguments.get("loan_id", "")).strip()
        return bool(loan_id and re.search(rf"(?<![\w]){re.escape(loan_id)}(?![\w])", caller_text, re.IGNORECASE))

    def allowed_tools(self) -> list[dict[str, object]]:
        names = self.flow["states"][self.state]["allowed_tools"]
        return [_TOOL_SCHEMAS[name] for name in names if name in _TOOL_SCHEMAS]

    def _tool_observation(self, result: dict[str, Any]) -> dict[str, object]:
        observation: dict[str, object] = {}
        duration = getattr(self.executor, "last_call_seconds", 0.0)
        if duration > 0:
            observation["duration_seconds"] = duration
        if "error" in result:
            error = str(result["error"]).casefold()
            observation["error_category"] = next(
                (term for term in ("timeout", "unavailable", "rejected", "identity", "invalid", "unknown", "duplicate") if term in error),
                "other",
            )
        return observation

    def _status_failure_reply(self) -> str:
        self.status_requested = False
        self._current_status_result = None
        return "I cannot retrieve the loan status right now. I can connect you with a human agent."

    async def respond(self, llm: Any, text: str, trace: dict[str, Any]) -> str:
        if not text.strip():
            return "I did not hear a clear request. Please repeat, or ask for a human agent."
        self._current_status_result = None
        if re.search(r"\b(?:loan|emi|balance|outstanding|due date|payment status|loan status|status)\b", text, re.IGNORECASE):
            self.status_requested = True
        callback_requested = bool(re.search(r"\b(?:callback|call me back|return my call)\b", text, re.IGNORECASE))
        callback_refused = bool(re.search(
            r"\b(?:no callback|don't want a callback|do not want a callback|don't need a callback|do not need a callback|"
            r"don't call me back|do not call me back|don't schedule a callback|do not schedule a callback|no need to)\b.{0,24}\b(?:callback|call me back)\b|"
            r"\b(?:no callback|don't want a callback|do not want a callback|don't need a callback|do not need a callback|don't call me back|do not call me back)\b",
            text, re.IGNORECASE,
        ))
        callback_requested = callback_requested and not callback_refused
        payment_link_requested = bool(re.search(r"\b(?:payment link|pay link|send me (?:a )?link)\b", text, re.IGNORECASE))
        payment_link_refused = bool(re.search(
            r"\b(?:don't|do not|never|no)\b.{0,24}\b(?:send|create|generate|want)\b.{0,24}\b(?:payment link|pay link|link)\b|"
            r"\b(?:payment link|pay link)\b.{0,16}\b(?:not|don't|no)\b|\bno\s+(?:need for\s+|to send\s+)?(?:a\s+)?(?:payment link|pay link)\b",
            text, re.IGNORECASE,
        ))
        payment_link_requested = payment_link_requested and not payment_link_refused
        outcome_requested = bool(re.search(r"\b(?:i can pay|i will pay|partial payment|payment offer|i paid)\b", text, re.IGNORECASE))
        tool_calls_before = len(trace["tool_calls"])
        if re.search(r"\b(?:goodbye|bye|stop (?:calling|now|the call)|end (?:the )?call|do not call|don't call|opt out|remove me from calls)\b", text, re.IGNORECASE):
            self.end_call = True
            return "Understood. I will end the call now."
        if re.search(r"\b(?:mera loan|kitna emi|paisa kab|ನನ್ನ ಸಾಲ|என் கடன்)\b", text, re.IGNORECASE):
            return "I cannot reliably handle this language mix in the local prototype. I can connect you with a human agent."
        if re.search(r"\b(?:which stock|what stock|should i invest|investment advice|guaranteed returns?|financial advice|recommend (?:a )?(?:loan|investment))\b", text, re.IGNORECASE):
            return "I cannot provide investment or financial advice. I can help with verified loan information or connect you with a human agent."
        if re.search(r"\b(?:i am confused|i'm confused|i do not understand|i don't understand|not sure what|unclear)\b", text, re.IGNORECASE):
            return "Could you tell me whether you need loan status, a callback, or a human agent?"
        if re.search(r"\b(?:useless|idiot|stupid|fuck(?:ing)?|hate you)\b", text, re.IGNORECASE):
            trace["guardrail_events"].append("conduct_escalation")
            return "I am sorry this is frustrating. I can connect you with a human agent or end the call."
        complaint = re.search(r"\b(?:complaint|dispute|disputing|wrong (?:amount|charge|payment)|payment (?:was )?not (?:made|credited))\b", text, re.IGNORECASE)
        if complaint or re.search(r"\b(?:human|agent|representative|real person)\b", text, re.IGNORECASE):
            tools = self.allowed_tools()
            allowed = {item["function"]["name"] for item in tools}
            if "escalate_to_human" not in allowed:
                return "I cannot complete that request right now."
            state_before = self.state
            output = await self.executor.execute("escalate_to_human", {})
            trace["tool_calls"].append({"name": "escalate_to_human", "arguments": {}, "result": output,
                                        "state": self.state, "state_before": state_before,
                                        "state_after": self.state, "allowed_tools": sorted(allowed),
                                        "arguments_valid": True, **self._tool_observation(output)})
            if complaint:
                trace["guardrail_events"].append("complaint_escalation")
            if "error" in output:
                trace["guardrail_events"].append("human_escalation_failed")
                return "I could not reach a human agent right now. I can try again or end the call."
            return "I will connect you with a human agent to review this complaint." if complaint else "I will connect you with a human agent."
        chat = getattr(llm, "chat_with_tools", None)
        if chat is None:
            if self.status_requested and self.state != "verified":
                return "I need to verify your identity before discussing loan or payment information."
            if self.status_requested:
                status_result = await self.executor.execute("get_loan_status", {})
                self._current_status_result = status_result
                trace["tool_calls"].append({"name": "get_loan_status", "arguments": {}, "result": status_result,
                                            "state": self.state, "state_before": self.state,
                                            "state_after": self.state, "allowed_tools": sorted(
                                                item["function"]["name"] for item in self.allowed_tools()),
                                            "arguments_valid": True, "source": "server_required_status_lookup",
                                            **self._tool_observation(status_result)})
                if "error" in status_result:
                    return self._status_failure_reply()
                self.tool_results.append(status_result)
                self.action_results.append(status_result)
                self.status_requested = False
            reply = "".join([part async for part in llm.stream_reply(text)]).strip()
            reply, violated = enforce_grounding(reply, self.tool_results)
            if violated:
                trace["guardrail_events"].append("grounding_violation")
            reply, violated = enforce_action_claims(reply, self.action_results)
            if violated:
                trace["guardrail_events"].append("unsupported_action_claim")
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
                if self.status_requested and self.state != "verified":
                    return "I need to verify your identity before discussing loan or payment information."
                status_lookup_succeeded = any(
                    item.get("name") == "get_loan_status" and isinstance(item.get("result"), dict)
                    and "error" not in item["result"] for item in trace["tool_calls"][tool_calls_before:]
                )
                if self.status_requested and self.state == "verified" and not status_lookup_succeeded:
                    status_result = await self.executor.execute("get_loan_status", {})
                    trace["tool_calls"].append({"name": "get_loan_status", "arguments": {}, "result": status_result,
                                                "state": self.state, "state_before": self.state,
                                                "state_after": self.state, "allowed_tools": sorted(
                                                    item["function"]["name"] for item in self.allowed_tools()),
                                                "arguments_valid": True, "source": "server_required_status_lookup",
                                                **self._tool_observation(status_result)})
                    if "error" in status_result:
                        return self._status_failure_reply()
                    self.tool_results.append(status_result)
                    self.action_results.append(status_result)
                    self.status_requested = False
                reply, violation = enforce_grounding(str(message["content"]), self.tool_results)
                if violation:
                    trace["guardrail_events"].append("grounding_violation")
                reply, violation = enforce_action_claims(reply, self.action_results)
                if violation:
                    trace["guardrail_events"].append("unsupported_action_claim")
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
                duplicate_replay = False
                server_resolved_loan = False
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
                        call_key = name + ":" + json.dumps(args, sort_keys=True, separators=(",", ":"))
                        deduplicated_operation = name in {
                            "get_customer", "get_loan_status", "schedule_callback",
                            "log_call_outcome", "create_payment_link", "escalate_to_human",
                        }
                        if deduplicated_operation and call_key in self._executed_tool_keys:
                            output = self._tool_result_cache[call_key]
                            duplicate_replay = True
                        elif name == "verify_identity" and not self._identity_arguments_grounded(args, text):
                            output = {"error": "identity arguments not grounded in caller input"}
                            arguments_valid = False
                        elif name == "schedule_callback" and not self._callback_arguments_grounded(args, text):
                            output = {"error": "callback date and time must be clearly supplied by caller"}
                            arguments_valid = False
                        elif name == "schedule_callback" and not callback_requested:
                            output = {"error": "callback was not requested by the caller"}
                            arguments_valid = False
                        elif name == "create_payment_link" and not payment_link_requested:
                            output = {"error": "payment link was not requested by the caller"}
                            arguments_valid = False
                        elif name == "log_call_outcome" and not outcome_requested:
                            output = {"error": "payment outcome was not supplied by the caller"}
                            arguments_valid = False
                        elif name == "get_loan_status" and not self.status_requested:
                            if self._current_status_result is None:
                                output = {"error": "loan status was not requested by the caller"}
                                arguments_valid = False
                            else:
                                output = self._current_status_result
                        elif name == "get_loan_status" and not self._loan_id_grounded(args, text):
                            if self._current_status_result and self._current_status_result.get("id") == args.get("loan_id"):
                                output = self._current_status_result
                            else:
                                arguments_valid = False
                                server_resolved_loan = True
                                output = await self.executor.execute(name, {})
                        else:
                            if deduplicated_operation:
                                self._executed_tool_keys.add(call_key)
                            output = await self.executor.execute(name, args)
                            if deduplicated_operation:
                                self._tool_result_cache[call_key] = output
                        if name == "verify_identity" and output.get("verified"):
                            self.state = "verified"
                    if name in {"get_customer", "get_loan_status"} and "error" not in output:
                        self.tool_results.append(output)
                    self.action_results.append(output)
                except (ValueError, TypeError, KeyError, json.JSONDecodeError):
                    arguments_valid = False
                    output = {"error": "invalid tool arguments"}
                trace["tool_calls"].append({"name": name, "arguments": args, "result": output,
                                            "state": self.state, "state_before": state_before,
                                            "state_after": self.state, "allowed_tools": sorted(allowed_names),
                                            "arguments_valid": arguments_valid,
                                            **({"server_resolved_active_loan": True} if server_resolved_loan else {}),
                                            **({} if duplicate_replay else self._tool_observation(output)),
                                            **({"idempotent_replay": True} if duplicate_replay else {})})
                messages.append({"role": "tool", "content": json.dumps(output), "tool_name": name})
                if name == "verify_identity" and output.get("error") == "identity arguments not grounded in caller input":
                    return "I did not clearly hear those details. Please repeat your date of birth and the last four digits of your phone number."
                if name == "schedule_callback" and output.get("error") == "callback date and time must be clearly supplied by caller":
                    return "Please confirm the callback date, time, and time zone before I schedule it."
                if name == "schedule_callback" and output.get("error") == "callback was not requested by the caller":
                    return "Understood. I will not schedule a callback."
                if name == "create_payment_link" and output.get("error") == "payment link was not requested by the caller":
                    return "Understood. I will not create a payment link."
                if name == "log_call_outcome" and output.get("error") == "payment outcome was not supplied by the caller":
                    return "I did not record a payment outcome because you did not state one."
                if name == "get_loan_status" and output.get("error") == "loan status was not requested by the caller":
                    return "I did not look up loan details because you did not ask for a status check."
                if name == "get_loan_status" and "error" not in output:
                    self.status_requested = False
                    self._current_status_result = output
                elif name == "get_loan_status" and "error" in output and self.status_requested and self.state == "verified":
                    return self._status_failure_reply()
                status_lookup_succeeded = any(
                    item.get("name") == "get_loan_status" and isinstance(item.get("result"), dict)
                    and "error" not in item["result"] for item in trace["tool_calls"][tool_calls_before:]
                )
                if self.status_requested and self.state == "verified" and not status_lookup_succeeded:
                    status_result = await self.executor.execute("get_loan_status", {})
                    self._current_status_result = status_result
                    trace["tool_calls"].append({"name": "get_loan_status", "arguments": {}, "result": status_result,
                                                "state": self.state, "state_before": self.state,
                                                "state_after": self.state, "allowed_tools": sorted(allowed_names),
                                                "arguments_valid": True, "source": "server_required_status_lookup",
                                                **self._tool_observation(status_result)})
                    if "error" in status_result:
                        return self._status_failure_reply()
                    self.tool_results.append(status_result)
                    self.action_results.append(status_result)
        return "I cannot complete that request right now. I can connect you with a human agent."
