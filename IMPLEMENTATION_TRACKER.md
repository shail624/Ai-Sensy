# Implementation Tracker (canonical)

> GitHub at the latest approved HEAD is the repository source of truth. Keep repository-verifiable
> engineering evidence separate from authenticated host visual acceptance.

_Last updated: 2026-08-04 · UI-TASTE-03A operator-first Dashboard is implemented and repository-
validated. Reactivation redesign has not started._

## Current state

- **Branch:** `ui/taste-modernization`
- **Priority 2 baseline:** `7d826987c272d28038663ba9cb15c832c37e2b02`
- **Release:** `1.0.0-rc1`
- **Migration/OpenAPI:** `0035_notification_center` · 193 paths · unchanged
- **Backend:** unchanged; CORE-09 baseline remains 948 pytest, Ruff clean, strict mypy clean
- **Frontend:** ESLint PASS · TypeScript PASS · 34 files / 661 Vitest tests PASS · build PASS
- **Production dependency boundary:** no high/critical finding; two moderate React Router advisories
- **Current milestone:** `UI-TASTE-03A — Operator-first Dashboard — IMPLEMENTED`
- **Host validation:** `PENDING – Host Machine Validation`
- **Next milestone:** `UI-TASTE-03B — Reactivation operational hierarchy — BLOCKED PENDING APPROVAL`

## Dashboard decisions now supported

| Operator question | Factual decision support |
|---|---|
| What requires attention now? | Severity-ranked queue combining authorized Reactivation, KYC, Campaign, Inbox and Template records with source deep links |
| Which customers are blocked? | Breached SLA, overdue follow-up, incomplete-document and unreachable-customer reasons with stage and owner |
| Which KYC reviews are pending? | `under_review` records with evidence completeness, progress, owner and SLA |
| Which SIM deliveries are delayed? | `sim_required` cases with breached persisted SLA; presented as delivery risk rather than invented courier data |
| Which activations are overdue? | `activation_pending` cases with breached persisted SLA |
| Which campaigns need action? | Failed/paused campaigns and campaigns carrying failed recipients |
| Which conversations need replies? | Unread open/pending conversations ordered by derived waiting age; not mislabelled as configured SLA |
| Which templates failed? | Rejected, paused and disabled templates with rejection detail when available |
| Which agents require attention? | Assigned blocked, overdue, breached-SLA and KYC-review workload; no synthetic performance score |
| Which KPIs changed today? | Today versus previous equivalent period with lower-is-better handling for failure and response time |

## Delivered implementation

- New `features/dashboard` selectors and responsive operational workspace.
- Permission-aware conditional queries over existing source APIs.
- Truthful loading, empty, partial-error, unavailable and success states.
- Signed-in operator task snapshot, source actions and preserved header action links.
- Four focused selector tests plus all existing navigation, domain and shared-control regressions.
- Dashboard lazy split with accessible skeleton: `31.96 kB` / `8.61 kB` gzip.

## Preserved invariants

- No backend endpoint, model, migration, generated contract, permission or business-rule change.
- No navigation/sidebar/route-catalogue redesign and no completed module rebuild.
- No fake record, decorative KPI, local-only workflow, copied reference implementation or duplicate
  reporting authority.
- Existing source queues remain authoritative for complete pagination; bounded Dashboard reads are not
  documented as exact enterprise totals.

## Validation and debt

- PASS: production dependency audit, ESLint, strict TypeScript, 661 tests, production build.
- PASS: attention classification, KPI direction, agent aggregation and primary link semantics.
- Main chunk improves to `733.62 kB` / `178.16 kB` gzip but remains above the 500 kB warning level.
- `OperationalDashboard` is split at `31.96 kB` / `8.61 kB` gzip.
- React Router future warnings and two moderate advisories remain separate upgrade work.
- PENDING: authenticated representative-data visual/reference comparison, screen reader, long-content
  overflow and target browser/device matrix.

## Remaining UI sequence

1. Owner reviews UI-TASTE-03A Dashboard evidence.
2. UI-TASTE-03B modernizes Reactivation hierarchy only, reusing the shared system and existing domain.
3. Later reviewed screen milestones cover Inbox, Contacts, Customer 360 and Notification Center.
4. UI-TASTE-04 performs final responsive/accessibility/performance regression.
5. UI-TASTE-05 records owner acceptance and merge evidence.

## Product sequence after UI review

Resume `CORE-10` Dedicated Chat History and `CORE-11` settings/team/tags/SLA controls, then the
approved growth, analytics, integration, enterprise and release roadmap. Payments, ads, commerce,
SaaS billing, marketplace, public signup, reseller and multi-project surfaces remain excluded.
