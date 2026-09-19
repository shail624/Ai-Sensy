# PAR-REP-04 — Team Productivity and Current Workload

## Status

`REPOSITORY IMPLEMENTED` on 2026-08-24. Target-host representative-data review, Docker/security
release rerun and production commissioning remain pending; this milestone does not claim
`Production Ready`.

## Authority and formula boundary

Team productivity and pending workload use two deliberately different data shapes:

- historical productivity is a **flow** derived from immutable conversation/task events through
  the existing Analytics rollups; and
- current workload is a **stock** read from indexed, tenant-scoped Conversation and Task tables at
  one `as_of` moment.

The stock snapshot is never folded into hourly/daily Analytics totals. Adding “open work at 09:00”
to “open work at 10:00” would double-count the same pending item, so the API and UI explicitly label
the snapshot time and keep it outside the rollup pipeline.

Current workload definitions are exact:

- unresolved conversations: non-deleted conversations whose status is not `resolved`;
- unread conversations: unresolved conversations with `unread_count > 0`;
- unread messages: the stored unread counters summed over those conversations;
- open tasks: non-deleted tasks in `open` state;
- overdue tasks: open tasks whose `due_at` is earlier than the snapshot moment; and
- due-today tasks: open tasks inside the selected organization/user timezone day.

Unassigned conversations and inactive/deleted owners with pending work remain visible as attention
cohorts. No online-presence, capacity limit, utilization percentage or “balanced” recommendation is
invented because those authorities do not yet exist.

## API, reports and UI

Analytics adds task productivity by assignee over the selected range. The Employees area becomes a
responsive Team Productivity workspace with conversation throughput, task throughput and the live
workload snapshot. Managers need existing `analytics:read` plus `tasks:assign`; analysts do not gain
access to live team allocation.

The fixed report catalogue grows from ten to eleven with Team Productivity. The report reuses the
existing CSV/XLSX/JSON/PDF projection, personal schedule, notification, expiry, signed-download and
Download Center authorities. Historical report values carry additive event components; current
pending stock is not silently inserted into a date-series report.

OpenAPI adds `/api/v1/analytics/task-productivity` and `/api/v1/users/workload`, reaching **219
paths** with synchronized generated TypeScript.

## Persistence and safety

Migration `0052_team_productivity_reports` only widens the governed schedule report catalogue and
preserves one linear **53-revision** history. It creates no duplicate operational or Analytics
fact table. Downgrade removes schedules using the new report value before restoring the prior check
constraint.

## Validation

- Focused workload/Analytics/schedule/migration/contract selection: **79 passed / 6 MySQL-only
  skipped / 0 failed**.
- Focused Analytics UI: **36/36 passed**.
- Complete backend: **1534 passed / 6 MySQL-only skipped / 0 failed in 367.01s**.
- Complete frontend: **41 files / 843 tests passed**.
- Static profile: **6/6 passed**; strict mypy covers **310 source files**; OpenAPI drift passes at
  **219 paths**.
- Vite **8.2.2** production build passes; Analytics is **427.87 kB / 121.06 kB gzip**.
- SQLite upgrade/downgrade/re-upgrade and single-head checks pass at **53 revisions**.
- Docker/security release evidence remains separately recorded in the canonical validation ledger.

## Remaining boundary

Campaign-to-case attribution, recovered-value/revenue and ROI require an approved monetary source
and attribution contract. Per-person capacity/utilization requires approved capacity limits;
online presence, login history and permission-audit views also remain pending. No value is inferred
from message cost, task count or Reactivation status.
