# Operations runbook template

**Scope:** Local prototype operation and a checklist for a future client deployment. No production system is represented.

## Triage a call

1. Filter by call ID and time window in the local dashboard/SQLite traces. Use only redacted trace material; do not copy raw caller data into tickets.
2. Check `/health`, provider mode, model/prompt version, consent state, failure tags, stage timing percentiles, tool success counts, and guardrail events.
3. For no/slow response, inspect ASR, LLM/tool loop, CRM, and TTS stage timings separately. Current structured tool loop is non-streaming; a reported first-sentence time is not LLM first-token latency.
4. For CRM errors/timeouts, verify local CRM health and synthetic credentials in environment configuration. Do not echo credentials or headers.
5. For disclosure/identity concerns, stop the simulated flow, preserve only sanitized trace IDs, reproduce with synthetic fixtures, and verify both `ConversationEngine` and CRM boundary.
6. For missing variables or incorrect response, compare tool arguments/results before persistence (synthetic only), flow state, prompt version, and redacted stored trace. Never restore account payloads to logs for convenience.
7. For failed handoff or unexpected termination, treat the handoff as failed unless the backend confirms success. Offer retry/end; record an operator ticket with no PII.

## Mitigation and rollback

- Local: stop the agent process; leave CRM fixtures and additive `idempotency_records` rows intact; restore the prior reviewed source revision only through normal Git review. The new table is created with `IF NOT EXISTS`, old code ignores it, and rollback does not drop it.
- Current Sarvam test agent: `Example-Fin-1e33e491-23c6`, immutable version 2, is not deployed and has no connected CRM or phone. Do not interpret its evaluation run as call monitoring evidence.
- When an authorized Sarvam deployment exists: identify the interaction from the failed-attempt report, inspect `analytics(operation='interaction', id='<YYYYMMDD/identifier>', params={app_id, include_trace:true})`, then compare the pinned app/version, transcript turns, lifecycle events, variables and tool calls. For latency/errors, narrow `analytics(operation='report')` to a UTC window and use `tool_latency`, `tool_error_types`, `tool_table`, and `tool_interactions` for the named tool. Use `analytics(operation='chat')` only for a saved text replay; it is not an audio recording.
- For a wrong response, preserve the immutable version and trace reference, reproduce against a synthetic scenario, fix the draft, rerun the pinned native suite, and commit a new version. Rollback by patching the existing deployment to its prior committed `app_version`; do not delete/recreate the deployment, which releases its numbers. Verify the exact MCP operation and deployment state before any rollback.
- For CRM/tool timeout or failure, inspect the tool error category and latency, verify the integration binding and credential reference without exposing values, and fail closed to the approved human/callback fallback. Never retry a non-idempotent write until its idempotency behavior is confirmed.
- For a handoff or unexpected termination, inspect lifecycle events and telephony connection/deployment state. If no controlled human route exists, report that the handoff is unavailable; do not claim success.
- If identity gate, consent, grounding, or CRM scope is uncertain, disable the affected account-specific tools and route callers to approved human support.

## Incident record

Record incident ID, UTC window, call IDs, app/agent/model/prompt version, affected stage/tool, error category, impact count, synthetic reproducer, mitigation, owner, and follow-up. Keep secrets and raw sensitive values out of logs/tickets.
