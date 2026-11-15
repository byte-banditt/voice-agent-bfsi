# Interview notes

Study and adapt these notes before using them in an interview.

## Provider interfaces

`ASRProvider`, `LLMProvider`, and `TTSProvider` isolate runtime dependencies from the call loop. Fakes make control-flow tests deterministic. The tradeoff is that fake success does not establish model quality. Debug by comparing provider input format, output, exception, and stage timing.

## Call state and audio

`CallStateMachine` rejects illegal transitions. `app/audio.py` owns mu-law decoding and PCM resampling. Debug barge-in by tracing task cancellation and state transitions. The current implementation is a skeleton; VAD and continuous streaming are not complete.

## CRM and tool gate

`app/crm.py` exposes mock REST endpoints. `BFSIToolExecutor` owns per-call identity authorization and allowlisting. Debug API failures by checking status, timeout, identity context, and redacted trace. The complete orchestrator does not yet call this executor.

## Guardrails

`app/guardrails.py` keeps identity and grounding decisions in code. Prompts alone cannot enforce either invariant. Regex grounding and PII masking have limits; a production design needs reviewed schemas and tested Presidio recognizers.

## Observability and evaluation

`CallStore` stores redacted transcript traces; Prometheus captures stage histograms. Debug missing metrics by checking instrumentation labels and call lifecycle paths. The standalone Ollama benchmark compares thinking options but does not represent end-to-end speech latency.

## Alternatives considered

An all-in-one voice framework was rejected because the learning goal requires owning the orchestration and cancellation path. Piper's original repository is archived; the maintained OHF fork was chosen. Local model execution avoids paid API requirements but requires model artifacts, hardware fit, and measured operational quality.
