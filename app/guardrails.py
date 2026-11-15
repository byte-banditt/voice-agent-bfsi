from __future__ import annotations

import re
from dataclasses import dataclass, field

SAFE_FALLBACK = "I cannot confirm that information right now. I can connect you with a human agent."


def redact_pii(text: str) -> str:
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[REDACTED_EMAIL]", text)
    text = re.sub(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)", "[REDACTED_PHONE]", text)
    text = re.sub(r"\b(?:\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b", "[REDACTED_DATE]", text)
    return text


_GROUNDED_TOKEN = re.compile(
    r"(?i)(?:\b\d+(?:,\d{3})*(?:\.\d+)?\b|(?<!\w)(?:account|loan)-[A-Z0-9-]{2,}\b)"
)


def enforce_grounding(reply: str, tool_results: list[dict[str, object]]) -> tuple[str, bool]:
    evidence = " ".join(str(value) for result in tool_results for value in result.values())
    evidence_tokens = {match.group(0).casefold().replace(",", "") for match in _GROUNDED_TOKEN.finditer(evidence)}
    grounded = all(match.group(0).casefold().replace(",", "") in evidence_tokens
                   for match in _GROUNDED_TOKEN.finditer(reply))
    return (reply, False) if grounded else (SAFE_FALLBACK, True)


@dataclass
class IdentityGate:
    attempts: int = 0
    customer_id: str | None = None
    escalated: bool = False

    def verify(self, customer_id: str, dob: str, phone_last4: str, expected: dict[str, str]) -> bool:
        if self.escalated or self.customer_id is not None:
            return self.customer_id == customer_id
        self.attempts += 1
        valid = dob == expected.get("dob") and phone_last4 == expected.get("phone_last4")
        if valid:
            self.customer_id = customer_id
        elif self.attempts >= 3:
            self.escalated = True
        return valid

    def authorize(self, customer_id: str) -> bool:
        return self.customer_id == customer_id and not self.escalated
