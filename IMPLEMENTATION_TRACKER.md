# Implementation Tracker (canonical)

> GitHub at the latest approved HEAD is the repository source of truth. Keep repository-verifiable
> engineering evidence separate from host/provider/runtime acceptance.

_Last updated: 2026-08-04 · M13-03 Persistent Channel Connections & Endpoint Records is Repository Validated. M13-04 has not started._

## Current state

- **Branch:** `ui/taste-modernization`
- **Starting HEAD:** `283ebe83b53a510ce671f150bfe14fe38a5292f6`
- **Release:** `1.0.0-rc1`
- **Migration/OpenAPI:** `0037_persistent_channel_connections` · 200 paths
- **Current milestone:** `M13-03 — Persistent Channel Connections & Endpoint Records — REPOSITORY VALIDATED`
- **Module 13 completion:** `24%` evidence-based estimate
- **Provider selection:** pending; no provider is registered
- **Next milestone:** `M13-04` — not started
- **Last synchronized:** `2026-08-04T17:45:00+05:30`

## Delivered

### M13-03 Persistent Channel Connections & Endpoint Records

- Provider-neutral persistent connection, endpoint and encrypted-secret entities owned by the existing Organization authority.
- Immutable provider identifiers, configuration/provider/endpoint metadata, desired/observed lifecycle, factual health, Audit references, soft delete and optimistic locking.
- AES-GCM secret-cipher abstraction with key version, secret version, rotation lineage, revocation, expiry/access evidence and redacted representations; plaintext never enters metadata or Audit.
- Tenant-scoped repositories and disabled-by-default read/write feature gates; no public secret or connection API was introduced.
- Additive migration `0037_persistent_channel_connections`; OpenAPI/client authority remains unchanged at 200 paths.

### Preserved M13-01 and M13-02 authorities

- `ChannelAdapter` remains the sole adapter/factory seam and no provider implementation is registered.
- Canonical Contact identity, immutable identity aliases, conflict review, recommendations, Audit/Timeline and all completed CRM/UI authorities remain unchanged.

## Validation

- Ruff PASS.
- Strict mypy PASS across 275 source files.
- Focused persistence suite: 4 PASS.
- Full backend suite: 965 PASS in validation run `30907651227`.
- Migration upgrade/downgrade/upgrade PASS at `0037_persistent_channel_connections`.
- OpenAPI generation and generated client PASS with 200 paths and no generated-authority drift.
- Python dependency audit and Bandit high-severity gate PASS.
- Frontend production audit high threshold, ESLint, TypeScript, 34 files / 661 tests and production build PASS with unchanged source.
- Bundle output remains unchanged: CSS 49.90/9.90 kB gzip, main 733.62/178.16 kB gzip and Operational Dashboard 31.96/8.61 kB gzip.
- Exact nine-file persistence boundary PASS before governance; no API, frontend, provider runtime or M13-04 file changed.

## Explicitly absent

QR login/pairing/session runtime, provider adapters, provider-specific backfill, history/message sync,
live messaging, webhooks, routing, Inbox/Customer 360 UI, public connection/secret APIs, frontend
source changes and generated-contract changes are absent.

## Remaining work

- Target-host MySQL migration and rollback evidence.
- Production encryption-key/KMS custody, rotation and revocation commissioning.
- Representative multi-tenant persistence, soft-delete/restore-policy and feature-flag rollout review.
- Provider selection/certification and all M13-04+ runtime/operator milestones.

## Stop rule

Do not begin M13-04 or any provider/runtime/QR/messaging/synchronization/webhook/routing/UI work.
Any architecture, scope, abstraction or milestone-order deviation requires owner approval and an additive ADR.
