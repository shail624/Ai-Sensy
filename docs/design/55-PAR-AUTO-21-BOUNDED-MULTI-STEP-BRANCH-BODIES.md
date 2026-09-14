# PAR-AUTO-21 — Bounded Multi-Step Branch Bodies

**Status:** Repository Implemented  
**Date:** 2026-08-23  
**Scope:** Extend one deterministic Yes/No decision without opening a general flow engine

## Decision

One event-backed live Automation may now use this exact topology:

`Trigger → Condition → Yes effect [→ Yes effect] | No effect [→ No effect]`

The Condition still owns exactly two outgoing edges labeled `yes` and `no`. Each branch contains
one or two ordered, trigger-safe internal effects. The existing total ceiling of four live effects
is unchanged. Only the selected branch executes; every node on the unselected branch receives a
terminal `skipped` attempt containing the Condition node and selected outcome.

## Safety and replay

Effects must remain distinct within one branch body. The same effect kind may appear on alternate
branches because only one side can execute. Existing node and domain idempotency keys protect each
selected effect from duplicate worker or receipt delivery.

If a worker stops after the first selected effect, replay resumes from the completed node and
executes only the missing second effect. If it stops before unselected evidence is complete, replay
adds only the missing skipped attempts. The decision is always recomputed from the immutable,
privacy-safe trigger input and cannot change between retries.

## Authoring experience

The list builder starts a branch from Trigger, Condition, one Yes effect and one No effect. While
the branch is active, a dedicated Yes/No effect palette can append one distinct internal effect to
either side. Branch steps are visibly labeled, general reordering remains locked, and only the
second/terminal effect can be removed without first returning to a linear gate.

Safe test mode follows the same bounded branch, simulates the one or two selected effects and marks
every unselected step as skipped without changing a business record.

## Fail-closed boundary

Three-or-more-step branch bodies, repeated effect kinds within one selected body, multiple or
nested Conditions, Delay/Wait inside a branch, branch merging, more than two outcomes, arbitrary
fan-out and external/customer actions remain blocked before a live effect.

No route, permission, migration, queue, provider configuration or customer-send authority is
added. Migration head remains `0048_automation_wait_subscriptions` (**49 revisions**) and OpenAPI
remains **211 paths**.

## Validation

- Live runtime plus safe-test runtime: **48/48 passed**.
- Combined Automation live/runtime/API/migration regression: **75/75 passed**.
- Focused Automation UI: **21/21 passed**; frontend lint and TypeScript pass.
- Static profile: **6/6 passed**; strict mypy covers **305 source files**; OpenAPI is synchronized.
- Complete release profile: **23/23 passed in 609.3s**, including **1518 backend tests with zero
  skips**, **40 frontend files / 831 tests**, production build, SAST/dependency/source/image scans,
  certified WAHA runtime, exact image contracts and CycloneDX SBOMs. `AutomationPage` is **48.38 kB
  / 12.24 kB gzip**.
- Automation remains **99%**: multiple/nested Conditions, branch Delay/Wait, longer branch bodies,
  branch merging, external/customer actions, recipient/team routing and operational reconciliation
  remain future work.
