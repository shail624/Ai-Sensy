# PAR-AUTO-20 — Bounded Live Yes/No Branch

**Status:** Repository Implemented  
**Date:** 2026-08-23  
**Scope:** Add one deterministic terminal decision split without opening a general flow engine

## Decision

One event-backed live Automation may now use this exact topology:

`Trigger → Condition → Yes effect | No effect`

The Condition owns exactly two outgoing edges labeled `yes` and `no`. Each edge ends at exactly one
already-approved internal effect. The condition is evaluated once against the immutable, privacy-
safe trigger input; only the selected effect executes. The unselected effect receives a terminal
`skipped` attempt containing the Condition node and selected branch, so a successful run retains
complete operator evidence rather than silently hiding the decision.

## Supported effects and event boundaries

Each terminal effect is revalidated against the existing trigger-specific allow-list:

- Message Received: Human handoff, Create task, Apply tag, Remove tag, Assignment or Notification.
- Contact Created: Apply tag, Remove tag or Notification.
- Conversation Auto-Resolved and Lead Stage Changed: Create task, Apply tag, Remove tag or
  Notification.
- Schedule remains linear and does not accept a Condition.

The two branches may use the same effect kind because only one can execute. Existing per-node and
domain idempotency keys still protect worker replay.

## Runtime and recovery

The selected effect uses the existing effect executor and checkpoints. A duplicate receipt or
worker delivery reuses the same live run. If a worker stops after the selected effect but before the
skip record, replay recognizes the completed effect and records only the missing unselected branch.
No customer send, provider call or new queue is introduced.

Safe test mode recognizes the same exact topology, simulates only the selected effect and records
the other as skipped. It remains side-effect-free.

## Authoring experience

The existing list builder exposes **Enable Yes/No branch** only after the operator builds exactly
Trigger, Condition, Yes action and No action. The third and fourth nodes receive visible Yes/No
badges, and adding or reordering is locked while the split is active. **Use linear gate** safely
returns the same four nodes to their connected linear order.

## Fail-closed boundary

Nested branches, multiple Conditions, branch sequences, Delay or Wait inside a branch, missing or
duplicate edge labels, branch merging, more than two outcomes and arbitrary fan-out remain blocked
before a live effect. Linear Delay/Wait behavior is unchanged.

No route, permission, migration, queue, provider configuration or customer-send authority is
added. Migration head remains `0048_automation_wait_subscriptions` (**49 revisions**) and OpenAPI
remains **211 paths**.

## Validation

- Live runtime plus safe-test runtime: **45/45 passed**.
- Combined Automation live/runtime/API/migration regression: **60/60 passed**.
- Focused Automation UI: **20/20 passed**; frontend lint and TypeScript pass.
- Static profile: **6/6 passed**; strict mypy covers **305 source files**; OpenAPI is synchronized.
- Complete release profile: **23/23 passed in 417.8s**, including **1515 backend tests with zero
  skips**, **40 frontend files / 830 tests**, production build, SAST/dependency/source/image scans,
  certified WAHA runtime, exact image contracts and CycloneDX SBOMs. `AutomationPage` is **44.79 kB
  / 11.20 kB gzip**.
- Automation remains **99%**: multiple/nested branches, multi-step branch bodies, external/customer
  actions, recipient/team routing and operational reconciliation remain future work.
