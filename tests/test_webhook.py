import time

from fastapi.testclient import TestClient

from app import webhook


def test_webhook_signature_and_duplicate_delivery(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(webhook, "DB", str(tmp_path / "webhooks.sqlite"))
    monkeypatch.setattr(webhook, "SECRET", "test-only-secret")
    client = TestClient(webhook.receiver)
    body = b'{"call_id":"synthetic-test"}'
    timestamp = str(int(time.time()))
    headers = {"X-Timestamp": timestamp, "X-Signature": webhook.sign(timestamp, body), "X-Idempotency-Key": "test-1"}
    assert client.post("/webhooks/call-completed", content=body, headers=headers).json() == {"status": "accepted"}
    assert client.post("/webhooks/call-completed", content=body, headers=headers).json() == {"status": "duplicate"}
    headers["X-Signature"] = "invalid"
    assert client.post("/webhooks/call-completed", content=body, headers=headers).status_code == 401
