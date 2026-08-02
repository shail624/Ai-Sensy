# ADR-0016: Deliver KYC operations through existing domain authorities

- **Status:** Accepted
- **Date:** 2026-08-02
- **Milestone:** CORE-04
- **Decision owners:** Repository owner and Vi Reactivation engineering

## Context

CORE-02 established tenant-scoped KYC cases, verification facts, immutable reviewer and manager
decisions, permissions, audit, Customer Timeline, idempotency, and optimistic concurrency. CORE-03
connected the Reactivation workspace to that authority. The remaining CORE-04 gaps are an
operational queue, protected document checklist links, Task-backed appointments, structured
rejection reasons, enforced requester/reviewer/manager separation, an approved Reactivation
handoff, and Customer 360 projection.

The repository already owns Contacts, protected documents, Tasks, Customer 360, Audit, Timeline,
RBAC, SLA, shared drawers, forms, status badges, skeletons, and error/empty states. CORE-04 must
extend those implementations; it must not introduce a second document store, appointment table,
approval engine, timeline, or KYC lifecycle.

## Decision

The existing `KycCase` aggregate and `ViDomainService` remain authoritative. A tenant-scoped KYC
operations projection joins the existing Reactivation case, Contact, User, KYC decision, Document,
Task, and SLA records. The dedicated UI consumes only this projection and the existing typed
commands; it has no sample records or local lifecycle state.

One additive migration, `0033_kyc_operations`, fills three verified persistence/constraint gaps:

- `kyc_document_references` links the Aadhaar and PAN checklist purposes to existing protected
  `ContactDocument` records. It stores document references only, never Aadhaar or PAN numbers.
- Tasks gain an optional, constrained `kyc_case` reference and UUID idempotency fields so KYC
  appointments reuse the existing Task lifecycle, immutable Task events, audit, and Timeline.
- KYC decisions gain a constrained structured reason code while immutable free-text explanation
  remains available.

KYC creation requires an eligible Reactivation case at the approved document-ready boundary and
records the requester. Reviewer decisions are forbidden for the requester. Manager decisions
require an approved reviewer decision and a manager distinct from both requester and reviewer.
Approval additionally requires all three verification facts and verified Aadhaar/PAN document
references. Only manager approval advances Reactivation through `kyc_pending` to `verification`,
using the existing transition authority and immutable stage history.

Appointments are created idempotently through `TaskService`; reschedule, completion, and
cancellation continue through existing Task commands. Protected document access continues through
Document Center permissions and signed-media policy. Material KYC changes append existing audit
and Customer Timeline evidence atomically.

The existing Reactivation case drawer gains a KYC tab and create/open boundary. Customer 360 uses
the real KYC projection. The `/reactivation/kyc` route becomes a responsive queue and case-detail
workspace composed from the repository design system.

## Consequences

- Refresh preserves KYC, checklist, appointment, decision, SLA, and handoff state because the
  server is the only operational authority.
- Sensitive identity numbers are outside the KYC schema, API, UI, audit payload, and migration.
- Optimistic concurrency guards aggregate mutations; idempotency protects case creation,
  appointment creation, and decisions.
- KYC-specific appointment facts remain linked Tasks, so reporting and customer history keep one
  task authority.
- The current KYC projection is intentionally bounded to 200 rows; larger-scale pagination and
  saved views remain later roadmap work.
- CORE-05 remains solely responsible for SIM fulfilment.

## Rejected alternatives

- Add Aadhaar/PAN columns to KYC: rejected because plaintext identity numbers are prohibited.
- Add KYC-owned uploads or media URLs: rejected because Document Center owns protected media.
- Add a KYC appointment table: rejected because the Task aggregate already owns scheduling and
  immutable lifecycle evidence.
- Implement manager approval only in the UI: rejected because separation of duties must be
  enforced by the server.
- Move the Reactivation stage directly from React: rejected because transition prerequisites,
  concurrency, audit, and immutable history belong to the CORE-02 service.
- Render illustrative queue records: rejected by the real-data and no-placeholder requirements.
