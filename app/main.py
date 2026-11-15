from __future__ import annotations

import asyncio
import base64
import json
import re
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.audio import mulaw_to_pcm16, pcm16_resample
from app.metrics import STAGE_SECONDS
from app.providers import FakeASR, FakeLLM, FakeTTS
from app.state import CallState, CallStateMachine

app = FastAPI(title="BFSI Voice Agent (MOCK providers)")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "providers": "MOCK"}


@app.websocket("/ws")
async def media_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    state = CallStateMachine()
    asr, llm, tts = FakeASR(), FakeLLM(), FakeTTS()
    playback: asyncio.Task[None] | None = None
    state.transition(CallState.LISTENING)
    try:
        while True:
            message = await websocket.receive_json()
            event = message.get("event")
            if event == "start":
                continue
            if event == "stop":
                if playback:
                    playback.cancel()
                state.transition(CallState.ENDED)
                await websocket.close()
                return
            if event != "media":
                await websocket.send_json({"event": "error", "error": "unsupported event"})
                continue
            if playback and playback.done() and state.state in {CallState.SPEAKING, CallState.THINKING}:
                state.transition(CallState.LISTENING)
            if playback and not playback.done():
                playback.cancel()
                await asyncio.gather(playback, return_exceptions=True)
                if state.state == CallState.SPEAKING:
                    state.transition(CallState.LISTENING)
                await websocket.send_json({"event": "barge_in"})

            try:
                encoded = base64.b64decode(message["media"]["payload"], validate=True)
            except (KeyError, ValueError, TypeError):
                await websocket.send_json({"event": "error", "error": "invalid media payload"})
                continue
            pcm = pcm16_resample(mulaw_to_pcm16(encoded), 8000, 16000)
            started = time.perf_counter()
            transcript = await asyncio.wait_for(asr.transcribe(pcm, 16000), timeout=10)
            STAGE_SECONDS.labels("asr").observe(time.perf_counter() - started)
            if not transcript.strip():
                await websocket.send_json({"event": "silence"})
                continue
            state.transition(CallState.THINKING)

            async def respond(user_text: str) -> None:
                llm_started = time.perf_counter()
                first_sentence = True
                pending = ""
                async for part in llm.stream_reply(user_text):
                    pending += part
                    sentences = re.split(r"(?<=[.!?])\s+", pending)
                    for sentence in sentences[:-1]:
                        if sentence.strip():
                            if first_sentence:
                                STAGE_SECONDS.labels("llm_first_sentence").observe(time.perf_counter() - llm_started)
                                state.transition(CallState.SPEAKING)
                                first_sentence = False
                            audio_started = time.perf_counter()
                            audio = await tts.synthesize(sentence.strip())
                            STAGE_SECONDS.labels("tts").observe(time.perf_counter() - audio_started)
                            await websocket.send_json({"event": "media", "media": {"payload": base64.b64encode(audio).decode("ascii")}, "mock": True})
                    pending = sentences[-1]
                if pending.strip():
                    if first_sentence:
                        STAGE_SECONDS.labels("llm_first_sentence").observe(time.perf_counter() - llm_started)
                        state.transition(CallState.SPEAKING)
                    audio_started = time.perf_counter()
                    audio = await tts.synthesize(pending.strip())
                    STAGE_SECONDS.labels("tts").observe(time.perf_counter() - audio_started)
                    await websocket.send_json({"event": "media", "media": {"payload": base64.b64encode(audio).decode("ascii")}, "mock": True})

            playback = asyncio.create_task(respond(transcript))
    except WebSocketDisconnect:
        if playback:
            playback.cancel()
