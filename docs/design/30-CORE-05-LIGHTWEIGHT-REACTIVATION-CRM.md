# Design Document 30 — CORE-05 Lightweight Reactivation CRM

## Purpose and boundary

This corrected milestone makes the existing Reactivation workspace the primary internal CRM. It
adds one current status, multiple labels, dated Task-backed reminders, assignment, notes, audit,
and Customer Timeline evidence. It preserves the CORE-02/04 KYC, SIM, and Activation foundations
and does not build a new SIM fulfilment, Activation Queue, notification system, or CRM authority.

## Repository reuse map

| Existing capability | Existing file paths | Extension | Genuine gap |
|---|---|---|---|
| Reactivation aggregate and lifecycle | `backend/app/models/vi_domain.py`, `repositories/vi_domain.py`, `services/vi_domain_service.py`, `schemas/vi_domain.py`, `api/v1/endpoints/vi_domain.py` | Replace the current operational status catalogue, add case labels/dates, reminder filters/counters, and Task composition while retaining immutable legacy events. | Current label relation and owner-approved status mapping. |
| Reactivation workspace | `frontend/src/features/reactivation/*` | Existing board/list/drawer gain status/label/assignee/date controls, chips, due views, factual counters, and shared Task actions. | CRM-specific composition only. |
| Tasks and reminders | `backend/app/models/task.py`, `repositories/task.py`, `services/task_service.py`, Task API/frontend hooks | Existing Task lifecycle gains Reactivation reference support, Snooze, due-dispatch evidence, audit coverage, and row-versioned actions. | Case reference, Snooze event, and due-notified timestamp. |
| Contacts and ownership | Existing Contact/User models, repositories, APIs, and user selector | Existing tenant contacts and active users remain the case/assignment authority. | No new authority. |
| Audit and Customer Timeline | Existing `AuditService`, `AuditLog`, `ContactEvent`, Task events, and Vi record helpers | Every label/date/assignment and reminder lifecycle change appends the existing evidence streams. | Additional event taxonomy only. |
| Celery and notifications | Existing Celery app/beat and assigned-user Task work queue | A bounded periodic adapter asks TaskService to mark due reminder delivery evidence. | Scheduled due detection; no Notification table. |
| Shared UI/accessibility | Existing Badge, Button, Card, Modal/drawer, skeleton, empty/error, responsive table/Kanban and form primitives | Original components are recomposed at approved information density. | No new design-system primitive. |

No completed Contacts, Inbox, Campaigns, Templates, Documents, Customer 360, Tasks, Analytics,
Automation, RBAC, Audit, Timeline, queue, KYC, SIM, Activation, or design-system authority is rebuilt.

## Persistence and transition design

Migration `0034_reactivation_crm` is additive from `0033_kyc_operations`. It creates
`reactivation_case_labels`, expands the Task reference constraint to `reactivation_case`, adds
`due_notified_at`, and maps only the mutable current stage to the nine statuses. Immutable
`reactivation_stage_events` keep both canonical and legacy values. The current case table continues
to provide exactly one non-null primary status. Labels are unique per case and constrained to the
approved catalogue.

All active statuses can move to another active/terminal owner-approved status through the existing
versioned, idempotent transition command. Completed and Not Required are terminal. Not Required
requires a reason. Follow-up requires a follow-up date; Name Change requires a release date. A
date-bearing label requires an assigned user so the existing Task can notify an accountable owner.

## Reminder lifecycle

Follow-up uses a `reminder` Task and Name Change uses a `custom` Task, both referenced to the
Reactivation case. Label updates create, reassign, reschedule, or retire those Tasks in the same
transaction as the case update. The pipeline projects open reminder facts and server-derived
Upcoming, Due Today, and Overdue buckets. Complete, Snooze, and Reschedule use shared Task commands
with optimistic concurrency. Due detection records a Task event, Audit action, Customer Timeline
event, and `due_notified_at` without closing the Task; an overdue reminder remains active until the
operator resolves it.

## API and UI

The existing Reactivation update and pipeline contracts are extended in place. One Task Snooze path
advances OpenAPI from 188 to 189 paths; generated TypeScript remains the only frontend contract.
The existing pipeline supplies real status counts, due counters, status/label/owner/date filters,
dense Kanban/list views, keyboard and pointer movement, and honest loading/empty/error/read-only
states. The case drawer supplies the quick status selector, label multi-select, required dates,
assignment, notes, and scheduled reminder actions.

## Reference and originality review

Paired `_full.png` and `_viewport.png` captures were reviewed from the ignored reference library:

- `0008_contacts_filter` for compact filters, flyout hierarchy, and dense result controls;
- `0054_manage_tags_create` for label management rhythm and chip presentation;
- `0052_manage_team_manage_team_members` for staff selection and compact table density;
- `0004_contacts_add_contact` for accessible form grouping and modal action placement.

The implementation retains recognizable filter density, layered case editing, compact chips,
primary/secondary actions, and responsive collapse using original Vi components, wording, Lucide
icons, tokens, spacing, and breakpoints. No reference code, asset, branding, text, exact color,
typography, pixel layout, or screenshot is copied or committed.

## Necessary new files

| New file | Why it is necessary |
|---|---|
| `backend/alembic/versions/0034_reactivation_crm_workflow.py` | Adds the verified label, Task-reference, due-delivery, and current-status persistence changes without rewriting history. |
| `backend/app/crm/reactivation_tasks.py` | Registers the bounded Celery adapter while leaving TaskService authoritative. |
| `backend/tests/test_reactivation_crm_workflow.py` | Regression coverage for statuses, labels, dates, tenant/RBAC boundaries, reminders, evidence, filters, and concurrency. |
| `docs/adr/0017-lightweight-reactivation-crm.md` | Permanently records the corrected authority and no-heavy-workspace decision. |
| `docs/design/30-CORE-05-LIGHTWEIGHT-REACTIVATION-CRM.md` | Records reuse, persistence, workflow, visual benchmark, and validation boundaries. |

All other changes extend existing implementations in place.

## Verified defect policy

The milestone closes workflow-blocking defects exposed by the correction: stale date submission
after label removal, non-versioned Complete/Reschedule UI commands, lack of a server-enforced Not
Required reason, timezone-aware date normalization, and owner-only updates leaving existing
reminders assigned to the former staff member. Review also found rollback constraints rejecting
post-upgrade status events; downgrade now translates populated event rows before restoring the
legacy constraint. Each root cause is corrected at the existing authority boundary and covered by
focused tests; tests and permissions are not weakened.

## Known limits

The periodic due adapter records durable assigned-user delivery evidence and relies on the existing
Task work queue; rich in-app Notification Center records, unread state, SSE, and optional delivery
channels remain the later shared Notification Center milestone. Final representative-data visual,
screen-reader/device, production Celery timing, and high-volume reminder performance remain host
validation. No standalone SIM or Activation workspace is next by default.
