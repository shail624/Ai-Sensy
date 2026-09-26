# PAR-CAM-01 — Campaign Recipient Failure Operations

**Status:** Repository implemented  
**Synchronized:** 2026-08-24T17:37:59+05:30  
**Host validated:** No  
**Production ready:** No

## Outcome

Campaign operators can inspect the complete persisted recipient outcome ledger, filter it by an
exact delivery status, move forward and backward through a stable cursor history, and deliberately
re-queue failed recipients. The UI no longer filters only the first 50 loaded rows or performs a
bulk retry without explaining its boundary.

## Authority and safety

- `campaign_recipients` remains the per-recipient outcome authority. The campaign counters remain
  the denormalized progress projection; the browser does not recompute campaign totals.
- `GET /api/v1/campaigns/{campaign_id}/recipients` now declares `status`, `limit` and `cursor` in
  OpenAPI. Exact status validation is generated into the TypeScript client.
- The endpoint keeps the earlier top-level `has_more` value for v1 client compatibility and adds
  the standard total-aware `page` envelope with `next_cursor`.
- Results use newest-first `(created_at,id)` keyset pagination. Total counts respect the same
  campaign and status predicate.
- Current contact identity is resolved only when the contact belongs to the campaign organization.
  A corrupt foreign contact reference renders blank identity rather than crossing a tenant.
- The UI exposes current contact name/WhatsApp identity, delivery status, safe error code, retry
  count and the latest factual lifecycle timestamp. Internal error detail, provider `wamid`, message
  IDs and storage references are not exposed.

## Failure retry

The existing `POST /api/v1/campaigns/{campaign_id}/retry` authority remains unchanged: only failed
recipient rows are reset and re-dispatched; successful recipients are not sent again. The existing
`campaigns:send` permission, lifecycle checks, rate gate, smart-retry classifier, durable queue and
Audit evidence remain authoritative. The UI now requires an explicit confirmation that states the
failed-recipient count and successful-recipient exclusion, keeps server errors inside the decision
dialog, and refreshes campaign/recipient state after success.

## Persistence and scale

Additive migration `0056_campaign_recipient_operations` creates:

- `ix_crecip_campaign_created (campaign_id, created_at, id)`
- `ix_crecip_campaign_status_created (campaign_id, status, created_at, id)`

These indexes match the unfiltered and status-filtered ledger scans without adding another roster,
job or retry table. The Alembic graph remains one linear **57-revision** head and the SQLite
upgrade/downgrade/re-upgrade proof checks both index names.

## UI

The existing Campaign Detail **Recipients** tab now provides server-backed status filtering,
current-contact identity, failure/retry evidence, total-aware summary, busy-safe cursor navigation,
and complete loading/empty/error states. The existing shared Pagination and confirmation dialog
components are reused; no copied AiSensy code, assets, branding or layout entered the repository.

## Validation

- Campaign and migration regression: **107/107**.
- Focused Campaign UI: **51/51** across campaign actions, recipient operations and result exports.
- Complete frontend: **43 files / 857 tests**.
- Static gate: **6/6**; strict mypy: **314 source files**; OpenAPI drift: PASS.
- OpenAPI remains **225 paths** with synchronized generated TypeScript.
- Vite **8.2.2** production build: PASS; Campaigns **109.34/28.02 kB gzip**.
- Complete backend: **1553 passed / 6 MySQL-only skipped / 0 failed in 476.67s**.

## Completion effect and remaining boundary

Campaigns advance **90% → 94%**. The canonical rows sum to 2,315, so the 31-module mean advances
**74.5% → 74.7%** and the recalculated median is **86%**. The prior 85% median summary was
arithmetic drift, not extra feature progress. OpenAPI path count, Download Center, permissions,
queue/task inventory and provider capabilities do not change.

Campaign-to-reactivation conversion attribution and approved recovered-value/revenue/ROI source
facts remain pending; none are inferred from unrelated delivery counts. Docker/security rerun,
target-MySQL query-plan/scale evidence, authenticated representative-data device/accessibility UAT,
commit/push and deployment remain outside this repository-only milestone.
