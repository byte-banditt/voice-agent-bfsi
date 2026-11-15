# Prompt changelog

| Version | Change | Metric delta |
|---|---|---|
| `emi-1`, `kyc-1` | Initial conservative prompts; require identity verification, prohibit pressure and third-party disclosure, permit human escalation | **NOT EXECUTED** as an end-to-end prompt comparison; no metric delta measured |

| `emi-4` | Explicit handling for caller requests, schema clarification, CRM errors, callback/status selection, abusive callers, partial payment, and unsupported values | qwen3:1.7b, 20 SYNTHETIC scenarios × 3: 54/60 overall; 18/20 scenarios passed 3/3. `malformed_tool_arguments` and `grounding_violation` remained 0/3 and are OPEN. Fake suite: 60/60. Raw traces: `raw-results/scenarios-ollama-1_7b-3x.json`, `raw-results/scenarios-fake-3x.json`; run commit `aaf971bc758287b5bd4323799625ea821c3c1a1a`. No further prompt fix attempted. |
| `emi-4` code-boundary follow-up | No prompt text changed. Server now grounds identity/callback arguments, gates status and write intents, requires backend evidence for action-completion claims, and limits repeat writes. | With `emi-4` unchanged: Fake providers 60/60; local Ollama `qwen3:1.7b` Q4_K_M 60/60 over 20 SYNTHETIC scenarios × 3, tool-call accuracy 0.875, LLM call latency median 0.297 s / p95 1.963 s; `raw-results/scenarios-fake-post-fix.json`, `raw-results/scenarios-ollama-1_7b-post-fix.json`. This measures the current code+prompt combination, not prompt-only improvement. |
