from __future__ import annotations

import re
from pathlib import Path

STAMP = "2026-08-04T03:00:00+05:30"
BASELINE = "7d826987c272d28038663ba9cb15c832c37e2b02"


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"Could not update {label}; matches={count}")
    return updated


project_state = f'''# Project State

> Current repository snapshot. GitHub is the implementation source of truth. `HEAD` is symbolic
> because a commit cannot embed its own final hash; resolve it after push with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `ui/taste-modernization` |
| Priority 2 starting baseline | `{BASELINE}` (`feat(ui): modernize shared enterprise design system`) |
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
| Last update | `{STAMP}` (Asia/Kolkata) |

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
'''
Path("PROJECT_STATE.md").write_text(project_state, encoding="utf-8")

tracker = f'''# Implementation Tracker (canonical)

> GitHub at the latest approved HEAD is the repository source of truth. Keep repository-verifiable
> engineering evidence separate from authenticated host visual acceptance.

_Last updated: 2026-08-04 · UI-TASTE-03A operator-first Dashboard is implemented and repository-
validated. Reactivation redesign has not started._

## Current state

- **Branch:** `ui/taste-modernization`
- **Priority 2 baseline:** `{BASELINE}`
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
'''
Path("IMPLEMENTATION_TRACKER.md").write_text(tracker, encoding="utf-8")

module_path = Path("MODULE_STATUS.md")
module = module_path.read_text(encoding="utf-8")
module = re.sub(r"Last synchronized: `[^`]+`\.", f"Last synchronized: `{STAMP}`.", module, count=1)
module = replace_once(
    module,
    r"## UI Taste Modernization — Priority 1 implementation\n.*?Completion percentages below remain domain-capability measures\. Shared polish improves consistency\nwithout falsely inflating business-workflow completion\.\n\n",
    '''## UI Taste Modernization — operator-first Dashboard\n\n- **Starting baseline:** `7d826987c272d28038663ba9cb15c832c37e2b02`.\n- **Status:** `UI-TASTE-03A` is implemented and repository-validated; authenticated representative-\n  data visual/reference review remains pending.\n- **Delivered:** cross-domain attention queue; blocked customer, KYC, SIM, Activation, Campaign,\n  Inbox, Template, agent-workload and today-KPI decision support; signed-in task snapshot; truthful\n  partial-source states; source deep links; responsive table/card transformations.\n- **Preserved:** backend, migrations, 193-path OpenAPI, generated contracts, permissions, source\n  workflows, sidebar/navigation, primary action links and existing shared design system.\n- **Performance:** operational workspace is lazy-split at 31.96 kB / 8.61 kB gzip; main chunk is\n  733.62 kB / 178.16 kB gzip, down from the Priority 1 measurement of 747.91 kB.\n- **Next:** Reactivation operational hierarchy only, blocked pending owner approval.\n\nCompletion percentages remain evidence-based domain/product estimates. Host visual acceptance and\nproduction-scale exact aggregate totals are not claimed by repository-only validation.\n\n''',
    "MODULE_STATUS UI section",
)
module = replace_once(
    module,
    r"\| Dashboard \|[^\n]+\n",
    "| Dashboard | 82% | UI-TASTE-03A replaces the messaging-led home with a permission-aware operational desk over real Reactivation, KYC, Task, Campaign, Inbox, Template and Analytics sources; 661 frontend tests and production build pass | Authenticated representative-data visual/WCAG/browser review, server-owned exact cross-domain aggregate totals beyond bounded source reads, and final route-performance commissioning. | Reactivation, KYC, Tasks, Campaigns, Inbox, Templates, Analytics |\n",
    "Dashboard module row",
)
module_path.write_text(module, encoding="utf-8")

validation_path = Path("VALIDATION_RESULTS.md")
validation = validation_path.read_text(encoding="utf-8")
validation = re.sub(r"Last synchronized: `[^`]+`\.", f"Last synchronized: `{STAMP}`.", validation, count=1)
section = '''\n## UI-TASTE-03A operator-first Dashboard\n\n| Validation item | Status | Latest evidence |\n|---|---|---|\n| Latest Git baseline | PASS | Work begins from `7d826987c272d28038663ba9cb15c832c37e2b02` on `ui/taste-modernization`; no completed work is recreated. |\n| Operator question coverage | PASS | Existing authorized sources answer attention, blocked customers, pending KYC, SIM SLA risk, overdue Activation, Campaign action, unread replies, blocked Templates, agent workload and today KPI change. |\n| Source truth and boundaries | PASS | Dashboard composes existing APIs only; no backend, duplicate projection, fake count, local persistence or generated-contract edit exists. Failed sources are disclosed and never rendered as zero. |\n| Permissions and tenant behavior | PASS | Queries are enabled only when their existing read permission is present; source APIs retain tenant/RBAC authority and deep links. |\n| Loading, empty and error states | PASS | Accessible skeletons, factual empty states, partial-source warning, source-specific retry and permission-empty state are implemented. |\n| Accessibility and responsive contracts | PASS | Semantic links/buttons/headings/tables, focus-visible treatment, live loading status, touch-safe actions and desktop-table/mobile-card transformations are present; existing layout regressions pass. |\n| Decision rules | PASS | Four focused tests cover blockers, KYC/Campaign/Inbox/Template action classification, agent aggregation and metric-aware KPI direction. |\n| Full frontend gates | PASS | Production audit, ESLint and TypeScript pass; 34 Vitest files / 661 tests pass; Vite production build passes. |\n| Verified bug fixes | PASS | Strict typing caught and fixed KPI sentiment widening; full-suite regression caught and fixed loss of Live Chat/New Campaign link semantics. |\n| Performance | PASS | Dashboard is lazy-split to 31.96 kB / 8.61 kB gzip; main chunk improves from 747.91 kB to 733.62 kB, though the existing >500 kB warning remains. |\n| Migration/API/dependency boundary | PASS | Migration remains `0035_notification_center`; OpenAPI remains 193 paths; no generated client or package dependency changes. |\n| Authenticated representative-data visual/reference review | PENDING – Host Machine Validation | Repository/jsdom/build gates cannot prove final density, long-content overflow, contrast, screen-reader behavior or approved-reference comparison on target devices. |\n| Milestone boundary | PASS | Only Dashboard composition, conditional-query support, focused tests and required governance evidence are included; Reactivation redesign is absent. |\n\n'''
if "## UI-TASTE-03A operator-first Dashboard" not in validation:
    validation = validation.replace("\n## UI-TASTE-02 shared enterprise design system\n", section + "## UI-TASTE-02 shared enterprise design system\n", 1)
validation_path.write_text(validation, encoding="utf-8")

changelog_path = Path("CHANGELOG.md")
changelog = changelog_path.read_text(encoding="utf-8")
entry = '''\n### 2026-08-04 — Operator-first operational Dashboard (UI-TASTE-03A)\n\n**Added**\n- Added a permission-aware operational desk that prioritizes blocked Reactivation customers, KYC\n  reviews, SIM/Activation SLA risk, Campaign failures, waiting conversations, blocked Templates,\n  agent workload and today KPI changes using existing source authorities.\n- Added truthful loading, empty, partial-source error and permission states, governed source actions,\n  signed-in task snapshot, responsive table/card transformations and four focused selector tests.\n\n**Changed**\n- Replaced the messaging-led Dashboard with decision-first operational intelligence while preserving\n  Live Chat/New Campaign primary links and all source workflows.\n- Added optional `enabled` controls to existing Reactivation, KYC, Template and Analytics query hooks\n  so unauthorized Dashboard sources issue no request.\n- Lazy-split the operational workspace behind an accessible skeleton. The main chunk improves from\n  747.91 kB to 733.62 kB; the Dashboard workspace is 31.96 kB / 8.61 kB gzip.\n\n**Fixed**\n- Fixed strict TypeScript widening of KPI sentiment literals.\n- Fixed a regression where primary Dashboard navigation actions had become buttons instead of real\n  links; the established accessibility/navigation contract is restored.\n\n**Validated**\n- Production dependency audit, ESLint, TypeScript, 34 Vitest files / 661 tests and production build\n  pass. Migration `0035`, 193-path OpenAPI, generated client, backend and dependencies are unchanged.\n- Authenticated representative-data visual/reference review remains `PENDING – Host Machine\n  Validation`; bounded source reads are not claimed as exact enterprise totals.\n'''
if "Operator-first operational Dashboard (UI-TASTE-03A)" not in changelog:
    changelog = changelog.replace("\n## [Unreleased]\n", "\n## [Unreleased]\n" + entry, 1)
changelog_path.write_text(changelog, encoding="utf-8")

roadmap_path = Path("ROADMAP.md")
roadmap = roadmap_path.read_text(encoding="utf-8")
roadmap = re.sub(r"Last synchronized: `[^`]+`\.", f"Last synchronized: `{STAMP}`.", roadmap, count=1)
roadmap = replace_once(
    roadmap,
    r"`UI-TASTE-01` documentation/audit baseline is complete\..*?Dashboard redesign is blocked until that approval\.\n",
    "`UI-TASTE-01` documentation/audit and `UI-TASTE-02` shared design-system modernization are complete. `UI-TASTE-03A` operator-first Dashboard is implemented and repository-validated from baseline `7d826987`; authenticated representative-data visual/reference review remains pending. `UI-TASTE-03B` Reactivation operational hierarchy is blocked pending owner approval.\n",
    "ROADMAP UI status",
)
roadmap = roadmap.replace(
    "| UI-TASTE-03 — Priority screen modernization — BLOCKED PENDING APPROVAL | Apply the shared system to the highest-value daily workflows one reviewed screen milestone at a time. | Begin with Dashboard only; later approvals cover Reactivation, Inbox, Contacts, Customer 360 and Notification Center. Preserve real data, permissions, business rules, routes and generated contracts. | Priority 1 is owner-approved first; each screen then passes functional and representative-data desktop/tablet/mobile review with no fake metric, placeholder workflow or backend duplication. |",
    "| UI-TASTE-03A — Operator-first Dashboard — IMPLEMENTED | Replace the messaging-led first screen with factual operational intelligence. | Cross-domain attention, blocked customers, KYC, SIM/Activation SLA risk, Campaigns, unread conversations, Templates, agent workload, today KPI changes, task snapshot and source actions. | Repository gates pass with 661 tests and split build; no fake metric/backend duplication; authenticated representative-data visual/reference review remains pending. |\n| UI-TASTE-03B — Reactivation operational hierarchy — BLOCKED PENDING APPROVAL | Apply the shared system to the highest-value Reactivation operator workflow without rebuilding its authority. | Stage/action hierarchy, due/reminder/SLA prioritization, connected-vs-foundation maturity, saved-view/pagination truth and responsive density. | Owner approves Dashboard closeout first; real persisted behavior, permissions, source contracts and representative-data review pass. |",
)
roadmap_path.write_text(roadmap, encoding="utf-8")

for name in (
    "PROJECT_STATE.md",
    "MODULE_STATUS.md",
    "IMPLEMENTATION_TRACKER.md",
    "VALIDATION_RESULTS.md",
    "CHANGELOG.md",
    "ROADMAP.md",
):
    if not Path(name).read_text(encoding="utf-8").strip():
        raise RuntimeError(f"{name} became empty")
