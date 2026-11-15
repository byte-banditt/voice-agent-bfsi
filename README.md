# Local BFSI voice-agent prototype

[![CI](https://github.com/byte-banditt/voice-agent-bfsi/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/byte-banditt/voice-agent-bfsi/actions/workflows/ci.yml)

Local portfolio prototype for EMI reminders and KYC identity checks. Provider integrations are swappable; **MOCK** providers remain the default. No real customer information or recordings belong in this repository.

## Quickstart

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
cp .env.example .env
uvicorn app.main:app --reload --env-file .env
```

Open `/docs` for the FastAPI schema, `/dashboard` for the minimal dashboard, `/health` for health, and `/metrics` for Prometheus metrics. The mock CRM is a separate app; start it with `make crm`. Never expose the demo services to an untrusted network.

Install `.[simulator]` to run `python tools/simulate_wav.py path/to/test.wav`; simulator WAVs must be synthetic or consented and remain outside Git.

The `/ws` endpoint accepts simulator JSON events with `start`, `media`, and `stop`. Inbound `media.payload` is base64 G.711 mu-law at 8 kHz; internal provider audio is mono PCM16 at 16 kHz. Outbound media uses the same telephony encoding. Provider-generated output is labeled **MOCK** unless real providers are enabled.

## Measured results

See [RESULTS.md](RESULTS.md) for command, raw output, commit, and hardware provenance. The local Qwen3 thinking ablation is a standalone text-model measurement; it is not end-to-end voice latency. Synthetic Piper/Faster-Whisper WER is reported separately; real-recording WER, end-to-end latency, and scripted call-flow pass rate are **NOT EXECUTED**.

| Measurement | Observed result | Scope |
|---|---|---|
| Local test suite | 24 passed, 0 failed, 0 skipped | Fake providers and deterministic tool-call test double; latest output in `raw-results/task4-pytest.txt` |
| Qwen3 thinking ON/OFF median wall time | 0.868016685 s / 0.129427925 s | Standalone text prompt |
| Synthetic Piper → Faster-Whisper WER | Clean 0.000000; noisy 0.000000 | Generated US English only |
| Qwen3 native tool-call probe | qwen3:0.6b: 0 calls; qwen3:1.7b: 1 call | One synthetic prompt per model |

Each value links to its exact command, raw output, commit, and hardware record in [RESULTS.md](RESULTS.md).

## Limitations

- The simulator exercises the documented `connected`/`start`/`media`/`stop` and `clear` message envelopes only. It is **format-compatible per docs, not tested against live Twilio**.
- The WebSocket flow now uses YAML flow state, versioned prompts, WebRTC VAD endpointing, and `BFSIToolExecutor` on structured Ollama tool calls. CI tests use fake providers and a deterministic tool-call test double; CRM-connected scenarios and real-provider end-to-end calls remain **NOT EXECUTED**.
- CRM data are invented fixtures (**MOCK**). Payment URLs and escalation are inert mock responses.
- Real provider wiring exists for faster-whisper, Ollama, and Piper. Ollama text generation and a small synthetic Piper-to-Faster-Whisper corpus were measured; real-recording quality was not.
- Transcript redaction runs before trace storage, using Presidio custom recognizers for Indian mobile numbers and account-like IDs plus local email, phone, and date patterns. This is not a guarantee against all PII. Raw audio is not stored.
- The dashboard summarizes stored call traces, stage percentiles, tool success, guardrail events, and prompt versions; production access control, retention, and deployment hardening are absent.
- RBI calling-hours guidance was not verified. 08:00–19:00 local time is an assumption and is not enforced by the call flow.
- Docker Compose was not executed because Docker is unavailable in the current WSL2 distribution.

## What is not done

See [BLOCKERS.md](BLOCKERS.md) and [docs/JD_COVERAGE.md](docs/JD_COVERAGE.md). Do not claim live telephony, a measured end-to-end CRM/provider call, real-user outcomes, real-recording WER, or end-to-end latency from this prototype.
