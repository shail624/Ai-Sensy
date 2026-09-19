# PAR-REP-03 — Domain Outcome Analytics

## Status

`REPOSITORY IMPLEMENTED` on 2026-08-24. Target-host representative-data, Docker/security release
and production commissioning remain pending; this milestone does not claim `Production Ready`.

## Delivered boundary

The existing Analytics rollup pipeline now carries a seventh derived fact family for Vi CRM
business outcomes. It is rebuilt from the immutable `business_events` ledger at hourly grain,
folded into the existing daily retention layer, tenant-scoped, freshness-tracked and safe to
backfill. No operational aggregate was duplicated and no dashboard request scans the live domain
tables.

The projection covers:

- Reactivation cases created, stage transitions, Completed and Not Required outcomes, lead source
  and terminal turnaround components;
- eligibility decisions split into Eligible, Not Eligible and Review Required;
- KYC review/manager decisions, terminal approvals/rejections/needs-information and terminal
  turnaround components;
- SIM delivery/failure and Activation completion/rejection outcomes; and
- SLA starts, breaches and resolutions by owning entity type.

Every stored measure is a count or sum. Ratios and averages remain read-time formulas:

- `reactivation_conversion_rate = completed / cases_created`;
- `reactivation_drop_off_rate = not_required / cases_created`;
- `eligibility_rate = eligible / eligibility_decisions`;
- `kyc_approval_rate = manager_approved / all_kyc_decisions`;
- `sla_breach_rate = breached / started` and `sla_resolution_rate = resolved / started`; and
- turnaround averages divide the summed seconds by their terminal-event counts.

An empty denominator returns unknown, never a fabricated zero.

## API, reports and UI

OpenAPI adds named Reactivation outcome, KYC outcome and Service-level resources while preserving
the generic metric/dimension/series/comparison endpoints. The metric catalogue also exposes
`domain`, `outcome`, `source` and domain actor dimensions. Zero-only cohorts are suppressed from
breakdown tables without changing aggregate totals.

The governed export catalogue grows from seven to ten report families with Reactivation, KYC and
Service Levels. CSV/XLSX/JSON/PDF generation, personal schedules, ready notifications, expiry,
signed downloads and Download Center history all reuse the existing authorities.

Analytics gains an original responsive Business outcomes tab with Reactivation, KYC and service
tables plus conversion, KYC approval/turnaround and SLA KPI cards. No AiSensy code, branding,
copy, assets or layout was copied.

## Persistence and safety

Migration `0051_domain_outcome_analytics` creates `analytics_domain_outcome_rollups`, widens the
report-schedule catalogue and preserves one linear 52-revision history. Bucket replacement remains
delete-then-insert and therefore convergent under retry/backfill. Organization scope is applied at
both source selection and rollup reads. The source ledger remains authoritative and rollups can be
fully regenerated.

## Validation

- Domain rollup/query/API/export/schedule/migration selection: **144/144 passed**.
- Analytics UI: **35/35 passed**.
- Complete backend: **1532 passed / 6 MySQL-only skipped / 0 failed in 426.19s**.
- Complete frontend: **41 files / 842 tests passed**.
- Static profile: **6/6 passed**; strict mypy covers **309 source files**; OpenAPI drift passes at
  **217 paths**.
- Vite **8.2.2** production build passes; Analytics is **423.51 kB / 120.07 kB gzip**.
- SQLite upgrade/downgrade/re-upgrade and single-head checks pass at **52 revisions**.
- Docker/security release evidence is recorded separately in the canonical validation ledger.

## Remaining boundary

Revenue, campaign-to-case conversion/attribution, ROI, workload/capacity reports, remaining
transcript/campaign/Scan/generated-document artifacts, external delivery channels and host
commissioning remain pending. Those figures will not be inferred from messaging cost or case
status without an approved source-of-truth formula.
