from __future__ import annotations

import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

DB_PATH = Path(os.getenv("CRM_DATABASE_PATH", "crm.db"))
API_KEY = os.getenv("CRM_API_KEY", "")


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def initialize() -> None:
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS customers (id TEXT PRIMARY KEY, name TEXT, dob TEXT, phone_last4 TEXT);
        CREATE TABLE IF NOT EXISTS loans (id TEXT PRIMARY KEY, customer_id TEXT, status TEXT, amount TEXT, due_date TEXT);
        CREATE TABLE IF NOT EXISTS call_outcomes (id INTEGER PRIMARY KEY, customer_id TEXT, outcome TEXT);
        CREATE TABLE IF NOT EXISTS callbacks (id INTEGER PRIMARY KEY, customer_id TEXT, requested_at TEXT);
        CREATE TABLE IF NOT EXISTS payment_links (id INTEGER PRIMARY KEY, customer_id TEXT, link TEXT);
        """)
        db.execute("INSERT OR IGNORE INTO customers VALUES ('cust-demo-1','Asha Example','1990-01-02','0134')")
        db.execute("INSERT OR IGNORE INTO loans VALUES ('loan-demo-1','cust-demo-1','due','1200','2030-01-15')")


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize()
    yield


crm_app = FastAPI(title="Mock CRM (MOCK data)", lifespan=lifespan)


def require_key(key: str | None) -> None:
    if not API_KEY or key is None or key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid API key")


class VerifyRequest(BaseModel):
    customer_id: str = Field(min_length=1, max_length=64)
    dob: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    phone_last4: str = Field(pattern=r"^\d{4}$")


class OutcomeRequest(BaseModel):
    customer_id: str = Field(min_length=1, max_length=64)
    outcome: str = Field(min_length=1, max_length=100)


class CallbackRequest(BaseModel):
    customer_id: str = Field(min_length=1, max_length=64)
    requested_at: str = Field(min_length=1, max_length=40)


def customer_exists(customer_id: str, db: sqlite3.Connection) -> bool:
    return db.execute("SELECT 1 FROM customers WHERE id=?", (customer_id,)).fetchone() is not None


@crm_app.post("/verify_identity")
def verify_identity(payload: VerifyRequest, x_api_key: str | None = Header(default=None)) -> dict[str, bool]:
    require_key(x_api_key)
    with connect() as db:
        row = db.execute("SELECT dob, phone_last4 FROM customers WHERE id=?", (payload.customer_id,)).fetchone()
    if not row:
        return {"verified": False}
    return {"verified": row["dob"] == payload.dob and row["phone_last4"] == payload.phone_last4}


def get_customer_data(customer_id: str, key: str | None, verified_customer_id: str | None) -> dict[str, Any]:
    require_key(key)
    if customer_id != verified_customer_id:
        raise HTTPException(status_code=403, detail="identity verification required")
    with connect() as db:
        row = db.execute("SELECT id,name FROM customers WHERE id=?", (customer_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="customer not found")
    return dict(row)


@crm_app.get("/customers/{customer_id}")
def get_customer(customer_id: str, x_api_key: str | None = Header(default=None), x_verified_customer: str | None = Header(default=None)) -> dict[str, Any]:
    return get_customer_data(customer_id, x_api_key, x_verified_customer)


@crm_app.get("/loans/{loan_id}")
def get_loan(loan_id: str, x_api_key: str | None = Header(default=None), x_verified_customer: str | None = Header(default=None)) -> dict[str, Any]:
    require_key(x_api_key)
    with connect() as db:
        row = db.execute("SELECT id,customer_id,status,amount,due_date FROM loans WHERE id=?", (loan_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="loan not found")
    if row["customer_id"] != x_verified_customer:
        raise HTTPException(status_code=403, detail="identity verification required")
    return dict(row)


@crm_app.post("/log_call_outcome")
def log_call_outcome(payload: OutcomeRequest, x_api_key: str | None = Header(default=None), x_verified_customer: str | None = Header(default=None)) -> dict[str, bool]:
    require_key(x_api_key)
    if payload.customer_id != x_verified_customer:
        raise HTTPException(status_code=403, detail="identity verification required")
    with connect() as db:
        if not customer_exists(payload.customer_id, db):
            raise HTTPException(status_code=404, detail="customer not found")
        db.execute("INSERT INTO call_outcomes(customer_id,outcome) VALUES (?,?)", (payload.customer_id, payload.outcome))
    return {"logged": True}


@crm_app.post("/schedule_callback")
def schedule_callback(payload: CallbackRequest, x_api_key: str | None = Header(default=None), x_verified_customer: str | None = Header(default=None)) -> dict[str, bool]:
    require_key(x_api_key)
    if payload.customer_id != x_verified_customer:
        raise HTTPException(status_code=403, detail="identity verification required")
    with connect() as db:
        if not customer_exists(payload.customer_id, db):
            raise HTTPException(status_code=404, detail="customer not found")
        db.execute("INSERT INTO callbacks(customer_id,requested_at) VALUES (?,?)", (payload.customer_id, payload.requested_at))
    return {"scheduled": True}


@crm_app.post("/create_payment_link")
def create_payment_link(customer_id: str, x_api_key: str | None = Header(default=None), x_verified_customer: str | None = Header(default=None)) -> dict[str, str]:
    require_key(x_api_key)
    if customer_id != x_verified_customer:
        raise HTTPException(status_code=403, detail="identity verification required")
    with connect() as db:
        if not customer_exists(customer_id, db):
            raise HTTPException(status_code=404, detail="customer not found")
        link = f"https://example.invalid/mock-payment/{customer_id}"
        db.execute("INSERT INTO payment_links(customer_id,link) VALUES (?,?)", (customer_id, link))
    return {"link": link, "mock": "true"}


@crm_app.post("/escalate_to_human")
def escalate_to_human(customer_id: str, x_api_key: str | None = Header(default=None)) -> dict[str, str]:
    require_key(x_api_key)
    return {"status": "queued", "customer_id": customer_id, "mock": "true"}
