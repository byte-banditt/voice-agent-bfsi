# ADR 0001: local voice-agent architecture

Status: accepted for the local portfolio prototype.

## Constraints and observations

Hardware observed in this WSL2 environment: NVIDIA GeForce RTX 4060 with 8 GiB VRAM (`nvidia-smi`); 4.8 GiB RAM (`free -h`); 16 logical CPUs (`nproc`); Python 3.13.12. Docker CLI is absent. Ollama 0.32.15 is installed. Piper's `rhasspy/piper` repository is archived (GitHub API checked 2026-11-15); its use would conflict with the maintenance requirement. Real model evaluation is deferred until dependencies and model artifacts are available and measured.

## Decision

Use a self-written FastAPI orchestration layer and explicit `ASRProvider`, `LLMProvider`, and `TTSProvider` contracts. Keep the deterministic Fake providers as the default local/CI path. Use SQLite for local call state and FastAPI WebSockets for audio transport. Place identity authorization and grounding checks in Python code, outside the prompt. Use a separate CRM HTTP service boundary in the final composition. Keep raw audio disabled by default.

The architecture diagram and audio boundary contract are below. Internal audio is mono 16 kHz signed 16-bit PCM; the telephony edge accepts 8 kHz G.711 mu-law and must resample before provider use. Twilio compatibility is a message-shape goal only; simulator-only checks cannot establish live Twilio interoperability.

## Official documentation checked

- FastAPI WebSockets: <https://fastapi.tiangolo.com/advanced/websockets/> (HTTP 200, checked 2026-11-15).
- Ollama tool calling: <https://docs.ollama.com/capabilities/tool-calling> (HTTP 200, checked 2026-11-15).
- Twilio Media Streams WebSocket messages: <https://www.twilio.com/docs/voice/media-streams/websocket-messages> (HTTP 200, checked 2026-11-15). The documented stream messages include `connected`, `start`, `media`, and `stop`; audio payload is base64 encoded. This project has no live Twilio test.
- Piper maintenance: <https://api.github.com/repos/rhasspy/piper> reports `archived: true`, checked 2026-11-15. Select an actively maintained local TTS after its API and supported hardware are validated; no TTS dependency is assumed in the Fake path.
- RBI calling-hours basis: NOT VERIFIED. The prototype uses 08:00–19:00 local time as a configurable conservative assumption, not legal guidance.

## Diagram

```mermaid
flowchart LR
  Sim[WAV / Media Streams simulator] --> WS[FastAPI WebSocket adapter]
  WS --> Orch[Python call orchestrator]
  Orch --> VAD[VAD] --> ASR[ASRProvider]
  Orch --> LLM[LLMProvider + state tools]
  Orch --> TTS[TTSProvider]
  LLM --> Guard[Identity + grounding + conduct guards]
  Guard --> CRM[Mock CRM REST API]
  Orch --> Store[(SQLite call store)]
  Orch --> Metrics[Prometheus metrics]
  CRM --> Webhook[Signed completion webhook]
  Webhook --> Store
```
