# Implementation Tracker (canonical)

> GitHub at the latest approved HEAD is the repository source of truth. Update this state ledger
> after every verified milestone; keep implementation evidence distinct from host visual approval.

_Last updated: 2026-08-04 · Priority 1 shared enterprise design-system modernization is implemented
and repository-validated. Owner approval and authenticated representative-data visual review remain
required before Dashboard work._

## Current state

- **Branch:** `ui/taste-modernization`
- **Original UI lineage baseline:** `62d4daa50617e2e0c8fff9f5ec9a514848a77f98`
- **Priority 1 starting baseline:** `9043fe03a80b682a010304c88c5d29d8ec77d1fa`
- **Release:** `1.0.0-rc1`
- **Migration/OpenAPI:** `0035_notification_center` · 193 paths · unchanged by Priority 1
- **Backend:** unchanged; CORE-09 baseline remains 948 pytest, Ruff clean, strict mypy clean
- **Frontend:** ESLint PASS · TypeScript PASS · 657/657 Vitest PASS · production build PASS
- **Production dependency boundary:** no high/critical production finding; two moderate React Router
  advisories remain
- **Current milestone:** `UI-TASTE-02 — IMPLEMENTED; OWNER APPROVAL PENDING`
- **Next milestone:** `UI-TASTE-03 — Dashboard redesign — BLOCKED PENDING APPROVAL`
- **Host validation:** authenticated representative-data desktop/tablet/mobile, keyboard, visual,
  and approved-reference comparison is `PENDING – Host Machine Validation`

## Delivered in UI-TASTE-02

| Area | Delivered |
|---|---|
| Radius and density | Named `control`/`surface`/`overlay` tiers; restrained shared surfaces; compact responsive gutters and touch-safe controls without altering navigation utilities |
| Form controls | Forward-ref `Input`, `Select`, `Textarea`, and `Field` with semantic invalid/disabled/focus states, icon/action slots, labels, help, and errors |
| Enterprise composition | Reusable `Toolbar`, groups/divider, `FilterBar`, and cursor-safe `Pagination` with busy/disabled/summary states |
| Existing primitives | Button, Card, CardHeader, PageHeader, and PageContainer refined in place; no parallel design system |
| Contacts | Search, desktop filters, mobile filter sheet, and cursor pagination converge on shared primitives; URL state/import/bulk workflow unchanged |
| Inbox | Search shortcut, triage views, advanced filters, saved views, bulk selects, and cursor pagination reuse shared primitives; thread workflow unchanged |
| Notifications | Type/status/date/assignee filters, mark-all, refresh, source actions, offline/read-only states reuse shared primitives; polling/read/deep-link behavior unchanged |
| Tests | Three focused shared-primitive tests plus the complete 657-test frontend suite |

## Preserved invariants

- No sidebar/navigation/route redesign and no removed destination.
- No backend, migration, OpenAPI, generated TypeScript contract, dependency, permission, or source-
  domain change.
- No copied reference code/assets/layout, heavy animation dependency, fake data, invented KPI, or
  executable-looking placeholder.
- Existing accessibility, focus, keyboard, reduced motion, responsive/mobile, and real-state
  boundaries remain authoritative.

## Validation

- PASS: ESLint, TypeScript, 33 Vitest files / 657 tests, production build.
- PASS: production dependency audit at high severity; only two moderate React Router advisories.
- PASS: changed-file boundary and existing layout/navigation regressions.
- PENDING – Host Machine Validation: authenticated representative-data visual/reference comparison,
  target browser/device matrix, screen-reader pass, and real long-content overflow review.
- Measured debt: main bundle 747.91 kB minified / 181.62 kB gzip with existing >500 kB warning;
  development/build-tool audit inventory contains 11 findings and requires a separate dependency
  modernization milestone rather than an unrelated breaking change here.

## Remaining UI sequence

1. Owner reviews and approves UI-TASTE-02.
2. UI-TASTE-03 begins with Dashboard only; no Reactivation or other screen in the same milestone.
3. Later priority-screen milestones reuse the shared layer rather than introducing local variants.
4. UI-TASTE-04 performs authenticated responsive/accessibility/performance regression.
5. UI-TASTE-05 records final owner acceptance and merge evidence.

## Product sequence after UI review

Resume `CORE-10` Dedicated Chat History and `CORE-11` settings/team/tags/SLA controls, followed by the
approved growth, analytics, integration, enterprise, and release milestones in `ROADMAP.md`.
Payments, ads, commerce, SaaS billing, marketplace, public signup, reseller, and multi-project
surfaces remain excluded.

## Known technical debt

- Main application chunk is 747.91 kB minified; further route-level splitting remains required.
- React Router future-flag warnings remain, and two moderate production advisories require an explicit
  routing upgrade rather than a silent patch.
- Development/build tooling contains transitive audit findings, including high/critical severities;
  production `--omit=dev` has no high/critical finding.
- Authenticated representative-data visual regression is not yet a canonical automated gate.
- Owner-bootstrap `.test` email validation mismatch remains unrelated maintenance debt.

## Permanent invariants

Repository → Service → API layering · all sends through `SendService` · Meta payloads stay in the
adapter · Retry Engine owns classify/backoff · Rate Gate fails safe · persist-first webhooks ·
campaign status controls dispatch · completed modules are extended, never rebuilt · generated API
types are authoritative · accessibility, responsive behavior, real state, and original premium
presentation are completion requirements.
