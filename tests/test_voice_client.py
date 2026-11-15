from fastapi.testclient import TestClient

from app.main import app


def test_voice_client_page_is_served() -> None:
    response = TestClient(app).get("/voice")

    assert response.status_code == 200
    assert "getUserMedia" in response.text
    assert "BROWSER" in response.text
    assert "Microphone opens when it finishes" in response.text
    assert "initialPromptPending" in response.text


def test_health_reports_real_provider_mode(monkeypatch) -> None:
    monkeypatch.setenv("VOICE_AGENT_REAL_PROVIDERS", "true")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:1.7b")

    response = TestClient(app).get("/health")

    assert response.json() == {"status": "ok", "providers": "REAL", "model": "qwen3:1.7b"}
