# ADR-0017: Keep Vi operations inside one lightweight Reactivation CRM

- **Status:** Accepted
- **Date:** 2026-08-02
- **Milestone:** CORE-05 (owner-corrected)
- **Decision owners:** Repository owner and Vi Reactivation engineering

## Context

CORE-02 through CORE-04 delivered durable Reactivation, KYC, SIM, Activation, SLA, document,
appointment, audit, and timeline foundations. The owner has clarified that day-to-day work must not
be split into further heavyweight KYC, SIM, and Activation products. Operators need one case,
exactly one primary status, flexible labels, dated follow-ups, assignment, notes, and evidence.

The repository already has the authoritative Reactivation aggregate, Task lifecycle, Contacts,
Users, Audit, Customer Timeline, RBAC, optimistic concurrency, Celery scheduling, and responsive
pipeline/drawer components. A new reminder, notification, pipeline, or activity authority would
duplicate completed work.

## Decision

`ReactivationCase` remains the single operator-facing CRM aggregate. Its primary status uses the
owner-approved nine-value catalogue: New Lead, Lead Confirmed, Documents Pending, Documents
Received, KYC / Verification, SIM Required, Activation Pending, Completed, and Not Required. A case
has exactly one status. Not Required is terminal and requires a closing reason.

Current labels are stored in a tenant-scoped case-label relation and use the six-value catalogue:
Follow-up, Prepaid Required, Name Change, Priority, Customer Not Reachable, and Documents
Incomplete. No value exists as both a current status and label. Immutable historical stage events
retain their legacy values; migration of the current case status never rewrites evidence.

Follow-up and Name Change dates are existing `Task` records linked to the Reactivation case.
TaskService remains authoritative for create, update, complete, snooze, reschedule, assignment,
row-version enforcement, Audit, and Customer Timeline. The existing Celery scheduler detects due
case reminders and records durable delivery evidence for the assigned user. Overdue Tasks remain
open until completed or rescheduled. No parallel reminder or notification store is introduced.

One additive migration, `0034_reactivation_crm`, maps current legacy stages to the new status
catalogue, preserves immutable event history, adds current case labels, permits Task links to
Reactivation cases, and adds due-notification state. Existing KYC, SIM, and Activation foundations
are retained for integrity and future explicit owner instructions, but no further standalone
operational workspace is planned by default.

## Consequences

- Operators work from one persisted Kanban/list and case drawer with status, labels, owner, notes,
  reminder controls, due counters, and filters.
- Refresh, RBAC, tenant isolation, concurrency, audit, and timeline behavior remain server-owned.
- Existing standalone KYC work is preserved; the corrected direction prevents additional heavy SIM
  or Activation workspaces unless the owner explicitly reauthorizes them.
- Full in-app Notification Center delivery remains a later shared-platform milestone; this change
  records due delivery evidence and exposes the assigned user's existing Task work queue.

## Rejected alternatives

- Separate reminder or notification tables: rejected because Tasks and durable evidence already own
  the lifecycle.
- Store Follow-up as both a status and label: rejected because status and label semantics must not
  overlap.
- Rewrite immutable legacy stage history: rejected because historical evidence cannot be altered.
- Delete CORE-02/04 models or APIs: rejected because completed foundations and data integrity must be
  preserved.
- Build standalone SIM and Activation workspaces now: rejected by the owner-approved lightweight
  operating model.
