# Project State

> Current repository snapshot. GitHub is the implementation source of truth. `HEAD` is symbolic
> because a commit cannot embed its own final hash; resolve it after push with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `ui/taste-modernization` |
| M13-01 starting baseline | `8b878bdbd21877cf3f77eac5e9bb209d6b6022be` (`docs(omnichannel): freeze M13-00 implementation contract`) |
| Current Git HEAD | `HEAD` (M13-02 closeout; resolve after push) |
| Current milestone | `M13-02 — Customer Identity Resolution — REPOSITORY VALIDATED` |
| Current phase | `Exact Contact identity convergence and restricted manual review delivered; M13-03 unstarted` |
| Repository version | `1.0.0-rc1` |
| Migration head | `0036_customer_identity_resolution` (36 linear revisions) |
| OpenAPI | `3.1.0` · `200` paths · generated TypeScript authority current |
| Backend evidence | Ruff PASS · strict mypy PASS across 271 source files · 22 focused tests PASS · 961 full pytest tests PASS |
| Frontend evidence | Unchanged source; production audit high threshold PASS · ESLint PASS · TypeScript PASS · 34 Vitest files / 661 tests PASS · production build PASS |
| Bundle evidence | Unchanged: main `733.62 kB` / `178.16 kB` gzip; Operational Dashboard `31.96 kB` / `8.61 kB` gzip; existing >500 kB warning remains |
| M13 contract | ADR-0020 and Design Document 33 remain frozen and authoritative |
| Module 13 implementation | `16%` evidence-based estimate: generic foundation plus exact Customer identity convergence |
| QR provider | Not selected; Required evaluation remains external |
| Next Module 13 milestone | `M13-03`; not started |
| Host evidence | Not applicable to this backend-only non-executable foundation; no Host Validated or Production Ready claim |
| Worktree expectation | Seven foundation/test files plus required governance only; no migration, route, generated contract, dependency, provider, frontend or runtime change |
| Last update | `2026-08-04T15:24:00+05:30` (Asia/Kolkata) |

## M13-01 delivered foundation

## M13-02 delivered identity resolution

- Added exact organization/namespace/scope/value identity normalization and immutable Contact ownership.
- Added ambiguity/conflict detection, tenant-scoped review queue and non-destructive merge recommendations.
- Added explicit approve/reject decisions with row-version checks, RBAC, feature flag, Audit and Timeline evidence.
- Added migration `0036_customer_identity_resolution`, seven API paths and regenerated OpenAPI/client authority.
- No Contact merge is executed and no identity ownership is moved by this milestone.


- Added immutable provider-independent communication intent, communication policy, channel
  metadata, health and lifecycle contracts plus shared enums and validation.
- Added thread-safe provider and capability catalogues that store metadata only and delegate
  adapter creation to the existing `ChannelAdapter` registry.
- Added fail-closed communication-policy evaluation over organization scope, channel family,
  purpose, origin, bulk behavior and required capabilities.
- Added disabled-by-default `omnichannel_connections_read` and
  `omnichannel_connections_write` scaffolding over the existing organization-scoped
  `feature_flags` authority, with organization overrides taking precedence over global rows.
- Added typed dependency-injection composition without registering a provider or changing
  application startup behavior.

## Preserved boundaries

- No QR pairing, session login, WhatsApp Web runtime, Meta runtime, history synchronization,
  live messaging, provider adapter, provider dependency or provider-specific branch exists.
- No Contact, Customer 360, Timeline, Inbox, Notification Center, Analytics, media, message,
  audit or `ChannelAdapter` authority was duplicated.
- No model table, Alembic revision, API route, OpenAPI document, generated client, package,
  frontend source, queue, deployment or feature exposure changed.
- Provider metadata catalogues are empty by default and feature flags are off when absent.

## Validation boundary

Repository validation proves domain invariants, policy decisions, registry parity, flag
precedence, DI stability, lint, typing, full backend regression and unchanged frontend build.
It does not prove provider certification, persisted connection lifecycle, browser/operator
workflows, runtime health, production performance or disaster recovery.

## Required remaining contract work

Design Document 33's persistent channel connection, endpoint, secret and Meta-backfill work
remains Required and unimplemented. The owner-approved M13-01 scope for this commit is the
generic in-process foundation only. The persistence/backfill work is not silently moved into
M13-02 and requires explicit sequencing before provider or runtime milestones.

## Existing UI modernization state

UI-TASTE-03A remains implemented and repository-validated with authenticated host review
pending. M13-01 does not alter the UI modernization sequence.

## Maintenance rule

Stop after M13-02. Do not begin M13-03, persistence/backfill work, provider selection or any
provider/runtime implementation without a separate explicit owner instruction.
