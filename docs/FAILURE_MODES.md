# Observed failure modes

All runs below used SYNTHETIC speech/scenarios and a MOCK CRM. They are local prototype findings, not production incidents.

| Symptom | Evidence | Root cause | Fix | Before / after |
|---|---|---|---|---|
| `loan-demo-1` in a spoken account reference was rejected by the grounding guard despite matching tool evidence | `raw-results/grounding-before.txt`; after output: `raw-results/grounding-after.txt` | The token matcher handled numeric account references but omitted hyphenated `loan-*` identifiers | Added a matcher for `account-*` and `loan-*` identifiers in commit `2bf5548e23bae1ed4df571cbf5c4525e71a14edd` | Before: 1 targeted test failed; after: 1 targeted test passed. This is a unit-level guardrail measurement, not voice quality. |
| Qwen3 `0.6b` returned no function call for the tested tool-use request | `raw-results/ollama-tool-calling.json`; after output: `raw-results/ollama-tool-calling-1_7b.json` | The `0.6b` model did not select the provided function; the cause beyond model/prompt size was not isolated | Selected Qwen3 `1.7b`, which emitted `get_loan_status` with `loan_id`; commit `0bd517c84f524358196815650a345571362e455c` | Before: 0 tool calls; after: 1 tool call for the same synthetic request. Local Ollama on RTX 4060 Laptop GPU, 8 GiB VRAM. This single prompt is not an accuracy rate. |
| faster-whisper file-path transcription failed with `TypeError: open() got an unexpected keyword argument 'metadata_errors'` | `raw-results/asr-av19-error.txt`; after output: `raw-results/asr-av18-success.txt` | PyAV 19's `av.open` rejected a keyword used by faster-whisper 1.2.1's file decoder; the unbounded optional dependency selected that incompatible release | Pin `av==18.0.0` in the real-provider extra in commit `c639b104711f8bcf8ac79e35fa6f87c206896def` | Before: file transcription raised `TypeError`; after: same WAV returned “I can arrange a callback with a human agent.” on CPU `int8`. Hardware: WSL2 host in `RESULTS.md`. |

No invented CRM, ASR, LLM, or telephony outage is listed.


## SYNTHETIC scenario run (qwen3:1.7b, 3 repeats)

| Scenario | Before | Root cause / disposition | After | Trace |
|---|---:|---|---:|---|
| `malformed_tool_arguments` | 0/3 pass | **OPEN**. The model guessed plausible DOB/phone values and issued a schema-valid `verify_identity` call despite the malformed-argument instruction. No pass rule changed; the versioned prompt already requests clarification, but measured behavior still fails. | 0/3 pass | `raw-results/scenarios-ollama-1_7b-3x.json` |
| `grounding_violation` | 0/3 pass | **OPEN**. The model refused to invent a value, but the existing deterministic scenario requires the grounding fallback/event. The disagreement is not resolved by changing the rule. | 0/3 pass | `raw-results/scenarios-ollama-1_7b-3x.json` |

Fake providers passed both cases 3/3. These are scenario outcomes against a MOCK CRM, not real customer calls. Full per-scenario table and run provenance are in `RESULTS.md`.

## Full-provider simulator findings

| Symptom | Evidence | Root cause | Fix / disposition | Before / after |
|---|---|---|---|---|
| Natural-language DOB produced a CRM verification error | `raw-results/latency-real-ws-30-before-input-fix.json` | Faster-Whisper returned `January 2, 1990`, while the mock CRM validates DOB as `YYYY-MM-DD` | Adjusted only the **SYNTHETIC** utterance to enunciate `1990 dash 01 dash 02`; no pass rule or production prompt was changed | Before: identity verification failed in 30/30. After: identity verified in 30/30; status lookup succeeded in 27/30. Full run: `raw-results/latency-real-ws-30.json` |
| Loan-status lookup got 404 in an initial audio probe | `raw-results/latency-real-ws-valid-probe.json` | ASR/model trace passed `demo-1` instead of the fixture's `loan-demo-1` | Adjusted the synthetic spoken identifier to “loan dash demo dash one” | Before: 404. After: successful fixture result in `raw-results/latency-real-ws-status-probe.json`; 27/30 status lookups in the full run |
| Model omitted the status tool after successful identity verification | Turns 3, 4, and 14 in `raw-results/latency-real-ws-30.json` | Model ended the tool loop without `get_loan_status`; turn 3 also logged `grounding_violation` | **OPEN**; no further prompt iteration within the sprint fix budget | 3/30 turns lacked the status lookup; identity verification still succeeded |
| Demo did not start CRM on first attempt | First `make demo` attempt; final reproducible artifact: `docs/demo-output.txt` | Startup probe sent no API key and therefore saw 401 instead of the expected authenticated CRM response | Added the synthetic API key to the local readiness probe and reran | Before: demo aborted at CRM readiness. After: demo **PASS**, including identity, status, and callback tools |
| Grounding guard fired in the passing demo | `docs/demo-output.txt` | **OPEN**; the trace records the event, but generated spoken text is not retained in the trace, so the specific unsupported claim cannot be isolated from this artifact | No rule or guard was weakened | Event observed once in the one-call demo; tool calls and CRM results succeeded |
