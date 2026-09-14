# PAR-AUTO-15 — Conversation Auto-Resolved Live Follow-up

**Status:** Repository Implemented  
**Date:** 2026-08-23  
**Scope:** Event-safe internal follow-up after governed inactivity auto-resolution

## Decision

The existing immutable `conversation.auto_resolved` Business Event is a third bounded live
Automation Trigger. A published flow may create one publisher-assigned follow-up Task, apply or
remove an existing CRM tag, and deliver an internal Notification. One approved Condition may use
`payload.previous_status` or `payload.inactive_after_hours`, and one durable Delay may pause the
connected sequence.

The underlying CORE-11C auto-resolution remains opt-in and authoritative. Automation consumes its
event only after the Conversation has been resolved; it does not own the inactivity policy or
resolution mutation.

## Tenant-safe execution references

The immutable event stores internal subject/contact lineage. At execution, the live runtime resolves
the referenced Contact and Conversation inside the receipt organization and copies only their
public IDs into the run input. The Business Event payload is not changed. Missing, deleted or
cross-tenant lineage therefore cannot be converted into an effect reference.

## Resolved Conversation boundary

Create task is allowed because it records explicit human follow-up while preserving the resolved
Conversation link. Tag changes and Notification remain Contact-scoped. Human handoff and Assignment
fail closed before any effect because Automation must not silently reopen or re-own a resolved chat.
A genuine future inbound message continues to use the existing Inbox lifecycle to reopen the thread.

## Dispatch and replay

The PAR-AUTO-14 minute scanner projects and claims the receipt through the existing scheduler queue,
and the existing Automation worker executes it. Receipt, run, node and domain idempotency converge a
duplicate delivery to one Task, one tag mutation and one Notification. No new dispatcher, queue,
table or workflow authority is introduced.

## Explicit boundary

General branching, multiple conditions, Wait-for-event subscriptions/timeouts, further live events,
campaign/webhook/customer-message executors, recipient/team routing, capacity/skill routing and
complete operational retry/DLQ/reconciliation UI remain future PAR-AUTO scope. This slice adds no
migration, API route, permission, provider call or customer send.

## Validation

- Live runtime, condition, lineage, replay and fail-closed checks: **29/29 passed**.
- Combined Automation, auto-resolve, trigger, API and scheduler checks: **50/50 passed**.
- Wider Automation, Inbox, Tasks, Tags and Notifications regression: **180/180 passed**.
- Frontend Automation: **15/15 passed**; complete frontend **40 files / 825 tests**.
- Static profile: **6/6 passed**; strict mypy covers **305 source files**.
- OpenAPI remains **211 paths**; migration head remains `0046` (**47 revisions**).
- Production build: PASS; AutomationPage **41.33 kB / 10.48 kB gzip**.
- Applicable backend: **1492 passed / 6 MySQL skips / 1 Redis-only deselection** in **212.83s**.
- Completion: Automation remains **99%** while its live-event evidence expands.
