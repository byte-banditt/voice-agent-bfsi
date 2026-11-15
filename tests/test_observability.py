from app.observability import CallStore


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
