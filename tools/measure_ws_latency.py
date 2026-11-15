from __future__ import annotations

import argparse
import asyncio
import base64
import json
import statistics
import time
import wave
from pathlib import Path

import httpx
import websockets

from app.audio import pcm16_resample, pcm16_to_mulaw


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    if q == .50:
        return statistics.median(values)
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int((len(ordered) * q + 0.999999)) - 1))]


def load_mulaw(path: Path) -> str:
    with wave.open(str(path), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
            raise ValueError("input must be mono PCM16 WAV")
        pcm = pcm16_resample(audio.readframes(audio.getnframes()), audio.getframerate(), 8000)
    return base64.b64encode(pcm16_to_mulaw(pcm)).decode("ascii")


async def run(args: argparse.Namespace) -> dict[str, object]:
    consent_audio = load_mulaw(args.consent_wav)
    request_audio = load_mulaw(args.request_wav)
    silence = base64.b64encode(b"\xff" * (160 * 2 * args.silence_frames)).decode("ascii")
    headers = {"classification": "SYNTHETIC audio; MOCK CRM; real local ASR/LLM/TTS"}
    report: dict[str, object] = {
        **headers,
        "providers": {"asr": args.asr_model, "asr_device": args.asr_device,
                      "asr_compute_type": args.asr_compute_type, "llm": args.llm_model,
                      "llm_quantization": args.llm_quantization, "thinking": False,
                      "tts": args.tts_voice, "vad": "WebRTC VAD"},
        "requested_turns": args.turns,
        "turns": [],
        "metrics_seconds": {},
        "notes": ["LLM uses non-streaming structured tool calls; true first-token latency is unavailable."],
    }
    output = args.output
    output.parent.mkdir(parents=True, exist_ok=True)

    async def send_media(socket, payload: str) -> None:
        await socket.send(json.dumps({"event": "media", "streamSid": "SIMULATOR",
                                      "media": {"payload": payload}}))

    async with httpx.AsyncClient(base_url=args.http_base) as client:
        for index in range(args.turns):
            record: dict[str, object] = {"turn": index + 1}
            try:
                async with websockets.connect(args.ws_url, max_size=8_000_000) as socket:
                    await socket.send(json.dumps({"event": "connected", "protocol": "Call", "version": "1.0.0"}))
                    await socket.send(json.dumps({"event": "start", "streamSid": "SIMULATOR",
                                                  "start": {"streamSid": "SIMULATOR"}}))
                    message = json.loads(await asyncio.wait_for(socket.recv(), timeout=30))
                    if message.get("event") != "media":
                        raise RuntimeError(f"consent audio missing: {message.get('event')}")
                    await send_media(socket, consent_audio)
                    await send_media(socket, silence)
                    # Consent is deliberately a separate synthetic utterance.
                    await asyncio.sleep(args.consent_gap)
                    await send_media(socket, request_audio)
                    speech_sent = time.perf_counter()
                    await send_media(socket, silence)
                    for _ in range(8):
                        message = json.loads(await asyncio.wait_for(socket.recv(), timeout=args.timeout))
                        if message.get("event") == "error":
                            raise RuntimeError(str(message.get("error")))
                        if message.get("event") == "media":
                            record["user_stop_to_first_tts_byte_seconds"] = time.perf_counter() - speech_sent
                            record["first_audio_received"] = True
                            await socket.send(json.dumps({"event": "stop", "streamSid": "SIMULATOR"}))
                            break
                    else:
                        raise RuntimeError("no TTS audio before event limit")
                await asyncio.sleep(0.05)
                calls = (await client.get("/calls", params={"limit": 1})).json()
                if calls:
                    trace = calls[0]
                    record["trace"] = trace
                    if trace.get("consent_status") != "granted":
                        raise RuntimeError(f"synthetic consent was not recognized: {trace.get('consent_status')}")
                    if not trace.get("stage_seconds", {}).get("llm_first_sentence"):
                        raise RuntimeError("call produced no LLM sentence stage")
                    stages = trace.get("stage_seconds", {})
                    record["vad_end_to_asr_done_seconds"] = stages.get("asr")
                    # Current non-streaming tool loop returns a complete sentence, not token chunks.
                    record["llm_first_token_seconds"] = None
                    record["first_sentence_seconds"] = stages.get("llm_first_sentence")
                    record["tts_first_audio_byte_seconds"] = stages.get("tts_first_audio")
                else:
                    raise RuntimeError("completed call trace not found")
            except Exception as exc:
                record["error"] = f"{type(exc).__name__}: {exc}"
            report["turns"].append(record)
            valid = [x for x in report["turns"] if "error" not in x]
            keys = ("vad_end_to_asr_done_seconds", "llm_first_token_seconds",
                    "first_sentence_seconds", "tts_first_audio_byte_seconds",
                    "user_stop_to_first_tts_byte_seconds")
            report["metrics_seconds"] = {
                key: {"p50": percentile([float(x[key]) for x in valid if x.get(key) is not None], .50),
                      "p95": percentile([float(x[key]) for x in valid if x.get(key) is not None], .95),
                      "samples": sum(x.get(key) is not None for x in valid)}
                for key in keys
            }
            report["completed_turns"] = len(valid)
            report["failed_turns"] = len(report["turns"]) - len(valid)
            output.write_text(json.dumps(report, indent=2) + "\n")
            print(f"turn {index + 1}/{args.turns}: {'OK' if 'error' not in record else record['error']}", flush=True)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure SYNTHETIC audio turns through the local /ws provider loop")
    parser.add_argument("--consent-wav", type=Path, required=True)
    parser.add_argument("--request-wav", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--turns", type=int, default=30)
    parser.add_argument("--silence-frames", type=int, default=20)
    parser.add_argument("--consent-gap", type=float, default=0.5)
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--ws-url", default="ws://127.0.0.1:8000/ws")
    parser.add_argument("--http-base", default="http://127.0.0.1:8000")
    parser.add_argument("--asr-model", default="base.en")
    parser.add_argument("--asr-device", default="cpu")
    parser.add_argument("--asr-compute-type", default="int8")
    parser.add_argument("--llm-model", default="qwen3:1.7b")
    parser.add_argument("--llm-quantization", default="Q4_K_M")
    parser.add_argument("--tts-voice", default="en_US-lessac-medium")
    args = parser.parse_args()
    if args.turns < 1 or args.silence_frames < 15:
        parser.error("turns must be positive and silence frames must meet the VAD endpoint threshold")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
