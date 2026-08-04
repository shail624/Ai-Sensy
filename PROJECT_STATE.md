# Project State

> Current repository snapshot. GitHub is the implementation source of truth. `HEAD` is symbolic
> because a commit cannot embed its own final hash; resolve it after push with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `ui/taste-modernization` |
| M13-04 starting baseline | `9d8f379f09719820c847be2b7c7df301e1617977` (`feat(channels): persist channel connections`) |
| Current Git HEAD | `HEAD` (M13-04 closeout; resolve after push) |
| Current milestone | `M13-04 — QR Session Manager Foundation — REPOSITORY VALIDATED` |
| Current phase | `Provider-neutral durable session state and lease/fencing foundation delivered; M13-05 unstarted` |
| Repository version | `1.0.0-rc1` |
| Migration head | `0038_qr_session_manager_foundation` (38 linear revisions) |
| OpenAPI | `3.1.0` · `200` paths · generated TypeScript authority unchanged |
| Backend evidence | Ruff PASS · strict mypy PASS across 279 source files · 7 focused session/migration tests PASS · 970 full pytest tests PASS |
| Frontend evidence | Unchanged source; production audit high threshold PASS · ESLint PASS · TypeScript PASS · 34 Vitest files / 661 tests PASS · production build PASS |
| Bundle evidence | Unchanged: main `733.62 kB` / `178.16 kB` gzip; CSS `49.90 kB` / `9.90 kB` gzip; Operational Dashboard `31.96 kB` / `8.61 kB` gzip; existing >500 kB warning remains |
| M13 contract | ADR-0020 and Design Document 33 remain frozen and authoritative |
| Module 13 implementation | `32%` evidence-based estimate: generic channel contracts, exact Customer identity, persistent connection records and provider-neutral session control-plane foundation |
| QR provider | Not selected; no provider adapter or live session exists |
| Next Module 13 milestone | `M13-05`; not started |
| Host evidence | Target-host MySQL migration, multi-node lease/fencing contention, runtime heartbeat/expiration/restart/recovery monitoring, KMS secret-reference custody and staged tenant/RBAC/flag commissioning remain pending; no Host Validated or Production Ready claim |
| Worktree expectation | Eleven session/model/repository/service/permission/migration/test files plus six required governance records; no API, generated contract, provider adapter/runtime, frontend, messaging, synchronization or M13-05 change |
| Last update | `2026-08-04T19:05:00+05:30` (Asia/Kolkata) |

## M13-04 delivered session-manager foundation

- Added provider-neutral `SessionManager` contracts and durable `ChannelSession` records linked to the existing organization-owned `ChannelConnection`; no duplicate connection, endpoint, credential or message storage was introduced.
- Added registration/discovery/ownership, governed lifecycle transitions, factual health, heartbeat and expiration, recovery metadata, restart policy, capability references and Audit evidence.
- Added database-backed leases, fencing tokens, row-version concurrency protection and tenant-scoped locking/release semantics for future multi-runtime safety.
- Added disabled-by-default session read/write feature flags and `channels:read/manage/diagnose` RBAC enforcement; metadata rejects secret-shaped material and stores secret references only.
- Added additive migration `0038_qr_session_manager_foundation`; OpenAPI and generated client remain unchanged at 200 paths.

## Preserved completed foundations

- M13-01 provider-neutral contracts, M13-02 Contact identity resolution and M13-03 connection/endpoint/encrypted-secret persistence remain authoritative and unchanged except for required model, permission and migration registration.
- Existing `ChannelAdapter`, Contact, Inbox, Customer 360, Timeline, Notification Center, Analytics, media, message and Audit authorities remain unchanged.

## Preserved boundaries

- No QR code generation/scanning, WhatsApp login, provider adapter, executable session runtime, message/history synchronization, sending, inbound webhook runtime, routing, Inbox or Customer 360 change exists.
- No public API route, OpenAPI path, generated client surface, frontend source, package dependency, provider-specific table or runtime message storage was added.
- Session metadata stores no plaintext provider secret; provider identifiers remain owned by existing connection records.

## Validation boundary

Repository validation proves lifecycle/state-machine rules, tenant/RBAC/flag boundaries, ownership,
secure metadata, database lease/fencing and optimistic concurrency behavior, heartbeat/expiration,
recovery/restart metadata, Audit serialization, additive migration, lint, typing, full backend regression
and unchanged frontend/OpenAPI builds. It does not prove target-host multi-node contention, a live provider
session, real runtime heartbeats, provider certification, production monitoring, disaster recovery or rollout.

## Required remaining contract work

Target-host session commissioning, provider selection/certification, QR pairing, provider adapters,
inbound/history, outbound messaging and unified operator experience remain later gated milestones.
M13-05 is not started.

## Existing UI modernization state

UI-TASTE-03A remains implemented and repository-validated with authenticated host review pending.
M13-04 changes no frontend source or UI modernization sequence.

## Maintenance rule

Stop after M13-04. Do not begin M13-05, provider selection/backfill, QR pairing/login, provider adapters/runtime,
messaging, synchronization, webhook, routing or UI work without a separate explicit owner instruction.
