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

    reply = asyncio.run(engine.respond(llm, "check my status. My date of birth is January 2, 1990 and phone last four are 0134", trace))

    assert llm.allowed[0] == {"verify_identity", "escalate_to_human"}
    assert trace["tool_calls"][0]["result"] == {"error": "tool not allowed in current state"}
    assert engine.state == "verified"
    assert "get_loan_status" not in llm.allowed[1]
    assert "get_loan_status" in llm.allowed[2]
    assert reply == "Your status is due."


def test_human_request_escalates_without_identity_disclosure():
    engine = ConversationEngine("emi_reminder", BFSIToolExecutor("http://127.0.0.1:1", "key", "cust-demo-1"))
    calls = []

    async def execute(name, args):
        calls.append((name, args))
        return {"status": "queued"}

    engine.executor.execute = execute
    trace = {"tool_calls": [], "guardrail_events": []}
    reply = asyncio.run(engine.respond(ToolLLM(), "Please connect me to a human", trace))
    assert calls == [("escalate_to_human", {})]
    assert reply == "I will connect you with a human agent."
    assert trace["tool_calls"][0]["name"] == "escalate_to_human"


def test_failed_human_transfer_is_not_reported_as_success():
    engine = ConversationEngine("emi_reminder", BFSIToolExecutor("http://127.0.0.1:1", "key", "cust-demo-1"))
    async def fail_transfer(name, args):
        return {"error": "escalation service unavailable"}
    engine.executor.execute = fail_transfer
    trace = {"tool_calls": [], "guardrail_events": []}
    reply = asyncio.run(engine.respond(ToolLLM(), "Please connect me with a human", trace))
    assert "could not reach" in reply
    assert "human_escalation_failed" in trace["guardrail_events"]


def test_payment_dispute_forces_human_escalation():
    engine = ConversationEngine("emi_reminder", BFSIToolExecutor("http://127.0.0.1:1", "key", "cust-demo-1"))
    calls = []
    async def execute(name, args):
        calls.append(name)
        return {"status": "queued"}
    engine.executor.execute = execute
    trace = {"tool_calls": [], "guardrail_events": []}
    reply = asyncio.run(engine.respond(ToolLLM(), "I want to dispute this payment", trace))
    assert calls == ["escalate_to_human"]
    assert "complaint" in reply
    assert "complaint_escalation" in trace["guardrail_events"]


def test_unsupported_financial_advice_and_unclear_requests_are_bounded():
    engine = ConversationEngine("emi_reminder", BFSIToolExecutor("http://127.0.0.1:1", "key", "cust-demo-1"))
    trace = {"tool_calls": [], "guardrail_events": []}
    advice = asyncio.run(engine.respond(ToolLLM(), "Which stock should I invest in?", trace))
    unclear = asyncio.run(engine.respond(ToolLLM(), "I am confused", trace))
    code_switch = asyncio.run(engine.respond(ToolLLM(), "Mera loan ka status kya hai?", trace))
    assert "cannot provide investment" in advice
    assert "whether you need loan status" in unclear
    assert "cannot reliably handle" in code_switch
    assert trace["tool_calls"] == []


def test_numeric_fake_reply_is_grounded_before_speech():
    class NumericLLM:
        async def stream_reply(self, transcript):
            yield "Your amount is 500."

    engine = ConversationEngine("emi_reminder", BFSIToolExecutor("http://127.0.0.1:1", "key", "cust-demo-1"))
    trace = {"tool_calls": [], "guardrail_events": []}
    reply = asyncio.run(engine.respond(NumericLLM(), "tell me my amount", trace))
    assert reply == "I cannot confirm that information right now. I can connect you with a human agent."
    assert trace["guardrail_events"] == ["grounding_violation"]


def test_unverified_status_request_cannot_leak_categorical_status():
    class LeakyLLM:
        async def stream_reply(self, transcript):
            yield "Your loan is overdue."
    engine = ConversationEngine("emi_reminder", BFSIToolExecutor("http://127.0.0.1:1", "key", "cust-demo-1"))
    trace = {"tool_calls": [], "guardrail_events": []}
    reply = asyncio.run(engine.respond(LeakyLLM(), "What is my loan status?", trace))
    assert reply == "I need to verify your identity before discussing loan or payment information."
    assert trace["tool_calls"] == []


def test_stop_request_uses_polite_exit_and_ends_call():
    engine = ConversationEngine("emi_reminder", BFSIToolExecutor("http://127.0.0.1:1", "key", "cust-demo-1"))
    trace = {"tool_calls": [], "guardrail_events": []}
    reply = asyncio.run(engine.respond(ToolLLM(), "Please end the call", trace))
    assert reply == "Understood. I will end the call now."
    assert engine.end_call


def test_opt_out_request_ends_call_without_tool_activity():
    engine = ConversationEngine("emi_reminder", BFSIToolExecutor("http://127.0.0.1:1", "key", "cust-demo-1"))
    trace = {"tool_calls": [], "guardrail_events": []}
    reply = asyncio.run(engine.respond(ToolLLM(), "Please opt out and remove me from calls", trace))
    assert reply == "Understood. I will end the call now."
    assert engine.end_call
    assert trace["tool_calls"] == []


def test_malformed_tool_arguments_are_rejected_without_execution():
    class InvalidArgsLLM:
        async def chat_with_tools(self, messages, tools):
            return {"content": "", "tool_calls": [{"function": {
                "name": "verify_identity", "arguments": {"dob": "1990-01-01"}}}]}

    engine = ConversationEngine("emi_reminder", BFSIToolExecutor("http://127.0.0.1:1", "key", "cust-demo-1"))
    async def must_not_execute(name, args):
        raise AssertionError("invalid tool call reached executor")
    engine.executor.execute = must_not_execute
    trace = {"tool_calls": [], "guardrail_events": []}
    asyncio.run(engine.respond(InvalidArgsLLM(), "verify me", trace))
    assert trace["tool_calls"][0]["result"] == {"error": "invalid tool arguments"}


def test_plausible_but_invented_identity_values_never_reach_executor():
    class GuessingLLM:
        async def chat_with_tools(self, messages, tools):
            return {"content": "", "tool_calls": [{"function": {"name": "verify_identity",
                    "arguments": {"dob": "1990-01-02", "phone_last4": "0134"}}}]}

    engine = ConversationEngine("emi_reminder", BFSIToolExecutor("http://127.0.0.1:1", "key", "cust-demo-1"))
    async def must_not_execute(name, args):
        raise AssertionError("invented identity factors reached CRM executor")
    engine.executor.execute = must_not_execute
    trace = {"tool_calls": [], "guardrail_events": []}
    reply = asyncio.run(engine.respond(GuessingLLM(), "I forgot my details", trace))
    assert "repeat your date of birth" in reply
    assert trace["tool_calls"][0]["arguments_valid"] is False
    assert trace["tool_calls"][0]["result"]["error"] == "identity arguments not grounded in caller input"


def test_phone_suffix_cannot_be_inferred_from_a_nearby_dob():
    class GuessingLLM:
        async def chat_with_tools(self, messages, tools):
            return {"content": "", "tool_calls": [{"function": {"name": "verify_identity",
                    "arguments": {"dob": "1990-01-02", "phone_last4": "1990"}}}]}
    engine = ConversationEngine("emi_reminder", BFSIToolExecutor("http://127.0.0.1:1", "key", "cust-demo-1"))
    async def must_not_execute(name, args):
        raise AssertionError("DOB digits were mistaken for a phone suffix")
    engine.executor.execute = must_not_execute
    trace = {"tool_calls": [], "guardrail_events": []}
    reply = asyncio.run(engine.respond(GuessingLLM(), "My date of birth is 1990-01-02; phone suffix unknown", trace))
    assert "repeat your date of birth" in reply
    assert trace["tool_calls"][0]["arguments_valid"] is False


def test_server_requires_status_lookup_when_verified_caller_asks():
    class OmittingLLM:
        calls = 0
        async def chat_with_tools(self, messages, tools):
            self.calls += 1
            if self.calls == 1:
                return {"content": "", "tool_calls": [{"function": {"name": "verify_identity",
                        "arguments": {"dob": "1990-01-02", "phone_last4": "0134"}}}]}
            return {"content": "Your status is fine.", "tool_calls": []}

    engine = ConversationEngine("emi_reminder", BFSIToolExecutor("http://127.0.0.1:1", "key", "cust-demo-1"))
    calls = []
    async def execute(name, args):
        calls.append((name, args))
        return {"verified": True} if name == "verify_identity" else {"status": "due", "amount": "1200", "due_date": "2030-01-15"}
    engine.executor.execute = execute
    trace = {"tool_calls": [], "guardrail_events": []}
    reply = asyncio.run(engine.respond(OmittingLLM(),
        "Please check my loan status. DOB January 2, 1990, phone last four 0134.", trace))
    assert calls == [("verify_identity", {"dob": "1990-01-02", "phone_last4": "0134"}), ("get_loan_status", {})]
    assert any(item.get("source") == "server_required_status_lookup" for item in trace["tool_calls"])
    assert reply == "Your status is fine."


def test_model_cannot_read_loan_status_without_caller_request():
    class UnrequestedStatusLLM:
        async def chat_with_tools(self, messages, tools):
            return {"content": "", "tool_calls": [{"function": {"name": "get_loan_status",
                    "arguments": {"loan_id": "loan-demo-1"}}}]}
    engine = ConversationEngine("emi_reminder", BFSIToolExecutor("http://127.0.0.1:1", "key", "cust-demo-1"))
    engine.state = "verified"
    engine.executor.identity.customer_id = "cust-demo-1"
    async def must_not_execute(name, args):
        raise AssertionError("unrequested status reached CRM")
    engine.executor.execute = must_not_execute
    trace = {"tool_calls": [], "guardrail_events": []}
    asyncio.run(engine.respond(UnrequestedStatusLLM(), "Hello", trace))
    assert trace["tool_calls"][0]["result"] == {"error": "loan status was not requested by the caller"}


def test_model_cannot_choose_an_unspoken_loan_identifier():
    class GuessedLoanLLM:
        calls = 0
        async def chat_with_tools(self, messages, tools):
            self.calls += 1
            if self.calls == 1:
                return {"content": "", "tool_calls": [{"function": {"name": "get_loan_status",
                        "arguments": {"loan_id": "loan-other-1"}}}]}
            return {"content": "Your status is due.", "tool_calls": []}
    engine = ConversationEngine("emi_reminder", BFSIToolExecutor("http://127.0.0.1:1", "key", "cust-demo-1"))
    engine.state = "verified"
    engine.executor.identity.customer_id = "cust-demo-1"
    calls = []
    async def execute(name, args):
        calls.append((name, args))
        return {"id": "loan-demo-1", "status": "due", "amount": "1200", "due_date": "2030-01-15"}
    engine.executor.execute = execute
    trace = {"tool_calls": [], "guardrail_events": []}
    asyncio.run(engine.respond(GuessedLoanLLM(), "Tell me my loan status", trace))
    assert calls == [("get_loan_status", {})]
    assert trace["tool_calls"][0]["arguments_valid"] is False
    assert trace["tool_calls"][0]["server_resolved_active_loan"] is True


def test_failed_status_lookup_does_not_retry_on_later_unrelated_turn():
    class NoCallLLM:
        async def chat_with_tools(self, messages, tools):
            return {"content": "I can help with that.", "tool_calls": []}
    engine = ConversationEngine("emi_reminder", BFSIToolExecutor("http://127.0.0.1:1", "key", "cust-demo-1"))
    engine.state = "verified"
    engine.executor.identity.customer_id = "cust-demo-1"
    calls = []
    async def unavailable(name, args):
        calls.append((name, args))
        return {"error": "CRM timeout"}
    engine.executor.execute = unavailable
    trace = {"tool_calls": [], "guardrail_events": []}
    asyncio.run(engine.respond(NoCallLLM(), "Please check my loan status", trace))
    asyncio.run(engine.respond(NoCallLLM(), "Hello", trace))
    assert calls == [("get_loan_status", {})]


def test_repeated_state_change_tool_is_not_executed_twice():
    class DuplicateLLM:
        calls = 0
        async def chat_with_tools(self, messages, tools):
            self.calls += 1
            if self.calls == 1:
                return {"content": "", "tool_calls": [{"function": {"name": "verify_identity",
                        "arguments": {"dob": "1990-01-02", "phone_last4": "0134"}}}]}
            return {"content": "", "tool_calls": [
                {"function": {"name": "schedule_callback", "arguments": {"requested_at": "2030-01-16T10:00:00Z"}}},
                {"function": {"name": "schedule_callback", "arguments": {"requested_at": "2030-01-16T10:00:00Z"}}},
            ]}

    engine = ConversationEngine("emi_reminder", BFSIToolExecutor("http://127.0.0.1:1", "key", "cust-demo-1"))
    calls = []
    async def execute(name, args):
        calls.append((name, args))
        return {"verified": True} if name == "verify_identity" else {"scheduled": True}
    engine.executor.execute = execute
    trace = {"tool_calls": [], "guardrail_events": []}
    asyncio.run(engine.respond(DuplicateLLM(), "Check my loan status; DOB January 2, 1990 and phone last four 0134. Schedule callback at 2030-01-16T10:00:00Z", trace))
    assert calls.count(("schedule_callback", {"requested_at": "2030-01-16T10:00:00Z"})) == 1
    assert sum(item.get("idempotent_replay", False) for item in trace["tool_calls"]) >= 1


def test_callback_date_and_time_must_come_from_caller():
    class CallbackLLM:
        async def chat_with_tools(self, messages, tools):
            return {"content": "", "tool_calls": [{"function": {"name": "schedule_callback",
                    "arguments": {"requested_at": "2030-01-16T10:00:00Z"}}}]}

    engine = ConversationEngine("emi_reminder", BFSIToolExecutor("http://127.0.0.1:1", "key", "cust-demo-1"))
    engine.state = "verified"
    engine.executor.identity.customer_id = "cust-demo-1"
    async def must_not_execute(name, args):
        raise AssertionError("invented callback time reached CRM")
    engine.executor.execute = must_not_execute
    trace = {"tool_calls": [], "guardrail_events": []}
    reply = asyncio.run(engine.respond(CallbackLLM(), "Please call me back sometime next week", trace))
    assert reply == "Please confirm the callback date, time, and time zone before I schedule it."
    assert trace["tool_calls"][0]["arguments_valid"] is False


def test_negated_callback_and_payment_link_requests_do_not_execute():
    class ActionLLM:
        def __init__(self, name, arguments): self.name, self.arguments = name, arguments
        async def chat_with_tools(self, messages, tools):
            return {"content": "", "tool_calls": [{"function": {"name": self.name, "arguments": self.arguments}}]}

    engine = ConversationEngine("emi_reminder", BFSIToolExecutor("http://127.0.0.1:1", "key", "cust-demo-1"))
    engine.state = "verified"
    engine.executor.identity.customer_id = "cust-demo-1"
    async def must_not_execute(name, args):
        raise AssertionError("negated request reached backend")
    engine.executor.execute = must_not_execute
    callback_trace = {"tool_calls": [], "guardrail_events": []}
    asyncio.run(engine.respond(ActionLLM("schedule_callback", {"requested_at": "2030-01-16T10:00:00Z"}),
        "I don't want a callback at 2030-01-16T10:00:00Z", callback_trace))
    stop_trace = {"tool_calls": [], "guardrail_events": []}
    asyncio.run(engine.respond(ActionLLM("schedule_callback", {"requested_at": "2030-01-16T10:00:00Z"}),
        "Don't call me back at 2030-01-16T10:00:00Z", stop_trace))
    link_trace = {"tool_calls": [], "guardrail_events": []}
    asyncio.run(engine.respond(ActionLLM("create_payment_link", {}), "Don't send me a payment link.", link_trace))
    assert callback_trace["tool_calls"][0]["result"]["error"] == "callback was not requested by the caller"
    assert stop_trace["tool_calls"] == []
    assert engine.end_call is True
    assert link_trace["tool_calls"][0]["result"]["error"] == "payment link was not requested by the caller"
