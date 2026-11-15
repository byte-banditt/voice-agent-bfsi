import time
import asyncio

import httpx

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


def test_sender_retries_signed_request_with_same_idempotency_key(monkeypatch) -> None:
    requests = []

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, content, headers):
            requests.append((content, headers))
            return httpx.Response(500 if len(requests) == 1 else 200, request=httpx.Request("POST", url))

    monkeypatch.setattr(webhook.httpx, "AsyncClient", lambda **kwargs: Client())
    response = asyncio.run(webhook.send_webhook("https://example.test/hook", {"call_id": "x"},
                                                "secret", "key-1", attempts=2, backoff_seconds=0))
    assert response.status_code == 200
    assert len(requests) == 2
    assert requests[0][1]["X-Idempotency-Key"] == requests[1][1]["X-Idempotency-Key"] == "key-1"
