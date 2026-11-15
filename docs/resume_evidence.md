# Resume evidence drafts

Use only after reviewing the raw evidence and explaining its limits.

- Built a Python voice-agent prototype with swappable ASR/LLM/TTS providers, a WebSocket audio adapter, WebRTC VAD endpointing, YAML flow/prompt loading, and a state-restricted structured tool-call loop through the CRM executor; verified by **24 passing local tests** with Fake providers and a deterministic tool-call test double ([RESULTS.md](../RESULTS.md), `raw-results/task4-pytest.txt`).
- Measured local `qwen3:0.6b` text-call wall-time medians of **0.868016685 s with thinking** and **0.129427925 s without thinking** on the recorded WSL2 hardware; this was a standalone prompt, not end-to-end voice latency ([RESULTS.md](../RESULTS.md), `raw-results/ollama-thinking-ablation.json`).
- Implemented per-call identity and numeric grounding guards for a mock CRM; regression proof: **1 failing targeted assertion before** and **1 passing after** the account-reference matcher fix ([RESULTS.md](../RESULTS.md), `raw-results/grounding-before.txt`, `raw-results/grounding-after.txt`).
- Created **20 SYNTHETIC** BFSI caller-scenario definitions with explicit pass rules; execution and pass rate remain **NOT EXECUTED** pending CRM/model-connected call runs ([RESULTS.md](../RESULTS.md), `raw-results/scenario-suite.json`).
- Added Presidio pattern redaction for Indian mobile numbers and account-like IDs before transcript persistence, signed webhook retries with idempotency, receiver deduplication, and trace summaries; these are prototype features, not production integration evidence ([RESULTS.md](../RESULTS.md), commit `5ea7ed4`).
- Evaluated local `base.en` CPU `int8` ASR on **10 clean** and **10 noisy SYNTHETIC** Piper utterances; measured WER was **0.000000** for both synthetic subsets and is not real-user evidence ([RESULTS.md](../RESULTS.md), `raw-results/synthetic-wer.txt`).
- End-to-end speech latency: **[X]**; replace only after a 30+ turn real-provider run is recorded in `RESULTS.md`.
- ASR WER on consented real recordings: **[X]**; real-recording WER is **NOT EXECUTED** until the author supplies and annotates a corpus.

## Claims not to make yet

- Live Twilio compatibility or a live telephony deployment.
- Real-user or client pilot results.
- Real-recording WER, synthetic-speech WER, or a scenario pass rate.
- End-to-end latency, production CRM integration, regulatory certification, or verified RBI calling-hours compliance.
