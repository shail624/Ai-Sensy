# Implementation Tracker (canonical)

> GitHub at the latest approved HEAD is the repository source of truth. Keep repository-verifiable
> engineering evidence separate from host/provider/runtime acceptance.

_Last updated: 2026-08-05 · UI-TASTE-03B Reactivation Operational Hierarchy is Repository Validated. Provider-dependent Module 13 work remains blocked._

## Current state

- **Branch:** `ui/taste-modernization`
- **Starting HEAD:** `5c3414bed1802276e99a9b02605dbde8e1cdcc36`
- **Release:** `1.0.0-rc1`
- **Migration/OpenAPI:** `0040_channel_sync_media_foundation` · 200 paths
- **Current milestone:** `UI-TASTE-03B — Reactivation Operational Hierarchy — REPOSITORY VALIDATED`
- **Reactivation completion:** `94%` evidence-based estimate · **Module 13:** `44%` unchanged
- **Provider selection:** WAHA evaluation requires additional evidence; no provider is certified or registered
- **Next milestone:** `UI-TASTE-04 — Responsive, accessibility, and performance regression`; live M13-06 remains blocked
- **Last synchronized:** `2026-08-05T03:21:50+05:30`

## Delivered

### UI-TASTE-03B Reactivation Operational Hierarchy

- Real Reactivation CRM is the default route; only connected and permission-available KYC,
  Document, and Report destinations remain in primary Reactivation navigation.
- Existing pipeline search/filters are URL-backed and use shared controls; factual All active,
  Due today, Overdue, and Completed work views preserve refresh/share context.
- Existing tenant-scoped stable ordering now supports additive non-negative offset pagination at
  25 cases per page without a new table, service, route, permission, or authority.
- Historical SIM/Activation/Completed/Interested/bulk links resolve to existing filtered CRM or
  Contact import workflows instead of placeholder operational shells.
- Design Document 34 records reuse, originality, responsive/accessibility, security, validation, and
  host-evidence boundaries.


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
- Focused Reactivation pagination/workflow suite: 4 PASS.
- Full backend suite: 980 PASS in workflow `30953600784`.
- OpenAPI/client drift PASS at 200 paths; migration head remains `0040_channel_sync_media_foundation`.
- Frontend production audit high threshold, ESLint, TypeScript, 35 files /
  668 tests and production build PASS.
- E2E TypeScript, Bandit, Python dependency audit, and tracked-source vulnerability/secret/IaC scan PASS.
- Main bundle: 733.97/178.29 kB gzip; Reactivation route:
  82.25/19.37 kB gzip.
- Authenticated representative-data visual/reference, screen-reader/device, and production-scale
  performance evidence: PENDING – Host Machine Validation.
- Exact nineteen-file product/tracking boundary PASS; no provider-specific or live Module 13 file changed.

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

Do not begin live/provider-dependent M13-06 QR image/login, adapter, ingestion, history, media,
messaging, webhook, routing, or provider UI work until certification and separate owner
authorization. Provider-neutral roadmap milestones may proceed in their approved sequence.
