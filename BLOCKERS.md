# Blockers and deferred work

- Docker Engine/Compose is unavailable in the current WSL2 distribution; container build and compose execution are **NOT EXECUTED**.
- The required 30+ turn end-to-end latency run is **NOT EXECUTED**. The WebSocket now has WebRTC VAD, flow-state prompt/tool handling, and tool-layer identity enforcement, but local CRM + Ollama + ASR + TTS have not been exercised together.
- No real recordings were provided; real-recording WER is **NOT EXECUTED**. The repo contains no user recordings.
- `ConversationEngine` now loads YAML flow policy and versioned prompts, restricts tools per state, loops structured model tool calls through `BFSIToolExecutor`, and records prompt/tool traces. The model/CRM-connected call path and all 20 end-to-end scenarios remain **NOT EXECUTED**.
- WebRTC VAD endpointing, cancellation of active playback on new media, Presidio pattern recognizers for Indian phone/account-like IDs, signed webhook sender retries, receiver deduplication, and trace dashboard summaries are implemented and covered by local tests.
- Recording consent, conduct policy, safe exit, verified calling-hours enforcement, and call-start escalation behavior are not fully enforced in the WebSocket loop.
- RBI recovery-calling-hours source was not verified; no calling-hours policy is currently enforced. If enabled before verification, 08:00–19:00 Asia/Kolkata must remain labelled **ASSUMPTION** and configurable.
- Qwen3 0.6b/1.7b/4b/8b comparative scenario and tool-call accuracy, the 30+ real-provider latency run, and requested ablations are **NOT EXECUTED**. Existing one-prompt Qwen probes are not accuracy measurements.
- Real-recording WER and pilot tooling remain **NOT EXECUTED**.
- Docker Compose execution remains **NOT EXECUTED**; the available WSL2 environment previously lacked Docker Engine/Compose. The last verified remote CI run is recorded in RESULTS.md.
