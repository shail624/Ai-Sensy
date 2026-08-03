# Design Document 32 — CORE-09 Unified Notification Center

## Purpose and boundary

CORE-09 adds durable, server-owned delivery and acknowledgement over existing Task and Reactivation
events. It does not create a second reminder, task, scheduler, event, audit, timeline, assignment,
notification-user, or real-time transport authority. CORE-10 Chat History is outside this change.

## Repository reuse map

| Existing capability | Existing file paths | Extension point | Genuine missing capability |
|---|---|---|---|
| Follow-up and Release reminders | `backend/app/models/task.py`, `repositories/task.py`, `services/task_service.py`, Task API/UI | Emit one delivery after the existing due scan; resolve it inside existing lifecycle commands. | Durable recipient/read/resolution projection. |
| Celery scheduling | `backend/app/crm/reactivation_tasks.py`, existing Beat registration and `scheduler.tick` queue | Keep the existing minute scan and transaction; no new task or queue. | No gap beyond calling the projection. |
| Reactivation assignment/status | `backend/app/models/vi_domain.py`, `services/vi_domain_service.py`, existing APIs | Emit transactionally from create, owner change, and immutable status transition paths. | Recipient delivery for governed changes. |
| Audit and Customer Timeline | Existing `AuditService`, Task/Vi audit and `ContactEventService` projections | Source commands retain their current evidence; notification acknowledgement adds Audit only. | Read/read-all audit actions. |
| RBAC, tenant and users | Existing `tasks:read`, `tasks:assign`, route dependencies, `User`, user directory hooks | Self-scope reads/writes; allow permission-checked, read-only team filter. | No new permission or directory. |
| Application shell and design system | `TopNav.tsx`, shared `Modal` drawer, Badge, Skeleton, EmptyState, ErrorState | Replace the transient queue badge with persisted unread count; retain authorized system-health signals. | Unified responsive Notification Center UI. |
| Generated API contracts | Existing FastAPI router, OpenAPI export and `openapi-typescript` pipeline | Add four permission-scoped paths and regenerate in place. | List, unread count, mark-one and mark-all contracts. |

No completed Contacts, Reactivation, Tasks, Notifications preferences, Customer 360, Audit, Timeline,
RBAC, queue, scheduler, user-directory, or design-system module is rebuilt.

## Persistence and delivery

`notifications` contains one UUID-addressable row per recipient delivery. Organization and recipient
are required foreign keys. Optional Contact, Reactivation case, Task, and actor references support
source navigation without copying source facts. `read_at` records acknowledgement and `resolved_at`
records source-work completion. A unique `(organization_id, dedup_key)` boundary prevents duplicate
delivery when a scheduler command or idempotent domain command is retried.

The due adapter supports only the existing Reactivation reminder Tasks. `task_type=reminder` maps to
Follow-up; the existing Name-change custom Task maps to Release date. Due Today, Upcoming and
Overdue are server-derived from `due_at`, resolution, and the signed-in user's timezone. No status
is copied back into Task.

## API and security

- `GET /api/v1/notifications` provides bounded cursor pagination and type, read/lifecycle, created
  date, and assignee filters.
- `GET /api/v1/notifications/unread-count` returns the signed-in recipient's persisted unread count.
- `POST /api/v1/notifications/{id}/read` and `POST /api/v1/notifications/read-all` are idempotent,
  self-scoped and audited.
- Foreign organizations and another recipient's identifier resolve to no writable notification.
  `tasks:assign` permits team reads only; the UI labels that state read-only.

## Workspace and interaction design

The existing bell opens the shared focus-trapped drawer. Desktop/tablet use a dense side panel;
mobile uses the existing full-width bottom/drawer transformation. A compact filter grid provides
type, status, date and permission-aware assignee controls. Unread emphasis, due-state chips,
recipient/customer context, timestamps and source actions preserve scanning density. Source actions
open Customer 360, Reactivation pipeline or Tasks using existing routes.

The center provides loading skeletons, useful empty copy, recoverable errors, offline evidence,
permission denial, recipient-only mutation behavior, bounded fifteen-second polling, Escape/backdrop
dismissal, focus trapping and invoker focus restoration. No fake record, count, metric or local-only
read state is present.

## Reference and originality review

The approved ignored reference pair reviewed before implementation was:

- `0055_manage_notification_preferences_add_device_full.png`
- `0055_manage_notification_preferences_add_device_viewport.png`

The captures supplied the benchmark for Manage-style hierarchy, compact cards, action placement,
control density, and mobile stacking. The repository has no approved notification-panel capture, so
the product contract and existing governed drawer determine the workflow. The implementation uses
original React components, Lucide icons, Vi wording, design tokens, colors, spacing and breakpoints.
No proprietary code, asset, branding, wording, exact color, typography, pixel layout, screenshot or
reference file is copied or committed.

## Defects fixed and regression evidence

1. A team assignee filter initially exposed recipient acknowledgement controls even though the API
   correctly scopes mark-read to the signed-in recipient. Root cause: presentation scope was not
   derived from the active assignee filter. The team view is now explicitly read-only; focused UI
   tests preserve self/team separation.
2. The former shell badge represented infrastructure thresholds rather than persisted user work.
   Root cause: the shell predated a durable notification projection. The badge now uses the
   server-owned unread count while existing operator signals remain visible to `system:read` users.

No reproducible Critical or High defect remains in the milestone scope. No test or permission was
weakened.

## Strictly necessary new files

| New file | Necessity |
|---|---|
| `backend/app/models/notification.py` | Durable, per-recipient delivery/read/resolution projection missing from all existing authorities. |
| `backend/app/repositories/notification.py` | Central tenant/recipient filters, deduplication, unread and resolution queries. |
| `backend/app/services/notification_service.py` | Transactional projection, self/team security and source-reference composition. |
| `backend/app/schemas/notification.py` | Generated-contract source for strongly typed notification and reference responses. |
| `backend/app/api/v1/endpoints/notifications.py` | Permission-scoped list/count/read API absent from the repository. |
| `backend/alembic/versions/0035_notification_center.py` | Additive persistence migration for the verified durable-read-state gap. |
| `backend/tests/test_notification_center.py` | Idempotency, lifecycle, audit, RBAC, tenant/source and API regression coverage. |
| `frontend/src/features/notifications/{types,api,NotificationCenter,index}.ts(x)` | Generated-contract adapter and unified shell workspace; no prior Notification Center feature existed. |
| `frontend/src/features/notifications/notifications.test.tsx` | Filters, deep links, read actions, honest states, focus, permission and responsive regression coverage. |
| `docs/adr/0019-unified-notification-projection.md` | Permanent ownership, polling and security decision. |
| `docs/design/32-CORE-09-UNIFIED-NOTIFICATION-CENTER.md` | Permanent reuse, contract, UI/reference, defect and validation record. |

## Validation boundary

Focused tests cover due/status/assignment delivery, idempotency, task resolution, read state, audit,
RBAC, tenant boundaries, filters, deep links, offline/error/empty/permission states, focus and
responsive transformations. The canonical pre-merge and, because scheduler/migration/runtime
behavior changes, deployed Docker gates provide the final evidence recorded in
`VALIDATION_RESULTS.md`.
