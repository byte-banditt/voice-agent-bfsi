import asyncio

from app.tools import BFSIToolExecutor


def test_unverified_tool_call_never_reaches_crm() -> None:
    executor = BFSIToolExecutor("http://127.0.0.1:1", "test-only-key", "cust-demo-1")
    result = asyncio.run(executor.execute("get_customer", {"customer_id": "cust-demo-1"}))
    assert result == {"error": "identity verification required"}


def test_unknown_tool_is_rejected() -> None:
    executor = BFSIToolExecutor("http://127.0.0.1:1", "test-only-key", "cust-demo-1")
    result = asyncio.run(executor.execute("reveal_everything", {}))
    assert result == {"error": "unknown tool"}
