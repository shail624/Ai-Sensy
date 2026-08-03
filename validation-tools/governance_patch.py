from __future__ import annotations

import re
from pathlib import Path

STAMP = "2026-08-04T01:38:00+05:30"
START = "9043fe03a80b682a010304c88c5d29d8ec77d1fa"
ORIGINAL = "62d4daa50617e2e0c8fff9f5ec9a514848a77f98"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Missing expected text for {label}")
    return text.replace(old, new, 1)


module_path = Path("MODULE_STATUS.md")
module = module_path.read_text(encoding="utf-8")
module = module.replace(
    "Last synchronized: `2026-08-04T01:27:00+05:30`.",
    f"Last synchronized: `{STAMP}`.",
)
new_section = f"""## UI Taste Modernization — Priority 1 implementation

- **Starting baseline:** `{START}`.
- **Status:** `UI-TASTE-02` is implemented and repository-validated; owner approval and authenticated
  representative-data visual comparison remain pending before Dashboard work.
- **Delivered:** named enterprise radius tiers; shared form, toolbar, filter, pagination, Button,
  Card, PageHeader, and PageContainer improvements; adoption in Contacts, Inbox, and Notification
  Center; focused shared-primitive regressions.
- **Preserved:** sidebar/navigation/routes, backend, migrations, OpenAPI/generated contracts,
  permissions, workflows, keyboard/focus, reduced motion, responsive/mobile behavior, semantic
  themes, and source-domain ownership.
- **Validation:** ESLint, TypeScript, 657 Vitest tests, production build, and high-severity production
  dependency audit pass. Host visual/reference review is pending.
- **Next:** Dashboard redesign only, blocked until owner approval.

Completion percentages below remain domain-capability measures. Shared polish improves consistency
without falsely inflating business-workflow completion.

"""
if "## UI Taste Modernization — Priority 1 implementation" not in module:
    module, count = re.subn(
        r"## UI Taste Modernization implementation plan\n.*?The plan does not change module completion percentages\. Percentages move only after implemented,\ntested, evidence-backed application changes\.\n\n",
        new_section,
        module,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise RuntimeError("Could not replace Module Status UI plan section")
module = replace_once(
    module,
    "| Inbox | 91% | Shared Inbox + Live Chat plus CORE-07 exact-contact conversation reuse | UI-TASTE shared-control convergence, intervention-request lifecycle, SLA badges, and final responsive/accessibility regression. | Notifications, SLA, shared design system |",
    "| Inbox | 91% | Shared Inbox + Live Chat plus CORE-07 exact-contact reuse; UI-TASTE-02 converges search, advanced filters, saved views, bulk selects, and pagination on shared accessible controls | Page-specific hierarchy polish, intervention-request lifecycle, SLA badges, and authenticated responsive/accessibility regression. | Notifications, SLA, shared design system |",
    "Inbox row",
)
module = replace_once(
    module,
    "| Contacts | 95% | FR-CON-04 release-ready baseline | UI-TASTE toolbar/table/pagination/bulk-action consistency plus final scope regression for opt-in, eligibility, assignment/export and server-shared saved views; no rebuild. | Saved Views, Reactivation, shared design system |",
    "| Contacts | 95% | FR-CON-04 baseline plus UI-TASTE-02 shared search/filter/mobile-sheet/pagination convergence | Page-specific table and bulk-action polish, final opt-in/eligibility/assignment/export regression, and server-shared saved views; no rebuild. | Saved Views, Reactivation, shared design system |",
    "Contacts row",
)
module = replace_once(
    module,
    "| Notifications | 85% | CORE-09 unified durable Notification Center: tenant/user-scoped records, unread count, mark-one/all-read, deep links, read-only team filter, 15-second polling, Task/Reactivation projections, Audit evidence, migration `0035`, and 193-path generated contract | UI-TASTE visual/density pass, final full frontend/regression evidence, notification settings, and separately approved optional delivery channels. SSE/browser push/email/internal WhatsApp are not implied by CORE-09. | Tasks, Reactivation, user preferences, shared design system |",
    "| Notifications | 85% | CORE-09 durable center plus UI-TASTE-02 shared type/status/date/assignee filters and action controls; polling, read-state, team view and deep links are preserved | Page-specific visual hierarchy, authenticated responsive review, notification settings, and separately approved optional channels. SSE/browser push/email/internal WhatsApp are not implied. | Tasks, Reactivation, user preferences, shared design system |",
    "Notifications row",
)
if "| Shared Enterprise Design System |" not in module:
    marker = "| Team Management | 80% | Users, roles, permissions, workload foundations complete |"
    addition = (
        "| Shared Enterprise Design System | 90% | UI-TASTE-02 implements governed radius/density, forms, toolbars, filters, pagination, page headers and shared surface refinements with 657-test validation | Authenticated representative-data visual/reference approval, remaining priority-screen adoption, route-level bundle optimization, and final WCAG/browser matrix. | UI-TASTE-03–05 |\n"
    )
    module = replace_once(module, marker, addition + marker, "shared design system row")
module_path.write_text(module, encoding="utf-8")


changelog_path = Path("CHANGELOG.md")
changelog = changelog_path.read_text(encoding="utf-8")
if "Shared enterprise design-system modernization (UI-TASTE-02)" not in changelog:
    entry = """
### 2026-08-04 — Shared enterprise design-system modernization (UI-TASTE-02)

**Added**
- Added original shared `Input`, `Select`, `Textarea`, `Field`, `Toolbar`, `FilterBar`, and cursor
  `Pagination` primitives with semantic focus, disabled, invalid, busy, label, help, error, icon,
  action, summary, and mobile touch-target behavior.
- Added named `control`, `surface`, and `overlay` radius tiers so enterprise density can converge
  without silently changing legacy sidebar or navigation utilities.
- Added three focused shared-primitive tests covering semantic labels, invalid state, pagination
  callbacks/disabled state, and loading-button accessibility.

**Changed**
- Refined shared Button, Card/CardHeader, PageHeader, and PageContainer hierarchy, spacing, elevation,
  responsive action alignment, and restrained interaction treatment.
- Replaced duplicated Contacts search/filter/mobile-sheet/pagination styling, Inbox search/advanced-
  filter/saved-view/bulk-select/pagination styling, and Notification Center filter/action styling
  with governed shared components. Existing URL state, shortcuts, bulk behavior, polling, read
  state, permissions, and source deep links are unchanged.

**Preserved**
- Sidebar, navigation, routes, backend, migrations, OpenAPI, generated contracts, dependencies,
  permissions, real workflows, keyboard/focus handling, reduced motion, responsive navigation, and
  source-domain ownership are unchanged. No heavy animation library, copied reference implementation,
  proprietary asset, fake metric, or parallel component system was introduced.

**Validated**
- ESLint and TypeScript pass; all 33 Vitest files and 657 tests pass; the production build passes
  after transforming 2,599 modules. The main application chunk is 747.91 kB minified / 181.62 kB
  gzip and retains the known >500 kB warning.
- The production dependency audit has no high/critical finding and reports two moderate React Router
  advisories. The combined development-tool inventory reports 11 transitive findings and remains a
  separately governed dependency-modernization task.
- Authenticated representative-data desktop/tablet/mobile and approved-reference visual comparison
  remains `PENDING – Host Machine Validation`; Priority 2 is blocked pending owner approval.
"""
    changelog = replace_once(changelog, "## [Unreleased]\n", "## [Unreleased]\n" + entry, "changelog entry")
changelog_path.write_text(changelog, encoding="utf-8")


validation_path = Path("VALIDATION_RESULTS.md")
validation = validation_path.read_text(encoding="utf-8")
validation = re.sub(
    r"> Status vocabulary is restricted to `PASS`, `FAIL`, and\n> `PENDING – Host Machine Validation`\..*?authorities\.\n",
    "> Status vocabulary is restricted to `PASS`, `FAIL`, and\n> `PENDING – Host Machine Validation`. This ledger records the latest applicable evidence and\n> separates repository-verifiable engineering gates from target-host visual/commissioning evidence.\n",
    validation,
    count=1,
    flags=re.S,
)
validation = validation.replace(
    "Last synchronized: `2026-08-02T17:34:14+05:30`.",
    f"Last synchronized: `{STAMP}`.",
)
if "## UI-TASTE-02 shared enterprise design system" not in validation:
    section = f"""
## UI-TASTE-02 shared enterprise design system

| Validation item | Status | Latest evidence |
|---|---|---|
| Starting baseline and branch | PASS | Implementation starts from `{START}` and targets `ui/taste-modernization`; the original CORE-09 lineage remains `{ORIGINAL}`. |
| Shared architecture | PASS | Existing React/Tailwind architecture is extended in place with named radius tiers, forward-ref form controls, toolbar/filter composition, cursor pagination, and refinements to existing Button/Card/PageHeader/PageContainer primitives; no parallel design system exists. |
| Product workflow preservation | PASS | Contacts URL filters/import/bulk flow, Inbox quick views/search shortcut/saved views/bulk mutations/thread flow, and Notification polling/read/team/deep-link behavior are unchanged. |
| Sidebar, navigation and contract boundary | PASS | Sidebar, TopNav structure, command palette, mobile navigation, routes, permissions, backend, migration `0035`, 193-path OpenAPI, generated client, and dependencies are unchanged. |
| Accessibility and responsive contracts | PASS | Shared controls retain labels, forward refs, focus-visible rings, invalid/disabled/busy semantics and mobile targets; existing 21 layout, 24 Inbox, 4 Contacts toolbar and 3 Notification Center tests pass. |
| Focused shared-primitive regression | PASS | Three new tests cover semantic labels/help/errors, invalid state, action slots, cursor pagination disabled/callback behavior, and loading-button accessible name/`aria-busy`. |
| Lint, typecheck and full frontend suite | PASS | ESLint passes; `tsc --noEmit` passes; 33 Vitest files and 657 tests pass. |
| Production build and bundle measurement | PASS | Vite transforms 2,599 modules and builds successfully; CSS is 49.39 kB / 9.79 kB gzip and the main application chunk is 747.91 kB / 181.62 kB gzip. The known >500 kB warning remains recorded debt. |
| Production dependency boundary | PASS | `npm audit --omit=dev --audit-level=high` reports only two moderate React Router advisories and no high/critical production finding. Combined development/build tooling reports 11 transitive findings and requires a separate upgrade milestone. |
| Originality and scope | PASS | Implementation is original, uses existing semantic product tokens and Lucide icons, imports no reference code/assets/branding/layout, adds no fake data/metric/placeholder, and introduces no heavy animation library. |
| Authenticated representative-data visual and reference comparison | PENDING – Host Machine Validation | Source review and jsdom tests cannot prove final visual density, long-content overflow, screen-reader behavior, or desktop/tablet/mobile comparison against the approved reference library. Owner/host review is required before Priority 2. |
| Milestone boundary | PASS | Only Priority 1 shared-system work and required governance evidence are included; Dashboard and all other Priority 2 screen redesign work remain absent. |

"""
    validation = replace_once(
        validation,
        "## CORE-07 Customer 360 domain convergence\n",
        section + "## CORE-07 Customer 360 domain convergence\n",
        "validation section",
    )
validation_path.write_text(validation, encoding="utf-8")


roadmap_path = Path("ROADMAP.md")
roadmap = roadmap_path.read_text(encoding="utf-8")
roadmap = roadmap.replace(
    "Last synchronized: `2026-08-04T01:27:00+05:30`.",
    f"Last synchronized: `{STAMP}`.",
)
roadmap = replace_once(
    roadmap,
    "- UI Taste Modernization implementation baseline:\n  `62d4daa50617e2e0c8fff9f5ec9a514848a77f98`.",
    f"- UI Taste Modernization lineage baseline: `{ORIGINAL}`.\n- Priority 1 starting baseline: `{START}`.",
    "roadmap baseline",
)
roadmap = replace_once(
    roadmap,
    "The owner has approved `UI-TASTE-01 — Taste Modernization implementation plan` on branch\n`ui/taste-modernization`. UI-TASTE-01 is documentation only: no application code, dependency,\nmigration, OpenAPI, generated client, or runtime behavior may change in its commit.",
    "`UI-TASTE-01` documentation/audit baseline is complete. `UI-TASTE-02` shared enterprise\ndesign-system modernization is implemented and repository-validated; owner approval and\nauthenticated representative-data visual/reference comparison remain pending. `UI-TASTE-03`\nDashboard redesign is blocked until that approval.",
    "roadmap current status",
)
roadmap = replace_once(
    roadmap,
    "| UI-TASTE-01 — Documentation and audit baseline — APPROVED | Freeze branch, baseline, findings, boundaries, priorities, and acceptance order before coding. | Only `PROJECT_STATE.md`, `MODULE_STATUS.md`, `IMPLEMENTATION_TRACKER.md`, and `ROADMAP.md`; design variance `4/10`, motion `3/10`, density `8/10`. | One documentation-only commit on `ui/taste-modernization`; no application/dependency/contract/runtime change; remote HEAD verified. |",
    "| UI-TASTE-01 — Documentation and audit baseline — COMPLETE | Freeze branch, baseline, findings, boundaries, priorities, and acceptance order before coding. | Governance records only; design variance `4/10`, motion `3/10`, density `8/10`. | COMPLETE at `9043fe03`; documentation-only boundary and remote HEAD were verified. |",
    "UI-TASTE-01 row",
)
roadmap = replace_once(
    roadmap,
    "| UI-TASTE-02 — Shared design-system modernization | Establish consistent enterprise density and hierarchy before page work. | Existing tokens/primitives extended for radius, typography, fields/selects, page headers, toolbars, pagination, bulk actions, skeleton/empty/error states, responsive behavior, and restrained motion. | Shared components are reused by priority screens; no parallel component system; typecheck/lint/focused tests/build pass; accessibility contracts preserved. |",
    "| UI-TASTE-02 — Shared design-system modernization — IMPLEMENTED; OWNER APPROVAL PENDING | Establish consistent enterprise density and hierarchy before page work. | Named radius tiers; shared form, toolbar, filter and pagination primitives; Button/Card/PageHeader/PageContainer refinements; adoption in Contacts, Inbox and Notification Center. | Repository gates pass: lint, typecheck, 657 tests, build and production audit. Host visual/reference comparison and owner approval remain pending; no parallel component system or navigation redesign exists. |",
    "UI-TASTE-02 row",
)
roadmap = replace_once(
    roadmap,
    "| UI-TASTE-03 — Priority screen modernization | Apply the shared system to the highest-value daily workflows. | Dashboard → Reactivation → Inbox → Contacts → Customer 360 → Notification Center. Preserve real data, permissions, business rules, routes, and generated contracts. | Each screen passes its functional tests and representative-data desktop/tablet/mobile review; no fake metric, placeholder workflow, or backend duplication is introduced. |",
    "| UI-TASTE-03 — Priority screen modernization — BLOCKED PENDING APPROVAL | Apply the shared system to the highest-value daily workflows one reviewed screen milestone at a time. | Begin with Dashboard only; later approvals cover Reactivation, Inbox, Contacts, Customer 360 and Notification Center. Preserve real data, permissions, business rules, routes and generated contracts. | Priority 1 is owner-approved first; each screen then passes functional and representative-data desktop/tablet/mobile review with no fake metric, placeholder workflow or backend duplication. |",
    "UI-TASTE-03 row",
)
roadmap_path.write_text(roadmap, encoding="utf-8")

for path in (
    module_path,
    changelog_path,
    validation_path,
    roadmap_path,
):
    text = path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        path.write_text(text + "\n", encoding="utf-8")
