# Integration contract template — local prototype

**Status:** Simulated-client artifact. `app/crm.py` is a local MOCK CRM, not a production CRM. HTTP schemas below describe this repository only.

Sarvam Voice Agents version 2 is a separate test-only platform agent. It has no bound CRM tool. Do not point it at this local `localhost` service or treat this local API contract as an approved client CRM contract. See `docs/SARVAM_PLATFORM_EVIDENCE.md` for the missing endpoint/credential blocker.

## Local API

Base URL defaults to `CRM_URL=http://localhost:8001`. Requests use `X-API-Key`; verified data requests additionally use `X-Verified-Customer`. Keep credentials in environment/approved secret storage. Never log headers or key values.

| Operation | Request | Success | Failure / authorization |
|---|---|---|---|
| `POST /verify_identity` | `{customer_id,dob: YYYY-MM-DD,phone_last4}` | `{verified:boolean}` | `401` invalid API key; malformed values rejected by Pydantic |
| `GET /customers/{customer_id}` | no body | synthetic profile | Requires matching verified-customer header; otherwise `403` |
| `GET /loans/{loan_id}` | no body | customer-scoped synthetic loan | Requires matching verified-customer header; other customer's loan denied |
| `GET /customers/{customer_id}/loans/first` | no body | `{id,status,amount,due_date}` | Returns the first synthetic loan ordered by ID; requires verified-customer match; `404` if absent |
| `POST /schedule_callback` | `{customer_id,requested_at}` | `{scheduled:boolean}` | Requires verified-customer match; no real callback service |
| `POST /log_call_outcome` | `{customer_id,outcome}` | `{logged:boolean}` | Requires verified-customer match |
| `POST /escalate_to_human?customer_id=...` | query only | mock queued result | Not a real transfer |

## Local caller-to-service behavior

- CRM calls use a 3-second HTTP timeout. No automatic CRM retry is configured; identity/lookup failures fail closed. Tool loop is bounded to 5 model rounds.
- Identity DOB is normalized on the server from ISO or unambiguous English month/day/year. Ambiguous slash dates and invalid dates are rejected.
- DOB and phone suffix passed to `verify_identity` must match values in the current caller utterance. Schema-valid model guesses are rejected before CRM.
- Callback creation requires an explicit caller request plus a date, time, and timezone grounded in that caller utterance. Local parser accepts ISO/RFC3339 timezone-bearing timestamps and unambiguous English date/time; unresolved timezone or date ambiguity fails closed. Production must agree timezone and accepted formats with the client.
- Loan IDs supplied to tools must be caller-grounded or backend-resolved for the verified customer; arbitrary model-proposed IDs are ignored in favor of the active customer-scoped loan.
- Server-side first-fixture-loan lookup resolves a loan only within the verified customer. It does not implement a business definition of “active”; production CRM must supply an approved eligibility/status rule. Loan IDs supplied to direct lookup are still customer-scoped by CRM.
- Same-call identical state-changing tool calls replay the first result in memory. The CRM also accepts optional `X-Idempotency-Key` on callback/outcome/payment-link/escalation writes; keys and request hashes are persisted transactionally in an additive `idempotency_records` table. Reuse with a different operation/body returns `409`. Legacy callers without the header retain prior behavior.
- The local app generates a random call ID per WebSocket connection and hashes it with operation/body into the idempotency key. Reconnects receive a new ID, so cross-connection exactly-once delivery is not guaranteed; production must use a stable provider call/request ID.
- Migration/rollback: startup creates the new table with `CREATE TABLE IF NOT EXISTS`; existing customer, loan, callback, outcome, and payment rows are unchanged. Old and new app versions can read/write existing tables concurrently; old versions ignore the added table. Rollback is source-only and leaves the table/data intact; do not drop the table during rollback.
- Webhook receiver verifies timestamped HMAC-SHA256, a bounded replay window, and `X-Idempotency-Key`; sender retry behavior uses the same key. SQLite deduplication is local only.
- Stored call traces omit tool arguments and account/loan result payloads; raw audio is not stored. Transcripts are redacted, but redaction is not guaranteed to identify every sensitive value.
- `/metrics` exposes bounded-cardinality tool call outcomes and latency histograms; the local dashboard summarizes per-tool p50/p95 latency and error categories when trace timings exist.
- Local opt-out/“do not call” ends the current simulated call. No dialer or persistent suppression list exists; a production outbound service must consult and update the client's authoritative opt-out store before any future attempt.

## Production integration decisions still required

Agree authentication scheme, canonical error schema, CRM identity-proof semantics, request IDs, idempotency-key ownership/storage, retryable status codes, rate limits, circuit behavior, data minimization/retention, webhook timestamp skew, and telephony media/signature protocol with the real system owner. Do not transfer this prototype contract to a client system without review.

## Sarvam validation status

Sarvam MCP authentication and native platform tools (`end_interaction`, language change) were exercised. No custom CRM integration or HTTPS API tool was configured because no authorized external test endpoint or credential exists in the workspace. Therefore CRM authentication, HTTP schema compatibility, timeouts, retries, idempotency, and outage behavior have **not** been tested through Sarvam. Local tests cover only the simulated contract above.
