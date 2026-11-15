# Prompt changelog

| Version | Change | Metric delta |
|---|---|---|
| `emi-1`, `kyc-1` | Initial conservative prompts; require identity verification, prohibit pressure and third-party disclosure, permit human escalation | **NOT EXECUTED** as an end-to-end prompt comparison; no metric delta measured |

| `emi-4` | Explicit handling for caller requests, schema clarification, CRM errors, callback/status selection, abusive callers, partial payment, and unsupported values | qwen3:1.7b, 20 SYNTHETIC scenarios × 3: 54/60 overall; 18/20 scenarios passed 3/3. `malformed_tool_arguments` and `grounding_violation` remained 0/3 and are OPEN. Fake suite: 60/60. Raw traces: `raw-results/scenarios-ollama-1_7b-3x.json`, `raw-results/scenarios-fake-3x.json`; run commit `aaf971bc758287b5bd4323799625ea821c3c1a1a`. No further prompt fix attempted. |
