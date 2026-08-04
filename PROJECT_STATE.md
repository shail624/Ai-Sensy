# Project State

> Current repository snapshot. GitHub is the implementation source of truth. `HEAD` is symbolic
> because a commit cannot embed its own final hash; resolve it after push with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `ui/taste-modernization` |
| M13-03 starting baseline | `283ebe83b53a510ce671f150bfe14fe38a5292f6` (`feat(identity): complete customer identity resolution`) |
| Current Git HEAD | `HEAD` (M13-03 closeout; resolve after push) |
| Current milestone | `M13-03 — Persistent Channel Connections & Endpoint Records — REPOSITORY VALIDATED` |
| Current phase | `Provider-neutral persistence foundation delivered; M13-04 unstarted` |
| Repository version | `1.0.0-rc1` |
| Migration head | `0037_persistent_channel_connections` (37 linear revisions) |
| OpenAPI | `3.1.0` · `200` paths · generated TypeScript authority unchanged |
| Backend evidence | Ruff PASS · strict mypy PASS across 275 source files · 4 focused persistence tests PASS · 965 full pytest tests PASS |
| Frontend evidence | Unchanged source; production audit high threshold PASS · ESLint PASS · TypeScript PASS · 34 Vitest files / 661 tests PASS · production build PASS |
| Bundle evidence | Unchanged: main `733.62 kB` / `178.16 kB` gzip; Operational Dashboard `31.96 kB` / `8.61 kB` gzip; existing >500 kB warning remains |
| M13 contract | ADR-0020 and Design Document 33 remain frozen and authoritative |
| Module 13 implementation | `24%` evidence-based estimate: generic foundation, exact Customer identity convergence, and persistent provider-neutral connection records |
| QR provider | Not selected; Required evaluation remains external |
| Next Module 13 milestone | `M13-04`; not started |
| Host evidence | Target-host MySQL migration, production key/KMS custody, representative multi-tenant persistence checks and staged feature-flag commissioning remain pending; no Host Validated or Production Ready claim |
| Worktree expectation | Nine persistence/model/repository/service/migration/test files plus six required governance records; no API, generated contract, dependency, provider runtime, frontend or M13-04 change |
| Last update | `2026-08-04T17:45:00+05:30` (Asia/Kolkata) |

## M13-03 delivered persistence foundation

- Added organization-owned, tenant-scoped `ChannelConnection`, `ChannelEndpoint` and `ChannelSecret` records.
- Added immutable provider identifiers, desired/observed lifecycle, factual health, provider/configuration/endpoint metadata, Audit references, soft deletion and optimistic row versions.
- Added AES-GCM encrypted credential storage behind a provider-neutral secret-cipher abstraction with secret versioning, rotation lineage, revocation and redacted representations.
- Added tenant-scoped repositories and a disabled-by-default feature-gated service; no secret is exposed through an API and plaintext is excluded from metadata and Audit payloads.
- Added additive migration `0037_persistent_channel_connections`; OpenAPI and generated client remain unchanged at 200 paths.

## Preserved completed foundations

- M13-01 provider-neutral contracts/registries/flags/DI and M13-02 Contact identity resolution remain authoritative and unchanged except for model registration required by the additive migration.
- Canonical Contact, Inbox, Customer 360, Timeline, Notification Center, Analytics, media, message and existing `ChannelAdapter` authorities remain unchanged.

## Preserved boundaries

- No QR login/pairing/session runtime, Meta or QR provider adapter, history synchronization, message sync, live messaging, webhook, routing-engine, Inbox or Customer 360 UI work exists.
- No public API route, OpenAPI path, generated client surface, frontend source, package dependency, queue, deployment topology or provider-specific branch was added.
- Provider identifiers are immutable after persistence; absent feature flags fail closed; soft-deleted rows and revoked secrets are excluded by default.

## Validation boundary

Repository validation proves schema/repository/service invariants, tenant isolation, immutable identifiers,
optimistic locking, encrypted credential rotation/revocation, soft deletion, Audit hygiene, migration
upgrade/downgrade/upgrade, lint, typing, full backend regression and unchanged frontend/OpenAPI builds.
It does not prove production KMS/HSM custody, target-host MySQL behavior, provider certification,
runtime sessions, operator workflows, performance, disaster recovery or production rollout.

## Required remaining contract work

Provider selection/certification, provider-specific backfill, session lease/fencing, runtime health,
QR pairing, inbound/history, outbound messaging and unified operator experience remain later gated
milestones. M13-04 is not started.

## Existing UI modernization state

UI-TASTE-03A remains implemented and repository-validated with authenticated host review pending.
M13-03 changes no frontend source or UI modernization sequence.

## Maintenance rule

Stop after M13-03. Do not begin M13-04, provider selection, provider-specific backfill, session/runtime,
QR, messaging, synchronization, webhook, routing or UI work without a separate explicit owner instruction.
