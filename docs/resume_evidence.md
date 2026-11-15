# Resume evidence (review before use)

- [CODE-VERIFIED] Implemented local Python/FastAPI voice-agent prototype with YAML conversation flows, tool-gated identity checks, local ASR/LLM/TTS adapters, a simulator WebSocket, and trace redaction. Evidence: `app/`, `flows/`, `prompts/`, and deterministic tests.
- [SYNTHETIC-EVALUATION] Evaluated 20 synthetic scenarios × 3 repeats with Fake providers and MOCK CRM; current artifact: `raw-results/scenarios-fake-post-fix.json`. Report the exact run summary from the artifact; this does not represent callers or production outcomes.
- [SYNTHETIC-EVALUATION] Evaluated a local Qwen3 model against the same synthetic suite; see `raw-results/scenarios-ollama-1_7b-post-fix.json` for exact numerator, denominator, model and configuration. The test is stochastic and local.
- [CODE-VERIFIED] Added caller-input grounding for identity arguments, strict date normalization, server-required status lookup after verification, duplicate same-call state-change protection, HMAC webhook validation, and sensitive tool payload omission from persisted traces.
- [PLATFORM-VERIFIED] Configured fictional-lender test-only Sarvam Voice Agents agent `Example-Fin-1e33e491-23c6`; immutable version 2; native suite `01M7GEBN68HJ4HMEFC915CD2SY` passed 18/18 synthetic text executions (two per each of nine scenarios). This is not a client deployment or phone test. Evidence: `docs/SARVAM_PLATFORM_EVIDENCE.md`.
- [NOT-IMPLEMENTED] CRM endpoint and credentials, inbound telephony connection/authorized phone number, CRM tool execution, Sarvam analytics from live calls, and real-call outcomes remain unavailable.
- [MANUAL-TEST] Physical browser microphone/speaker session is not executed; hardware behavior remains unverified.
- [NOT-IMPLEMENTED] No client deployment, live CRM, real telephony, regulatory certification, customer acceptance, or real-call outcome is evidenced.

Use only metrics with the matching artifact and run configuration. Do not convert synthetic results into customer or platform claims.
