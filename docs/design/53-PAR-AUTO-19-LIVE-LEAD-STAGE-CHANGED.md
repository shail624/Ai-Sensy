# PAR-AUTO-19 — Live Lead-Stage Changed Automation

**Status:** Repository Implemented  
**Date:** 2026-08-23  
**Scope:** Consume the authoritative Reactivation transition fact as a bounded live Automation
trigger and same-customer Wait event

## Decision

`lead.stage_changed` is now live on the bounded Automation runtime. The Reactivation service
remains the only status-transition authority and continues to append its immutable
`reactivation.stage.transitioned` Business Event in the same transaction as case state, stage
history, Audit, Timeline and owner Notification evidence. Automation treats that existing fact as
the approved `lead.stage_changed` alias; it does not append a duplicate CRM event or create a
parallel pipeline authority.

## Privacy-safe projection

The immutable domain event may retain the operator's transition reason for governed evidence.
Automation receives only `from_stage`, `to_stage` and the tenant-checked public Contact ID. The
reason, internal case/stage row identifiers and other private Reactivation state are not copied
into the run input, condition evidence, Task or Notification.

The new live-safe condition fields are `payload.from_stage` and `payload.to_stage`, using the
existing `eq`, `ne`, `contains` and `exists` operators. Unsupported fields/operators still fail
closed before an effect.

## Bounded trigger path

A clean published Lead stage changed path may use:

`Trigger → optional Condition → optional Delay/Wait → one to four distinct effects`

The allowed effects are Create task, Apply tag, Remove tag and internal Notification. A created
Task is linked to the Contact and active publisher; it has no fabricated Conversation link.
Human handoff and Assignment require a real Conversation and remain rejected. Branches, repeated
effect kinds, larger graphs, campaigns, webhooks, customer messages and external actions remain
blocked.

## Wait and recovery

The existing durable Wait matcher now accepts `lead.stage_changed`. Only a future immutable stage
transition in the same organization and Contact, after the Wait start and before its deadline, may
resume the original receipt/run/checkpoints. Wrong-Contact, early, duplicate and replayed events
converge through the existing subscription and node-attempt evidence. The minute receipt heartbeat
continues to own dispatch recovery and timeout resume; no new queue or long broker timer is added.

## API, persistence and provider boundary

No route, permission, migration, queue, provider configuration or customer-send authority is
added. Migration head remains `0048_automation_wait_subscriptions` (**49 revisions**) and OpenAPI
remains **211 paths**. The change is additive over the existing event ledger, Automation receipt,
Task, Tag, Notification and Reactivation authorities.

## Validation

- Live Lead-stage trigger and Wait-focused Automation runtime: **35/35 passed**.
- Combined Automation definition/runtime, Reactivation service/API and migration regression:
  **56/56 passed**.
- Focused Automation UI: **19/19 passed**.
- Static profile: **6/6 passed**; strict mypy covers **305 source files**; OpenAPI remains current.
- Complete release profile: **23/23 passed in 389.1s**, including **1512 backend tests with zero
  skips**, **40 frontend files / 829 tests**, production build, SAST/dependency/source/image scans,
  certified WAHA runtime, exact image contracts and CycloneDX SBOMs. `AutomationPage` is **42.56 kB
  / 10.49 kB gzip**.
- Completion remains **99%**: general branching, external/customer actions, recipient/team routing
  and operational reconciliation remain future work.
