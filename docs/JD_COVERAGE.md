# Job-description evidence map

| Requirement | Evidence | Status |
|---|---|---|
| LLM + voice harness: ASR, LLM, TTS, prompts, tool calls | `app/providers.py`, `app/main.py`, `app/conversation.py`, `prompts/`, `app/tools.py` | Simulator wires WebRTC VAD, ASR, flow/prompt state, structured Ollama tool calls, CRM executor, and TTS; end-to-end local-provider operation remains **NOT EXECUTED** |
| Strong Python + REST APIs | `app/main.py`, `app/crm.py`, `app/webhook.py`, `tests/` | Local FastAPI APIs and deterministic tests |
| Cross-stack debugging | `docs/FAILURE_MODES.md` | One observed unit-level grounding regression; no production incident claimed |
| Client integrations: CRM, telephony, internal APIs | `app/crm.py`, `app/tools.py`, `app/main.py` | Mock CRM and simulator-only WebSocket; live client integration is a gap |
| Requirements scoping and flow/prompt design | `flows/`, `prompts/`, `docs/CLIENT_ONBOARDING.md` | Templates and initial flows; not client work |
| Monitoring/evaluating call quality | `app/metrics.py`, `app/observability.py`, `tools/benchmark_ollama.py`, `RESULTS.md` | Trace dashboard reports stage percentiles, tool success, guardrail events, and prompt versions; scenario and 30+ turn evaluation remain **NOT EXECUTED** |
| BFSI care with regulated workflows/customer data | `app/guardrails.py`, `app/tools.py`, `app/crm.py` | Tool-layer identity gate, consent-before-transcript storage, numeric/date grounding, polite exit, and configurable assumed calling-hours gate; conduct filter is phrase-based and RBI hours are **ASSUMPTION / NOT VERIFIED** |
| Feed learnings back | `docs/PROMPT_CHANGELOG.md`, `docs/PILOT_PROTOCOL.md` | Templates only; pilot **NOT EXECUTED** |
