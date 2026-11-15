# Job-description evidence map

| Requirement | Evidence | Status |
|---|---|---|
| LLM + voice harness: ASR, LLM, TTS, prompts, tool calls | `app/providers.py`, `app/main.py`, `prompts/`, `app/tools.py` | Interfaces and local Ollama provider exist; complete integrated voice/tool loop is a gap |
| Strong Python + REST APIs | `app/main.py`, `app/crm.py`, `app/webhook.py`, `tests/` | Local FastAPI APIs and deterministic tests |
| Cross-stack debugging | `docs/FAILURE_MODES.md` | One observed unit-level grounding regression; no production incident claimed |
| Client integrations: CRM, telephony, internal APIs | `app/crm.py`, `app/tools.py`, `app/main.py` | Mock CRM and simulator-only WebSocket; live client integration is a gap |
| Requirements scoping and flow/prompt design | `flows/`, `prompts/`, `docs/CLIENT_ONBOARDING.md` | Templates and initial flows; not client work |
| Monitoring/evaluating call quality | `app/metrics.py`, `app/observability.py`, `tools/benchmark_ollama.py`, `RESULTS.md` | Basic metrics and standalone LLM ablation; full trace dashboard and call evaluation are gaps |
| BFSI care with regulated workflows/customer data | `app/guardrails.py`, `app/tools.py`, `app/crm.py` | Mock identity gate and grounding guard; compliance review and RBI hours verification are gaps |
| Feed learnings back | `docs/PROMPT_CHANGELOG.md`, `docs/PILOT_PROTOCOL.md` | Templates only; pilot **NOT EXECUTED** |
