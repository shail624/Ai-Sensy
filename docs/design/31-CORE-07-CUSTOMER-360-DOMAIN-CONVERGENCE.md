# Design Document 31 — CORE-07 Customer 360 Domain Convergence

## Purpose and boundary

CORE-07 extends the existing Contact profile into one factual Customer 360 workspace. It composes
persisted identity, conversations, Reactivation CRM, reminders, notes, KYC/SIM/Activation facts,
documents, tasks, campaign participation, audit, and Customer Timeline evidence. It does not create
a new customer aggregate, persistence snapshot, workflow engine, migration, or endpoint family.

## Repository reuse map

| Existing capability | Existing file paths | Extension point | Genuine missing capability |
|---|---|---|---|
| Contact identity and attributes | `backend/app/models/contact.py`, Contact repository/service/API; `frontend/src/features/customer-profile/*` | Keep the public Contact id as the workspace join key and retain existing identity/attribute reads. | A factual, responsive composition of existing sections. |
| WhatsApp conversations and messages | Existing Conversation/Message models, Inbox repository/service/API, `frontend/src/features/inbox/*` | Add an optional exact public Contact filter to the existing Inbox list query; reuse the existing message query and bubbles. | Contact-scoped history without a second conversation API. |
| Reactivation status, labels, owner, notes, reminders, SLA | CORE-02/03/05 Vi models, repository, service, API, Task authority, `frontend/src/features/reactivation/*` | Add an exact Contact filter to the existing pipeline query and compose returned case/task/note evidence read-only. | Contact-specific case projection. |
| KYC, SIM, and Activation facts | `backend/app/models/vi_domain.py`, existing Vi services/APIs, generated contracts | Reuse existing case-detail list APIs after resolving the Contact's authoritative Reactivation case. | No new persistence or workflow. |
| Documents and protected media | Existing Document Center models/services/APIs and `DocumentsSection` | Retain protected reads and source-workflow deep links. | No new authority. |
| Tasks, appointments, assignment, and reminders | Existing Task model/repository/service/API and `TasksSection` | Reuse factual contact Tasks and source lifecycle actions. | No new authority. |
| Campaign participation | Existing Campaign recipient/query authority and `CampaignParticipationSection` | Reuse recipient evidence and Campaign deep links. | No new authority. |
| Audit and Customer Timeline | Existing `AuditLog`, `ContactEvent`, APIs, and `TimelineSection` | Present separate Timeline and Audit views from the same immutable evidence sources. | Richer evidence rows and source references. |
| RBAC, tenant isolation, and design system | Existing permissions, tenant filters, route guards, Card/Badge/Button/skeleton/error components | Apply section-level read/write visibility and accessible responsive tab composition. | Explicit denied/read-only states and keyboard tab behavior. |

No completed Contacts, Inbox, Campaigns, Documents, Customer 360, Tasks, Reactivation, KYC, SIM,
Activation, Audit, Timeline, RBAC, queue, or design-system authority is rebuilt.

## Data and contract design

`GET /conversations` accepts optional `contact`, resolves that public id through the tenant-scoped
Contact repository, and applies the Contact internal id inside the existing Conversation repository.
An unknown or foreign id returns an empty conversation page; malformed public ids keep the shared
400 validation behavior.

`GET /vi/reactivation-pipeline` accepts optional `contact_id`, resolves it through the same tenant
boundary, and filters the existing case query. The existing pipeline serializer remains the sole
authority for status, labels, assignment, reminders, notes, reservation, family-plan, conversion,
and SLA facts. Existing case APIs provide KYC, SIM order, and Activation records. Both extensions
are optional and backward compatible. OpenAPI is regenerated with no path increase.

## Workspace and interaction design

The existing Contact route now provides:

- a persisted identity header with source and last-contact facts;
- eight keyboard-operable tabs with Arrow, Home, and End behavior and labelled tab panels;
- a Vi operations view composed from the authoritative case, Task, note, KYC, SIM, and Activation
  contracts;
- exact contact-scoped WhatsApp threads with read-only message history and an Inbox deep link;
- existing task, document, campaign, timeline, and audit evidence with source deep links;
- honest loading skeletons, useful empty states, recoverable errors, permission-denied sections,
  and read-only mutation controls;
- two-column desktop density, tablet card reflow, horizontal tab affordance, and single-column
  mobile presentation with no page overflow.

Customer 360 does not mutate source facts. Deep links take authorized users to the source workflow,
where existing optimistic concurrency, approval, audit, and timeline rules continue to apply.

## Reference and originality review

The paired `_full.png` and `_viewport.png` captures reviewed from the ignored reference library are:

- `0001_live_chat_active` for conversation/context hierarchy and message density;
- `0008_contacts_filter` for compact contact actions and information hierarchy;
- `0010_campaigns_tab_all` for tab and table density;
- `0048_manage_user_attributes_tab_contact_attributes` for attribute grouping and form rhythm.

The implementation keeps a recognizable dense customer context, compact source actions, horizontal
tabs, structured evidence cards, and responsive transformations using original Vi Reactivation
components, wording, Lucide icons, design tokens, colors, spacing, and breakpoints. No proprietary
code, asset, branding, wording, exact color, typography, pixel layout, or screenshot is copied or
committed.

## Defects fixed and regression evidence

1. Contact conversation history was blocked by an unavailable placeholder because the existing
   Inbox list contract could not request one exact Contact. The existing query was extended and
   tenant/malformed-id regression tests were added.
2. Contact tag mutation controls remained visible to users without `contacts:write`. The existing
   tag section now renders an explicit read-only state, with a focused regression test.
3. The former Customer 360 surface could imply synthetic Vi facts from generic attributes and
   advertised an AI context placeholder. Both were replaced by persisted source evidence and honest
   empty states, with no synthetic metric or local-only record.
4. The deployed owner journey asserted the superseded KYC, SIM, and AI placeholder tabs. The release
   proof now requires the converged Vi operations, Conversations, Tasks, Documents, and Audit tabs
   and asserts the placeholder is absent.

No Critical or High defect remains reproducible in the milestone scope. The lower-severity CLI
bootstrap inconsistency that accepts a reserved email domain later rejected by login validation is
recorded in the gap analysis.

## Strictly necessary new files

| New file | Necessity |
|---|---|
| `frontend/src/features/customer-profile/customer360.test.tsx` | Focused regression coverage for the converged workspace, persisted Vi evidence, exact Contact conversation composition, RBAC/error states, read-only tags, and absence of placeholders. |
| `docs/adr/0018-customer-360-domain-convergence.md` | Permanently records source ownership, query-extension, and no-parallel-authority decisions. |
| `docs/design/31-CORE-07-CUSTOMER-360-DOMAIN-CONVERGENCE.md` | Records reuse, contracts, UI/reference review, accessibility, defects, and validation boundaries. |

Every runtime change extends an existing file in place.

## Validation boundary

Focused backend API tests cover exact Contact filtering, malformed identifiers, and tenant isolation.
Focused frontend tests cover factual composition, permission/error/read-only states, and no fake
content. Browser review covers desktop, tablet, and mobile layouts, zero horizontal overflow,
keyboard tab navigation, and console errors. Canonical repository validation supplies the final
pytest, migration, OpenAPI, generated-contract, static-analysis, Vitest, Playwright, build, Docker,
accessibility, and performance evidence recorded in `VALIDATION_RESULTS.md`.
