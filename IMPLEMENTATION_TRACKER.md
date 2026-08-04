# Implementation Tracker (canonical)

> GitHub at the latest approved HEAD is the repository source of truth. Keep repository-verifiable
> engineering evidence separate from host/provider/runtime acceptance.

_Last updated: 2026-08-05 · M13-06A Provider-neutral Sync & Media Persistence Foundation is Repository Validated. Live provider-dependent M13-06 behavior remains blocked._

## Current state

- **Branch:** `ui/taste-modernization`
- **Starting HEAD:** `2386b50bc1110e88f346ddff028cf1e017ad2503`
- **Release:** `1.0.0-rc1`
- **Migration/OpenAPI:** `0040_channel_sync_media_foundation` · 200 paths
- **Current milestone:** `M13-06A — Provider-neutral Sync & Media Persistence Foundation — REPOSITORY VALIDATED`
- **Module 13 completion:** `44%` evidence-based estimate
- **Provider selection:** WAHA evaluation requires additional evidence; no provider is certified or registered
- **Next milestone:** Provider certification host evidence; live M13-06 remains blocked
- **Last synchronized:** `2026-08-05T01:17:00+05:30`

## Delivered

### M13-06A Provider-neutral Sync & Media Persistence Foundation

- Added inert organization-scoped history checkpoints and endpoint-scoped provider media references from the frozen data model.
- Added bounded progress/count constraints, opaque non-secret cursor metadata, expiry/verification facts, optimistic concurrency and tenant-scoped repositories.
- Extended only the existing capability vocabulary with `history_sync`; no adapter implementation or provider branch exists.
- Additive migration `0040_channel_sync_media_foundation`; no API, generated-contract, queue, dependency or frontend source change.

### M13-05 QR Pairing & Provider Runtime Foundation

- Provider-neutral runtime metadata/lifecycle/event/health contracts and a runtime registry over the existing adapter seam.
- Tenant-scoped runtime registration, discovery and ownership; durable capability observations, health/lifecycle reports, heartbeat, restart policy and recovery metadata on the existing `ChannelSession` authority.
- No-store pairing lifecycle with constrained state/reason/timestamp facts only; no QR payload, image, token, protocol credential or login implementation.
- Lease/fencing and optimistic-concurrency enforcement for runtime reports; holder-specific observations reset safely when runtime ownership changes.
- Disabled-by-default runtime/pairing flags, dedicated permissions, Audit coverage and bounded pairing-expiry processing.
- Additive migration `0039_qr_pairing_provider_runtime_foundation`; no API, generated-contract or frontend source change.

### Preserved M13-01 through M13-04 authorities

- Existing `ChannelAdapter`, provider metadata/capability registries, canonical Contact identity, persistent connection/endpoint/encrypted-secret records and durable session lifecycle/lease/fencing remain authoritative.
- No provider implementation, duplicate persistence authority or shared CRM/message/UI authority was added.

## Validation

- Ruff PASS.
- Strict mypy PASS.
- Focused channel/sync/media/migration suite: 18 PASS.
- Full backend suite: 979 PASS in workflow `30946554198`.
- Migration validation PASS at `0040_channel_sync_media_foundation`.
- OpenAPI semantic equality PASS with 200 paths and no M13-05 route/schema/client change; the untouched baseline retains a pre-existing key-order-only exporter mismatch under the current dependency resolver.
- Generated TypeScript client PASS with no drift.
- Python dependency audit, Bandit high-severity and tracked-source vulnerability/secret/IaC scan PASS.
- Frontend production audit high threshold, ESLint, TypeScript, 34 files / 661 tests and production build PASS with unchanged source.
- Bundle output remains unchanged: CSS 49.90/9.90 kB gzip, main 733.62/178.16 kB gzip and Operational Dashboard 31.96/8.61 kB gzip.
- Exact sixteen-file implementation boundary PASS before governance; no API, frontend, provider adapter, messaging, synchronization or M13-06 file changed.

## Explicitly absent

QR image generation/scanning, WhatsApp login/protocol, provider adapters, live event ingestion,
history execution, media transfer/processing, sending, incoming webhooks, routing, Inbox/Customer
360/Analytics changes, public runtime/pairing/sync APIs and provider-specific tables are absent.

## Remaining work

- Target-host MySQL migration and rollback evidence.
- Real multi-node runtime/lease/fencing contention and stale-runtime recovery validation.
- Runtime supervisor, heartbeat, reconnect/re-authentication and alerting commissioning.
- Production KMS custody for referenced provider credentials.
- Representative tenant/RBAC/feature-flag rollout and operator acceptance.
- Provider certification host evidence and all live M13-06 inbound/history/media execution plus later messaging/operator milestones.

## Stop rule

Do not begin any live M13-06 QR image/login, provider adapter, event ingestion, history execution,
media transfer, messaging, webhook, routing, Inbox, Customer 360 or Analytics work until provider
certification and separate owner authorization. M13-06A adds persistence only.
