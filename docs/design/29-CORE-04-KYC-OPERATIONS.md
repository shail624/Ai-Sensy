# Design Document 29 — CORE-04 KYC Operations

## Purpose and boundary

CORE-04 delivers the governed KYC queue and case workflow over the CORE-02 domain foundation. It
covers prerequisites, original-holder/Delhi/active-number verification, protected Aadhaar/PAN
checklist references, appointment lifecycle, reviewer and manager decisions, immutable evidence,
approved Reactivation handoff, and Customer 360 projection. It does not begin SIM fulfilment or
create parallel document, task, approval, audit, timeline, or SLA authorities.

## Repository reuse map

| Existing capability | Existing file paths | Extension | Genuine gap |
|---|---|---|---|
| KYC domain authority | `backend/app/models/vi_domain.py`, `repositories/vi_domain.py`, `services/vi_domain_service.py`, `schemas/vi_domain.py`, `api/v1/endpoints/vi_domain.py` | Existing case/decision lifecycle gains the operations projection, checklist commands, appointment composition, structured reasons, separation rules, and approved handoff. | Durable document-purpose links, structured reasons, and operations projection. |
| Reactivation pipeline | `frontend/src/features/reactivation/ReactivationCaseDrawer.tsx`, `ReactivationPipelineBoard.tsx`, existing CORE-02 transition service | Existing case drawer creates/opens KYC; manager approval invokes the existing transition authority. | KYC tab and truthful create/open boundary. |
| Protected documents | `backend/app/models/contact_document.py`, document repository/service/API, `frontend/src/features/documents/DocumentWorkspace.tsx` | Existing verified protected documents are linked by UUID and reused in the checklist/workspace. | Purpose-to-document relation only. |
| Contacts and Customer 360 | Contact model/repository/API; `frontend/src/features/customer-profile/*` | Existing contact identity and profile project real KYC state and link to the KYC workspace. | KYC projection in the existing Reactivation profile section. |
| Tasks and appointments | `backend/app/models/task.py`, `services/task_service.py`, Task APIs and frontend hooks | Existing Task commands own scheduling, rescheduling, completion, cancellation, audit, immutable events, and Timeline. | Optional constrained KYC reference and creation idempotency. |
| Audit, Timeline, RBAC and SLA | Existing audit/contact-event services, permission catalogue/dependencies, CORE-02 SLA records | Existing tenant/permission filters and evidence paths cover every material operation; latest SLA facts are projected. | No new authority. |
| Shared UI system | Existing `Button`, `Badge`, `Modal`, `Skeleton`, `EmptyState`, `ErrorState`, table and form patterns | Existing primitives compose the queue, responsive cards, drawer, tabs, checklist, forms, and read-only boundaries. | KYC-specific composition only. |

No completed Contacts, Inbox, Campaigns, Templates, Documents, Customer 360, Tasks, Analytics,
Automation, RBAC, Audit, Timeline, queue, or design-system implementation is rebuilt.

## Persistence and contract

Migration `0033_kyc_operations` is additive from `0032_vi_domain_foundation`:

- `kyc_document_references` uniquely maps each KYC case and `aadhaar`/`pan` purpose to a protected
  `contact_documents` row, with tenant scope, restricted document deletion, row version, and audit
  fields;
- Task reference columns are constrained as an all-null pair or a `kyc_case` plus identifier, and
  tenant/idempotency uniqueness prevents duplicate appointment creation;
- KYC decision reason codes are limited to the governed catalogue.

No field accepts or returns an Aadhaar or PAN number. A checklist link is accepted only when the
Document Center row belongs to the same tenant and contact and is verified. Replacing/unlinking a
reference changes only the governed link, not the protected document.

Four additive paths advance OpenAPI from 184 to 188:

- `GET /api/v1/kyc-operations`;
- `GET/PUT /api/v1/kyc-cases/{kyc_id}/document-references` and
  `DELETE /api/v1/kyc-cases/{kyc_id}/document-references/{purpose}`;
- `GET/POST /api/v1/kyc-cases/{kyc_id}/appointments`.

Existing KYC create/update/decision/approval and Task update/complete/cancel paths are extended in
place. Generated OpenAPI JSON and TypeScript contracts remain the frontend contract authority.

## Workflow and authority rules

1. An eligible Reactivation case at `documents_received` creates one idempotent KYC case and enters
   `kyc_pending` through the existing stage command.
2. The operator records original-holder, Delhi-presence, and active-number verification with the
   current KYC row version.
3. Aadhaar and PAN checklist items reference verified, same-contact protected documents.
4. Appointments are Task records linked to the KYC case. Existing Task commands handle reschedule,
   complete, and cancel while retaining Task history and Customer Timeline entries.
5. A reviewer distinct from the requester records an immutable review. Rejection or information
   requests require a structured code and explanation.
6. A manager distinct from requester and reviewer can decide only after an approved review.
7. Manager approval requires all checks and verified checklist references, then moves Reactivation
   to `verification` through immutable CORE-02 stage events.

Every lookup is tenant-scoped. The service enforces prerequisites, permissions, separation,
idempotency, and optimistic concurrency; UI hiding is only an additional usability boundary.

## UI and reference review

The queue uses real counts, compact search/status filters, a dense desktop table, tablet wrapping,
mobile cards, and an accessible detail drawer. The drawer has Verification, Documents,
Appointments, and Decisions tabs with explicit progress, missing-document, loading, empty, error,
permission-denied, read-only, and conflict states. The existing protected `DocumentWorkspace` is
embedded rather than recreated.

Before implementation, paired `_full.png` and `_viewport.png` references were reviewed:

- `0010_campaigns_tab_all` for operational toolbar, filter, status, and table density;
- `0008_contacts_filter` for compact filters and layered workspace behavior;
- `0053_manage_team_add_team_member` for governed form hierarchy and action placement;
- `0004_contacts_add_contact` for modal/form rhythm and responsive grouping.

The result retains familiar relative hierarchy, density, status presentation, and drawer/form
workflow. Original Vi wording, design tokens, Lucide icon language, colors, component dimensions,
and responsive breakpoints intentionally differ. No reference code, asset, logo, proprietary text,
exact styling, or screenshot is copied or committed.

## New files and necessity

| New file | Necessity |
|---|---|
| `backend/alembic/versions/0033_kyc_operations.py` | Adds the verified document-reference, Task-link/idempotency, and structured-reason persistence constraints. |
| `backend/tests/test_kyc_operations.py` | Covers KYC prerequisites, checks, protected links, appointments, separation, decisions, concurrency/idempotency, audit/Timeline, tenant isolation, and handoff. |
| `frontend/src/features/kyc/types.ts` | Central generated-contract aliases and governed labels. |
| `frontend/src/features/kyc/api.ts` | Typed React Query boundaries for existing/extended KYC and Task authorities. |
| `frontend/src/features/kyc/KycOperationsWorkspace.tsx` | Real tenant queue, filters, factual states, responsive table/cards, and drawer orchestration. |
| `frontend/src/features/kyc/KycCasePanel.tsx` | Verification, protected checklist, appointment, separated decision, and immutable-history composition. |
| `frontend/src/features/kyc/index.ts` | Stable feature export boundary. |
| `frontend/src/features/kyc/kyc.test.tsx` | Focused real-data, state, permission, accessibility, responsive, and workflow tests. |
| `docs/adr/0016-governed-kyc-operations.md` | Permanent authority and security decision. |
| `docs/design/29-CORE-04-KYC-OPERATIONS.md` | Permanent reuse, workflow, UI-reference, contract, validation, and file-boundary record. |

All other changes extend existing files in place.

## Validation boundary

Twenty-four focused backend tests cover creation prerequisites, verification/checklist rules,
protected access, appointment lifecycle, reviewer/manager separation, approval/rejection,
tenant/RBAC isolation, concurrency/idempotency, immutable audit/Timeline evidence, and Reactivation
handoff. Thirty-three focused cross-feature frontend tests cover real projections, interactions,
loading/empty/error/read-only states, accessibility, responsive transformation, integration from
Reactivation and Customer 360, and absence of mock fallbacks. The canonical deployed profile
passes all 22 steps: 940/940 pytest, 646/646 Vitest, Ruff, strict mypy across 252 files, OpenAPI
drift, ESLint, frontend/browser TypeScript, production build, Bandit, dependency/source/image
scans, SBOMs, Compose/image contracts, MySQL migration `0033`, healthy Redis/Celery, and Playwright
1/1 in 8.635 seconds. Python compile passes separately. The standard-read canary records p95
12.551 ms across 30 samples against a 300 ms budget.

Authenticated live KYC visual review requires a host account with representative protected domain
data. The protected local route correctly redirects anonymous access to sign-in; the target data
and device/browser matrix therefore remain a host validation item.

## Known limits and next boundary

The queue returns at most 200 rows and does not yet expose server-saved views or virtualization.
Task reschedules are authoritative in Task history; the legacy `KycCase.appointment_at` compatibility
field is not rewritten on later Task lifecycle changes. Target-host WCAG/device review, high-volume
KYC performance, and production document/media commissioning remain host validation. CORE-05 is
the next milestone and exclusively owns SIM fulfilment.
