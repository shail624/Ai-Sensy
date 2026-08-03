# ADR-0019: Project existing work events into one durable Notification Center

- **Status:** Accepted
- **Date:** 2026-08-02
- **Milestone:** CORE-09
- **Decision owners:** Repository owner and Vi Reactivation engineering

## Context

The existing Task authority already owns Follow-up and Release-date reminders, immutable lifecycle
events, completion/reschedule/snooze behavior, and the Celery due-reminder scan. Reactivation owns
case assignment and primary-status transitions. Audit and Customer Timeline already preserve source
evidence. What the platform lacked was a durable per-recipient delivery/read projection: the shell
could show infrastructure health, but a user could not review or acknowledge their work events
across devices.

No server-sent-event, WebSocket, or other reusable real-time authority exists in the repository.
Creating one solely for this milestone would add infrastructure without improving the durability
boundary.

## Decision

Add one tenant-scoped `Notification` projection with recipient, source references, type, due time,
read time, resolution time, and an organization-scoped deduplication key. Tasks and Reactivation
remain the workflow authorities; the notification row does not copy task state, case state, audit,
timeline, reminder, or user records.

The existing due scheduler creates idempotent Follow-up/Release notices in the same database
transaction as `due_notified_at`, TaskEvent, Audit, and Customer Timeline evidence. Existing Task
complete, cancel, skip, snooze, reschedule, and reassign commands resolve an active delivery while
retaining its history. Existing Reactivation create/update/transition commands create assignment
and primary-status notices transactionally.

Authenticated users list and mark only their own notifications. The existing `tasks:read`
permission gates the center; the existing `tasks:assign` permission permits a read-only assignee
filter for team supervision. Mark-one/all-read actions remain self-scoped and write immutable Audit
evidence. The UI polls the bounded unread/list endpoints every fifteen seconds because no safe
real-time transport authority exists.

## Consequences

- Migration head advances additively from `0034_reactivation_crm` to
  `0035_notification_center`; no existing column or record is rewritten.
- OpenAPI advances from 189 to 193 paths and generated TypeScript contracts remain authoritative.
- The application-shell badge represents persisted unread work, not queue-health alerts. Authorized
  operators retain queue/worker signals inside a separate compact section of the same drawer.
- Customer, Reactivation case, Task, and Customer 360 links use existing routes and source records.
- Delivery retries converge through the unique deduplication key; Task resolution never deletes
  prior notification evidence.
- Push, email, internal WhatsApp, SSE, and browser-push channels remain unimplemented unless a later
  owner-approved milestone establishes their infrastructure and privacy contracts.

## Rejected alternatives

- Reuse `TaskEvent` as read state: rejected because events are immutable shared history, not
  per-recipient acknowledgement records.
- Create a second reminder or scheduler system: rejected because Task/Celery already own dates and
  due dispatch.
- Store notifications only in browser state: rejected because read state must survive refreshes and
  devices.
- Introduce SSE now: rejected because the repository has no reusable streaming authority and
  bounded polling satisfies the reliability requirement without parallel infrastructure.
- Let managers mark another assignee's notifications read: rejected because acknowledgement belongs
  to the recipient; team filtering is intentionally read-only.
