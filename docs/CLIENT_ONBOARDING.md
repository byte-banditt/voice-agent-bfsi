# Client onboarding templates

Templates only; no real client work is represented.

## Requirements-scoping questionnaire

- Business objective, eligible accounts, prohibited account states, and success definition:
- Call direction, languages, accents, expected concurrent calls, and operating geography:
- Approved data sources, identity factors, tool permissions, and escalation destination:
- Consent, recording, retention, deletion, and audit requirements:
- Calling-hours policy and its authoritative source:
- Human handoff, outage behavior, and service-level expectations:
- Acceptance scenarios, approvers, and rollback trigger:

## Integration checklist

- [ ] API ownership, authentication, schema, timeout, retry, idempotency, and rate limits agreed
- [ ] Least-privilege test credentials provisioned out of band
- [ ] Synthetic test fixtures and masked examples approved
- [ ] Telephony message/audio contract and failure behavior verified in a simulator
- [ ] Webhook signature, replay window, deduplication, and delivery retry tested
- [ ] PII, retention, access, and deletion reviewed by the client

## Go-live checklist

- [ ] Legal/compliance and security sign-off
- [ ] Client-system integration tested in an approved environment
- [ ] Call scenarios and human escalation accepted
- [ ] Monitoring, paging, incident owner, rollback, and retention verified
- [ ] Launch approval recorded

## Monitoring and incident runbook

1. Identify affected call IDs and time window; do not copy raw PII into tickets.
2. Check service health, provider health, CRM status, stage latency, tool errors, and guardrail events.
3. Stop outbound activity if identity, grounding, consent, or routing safety is uncertain.
4. Escalate to the named client operator; preserve only approved redacted traces.
5. Record root cause, mitigation, owner, and measured before/after evidence.
