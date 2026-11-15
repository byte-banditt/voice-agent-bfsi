# Sarvam Voice Agents platform evidence

**Classification:** Platform-verified configuration and synthetic text evaluation only. No client, production, CRM, phone, or real-call evidence.

## Authentication and workspace inventory

On 2026-11-15 the authenticated Sarvam Voice Agents MCP responded successfully to read operations (`agents.list`, template/voice reads, integration/secret inventory, and telephony inventory). No secret values were read. This confirms the current MCP session is authenticated; it does not establish that CRM or telephony credentials exist.

The workspace inventory returned zero custom integrations, zero stored secrets, zero telephony connections, zero verified numbers, and zero inbound deployments. No CRM endpoint or credential was supplied in the workspace. No phone number was exposed or used.

## Agent and version

- Agent: `Example-Fin-1e33e491-23c6`
- Name: `Example Finance EMI Reminder — Test Only (CRM Pending)`
- Immutable version: **2** (committed through the documented Voice Agents MCP lifecycle)
- Channel: v2v configuration; Hindi initial language, English also enabled
- Voice: Sarvam customer-care catalogue voice, `01a0cf16-a571-7451-a420-be5f97e71f71`
- Prompt: controlled-test safe fallback. It discloses that no CRM, verification service, callback scheduler, or human route is connected; it does not solicit caller data or claim account actions. The platform's default caller name and post-call summary variables were removed. The default Sarvam-branded opening was replaced. Voicemail detection is off to avoid the inherited false callback promise.
- Not deployed. No number is bound. The platform advanced its editable draft to version 3 after committing version 2; evaluation below is pinned to immutable version 2.

## Native evaluation

Suite `01M7GEBN68HJ4HMEFC915CD2SY`, **9 scenarios**, pinned to agent version 2:

| Run | Frequency | Executions | Passes | Result |
|---|---:|---:|---:|---|
| `01M7GEP5A73RCSVF5APM4K4DVF` | 1 | 9 | 9 | Completed |
| `01M7GERSSSB8AMAGJDS0TGJXEP` | 2 | 18 | 18 | Completed |

Scenarios cover an account-status request with no CRM, consent refusal, opt-out, volunteered identity details, complaint/payment dispute, callback request, unsupported financial advice, explicit Hindi-to-English switch, and an unclear payment question. This is a platform judge's transcript evaluation over synthetic text personas; it does not prove safety, audio quality, real language recognition, call completion, or backend reliability.

The first version-1 run revealed a gap: the agent repeated a synthetic caller name even though the evaluator passed the scenario. The prompt and expected behavior were tightened. A focused draft run and the final version-2 suite then passed without repeating the name or loan identifier in the tested transcript. This is a useful regression observation, not proof that every variation is safe.

Native text interactions exercised `end_interaction` for refusal/opt-out and `change_output_language` for the explicit language request. No CRM/API tool was configured or invoked. Platform eval results expose no external CRM timeout, retry, or outage test because no CRM integration is connected.

## Telephony and CRM blockers

No inbound deployment could be created: the platform reported no telephony connection or onboarded endpoint, and `configure_deployment` requires an existing connection and its endpoint number. No test call was placed. No usage from telephony calls was incurred.

No authorized test CRM can be integrated until its owner supplies an externally reachable test endpoint and approved least-privilege authentication through the Sarvam secret store (or another documented platform auth path). A local `localhost` MOCK CRM is not reachable by Sarvam and is not a production or platform integration. The current platform agent therefore has no identity verification or account lookup and must remain test-only.

## Validation boundary

- **Authentication:** Sarvam MCP read operations succeeded; no credential values were read or changed.
- **Platform tool execution:** `end_interaction` and `change_output_language` were observed in native synthetic runs.
- **Local prototype only:** the repository test suite exercises synthetic MOCK CRM timeouts/unavailability, bounded tool-loop behavior, idempotency, webhook HMAC/replay protection, and failure fallbacks. See `docs/RESULTS.md` and `docs/INTEGRATION_CONTRACT.md`.
- **Not validated against Sarvam CRM:** credentialed HTTP requests, response schemas, backend timeout handling, HTTP retries, CRM idempotency, webhook authentication, or CRM failure recovery.
- **Not validated against telephony:** inbound connection, caller audio, interruption/silence on a real call, call analytics, latency, handoff, or unexpected disconnect.

## Required before CRM/telephony integration

1. Supply the authorized test CRM base URL, API contract, test-only identity/loan fixtures, rate/timeout policy, and credential delivery through the approved secret manager. Do not send secrets in this repository or chat.
2. Provision or connect an authorized telephony provider account, onboard the controlled test number, and identify the exact connection and endpoint. This authorization permits preparing a binding; any real phone call still requires a separate explicit go-ahead.
3. Confirm any human transfer destination and approved consent/retention/calling policy. These are not configured or inferred here.
4. Configure reviewed HTTPS tools with least privilege, then test success, malformed arguments, authentication failure, timeout, retry bounds, duplicate requests, and backend outage against synthetic CRM data. Only then create an inbound deployment pinned to an immutable agent version.
