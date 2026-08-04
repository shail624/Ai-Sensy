# Design Document 34 — UI-TASTE-03B Reactivation Operational Hierarchy

**Status:** Repository implementation record

**Milestone:** UI-TASTE-03B

**Authority:** ADR-0012, ADR-0017, Design Documents 25 and 30, and `ROADMAP.md`

## Purpose and boundary

This milestone makes the completed lightweight Reactivation CRM the unmistakable day-to-day
operator workspace. It improves hierarchy, prioritization, bounded pagination, responsive density,
permission truth, and route continuity without creating a new Reactivation, reminder, KYC, SIM,
Activation, saved-view, reporting, or audit authority.

Provider certification, QR runtime, live WhatsApp sessions, event ingestion, history
synchronization, media transfer, provider adapters, target-host commissioning, production
credentials, and all Module 13 live behavior remain out of scope and blocked.

## Repository reuse map

| Need | Existing authority reused | Milestone extension |
|---|---|---|
| Primary operator workflow | `ReactivationCase`, `ViDomainService`, existing pipeline API, board/list/drawer | Make `/reactivation` resolve to the real CRM and emphasize status, due work, SLA, ownership, documents, and next task. |
| Work prioritization | Existing Task-backed reminder projection and SLA evidence | Add factual All active, Due today, Overdue, and Completed URL-backed work views. |
| Search and filters | Existing pipeline query, Contact/User identities, status/label/reminder filters | Recompose with shared `FilterBar`, `Field`, `Input`, `Select`, and URL query state. |
| Bounded scale | Existing stable tenant-scoped repository order and `total` count | Add an additive non-negative offset query and shared previous/next pagination at 25 records per page. |
| Permissions | Existing Reactivation, KYC, Document, and Analytics route guards | Hide secondary navigation that the current role cannot open; no permission or policy changes. |
| Historical links | Existing pipeline statuses and Contact import workflow | Redirect old SIM, Activation, Completed, Interested, and bulk-eligibility links to factual existing workflows. |
| Evidence and mutation | Existing optimistic concurrency, Audit, Customer Timeline, Task, Document, KYC, and transition commands | No mutation behavior changes; every move and case edit remains server-owned. |
| UI language | Existing PageHeader, Badge, Button, Card, FilterBar, Toolbar, Pagination, form controls, Modal, Empty/Error/Skeleton states | Remove one-off filter controls and foundation placeholder panels. |

No completed Contact, Task, Notification, KYC, Document, SIM, Activation, Analytics, RBAC, tenant,
Audit, Timeline, route-shell, or design-system authority is rebuilt.

## Operational hierarchy

The Reactivation root redirects to `/reactivation/pipeline`. Primary Reactivation navigation contains
only connected, permission-available destinations:

1. Reactivation CRM
2. KYC Operations
3. Document Center
4. Reports

Foundation-only SIM, Activation, eligibility, bulk, interested, and completed pseudo-workspaces are
not presented as equal product destinations. Existing bookmarks remain valid through explicit
redirects:

- SIM Orders → CRM filtered to `sim_required`
- Activation → CRM filtered to `activation_pending`
- Completed → CRM filtered to `completed`
- Interested → CRM filtered to `lead_confirmed`
- Bulk eligibility → existing Contact import workflow
- Eligible Numbers → CRM list without inventing an unsupported eligibility-only filter

The redirects preserve navigation continuity while avoiding a second operating model.

## Pagination and query contract

`GET /api/v1/reactivation-pipeline` gains an optional `offset` query parameter constrained to
non-negative values. The existing stable `updated_at DESC, id DESC` ordering, tenant predicates,
filter predicates, total count, batched evidence queries, and 200-record server ceiling remain
authoritative. The UI requests 25 records and exposes previous/next navigation through the shared
pagination component.

Offset is reset whenever a material filter changes. Search, status, label, owner, reminder bucket,
reminder date, display mode, and page are encoded in the URL so refresh and sharing preserve the
operator's context. These are truthfully described as URL-backed work views, not server-shared saved
views.

## Security and correctness

- The API remains protected by `reactivation:read`.
- Every query retains organization predicates and active-record predicates.
- KYC, Document, and Report tabs use the same permissions as their route guards.
- No client-side count is promoted as a server total.
- No optimistic mutation, transition, assignment, reminder, audit, or timeline contract changes.
- Terminal cards are no longer advertised as draggable.
- No secret, customer document content, or provider data is added to the URL.

## Verified defects addressed

1. The Reactivation shell advertised foundation-only placeholder workspaces as equal operational
   destinations despite ADR-0017's single lightweight CRM decision.
2. Secondary tabs disclosed routes that the current role could not open.
3. The pipeline loaded and rendered up to 200 records without navigation despite already returning a
   total count.
4. Filter and view context disappeared on refresh and could not be shared.
5. Reactivation duplicated shared filter/form styling instead of using the governed components.
6. Terminal cases remained draggable even though the server exposed no permitted transition.
7. A visible result summary contained a malformed `Â·` encoding sequence.
8. Reactivation page copy still described completed KYC/domain capability as future or gated.

## Responsive and accessibility behavior

The shared controls retain labelled inputs, keyboard focus, minimum mobile target sizes, semantic
navigation, live result summaries, actionable empty/error states, and focus-managed mutation
dialogs. Desktop keeps dense board/list operation; mobile retains the list/card transformation and
horizontal Kanban overflow without page-level horizontal overflow.

Repository tests cover URL restoration, page transitions, filter page reset, work-view truth,
permission-scoped navigation, historical redirects, read-only behavior, terminal drag behavior,
loading/empty/error states, and existing case-detail workflows.

## Validation boundary

Repository validation can prove source formatting, strict typing, generated-contract consistency,
tenant-safe pagination behavior, focused and full backend/frontend regressions, production build,
dependency/security scans, and unchanged migration lineage.

Authenticated representative-data visual comparison, browser/device matrix, screen-reader review,
and production-scale query timing remain `PENDING – Host Machine Validation`. They are not required
to claim Repository Validated implementation and are not fabricated here.

## Premium screen Definition of Done

UI-TASTE-03B satisfies the repository-verifiable portions of all twenty Design Document 25 checks:
approved scope, real backend data, clear primary goal, consistent hierarchy, shared-component reuse,
original implementation, no gated feature exposure, truthful states, explicit mutation behavior,
bounded pagination, responsive/accessibility contracts, preserved RBAC/tenant/audit boundaries,
tests, performance-conscious rendering, and this comparison record.

Host-only visual, assistive-technology, and representative-data evidence remains explicitly pending.
