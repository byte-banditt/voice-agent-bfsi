from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import httpx
import websockets
from piper import PiperVoice, SynthesisConfig

from app.audio import pcm16_resample, pcm16_to_mulaw


ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def synthesize(voice: PiperVoice, text: str, output: Path) -> None:
    with wave.open(str(output), "wb") as audio:
        voice.synthesize_wav(text, audio, syn_config=SynthesisConfig(noise_scale=0, noise_w_scale=0))


def to_mulaw(path: Path) -> str:
    with wave.open(str(path), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
            raise ValueError("Piper output must be mono PCM16")
        pcm = pcm16_resample(audio.readframes(audio.getnframes()), audio.getframerate(), 8000)
    return base64.b64encode(pcm16_to_mulaw(pcm)).decode("ascii")


async def send_audio(socket, payload: str) -> None:
    await socket.send(json.dumps({"event": "media", "streamSid": "SYNTHETIC-DEMO",
                                  "media": {"payload": payload}}))


async def collect_reply(socket, timeout: float = 90, idle: float = 2.5) -> int:
    deadline = time.monotonic() + timeout
    last_media = None
    media_count = 0
    while time.monotonic() < deadline:
        wait = min(0.25, max(0.01, deadline - time.monotonic()))
        try:
            event = json.loads(await asyncio.wait_for(socket.recv(), timeout=wait))
        except TimeoutError:
            if last_media is not None and time.monotonic() - last_media >= idle:
                return media_count
            continue
        if event.get("event") == "error":
            raise RuntimeError(f"WebSocket error: {event.get('error')}")
        if event.get("event") == "media":
            media_count += 1
            last_media = time.monotonic()
    raise TimeoutError("assistant did not return a TTS media event")


async def replay(ws_url: str, base_url: str, consent: str, identity_and_status: str,
                 callback: str, silence_frames: int = 20) -> dict[str, object]:
    silence = base64.b64encode(b"\xff" * (160 * 2 * silence_frames)).decode("ascii")
    async with websockets.connect(ws_url, max_size=8_000_000) as socket:
        await socket.send(json.dumps({"event": "connected", "protocol": "Call", "version": "1.0.0"}))
        await socket.send(json.dumps({"event": "start", "streamSid": "SYNTHETIC-DEMO",
                                      "start": {"streamSid": "SYNTHETIC-DEMO"}}))
        opening = json.loads(await asyncio.wait_for(socket.recv(), timeout=30))
        if opening.get("event") != "media":
            raise RuntimeError("call did not play the recording-consent line")
        await send_audio(socket, consent)
        await send_audio(socket, silence)
        await asyncio.sleep(0.3)
        await send_audio(socket, identity_and_status)
        await send_audio(socket, silence)
        first_audio = await collect_reply(socket)
        await send_audio(socket, callback)
        await send_audio(socket, silence)
        second_audio = await collect_reply(socket)
        await socket.send(json.dumps({"event": "stop", "streamSid": "SYNTHETIC-DEMO"}))
    await asyncio.sleep(0.1)
    async with httpx.AsyncClient(base_url=base_url, timeout=10) as client:
        traces = (await client.get("/calls", params={"limit": 1})).json()
    if not traces:
        raise RuntimeError("call trace was not saved")
    trace = traces[0]
    trace["simulator_tts_media_events"] = first_audio + second_audio
    return trace


async def wait_ready(url: str, *, crm: bool = False) -> None:
    async with httpx.AsyncClient(timeout=1) as client:
        for _ in range(100):
            try:
                response = await client.get(url, headers={"X-API-Key": "synthetic-demo-key"} if crm else None)
                if crm and response.status_code == 403:
                    return
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.1)
    raise RuntimeError(f"local service did not start: {url}")


def run_demo(args: argparse.Namespace) -> str:
    with tempfile.TemporaryDirectory(prefix="voice-agent-demo-") as temp:
        temp_path = Path(temp)
        crm_port, app_port = free_port(), free_port()
        key = "synthetic-demo-key"
        crm_url = f"http://127.0.0.1:{crm_port}"
        app_url = f"http://127.0.0.1:{app_port}"
        env = os.environ.copy()
        env.update({"VOICE_AGENT_REAL_PROVIDERS": "true", "VOICE_AGENT_FLOW": "emi_reminder",
                    "OLLAMA_MODEL": args.model, "ASR_MODEL": "base.en", "ASR_DEVICE": "cpu",
                    "ASR_COMPUTE_TYPE": "int8", "PIPER_VOICE_PATH": str(args.voice),
                    "CRM_URL": crm_url, "CRM_API_KEY": key, "CRM_CUSTOMER_ID": "cust-demo-1",
                    "CRM_DATABASE_PATH": str(temp_path / "crm.db"),
                    "DATABASE_PATH": str(temp_path / "calls.db"),
                    "CALLING_HOURS_START": "00:00", "CALLING_HOURS_END": "23:59"})
        crm = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.crm:crm_app", "--host",
                                "127.0.0.1", "--port", str(crm_port)], cwd=ROOT, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        app = None
        try:
            asyncio.run(wait_ready(f"{crm_url}/loans/loan-demo-1", crm=True))
            app = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host",
                                    "127.0.0.1", "--port", str(app_port)], cwd=ROOT, env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            asyncio.run(wait_ready(f"{app_url}/health"))
            voice = PiperVoice.load(str(args.voice))
            utterances = {
                "consent": "Okay.",
                "identity_and_status": ("My D O B is 1990 dash 01 dash 02. My phone last four digits are 0134. "
                                         "Please tell me the status of the loan. The exact identifier is loan dash demo dash one."),
                "callback": "Please schedule a callback for 2030 dash 01 dash 16 at 10 AM.",
            }
            payloads = {}
            for name, text in utterances.items():
                path = temp_path / f"{name}.wav"
                synthesize(voice, text, path)
                payloads[name] = to_mulaw(path)
            trace = asyncio.run(replay(f"ws://127.0.0.1:{app_port}/ws", app_url,
                                       payloads["consent"], payloads["identity_and_status"],
                                       payloads["callback"]))
        finally:
            if app is not None:
                app.terminate()
                app.wait(timeout=10)
            crm.terminate()
            crm.wait(timeout=10)

    calls = trace.get("tool_calls", [])
    successes = [call for call in calls if isinstance(call.get("result"), dict)
                 and "error" not in call["result"]]
    passed = (trace.get("provider_mode") == "REAL" and trace.get("consent_status") == "granted"
              and any(x.get("name") == "verify_identity" and x["result"].get("verified") for x in successes)
              and any(x.get("name") == "get_loan_status" for x in successes)
              and any(x.get("name") == "schedule_callback" and x["result"].get("scheduled") for x in successes))
    result = {
        "classification": "SYNTHETIC voice input; REAL local ASR/LLM/TTS; MOCK CRM",
        "result": "PASS" if passed else "FAIL",
        "provider_versions": trace.get("model_versions"),
        "prompt_version": trace.get("prompt_version"),
        "consent_status": trace.get("consent_status"),
        "redacted_transcript": trace.get("transcript"),
        "tool_calls": calls,
        "stage_seconds": {
            "vad_end_to_asr_done": trace.get("stage_seconds", {}).get("asr"),
            "llm_first_token": "NOT MEASURED: Ollama tool calls are non-streaming",
            "first_sentence_available_after_complete_tool_loop": trace.get("stage_seconds", {}).get("llm_first_sentence"),
            "tts_synthesis_to_audio_available": trace.get("stage_seconds", {}).get("tts_first_audio"),
        },
        "guardrail_events": trace.get("guardrail_events"),
        "errors": trace.get("errors"),
        "simulator_tts_media_events": trace.get("simulator_tts_media_events"),
        "calling_hours": "temporary demo configuration 00:00-23:59; default hours remain ASSUMPTION",
    }
    return json.dumps(result, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one SYNTHETIC real-provider EMI call through /ws and MOCK CRM")
    parser.add_argument("--voice", type=Path, required=True, help="local Piper ONNX voice file")
    parser.add_argument("--model", default="qwen3:1.7b")
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "demo-output.txt")
    args = parser.parse_args()
    if not args.voice.is_file():
        parser.error(f"Piper voice file does not exist: {args.voice}")
    output = run_demo(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output + "\n", encoding="utf-8")
    print(output)
    if json.loads(output)["result"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
