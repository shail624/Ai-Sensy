# PAR-AUTO-09 — Live Assignment Executor

**Status:** Repository Implemented  
**Date:** 2026-08-21  
**Scope:** One internal `Assignment` effect in the automatic inbound runtime

## Decision

The bounded live runtime now accepts `Trigger → Assignment` and
`Trigger → Condition → Assignment` alongside Human handoff, Create task and Apply tag. The action
assigns the inbound Conversation through the existing organization User, effective Inbox RBAC,
Conversation ownership and tamper-evident Audit authorities. It adds no second queue, assignment
table, permission, API route, provider operation, customer message or migration.

Published assignment configuration supports two existing typed modes:

- `user` resolves the immutable user UUID and requires that user to remain active, same-tenant and
  effectively entitled to `inbox:read` when the receipt executes.
- `round_robin` orders all currently eligible active Inbox users by durable internal identifier and
  selects from that stable order using the receipt's one-based position within its Automation flow.
  Two consecutive receipts for a two-user flow therefore select user one and user two without a
  mutable cursor or cross-tenant state.

Missing, malformed, deleted, inactive, foreign or no-longer-eligible references fail closed before
any ownership mutation.

## Ownership, concurrency and replay

The existing `conversations.assigned_user_id` column remains the sole ownership source. The
executor resolves the Conversation inside the receipt organization and locks its row before making
the decision. If the Conversation already has an owner—from a manual assignment, Inbox policy or
an earlier automatic attempt—the executor returns `already_assigned` and does not steal or replace
that owner.

A new automatic assignment increments the existing Conversation row version and records one
`conversation.assigned` system Audit entry in the same transaction. Evidence names the automation
source, receipt, flow, node and assignment policy without customer content or credentials.

If a worker stops after that transaction but before its step attempt completes, a stale receipt can
run again. The locked Conversation is already owned, so the replay records a successful
`already_assigned` attempt without a second ownership change, row-version bump or Audit entry.

## Conditional behavior and evidence

The PAR-AUTO-06 privacy-safe condition allowlist is unchanged. A match continues to Assignment. A
non-match records the Assignment step as `skipped` with `condition_not_matched` and writes no
ownership or Audit effect. Successful attempt evidence is limited to public Conversation/assignee
identity, mode, outcome and whether a change was applied.

## Operator contract

The Automation builder labels Assignment as a live contract. Operators can choose Round robin or
Specific user; the latter uses the existing organization user source and preserves an immutable
published UUID. Guidance states that an existing owner is never replaced and that execution-time
Inbox eligibility is authoritative. Safe test mode remains deterministic and side-effect-free.

## Explicit boundary

This milestone does not add team presence, capacity limits, queues, skills, SLA routing, fallback
groups or mutable round-robin cursor administration. Multiple effects, general branching,
waits/delays, Remove tag, notification/campaign/webhook and customer-message executors, other live
event consumers, retry/DLQ operator controls and reconciliation UI remain future PAR-AUTO scope.
The general AiSensy chatbot/automation engine is not claimed complete.

## Validation

- Live runtime including specific-user replay and two-conversation round-robin rotation: **11/11
  passed**.
- Automation definition/runtime plus existing Inbox regression: **45/45 passed**.
- Full frontend: **40 files / 820 tests**; focused Automation **10/10**; ESLint and TypeScript pass.
- Static profile: **6/6 passed**; strict mypy covers **305 source files**.
- OpenAPI/generated TypeScript: **211 paths**, drift-free.
- Migration head remains `0045` (**46 revisions**); no migration or API path was added.
- Production build: PASS; AutomationPage **38.91 kB / 10.05 kB gzip**.
- Canonical backend: **1474 passed / 6 MySQL skips / 1 known Redis-only failure**.
- Applicable backend: **1474 passed / 6 MySQL skips / 1 known Redis-only deselection**.
