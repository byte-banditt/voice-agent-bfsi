from __future__ import annotations

import argparse
import asyncio
import base64
import json
import wave
from pathlib import Path

import websockets

from app.audio import pcm16_resample, pcm16_to_mulaw


async def replay(uri: str, wav_path: Path) -> None:
    with wave.open(str(wav_path), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
            raise ValueError("input must be mono PCM16 WAV")
        pcm = audio.readframes(audio.getnframes())
        pcm = pcm16_resample(pcm, audio.getframerate(), 8000)
    encoded = base64.b64encode(pcm16_to_mulaw(pcm)).decode("ascii")
    async with websockets.connect(uri) as socket:
        await socket.send(json.dumps({"event": "connected", "protocol": "Call", "version": "1.0.0"}))
        await socket.send(json.dumps({"event": "start", "streamSid": "SIMULATOR", "start": {"streamSid": "SIMULATOR", "mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1}}}))
        await socket.send(json.dumps({"event": "media", "streamSid": "SIMULATOR", "media": {"payload": encoded}}))
        sent_stop = False
        try:
            while True:
                message = json.loads(await socket.recv())
                print(json.dumps({"event": message.get("event"), "streamSid": message.get("streamSid")}))
                if not sent_stop and message.get("event") in {"media", "error", "silence"}:
                    await socket.send(json.dumps({"event": "stop", "streamSid": "SIMULATOR"}))
                    sent_stop = True
        except websockets.ConnectionClosed:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay a local WAV through the simulator-only WebSocket adapter")
    parser.add_argument("wav", type=Path)
    parser.add_argument("--uri", default="ws://localhost:8000/ws")
    args = parser.parse_args()
    asyncio.run(replay(args.uri, args.wav))


if __name__ == "__main__":
    main()
