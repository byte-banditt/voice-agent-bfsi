# Results

All benchmark and test outputs are local and synthetic/mock unless noted. Hardware: NVIDIA GeForce RTX 4060, 8 GiB VRAM; 4.8 GiB RAM; 16 logical CPUs; Python 3.13.12. Full probe output: `raw-results/hardware.txt`; command: `{ nvidia-smi; free -h; nproc; python --version; ollama --version; docker --version; } > raw-results/hardware.txt 2>&1`.

| Result | Exact command | Raw output | Commit | Hardware / interpretation |
|---|---|---|---|---|
| **NOT EXECUTED**; Phase 0 had no test suite | `python -m pytest -ra` | No test suite existed at that commit | `238a3da9d2f85411f9ff0fbfb8c4e9b4da161af1` | Hardware above |
| 7 passed, 0 failed, 0 skipped | `python -m pytest -ra` on Phase 1 source | `raw-results/phase1-pytest.txt` | `c2e3673027da4591cb9f6c04c847e66989ba71d7` | WSL2; fake providers |
| Hardware observed: RTX 4060 8 GiB VRAM, 4.8 GiB RAM, 16 logical CPUs, Python 3.13.12 | `{ nvidia-smi; free -h; nproc; python --version; ollama --version; docker --version; } > raw-results/hardware.txt 2>&1` | `raw-results/hardware.txt` | `3373700565a323be0d33d7a74d60745df03e85b4` | WSL2 host |
| Local `OllamaLLM.stream_reply` smoke produced text | `python tools/smoke_ollama.py --model qwen3:1.7b` | `raw-results/ollama-provider-smoke-1_7b.txt` | `0bd517c84f524358196815650a345571362e455c` | Qwen3 `1.7b`, Q4_K_M per `raw-results/ollama-model-1_7b.json`; output is **SYNTHETIC** model text, not a scripted caller or voice result |
| Qwen3 native tool-call probe: `0.6b` emitted 0 calls; `1.7b` emitted 1 call with valid `loan_id` | `python tools/smoke_ollama_tools.py --model qwen3:0.6b` and `python tools/smoke_ollama_tools.py --model qwen3:1.7b` | `raw-results/ollama-tool-calling.json`; `raw-results/ollama-tool-calling-1_7b.json` | `0bd517c84f524358196815650a345571362e455c` | Ollama local GPU; exact model metadata in `raw-results/ollama-model-1_7b.json`; one synthetic prompt per model, not an accuracy rate |
| `qwen3:1.7b` artifact metadata | `python tools/inspect_ollama.py --model qwen3:1.7b > raw-results/ollama-model-1_7b.json` | `raw-results/ollama-model-1_7b.json` | `0bd517c84f524358196815650a345571362e455c` | Ollama reports Q4_K_M; `ollama ps` placement: `raw-results/ollama-processors.txt`; GPU use observed locally |
| Qwen3 thinking ON median wall time: 0.868016685 seconds; OFF: 0.129427925 seconds | `python tools/benchmark_ollama.py --model qwen3:0.6b --repeats 3` | `raw-results/ollama-thinking-ablation.json` | `3373700565a323be0d33d7a74d60745df03e85b4` | Ollama 0.32.15; `qwen3:0.6b`, Q4_K_M per `raw-results/ollama-model.json`; RTX 4060 Laptop GPU, 8 GiB VRAM. Standalone text prompt, not voice latency. |
| **SYNTHETIC** corpus: 10 clean + 10 noisy files; `noise_scale=250`, `seed=17` | `python tools/make_synthetic_dataset.py --voice /tmp/voice-agent-models/en_US-lessac-medium.onnx --output /tmp/voice-agent-synthetic --noise-scale 250 --seed 17` | `raw-results/synthetic-dataset.txt` | `5fe1d16bcfa0cf9399aca1c6027dce9f7cf81d87` | Piper `en_US-lessac-medium`, mono 16 kHz PCM16; WSL2 host above |
| Synthetic ASR hypotheses generated | `python tools/run_asr_dataset.py --manifest /tmp/voice-agent-synthetic/manifest.csv --output /tmp/voice-agent-synthetic/hypotheses.csv --model base.en --device cpu --compute-type int8` | `raw-results/synthetic-asr.txt` | `5fe1d16bcfa0cf9399aca1c6027dce9f7cf81d87` | Faster-Whisper `base.en`, CPU `int8`; WSL2 host above |
| Synthetic beam-size probe: beam 1 and beam 5 both measured clean/noisy WER 0.000000 | `python tools/run_asr_dataset.py --manifest /tmp/voice-agent-synthetic/manifest.csv --output /tmp/voice-agent-synthetic/hypotheses-beam1.csv --model base.en --device cpu --compute-type int8 --beam-size 1`; `python tools/evaluate_wer.py --manifest /tmp/voice-agent-synthetic/manifest.csv --hypotheses /tmp/voice-agent-synthetic/hypotheses-beam1.csv`; `python tools/run_asr_dataset.py --manifest /tmp/voice-agent-synthetic/manifest.csv --output /tmp/voice-agent-synthetic/hypotheses.csv --model base.en --device cpu --compute-type int8 --beam-size 5`; `python tools/evaluate_wer.py --manifest /tmp/voice-agent-synthetic/manifest.csv --hypotheses /tmp/voice-agent-synthetic/hypotheses.csv` | `raw-results/synthetic-asr-beam1.txt`, `raw-results/synthetic-wer-beam1.txt`, `raw-results/synthetic-asr.txt`, `raw-results/synthetic-wer.txt` | `c639b104711f8bcf8ac79e35fa6f87c206896def` | Same small **SYNTHETIC** Piper set; this does not establish equal real-world accuracy or latency |
| Synthetic WER: clean 0.000000 across 10 utterances; noisy 0.000000 across 10 utterances | `python tools/evaluate_wer.py --manifest /tmp/voice-agent-synthetic/manifest.csv --hypotheses /tmp/voice-agent-synthetic/hypotheses.csv` | `raw-results/synthetic-wer.txt` | `c639b104711f8bcf8ac79e35fa6f87c206896def` | Piper `en_US-lessac-medium` (fixed Piper noise scales 0.0); Faster-Whisper `base.en`, CPU `int8`, beam size 5; both subsets are **SYNTHETIC**, not real recordings. |
| PyAV 19 file-path decode failed; PyAV 18 decoded the same WAV | `python tools/probe_faster_whisper_file.py /tmp/voice-agent-synthetic/utt-05-clean.wav` under each installed version | `raw-results/asr-av19-error.txt`; `raw-results/asr-av18-success.txt` | `c639b104711f8bcf8ac79e35fa6f87c206896def` | faster-whisper `base.en`, CPU `int8`; WSL2 host above |
| Phase 2: 8 passed, 0 failed, 0 skipped | `python -m pytest -ra` | `raw-results/phase2-pytest.txt` | `3373700565a323be0d33d7a74d60745df03e85b4` | WSL2; Fake providers |
| Phase 3: 17 passed, 0 failed, 0 skipped | `python -m pytest -ra` | `raw-results/phase3-pytest.txt` | `2bf5548e23bae1ed4df571cbf5c4525e71a14edd` | WSL2; Fake providers, no GPU model inference in this test run |
| Phase 4: 19 passed, 0 failed, 0 skipped | `python -m pytest -ra` | `raw-results/phase4-pytest.txt` | `e0346027ed6794a58cbe36ef1e11c75071af54df` | WSL2; Fake providers |
| Phase 5: 19 passed, 0 failed, 0 skipped | `python -m pytest -ra` | `raw-results/phase5-pytest.txt` | `5fe1d16bcfa0cf9399aca1c6027dce9f7cf81d87` | WSL2; deterministic Fake providers |
| Phase 6: 19 passed, 0 failed, 0 skipped | `python -m pytest -ra` | `raw-results/phase6-pytest.txt` | `5afea4e83750f1cec704912b0adc0a0dc6e779b0` | WSL2; deterministic Fake providers |
| Phase 7: 19 passed, 0 failed, 0 skipped | `python -m pytest -ra` | `raw-results/phase7-pytest.txt` | `6acb0ff5477ded880be6a1f1148fec07d0042894` | WSL2; deterministic Fake providers |
| Remote GitHub Actions on merged `main`: 19 passed, 0 failed, 0 skipped, 1 pytest warning; conclusion success | `gh run view 43697354918 --repo byte-banditt/voice-agent-bfsi --log` | `raw-results/remote-ci.txt` | `04a4bfbc0f0e7981c2bd72aa7c449e27fd7be7eb` | GitHub-hosted Linux runner: Intel Xeon 6975P-C, 4 CPUs, 15 GiB RAM, Python 3.13.18; fake providers. Warning: Starlette `TestClient`/httpx deprecation; workflow also reports Node.js action deprecations. |
| Latest verified remote `main` CI: success | `gh run view 43697649099 --repo byte-banditt/voice-agent-bfsi --json headSha,conclusion,workflowName,createdAt,url` | `raw-results/latest-main-ci.json` | Remote head `758adb092d87da63824241ef056d7868c643c58e` | Verified 2026-11-15; this run predates the local commits in this worktree and does not validate them. |
| Step 0 remote CI on pushed HEAD: **failure**, 6 failed, 28 passed | `gh run view 43719643851 --repo byte-banditt/voice-agent-bfsi --log-failed` | `raw-results/step0-ci-failure.txt` | `468de6c7fe63ee25372d2b160aef4dba7d668f46` | GitHub Actions Python 3.13.18, Ubuntu runner. Time-dependent calling-hours tests plus missing-Presidio fallback caused failures; details in `BLOCKERS.md`. |
| Qwen3 model selection fix: 19 passed, 0 failed, 0 skipped | `python -m pytest -ra` | `raw-results/model-fix-pytest.txt` | `0bd517c84f524358196815650a345571362e455c` | WSL2; deterministic Fake providers |
| PyAV pin and reproducible-evaluation fix: 19 passed, 0 failed, 0 skipped | `python -m pytest -ra` | `raw-results/asr-fix-pytest.txt` | `c639b104711f8bcf8ac79e35fa6f87c206896def` | WSL2; deterministic Fake providers |
| Flow/tool-loop, WebRTC VAD, Presidio redaction, webhook retry, and trace-summary changes: 24 passed, 0 failed, 0 skipped; 2 Presidio transitive Click deprecation warnings | `python -m pytest -ra` | `raw-results/task4-pytest.txt` | `5ea7ed4` | WSL2; Fake providers and deterministic tool-call test double; no connected CRM or local model run |
| Consent/calling-hours/guardrail enforcement, validated tool schemas, and call-completion webhook wiring: 34 passed, 0 failed, 0 skipped; 2 Presidio transitive Click deprecation warnings | `python -m pytest -ra` | `raw-results/final-local-pytest.txt` | `1743b55` | WSL2; Fake providers and deterministic tool-call test doubles; no connected CRM/model call |
| At historical commit `bd06248`: 20 scripted scenarios catalogued, 0 executed | `python tools/evaluate_scenarios.py > raw-results/scenario-suite.json` | `raw-results/scenario-suite.json`; count summary `raw-results/scenario-summary.txt` | `bd06248` | Historical baseline only; the runner and later measured results are documented below |
| Real-recording WER **NOT EXECUTED**; no author recordings/reference transcripts supplied | `python tools/evaluate_wer.py --manifest <csv> --hypotheses <csv>` | `BLOCKERS.md` | `5fe1d16bcfa0cf9399aca1c6027dce9f7cf81d87` | Real WER remains unmeasured |
| **NOT EXECUTED**; Docker CLI unavailable | `docker compose up --build` | `raw-results/hardware.txt` (`docker --version` failed) | `5afea4e83750f1cec704912b0adc0a0dc6e779b0` | WSL2 |
| Docker Compose build could not start; exit code 1 because `docker` is absent from this WSL2 distro | `docker compose up --build` | `raw-results/docker-compose-probe.txt` | `563aa86` | Shell output recommends enabling Docker Desktop WSL integration; compose was not executed |
| No broken installed-package requirements | `python -m pip check` | `raw-results/pip-check.txt` | `c639b104711f8bcf8ac79e35fa6f87c206896def` | Local environment with all declared extras installed |

The grounding guard regression was reproduced before and after the fix with `python -m pytest tests/test_guardrails.py::test_grounding_accepts_tool_backed_claim -ra`. Before: 1 failed (`raw-results/grounding-before.txt`); after: 1 passed (`raw-results/grounding-after.txt`). This is a unit assertion, not a call-quality metric.

PyPI latest-version command: `python tools/check_package_versions.py > raw-results/official-package-versions.txt`. Installed versions command: `python tools/check_installed_versions.py > raw-results/installed-package-versions.txt`. Ollama model metadata commands: `python tools/inspect_ollama.py --model qwen3:0.6b > raw-results/ollama-model.json` and `python tools/inspect_ollama.py --model qwen3:1.7b > raw-results/ollama-model-1_7b.json`; active placement command: `ollama ps | tee raw-results/ollama-processors.txt`. Exact pins are in `pyproject.toml`; code/evidence commit `c639b104711f8bcf8ac79e35fa6f87c206896def`; WSL2 hardware as above.

At the earlier baseline, full-stack ASR model-size comparison, VAD threshold comparison, grounding-guard ablation, 30+ turn provider latency, and connected scenario execution were **NOT EXECUTED**. Current scenario and latency measurements are documented below; real-recording WER and requested full-stack ablations remain **NOT EXECUTED**.

## Latency summary

| Stage / measure | Result | Evidence |
|---|---|---|
| User stops speaking → first TTS audio byte (historical baseline) | **NOT EXECUTED** at that earlier baseline | `BLOCKERS.md` |
| VAD end → ASR done; LLM first token; first sentence; TTS first byte (historical baseline) | **NOT EXECUTED** at that earlier baseline | `BLOCKERS.md` |
| Standalone Qwen3 text generation, thinking ON/OFF, wall-time median | 0.868016685 s / 0.129427925 s for the measured prompt and model | Exact command and raw samples in the table above and `raw-results/ollama-thinking-ablation.json` |

Exact hardware and tool probe for those historical measurements: `raw-results/hardware.txt`. It alone makes no latency, WER, scenario-rate, or full-call success claim.


## Scenario evaluation (Step 1; SYNTHETIC callers, MOCK CRM)

Command: `python tools/evaluate_scenarios.py --mode fake --repeats 3 --output raw-results/scenarios-fake-3x.json` and `python tools/evaluate_scenarios.py --mode ollama --model qwen3:1.7b --repeats 3 --output raw-results/scenarios-ollama-1_7b-3x.json`. The runner uses all 20 fixed scenarios, 3 repeats each, and unchanged pass rules. Code and raw JSON/CRM traces: commit `aaf971bc758287b5bd4323799625ea821c3c1a1a`. Hardware: WSL2, NVIDIA GeForce RTX 4060, 8188 MiB VRAM; Ollama local GPU, qwen3:1.7b Q4_K_M (`raw-results/ollama-model-1_7b.json`, `raw-results/scenario-hardware.txt`).

| Scenario | Fake providers (MOCK) | qwen3:1.7b (real local LLM) |
|---|---:|---:|
| `happy_path` | 3/3 | 3/3 |
| `wrong_identity_three_attempts` | 3/3 | 3/3 |
| `refuses_verification` | 3/3 | 3/3 |
| `another_person_account` | 3/3 | 3/3 |
| `prompt_injection` | 3/3 | 3/3 |
| `abusive_caller` | 3/3 | 3/3 |
| `barge_in_mid_sentence` | 3/3 | 3/3 |
| `long_silence` | 3/3 | 3/3 |
| `mumbled_noisy_input` | 3/3 | 3/3 |
| `out_of_scope` | 3/3 | 3/3 |
| `crm_server_error` | 3/3 | 3/3 |
| `crm_timeout` | 3/3 | 3/3 |
| `duplicate_webhook` | 3/3 | 3/3 |
| `human_request` | 3/3 | 3/3 |
| `schedule_callback` | 3/3 | 3/3 |
| `partial_payment_promise` | 3/3 | 3/3 |
| `third_party_answers` | 3/3 | 3/3 |
| `malformed_tool_arguments` | 3/3 | 0/3 |
| `grounding_violation` | 3/3 | 0/3 |
| `consent_withdrawal` | 3/3 | 3/3 |

Fake overall: 60/60 (100%), tool-call accuracy 0.70. qwen3:1.7b overall: 54/60 (90%), tool-call accuracy 1.00, LLM-call median 0.438480215 s, p95 2.590261806 s. The two OPEN scenarios failed 0/3 each; traces are embedded in `raw-results/scenarios-ollama-1_7b-3x.json` under `malformed_tool_arguments` and `grounding_violation`. qwen3:4b was interrupted after about 10 minutes before the runner emitted a result JSON; its accuracy/pass rate are **NOT EXECUTED**. Partial VRAM sampling is in `raw-results/qwen4-vram-samples.csv` and is not used as a model comparison.



## Model comparison and real-provider latency (Step 2)

| Mode/model | Scenario pass rate | Tool-call accuracy | LLM latency | VRAM / disposition |
|---|---:|---:|---:|---|
| Fake providers + MOCK CRM | 60/60 (100%) | 0.70 | Not applicable; deterministic Fake | CI-safe baseline; raw trace in `raw-results/scenarios-fake-3x.json` |
| qwen3:1.7b Q4_K_M | 54/60 (90%); 18/20 scenarios pass all 3 repeats | 1.00 | median 0.438 s; p95 2.590 s per tool-loop request | 100% GPU per `ollama ps`; 8 GiB RTX 4060, hardware record below |
| qwen3:4b | **NOT EXECUTED** to completion | **NOT EXECUTED** | **NOT EXECUTED** | Run interrupted before result JSON; partial sampler only: `raw-results/qwen4-vram-samples.csv` |
| qwen3:0.6b, qwen3:8b | **NOT EXECUTED** in this comparison | **NOT EXECUTED** | **NOT EXECUTED** | Explicitly out of scope for this sprint |

Tool-call accuracy is computed from scenario traces as correct tool, schema-valid arguments, and permitted current state. Default remains qwen3:1.7b because it is the only real model with a completed 20-scenario × 3-repeat result in this sprint: 90% pass and 1.00 tool-call accuracy. This supports a measured prototype default; qwen3:4b was not completed, so no claim that 1.7b is best among model sizes is supported. Scenario command/raw files: `tools/evaluate_scenarios.py`, `raw-results/scenarios-fake-3x.json`, `raw-results/scenarios-ollama-1_7b-3x.json`; implementation/evidence commit `aaf971bc758287b5bd4323799625ea821c3c1a1a`.

**SYNTHETIC audio; MOCK CRM; real local providers.** Command: `python tools/measure_ws_latency.py --consent-wav raw-results/synthetic-consent.wav --request-wav raw-results/synthetic-status.wav --output raw-results/latency-real-ws-30.json --turns 30 --asr-model base.en --asr-device cpu --asr-compute-type int8 --llm-model qwen3:1.7b --llm-quantization Q4_K_M --tts-voice en_US-lessac-medium`. Run code, audio, and 30 raw traces: commit `2e6a1f2239f9b2d533dd24365b5f87023c8d2adf`. Hardware/provider details: `raw-results/step2-hardware.txt` (RTX 4060, 8 GiB VRAM; qwen3:1.7b Q4_K_M, Ollama reports 100% GPU; Faster-Whisper `base.en`, CPU `int8`; WebRTC VAD; Piper `en_US-lessac-medium`; thinking OFF). All 30 calls granted consent; identity verified 30/30; loan status CRM lookup succeeded 27/30 (3 calls did not issue the status tool). The calls used no real customer data or recordings.

| Stage | p50 (s) | p95 (s) | Samples / definition |
|---|---:|---:|---|
| VAD endpoint → ASR done | 1.643 | 3.780 | 30; ASR stage elapsed after utterance endpoint |
| LLM first token | **NOT MEASURED** | **NOT MEASURED** | Ollama structured tool loop is non-streaming; raw trace's legacy `llm_first_token` key is response-ready elapsed time, not token latency |
| First sentence available | 2.419 | 3.266 | 30; after the complete non-streaming tool loop returns |
| TTS audio available | 2.067 | 8.030 | 30; Piper synthesis duration until complete audio bytes are available to the WebSocket sender |
| User's final audio sent → first TTS media received | 14.383 | 18.705 | 30; simulator client wall clock, includes VAD hangover, ASR, LLM/tool loop, TTS, and transport |

The percentile script uses median for p50 and nearest-rank for p95. Its raw per-turn observations, full call traces, and sample audio are committed above. A prior 30-turn input phrased DOB naturally and caused CRM validation errors; corrected SYNTHETIC speech explicitly enunciated the ISO date. Before/after evidence: `raw-results/latency-real-ws-30-before-input-fix.json` and `raw-results/latency-real-ws-30.json`. This input correction is not a code-quality or real-user success claim.


## Demo and current CI evidence (Steps 0 and 3)

`PIPER_VOICE_PATH=/path/to/en_US-lessac-medium.onnx make demo` ran with real local Faster-Whisper `base.en`, Ollama qwen3:1.7b Q4_K_M, Piper, and **MOCK** CRM. Result: **PASS** for synthetic recording consent, identity verification, loan-status lookup, and callback scheduling; output and redacted incoming transcript: `docs/demo-output.txt`. This local call logged a `grounding_violation` event; see `docs/FAILURE_MODES.md`. Source, run output, and artifact commit: `8968820f3f6d5bdf873b04312fc6b008e82cbe98`. No real customer data or audio was used.

| Remote CI evidence | Result | Exact HEAD SHA | Raw output |
|---|---|---|---|
| Step 1 push | success, run `43724893777` | `ac568cdbefc52c0a992ce46973b549f129add8cc` | `raw-results/step1-ci.json` |
| Step 2 push | success, run `43728808269` | `15715d73bc775d65907651edf3d9f18805e8ba98` | `raw-results/step2-ci.json` |
| Step 3 push | success, run `43728953652` | `8968820f3f6d5bdf873b04312fc6b008e82cbe98` | `raw-results/step3-ci.json` |
| Docker Compose CLI probe | version `v5.5.1`; build and service checks **NOT EXECUTED** by sprint scope | Local WSL2 | `docker compose version` → `raw-results/docker-compose-version.txt` |

The first Step 0 pushes failed CI (runs `43719643851` and `43720052510`); time-dependent tests and the missing-optional-Presidio fallback were fixed. The later Step 1–3 pushes above passed. Final documentation HEAD CI is verified in the final report.
