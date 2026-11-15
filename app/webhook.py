from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import time

from fastapi import FastAPI, Header, HTTPException, Request

receiver = FastAPI(title="Mock webhook receiver")
SECRET = os.getenv("WEBHOOK_SECRET", "")
DB = "webhooks.db"


def sign(timestamp: str, body: bytes) -> str:
    return hmac.new(SECRET.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()


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
