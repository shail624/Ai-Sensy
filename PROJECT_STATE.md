# Project State

> Current repository snapshot. GitHub is the implementation source of truth. `HEAD` is symbolic
> because a commit cannot embed its own final hash; resolve it after push with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `ui/taste-modernization` |
| M13-05 starting baseline | `5d7ea154588418410611de4f568e978c2e3caba9` (`feat(channels): add session manager foundation`) |
| Current Git HEAD | `HEAD` (M13-05 closeout; resolve after push) |
| Current milestone | `M13-05 — QR Pairing & Provider Runtime Foundation — REPOSITORY VALIDATED` |
| Current phase | `Provider-neutral runtime registration, pairing state and runtime/session integration delivered; M13-06 unstarted` |
| Repository version | `1.0.0-rc1` |
| Migration head | `0039_qr_pairing_provider_runtime_foundation` (39 linear revisions) |
| OpenAPI | `3.1.0` · `200` paths · no public runtime/pairing route or generated TypeScript change |
| Backend evidence | Ruff PASS · strict mypy PASS · 20 focused channel/session/runtime/migration tests PASS · 976 full pytest tests PASS |
| Frontend evidence | Unchanged source; production audit high threshold PASS · ESLint PASS · TypeScript PASS · 34 Vitest files / 661 tests PASS · production build PASS |
| Bundle evidence | Unchanged: main `733.62 kB` / `178.16 kB` gzip; CSS `49.90 kB` / `9.90 kB` gzip; Operational Dashboard `31.96 kB` / `8.61 kB` gzip; existing >500 kB warning remains |
| M13 contract | ADR-0020 and Design Document 33 remain frozen and authoritative |
| Module 13 implementation | `40%` evidence-based estimate: generic contracts, exact identity, persistent connections, session control plane, provider-neutral runtime registry and no-store pairing lifecycle |
| QR provider | Not selected; no provider adapter, QR image, WhatsApp protocol or live provider login exists |
| Next Module 13 milestone | `M13-06`; not started |
| Host evidence | Target-host MySQL migration, real multi-node runtime/lease contention, provider certification, runtime supervision/monitoring, KMS custody and staged tenant/RBAC/flag commissioning remain pending; no Host Validated or Production Ready claim |
| Worktree expectation | Sixteen runtime/session/model/repository/service/permission/migration/test files plus six required governance records; no API, generated contract, frontend, provider adapter, messaging, synchronization or M13-06 change |
| Last update | `2026-08-04T22:45:00+05:30` (Asia/Kolkata) |

## M13-05 delivered provider runtime and pairing foundation

- Added provider-neutral runtime metadata, lifecycle, event and health contracts plus a thread-safe runtime registry that resolves executable behavior only through the existing `ChannelAdapter` seam.
- Added `ProviderRuntimeManager` registration/discovery/ownership, capability publication, health/lifecycle reporting, heartbeat integration, restart/recovery metadata and durable `ChannelSession` projection.
- Added a no-store `PairingManager` abstraction with governed `UNPAIRED`, `PAIRING_REQUESTED`, `PAIRING_AVAILABLE`, `PAIRING_EXPIRED`, `PAIRING_CANCELLED`, `PAIRED` and `ACTIVE` transitions; no QR payload, image, token or provider credential is persisted.
- Reused M13-04 lease/fencing, optimistic concurrency, session ownership, health, heartbeat, restart/recovery and Audit authorities rather than creating a second runtime truth table.
- Added disabled-by-default runtime/pairing flags, runtime/pairing RBAC permissions, additive migration `0039_qr_pairing_provider_runtime_foundation` and tenant-scoped expiry sweeps bounded to 1–1000 records.

## Preserved completed foundations

- M13-01 provider metadata/capability registries, M13-02 Contact identity, M13-03 connection/endpoint/encrypted-secret persistence and M13-04 session lifecycle/lease/fencing remain authoritative.
- Existing Contact, Inbox, Customer 360, Timeline, Notification Center, Analytics, message, media and Audit authorities remain unchanged.

## Preserved boundaries

- No QR image generation/scanning, WhatsApp login or protocol, provider adapter, history/message synchronization, incoming/outgoing messages, webhook runtime, routing, Inbox, Customer 360, Analytics or frontend behavior exists.
- No public API route, OpenAPI path, generated client surface, provider dependency, provider-specific table or runtime message storage was added.
- Pairing persistence contains state, timestamps and constrained reason codes only; secret references continue to use existing encrypted credential records.

## Validation boundary

Repository validation proves provider-neutral registry/runtime/pairing contracts, tenant/RBAC/flag
boundaries, durable session integration, lease/fencing enforcement, bounded expiry, health, heartbeat,
restart/recovery metadata, Audit redaction, additive migration, lint, typing, full regressions, source
security scans and unchanged frontend/API semantics. OpenAPI generation under the current unpinned
FastAPI/Pydantic resolver has a pre-existing JSON key-order mismatch at the untouched M13-04 baseline;
semantic schemas are equal and M13-05 introduces no route or schema. It does not prove a live provider,
QR scan/login, target-host multi-node runtime behavior, provider certification, production monitoring,
disaster recovery or rollout.

## Required remaining contract work

Target-host commissioning, provider selection/certification, live inbound/history/media, outbound
messaging and unified operator experience remain later gated milestones. M13-06 is not started.

## Existing UI modernization state

UI-TASTE-03A remains implemented and repository-validated with authenticated host review pending.
M13-05 changes no frontend source or UI modernization sequence.

## Maintenance rule

Stop after M13-05. Do not begin M13-06, provider selection/backfill, QR image/login, provider adapters,
messaging, synchronization, webhook, routing or UI work without a separate explicit owner instruction.
