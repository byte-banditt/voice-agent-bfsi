# FDSE JD coverage map

This is a project evidence map, not evidence of client work. The repository is a local prototype with fictional CRM fixtures.

| FDSE responsibility | Evidence | Classification / gap |
|---|---|---|
| Voice AI orchestration, ASR/LLM/TTS, tool calls | `app/providers.py`, `app/conversation.py`, `app/main.py`, `app/static/voice.html`; Sarvam agent `Example-Fin-1e33e491-23c6` v2 | [CODE-VERIFIED] Local provider adapters and simulated WebSocket. [PLATFORM-VERIFIED] Test-only Hindi/English Sarvam agent version committed; no telephony deployment. |
| Secure BFSI workflow and API integration | `app/tools.py`, `app/crm.py`, `tests/test_conversation.py`, `tests/test_crm.py` | [CODE-VERIFIED] Synthetic identity, CRM gate, DOB normalization, state-gated operations; MOCK CRM only. |
| Tool grounding and model failure handling | `app/conversation.py`, `app/guardrails.py`, `raw-results/scenarios-fake-post-fix.json`, `raw-results/scenarios-ollama-1_7b-post-fix.json` | [SYNTHETIC-EVALUATION] Repeat counts and failures in artifacts; no claim of universal model behavior. |
| Client discovery and integration design | `docs/CLIENT_REQUIREMENTS.md`, `docs/INTEGRATION_CONTRACT.md`, `docs/AGENT_DESIGN.md` | [CODE-VERIFIED] Templates only; no client discovery or approval. |
| Observability and incident debugging | `app/observability.py`, `app/metrics.py`, `docs/OPERATIONS_RUNBOOK.md` | [CODE-VERIFIED] Redacted local traces/metrics/runbook; no production monitoring or Sarvam call traces. |
| Evaluation and quality | `docs/TEST_PLAN.md`, `docs/RESULTS.md`, `RESULTS.md` | [SYNTHETIC-EVALUATION] Fake and local Ollama runs only; manual audio and real callers absent. |
| Sarvam Voice Agents platform | `docs/SARVAM_PLATFORM_EVIDENCE.md` | [PLATFORM-VERIFIED] MCP authenticated, agent/version and native suite executed. [NOT-IMPLEMENTED] CRM endpoint/credentials, telephony connection/number, deployment, call analytics and real calls unavailable. |
| Browser/device operations | `tests/test_voice_client.py`, `tests/test_websocket.py` | [CODE-VERIFIED] Route/protocol tests only. [MANUAL-TEST] Physical microphone and speaker behavior not tested. |
| Client production delivery | `docs/GO_LIVE_CHECKLIST.md` | [NOT-IMPLEMENTED] No live CRM, phone number, customer deployment, client acceptance, or compliance review. |

Never describe MOCK CRM as production CRM, simulator media as live telephony, or synthetic scenario/audio output as customer results.
