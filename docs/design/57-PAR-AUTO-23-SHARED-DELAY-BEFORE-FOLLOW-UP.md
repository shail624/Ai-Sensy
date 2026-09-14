# PAR-AUTO-23 — Shared Delay Before Follow-Up

**Status:** Repository Implemented  
**Date:** 2026-08-23  
**Scope:** Add one durable pause after an exact Yes/No convergence without enabling branch-local timers

## Decision

One event-backed live Automation may now use this exact topology:

`Trigger → Condition → Yes effect [→ Yes effect] ↘`

`                                              Shared Delay → Shared effect`

`Trigger → Condition → No effect [→ No effect]  ↗`

The shared Delay is optional and exists only immediately before the existing terminal shared
follow-up. Both branch terminals must point to it, it must point to exactly one trigger-safe shared
effect, and the existing ceiling of four effects remains unchanged. The Delay is not an effect and
does not increase that ceiling.

## Durable execution and replay

Only the selected branch executes before the shared Delay. The first delivery creates one running
Delay attempt, records its immutable resume deadline and leaves the shared effect untouched. Early
or duplicate delivery reuses that attempt and the completed selected-branch checkpoints.

At or after the deadline, the same receipt completes the Delay, executes the shared effect once and
records every alternate-only branch node as skipped. The shared Delay and effect belong to both
path projections, so neither can be misclassified as unselected.

## Authoring experience

After an operator adds one `After both` follow-up, the builder enables `Add shared delay before
follow-up`. The new node is inserted before the follow-up, labeled `Shared delay` and uses the
existing 60-second-to-30-day Delay inspector. Removing it reconnects both branch terminals directly
to the shared effect. Removing the follow-up also removes its dependent shared Delay so the graph
cannot retain a terminal timer.

Safe test mode simulates the selected branch, shared Delay and shared follow-up while skipping only
the alternate-only nodes and changing no business state.

## Fail-closed boundary

Branch-specific Delay/Wait, a Delay without a shared effect, multiple delays, Wait at the merge,
arbitrary or multiple merges, nested/multiple Conditions, longer branch bodies, loops, external/
customer actions and recipient/team routing remain blocked.

No route, permission, migration, queue, provider configuration or customer-send authority is
added. Migration head remains `0048_automation_wait_subscriptions` (**49 revisions**) and OpenAPI
remains **211 paths**.

## Validation

- Live runtime plus safe-test runtime: **54/54 passed**.
- Automation/API/trigger/Schedule/migration regression: **77/77 passed**.
- Focused Automation UI: **23/23 passed**.
- Complete backend: **1524/1524 passed** in **475.70s**.
- Complete frontend: **40 files / 833 tests passed**.
- Static profile: **6/6 passed**; strict mypy covers **305 source files**; OpenAPI is synchronized.
- Production build passes; `AutomationPage` is **52.47 kB / 13.23 kB gzip**.
- The Docker/security-backed `release` profile was not rerun because the required approval service
  rejected the escalation after its usage allowance was exhausted. The last complete release
  certification remains PAR-AUTO-22 at **23/23 in 685.9s**; no release success is inferred for this
  changed tree.
- Automation remains **99%**: branch-specific Delay/Wait, arbitrary/multiple merges, multiple/
  nested Conditions, longer bodies, external/customer actions, recipient/team routing and
  operational reconciliation remain future work.
