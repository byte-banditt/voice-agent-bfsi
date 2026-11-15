import base64

from fastapi.testclient import TestClient

from app.main import app


def test_simulator_media_stream_round_trip() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws") as socket:
        socket.send_json({"event": "start", "start": {"mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1}}})
        socket.send_json({"event": "media", "media": {"payload": base64.b64encode(b"\xff" * 80).decode()}})
        response = socket.receive_json()
        assert response["event"] == "media"
        assert response["mock"] is True
        socket.send_json({"event": "stop"})


def test_empty_media_returns_silence() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws") as socket:
        socket.send_json({"event": "media", "media": {"payload": ""}})
        assert socket.receive_json() == {"event": "silence"}
        socket.send_json({"event": "stop"})
