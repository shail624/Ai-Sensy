# PAR-AUTO-05 — Automatic Inbound Handoff Runtime

**Status:** Repository Implemented  
**Date:** 2026-08-21  
**Scope:** One automatic live path: `message.received` Trigger → Human handoff

## Decision

A newly accepted inbound message now appends a privacy-safe `message.received` Business Event in
the same transaction as its Message and Conversation facts. Existing clean published Automation
versions that match that event receive durable receipts. The inbound worker dispatches those
receipts only after commit, using the receipt UUID as the deterministic task identity.

The live consumer supports exactly one graph shape in this slice: one matching Trigger connected
directly to one Human handoff. It pins the immutable version, creates one `mode=live` AutomationRun,
checkpoints both steps, and executes the existing governed handoff service. Every other graph fails
closed with run/receipt evidence and no business effect. Safe manual test runs remain fully
simulated.

## Persistence and state

Migration `0044_automation_live_handoff_runtime` is additive to the existing authorities:

- AutomationRun mode expands from `test` to `test|live`.
- Trigger receipts progress through `received`, `processing`, `processed`, or `failed`.
- Each receipt may reference exactly one run and records processing/terminal timestamps.
- A five-minute processing lease allows a genuinely abandoned receipt to resume; a fresh lease
  suppresses a duplicate worker.
- Receipt claim, run creation, queued job evidence and system Audit evidence commit together while
  the receipt row is locked.

The receipt UUID is also the run idempotency key and correlation/task identifier. A broker or
webhook redelivery therefore converges on the same receipt and run. Completed and failed receipts
are not redispatched; an old duplicate remains a ledger no-op.

## Privacy and recovery

The inbound event carries only public Message, Conversation and Contact identifiers, direction,
message type and connector source. It never copies message body, provider message ID, phone, name,
credential or provider payload. The live run input contains only that governed event payload.

The trigger checkpoint commits before the handoff attempt. The handoff itself is independently
idempotent through its deterministic Business Event identity. If a worker stops after the effect
but before its step checkpoint, a stale-lease replay reads the existing effect and finishes the
same pinned run without requeueing an intervened chat.

## Operator contract

Automation now shows one `Run history` for test and live modes, per-step evidence, and the real
receipt state. Runs/receipts poll while the workspace is open so externally triggered work appears
without a page reload. The UI states the exact supported live path and preserves evidence-only
truth for other event types.

## Explicit boundary

This is not a general chatbot engine. Conditions, branching, delays/waits, task/tag/notification/
campaign/webhook executors, scheduled/contact/lead live consumers, customer-message actions,
retry/DLQ control UI and broad recovery/reconciliation operations remain future PAR-AUTO work.
No new permission, API path, provider call, customer send or second Inbox state machine is added.

## Validation

- Focused Automation/Inbox regression: **40/40 passed** after the final receipt-lock hardening.
- Full frontend: **40 files / 817 tests**; ESLint and TypeScript pass.
- Static profile: **6/6 passed**; strict mypy covers **305 source files**.
- OpenAPI/generated TypeScript: **211 paths**, drift-free.
- Migration: SQLite upgrade/downgrade/re-upgrade **5/5 passed**; head is `0044` (45 revisions).
- Production build: PASS; AutomationPage **35.10 kB / 9.16 kB gzip**.
- Canonical unfiltered backend: **1465 passed / 6 MySQL skips / 1 known Redis-only failure**.
- Applicable backend: **1465 passed / 6 MySQL skips / 1 known Redis-only deselection**.
