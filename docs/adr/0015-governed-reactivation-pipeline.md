# ADR-0015: Connect the Reactivation workspace to the Vi domain authority

- **Status:** Accepted
- **Date:** 2026-08-02
- **Milestone:** CORE-03
- **Decision owners:** Repository owner and Vi Reactivation engineering

## Context

CORE-02 established the tenant-scoped `ReactivationCase`, immutable stage and eligibility evidence,
SLA records, permission boundaries, optimistic concurrency, audit, and Customer Timeline authority.
The existing Reactivation page still rendered a local blueprint rather than those records. CORE-03
must connect that workspace without rebuilding Contacts, Customer 360, Documents, Tasks, Audit,
Timeline, SLA, RBAC, or the general CRM pipeline.

The approved AiSensy captures are a local-only visual and workflow benchmark. The paired Contacts
filter, Campaigns table, Add Contact modal, and Live Chat screenshots were reviewed for density,
filter placement, modal/drawer behavior, hierarchy, responsive transformation, and empty states.
No reference code, asset, branding, wording, icon, exact color, typography, or pixel value is used.

## Decision

The existing `/reactivation/pipeline` route and `ReactivationPipelineBoard` remain the single UI
entry point. They now query a server-composed, tenant-scoped projection built by the existing
`ViDomainRepository` and `ViDomainService`. The projection joins the existing Contact and User
authorities and batches the latest eligibility, stage, SLA, task, document, reservation, family,
and conversion facts. Counts and cards never fall back to browser fixtures or local workflow state.

All movements use the existing CORE-02 transition command. The API publishes the server-computed
`available_transitions`; drag/drop, keyboard movement, and drawer actions only request one of those
targets with the current `row_version` and a fresh idempotency key. The service remains authoritative
for lifecycle prerequisites, tenant scope, RBAC, immutable stage history, audit, Customer Timeline,
and optimistic-concurrency conflicts.

Two verified contract gaps are filled additively:

- `GET /api/v1/reactivation-pipeline` supplies factual counts and a bounded, filterable card
  projection without browser-side fan-out.
- `GET/POST /api/v1/reactivation-cases/{case_id}/notes` stores internal case notes as existing
  immutable contact events and projects the write through existing audit and Customer Timeline
  authorities.

Assignments and case numbers use the existing CORE-02 update command. Tasks/reminders reuse
`TasksSectionForProfile` and its persisted Task service. Documents reuse `DocumentWorkspace` and
the governed document aggregate. Customer 360 remains the customer-context destination. The
shared `Modal` gains a drawer presentation without adding a parallel overlay system.

No migration is required: the verified projection and note gaps fit existing records and immutable
event storage. OpenAPI moves forward from 182 to 184 paths and generated TypeScript contracts are
regenerated.

## Consequences

- Refresh, assignment, transition, eligibility, notes, task, document, and SLA state remain
  server-owned and tenant-scoped.
- The UI supplies Kanban and responsive list presentations of the same projection; mobile uses the
  existing governed shell and bottom navigation.
- Loading, empty, error, permission-denied, stale-version, and rejected-transition outcomes remain
  truthful rather than being replaced with sample cards.
- The projection is intentionally capped at 200 visible cards. Counts remain factual beyond that
  window; pagination/virtualization is a later scale refinement.
- CORE-04 remains responsible for the complete protected KYC operations workspace.

## Rejected alternatives

- Reuse or extend the configurable lead-pipeline authority: rejected because CORE-02 owns the fixed
  Vi lifecycle and its prerequisites.
- Persist stage changes in React state: rejected because refresh, concurrency, audit, and tenant
  guarantees would be lost.
- Create Reactivation-specific task, document, note, timeline, or modal systems: rejected as
  duplicate authorities/components.
- Seed mock cards for visual parity: rejected by the no-placeholder product rule.
- Add columns for reservation/family facts: rejected because existing typed contact attributes are
  the approved persisted authority for those customer facts.
