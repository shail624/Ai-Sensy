# PAR-AUTO-18 — Durable Task-Completed Wait

**Status:** Repository Implemented  
**Date:** 2026-08-23  
**Scope:** Resume a contact-scoped Automation Wait from the authoritative Task lifecycle

## Decision

The existing `Task completed` Wait choice is now a governed live event on the bounded Automation
paths introduced by PAR-AUTO-17. A supported event-backed run may pause for the same Contact's
future `task.completed` fact for 60 seconds to 30 days, then continue from the original receipt,
run and node checkpoints to a later approved internal effect.

The Task service remains the completion authority. Single-task and bulk completion write one
immutable Business Event inside the existing Task transaction, alongside Task state/history,
Contact Timeline and Audit evidence. A failure to append or project the fact rolls back the Task
mutation; there is no half-completed state. `lead.stage_changed` remains safe-test-only.

## Immutable completion cycle

Each completion fact is deterministic from organization, public Task ID and the pending Task row
revision. This makes retries converge while allowing a genuinely reopened Task to emit a distinct
fact when it is completed again. The event keeps internal Contact ownership for tenant-safe
matching and exposes only public Task ID, type, priority, completed status and completion revision.
Task title, description, completion note and other private text are not copied.

The existing Wait matcher enforces organization, Contact, event type, start time and deadline. A
completion for another Contact cannot resume the subscription. The immutable matched event UUID
is retained, and duplicate event/receipt/worker delivery converges on the existing Wait attempt and
downstream checkpoints.

## Dispatch and recovery

Task completion returns the original paused receipt to `received` in the same transaction. The
existing minute receipt heartbeat claims it and hands it to the idempotent Automation consumer. It
also remains the recovery authority for post-commit enqueue gaps and for the Wait timeout path; no
broker-owned long timer, new queue or second task lifecycle authority is introduced.

## API and UI boundary

No route, permission, migration, queue, provider configuration or customer-send authority is
added. Migration head remains `0048_automation_wait_subscriptions` (**49 revisions**) and OpenAPI
remains **211 paths**. The builder now truthfully describes both Message received and Task
completed as live same-customer Wait choices. Lead stage changed remains test-only.

## Validation

- Focused completion-cycle/live-Wait contract: **4/4 passed**.
- Task and Wait regression: **53/53 passed**.
- Combined Automation/Task/API/Notification/KYC regression: **130/130 passed**.
- Focused Automation UI: **18/18 passed**; complete frontend **40 files / 828 tests**.
- Static profile: **6/6 passed**; strict mypy covers **305 source files**.
- OpenAPI remains **211 paths**; migration head remains `0048` (**49 revisions**).
- Production build: PASS; AutomationPage **42.56 kB / 10.78 kB gzip**.
- Applicable backend: **1501 passed / 6 MySQL skips / 1 known Redis-only deselection** in
  **377.10s**. The Redis-only case was separately reproduced unchanged in **65.28s**.
- Completion: Automation remains **99%**; Lead-stage projection, general branching,
  external/customer actions, recipient/team routing and operational reconciliation remain pending.
