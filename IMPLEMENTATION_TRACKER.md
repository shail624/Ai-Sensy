# Implementation Tracker (canonical)

> Canonical implementation tracker. GitHub at the latest approved HEAD remains the repository source
> of truth. Every new session must read this first. Update it after each verified milestone. Keep it
> short: state, not narrative.

_Last updated: 2026-08-04 · CORE-09 Unified Notification Center is merged and validated. Phase 1 UI
Taste Modernization is owner-approved on `ui/taste-modernization`; the current milestone is a
documentation-only implementation plan._

## Current state

- **Branch:** `ui/taste-modernization`
- **Implementation baseline:** `62d4daa50617e2e0c8fff9f5ec9a514848a77f98`
- **Release baseline:** `v1.0.0-rc1`
- **Migration head:** `0035_notification_center` (35 linear revisions, base `0001`)
- **OpenAPI:** 3.1.0 · 193 paths · generated TypeScript contract remains authoritative
- **Backend evidence:** 948 tests passed · Ruff clean · strict mypy clean across 258 source files
- **Frontend evidence:** CORE-09 focused notification/layout tests passed before merge; the full
  frontend suite is intentionally not re-run in this documentation-only milestone
- **Current milestone:** `UI-TASTE-01 — Taste Modernization implementation plan — DOCUMENTATION ONLY`
- **Current restriction:** only `PROJECT_STATE.md`, `MODULE_STATUS.md`,
  `IMPLEMENTATION_TRACKER.md`, and `ROADMAP.md` may change; no application code, dependency,
  migration, OpenAPI, generated client, or runtime behavior change is authorized
- **Last completed milestone:** `CORE-09 — Unified Notification Center`
- **Next milestone:** `UI-TASTE-02 — Shared design-system modernization`, after owner review of the
  documentation plan
- **Roadmap correction:** `CORE-08 — Skipped: Not required by product owner.` Preserve existing
  KYC-specific approval logic and completed authorization safeguards; do not create a generic
  Approval Center, framework, queue, escalation system, or authority.

## UI Taste Modernization approval

- **Design variance:** `4/10`
- **Motion intensity:** `3/10`
- **Visual density:** `8/10`
- **Approach:** targeted modernization of the existing React/Tailwind application; no rewrite and no
  imitation of another product.
- **Preserve:** sidebar and route structure, permissions, generated API contracts, source-domain
  ownership, real workflows, mobile navigation, keyboard/focus behavior, reduced motion, semantic
  light/dark tokens, and existing test contracts.

### Phase 1 audit findings

1. The application shell is already a strong accessible/responsive foundation and must be refined,
   not replaced.
2. Dashboard hierarchy is messaging-led and does not prioritize factual Reactivation operator work.
3. Reactivation mixes connected production capability with foundation/future states; maturity and
   action hierarchy need clearer separation.
4. Large radii, nested cards, soft fills, and gradients are overused for dense enterprise workflows.
5. Inbox, Contacts, and adjacent modules use inconsistent raw controls for filters, selects,
   pagination, toolbars, bulk actions, and loading/empty/error states.
6. Navigation is robust but information-heavy; everyday role-relevant work and advanced controls
   need clearer hierarchy and contextual shortcuts.
7. Source review is not final visual evidence. Authenticated representative-data browser review,
   responsive overflow, keyboard/focus, accessibility, bundle, and route performance checks remain
   mandatory.

### Approved execution order

1. **UI-TASTE-01 — Documentation/audit baseline:** synchronize branch, baseline, findings,
   boundaries, priorities, and acceptance rules. No application code.
2. **UI-TASTE-02 — Shared design system:** normalize density, radius, typography, form controls,
   page headers, toolbars, pagination, bulk actions, skeleton/empty/error states, and responsive
   behavior through existing shared components.
3. **UI-TASTE-03 — Priority screens:** Dashboard → Reactivation → Inbox → Contacts → Customer 360 →
   Notification Center. Preserve backend behavior and generated contracts.
4. **UI-TASTE-04 — Regression:** desktop/tablet/mobile, keyboard, focus, WCAG-oriented semantics and
   contrast, reduced motion, representative-data overflow, bundle size, and route performance.
5. **UI-TASTE-05 — Review and merge:** owner review, focused corrections, full frontend gates,
   recorded evidence, and merge only after approval.

## Completed baseline

| Area | Verified state at baseline `62d4daa` |
|---|---|
| Foundation | Identity, authentication, RBAC, audit, settings, API keys, queue/storage, and linear migrations `0001`–`0035` |
| CRM and engagement | Contacts, tags/attributes, segments, import/export/bulk, WhatsApp channels, templates, campaigns, Inbox, Tasks, media, analytics, and Customer Timeline |
| Reactivation domain | Persisted Reactivation pipeline and lightweight CRM, KYC operations, Documents, Task-backed Follow-up/Release dates, SLA evidence, and Customer 360 convergence |
| Notification Center | Durable tenant/user-scoped projection, unread count, mark-one/all-read, read-only team filtering, deep links, 15-second polling, Task/Reactivation event projection, Audit evidence, and lifecycle-consistency regression |
| Frontend shell | Permission-aware compact/expanded rail, grouped More navigation, command palette, mobile bottom navigation/drawer, semantic tokens, light/dark themes, focus-managed overlays, and reduced-motion behavior |
| Quality | CORE-09 backend closeout passed Ruff, strict mypy, and all 948 pytest tests; no uncommitted application change is part of UI-TASTE-01 |

## Remaining implementation sequence

- Complete the five approved UI Taste milestones above without changing product scope or duplicating
  completed authorities.
- Resume final-product sequence after UI review: `CORE-10` Dedicated Chat History, `CORE-11` core
  settings/team/tags/SLA controls, then the approved growth, analytics, integrations, enterprise,
  and release milestones in `ROADMAP.md`.
- Payments, catalogs, carts, checkout, orders, refunds, commerce, ads, public signup, reseller,
  marketplace, and multi-project journeys remain permanently excluded.

## Release blockers

- Full load/stress/spike/soak and 1M-contact capacity evidence requires the isolated Performance Lab.
- Metrics/dashboard/alerting/log-shipping and external synthetic-monitor evidence remain target-
  environment deployment work.
- TLS/host hardening, UAT, verified restore, rollback rehearsal, and production approval remain
  environment commissioning evidence.

## Known technical debt

- The production frontend build previously warned about a roughly 737.53 kB main chunk. Analytics,
  Reactivation, Automation, and Scan Studio are route-split; further route-level splitting remains.
- Frontend tests emit React Router v7 future-flag and Node localStorage experimental warnings.
- Two moderate React Router advisories require an explicit React Router 7.18+ upgrade rather than a
  silent patch.
- Owner bootstrap accepts reserved `.test` email addresses that the login request schema rejects.
- Representative-data authenticated visual regression infrastructure is not yet a canonical gate.

## Permanent invariants

Repository → Service → API layering · all sends through `SendService` · provider payloads remain in
the Meta adapter · Retry Engine is the single classify/backoff authority · Rate Gate fails safe ·
persist-first webhooks · campaign status controls dispatch · completed modules are extended rather
than rebuilt · unbuilt surfaces remain absent or honestly gated · partitioned tables carry no FKs ·
frontend API types are generated only · accessibility, responsive behavior, and real data are part of
completion rather than optional polish.

## Notes for the next session

- Confirm `git branch --show-current` is `ui/taste-modernization` and the baseline ancestry includes
  `62d4daa` before application edits.
- Begin only `UI-TASTE-02`; do not jump directly into page-specific redesigns before shared primitive
  decisions are implemented and tested.
- Run backend commands from `backend/` via `.venv/Scripts/python.exe`.
- Run frontend typecheck, lint, focused tests, production build, and then the full Vitest suite for
  every implementation closeout.
- Regenerate OpenAPI/types only when an approved backend contract changes; UI Taste work must not
  hand-edit generated API types.
