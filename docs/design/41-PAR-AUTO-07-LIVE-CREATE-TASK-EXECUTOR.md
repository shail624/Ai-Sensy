# PAR-AUTO-07 — Live Create Task Executor

**Status:** Repository Implemented  
**Date:** 2026-08-21  
**Scope:** One internal `Create task` effect in the automatic inbound runtime

## Decision

The bounded live runtime now accepts either `Trigger → Create task` or
`Trigger → Condition → Create task`, alongside the already supported Human handoff paths. The
effect creates a real Task through the existing tenant-scoped Task service and binds it to the
inbound Contact and, when present, Conversation. It does not introduce another task table, API
route, permission, queue, customer message, or provider action.

The published action owns four immutable inputs: a trimmed title, existing Task type, existing
priority, and a due delay from 5 minutes through 365 days. New actions default to Custom, Medium,
and 24 hours. The active automation publisher is the assignee; an inactive, deleted, missing, or
cross-tenant publisher fails closed rather than creating unowned work. Due time is calculated from
the immutable event occurrence time, so worker delay or replay cannot change it.

## Durable effect and replay

Task creation reuses the existing Task, Task history, Contact Timeline and tamper-evident Audit
authorities. System execution records `created_by = null` and a system Audit actor while retaining
the publisher as the accountable assignee. Public Contact/Conversation identifiers are resolved
inside the receipt's organization before the Task service is called.

The receipt UUID is the Task idempotency key. A canonical command hash binds the pinned version,
action node, Contact, Conversation, title, type, priority, due time and assignee. If a worker stops
after the Task transaction but before completing its Automation attempt, stale-receipt recovery
finds and returns that exact Task. A changed command under the same receipt fails with
`automation_task_replay_conflict`; it cannot silently reuse or duplicate work.

## Conditional behavior and evidence

The same privacy-safe live condition allowlist from PAR-AUTO-06 applies. A matching condition
continues to Create task. A non-match records the action attempt as `skipped` with
`condition_not_matched` and creates no Task, TaskEvent, ContactEvent, or Task Audit entry. A
successful attempt exposes only Task identity, status, due time, assignee identity and whether the
effect was recovered; customer message content and provider identity remain absent.

## Operator contract

The existing Automation builder exposes Task title, type, priority and due delay on the Action
node, explains the publisher-assignment rule, and presents the exact Trigger → optional Condition
→ Human handoff/Create task live boundary. Run evidence labels both successful effects and
condition-driven no-effect outcomes. Safe test mode remains deterministic and side-effect-free.

## Explicit boundary

General branching, multiple conditions, waits/delays, tag/notification/campaign/webhook and
customer-message executors, scheduled/contact/lead consumers, task escalation or reassignment
policies, retry/DLQ operator controls, and reconciliation UI remain future PAR-AUTO scope. No claim
is made that the general AiSensy chatbot/automation engine is complete.

## Validation

- Live runtime including direct, conditional and crash-replay Task paths: **7/7 passed**.
- Existing Task API regression: **45/45 passed**.
- Full frontend: **40 files / 818 tests**; focused Automation **8/8**; ESLint and TypeScript pass.
- Static profile: **6/6 passed**; strict mypy covers **305 source files**.
- OpenAPI/generated TypeScript: **211 paths**, drift-free.
- Migration head remains `0045` (**46 revisions**); no migration or API path was added.
- Production build: PASS; AutomationPage **37.59 kB / 9.76 kB gzip**.
- Canonical backend: **1470 passed / 6 MySQL skips / 1 known Redis-only failure**.
- Applicable backend: **1470 passed / 6 MySQL skips / 1 known Redis-only deselection**.
