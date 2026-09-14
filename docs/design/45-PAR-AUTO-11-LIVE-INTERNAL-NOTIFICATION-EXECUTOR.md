# PAR-AUTO-11 — Live Internal Notification Executor

**Status:** Repository Implemented  
**Date:** 2026-08-21  
**Scope:** One internal Notification Center effect in the automatic inbound runtime

## Decision

The bounded live runtime accepts `Trigger → Notification` and
`Trigger → Condition → Notification` alongside the five previously proven effects. It delivers the
published internal message to the active automation publisher through the existing Notification
Center and links the delivery to the triggering Contact. It sends no email, browser push, WhatsApp
message, provider request or customer-facing content.

The publisher must still be active in the receipt organization and effectively entitled to
`tasks:read`, which is the existing Notification Center access authority. Missing, inactive,
deleted, foreign or ineligible publishers and invalid Contact references fail closed before a
delivery is written. The message is trimmed and bounded to 500 characters at the typed publication
boundary.

## Durable delivery and replay

The existing `notifications` table remains the only delivery projection. A new
`automation_attention` type is added through migration `0046_automation_notifications`; no second
notification table, route, permission, queue or Audit authority is created. The migration changes
only the existing type constraint and deletes this derived projection type before restoring the
legacy constraint on downgrade.

The receipt and node form a stable tenant-scoped deduplication key. A first execution writes one
unread Contact-linked notification. If a worker stops after that commit but before its Automation
attempt completes, replay resolves the same row as `already_delivered`. A key bound to different
recipient, Contact, title, body or type fails closed instead of accepting ambiguous evidence.

## Conditional behavior and operator contract

A false privacy-safe Condition records Notification as skipped and writes no delivery. Successful
attempt evidence contains only public Notification, recipient and Contact identifiers plus the
`delivered|already_delivered` result. The Automation builder marks Notification as a live contract,
states that the active publisher is the recipient and explicitly excludes external/customer sends.
Safe test mode remains simulated.

## Explicit boundary

Specific-recipient/team notification routing, email, browser push, internal WhatsApp, multiple
effects, general branching, waits/delays, campaign/webhook/customer-message executors, other live
event consumers and retry/DLQ reconciliation UI remain future scope.

## Validation state

- Live runtime including direct, conditional and crash-replay Notification paths: **15/15 passed**.
- Runtime plus Notification Center/lifecycle and migration regression: **23/23 passed**.
- Static profile: **6/6 passed**; strict mypy covers **305 source files**.
- OpenAPI/generated TypeScript: **211 paths**, drift-free.
- Migration head: `0046_automation_notifications` (**47 revisions**); round trip passes.
- Canonical backend: **1478 passed / 6 MySQL skips / 1 known Redis-only failure**.
- Applicable backend: **1478 passed / 6 MySQL skips / 1 Redis-only deselection**.
- Frontend ESLint and TypeScript pass; focused Automation/Notification checks are **14/14**.
- Full frontend: **40 files / 821 tests passed**.
- Production build: PASS; AutomationPage **40.08 kB / 10.20 kB gzip**.
- Completion: Automation advances **94% → 96%**.
