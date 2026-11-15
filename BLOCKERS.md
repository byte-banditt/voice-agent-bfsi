# Blockers and deferred work

- Docker Engine/Compose is unavailable in the current WSL2 distribution; container build and compose execution are **NOT EXECUTED**.
- The local Piper and `faster-whisper` providers ran on generated synthetic speech. The required 30+ turn end-to-end latency run is **NOT EXECUTED** because CRM tools, VAD, and conversation policy are not wired into the call loop.
- No real recordings were provided; real-recording WER is **NOT EXECUTED**. The repo contains no user recordings.
- A complete conversation loop that invokes `BFSIToolExecutor`, loads YAML flow policy, and applies conduct/consent rules is not wired; the full scenario suite and per-scenario pass rate are **NOT EXECUTED**.
- Presidio recognizer pipeline, webhook sender/retry, CRM-backed dashboard query, and conduct/consent enforcement in the live call loop are not complete.
- RBI recovery-calling-hours source was not verified; the configured-hours policy is only an assumption and is not enforced.
- Docker Compose execution and end-to-end provider/CRM integration remain **NOT EXECUTED**; the remote CI run is recorded in RESULTS.md.
