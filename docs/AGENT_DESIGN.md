# Agent design — Example Finance synthetic workflow

**Status:** Local project design template plus a platform-verified, test-only Sarvam agent (immutable version 2). No client discovery or deployment has occurred. The browser WebSocket is a simulator, not deployed telephony.

## State and gates

| State | Allowed behavior | Transition |
|---|---|---|
| `identity_check` | Consent handling, identity verification, human escalation | Successful CRM verification → `verified`; 3 failed attempts → escalation lock |
| `verified` | Customer-scoped status lookup, callback/outcome operations, escalation | Caller ends → call ends; backend error → safe fallback |
| consent pending | Play consent line; repeat unclear response once per current flow; do not process account tools | Explicit refusal ends without transcript storage; explicit consent continues |

The `ConversationEngine` supplies state-specific tools. `BFSIToolExecutor` and CRM independently enforce verification. Caller-grounding validation checks DOB and last four digits against current caller input. Status requests made before verification remain pending; once verified, server performs the required first-fixture-loan lookup even if the model omits the tool call.

## Tool and response rules

- Verify identity using only caller-supplied DOB and phone suffix; do not infer missing values.
- Get loan status only after verification; the local MOCK CRM resolves the first synthetic loan ordered by ID, not a business-defined “active” loan. A production CRM must implement the client's approved eligibility rule. Caller-supplied IDs remain CRM-scoped to the verified customer.
- Speak balances and dates only from successful CRM results; no payment claim unless a backend confirms it.
- Normalize dates server-side; ask the caller to restate unclear or ambiguous dates/identifiers.
- Refuse unsupported financial advice. Escalate disputes, complaints, uncertainty, and explicit human requests.
- On consent refusal, opt-out, or end request, stop account processing and end politely.
- If transfer fails, state that it failed; offer retry or end. Do not claim transfer success.

## Local prompt/provider boundary

Prompts live under `prompts/`; flow tool/state selection is in `flows/`. Faster-Whisper, Ollama, and Piper remain separate local prototype providers. They do not replace or run inside Sarvam Voice Agents.

## Sarvam platform evidence and current limit

Official references for later authenticated work: [Voice Agents introduction](https://docs.sarvam.ai/voice-agents/introduction), [overview](https://docs.sarvam.ai/voice-agents/overview), [MCP](https://docs.sarvam.ai/voice-agents/mcp), [HTTPS tools](https://docs.sarvam.ai/voice-agents/build/tools/https-tool), and [telephony deployment](https://docs.sarvam.ai/voice-agents/deploy/telephony).

The Sarvam MCP authenticated successfully in the current session. Agent `Example-Fin-1e33e491-23c6`, immutable version 2, uses a Hindi/English customer-care voice and a safety-only prompt for controlled evaluation. Native suite `01M7GEBN68HJ4HMEFC915CD2SY` covers nine synthetic safe-fallback scenarios; version 2 run `01M7GEP5A73RCSVF5APM4K4DVF` passed 9/9 and repeated run `01M7GERSSSB8AMAGJDS0TGJXEP` passed 18/18 (two executions per scenario). It intentionally has no account tools and explains that CRM, human routing, and callback are unavailable. The version is not connected to a phone or live customer.

The workspace had no custom integrations, stored secrets, telephony connections, verified numbers, or deployments when checked. Thus no Sarvam HTTPS CRM tool could be safely configured or exercised, and no inbound deployment could be prepared with a valid connection/endpoint. The caller must provide an authorized test CRM endpoint, least-privilege test credential through the approved secret store, and an authorized telephony connection/number before those steps. Do not infer endpoints or claim platform CRM/telephony integration from this local design. Full record: `docs/SARVAM_PLATFORM_EVIDENCE.md`.
