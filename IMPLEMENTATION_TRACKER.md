# Implementation Tracker (canonical)

> GitHub at the latest approved HEAD is the repository source of truth. Keep repository-verifiable
> engineering evidence separate from host/provider/runtime acceptance.

_Last updated: 2026-08-05 · M13-06B Provider-neutral History & Media Control Plane is Repository Validated. Provider certification still blocks every live history, media, event and adapter behavior._

## Current state

- **Branch:** `ui/taste-modernization`
- **Starting HEAD:** `f9a110d34f2095a3e9dbe61a779825edade38bda`
- **Release:** `1.0.0-rc1`
- **Migration/OpenAPI:** `0041_channel_sync_control_plane` · 200 paths
- **Current milestone:** `M13-06B — Provider-neutral History & Media Control Plane — REPOSITORY VALIDATED`
- **Completion:** Shared Enterprise Design System `94%` · Global Search `85%` · Reactivation `94%` unchanged · Module 13 `48%`
- **Provider selection:** WAHA evaluation requires additional evidence; no provider is certified or registered
- **Next milestone:** `None`; provider certification and separate owner instruction are required before any live M13-06 work
- **Last synchronized:** `2026-08-05T17:00:00+05:30`

## Delivered

### M13-06B Provider-neutral History & Media Control Plane

- Added one provider-neutral service over the existing checkpoint/media-reference persistence; it
  owns no provider call, queue execution, API route, event ingestion, history retrieval or media bytes.
- History checkpoints are feature-gated, permissioned, tenant/object scoped, capability-gated and
  versioned; legal transitions, monotonic progress, cutover/watermark boundaries and restart semantics
  fail closed and emit immutable Audit evidence.
- Provider media identifiers reuse existing `MediaAsset` and `ChannelEndpoint` authorities; registration
  is idempotent, declared media capability is required and factual transfer observations reject secrets.
- Additive migration `0041_channel_sync_control_plane` seeds only `channels:history_sync`; OpenAPI and
  frontend remain unchanged.

### UI-TASTE-05 Owner Review, Release Candidate Audit and Merge Readiness

- Completed a full repository release-candidate audit across product routes, shared components,
  authentication/RBAC, tenant/object authorization evidence, API contracts, audits and Module 13
  provider-neutral boundaries.
- Fixed one verified Major defect: campaign create/edit lazy chunks no longer depend on a cyclic barrel
  re-export that Rollup warned could break execution order.
- Full repository validation passes in workflow `30982637585`; the main application bundle is `199.78/54.87 kB gzip`.
- No feature, architecture, governance, provider, QR, runtime, API, migration, dependency, permission
  catalog or roadmap-sequencing change was made.
- No verified Blocker or Major defect remains in repository-verifiable scope. The branch is ready for
  explicit Owner Approval and Merge, not Host Validated or Production Ready.

### UI-TASTE-04 Responsive, Accessibility and Performance Regression

- Reactivation KYC deep links now reuse the existing `kyc:read` route authority.
- Workspace record search waits 250 ms before issuing bounded permission-scoped requests; empty
  collections retain keyboard index zero and truthful loading feedback.
- Keyboard shortcuts use the shared modal authority; shared modals lock background scroll and shared
  pagination wraps without narrow-screen overflow.
- Authenticated pages and administrative panels load at their route boundaries; the main JavaScript
  bundle measures 199.78/54.87 kB gzip.
- Verified unused `ComingSoonPage` code is removed. No business workflow or route was added.

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

- Repository pre-merge quality gate PASS in workflow `31038662241`.
- Ruff and strict mypy PASS; OpenAPI/generated-client drift PASS at 200 paths.
- Full backend regression: 985 PASS; migration head is `0041_channel_sync_control_plane`.
- Frontend ESLint and TypeScript PASS; 36 Vitest files / 671 tests PASS; production build PASS.
- E2E TypeScript, Bandit, Python/frontend/browser dependency audits and tracked-source
  vulnerability/secret/IaC scan PASS.
- Main application bundle remains 199.78/54.87 kB gzip; no frontend or API execution path changed.
- Five focused M13-06B tests cover lifecycle, RBAC/flags, tenant isolation, capability boundaries,
  idempotency, audit, secret rejection and absence of public/provider execution.
- Host/provider certification evidence remains `PENDING – Host Machine Validation`.

## Explicitly absent

QR image generation/scanning, WhatsApp login/protocol, provider adapters, live event ingestion,
provider history retrieval, media-byte transfer/processing, sending, incoming webhooks, routing, Inbox/Customer
360/Analytics changes, public runtime/pairing/sync APIs and provider-specific tables are absent.

## Remaining work

- Target-host MySQL migration and rollback evidence.
- Real multi-node runtime/lease/fencing contention and stale-runtime recovery validation.
- Runtime supervisor, heartbeat, reconnect/re-authentication and alerting commissioning.
- Production KMS custody for referenced provider credentials.
- Representative tenant/RBAC/feature-flag rollout and operator acceptance.
- Provider certification host evidence and all live M13-06 inbound/history/media execution plus later messaging/operator milestones.

## Stop rule

Stop after M13-06B. No implementation milestone is authorized after this commit.

Do not begin provider adapter, QR image/login, live event ingestion, provider history retrieval,
media-byte transfer, messaging, webhook, routing or provider UI until certification and a separate
owner instruction.
