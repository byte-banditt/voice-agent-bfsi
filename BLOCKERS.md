# Blockers and deferred work

- Docker Engine/Compose is unavailable in the current WSL2 distribution; container build and compose execution are **NOT EXECUTED**.
- The required 30+ turn end-to-end latency run is **NOT EXECUTED**. The WebSocket now has WebRTC VAD, flow-state prompt/tool handling, and tool-layer identity enforcement, but local CRM + Ollama + ASR + TTS have not been exercised together.
- No real recordings were provided; real-recording WER is **NOT EXECUTED**. The repo contains no user recordings.
- `ConversationEngine` loads YAML flow policy and versioned prompts, validates tool arguments, restricts tools per state, loops structured model tool calls through `BFSIToolExecutor`, and records prompt/tool traces. The model/CRM-connected call path and all 20 end-to-end scenarios remain **NOT EXECUTED**.
- WebRTC VAD endpointing, cancellation of active playback on new media, Presidio pattern recognizers for Indian phone/account-like IDs, signed webhook sender retries, receiver deduplication, and trace dashboard summaries are implemented and covered by local tests.
- Call-start recording consent is enforced; declining stores no transcript. Caller stop requests get a polite exit, human requests escalate, and start events outside configured hours get a polite exit. Numeric/date grounding replaces unsupported claims. Conduct filtering is phrase-based and does not establish complete policy coverage.
- The enforced default hours are 08:00–19:00 `Asia/Kolkata`, configurable with `CALLING_HOURS_TIMEZONE`, `CALLING_HOURS_START`, and `CALLING_HOURS_END`. This is **ASSUMPTION**: no RBI recovery-hours source URL was verified, so compliance with RBI guidance is **NOT VERIFIED**.
- Qwen3 0.6b/1.7b/4b/8b comparative scenario and tool-call accuracy, the 30+ real-provider latency run, and requested ablations are **NOT EXECUTED**. Existing one-prompt Qwen probes are not accuracy measurements.
- Real-recording WER and pilot tooling remain **NOT EXECUTED**.
- Docker Compose execution remains **NOT EXECUTED**; the available WSL2 environment previously lacked Docker Engine/Compose. The last verified remote CI run is recorded in RESULTS.md.
