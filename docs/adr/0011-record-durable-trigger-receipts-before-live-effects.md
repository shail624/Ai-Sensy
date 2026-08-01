# ADR-0011 — Record durable trigger receipts before live effects

- **Status:** Accepted — 2026-07-30
- **Scope:** MD5 Phase 2C business-event ingress and automation trigger receipts
- **Runtime/API/schema change:** additive ledger, receipt projection and read route; no action execution

## Context

Phase 2B proves that a pinned graph can run deterministically in side-effect-free test mode. Live
automation must next prove where triggers came from and which immutable publication matched them.
Calling a flow directly from contact, webhook or campaign code would couple publishers to automation,
lose replay evidence and conflict with the durable-first Domain Event Bus in Design Book 06 §47.

Enabling internal or customer-facing actions in the same change would also make trigger-ingress
correctness difficult to isolate. The repository therefore needs one reversible receipt milestone
before a consumer may attach business effects.

## Decision

- Real business facts are appended to the frozen `business_events` envelope from Design Book 03
  §21. The ledger is immutable, versioned, tenant-scoped and contains no direct update/delete path.
- `contact.created` is the first additive taxonomy entry. API creation, queued import and system
  conversation/contact creation all use the same recorder inside their existing transaction.
- Each enabled published flow whose immutable trigger is exactly `contact.created` receives one
  `automation_trigger_receipts` row. `(flow, version, event UUID)` is unique, so replay cannot create
  a second receipt.
- Disabled flows, drafts, dirty unpublished changes, schedules and other event types do not match.
- Receipt history is permission-scoped and read-only in the existing automation API and builder.
- No receipt starts a run or invokes a task, tag, assignment, notification, webhook, campaign,
  provider, approval, handoff or send. Those remain separate governed milestones.

## Consequences

- Trigger provenance and replay identity exist before live effects, and publishers depend only on
  the event recorder rather than the automation runtime.
- Contact creation gains one append-only ledger write plus receipt fan-out in its existing database
  transaction. A failure rolls back the contact, timeline, audit, event and receipts together.
- Only `contact.created` is claimed as live ingress. Other typed triggers remain authorable and
  testable but visibly have no real receipt until their publisher contract is implemented.
- Future consumers may claim receipts and create live runs without changing contact publishers.

## Rejected alternatives

- **Call automation directly after contact commit:** not durable, replayable or decoupled.
- **Start actions immediately:** combines trigger and effect correctness and weakens rollback safety.
- **Reuse `contact_events`:** it is a customer-timeline projection, not the enterprise event ledger.
- **Expose a public event-injection API:** would let callers manufacture internal business facts.
