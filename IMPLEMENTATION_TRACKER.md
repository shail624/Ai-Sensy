# Implementation Tracker (canonical)

> GitHub at the latest approved HEAD is the repository source of truth. Keep repository-verifiable
> engineering evidence separate from authenticated host visual acceptance.

_Last updated: 2026-08-04 · M13-00 Architecture & Provider Lock is documentation-complete and
repository-validated. Module 13 implementation has not started._

## Current state

- **Branch:** `ui/taste-modernization`
- **M13-00 baseline:** `7e503a3f2e1d35d54548d9d8fe95e82591e26be1`
- **Release:** `1.0.0-rc1`
- **Migration/OpenAPI:** `0035_notification_center` · 193 paths · unchanged
- **Product source:** unchanged; no backend, frontend, API, migration, generated client,
  dependency, route, queue, runtime or deployment implementation
- **Current milestone:** `M13-00 — Architecture & Provider Lock — REPOSITORY VALIDATED`
- **Contract:** ADR-0020 + Design Document 33 — accepted and frozen
- **Provider selection:** Required external gate pending; no candidate is claimed
- **Module 13 implementation:** `0%`
- **Next Module 13 milestone:** `M13-01` — not authorized
- **Existing roadmap next implementation:** `UI-TASTE-03B` — previously approved, not started
- **Host validation:** not applicable to documentation-only M13-00; no higher status claimed

## M13-00 implementation contract

| Contract area | Frozen result |
|---|---|
| Architecture decision | One existing capability-based ChannelAdapter; one CRM/Contact/ledger; separate endpoint conversations under one Customer 360 |
| Provider behavior | Meta official capabilities remain official; QR is restricted to approved declared human/session/history/media capabilities |
| Provider selection | Required pass/fail criteria frozen; legal, stable IDs, replay, ambiguous-send reconciliation, session security/recovery, history, media, health and support must pass |
| Security | Separate encrypted secret types, write-only APIs, short-lived QR, RBAC/object authorization, organization isolation, lease/fencing and redacted evidence |
| Session lifecycle | Durable desired/observed state, legal transition matrix, one active holder, bounded reconnect and explicit re-authentication |
| Identity | Exact organization/namespace/scope/value resolution; no fuzzy auto-merge; one provider identity belongs to one active Contact |
| API | Additive `/api/v1` connection, endpoint, auth-session, device, health, history and conversation-send resources; current Meta APIs remain compatible |
| Database | Eight approved generic records plus additive links/backfills; expand/backfill/dual-write/verify/switch/contract; migration head unchanged in M13-00 |
| Operations | Disabled-by-default flags, staged Meta parity then QR pilots, explicit rollback, DR, metrics, alerts and runbook evidence |
| Quality | Repository, security, performance, browser, accessibility, UX, operator and production gates mapped to future implementation milestones |

## Verified gaps

### Required

- Select and approve a concrete QR provider using the frozen evidence matrix.
- Complete legal/policy/data-processing review.
- Select production key management and session-runtime deployment topology.
- Verify Meta backfill cardinality, high-volume migration/query plans and provider-scoped
  idempotency before the affected implementation milestone.
- Define the restricted identity-conflict workflow and ratify target RPO/RTO.
- Satisfy recorded prerequisite workflows and obtain a separate owner instruction.

### Recommended

- Step-up authentication for pairing/credential rotation.
- Formal provider support SLA, conformance harness, per-connection capacity model and operator runbook.

### Future Enhancement

- Calls, presence, typing, edit/delete synchronization, advanced interactions, additional
  providers and expanded device administration. None are current Module 13 requirements.

## Consistency decisions

- Existing `ChannelAdapter` remains the only adapter abstraction; optional provider operations
  use the existing capability mechanism.
- ADR-0020 is the later owner decision that permits Instagram only as future evaluation scope;
  it does not authorize implementation and does not reopen excluded SaaS/ads/payments/commerce scope.
- The current private deployment remains organization-scoped and self-hosted; organization
  predicates remain mandatory even though public multi-tenant SaaS is excluded.

## Validation boundary

- PASS: required headings, contract areas, governance links and gap classifications exist.
- PASS: documentation agrees with existing schema/API/channel/CRM authorities and records
  intentional additive migrations without modifying them.
- PASS: changed-file boundary is documentation only.
- Existing application test and bundle evidence remains unchanged because product source is unchanged.
- Browser, screenshots, operator journey, runtime performance, provider certification and DR
  evidence belong to later executable milestones and are not claimed by M13-00.

## Next-step rule

Stop after M13-00. Do not begin M13-01. Any architecture/scope/abstraction/milestone-order
deviation requires owner approval and an additive ADR.
