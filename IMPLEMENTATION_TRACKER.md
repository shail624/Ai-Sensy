# Implementation Tracker (canonical)

> GitHub at the latest approved HEAD is the repository source of truth. Keep repository-verifiable
> engineering evidence separate from host/provider/runtime acceptance.

_Last updated: 2026-08-04 · M13-02 Customer Identity Resolution is Repository Validated. M13-03 has not started._

## Current state

- **Branch:** `ui/taste-modernization`
- **Baseline:** `8b878bdbd21877cf3f77eac5e9bb209d6b6022be`
- **Release:** `1.0.0-rc1`
- **Migration/OpenAPI:** `0036_customer_identity_resolution` · 200 paths
- **Current milestone:** `M13-02 — Customer Identity Resolution — REPOSITORY VALIDATED`
- **Module 13 completion:** `16%` evidence-based estimate
- **Provider selection:** pending; no provider is registered
- **Next milestone:** `M13-03` — not started
- **Last synchronized:** `2026-08-04T15:24:00+05:30`

## Delivered

### M13-02 Customer Identity Resolution

- Canonical Contact-based exact identity resolution with immutable provider/endpoint aliases.
- Tenant-scoped conflict/review queue and non-destructive recommendations with explicit decisions.
- RBAC, disabled-by-default feature flag, Audit/Timeline integration, migration `0036`, 200-path OpenAPI and generated TypeScript authority.
- Repository gates: Ruff PASS, mypy PASS (271 files), 22 focused and 961 full backend tests PASS; frontend lint/type/Vitest/build and migration/client generation PASS.


| Area | Repository result |
|---|---|
| Existing abstraction | `ChannelAdapter` remains the sole adapter/factory seam |
| Shared domain | Communication Intent, Communication Policy, Channel Metadata, Provider Health and Provider Lifecycle immutable contracts |
| Enums | Provider-independent purpose, origin, desired/observed state and health vocabularies |
| Registries | Thread-safe provider metadata and capability registries; adapter resolution delegates to existing `get_adapter` |
| Validation | Connector/text/time/score/capability validation and fail-closed policy evaluation |
| Feature flags | Two frozen generic connection flags resolved through existing global/organization `FeatureFlag` rows; absent means disabled |
| Dependency injection | Cached empty foundation container and request-scoped flag resolver wiring |
| Regression coverage | Seven new foundation tests plus existing channel/config regression suite |

## Validation

- Ruff PASS.
- Strict mypy PASS across 263 source files.
- Focused channel/config suite: 46 PASS.
- Full backend suite: 955 PASS in 260.89 seconds in validation run `30886853478`.
- Frontend production audit high threshold, ESLint, TypeScript, 34 files / 661 tests and
  production build PASS with unchanged source.
- Bundle output is unchanged: CSS 49.90/9.90 kB gzip, main 733.62/178.16 kB gzip and
  Operational Dashboard 31.96/8.61 kB gzip.
- Exact seven-file provider-neutral boundary PASS.

## Explicitly absent

QR pairing, sessions, provider runtimes, provider adapters, history synchronization, live
messaging, database records/migrations, API routes, generated contracts, UI, Contact/Inbox/
Customer 360/Timeline/Notification/Analytics changes and new dependencies are absent.

## Remaining work

- Persistent channel connection, endpoint and secret records plus Meta backfill remain a
  Required frozen-contract gap and need explicit owner sequencing.
- M13-03 session and connection control plane is not started.
- Provider evaluation, runtime, pairing, inbound/history, outbound and unified operator
  experience remain later gated work.

## Stop rule

Do not begin M13-03 or any unassigned persistence/provider work. Any architecture, scope,
abstraction or milestone-order deviation requires owner approval and an additive ADR.
