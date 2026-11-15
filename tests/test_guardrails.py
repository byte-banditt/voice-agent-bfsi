from app.guardrails import (CONDUCT_FALLBACK, IdentityGate, SAFE_FALLBACK,
                            declines_recording_consent, enforce_conduct,
                            enforce_grounding, grants_recording_consent, redact_pii)


def test_consent_recognizes_spoken_yes_variants_without_accepting_ambiguous_text() -> None:
    for transcript in ("yes", "Yes.", "yeah", "yep", "yes, I do", "I consent to continue"):
        assert grants_recording_consent(transcript)
    assert not grants_recording_consent("yes, but I do not consent")
    assert declines_recording_consent("no")
    assert declines_recording_consent("I don't consent")
    assert not declines_recording_consent("I think so")


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


def test_conduct_guard_rejects_threats_and_pressure() -> None:
    reply, violated = enforce_conduct("Pay now or else we will hurt you.")
    assert violated
    assert reply == CONDUCT_FALLBACK


def test_redaction_removes_common_transcript_pii() -> None:
    redacted = redact_pii("Call me at +1 202 555 0101 or a@example.test on 1990-01-02")
    assert "+1 202 555 0101" not in redacted
    assert "a@example.test" not in redacted
    assert "1990-01-02" not in redacted


def test_presidio_redacts_indian_phone_and_account_like_id() -> None:
    redacted = redact_pii("Call +91 9876543210 about account: AB12345678")
    assert "+91 9876543210" not in redacted
    assert "AB12345678" not in redacted
