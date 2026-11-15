from __future__ import annotations

import re
from dataclasses import dataclass, field

SAFE_FALLBACK = "I cannot confirm that information right now. I can connect you with a human agent."
CONDUCT_FALLBACK = "I want to keep this conversation respectful. I can connect you with a human agent."
RECORDING_CONSENT_LINE = "This call may be recorded to improve service. Do you consent to continue? Please say yes or no."
CONSENT_DECLINED_REPLY = "I understand. I will not continue or save this conversation. Goodbye."
REPEAT_PROMPT = "I did not catch that. Could you please repeat?"


def grants_recording_consent(text: str) -> bool:
    return bool(re.fullmatch(
        r"\s*(?:yes(?:,? i do)?|yeah|yep|yup|sure|okay|ok|"
        r"i consent(?: to continue)?|i agree(?: to continue)?)\s*[.!]?\s*",
        text, re.IGNORECASE,
    ))


def declines_recording_consent(text: str) -> bool:
    return bool(re.fullmatch(
        r"\s*(?:no(?:,? i do not)?|no,? thanks|i do not consent|"
        r"i don't consent|i do not agree|i don't agree|i refuse|stop)\s*[.!]?\s*",
        text, re.IGNORECASE,
    ))


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
    text = re.sub(r"(?i)\b(?:account|a/c|loan|customer)[\s:#-]*[A-Z0-9][A-Z0-9-]{5,}\b",
                  "[REDACTED_ACCOUNT_ID]", text)
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[REDACTED_EMAIL]", text)
    text = re.sub(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)", "[REDACTED_PHONE]", text)
    text = re.sub(r"\b(?:\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b", "[REDACTED_DATE]", text)
    return text


_GROUNDED_TOKEN = re.compile(
    r"(?i)(?:\b\d+(?:,\d{3})*(?:\.\d+)?\b|(?<!\w)(?:account|loan)-[A-Z0-9-]{2,}\b)"
)
_NUMBER_WORD = r"(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|lakh|lakhs|crore|crores)"
_SPOKEN_FINANCIAL_AMOUNT = re.compile(
    rf"(?i)\b(?:amount|balance|emi|installment|rupees?|inr)\b[^.!?]{{0,45}}\b{_NUMBER_WORD}\b"
)
_SPOKEN_DATE = re.compile(
    r"(?i)\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth|"
    r"thirteenth|fourteenth|fifteenth|sixteenth|seventeenth|eighteenth|nineteenth|twentieth|"
    r"twenty[- ]first|twenty[- ]second|twenty[- ]third|twenty[- ]fourth|twenty[- ]fifth|"
    r"twenty[- ]sixth|twenty[- ]seventh|twenty[- ]eighth|twenty[- ]ninth|thirtieth|thirty[- ]first)\b"
)


def enforce_grounding(reply: str, tool_results: list[dict[str, object]]) -> tuple[str, bool]:
    evidence = " ".join(str(value) for result in tool_results for value in result.values())
    evidence_tokens = {match.group(0).casefold().replace(",", "") for match in _GROUNDED_TOKEN.finditer(evidence)}
    grounded = all(match.group(0).casefold().replace(",", "") in evidence_tokens
                   for match in _GROUNDED_TOKEN.finditer(reply))
    if _SPOKEN_FINANCIAL_AMOUNT.search(reply) or _SPOKEN_DATE.search(reply):
        return SAFE_FALLBACK, True
    return (reply, False) if grounded else (SAFE_FALLBACK, True)


def enforce_action_claims(reply: str, tool_results: list[dict[str, object]]) -> tuple[str, bool]:
    """Allow consequential completion claims only when their backend result exists."""
    claims = (
        (re.compile(r"(?i)\b(?:your )?payment (?:was|has been|is) (?:made|received|processed|successful|complete)|we received your payment|your payment went through\b"), "payment_confirmed"),
        (re.compile(r"(?i)\b(?:callback is|callback has been|your callback was) scheduled\b"), "scheduled"),
        (re.compile(r"(?i)\b(?:payment )?link (?:was|has been|is) (?:created|sent)\b"), "link"),
        (re.compile(r"(?i)\b(?:offer|payment outcome) (?:is|was|has been) recorded\b"), "logged"),
        (re.compile(r"(?i)\b(?:i will|i have|we will|we have) (?:connect|transfer) you to a human agent\b"), "status"),
    )
    for pattern, result_key in claims:
        confirmed = any(
            result.get("status") == "queued" if result_key == "status" else bool(result.get(result_key))
            for result in tool_results
        )
        if pattern.search(reply) and not confirmed:
            return SAFE_FALLBACK, True
    return reply, False


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
