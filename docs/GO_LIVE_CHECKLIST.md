# Go-live checklist template

**Not approved for production.** This checklist is incomplete until a real client and platform owner validate each item. No regulatory-compliance claim is made.

## Governance and policy

- [ ] Client approves business scope, languages, call direction, eligible accounts, and acceptance thresholds.
- [ ] Authoritative requirements for consent, calling hours, opt-out, collections, retention/deletion, and recording are reviewed; current local calling-hour assumptions are unverified.
- [ ] Legal, compliance, privacy, and security owners approve the actual design and operating policies.

## Identity, tools, and data

- [ ] Synthetic security tests pass; independent review verifies fail-closed behavior and customer-scoped CRM authorization.
- [ ] Real CRM schemas, auth, least privilege, timeouts, retries, idempotency, rate limits, audit, and failure modes validated in an approved test environment.
- [ ] Logs, traces, dashboards, transcripts, backups, access controls, retention and deletion reviewed; secret scanning passes.
- [ ] No Aadhaar, bank credentials, payment credentials, or unapproved customer data are collected.

## Agent and telephony

- [ ] Immutable Sarvam agent version identified; native evaluation suite passes agreed thresholds over repeated runs.
- [ ] Controlled test number and inbound telephony path verified by authorized operator; no campaign or outbound traffic without explicit approval.
- [ ] Real-device microphone/audio/interrupt/consent tests completed for every supported language; outcomes labeled MANUAL-TEST.
- [ ] Human transfer, failed transfer, callback, opt-out, silence, interruption, and unexpected disconnect tested end-to-end.

## Operations and launch

- [ ] Monitoring, alert thresholds, incident owner/on-call, troubleshooting, and runbook exercised.
- [ ] Rollback to last known-good immutable agent version and backend release rehearsed.
- [ ] Client acceptance and explicit launch authorization recorded.
