from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time
from zoneinfo import ZoneInfo
import os

SAFE_FALLBACK = "I cannot confirm that information right now. I can connect you with a human agent."
CONDUCT_FALLBACK = "I want to keep this conversation respectful. I can connect you with a human agent."
OUT_OF_HOURS_REPLY = "I am sorry, this is outside our permitted calling hours. We can contact you during the configured hours."
RECORDING_CONSENT_LINE = "This call may be recorded to improve service. Do you consent to continue? Please say yes or no."
CONSENT_DECLINED_REPLY = "I understand. I will not continue or save this conversation. Goodbye."


def grants_recording_consent(text: str) -> bool:
    return bool(re.fullmatch(r"\s*(?:yes|yes,? i consent|i consent|i agree|okay|ok)\s*[.!]?\s*", text, re.IGNORECASE))


def within_calling_hours(now: datetime | None = None) -> bool:
    """Check configurable local hours; defaults are an explicitly unverified policy assumption."""
    timezone = ZoneInfo(os.getenv("CALLING_HOURS_TIMEZONE", "Asia/Kolkata"))
    current = (now or datetime.now(timezone)).astimezone(timezone).time().replace(tzinfo=None)
    try:
        start = time.fromisoformat(os.getenv("CALLING_HOURS_START", "08:00"))
        end = time.fromisoformat(os.getenv("CALLING_HOURS_END", "19:00"))
    except ValueError as exc:
        raise ValueError("calling hours must use HH:MM values") from exc
    if start == end:
        return True
    if start < end:
        return start <= current < end
    return current >= start or current < end


def _presidio_spans(text: str) -> list[tuple[int, int, str]]:
    """Use Presidio PatternRecognizers for Indian phone and account-like identifiers."""
    try:
        from presidio_analyzer import Pattern, PatternRecognizer
    except ImportError:
        return []
    recognizers = (
        ("IN_PHONE", PatternRecognizer(
            supported_entity="IN_PHONE", patterns=[Pattern("indian_mobile", r"(?<!\d)(?:\+?91[ -]?)?[6-9]\d{9}(?!\d)", 0.85)],
        )),
        ("ACCOUNT_ID", PatternRecognizer(
            supported_entity="ACCOUNT_ID", patterns=[Pattern("account_reference", r"(?i)\b(?:account|a/c|loan|customer)[\s:#-]*[A-Z0-9][A-Z0-9-]{5,}\b", 0.9)],
        )),
    )
    spans: list[tuple[int, int, str]] = []
    for entity, recognizer in recognizers:
        spans.extend((item.start, item.end, f"[REDACTED_{entity}]")
                     for item in recognizer.analyze(text=text, entities=[entity]))
    return spans


def redact_pii(text: str) -> str:
    for start, end, replacement in sorted(_presidio_spans(text), reverse=True):
        text = text[:start] + replacement + text[end:]
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


_UNSAFE_CONDUCT = re.compile(
    r"(?i)\b(?:pay now or else|pay immediately or|we will (?:hurt|harm|punish|arrest) you|"
    r"you must pay right now|i will make you pay|we will seize your property today)\b"
)


def enforce_conduct(reply: str) -> tuple[str, bool]:
    return (CONDUCT_FALLBACK, True) if _UNSAFE_CONDUCT.search(reply) else (reply, False)


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
