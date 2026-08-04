# Implementation Tracker (canonical)

> GitHub at the latest approved HEAD is the repository source of truth. Keep repository-verifiable
> engineering evidence separate from host/provider/runtime acceptance.

_Last updated: 2026-08-04 · M13-05 QR Pairing & Provider Runtime Foundation is Repository Validated. M13-06 has not started._

## Current state

- **Branch:** `ui/taste-modernization`
- **Starting HEAD:** `5d7ea154588418410611de4f568e978c2e3caba9`
- **Release:** `1.0.0-rc1`
- **Migration/OpenAPI:** `0039_qr_pairing_provider_runtime_foundation` · 200 paths
- **Current milestone:** `M13-05 — QR Pairing & Provider Runtime Foundation — REPOSITORY VALIDATED`
- **Module 13 completion:** `40%` evidence-based estimate
- **Provider selection:** pending; no provider adapter or live provider is registered
- **Next milestone:** `M13-06` — not started
- **Last synchronized:** `2026-08-04T22:45:00+05:30`

## Delivered

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
- Focused channel/session/runtime/migration suite: 20 PASS.
- Full backend suite: 976 PASS in workflow `30933007710`.
- Migration validation PASS at `0039_qr_pairing_provider_runtime_foundation`.
- OpenAPI semantic equality PASS with 200 paths and no M13-05 route/schema/client change; the untouched baseline retains a pre-existing key-order-only exporter mismatch under the current dependency resolver.
- Generated TypeScript client PASS with no drift.
- Python dependency audit, Bandit high-severity and tracked-source vulnerability/secret/IaC scan PASS.
- Frontend production audit high threshold, ESLint, TypeScript, 34 files / 661 tests and production build PASS with unchanged source.
- Bundle output remains unchanged: CSS 49.90/9.90 kB gzip, main 733.62/178.16 kB gzip and Operational Dashboard 31.96/8.61 kB gzip.
- Exact sixteen-file implementation boundary PASS before governance; no API, frontend, provider adapter, messaging, synchronization or M13-06 file changed.

## Explicitly absent

QR image generation/scanning, WhatsApp login/protocol, provider adapters, message/history
synchronization, sending, incoming webhooks, routing, Inbox/Customer 360/Analytics changes, public
runtime/pairing APIs and provider-specific tables are absent.

## Remaining work

- Target-host MySQL migration and rollback evidence.
- Real multi-node runtime/lease/fencing contention and stale-runtime recovery validation.
- Runtime supervisor, heartbeat, reconnect/re-authentication and alerting commissioning.
- Production KMS custody for referenced provider credentials.
- Representative tenant/RBAC/feature-flag rollout and operator acceptance.
- Provider selection/certification and all M13-06+ inbound/history/media/messaging/operator milestones.

## Stop rule

Do not begin M13-06 or any live QR image/login, provider adapter, messaging, synchronization, webhook,
routing, Inbox, Customer 360 or Analytics work. Any architecture or scope deviation requires owner approval.
