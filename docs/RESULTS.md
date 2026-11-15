# Current reproducible results

## Repository baseline

- Initial branch: `main`; HEAD: `21fa9fd75627ed47e45a9898c90cc1fb3e546e9d`.
- Initial working tree already had uncommitted edits in `app/conversation.py`, `app/main.py`, `app/static/voice.html`, `app/tools.py`, `tests/test_tools.py`, and `tests/test_websocket.py`. They were preserved and incorporated as pre-existing user work; no branch was created.
- Baseline command: `python -m pytest -ra` → **39 passed, 0 failed**, 2 dependency deprecation warnings.

## Current verification

- Baseline command: `python -m pytest -ra` → **39 passed, 0 failed**, 2 dependency deprecation warnings.
- Final command: `python -m pytest -ra` → **60 passed, 0 failed**, 2 dependency deprecation warnings.
- Fake synthetic scenario run: `python tools/evaluate_scenarios.py --mode fake --repeats 3 --output raw-results/scenarios-fake-post-fix.json` → **60/60 passed**, 20 scenarios × 3 repeats, Fake providers, MOCK CRM, tool-call accuracy 0.70. No latency value applies to Fake providers.
- Local stochastic model run: `python tools/evaluate_scenarios.py --mode ollama --model qwen3:1.7b --repeats 3 --output raw-results/scenarios-ollama-1_7b-post-fix.json` → **60/60 passed**, 20 scenarios × 3 repeats, local Ollama `qwen3:1.7b` GGUF Q4_K_M, current prompt `emi-4`, MOCK CRM; model-selected tool-call accuracy **0.875**; LLM call median **0.297 s**, p95 **1.963 s**. Safety-required server-side lookups are excluded from model tool-selection accuracy. Agent/platform immutable version: **N/A**.
- Sarvam platform evidence is recorded separately in [`SARVAM_PLATFORM_EVIDENCE.md`](SARVAM_PLATFORM_EVIDENCE.md). MCP list calls now authenticate successfully. Test-only agent `Example-Fin-1e33e491-23c6`, immutable version 2, passed its 9-case native suite 18/18 across two executions per case (`01M7GERSSSB8AMAGJDS0TGJXEP`). This is synthetic text evaluation only. No CRM, telephony connection, verified phone number, deployment, call analytics, or real call was available/executed.
- Manual browser microphone test: **NOT EXECUTED**. Protocol/route tests are not hardware evidence.
- `ruff check app tools tests --output-format concise` was explored but is not a CI gate; current repository reports **40 lint findings**. No Ruff configuration existed in the baseline. No static type checker is configured in the repository.

All local scenario data are synthetic and all CRM data are mock fixtures. No real calls, customer outcomes, platform deployments, or client approvals are included.
