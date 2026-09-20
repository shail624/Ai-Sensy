# GSHEET-02 — Queued contact export to a new Google Sheet tab

Date: 2026-09-20

## Owner decision

Every export creates a new dated tab. Existing tabs are never selected as an overwrite target.
Revenue and ROI remain unavailable because the owner confirmed there is no factual source yet.

## Implementation

- Google Sheets is a fourth destination in the existing contact Export dialog.
- The operator pastes a Sheet link or id; a queued export resolves the current server-side contact
  filters, exactly like CSV/XLSX/JSON.
- The worker creates a job-owned dated tab and streams rows in bounded batches with RAW input
  semantics. It never materializes the complete contact set in memory.
- The tab name includes the export id. A retry finds and clears only that job-owned tab, then writes
  it again, preventing duplicate tabs and duplicate rows.
- The same `contacts:export` permission, tenant-scoped export record, progress endpoint, audit and
  queue authority remain in force. Service-account material stays environment-only.
- Migration `0069_google_sheet_export_format` extends only the existing export-format constraint.
  OpenAPI remains 247 paths; generated TypeScript is synchronized.

## Validation

- PASS: 38 focused backend/integration/migration tests.
- PASS: SQLite migration upgrade/downgrade/re-upgrade and single linear head at 0069.
- PASS: Ruff and strict mypy across 332 backend files.
- PASS: applicable backend suite, 1,761 passed, 6 MySQL-only skipped, 6 Redis-dependent tests
  deselected after the unfiltered run proved Redis unavailable on this host.
- PASS: frontend 61 files / 1,013 tests, TypeScript, ESLint and production build.
- PENDING – Host Machine Validation: real Google service account, Editor share, live Sheet write;
  MySQL migration and the six Redis-dependent tests.

## Remaining Google Sheets scope

Scheduled re-sync, multi-tab batches and live owner credential commissioning remain separate
milestones. No secret was supplied or stored in this milestone.
