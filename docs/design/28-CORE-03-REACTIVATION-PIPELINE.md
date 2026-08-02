# Design Document 28 — CORE-03 Reactivation Pipeline

## Purpose and boundary

CORE-03 turns the existing Reactivation pipeline route into a real operational workspace over the
CORE-02 Vi domain. It delivers the approved fifteen-stage board/list workflow, factual dashboard
counts, assignments, evidence, tasks/reminders, documents, SLA, and accessible responsive actions.
It does not begin the CORE-04 KYC workspace, add a migration, or recreate any completed module.

## Repository reuse map

| Existing capability | Existing extension point | Extension | Genuine gap |
|---|---|---|---|
| Reactivation route/workspace | `frontend/src/pages/ReactivationPage.tsx`, `frontend/src/features/reactivation/ReactivationPipelineBoard.tsx`, `sections.ts`, router | Existing route and board now render persisted projection data and honest states. | Typed client hooks and a case-detail drawer. |
| CORE-02 Vi authority | `models/vi_domain.py`, `repositories/vi_domain.py`, `services/vi_domain_service.py`, `schemas/vi_domain.py`, `api/v1/endpoints/vi_domain.py` | Existing repository/service/API layers compose the pipeline and keep transition/update commands authoritative. | One joined projection path and note read/write paths. |
| Contacts and ownership | Contact/User models, `features/admin/api.ts` | Existing tenant contact identity, typed attributes, and user directory supply card, reservation, family, and assignee facts. | Permission-aware user-query enablement. |
| Documents | `DocumentWorkspace`, document aggregate/service | Existing compact document workspace is embedded in the case drawer. | None. |
| Customer 360 | Existing `/contacts/:id` profile | Drawer deep-links to the canonical customer context. | None. |
| Tasks/reminders | `TasksSectionForProfile`, Task repository/service/API | Existing persisted task form/list is reused with read/write permission checks. | Permission-aware embedded boundary. |
| Audit and Timeline | `AuditService`, `ContactEventService`, contact-event repository/model | Stage transitions remain CORE-02-owned; notes append the existing audit and Customer Timeline evidence. | Reference-scoped immutable note listing. |
| SLA | CORE-02 SLA policy/event records and repository | Latest SLA fact is batched into cards and shown as due/breach evidence. | None. |
| Design system | `Modal`, cards, badges, empty/error/skeleton controls, responsive shell | Existing Modal gains a drawer width/placement variant with the same focus trap and restoration. | Drawer presentation only. |

No completed Contacts, Inbox, Campaigns, Templates, Documents, Customer 360, Tasks, Analytics,
Automation, RBAC, Audit, Timeline, queue, or design-system authority was rebuilt.

## Data projection and API contract

`GET /api/v1/reactivation-pipeline` accepts bounded search, stage, and owner filters. The repository
joins tenant-scoped cases to Contact and User once, computes stage counts, and batches latest
eligibility/stage/SLA evidence plus task/document aggregates. The service derives only explicit
presentation facts from persisted values: reservation and family-plan values come from typed
contact attributes; conversion follows terminal persisted stages. It returns all fifteen counts,
the true total, at most 200 visible cards, and server-computed permitted transitions.

Case notes use `ContactEvent.EVENT_REACTIVATION_NOTE_ADDED`. The event payload contains the bounded
note and actor UUID; writes atomically append audit and Customer Timeline evidence. The history is
immutable and tenant/reference scoped. No mutable notes table or second timeline is introduced.

## Interaction model

The desktop board follows the approved dense filter/table/workspace rhythm: summary metrics,
search and owner filters, board/list switch, refresh, horizontally scrollable fifteen-stage board,
and a shared side drawer. Tablet collapses metrics and controls into two columns. Mobile uses a
single-column list, horizontal section tabs, the existing bottom navigation, and the same drawer as
a full-width overlay.

Cards expose factual identity, owner, eligibility, task/document counts, SLA status, and row
version. Pointer drag/drop and `Alt+ArrowLeft`/`Alt+ArrowRight` request only a server-published next
stage. A confirmation dialog collects a reason and makes the existing idempotent transition call.
On success, all relevant real queries are invalidated; on stale versions or rejected prerequisites,
the server problem response is displayed and no local stage mutation is retained.

The drawer contains:

- persisted case, reservation, family, conversion, rejection, document, and SLA facts;
- permission-aware owner/number updates using optimistic concurrency;
- immutable eligibility decisions and rejection reasons;
- server-owned next actions;
- immutable stage history and internal notes;
- the existing task/reminder and governed document workspaces;
- a canonical Customer 360 link.

## Visual reference and originality review

Reviewed paired `_full.png` and `_viewport.png` captures:

- `0008_contacts_filter` for compact filter hierarchy and overlay behavior;
- `0010_campaigns_tab_all` for dense toolbar/table/list rhythm;
- `0004_contacts_add_contact` for centered dialog organization and action placement;
- `0001_live_chat_active` for operational context density and drawer/panel relationships.

Workflow familiarity is retained through relative hierarchy, density, compact controls, status
presentation, and responsive transformations. Intentional differences preserve the original Vi
branding, design tokens, Lucide-based icon language, wording, color system, component dimensions,
and the domain-specific fifteen-stage lifecycle. `.reference/aisensy/` remains ignored and is not
part of the repository.

## New files and necessity

| New file | Necessity |
|---|---|
| `frontend/src/features/reactivation/types.ts` | Central generated-contract aliases plus the approved ordered stage/label catalogue. |
| `frontend/src/features/reactivation/api.ts` | Typed React Query hooks over existing/generated CORE-02 contracts, idempotency, concurrency, and cache invalidation. |
| `frontend/src/features/reactivation/ReactivationCaseDrawer.tsx` | One composed case workspace that reuses Customer 360, Tasks, Documents, eligibility, history, and shared Modal. |
| `frontend/src/features/reactivation/reactivation.test.tsx` | Focused persisted-data, transition, permission, state, accessibility, responsive, and no-mock regression coverage. |
| `docs/adr/0015-governed-reactivation-pipeline.md` | Permanent authority/reuse decision. |
| `docs/design/28-CORE-03-REACTIVATION-PIPELINE.md` | Permanent design, reuse, reference, validation, and file-boundary record. |

No new backend module file or migration is necessary; verified gaps extend existing files in place.

## Validation

- 938 backend tests pass, including exact permitted/rejected transition coverage, tenant isolation,
  RBAC, assignment, immutable history/note evidence, concurrency, and pipeline projection tests.
- 641 frontend tests pass, including five focused Reactivation tests for real data, drag/keyboard
  movement, refresh-preserving query state, permission/loading/empty/error boundaries, drawer
  accessibility, and responsive list/board behavior.
- OpenAPI drift, generated TypeScript contracts, Ruff, strict mypy across 252 files, ESLint,
  TypeScript, Playwright types, and production build pass.
- Authenticated live review passes at 1280×720, 768×1024, and 390×844 with no page-level horizontal
  overflow. The list toggle exposes correct `aria-pressed` state; controls have accessible names.
- The 20-step release gate and 22-step isolated deployed gate pass. MySQL applies migration `0032`;
  Redis and all Celery workers/beat are healthy; Playwright passes 1/1; the standard-read canary is
  8.547 ms p95 across 30 samples against the 300 ms budget.

## Known limits and next boundary

The visible card window is capped at 200 and does not yet provide server pagination or virtualized
columns. Full load/stress/spike/soak certification remains Performance Lab work. React Router emits
existing v7 future-flag warnings and the production bundle retains its known size warning. CORE-04
is the next milestone and owns protected KYC operations; this milestone adds no KYC operational UI.
