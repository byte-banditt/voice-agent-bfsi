from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import time
import asyncio
import uuid
from typing import Any

import httpx

from fastapi import FastAPI, Header, HTTPException, Request

receiver = FastAPI(title="Mock webhook receiver")
SECRET = os.getenv("WEBHOOK_SECRET", "")
DB = "webhooks.db"


def sign(timestamp: str, body: bytes, secret: str | None = None) -> str:
    return hmac.new((SECRET if secret is None else secret).encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()


async def send_webhook(
    url: str,
    payload: dict[str, Any],
    secret: str,
    idempotency_key: str | None = None,
    attempts: int = 3,
    backoff_seconds: float = 0.25,
) -> httpx.Response:
    """Send a signed event; retain one idempotency key across bounded retries."""
    if not secret or attempts < 1 or backoff_seconds < 0:
        raise ValueError("secret, positive attempts, and nonnegative backoff are required")
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    key = idempotency_key or str(uuid.uuid4())
    async with httpx.AsyncClient(timeout=5.0) as client:
        for attempt in range(attempts):
            timestamp = str(int(time.time()))
            headers = {
                "Content-Type": "application/json",
                "X-Signature": sign(timestamp, body, secret),
                "X-Timestamp": timestamp,
                "X-Idempotency-Key": key,
            }
            try:
                response = await client.post(url, content=body, headers=headers)
                if response.status_code < 500:
                    response.raise_for_status()
                    return response
                if attempt + 1 == attempts:
                    response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500 or attempt + 1 == attempts:
                    raise
            except httpx.HTTPError:
                if attempt + 1 == attempts:
                    raise
            await asyncio.sleep(backoff_seconds * (2 ** attempt))
    raise RuntimeError("webhook retry loop exhausted")


@receiver.post("/webhooks/call-completed")
async def receive(request: Request, x_signature: str | None = Header(default=None), x_timestamp: str | None = Header(default=None), x_idempotency_key: str | None = Header(default=None)) -> dict[str, str]:
    if not SECRET:
        raise HTTPException(503, "webhook secret is not configured")
    body = await request.body()
    if not x_signature or not x_timestamp or not x_idempotency_key:
        raise HTTPException(400, "missing signature headers")
    try:
        timestamp = int(x_timestamp)
    except ValueError as exc:
        raise HTTPException(400, "invalid timestamp") from exc
    if abs(time.time() - timestamp) > 300:
        raise HTTPException(401, "stale timestamp")
    if not hmac.compare_digest(sign(x_timestamp, body), x_signature):
        raise HTTPException(401, "invalid signature")
    try:
        json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "invalid JSON") from exc
    with sqlite3.connect(DB) as db:
        db.execute("CREATE TABLE IF NOT EXISTS deliveries (key TEXT PRIMARY KEY, body BLOB NOT NULL)")
        cursor = db.execute("INSERT OR IGNORE INTO deliveries VALUES (?,?)", (x_idempotency_key, body))
    return {"status": "accepted" if cursor.rowcount else "duplicate"}
