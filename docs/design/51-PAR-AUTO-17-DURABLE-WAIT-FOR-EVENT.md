# PAR-AUTO-17 — Durable Wait for Event

**Status:** Repository Implemented  
**Date:** 2026-08-23  
**Scope:** Restart-safe, contact-scoped Automation pause/resume on a future inbound message

## Decision

The existing Wait for event builder node is now a bounded live checkpoint on event-backed
Automation paths. One Wait may subscribe to the same Contact's future `message.received` fact for
60 seconds to 30 days and must be followed by at least one already-approved internal effect.
`lead.stage_changed` and `task.completed` remain safe-test-only because they do not yet have the
required immutable Business Event projection.

Schedule cannot Wait because it carries no Contact lineage. Missing timeouts, terminal Wait nodes,
multiple Waits, unavailable event types, branches and otherwise unsupported live graphs fail closed
before any business effect.

## Durable subscription and matching

Migration `0048_automation_wait_subscriptions` adds one tenant-owned subscription per run/node. It
pins the original trigger receipt and Contact, expected event type, start/deadline, state and optional
matched Business Event UUID. Indexed match and timeout projections are bounded and row-locked with
`SKIP LOCKED`.

When the runtime reaches the node it creates one running step attempt and one `waiting`
subscription, clears the receipt's processing lease and marks the run `retrying`. A future immutable
Business Event may resolve only subscriptions with the same organization, Contact and event type,
after their start and before their deadline. The original receipt returns to `received`; its normal
idempotent consumer resumes the same pinned run, completes the Wait attempt as `matched`, then
continues from existing checkpoints.

The inbound message path can return the resumed receipt immediately. If enqueueing fails, the
existing minute receipt scanner recovers it. Duplicate event delivery, projection or worker delivery
converges on the same subscription, attempt and downstream effect evidence.

## Timeout and recovery

The existing minute receipt heartbeat also row-locks due `waiting` subscriptions. It marks them
`timed_out`, releases their original paused receipt and claims that receipt through the same bounded
dispatcher transaction. The runtime records the timeout outcome on the Wait attempt and continues
to the later internal effect. There is no broker-owned long timer, second queue or ephemeral
in-memory subscription authority.

## API and UI boundary

No route, permission, queue, provider configuration or customer-send authority is added. OpenAPI
remains **211 paths**. The builder now labels Wait as a live contract, explains same-customer
matching, requires the 1-minute-to-30-day timeout and truthfully identifies the two test-only Wait
events.

## Validation

- Wait event/timeout/isolation/fail-closed checks: **3/3 passed**.
- Combined Automation/API/handoff/Schedule/migration regression: **55/55 passed**.
- Wider Inbox/message/provider/Task regression: **112/112 passed**.
- Focused Automation UI: **17/17 passed**; complete frontend **40 files / 827 tests**.
- Static profile: **6/6 passed**; strict mypy covers **305 source files**.
- OpenAPI remains **211 paths**; migration head is `0048` (**49 revisions**).
- Production build: PASS; AutomationPage **42.50 kB / 10.77 kB gzip**.
- Applicable backend: **1499 passed / 6 MySQL skips / 1 known Redis-only deselection** in
  **400.25s**; the final temporal edge rerun passes **3/3**.
- Completion: Automation remains **99%**; general branching, additional wait/event projections,
  external/customer actions, recipient/team routing and operational reconciliation remain pending.
