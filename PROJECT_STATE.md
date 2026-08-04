# Project State

> Current repository snapshot. GitHub is the implementation source of truth. `HEAD` is symbolic
> because a commit cannot embed its own final hash; resolve it after push with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `ui/taste-modernization` |
| Priority 2 starting baseline | `7d826987c272d28038663ba9cb15c832c37e2b02` (`feat(ui): modernize shared enterprise design system`) |
| Current Git HEAD | `HEAD` (governance-only Module 13 owner-approval freeze; resolve after push) |
| Current milestone | `UI-TASTE-03A — Operator-first Dashboard — IMPLEMENTED; HOST VISUAL REVIEW PENDING` |
| Current phase | `UI Taste Modernization — continue the existing roadmap; Module 13 implementation is gated and has not started` |
| Repository version | `1.0.0-rc1` |
| Migration head | `0035_notification_center` (35 linear revisions; unchanged) |
| OpenAPI | `3.1.0` · `193` paths · generated TypeScript authority unchanged |
| Backend evidence | Existing CORE-09 baseline: Ruff clean, strict mypy clean across 258 files, 948 pytest tests; backend not changed or re-run |
| Frontend evidence | ESLint PASS · TypeScript PASS · 34 Vitest files / 661 tests PASS · production build PASS |
| Dependency evidence | Production audit has two moderate React Router advisories and no high/critical finding |
| Bundle evidence | Main chunk `733.62 kB` / `178.16 kB` gzip; operational Dashboard split to `31.96 kB` / `8.61 kB` gzip |
| Visual acceptance | `PENDING – Host Machine Validation` for authenticated representative-data desktop/tablet/mobile, keyboard, screen-reader and approved-reference review |
| Last completed milestone | `UI-TASTE-03A — Operator-first Dashboard` (repository engineering gates complete) |
| Next implementation milestone | `UI-TASTE-03B — Reactivation operational hierarchy`; approved previously, not started on the target branch |
| Module 13 planning | `Enterprise Omnichannel Channel Manager — OWNER APPROVED`; architecture frozen as the implementation contract |
| Module 13 implementation gate | `BLOCKED` until Reactivation Mission Control, Customer 360, Unified Inbox and Notification Center are each `Production Ready` under `ENGINEERING_STANDARDS.md`, and the owner explicitly instructs implementation |
| Worktree expectation | Governance-only approval record; no backend, frontend, migration, OpenAPI, generated-client, dependency, route, milestone-order or architecture change |
| Last update | `2026-08-04T10:52:00+05:30` (Asia/Kolkata) |

## Module 13 owner-approved planning freeze

- The approved Module 13 Architecture Review, including its approved additive refinements, is now
  the implementation contract for the Enterprise Omnichannel Channel Manager.
- Planning status is **Owner Approved**. Implementation has not started and no implementation claim is
  made by this governance update.
- The approved architecture, scope and milestone order are frozen. Do not add abstractions, expand
  scope, reorder milestones or redesign approved decisions.
- A verified implementation blocker may be documented, but any deviation from the approved contract
  requires explicit owner approval before code changes proceed.
- Module 13 cannot begin until Reactivation Mission Control, Customer 360, Unified Inbox and
  Notification Center are all `Production Ready` according to `ENGINEERING_STANDARDS.md`.
- Even after those prerequisites pass, Module 13 still requires a separate explicit owner instruction
  before implementation starts.
- Continue the existing roadmap only. Do not create additional Module 13 planning documents.

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

Continue the existing approved roadmap from the latest Git HEAD. Preserve the operator-first
information order and never turn bounded source reads into unlabelled enterprise totals. Keep Module
13 frozen and unimplemented until all recorded prerequisites and the separate owner-instruction gate
are satisfied.
