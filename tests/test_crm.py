from fastapi.testclient import TestClient

from app import crm


def test_crm_requires_api_key_and_verified_identity(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(crm, "DB_PATH", tmp_path / "crm.sqlite")
    monkeypatch.setattr(crm, "API_KEY", "test-only-key")
    with TestClient(crm.crm_app) as client:
        denied = client.get("/customers/cust-demo-1", headers={"X-API-Key": "test-only-key"})
        assert denied.status_code == 403
        invalid_key = client.post("/verify_identity", json={"customer_id": "cust-demo-1", "dob": "1990-01-02", "phone_last4": "0134"})
        assert invalid_key.status_code == 401
        verified = client.post("/verify_identity", headers={"X-API-Key": "test-only-key"}, json={"customer_id": "cust-demo-1", "dob": "1990-01-02", "phone_last4": "0134"})
        assert verified.json() == {"verified": True}
        allowed = client.get("/customers/cust-demo-1", headers={"X-API-Key": "test-only-key", "X-Verified-Customer": "cust-demo-1"})
        assert allowed.status_code == 200
        active_loan = client.get("/customers/cust-demo-1/loans/first", headers={"X-API-Key": "test-only-key", "X-Verified-Customer": "cust-demo-1"})
        assert active_loan.json() == {"id": "loan-demo-1", "status": "due", "amount": "1200", "due_date": "2030-01-15"}
        other_customer = client.get("/customers/cust-demo-1/loans/first", headers={"X-API-Key": "test-only-key", "X-Verified-Customer": "cust-demo-2"})
        assert other_customer.status_code == 403
        with crm.connect() as db:
            db.execute("INSERT INTO customers VALUES ('cust-demo-2','Other Example','1980-01-01','9999')")
            db.execute("INSERT INTO loans VALUES ('loan-other-1','cust-demo-2','due','9900','2030-02-01')")
        cross_account = client.get("/loans/loan-other-1", headers={"X-API-Key": "test-only-key", "X-Verified-Customer": "cust-demo-1"})
        assert cross_account.status_code == 403
        callback_headers = {"X-API-Key": "test-only-key", "X-Verified-Customer": "cust-demo-1", "X-Idempotency-Key": "callback-test-1"}
        callback_payload = {"customer_id": "cust-demo-1", "requested_at": "2030-01-16T10:00:00Z"}
        assert client.post("/schedule_callback", headers=callback_headers, json=callback_payload).json() == {"scheduled": True}
        assert client.post("/schedule_callback", headers=callback_headers, json=callback_payload).json() == {"scheduled": True}
        changed_payload = {"customer_id": "cust-demo-1", "requested_at": "2030-01-17T10:00:00Z"}
        assert client.post("/schedule_callback", headers=callback_headers, json=changed_payload).status_code == 409
        with crm.connect() as db:
            assert db.execute("SELECT COUNT(*) FROM callbacks").fetchone()[0] == 1
        legacy = client.post("/schedule_callback", headers={"X-API-Key": "test-only-key", "X-Verified-Customer": "cust-demo-1"}, json=changed_payload)
        assert legacy.status_code == 200
        with crm.connect() as db:
            assert db.execute("SELECT COUNT(*) FROM callbacks").fetchone()[0] == 2
