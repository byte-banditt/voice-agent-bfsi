from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import uuid
import time

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.audio import mulaw_to_pcm16, pcm16_resample, pcm16_to_mulaw
from app.observability import CallStore
from app.metrics import STAGE_SECONDS
from app.providers import configured_providers
from app.state import CallState, CallStateMachine
from app.conversation import ConversationEngine
from app.tools import BFSIToolExecutor

app = FastAPI(title="BFSI Voice Agent (MOCK providers)")
store = CallStore(os.getenv("DATABASE_PATH", "voice_agent.db"))


async def _iterate(parts):
    for part in parts:
        yield part


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "providers": "MOCK"}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> str:
    return "<html><title>Voice Agent Calls</title><body><h1>Call traces</h1><pre id='summary'></pre><pre id='calls'></pre><script>fetch('/calls/summary').then(r=>r.json()).then(x=>document.getElementById('summary').textContent=JSON.stringify(x,null,2));fetch('/calls').then(r=>r.json()).then(x=>document.getElementById('calls').textContent=JSON.stringify(x,null,2));</script></body></html>"


@app.get("/calls")
async def list_calls(limit: int = 100) -> list[dict[str, object]]:
    if not 1 <= limit <= 500:
        raise HTTPException(422, "limit must be between 1 and 500")
    return store.list_calls(limit)


@app.get("/calls/summary")
async def call_summary() -> dict[str, object]:
    return store.summary()


class Feedback(BaseModel):
    call_id: str = Field(min_length=1, max_length=64)
    resolved: bool
    confusing: bool
    rating: int = Field(ge=1, le=5)
    free_text: str = Field(default="", max_length=2000)


@app.post("/feedback", status_code=201)
async def submit_feedback(payload: Feedback) -> dict[str, str]:
    if not any(row.get("call_id") == payload.call_id for row in store.list_calls(500)):
        raise HTTPException(404, "call not found")
    store.add_feedback(payload.call_id, payload.resolved, payload.confusing, payload.rating, payload.free_text)
    return {"status": "saved"}


@app.websocket("/ws")
async def media_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    state = CallStateMachine()
    asr, llm, tts = configured_providers()
    playback: asyncio.Task[None] | None = None
    stream_sid = "SIMULATOR"
    real_mode = os.getenv("VOICE_AGENT_REAL_PROVIDERS", "false").lower() == "true"
    flow_name = os.getenv("VOICE_AGENT_FLOW", "emi_reminder")
    engine = ConversationEngine(flow_name, BFSIToolExecutor(
        os.getenv("CRM_URL", "http://127.0.0.1:8001"), os.getenv("CRM_API_KEY", ""),
        os.getenv("CRM_CUSTOMER_ID", "cust-demo-1"),
    ))
    trace = {"call_id": str(uuid.uuid4()), "provider_mode": "REAL" if real_mode else "MOCK",
             "model_versions": {"asr": getattr(asr, "model_name", "FAKE"),
                                "llm": getattr(llm, "model", "FAKE"),
                                "tts": os.path.basename(getattr(tts, "voice_path", "FAKE"))},
             "prompt_version": engine.prompt_version, "flow": flow_name, "transcript": "", "stage_seconds": {},
             "tool_calls": [], "guardrail_events": [], "errors": []}
    state.transition(CallState.LISTENING)
    try:
        while True:
            message = await websocket.receive_json()
            event = message.get("event")
            if event == "connected":
                continue
            if event == "start":
                stream_sid = str(message.get("streamSid") or (message.get("start") or {}).get("streamSid") or "SIMULATOR")
                continue
            if event == "stop":
                if playback:
                    playback.cancel()
                    if playback.done() and not playback.cancelled() and playback.exception():
                        trace["errors"].append(type(playback.exception()).__name__)
                store.save_trace(trace)
                state.transition(CallState.ENDED)
                await websocket.close()
                return
            if event != "media":
                await websocket.send_json({"event": "error", "error": "unsupported event"})
                continue
            if playback and playback.done() and state.state in {CallState.SPEAKING, CallState.THINKING}:
                if not playback.cancelled() and playback.exception():
                    trace["errors"].append(type(playback.exception()).__name__)
                    await websocket.send_json({"event": "error", "error": "response generation failed"})
                state.transition(CallState.LISTENING)
            if playback and not playback.done():
                playback.cancel()
                await asyncio.gather(playback, return_exceptions=True)
                if state.state in {CallState.SPEAKING, CallState.THINKING}:
                    state.transition(CallState.LISTENING)
                await websocket.send_json({"event": "clear", "streamSid": stream_sid})

            try:
                encoded = base64.b64decode(message["media"]["payload"], validate=True)
            except (KeyError, ValueError, TypeError):
                await websocket.send_json({"event": "error", "error": "invalid media payload"})
                continue
            pcm = pcm16_resample(mulaw_to_pcm16(encoded), 8000, 16000)
            started = time.perf_counter()
            try:
                transcript = await asyncio.wait_for(asr.transcribe(pcm, 16000), timeout=10)
            except TimeoutError:
                STAGE_SECONDS.labels("asr").observe(time.perf_counter() - started)
                await websocket.send_json({"event": "error", "error": "ASR timeout"})
                trace["errors"].append("ASR timeout")
                continue
            except Exception as exc:
                STAGE_SECONDS.labels("asr").observe(time.perf_counter() - started)
                trace["errors"].append(type(exc).__name__)
                await websocket.send_json({"event": "error", "error": "ASR unavailable"})
                continue
            elapsed = time.perf_counter() - started
            STAGE_SECONDS.labels("asr").observe(elapsed)
            trace["stage_seconds"]["asr"] = elapsed
            trace["transcript"] = (str(trace["transcript"]) + " " + transcript).strip()
            if not transcript.strip():
                await websocket.send_json({"event": "silence"})
                continue
            state.transition(CallState.THINKING)

            async def respond(user_text: str) -> None:
                llm_started = time.perf_counter()
                first_sentence = True
                pending = ""
                if hasattr(llm, "chat_with_tools"):
                    response_text = await engine.respond(llm, user_text, trace)
                    response_parts = (response_text,)
                else:
                    response_parts = llm.stream_reply(user_text)
                async for part in response_parts if hasattr(response_parts, "__aiter__") else _iterate(response_parts):
                    trace["stage_seconds"].setdefault("llm_first_token", time.perf_counter() - llm_started)
                    pending += part
                    sentences = re.split(r"(?<=[.!?])\s+", pending)
                    for sentence in sentences[:-1]:
                        if sentence.strip():
                            if first_sentence:
                                STAGE_SECONDS.labels("llm_first_sentence").observe(time.perf_counter() - llm_started)
                                trace["stage_seconds"]["llm_first_sentence"] = time.perf_counter() - llm_started
                                state.transition(CallState.SPEAKING)
                                first_sentence = False
                            audio_started = time.perf_counter()
                            audio = await tts.synthesize(sentence.strip())
                            tts_elapsed = time.perf_counter() - audio_started
                            STAGE_SECONDS.labels("tts").observe(tts_elapsed)
                            trace["stage_seconds"]["tts_first_audio"] = tts_elapsed
                            telephony_audio = pcm16_to_mulaw(pcm16_resample(audio, 16000, 8000))
                            await websocket.send_json({"event": "media", "streamSid": stream_sid, "media": {"payload": base64.b64encode(telephony_audio).decode("ascii")}})
                    pending = sentences[-1]
                if pending.strip():
                    if first_sentence:
                        STAGE_SECONDS.labels("llm_first_sentence").observe(time.perf_counter() - llm_started)
                        trace["stage_seconds"]["llm_first_sentence"] = time.perf_counter() - llm_started
                        state.transition(CallState.SPEAKING)
                    audio_started = time.perf_counter()
                    audio = await tts.synthesize(pending.strip())
                    tts_elapsed = time.perf_counter() - audio_started
                    STAGE_SECONDS.labels("tts").observe(tts_elapsed)
                    trace["stage_seconds"]["tts_first_audio"] = tts_elapsed
                    telephony_audio = pcm16_to_mulaw(pcm16_resample(audio, 16000, 8000))
                    await websocket.send_json({"event": "media", "streamSid": stream_sid, "media": {"payload": base64.b64encode(telephony_audio).decode("ascii")}})

            async def respond_safely(user_text: str) -> None:
                try:
                    await respond(user_text)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    trace["errors"].append(type(exc).__name__)
                    if state.state in {CallState.THINKING, CallState.SPEAKING}:
                        state.transition(CallState.LISTENING)
                    await websocket.send_json({"event": "error", "error": "response generation unavailable"})

            playback = asyncio.create_task(respond_safely(transcript))
    except WebSocketDisconnect:
        if playback:
            playback.cancel()
        store.save_trace(trace)
