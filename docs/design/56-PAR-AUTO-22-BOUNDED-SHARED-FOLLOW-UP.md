# PAR-AUTO-22 — Bounded Shared Follow-Up

**Status:** Repository Implemented  
**Date:** 2026-08-23  
**Scope:** Allow one exact Yes/No decision to converge without opening arbitrary graph merging

## Decision

One event-backed live Automation may now use this exact topology:

`Trigger → Condition → Yes effect [→ Yes effect] ↘ Shared effect`

`Trigger → Condition → No effect [→ No effect]  ↗`

The shared node is optional, terminal, trigger-safe and reached by both branch terminals. The
existing ceiling of four effects across the graph is unchanged. Each executable path therefore
contains one or two branch effects followed by at most one shared effect.

## Safety and replay

The graph may contain exactly one node with two incoming edges and that node must have no outgoing
edge. Both branches must converge on it; partial, multiple, nested or non-terminal merges fail
closed. Effect kinds remain distinct along each executable path, so a branch cannot repeat the
kind used by the shared follow-up.

Only the selected branch executes. Unselected-only nodes receive durable `skipped` attempts, while
the shared node belongs to both executable path projections and is never classified as unselected.
Existing node/domain idempotency means duplicate receipt or worker delivery reuses one shared
effect. A replay after the selected branch completes resumes at the shared checkpoint without
repeating earlier work.

## Authoring experience

While a bounded split is active, the builder exposes Effect, Yes, No and After controls. `+ Both`
adds one shared follow-up and the node is labeled `After both`. A second step can still be inserted
on either branch before the shared node; the builder rewires that branch terminal to preserve the
single merge. Removing a branch terminal reconnects its predecessor to the shared node, and
removing the shared node returns the graph to two independent terminal bodies.

Safe test mode mirrors the selected branch and shared follow-up without changing business state.

## Fail-closed boundary

Arbitrary or multiple merges, nested/multiple Conditions, longer branch bodies, branch Delay/Wait,
loops, more than two outcomes, arbitrary fan-out and external/customer actions remain blocked
before a live effect.

No route, permission, migration, queue, provider configuration or customer-send authority is
added. Migration head remains `0048_automation_wait_subscriptions` (**49 revisions**) and OpenAPI
remains **211 paths**.

## Validation

- Live runtime plus safe-test runtime: **51/51 passed**.
- Combined Automation live/runtime/API/migration regression: **78/78 passed**.
- Focused Automation UI: **22/22 passed**; frontend lint and TypeScript pass.
- Static profile: **6/6 passed**; strict mypy covers **305 source files**; OpenAPI is synchronized.
- Complete release profile: **23/23 passed in 685.9s**, including **1521 backend tests with zero
  skips** (**498.31s** raw pytest), **40 frontend files / 832 tests**, production build, SAST/
  dependency/source/image scans, certified WAHA runtime, exact image contracts and CycloneDX
  SBOMs. `AutomationPage` is **50.52 kB / 12.77 kB gzip**.
- Automation remains **99%**: arbitrary/multiple merges, multiple/nested Conditions, branch
  Delay/Wait, longer branch bodies, external/customer actions, recipient/team routing and
  operational reconciliation remain future work.
