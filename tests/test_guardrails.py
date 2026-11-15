from app.guardrails import IdentityGate, SAFE_FALLBACK, enforce_grounding, redact_pii


def test_identity_gate_limits_attempts_and_protects_data() -> None:
    gate = IdentityGate()
    expected = {"dob": "1990-01-02", "phone_last4": "0134"}
    assert not gate.verify("cust-demo-1", "wrong", "0000", expected)
    assert not gate.verify("cust-demo-1", "wrong", "0000", expected)
    assert not gate.verify("cust-demo-1", "wrong", "0000", expected)
    assert gate.escalated
    assert not gate.authorize("cust-demo-1")


def test_identity_gate_authorizes_only_verified_customer() -> None:
    gate = IdentityGate()
    assert gate.verify("cust-demo-1", "1990-01-02", "0134", {"dob": "1990-01-02", "phone_last4": "0134"})
    assert gate.authorize("cust-demo-1")
    assert not gate.authorize("other-customer")


def test_grounding_replaces_unsubstantiated_financial_claim() -> None:
    reply, violated = enforce_grounding("Your EMI is 1200 rupees.", [{"amount": "900 rupees"}])
    assert violated
    assert reply == SAFE_FALLBACK


def test_grounding_accepts_tool_backed_claim() -> None:
    reply, violated = enforce_grounding("Your account number is loan-demo-1", [{"id": "loan-demo-1"}])
    assert not violated
    assert "loan-demo-1" in reply


def test_redaction_removes_common_transcript_pii() -> None:
    redacted = redact_pii("Call me at +1 202 555 0101 or a@example.test on 1990-01-02")
    assert "+1 202 555 0101" not in redacted
    assert "a@example.test" not in redacted
    assert "1990-01-02" not in redacted
