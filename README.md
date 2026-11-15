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

## Interactive browser voice

Install the real local providers and make sure Ollama has the model and Piper voice available:

```sh
python -m pip install -e '.[real]'
ollama pull qwen3:1.7b
```

In `.env`, set `VOICE_AGENT_REAL_PROVIDERS=true`, `OLLAMA_MODEL=qwen3:1.7b`, `PIPER_VOICE_PATH=/absolute/path/to/en_US-lessac-medium.onnx`, and a local `CRM_API_KEY`. Keep the same CRM key for the CRM and agent; `.env` is read by both `make crm` and `make agent`. Start each service in a separate terminal:

```sh
make crm
```

```sh
make agent
```

Open <http://localhost:8000/voice>, allow microphone access, press **Start call**, listen to the recording-consent line, then speak. Speak again for each turn; speak while the agent is talking to interrupt it. Use headphones to reduce acoustic echo. The browser streams microphone audio to the local `/ws` endpoint; transcripts are redacted before they are stored, and raw audio is not stored.

The local simulator does not enforce calling hours. Use only synthetic/mock customer details. This is not live telephony.

The LLM tool-call loop is non-streaming; measured synthetic input-to-first-audio p50/p95 was 14.383/18.705 seconds on the recorded hardware. `make demo` remains the fixed scripted demonstration.

Install `.[simulator]` to run `python tools/simulate_wav.py path/to/test.wav`; simulator WAVs must be synthetic or consented and remain outside Git.

The `/ws` endpoint accepts simulator JSON events with `start`, `media`, and `stop`. Inbound `media.payload` is base64 G.711 mu-law at 8 kHz; internal provider audio is mono PCM16 at 16 kHz. Outbound media uses the same telephony encoding. Provider-generated output is labeled **MOCK** unless real providers are enabled.

## Measured results

See [RESULTS.md](RESULTS.md) for exact commands, raw artifacts, commit SHAs, and hardware. All call scenarios and voice inputs below are **SYNTHETIC**; CRM data are **MOCK**.

| Measurement | Observed result | Scope |
|---|---|---|
| Local tests | 36 passed, 0 failed, 2 dependency warnings | Fake providers; `raw-results/interactive-voice-pytest.txt` |
| Fake scenario suite | 60/60 pass; tool-call accuracy 0.70 | 20 scenarios × 3 repeats; mock CRM |
| qwen3:1.7b Q4_K_M scenario suite | 54/60 pass (90%); tool-call accuracy 1.00 | 20 scenarios × 3 repeats; 2 OPEN scenarios |
| Real-provider `/ws` latency | 30 turns; user-audio sent → first TTS media p50 14.383 s, p95 18.705 s | WebRTC VAD, Faster-Whisper `base.en` CPU `int8`, Ollama qwen3:1.7b, Piper `en_US-lessac-medium`; 27/30 status lookups succeeded |
| Synthetic Piper → Faster-Whisper WER | Clean 0.000000; noisy 0.000000 | Generated US English only; not real-recording quality |
| Demo call | PASS: consent, identity, loan status, callback scheduled | `make demo`; real local providers and MOCK CRM |

## Not done

qwen3:4b comparison incomplete; qwen3:0.6b/8b comparison; true LLM first-token latency; full-stack ablations; real-recording WER; pilot; Docker Compose build; RBI source verification; live telephony; manual browser-microphone smoke test by the user.

## Limitations

- The simulator exercises the documented `connected`/`start`/`media`/`stop` and `clear` message envelopes only. It is **format-compatible per docs, not tested against live Twilio**.
- The WebSocket flow uses YAML flow state, versioned prompts, WebRTC VAD endpointing, and `BFSIToolExecutor` on structured Ollama tool calls. Thirty SYNTHETIC audio turns ran through real local ASR/LLM/TTS with a MOCK CRM; 27/30 status lookups succeeded. The separate demo completed consent, identity, status lookup, and callback scheduling.
- CRM data are invented fixtures (**MOCK**). Payment URLs and escalation are inert mock responses.
- Real provider wiring exists for faster-whisper, Ollama, and Piper. Ollama text generation and a small synthetic Piper-to-Faster-Whisper corpus were measured; real-recording quality was not.
- Transcript redaction runs before trace storage, using Presidio custom recognizers for Indian mobile numbers and account-like IDs plus local email, phone, and date patterns. This is not a guarantee against all PII. Raw audio is not stored.
- The dashboard summarizes stored call traces, stage percentiles, tool success, guardrail events, and prompt versions; production access control, retention, and deployment hardening are absent.
- Docker Compose version is available, but `docker compose up --build` and health checks were **NOT EXECUTED** in this sprint.
- RBI calling-hours guidance is **ASSUMPTION / NOT VERIFIED**; the local simulator currently has no calling-hours gate.

See [BLOCKERS.md](BLOCKERS.md) and [docs/JD_COVERAGE.md](docs/JD_COVERAGE.md). Do not claim live telephony, live CRM, real-user outcomes, real-recording WER, regulatory certification, or universal call quality from this prototype.
