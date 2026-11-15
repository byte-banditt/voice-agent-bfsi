# Local BFSI voice-agent prototype

[CODE-VERIFIED] This repository contains a local EMI reminder/KYC prototype using FastAPI, YAML flows, provider adapters, a simulated WebSocket media stream, and a separate MOCK CRM seeded with fictional records. It is not a production CRM or live telephony integration.

[CODE-VERIFIED] Verification tools enforce identity state at both conversation and CRM boundaries; DOB normalization, caller-input grounding, bounded verification attempts, duplicate state-changing call protection, and persisted-trace redaction have local regression tests.

[CODE-VERIFIED] Optional local providers are Faster-Whisper ASR, Ollama LLM and Piper TTS. This pipeline is independent of Sarvam Voice Agents.

[PLATFORM-VERIFIED] Sarvam Voice Agents MCP authentication is available in the current session. A dedicated fictional-lender test agent was created and immutable version 2 was committed; its native test suite completed 18/18 synthetic scenario executions. See [platform evidence and blockers](docs/SARVAM_PLATFORM_EVIDENCE.md). This test-only agent has no CRM integration and is not deployed to telephony.

[NOT-IMPLEMENTED] Authorized CRM endpoint/credentials and telephony connection/test number are absent from the workspace. CRM tool execution, backend timeout/retry validation against Sarvam, analytics on real calls, and inbound deployment remain incomplete. No call was placed.

## Quickstart

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
cp .env.example .env
uvicorn app.main:app --reload --env-file .env
```

[CODE-VERIFIED] `/health`, `/metrics`, `/dashboard`, `/voice`, and `/docs` are local prototype routes. Start the synthetic CRM separately with `make crm`. Keep both services on a trusted local interface; never use real customer details.

## Optional local ASR/LLM/TTS providers

[CODE-VERIFIED] The local prototype can run Faster-Whisper, Ollama, and Piper separately from Sarvam:

```sh
python -m pip install -e '.[real]'
ollama pull qwen3:1.7b
```

Set `VOICE_AGENT_REAL_PROVIDERS=true`, `OLLAMA_MODEL=qwen3:1.7b`, `PIPER_VOICE_PATH` to a local Piper ONNX voice, and a synthetic-only `CRM_API_KEY` in `.env`. Run `make crm` and `make agent` in separate terminals. This WebSocket remains a local simulator; any microphone run is a manual device test and not live telephony.

## Local tests and evaluation

```sh
python -m pytest -ra
python tools/evaluate_scenarios.py --mode fake --repeats 3 --output raw-results/scenarios-fake-post-fix.json
python tools/evaluate_scenarios.py --mode ollama --model qwen3:1.7b --repeats 3 --output raw-results/scenarios-ollama-1_7b-post-fix.json
```

[SYNTHETIC-EVALUATION] Scenario outputs use synthetic callers and MOCK CRM data. See [current results](docs/RESULTS.md) and [full historical measurements](RESULTS.md) for run counts, versions, latency definitions, failures and limits.

[MANUAL-TEST] A real browser microphone/speaker interaction has not been recorded; WebSocket protocol tests are not hardware tests.

## Delivery templates

- [Client requirements](docs/CLIENT_REQUIREMENTS.md)
- [Integration contract](docs/INTEGRATION_CONTRACT.md)
- [Agent design](docs/AGENT_DESIGN.md)
- [Test plan](docs/TEST_PLAN.md)
- [Operations runbook](docs/OPERATIONS_RUNBOOK.md)
- [Go-live checklist](docs/GO_LIVE_CHECKLIST.md)
- [JD coverage](docs/JD_COVERAGE.md)

[NOT-IMPLEMENTED] No client discovery, client acceptance, regulatory approval, live calling, production integration, or customer deployment is evidenced by this repository.
