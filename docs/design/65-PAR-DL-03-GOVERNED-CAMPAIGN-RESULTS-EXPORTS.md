# PAR-DL-03 — Governed Campaign Results Exports

**Status:** Repository implemented  
**Synchronized:** 2026-08-24T16:50:12+05:30  
**Host validated:** No  
**Production ready:** No

## Outcome

Authorized campaign managers can generate a complete or recipient-status-filtered results artifact
for one tenant-scoped campaign. The export is created asynchronously from the persisted campaign
recipient ledger and appears in the existing personal Download Center. The browser's currently
visible recipient page is never treated as complete campaign evidence.

## Authority and boundaries

- `campaign_recipients` remains the per-recipient outcome authority; campaign counters remain its
  denormalized dashboard projection.
- The existing `exports` row, `exports` queue, job metadata, retry discipline, storage provider,
  expiry, signed links and audit actions remain the only artifact pipeline.
- `campaigns:export` is a separate entitlement, granted by default to Owner, Admin and Manager.
  Campaign read/send/manage permissions do not silently imply bulk result extraction.
- Start and progress are tenant-, requester-, campaign- and current-permission-scoped. A job UUID
  cannot be substituted beneath another campaign route, and another authorized user receives 404.
- The worker reads in 500-row oldest-first `(created_at, id)` keyset batches. Progress is committed
  per batch, so large campaign rosters are not materialized in memory.
- CSV, XLSX, JSON and PDF reuse the hardened shared writers, including formula-leading cell
  neutralization.

## Artifact contract

The artifact includes campaign public ID/name, current contact public ID/name/phone, recipient
status, safe error code, retry count, cost/currency and queued/sent/delivered/read/failed timestamps.
Current contact identity is explicitly labelled as current because the recipient ledger does not
snapshot mutable identity fields.

Provider `wamid`, internal message IDs, template-variable payloads, internal error detail and
storage/provider references are excluded. A corrupt cross-tenant contact reference renders blank
identity fields rather than disclosing another organization's contact.

## API and UI

- `POST /api/v1/campaigns/{campaign_id}/exports`
- `GET /api/v1/campaigns/{campaign_id}/exports/{export_id}`
- OpenAPI advances from 223 to **225 paths** with synchronized generated TypeScript.
- Campaign Detail provides an original responsive export sheet with format and optional recipient
  status, queued/failed/ready states, row count, signed download and Download Center deep link.
- Download Center adds a permission-filtered **Campaign results** family and its navigation/route
  entitlement recognizes `campaigns:export`.
- The source image contract advances from 31 to **32 application tasks**.

## Migration

`0055_campaign_results_exports` adds only the governed permission. No duplicate job, artifact,
campaign or storage table is introduced. The Alembic graph remains one linear head with **56
revisions** and passes SQLite upgrade/downgrade/re-upgrade.

## Validation

- Campaign export + Download Center focused backend: **10/10**.
- Full campaign/export regression: **106/106**.
- Provider/OpenAPI/smoke/image-contract regression after task-count synchronization: **32/32**.
- Migration round trip and graph: **5/5**.
- Campaign/Download/navigation focused frontend: **63/63**.
- Complete frontend: **42 files / 854 tests**.
- Static gate: **6/6**; strict mypy: **314 source files**; OpenAPI drift: PASS.
- Vite **8.2.2** production build: PASS; Campaigns **108.35/27.75 kB gzip**, Download Center
  **7.18/2.54 kB gzip**.
- Complete backend: **1552 passed / 6 MySQL-only skipped / 0 failed in 475.58s**.

## Completion effect and remaining boundary

Campaigns advance **85% → 90%**, Download Center **80% → 88%**, API **94% → 95%**, and the
canonical 31-module mean advances **74.1% → 74.5%**; median remains **85%**.

Campaign conversion/ROI attribution and failed-message retry UX remain in the Campaign roadmap.
Compliant Scan-result and generated-document artifact sources remain in Download Center. Docker/
security release rerun, target-host MySQL performance, authenticated representative-data browser/
device/accessibility acceptance and deployment commissioning remain host evidence—not local PASS.
