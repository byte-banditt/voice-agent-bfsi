# Resume evidence drafts

Use only after reviewing the cited raw evidence and its limits.

- Built a Python voice-agent prototype with configurable ASR/LLM/TTS providers, an interactive browser microphone client, WebRTC VAD, versioned YAML flows, structured tool calls, and transcript redaction; the local suite recorded **36 passed** with Fake providers (`RESULTS.md`, `raw-results/interactive-voice-pytest.txt`). The browser route is tested; a physical browser-microphone session is not yet measured.
- Evaluated **20 SYNTHETIC** call scenarios × 3 repeats: qwen3:1.7b Q4_K_M passed **54/60 (90%)** with **1.00** tool-call accuracy; Fake providers passed **60/60**. Two model scenarios remain OPEN (`RESULTS.md`, `raw-results/scenarios-ollama-1_7b-3x.json`).
- Measured **30 SYNTHETIC** audio turns through real local VAD, Faster-Whisper `base.en` CPU `int8`, Ollama qwen3:1.7b, Piper, and a MOCK CRM; user-audio sent → first TTS media p50/p95 were **14.383/18.705 s**, with loan status lookup in **27/30** turns (`RESULTS.md`, `raw-results/latency-real-ws-30.json`).
- Ran a **SYNTHETIC** real-provider demo that passed recording consent, identity verification, loan-status lookup, and callback scheduling through the local MOCK CRM; redacted output is in `docs/demo-output.txt`. No real customer data or telephony was involved.
- Measured synthetic Piper speech WER of **0.000000** on 10 clean and 10 noisy utterances using Faster-Whisper `base.en` CPU `int8`; this does not establish real-recording WER (`RESULTS.md`, `raw-results/synthetic-wer.txt`).

Unmeasured: real-recording WER **[X]**; full-stack ablation results **[X]**; qwen3:4b completed comparison **[X]**.

## Claims not to make yet

- Live telephony or Twilio compatibility.
- Real-user/client pilot results or production CRM integration.
- Real-recording WER, regulatory certification, or verified RBI calling-hours compliance.
- Universal quality or model-size superiority; qwen3:4b comparison is incomplete and two qwen3:1.7b scenarios remain OPEN.
