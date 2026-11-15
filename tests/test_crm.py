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
