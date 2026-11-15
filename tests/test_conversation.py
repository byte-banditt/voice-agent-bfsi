import asyncio

from app.conversation import ConversationEngine
from app.tools import BFSIToolExecutor


class ToolLLM:
    def __init__(self):
        self.calls = 0
        self.allowed = []

    async def chat_with_tools(self, messages, tools):
        self.allowed.append({tool["function"]["name"] for tool in tools})
        self.calls += 1
        if self.calls == 1:
            return {"content": "", "tool_calls": [{"function": {"name": "get_loan_status", "arguments": {"loan_id": "loan-demo-1"}}}]}
        if self.calls == 2:
            return {"content": "", "tool_calls": [{"function": {"name": "verify_identity", "arguments": {"dob": "1990-01-02", "phone_last4": "0134"}}}]}
        if self.calls == 3:
            return {"content": "", "tool_calls": [{"function": {"name": "get_loan_status", "arguments": {"loan_id": "loan-demo-1"}}}]}
        return {"content": "Your status is due.", "tool_calls": []}


def test_engine_limits_tools_to_flow_state_and_runs_tool_loop():
    engine = ConversationEngine("emi_reminder", BFSIToolExecutor("http://127.0.0.1:1", "key", "cust-demo-1"))
    async def execute(name, args):
        return {"verified": True} if name == "verify_identity" else {"status": "due", "amount": "1200", "due_date": "2030-01-15"}
    engine.executor.execute = execute
    llm = ToolLLM()
    trace = {"tool_calls": [], "guardrail_events": []}

    reply = asyncio.run(engine.respond(llm, "check my status", trace))

    assert llm.allowed[0] == {"verify_identity"}
    assert trace["tool_calls"][0]["result"] == {"error": "tool not allowed in current state"}
    assert engine.state == "verified"
    assert "get_loan_status" not in llm.allowed[1]
    assert "get_loan_status" in llm.allowed[2]
    assert reply == "Your status is due."
