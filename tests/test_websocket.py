import base64
import asyncio
import time
from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

from app import main
from app.main import app
from app.providers import FakeASR, FakeTTS


class FakeVAD:
    def __init__(self):
        self.calls = 0
        self.frame_bytes = 640

    def is_speech(self, frame):
        self.calls += 1
        return (self.calls - 1) % 17 < 2


def test_simulator_media_stream_round_trip(monkeypatch) -> None:
    monkeypatch.setattr(main, "WebRTCVAD", FakeVAD)
    client = TestClient(app)
    with client.websocket_connect("/ws") as socket:
        socket.send_json({"event": "start", "start": {"mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1}}})
        socket.send_json({"event": "media", "media": {"payload": base64.b64encode(b"\xff" * 160 * 17).decode()}})
        response = socket.receive_json()
        assert response["event"] == "media"
        assert response["streamSid"] == "SIMULATOR"
        assert len(base64.b64decode(response["media"]["payload"])) > 0
        socket.send_json({"event": "stop"})


def test_empty_media_returns_silence() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws") as socket:
        socket.send_json({"event": "media", "media": {"payload": ""}})
        assert socket.receive_json() == {"event": "silence"}
        socket.send_json({"event": "stop"})


def test_barge_in_cancels_inflight_llm(monkeypatch) -> None:
    class SlowFirstReply:
        calls = 0

        async def stream_reply(self, transcript: str) -> AsyncIterator[str]:
            self.calls += 1
            if self.calls == 1:
                await asyncio.sleep(10)
            yield "I can help."

    provider = SlowFirstReply()
    monkeypatch.setattr(main, "WebRTCVAD", FakeVAD)
    monkeypatch.setattr(main, "configured_providers", lambda: (FakeASR(), provider, FakeTTS()))
    media = {"event": "media", "media": {"payload": base64.b64encode(b"\xff" * 160 * 17).decode()}}
    with TestClient(app).websocket_connect("/ws") as socket:
        socket.send_json(media)
        time.sleep(0.05)
        socket.send_json(media)
        assert socket.receive_json()["event"] == "clear"
        assert socket.receive_json()["event"] == "media"
        socket.send_json({"event": "stop"})
