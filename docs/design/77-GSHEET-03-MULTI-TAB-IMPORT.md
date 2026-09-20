# GSHEET-03 — Multi-tab Google Sheet contact import

Date: 2026-09-20

## Scope

- The existing Google Sheet source in the contact import wizard accepts one to ten tab names.
- Tabs are read in the operator's stated order and staged as one CSV upload for the existing
  mapping, duplicate handling, queued import, progress, error-report and audit workflow.
- Every selected tab must have the same non-empty header row. A mismatch stops staging before an
  import job exists and identifies the mismatching tab.
- The combined data-row count remains subject to the existing contact import limit. Duplicate tab
  names and requests containing both the legacy single-tab field and the multi-tab field are
  rejected.
- The legacy single-tab request stays accepted for compatibility. The generated contract exposes
  the multi-tab request and response truth to new clients.

## Boundaries

This milestone does not add scheduled synchronization, polling, spreadsheet discovery, provider
credentials, migrations, or a second import pipeline. It does not change contact field mapping,
deduplication, permissions, tenant isolation or job execution.

## Validation

- PASS: 22 focused Google Sheet backend tests, including combination, header mismatch and the
  retained single-tab contract.
- PASS: 16 focused contact-import frontend tests.
- PASS: Ruff and strict mypy across 332 backend files; TypeScript and ESLint.
- PASS: OpenAPI and generated TypeScript synchronized at 247 paths.
- PASS: frontend 61 files / 1,013 tests.
- PASS: applicable backend suite, 1,763 passed, 6 MySQL-only skipped and 6 Redis-dependent tests
  deselected because those host services are unavailable.
- PASS: frontend production build.
- PENDING: live owner Google account and shared-Sheet validation; MySQL and Redis host validation.

## Remaining Google Sheets scope

Scheduled re-sync and live owner credential/share commissioning remain separate milestones. No
secret was requested, supplied or stored in this milestone.
