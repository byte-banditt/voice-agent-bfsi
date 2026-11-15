import base64
import asyncio
import time
from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

from app import main
from app.main import app
from app.providers import FakeASR, FakeLLM, FakeTTS


class FakeVAD:
    def __init__(self):
        self.calls = 0
        self.frame_bytes = 640

    def is_speech(self, frame):
        self.calls += 1
        return (self.calls - 1) % 17 < 2


def test_simulator_media_stream_round_trip(monkeypatch) -> None:
    monkeypatch.setattr(main, "WebRTCVAD", FakeVAD)
    monkeypatch.setattr(main, "configured_providers", lambda: (FakeASR("yes"), FakeLLM(), FakeTTS()))
    client = TestClient(app)
    with client.websocket_connect("/ws") as socket:
        socket.send_json({"event": "start", "start": {"mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1}}})
        assert socket.receive_json()["event"] == "media"
        socket.send_json({"event": "media", "media": {"payload": base64.b64encode(b"\xff" * 160 * 17).decode()}})
        socket.send_json({"event": "media", "media": {"payload": base64.b64encode(b"\xff" * 160 * 17).decode()}})
        response = socket.receive_json()
        assert response["event"] == "media"
        assert response["streamSid"] == "SIMULATOR"
        assert len(base64.b64decode(response["media"]["payload"])) > 0
        socket.send_json({"event": "stop"})


def test_empty_media_returns_silence(monkeypatch) -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws") as socket:
        socket.send_json({"event": "start"})
        assert socket.receive_json()["event"] == "media"
        socket.send_json({"event": "media", "media": {"payload": ""}})
        assert socket.receive_json() == {"event": "silence"}
        socket.send_json({"event": "stop"})


def test_completion_persists_trace_after_webhook_delivery(monkeypatch) -> None:
    sent = []
    saved = []

    async def send(trace):
        sent.append(trace["call_id"])

    class Store:
        def save_trace(self, trace):
            saved.append(trace["call_id"])

    monkeypatch.setattr(main, "_send_completion_event", send)
    monkeypatch.setattr(main, "store", Store())
    import asyncio
    asyncio.run(main._save_completed_trace({"call_id": "synthetic-call", "errors": []}))
    assert sent == ["synthetic-call"]
    assert saved == ["synthetic-call"]


def test_declined_consent_exits_without_persisting_transcript(monkeypatch) -> None:
    class Store:
        trace = None

        def save_trace(self, trace):
            self.trace = dict(trace)

    store = Store()
    monkeypatch.setattr(main, "store", store)
    monkeypatch.setattr(main, "WebRTCVAD", FakeVAD)
    monkeypatch.setattr(main, "configured_providers", lambda: (FakeASR("no"), FakeLLM(), FakeTTS()))
    speech = {"event": "media", "media": {"payload": base64.b64encode(b"\xff" * 160 * 17).decode()}}
    with TestClient(app).websocket_connect("/ws") as socket:
        socket.send_json({"event": "start"})
        assert socket.receive_json()["event"] == "media"  # Recording-consent prompt.
        socket.send_json(speech)
        assert socket.receive_json()["event"] == "media"  # Polite exit.
    assert store.trace["transcript"] == ""
    assert store.trace["consent_status"] == "declined"


def test_uncertain_consent_repeats_prompt_then_accepts_yes(monkeypatch) -> None:
    class SequenceASR:
        hypotheses = iter(("I think so", "yeah"))

        async def transcribe(self, pcm16: bytes, sample_rate: int) -> str:
            return next(self.hypotheses)

    class Store:
        trace = None

        def save_trace(self, trace):
            self.trace = dict(trace)

    store = Store()
    monkeypatch.setattr(main, "store", store)
    monkeypatch.setattr(main, "WebRTCVAD", FakeVAD)
    monkeypatch.setattr(main, "configured_providers", lambda: (SequenceASR(), FakeLLM(), FakeTTS()))
    speech = {"event": "media", "media": {"payload": base64.b64encode(b"\xff" * 160 * 17).decode()}}

    with TestClient(app).websocket_connect("/ws") as socket:
        socket.send_json({"event": "start"})
        assert socket.receive_json()["event"] == "media"  # Initial consent prompt.
        socket.send_json(speech)
        assert socket.receive_json()["event"] == "media"  # Unclear response repeats consent.
        socket.send_json(speech)
        socket.send_json({"event": "stop"})

    assert store.trace["consent_status"] == "granted"


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
    monkeypatch.setattr(main, "configured_providers", lambda: (FakeASR("yes"), provider, FakeTTS()))
    media = {"event": "media", "media": {"payload": base64.b64encode(b"\xff" * 160 * 17).decode()}}
    with TestClient(app).websocket_connect("/ws") as socket:
        socket.send_json({"event": "start"})
        assert socket.receive_json()["event"] == "media"
        socket.send_json(media)
        socket.send_json(media)  # Consent turn, then first assistant turn.
        time.sleep(0.05)
        socket.send_json(media)
        assert socket.receive_json()["event"] == "clear"
        assert socket.receive_json()["event"] == "media"
        socket.send_json({"event": "stop"})


def test_silence_does_not_cancel_inflight_llm(monkeypatch) -> None:
    class FirstSpeechOnlyVAD:
        def __init__(self):
            self.calls = 0
            self.frame_bytes = 640

        def is_speech(self, frame):
            self.calls += 1
            return self.calls <= 2 or 18 <= self.calls <= 19

    class SlowReply:
        calls = 0

        async def stream_reply(self, transcript: str) -> AsyncIterator[str]:
            self.calls += 1
            await asyncio.sleep(10)
            yield "I can help."

    provider = SlowReply()
    monkeypatch.setattr(main, "WebRTCVAD", FirstSpeechOnlyVAD)
    monkeypatch.setattr(main, "configured_providers", lambda: (FakeASR("yes"), provider, FakeTTS()))
    speech = {"event": "media", "media": {"payload": base64.b64encode(b"\xff" * 160 * 17).decode()}}
    silence = {"event": "media", "media": {"payload": base64.b64encode(b"\xff" * 160 * 17).decode()}}
    with TestClient(app).websocket_connect("/ws") as socket:
        socket.send_json({"event": "start"})
        assert socket.receive_json()["event"] == "media"
        socket.send_json(speech)
        time.sleep(0.05)
        socket.send_json(silence)
        time.sleep(0.05)
        socket.send_json(silence)
        time.sleep(0.05)
        assert provider.calls == 1
        socket.send_json({"event": "stop"})
