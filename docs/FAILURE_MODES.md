# Observed failure modes

No runtime voice-agent failure has been observed; real voice providers have not run. The table below records only a deterministic test defect observed during implementation, not a production failure.

| Symptom | Evidence | Root cause | Fix | Before / after |
|---|---|---|---|---|
| `loan-demo-1` in a spoken account reference was rejected by the grounding guard despite matching tool evidence | `raw-results/grounding-before.txt`; after output: `raw-results/grounding-after.txt` | The token matcher handled numeric account references but omitted hyphenated `loan-*` identifiers | Added a matcher for `account-*` and `loan-*` identifiers in commit `2bf5548e23bae1ed4df571cbf5c4525e71a14edd` | Before: 1 targeted test failed; after: 1 targeted test passed. This is a unit-level guardrail measurement, not voice quality. |

No invented CRM, ASR, LLM, or telephony outage is listed.
