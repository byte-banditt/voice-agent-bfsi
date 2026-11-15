# Observed failure modes

No runtime voice-agent failure has been observed; real voice providers have not run. The table below records only a deterministic test defect observed during implementation, not a production failure.

| Symptom | Evidence | Root cause | Fix | Before / after |
|---|---|---|---|---|
| `loan-demo-1` in a spoken account reference was rejected by the grounding guard despite matching tool evidence | `raw-results/grounding-before.txt`; after output: `raw-results/grounding-after.txt` | The token matcher handled numeric account references but omitted hyphenated `loan-*` identifiers | Added a matcher for `account-*` and `loan-*` identifiers in commit `2bf5548e23bae1ed4df571cbf5c4525e71a14edd` | Before: 1 targeted test failed; after: 1 targeted test passed. This is a unit-level guardrail measurement, not voice quality. |
| Qwen3 `0.6b` returned no function call for the tested tool-use request | `raw-results/ollama-tool-calling.json`; after output: `raw-results/ollama-tool-calling-1_7b.json` | The `0.6b` model did not select the provided function; the cause beyond model/prompt size was not isolated | Selected Qwen3 `1.7b`, which emitted `get_loan_status` with `loan_id`; commit `0bd517c84f524358196815650a345571362e455c` | Before: 0 tool calls; after: 1 tool call for the same synthetic request. Local Ollama on RTX 4060 Laptop GPU, 8 GiB VRAM. This single prompt is not an accuracy rate. |
| faster-whisper file-path transcription failed with `TypeError: open() got an unexpected keyword argument 'metadata_errors'` | `raw-results/asr-av19-error.txt`; after output: `raw-results/asr-av18-success.txt` | PyAV 19's `av.open` rejected a keyword used by faster-whisper 1.2.1's file decoder; the unbounded optional dependency selected that incompatible release | Pin `av==18.0.0` in the real-provider extra in commit `c639b104711f8bcf8ac79e35fa6f87c206896def` | Before: file transcription raised `TypeError`; after: same WAV returned “I can arrange a callback with a human agent.” on CPU `int8`. Hardware: WSL2 host in `RESULTS.md`. |

No invented CRM, ASR, LLM, or telephony outage is listed.
