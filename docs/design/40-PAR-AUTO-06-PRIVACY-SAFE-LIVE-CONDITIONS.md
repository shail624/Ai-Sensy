# PAR-AUTO-06 — Privacy-Safe Live Conditions

**Status:** Repository Implemented  
**Date:** 2026-08-21  
**Scope:** One optional condition in the automatic inbound handoff path

## Decision

The first live automation path now supports either `Trigger → Human handoff` or
`Trigger → Condition → Human handoff`. The condition is evaluated against the immutable,
privacy-safe inbound event snapshot already pinned to the live run. A matching decision continues
to the existing governed handoff. A non-matching decision completes successfully with the handoff
recorded as `skipped` and no Conversation, provider, or customer-message effect.

This remains a bounded linear contract, not a general branch engine. The only live condition fields
are `event_type`, `source`, `payload.direction`, and `payload.message_type`; the only live operators
are `eq`, `ne`, `contains`, and `exists`. Private identifiers, message content, arbitrary dotted
paths, numeric comparisons, multiple conditions, forks, and joins fail closed before an effect.
Test mode retains its broader deterministic simulator.

## Evidence and recovery

The condition attempt records only field name, operator, presence, and boolean match result. It
does not copy the actual value, expected value, customer identity, or message content. When the
condition is false, a terminal handoff attempt records `condition_not_matched` and the condition
node id. Migration `0045_automation_live_conditions` adds `skipped` to the existing attempt status
constraint so the run can truthfully finish all steps without claiming the handoff succeeded.

Completed-node recovery treats both `succeeded` and `skipped` as terminal checkpoints. Receipt UUID,
run identity, immutable version pinning, stale processing lease, and handoff idempotency remain
unchanged. Replaying a processed receipt returns the same terminal run and cannot create a second
handoff or skipped branch.

## Operator contract

The builder defaults new conditions to the live-safe `payload.message_type = text` example and
suggests all four live metadata fields. It keeps arbitrary test-only definitions authorable, labels
their live fail-closed boundary, and explains that the value is unnecessary for `exists`. Run
evidence renders `skipped` distinctly and states when a live decision completed with no handoff
effect.

## Explicit boundary

General branching, multiple conditions, waits/delays, task/tag/notification/campaign/webhook
executors, scheduled/contact/lead consumers, customer-message actions, retries/DLQ controls, and
reconciliation operations remain future PAR-AUTO work. No API path, permission, queue, provider
call, customer send, or second Inbox state machine is added.

## Validation

- Conditional live runtime plus migration: **10/10 passed**.
- Full frontend: **40 files / 818 tests**; focused Automation **8/8**; ESLint and TypeScript pass.
- Static profile: **6/6 passed**; strict mypy covers **305 source files**.
- OpenAPI/generated TypeScript: **211 paths**, drift-free.
- Migration: SQLite upgrade/downgrade/re-upgrade **5/5 passed**; head is `0045` (46 revisions).
- Production build: PASS; AutomationPage **35.98 kB / 9.43 kB gzip**.
- Canonical backend: **1468 passed / 6 MySQL skips / 1 known Redis-only failure**.
- Applicable backend: **1468 passed / 6 MySQL skips / 1 known Redis-only deselection**.
