# PAR-AUTO-16 — Durable Live Schedule

**Status:** Repository Implemented  
**Date:** 2026-08-23  
**Scope:** Restart-safe, organization-timezone Automation schedule execution

## Decision

The existing five-field cron Schedule trigger is now a fourth bounded live Automation trigger.
Publishing a clean immutable version projects its next occurrence to `AutomationFlow.next_run_at`
as naive UTC, interpreted from the organization's IANA timezone. Disabling clears that projection;
enabling and republishing recompute it from the active immutable version.

The database is the schedule. Celery Beat supplies only a one-minute heartbeat and never owns a
flow's cron. The due query uses the indexed `(status, next_run_at)` projection, requires a clean
enabled publication and active organization, row-locks with `SKIP LOCKED`, orders deterministically
and obeys the shared scheduler scan limit.

## Exactly-once slot projection

Each claimed occurrence gets a deterministic UUID from organization, flow, immutable version and
scheduled UTC slot. One immutable `schedule` Business Event and one exact flow/version receipt are
committed together with advancement to the first future cron occurrence. Overlapping ticks cannot
claim the same row; retries converge on the event/receipt uniqueness contracts. If enqueueing fails
after commit, the existing stale-receipt recovery scanner re-dispatches the durable receipt.

Missed recurring occurrences are not replayed as a burst. One due fact is emitted for the stored
slot and the projection realigns after the current time, matching the existing campaign scheduler's
bounded catch-up policy.

## Safe live effect boundary

A live Schedule path is `Trigger → optional Delay → Notification`. Notification is delivered once
to the active eligible publisher through the existing Notification Center with no Contact link.
Conditions, Tasks, tags, Assignment, Handoff, Wait, webhook, campaign and customer-message effects
fail closed before any business effect. Safe test mode remains unchanged and can simulate the full
typed graph.

## API and UI

Malformed cron expressions are rejected by the typed request contract. Automation responses expose
`next_run_at`; the builder states that the cron uses organization timezone, shows the next live run,
and truthfully limits Schedule to one workspace-only Notification with one optional Delay.

## Migration

`0047_automation_schedule_due` additively adds nullable `automation_flows.next_run_at` and
`ix_automation_flows_schedule_due`. Upgrade/downgrade/re-upgrade is covered. No route, permission,
queue, provider configuration or customer-send authority is added.

## Validation

- Schedule projection/runtime/dispatcher: **4/4 passed**.
- Combined Automation definition/live runtime: **42/42 passed**.
- Wider Automation/Inbox/Tasks/Tags/Notifications regression: **222/222 passed**.
- Focused Automation UI: **16/16 passed**; complete frontend **40 files / 826 tests**.
- Static profile: **6/6 passed**; strict mypy covers **305 source files**.
- OpenAPI remains **211 paths**; migration head is `0047` (**48 revisions**).
- Production build: PASS; AutomationPage **41.90 kB / 10.62 kB gzip**.
- Applicable backend: **1496 passed / 6 MySQL skips / 1 Redis-only deselection** in **376.13s**.
- Completion: Automation remains **99%**; general branching, Wait-for-event, external/customer
  actions and operational reconciliation remain pending.
