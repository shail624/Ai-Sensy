# PAR-REP-02 — Scheduled Analytics Reports

**Status:** Repository Implemented  
**Date:** 2026-08-24  
**Scope:** Personal daily, weekly and monthly delivery of existing Analytics report exports

## Decision

A report schedule is a durable instruction to create an ordinary analytics export at a future
local-time occurrence. It does not create a second report, queue, artifact or download system.
The heartbeat claims a due database row, advances its next occurrence, and calls the existing
`ExportService.start_report`; the normal export worker, storage provider, expiry policy, signed
link and personal Download Center own everything after that handoff.

Schedule management requires both `analytics:export` and `analytics:executive`. Schedules are
personal inside the tenant: operators can list, edit, pause, resume and delete only their own rows,
with optimistic concurrency on every update/delete. A user may hold at most 25 schedules and names
are case-insensitively unique per owner.

## Schedule contract

- fixed report families: messages, failures, campaigns, conversations, tasks, customers and costs;
- fixed scheduled formats: PDF, Excel and CSV;
- fixed ranges: yesterday, last 7/30 days, this/last month and this quarter;
- daily, weekly or monthly cadence in an IANA timezone and `HH:MM` local time;
- weekly weekday or monthly day 1–28, with impossible mixed shapes rejected;
- active/paused state, last occurrence, precomputed UTC next occurrence and row version; and
- organization/user scope, a 25-row personal ceiling, audit evidence and deterministic validation.

The shared Celery Beat heartbeat runs once per minute. `SELECT … FOR UPDATE SKIP LOCKED` claims one
due row per transaction, preventing overlapping ticks from exporting the same occurrence. A
deactivated/deleted owner or revoked permission disables the schedule instead of producing an
unauthorized artifact. Recurrences realign from the current time rather than replaying every missed
slot after downtime.

## Delivery and notification

Scheduled occurrences retain their schedule id/name and due slot in reserved export metadata.
When the normal export worker reaches `ready`, it emits one idempotent `report_ready` Notification
Center item keyed by the export id. Its action opens the Analytics-ready Download Center filter.
The artifact is still personal, expiring and permission-scoped; notification delivery does not
grant access or hold a second URL.

## Persistence and rollback

Migration `0050_scheduled_analytics_reports` adds `report_schedules` and widens the existing
notification-type constraint with `report_ready`. Downgrade removes those notifications, restores
the legacy constraint and drops the schedule table. The migration graph remains one linear head at
**51 revisions**. OpenAPI grows from **212 to 214 paths** for the collection and item schedule
resources; generated TypeScript and the 30-task image inventory are synchronized.

## UI

Analytics → Export center now contains an original responsive Scheduled reports workspace with:

- complete loading, error, empty and permission-hidden states;
- an adaptive create/edit form for report, format, range, grouping, cadence, local time and zone;
- active/paused badges, readable recurrence and next-run facts;
- pause/resume and optimistic full-edit controls;
- inline two-step deletion instead of a destructive one-click action; and
- a direct Download Center action.

## Validation

- Scheduled-report API/service/worker/notification regression: **5/5 passed**.
- Combined Analytics, Notification Center, smoke, contract and quality-tool backend selection:
  **71/71 passed**.
- Analytics UI: **34/34 passed**, including permission gating and generated-client creation.
- Complete backend: **1530 passed / 6 MySQL-only skipped / 0 failed in 425.43s**.
- Complete frontend: **41 files / 841 tests passed**.
- Static profile: **6/6 passed**; strict mypy covers **309 source files**; OpenAPI drift passes.
- Frontend lint, TypeScript, browser-test types and Vite **8.2.2** production build pass.
- SQLite migration upgrade/downgrade/re-upgrade and single-head checks pass.
- A disposable migrated local app booted through the in-app browser with no console warnings/errors;
  authenticated representative-data visual/device acceptance remains target-host work.
- Docker/security release rerun remains pending; PAR-AUTO-22 at **23/23 in 685.9s** remains the last
  complete release certificate and is not attributed to this changed tree.

Executive Reports advance **35% → 50%**, Download Center **70% → 72%**, Notifications **85% →
86%**, and API **89% → 90%**. The canonical 31-module mean advances **70.0% → 70.6%**; the median
remains **82%**. New revenue/ROI/productivity/workload/SLA/case-outcome projections, transcript/
campaign/Scan/generated-document artifact families, optional external delivery channels and host
acceptance remain pending.
