# Project State

> Current repository snapshot. GitHub is the implementation source of truth. `HEAD` is symbolic
> because a commit cannot embed its own final hash; resolve it after push with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `ui/taste-modernization` |
| Priority 2 starting baseline | `7d826987c272d28038663ba9cb15c832c37e2b02` (`feat(ui): modernize shared enterprise design system`) |
| Current Git HEAD | `HEAD` (Dashboard closeout commit; resolve after push) |
| Current milestone | `UI-TASTE-03A — Operator-first Dashboard — IMPLEMENTED; HOST VISUAL REVIEW PENDING` |
| Current phase | `UI Taste Modernization — Dashboard complete; Reactivation redesign blocked pending owner approval` |
| Repository version | `1.0.0-rc1` |
| Migration head | `0035_notification_center` (35 linear revisions; unchanged) |
| OpenAPI | `3.1.0` · `193` paths · generated TypeScript authority unchanged |
| Backend evidence | Existing CORE-09 baseline: Ruff clean, strict mypy clean across 258 files, 948 pytest tests; backend not changed or re-run |
| Frontend evidence | ESLint PASS · TypeScript PASS · 34 Vitest files / 661 tests PASS · production build PASS |
| Dependency evidence | Production audit has two moderate React Router advisories and no high/critical finding |
| Bundle evidence | Main chunk `733.62 kB` / `178.16 kB` gzip; operational Dashboard split to `31.96 kB` / `8.61 kB` gzip |
| Visual acceptance | `PENDING – Host Machine Validation` for authenticated representative-data desktop/tablet/mobile, keyboard, screen-reader and approved-reference review |
| Last completed milestone | `UI-TASTE-03A — Operator-first Dashboard` (repository engineering gates complete) |
| Next milestone | `UI-TASTE-03B — Reactivation operational hierarchy`, blocked pending owner approval |
| Worktree expectation | One Dashboard milestone commit; no backend, migration, OpenAPI, generated-client, dependency, route-catalogue or navigation change |
| Last update | `2026-08-04T03:00:00+05:30` (Asia/Kolkata) |

## Delivered operator intelligence

The first authenticated screen now answers the approved operating questions through existing,
permission-scoped source authorities:

- prioritized cross-domain attention queue for blocked customers, KYC, SIM, Activation, campaigns,
  conversations and templates;
- blocked-customer reasons, current stage and assignee;
- reviewer-pending KYC and evidence/SLA state;
- SIM Required and Activation Pending cases whose persisted SLA is breached;
- failed, paused or recipient-failing campaigns;
- unread open/pending conversations ordered by waiting age, explicitly labelled as a derived age and
  not a configured SLA;
- rejected, paused or disabled templates;
- agent attention derived from assigned blocked, overdue, breached-SLA and KYC work without invented
  productivity scores;
- today-versus-previous-period KPI changes with metric-aware direction;
- signed-in operator task snapshot and governed source deep links.

## Architecture and truth boundaries

- Dashboard composes existing Reactivation, KYC, Task, Campaign, Inbox, Template and Analytics APIs;
  it adds no dashboard backend, duplicate projection, fake KPI, local persistence or parallel domain.
- Source errors remain visible as partial-data warnings and are never converted to zero.
- Reactivation/KYC/Inbox signals are bounded by existing source-query limits; source queues remain the
  authority for complete pagination and production-scale exact totals.
- Permission-gated queries do not issue unauthorized requests.
- Existing primary action links, route catalogue, navigation, source workflows and business rules are
  preserved.

## Verified fixes and performance work

- Fixed KPI sentiment literal widening caught by strict TypeScript.
- Fixed the Dashboard header regression that changed navigable Live Chat/New Campaign links into
  buttons; the established semantic and test contract is restored.
- Lazy-loaded the operational intelligence workspace behind an accessible skeleton. The main chunk
  falls from the Priority 1 measurement of `747.91 kB` to `733.62 kB`; the new workspace is a separate
  `31.96 kB` chunk.

## Validation boundary

Repository validation proves contracts, selectors, semantics, compilation and build integrity. It
does not prove final density, long-content overflow, contrast, browser behavior or screen-reader
quality with authenticated representative records. Those remain `PENDING – Host Machine Validation`.

## Maintenance rule

Do not begin Reactivation redesign until the owner approves this closeout. Preserve the operator-first
information order and never turn bounded source reads into unlabelled enterprise totals.
