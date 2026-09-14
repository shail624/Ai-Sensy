# PAR-AUTO-13 — Durable Live Delay

**Status:** Repository Implemented  
**Date:** 2026-08-23  
**Scope:** One bounded scheduled pause inside the existing linear inbound live runtime

## Decision

The supported `message.received` live path may now contain one Delay alongside one to four
distinct proven internal effects. The optional privacy-safe Condition remains immediately after
the Trigger. The Delay may pause the connected sequence for 60 seconds to 30 days; effects before
it complete normally, while effects after it cannot run until the durable resume time is due.

This is scheduled continuation of the existing pinned run, not a general timer or workflow engine.
Multiple delays, Wait-for-event nodes, branches, repeated effect kinds, more than four effects,
unsupported actions and external/customer-facing nodes still fail closed before any business
effect begins.

## Durable pause and resume

The first delivery creates one running Delay attempt with the immutable duration and calculated
`resume_at` evidence. The run moves to `retrying`, the receipt remains `processing`, and the same
Automation worker task is scheduled with a bounded countdown on the existing `automation.run`
queue. No new table, migration or queue is required.

An early or duplicate delivery finds the same running Delay attempt and cannot advance past it.
When the due time is reached, that attempt becomes the completed checkpoint and execution resumes
at the first incomplete downstream node. Effects completed before the Delay retain PAR-AUTO-12's
durable checkpoints and domain idempotency, so worker retry cannot duplicate them.

## Condition behavior

A false approved Condition skips the entire downstream path, including the Delay, without
scheduling a resume or applying an effect. A true Condition follows the published linear order.
Safe test mode continues to simulate every node without applying business effects.

## Explicit boundary

General branching, multiple conditions, Wait-for-event subscriptions/timeouts, other live event
consumers, campaign/webhook/customer-message executors, recipient/team notification routing,
capacity/skill routing and complete operational retry/DLQ/reconciliation UI remain future
PAR-AUTO scope. This slice adds no provider call, customer send, route, permission or parallel
domain authority.

## Validation

- Live runtime, scheduling, replay, condition and graph-boundary checks: **22/22 passed**.
- Wider Automation, Tasks, Tags and Notifications regression: **166/166 passed**.
- Frontend Automation: **13/13 passed**; complete frontend **40 files / 823 tests**.
- Static profile: **6/6 passed**; strict mypy covers **305 source files**.
- OpenAPI remains **211 paths**; migration head remains `0046` (**47 revisions**).
- Production build: PASS; AutomationPage **40.53 kB / 10.33 kB gzip**.
- Canonical backend: **1485 passed / 6 MySQL skips / 1 known Redis-only failure** in **275.76s**.
- Applicable backend: **1485 passed / 6 MySQL skips / 1 Redis-only deselection** in **210.49s**.
- Completion: Automation advances **98% → 99%**.
