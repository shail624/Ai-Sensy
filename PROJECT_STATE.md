# Project State

> Current repository snapshot. Update this file at every milestone closeout and whenever the
> milestone baseline changes. `HEAD` is kept symbolic because a Git commit cannot embed its own
> final hash; resolve it from the authoritative checkout with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `ui/taste-modernization` |
| Original UI branch baseline | `62d4daa50617e2e0c8fff9f5ec9a514848a77f98` (`CORE-09` validated baseline) |
| Priority 1 starting baseline | `9043fe03a80b682a010304c88c5d29d8ec77d1fa` (`docs(ui): add taste modernization implementation plan`) |
| Current Git HEAD | `HEAD` (Priority 1 closeout commit; resolve from Git after push) |
| Current milestone | `UI-TASTE-02 — Shared enterprise design system — IMPLEMENTED; OWNER APPROVAL PENDING` |
| Current phase | `UI Taste Modernization — Priority 1 implemented; Priority 2 blocked pending approval` |
| Repository version | `1.0.0-rc1` |
| Current migration head | `0035_notification_center` (35 linear revisions) |
| OpenAPI path count | `193` (OpenAPI `3.1.0`) |
| Backend evidence | Existing CORE-09 baseline: Ruff clean, strict mypy clean across 258 files, 948 pytest tests passed; backend not changed or re-run for this frontend-only milestone |
| Frontend evidence | ESLint PASS; TypeScript PASS; 657/657 Vitest tests across 33 files PASS; production build PASS |
| Dependency evidence | Production audit has 2 moderate React Router advisories and no high/critical finding; development-tooling audit inventory remains recorded as technical debt |
| Visual acceptance | `PENDING – Host Machine Validation` for authenticated representative-data desktop/tablet/mobile and reference-comparison review |
| Last completed product milestone | `CORE-09 — Unified Notification Center` |
| Last completed governance milestone | `UI-TASTE-01 — Documentation and audit baseline` |
| Next milestone | `UI-TASTE-03 — Dashboard redesign`, blocked until owner approval of Priority 1 |
| Current worktree expectation | One Priority 1 squash commit; no sidebar, navigation, route, API, backend, migration, OpenAPI, generated-client, dependency, or workflow file change |
| Last update timestamp | `2026-08-04T01:38:00+05:30` (Asia/Kolkata) |

## Priority 1 implementation

Priority 1 modernizes the shared enterprise presentation layer without changing product workflows:

- added governed `Input`, `Select`, `Textarea`, and `Field` controls with forward refs, semantic
  disabled/invalid states, icon/action slots, mobile touch targets, and focus-visible treatment;
- added shared `Toolbar`, `ToolbarGroup`, `ToolbarDivider`, `FilterBar`, and cursor-safe `Pagination`;
- added named `control`, `surface`, and `overlay` radius tiers without changing existing sidebar or
  navigation radius utilities;
- refined shared Button, Card, PageHeader, and PageContainer density and hierarchy;
- replaced duplicated controls in Contacts, Inbox, and Notification Center while preserving URL
  filters, bulk actions, saved views, keyboard shortcuts, polling, read-state, and source deep links;
- added focused semantic and interaction tests for the new primitives.

## Preserved boundaries

- Sidebar, TopNav structure, command palette, mobile navigation, routes, permissions, source-domain
  ownership, generated API contracts, backend services, migrations, and business rules are unchanged.
- No heavy animation library, copied code, reference asset, proprietary wording, fake metric,
  placeholder workflow, parallel component system, or dependency upgrade was introduced.
- Existing keyboard navigation, focus management, reduced-motion behavior, semantic light/dark
  tokens, responsive composition, loading/empty/error states, and truthful disabled states remain.

## Validation evidence

- `npm run lint`: PASS.
- `npm run typecheck`: PASS.
- `npm test`: PASS — 33 files, 657 tests, including 3 new primitive tests, 4 Contacts toolbar tests,
  24 Inbox tests, 3 Notification Center tests, and 21 layout/navigation tests.
- `npm run build`: PASS — 2,599 modules transformed; CSS 49.39 kB (9.79 kB gzip); main application
  chunk 747.91 kB (181.62 kB gzip). The existing >500 kB chunk warning remains technical debt.
- `npm audit --omit=dev --audit-level=high`: PASS — two moderate React Router advisories only; no
  high or critical production dependency finding.
- Full audit inventory: 11 transitive findings in production plus development tooling combined
  (6 moderate, 4 high, 1 critical). High/critical items are confined to development/build tooling;
  breaking upgrades remain a separate maintenance milestone.
- Authenticated representative-data visual comparison and target-device/browser review:
  `PENDING – Host Machine Validation`.

## Approved phase priorities

1. `UI-TASTE-01` — documentation and audit baseline — complete.
2. `UI-TASTE-02` — shared enterprise design system — implemented; owner approval pending.
3. `UI-TASTE-03` — Dashboard redesign — blocked until owner approval.
4. `UI-TASTE-04` — responsive, accessibility, representative-data, bundle, and route-performance
   regression.
5. `UI-TASTE-05` — final owner review and merge closeout.

## Maintenance rule

At closeout, re-read live Git, migration, OpenAPI, dependency, build, and test evidence. Do not claim
visual production acceptance from source or jsdom tests alone, and do not begin Priority 2 before the
owner approves this milestone.
