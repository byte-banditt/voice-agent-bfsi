# Test plan

**Classification:** Deterministic repository tests and synthetic local evaluations only unless individually labeled otherwise.

## Deterministic gates

Run `python -m pytest -ra`. Coverage includes caller-grounded identity arguments, schema rejection, state-gated tools, third-party access rejection, date normalization, three-attempt lockout, CRM unavailability behavior, duplicate state-changing calls/webhooks, redaction, consent, callback, escalation failure, browser route, and WebSocket protocol sequencing.

### Required case map

| Required case | Deterministic evidence |
|---|---|
| Successful / failed verification and 3-attempt limit | `test_identity_gate_authorizes_only_verified_customer`; `test_identity_gate_limits_attempts_and_protects_data`; `test_third_failed_identity_attempt_locks_verification_and_escalates`; scenario `wrong_identity_three_attempts` |
| Ambiguous/invalid DOB; hallucinated plausible identity; phone suffix confused with DOB digits | `test_spoken_english_date_of_birth_normalizes_to_crm_format`; `test_plausible_but_invented_identity_values_never_reach_executor`; `test_phone_suffix_cannot_be_inferred_from_a_nearby_dob` |
| Status before verification; correct and cross-customer lookup | `test_unverified_status_request_cannot_leak_categorical_status`; `test_server_requires_status_lookup_when_verified_caller_asks`; CRM first-fixture-loan and cross-account assertions |
| CRM timeout/unavailable and invalid arguments | scenarios `crm_timeout`, `crm_server_error`, `malformed_tool_arguments`; executor rejects unverified and invalid dates before CRM |
| Duplicate tool request and duplicate webhook | `test_repeated_state_change_tool_is_not_executed_twice`; scenario `duplicate_webhook` |
| Consent refusal and opt-out | `test_declined_consent_exits_without_persisting_transcript`; scenario `consent_withdrawal`; end request test |
| Callback and escalation, including failed transfer and negation | scenario `schedule_callback`; `test_callback_date_and_time_must_come_from_caller`; `test_negated_callback_and_payment_link_requests_do_not_execute`; CRM idempotency replay/conflict assertions; `test_payment_dispute_forces_human_escalation`; `test_failed_human_transfer_is_not_reported_as_success` |
| Interruption, silence, unclear request | scenarios `barge_in_mid_sentence`, `long_silence`; `test_unsupported_financial_advice_and_unclear_requests_are_bounded` |
| Hindi-English code-switch | Fixed test verifies fail-safe refusal. Hindi-English service support is **NOT IMPLEMENTED / NOT EVALUATED**; do not list it as a supported language. |
| Complaint, payment dispute, unsupported advice, grounding challenge | `test_payment_dispute_forces_human_escalation`; `test_unsupported_financial_advice_and_unclear_requests_are_bounded`; scenario `grounding_violation`; partial payment scenario |

## Synthetic scenario suite

`tools/evaluate_scenarios.py` has 20 named scenarios, including success, 3 failed verification attempts, unverified and third-party access, prompt injection, malformed/ungrounded identity values, made-up amount/date grounding, CRM timeout/500, consent refusal, callback, duplicate webhook, interruption, silence, and empty ASR. Run with `--mode fake` for deterministic scripted provider behavior or `--mode ollama --model qwen3:1.7b` for stochastic local model behavior. The tool records run count, scenario-level numerator/denominator, model, tool accuracy, latency, and failure reason in its JSON artifact.

The `grounding_violation` scenario is an adversarial unsafe-output challenge: success means unsupported values never reach the spoken reply, either because `enforce_grounding` replaces them and emits `grounding_violation`, or because the model safely refuses before the guard intervenes. A guardrail event alone is not evidence of a spoken violation. The malformed-argument case passes only when ungrounded/schema-invalid inputs are rejected before CRM and no data are disclosed.

## Manual and platform evaluations

- Physical browser microphone/speaker smoke: **NOT EXECUTED**. WebSocket route tests do not prove hardware permissions, acoustic feedback, or real-device timing.
- Sarvam native Tests: **PLATFORM-VERIFIED** against immutable agent version 2. Suite `01M7GEBN68HJ4HMEFC915CD2SY`, 9 scenarios × 2 executions: run `01M7GERSSSB8AMAGJDS0TGJXEP`, **18/18 evaluator passes**. A single-run suite also completed 9/9 (`01M7GEP5A73RCSVF5APM4K4DVF`). These are synthetic text simulations, not audio or phone calls; the judge is not a security proof. A first baseline run exposed that the evaluator missed a repeated caller name; the prompt and expected behavior were tightened, and the final repeated run passed.
- Sarvam tool execution: native text simulations exercised `end_interaction` on refusal/opt-out and `change_output_language` on an explicit language change. CRM tool execution and external timeout/retry/failure behavior were **NOT EXECUTED** because there is no connected CRM or authorized endpoint/credential.
- Sarvam call analytics/traces and inbound telephony: **NOT EXECUTED**; no telephony connection, verified phone number, deployment, or real call exists.
- No real calls, phone numbers, customer records, or audio recordings were used.
- No reference-labeled real audio exists; no real-audio WER/CER claim is made. Existing WER evidence uses synthetic Piper speech only.

## Evaluation dimensions and limits

Measure task completion, verification order, unauthorized operations/disclosure, tool selection/arguments, result-grounded amount/date speech, escalation/refusal behavior, tool error/latency, and end-to-end timing. Synthetic metrics cannot establish real callers' ASR quality, language support, consent validity, or service reliability. Repeat stochastic tests with exact agent/model version and retain every failure.
