from app.observability import CallStore


def test_call_store_redacts_identity_tool_arguments(tmp_path) -> None:
    store = CallStore(tmp_path / "calls.sqlite")
    store.save_trace({"call_id": "synthetic", "tool_calls": [{"name": "verify_identity",
        "arguments": {"dob": "1990-01-02", "phone_last4": "0134"}, "result": {"verified": True}}]})
    call = store.list_calls()[0]
    assert call["tool_calls"][0]["arguments"] == {"redacted": True, "field_names": ["dob", "phone_last4"]}
    assert call["tool_calls"][0]["result"] == {"verified": True}


def test_call_store_removes_account_tool_payloads(tmp_path) -> None:
    store = CallStore(tmp_path / "calls.sqlite")
    store.save_trace({"call_id": "synthetic", "tool_calls": [{"name": "get_loan_status",
        "arguments": {"loan_id": "loan-demo-1"},
        "result": {"id": "loan-demo-1", "status": "due", "amount": "1200", "due_date": "2030-01-15"}}]})
    call = store.list_calls()[0]
    assert call["tool_calls"][0]["result"] == {"redacted": True, "success": True}
    assert "1200" not in str(call)
    assert "loan-demo-1" not in str(call)


def test_summary_reports_per_tool_latency_percentiles(tmp_path) -> None:
    store = CallStore(tmp_path / "calls.sqlite")
    store.save_trace({"call_id": "synthetic", "tool_calls": [{"name": "get_loan_status",
        "arguments": {}, "result": {"status": "due"}, "duration_seconds": 0.125}]})
    summary = store.summary()
    assert summary["tool_latency_percentiles_seconds"]["get_loan_status"] == {"p50": 0.125, "p95": 0.125}


def test_call_store_redacts_transcript_and_summarizes_stages(tmp_path) -> None:
    store = CallStore(tmp_path / "calls.sqlite")
    call_id = store.save_trace({"transcript": "Call +1 202 555 0101", "prompt_version": "emi-1",
                               "stage_seconds": {"asr": 0.1, "llm": 0.2}})
    call = store.list_calls()[0]
    assert call["call_id"] == call_id
    assert "+1 202 555 0101" not in call["transcript"]
    assert store.summary()["stage_percentiles_seconds"]["asr"] == {"p50": 0.1, "p95": 0.1}


def test_feedback_validates_rating_and_redacts_free_text(tmp_path) -> None:
    store = CallStore(tmp_path / "calls.sqlite")
    try:
        store.add_feedback("call-1", True, False, 0, "text")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid feedback rating accepted")

    store.add_feedback("call-1", True, False, 5, "Call +1 202 555 0101")
    with store.connect() as db:
        row = db.execute("SELECT free_text FROM feedback").fetchone()
    assert "+1 202 555 0101" not in row[0]


def test_summary_reports_tools_guardrails_and_prompt_percentiles(tmp_path) -> None:
    store = CallStore(tmp_path / "metrics.sqlite")
    store.save_trace({"prompt_version": "emi-1", "stage_seconds": {"tts": 0.2},
                      "tool_calls": [{"result": {"verified": True}}, {"result": {"error": "denied"}}],
                      "guardrail_events": ["grounding_violation"]})
    summary = store.summary()
    assert summary["tool_success_rate"] == 0.5
    assert summary["guardrail_events"] == {"grounding_violation": 1}
    assert summary["prompt_versions"]["emi-1"]["stage_percentiles_seconds"]["tts"]["p95"] == 0.2
