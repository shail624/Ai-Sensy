# PAR-REP-01 — Analytics PDF Reports

**Status:** Repository Implemented  
**Date:** 2026-08-24  
**Scope:** Add governed PDF delivery to the existing asynchronous analytics report pipeline

## Decision

PDF is a rendering option for analytics reports, not a new reporting system. The existing
`exports` record, `exports` queue, rollup query service, storage provider, expiry policy, signed
artifact route and Download Center remain the sole authorities. All seven existing report families
can now request CSV, Excel, JSON or PDF through `POST /api/v1/analytics/reports/export`.

Contact exports deliberately remain CSV/Excel/JSON. Both the request schema and service boundary
reject contact PDF so a table renderer optimized for fixed analytics labels and numeric facts is
not misrepresented as a general contact-document generator.

## Artifact contract

The report worker pivots the same rollup series into period rows used by the other formats, then
renders a compressed landscape-A4 table with:

- a report-specific title and repeated page numbering;
- repeated column headers, alternating row bands and stable margins;
- deterministic built-in fonts with bounded cell fitting;
- explicit empty-result text;
- honest micro-unit labels for cost metrics; and
- the existing short-lived signed download and retention behavior.

The artifact is available immediately from the report progress response and automatically appears
in the requesting operator's permission-scoped Download Center. No second download route or
artifact index is added.

## Persistence and rollback

Migration `0049_report_pdf_exports` widens the existing `ck_exports_format` check to include `pdf`.
Downgrade removes expiring PDF job records before restoring the legacy three-format constraint;
stored bytes remain governed by normal retention. The migration chain remains single-head and
linear at **50 revisions**. OpenAPI remains **212 paths** because the change extends an existing
request enum rather than adding a route; generated TypeScript is synchronized.

## Security and scope boundary

The existing `analytics:export` permission, organization scope, requesting-user ownership,
background job evidence, signed link and expiry rules apply unchanged. Report titles, columns and
metrics come only from the fixed server catalogue; no caller-supplied HTML, JavaScript, font or
template enters the artifact.

This slice does not add report schedules, revenue/ROI/productivity/workload/SLA/case-outcome
projections, email or WhatsApp delivery, Chat History transcripts, campaign/Scan exports, generated
documents, retry controls or target-host commissioning.

## Validation

- Focused Analytics/report/format/export/Download/migration backend selection: **139/139 passed**.
- PDF writer regression: multi-page output, stable finish and honest cost-unit labels pass.
- Signed PDF artifact and Download Center end-to-end regression pass.
- Focused Analytics/Download Center UI: **36/36 passed**.
- Complete backend: **1525 passed / 6 MySQL-only skipped / 0 failed** in **434.13s**.
- Complete frontend: **41 files / 839 tests passed**.
- Static profile: **6/6 passed**; strict mypy covers **306 source files**; OpenAPI drift passes.
- Frontend lint, TypeScript and Vite **8.2.2** production build pass.
- Current backend dependency audit, including ReportLab, reports **no known vulnerabilities**.
- A three-page sample was rendered with Poppler and inspected page by page; headers, margins,
  columns, row bands, page numbers and footers are aligned and unclipped. `pdfinfo` and `pypdf`
  confirm landscape A4, three pages, title metadata and complete first-to-last-row extraction.
- Docker/security release rerun remains pending; PAR-AUTO-22 at **23/23 in 685.9s** remains the last
  complete release certificate and is not attributed to this changed tree.

Executive Reports advance **25% → 35%** and Download Center advances **65% → 70%**. The canonical
31-module mean advances **69.5% → 70.0%**; schedules, executive/domain report content, other artifact
families and host acceptance remain pending.
