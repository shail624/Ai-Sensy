# PAR-AUTO-12 — Bounded Sequential Effect Runtime

**Status:** Repository Implemented  
**Date:** 2026-08-22  
**Scope:** One inbound trigger executes a bounded linear sequence of existing internal effects

## Decision

The live inbound runtime now accepts one `message.received` Trigger, one optional privacy-safe
Condition, and one to four distinct supported effects connected in a single line. The supported
effects remain Human handoff, Create task, Apply tag, Remove tag, Assignment and internal
Notification. Their published edge order is their execution order.

This is a bounded sequence, not a general workflow engine. A path with branching, more than four
effects, repeated effect kinds, multiple conditions, delays, waits, approval/campaign/webhook
nodes, unsupported actions or disconnected nodes fails closed before any business effect begins.

## Durable checkpoints and replay

Every effect keeps its existing domain authority and node-scoped Automation attempt. A completed
node is a durable checkpoint. If a worker is interrupted after earlier effects commit, task retry
resumes from the first incomplete node instead of replaying completed work.

The existing effect idempotency contracts remain authoritative: handoff uses its Business Event
command, Create task uses its receipt command hash, tag changes converge on the Contact/Tag
association, Assignment preserves an existing owner, and Notification uses its receipt/node dedup
key. The runtime does not add a parallel effect ledger, queue, permission, route or transaction
coordinator.

## Condition behavior and operator contract

The optional approved Condition controls the entire sequence. A false result records every effect
as skipped and applies none of them. A true result executes the effects in connected order. The
builder explains the one-to-four distinct-effect limit and the fail-closed boundary; safe test mode
continues to simulate all nodes.

## Explicit boundary

General branching, repeated same-kind actions, more than four effects, per-effect conditions,
waits/delays, other live event consumers, recipient/team notification routing, campaign/webhook/
customer-message effects, capacity/skill routing and complete retry/DLQ/reconciliation operations
remain future PAR-AUTO scope. No provider or customer send is introduced.

## Validation

- Sequential live runtime, replay, condition and graph-boundary checks: **19/19 passed**.
- Automation plus Tasks, Tags, Notifications and migration regression: **88/88 passed**.
- Frontend Automation: **12/12 passed**; complete frontend **40 files / 822 tests**.
- Static profile: **6/6 passed**; strict mypy covers **305 source files**.
- OpenAPI remains **211 paths**; migration head remains `0046` (**47 revisions**).
- Production build: PASS; AutomationPage **40.17 kB / 10.23 kB gzip**.
- Canonical backend: **1482 passed / 6 MySQL skips / 1 known Redis-only failure** in **465.36s**.
- Applicable backend: **1482 passed / 6 MySQL skips / 1 Redis-only deselection** in **396.20s**.
- Completion: Automation advances **96% → 98%**.
