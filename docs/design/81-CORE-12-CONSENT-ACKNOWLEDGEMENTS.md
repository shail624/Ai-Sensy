# CORE-12 — consent keyword acknowledgements

## Decision

The existing inbound consent-keyword evaluator may optionally accept one acknowledgement for an
actual opt-in or opt-out transition. The contact's consent change, audit record, contact timeline
event, inbound message and durable outbound acknowledgement are committed together. Provider
delivery occurs only after that commit, so a delivery failure cannot reverse or hide the recorded
customer choice.

## Scope boundary

- Add independently configurable opt-in and opt-out acknowledgement text to the validated inbox
  operations policy.
- Acknowledge only a fresh inbound text message that causes a real consent-state transition.
- Reuse the existing automatic-reply event ledger and source-message idempotency authority.
- Permit an opted-out contact to receive only its own withdrawal acknowledgement; no other system
  or operator send bypasses the consent guard.
- Expose the controls in the existing Application settings surface and generated API contract.

## Deliberately unchanged

This milestone adds no blocked state, outbound webhook, campaign behavior, template behavior,
provider-specific setting, migration or new event table. The independent blocked-versus-consent
model decision remains outside this milestone. Welcome and off-hours replies keep their existing
freshness, window and rate-limit behavior.

## Failure and duplicate semantics

An acknowledgement is accepted only after the consent mutation has been applied in the inbound
transaction. A duplicate webhook delivery recovers the same accepted reply rather than creating a
second message. Provider dispatch starts after commit; a later send failure changes only delivery
status and never rolls back consent.

## Acceptance evidence

- Backend coverage verifies validated settings, actual transition, withdrawal acknowledgement,
  renewed opt-in acknowledgement and duplicate recovery.
- Frontend coverage verifies the settings controls and generated request shape.
- OpenAPI and generated TypeScript remain synchronized at 247 paths.
- Static analysis, full test suites and production build results are recorded in
  `VALIDATION_RESULTS.md`.
