import asyncio

from app.tools import BFSIToolExecutor, _normalize_dob
from app.metrics import TOOL_CALLS, TOOL_SECONDS


def test_spoken_english_date_of_birth_normalizes_to_crm_format() -> None:
    assert _normalize_dob("January 2, 1990") == "1990-01-02"
    assert _normalize_dob("January 2nd, 1990") == "1990-01-02"
    assert _normalize_dob("1990-01-02") == "1990-01-02"
    assert _normalize_dob("01/02/1990") is None
    assert _normalize_dob("February 30, 1990") is None
    assert _normalize_dob("01-02-1990") is None


def test_unverified_tool_call_never_reaches_crm() -> None:
    executor = BFSIToolExecutor("http://127.0.0.1:1", "test-only-key", "cust-demo-1")
    result = asyncio.run(executor.execute("get_customer", {"customer_id": "cust-demo-1"}))
    assert result == {"error": "identity verification required"}


def test_unknown_tool_is_rejected() -> None:
    executor = BFSIToolExecutor("http://127.0.0.1:1", "test-only-key", "cust-demo-1")
    result = asyncio.run(executor.execute("reveal_everything", {}))
    assert result == {"error": "unknown tool"}


def test_third_failed_identity_attempt_locks_verification_and_escalates(monkeypatch) -> None:
    import httpx

    requests = []

    class Response:
        status_code = 200
        def __init__(self, url): self.request = httpx.Request("POST", url)
        def raise_for_status(self): return None
        def json(self):
            return {"status": "queued"} if "escalate_to_human" in self.request.url.path else {"verified": False}

    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def post(self, url, **kwargs):
            requests.append(url)
            return Response(url)

    monkeypatch.setattr("app.tools.httpx.AsyncClient", lambda **kwargs: Client())
    executor = BFSIToolExecutor("http://crm.test", "synthetic-key", "cust-demo-1")
    async def run():
        outcomes = [await executor.execute("verify_identity", {"dob": "1990-01-02", "phone_last4": "0000"})
                    for _ in range(4)]
        return outcomes
    outcomes = asyncio.run(run())
    assert [url.rsplit("/", 1)[-1] for url in requests] == ["verify_identity", "verify_identity", "verify_identity", "escalate_to_human"]
    assert outcomes[2]["status"] == "queued"
    assert outcomes[3] == {"verified": False}
    assert executor.identity.attempts == 3


def test_backend_tool_metrics_count_calls_and_latency() -> None:
    executor = BFSIToolExecutor("http://127.0.0.1:1", "test-only-key", "cust-demo-1")
    calls_before = TOOL_CALLS.labels("get_customer", "error")._value.get()
    asyncio.run(executor.execute("get_customer", {"customer_id": "cust-demo-1"}))
    assert TOOL_CALLS.labels("get_customer", "error")._value.get() == calls_before + 1
    assert TOOL_SECONDS.labels("get_customer")._sum.get() > 0
