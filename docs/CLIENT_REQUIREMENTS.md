# Client requirements template — synthetic lender

**Status:** Project template only. No client discovery, customer acceptance, or production deployment has occurred.

## Business goal

Provide a respectful inbound/outbound EMI reminder assistant that can verify a caller, read loan status from an approved CRM, arrange a callback, or route the caller to a human. The local demo uses fictional lender **Example Finance** and seeded synthetic records only.

## Scope and assumptions

- Supported local flow: recording consent, identity check, EMI/loan status, callback request, human escalation, caller refusal, and end-of-call request.
- Local default language is English. Hindi-English code-switching requires language-specific ASR, prompts, and human review before acceptance; it is not verified here.
- No payment collection, payment confirmation, credit decision, collections promise, Aadhaar, bank credentials, or payment credentials.
- CRM, transfer, callbacks, and telephony are simulated/local prototype integrations.
- Calling hours, consent wording, recording retention, opt-out rules, and collections policy are unset pending client and authoritative policy review.

## Client discovery questions

Confirm account eligibility, permitted call direction, supported languages/accents, approved identity factors, data ownership, CRM source of truth, transfer destination, callback timezone and accepted time formats, consent/recording rules, retention/deletion, concurrency, service levels, and outage policy before implementation against client systems.

## Acceptance criteria for a real implementation

1. CRM owner approves schemas, least-privilege credentials, environments, rate limits, timeout, retries, idempotency, and audit fields.
2. Independent security review confirms that account data cannot be read before successful verification and caller-supplied identifiers remain customer-scoped.
3. Approved language and synthetic/consented audio test sets pass the agreed thresholds with denominators and exact agent versions recorded.
4. Consent refusal and opt-out terminate safely; disputes, complaints, uncertainty, and transfer failures have an approved human/callback route.
5. Monitoring, incident ownership, retention, rollback, and launch authorization are signed off by the client.

These criteria are proposed acceptance inputs, not received client requirements or approval.
