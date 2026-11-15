from __future__ import annotations

from typing import Any

import httpx

from app.guardrails import IdentityGate

_VERIFIED_TOOLS = {
    "get_customer": ("GET", "/customers/{customer_id}"),
    "get_loan_status": ("GET", "/loans/{loan_id}"),
    "log_call_outcome": ("POST", "/log_call_outcome"),
    "schedule_callback": ("POST", "/schedule_callback"),
    "create_payment_link": ("POST", "/create_payment_link"),
}


class BFSIToolExecutor:
    """Per-call tool gate. API credentials and verified identity stay server-side."""

    def __init__(self, crm_url: str, api_key: str, customer_id: str) -> None:
        self.crm_url = crm_url.rstrip("/")
        self.api_key = api_key
        self.customer_id = customer_id
        self.identity = IdentityGate()
        self.allowed_tools = {"verify_identity", "escalate_to_human"}

    async def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "verify_identity":
            if self.identity.escalated or self.identity.customer_id:
                return {"verified": self.identity.authorize(self.customer_id)}
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    response = await client.post(
                        f"{self.crm_url}/verify_identity",
                        headers={"X-API-Key": self.api_key},
                        json={"customer_id": self.customer_id, "dob": arguments["dob"], "phone_last4": arguments["phone_last4"]},
                    )
                    response.raise_for_status()
                    verified = bool(response.json().get("verified"))
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                return {"error": "identity service unavailable", "detail": type(exc).__name__}
            if verified:
                self.identity.customer_id = self.customer_id
                self.allowed_tools.update(_VERIFIED_TOOLS)
            else:
                self.identity.attempts += 1
                if self.identity.attempts >= 3:
                    self.identity.escalated = True
                    return await self._escalate()
            return {"verified": verified, "attempts_remaining": max(0, 3 - self.identity.attempts)}

        if name == "escalate_to_human":
            return await self._escalate()
        if name not in _VERIFIED_TOOLS:
            return {"error": "unknown tool"}
        if name not in self.allowed_tools or not self.identity.authorize(self.customer_id):
            return {"error": "identity verification required"}
        method, path = _VERIFIED_TOOLS[name]
        payload = dict(arguments)
        if name in {"log_call_outcome", "schedule_callback"}:
            payload["customer_id"] = self.customer_id
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.request(
                    method,
                    f"{self.crm_url}{path.format(customer_id=arguments.get('customer_id', self.customer_id), loan_id=arguments.get('loan_id', ''))}",
                    headers={"X-API-Key": self.api_key, "X-Verified-Customer": self.customer_id},
                    json=payload if method == "POST" else None,
                    params={"customer_id": self.customer_id} if name == "create_payment_link" else None,
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            return {"error": "CRM timeout"}
        except httpx.HTTPStatusError as exc:
            return {"error": "CRM rejected tool request", "status": exc.response.status_code}
        except httpx.HTTPError as exc:
            return {"error": "CRM unavailable", "detail": type(exc).__name__}

    async def _escalate(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.post(
                    f"{self.crm_url}/escalate_to_human",
                    headers={"X-API-Key": self.api_key},
                    params={"customer_id": self.customer_id},
                )
                response.raise_for_status()
                self.identity.escalated = True
                return response.json()
        except httpx.HTTPError as exc:
            self.identity.escalated = True
            return {"error": "escalation service unavailable", "detail": type(exc).__name__}
