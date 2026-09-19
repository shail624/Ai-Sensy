# PAR-AUTO-14 — Contact Created Live Consumer and Receipt Recovery

**Status:** Repository Implemented  
**Date:** 2026-08-23  
**Scope:** Event-safe Contact Created effects and bounded recovery of durable Automation receipts

## Decision

The existing `contact.created` Business Event receipt is no longer evidence-only. A published
Contact Created Trigger may execute Apply tag, Remove tag and internal Notification through the
same domain services used by the proven Message Received path. The approved Condition may inspect
`payload.source` or `payload.opt_in_status`, and one existing durable Delay may pause the connected
sequence.

This event does not guarantee a Conversation. Human handoff, Create task and Assignment therefore
fail closed before any effect begins. Message Received retains its existing six-effect boundary;
other trigger event types remain safe-test-only.

## Durable receipt dispatcher

A once-per-minute task on the existing `scheduler.tick` queue row-locks a bounded batch of receipts
that are either newly received or have remained processing beyond the recovery lease. New rows move
to processing before dispatch. Stale rows retain their old processing timestamp so the consumer can
recognize recovery rather than concurrent work. Each handoff uses the receipt public ID as the
stable task ID and targets the existing `automation.run` consumer.

The consumer, run attempts and domain services remain the idempotency authorities. No new queue,
table or parallel workflow state is introduced.

## Delay ownership

A receipt paused at a durable Delay stores no processing lease. The general scanner intentionally
excludes that row because its already-scheduled Automation task owns the resume deadline. This
prevents minute-by-minute redispatch while preserving the same early-delivery and checkpoint
behavior proved in PAR-AUTO-13.

## Explicit boundary

General branching, multiple conditions, Wait-for-event subscriptions/timeouts, further event
consumers, campaign/webhook/customer-message executors, recipient/team routing, capacity/skill
routing and complete operational retry/DLQ/reconciliation UI remain future PAR-AUTO scope. This
slice adds no migration, API route, permission, provider call or customer send.

## Validation

- Contact Created live runtime, condition, fail-closed and dispatcher checks: **26/26 passed**.
- Trigger, scheduler and runtime selection: **35/35 passed**.
- Wider Automation, Tasks, Tags and Notifications regression: **175/175 passed**.
- Frontend Automation: **14/14 passed**; complete frontend **40 files / 824 tests**.
- Static profile: **6/6 passed**; strict mypy covers **305 source files**.
- OpenAPI remains **211 paths**; migration head remains `0046` (**47 revisions**).
- Production build: PASS; AutomationPage **40.93 kB / 10.39 kB gzip**.
- Canonical execution: **1489 passed / 6 MySQL skips / 1 known Redis-only failure**.
- Applicable backend: **1489 passed / 6 MySQL skips / 1 Redis-only deselection** in **217.62s**.
- Completion: Automation remains **99%** while its live-event evidence expands.
