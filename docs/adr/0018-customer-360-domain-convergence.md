# ADR-0018: Converge customer evidence in the existing Customer 360 workspace

- **Status:** Accepted
- **Date:** 2026-08-02
- **Milestone:** CORE-07
- **Decision owners:** Repository owner and Vi Reactivation engineering

## Context

Customer identity, WhatsApp conversations, Reactivation operations, reminders, documents, tasks,
campaign participation, audit, and timeline evidence already have authoritative models, services,
and APIs. The existing Customer 360 route exposed only part of that evidence and used an unavailable
conversation placeholder and attribute-derived Vi facts. Adding a second customer aggregate or a
Customer 360 persistence layer would duplicate completed authorities and risk tenant or permission
drift.

## Decision

The existing Contact remains the single customer identity. Customer 360 is a read-oriented,
permission-aware composition over existing sources; it owns no duplicate customer, conversation,
task, document, Reactivation, KYC, SIM, Activation, campaign, audit, or timeline record.

The existing conversation-list and Reactivation-pipeline contracts gain optional exact public
Contact filters. Each filter resolves through the existing tenant-scoped Contact repository before
querying the source authority. Unknown or foreign contacts disclose no cross-tenant records.
Customer 360 uses those filters and existing detail APIs to render persisted source facts and deep
links back to the workflow that owns each mutation.

The workspace is organized as accessible Overview, Vi operations, Conversations, Timeline, Tasks,
Documents, Campaigns, and Audit tabs. Permission-gated sections provide explicit denied or read-only
states. Mutations continue through their source workflows; Customer 360 does not introduce a new
write API, migration, synthetic metric, or local-only record.

## Consequences

- One Contact identifier joins factual evidence across modules without copying records.
- Tenant isolation and RBAC remain enforced at each existing source authority.
- KYC, SIM, and Activation facts are projected from the completed CORE-02/04 domain APIs; no heavy
  operational workspace is introduced.
- OpenAPI remains at 189 paths and migration head remains `0034_reactivation_crm`.
- The exact-contact query parameters extend existing endpoints and generated TypeScript contracts
  without creating a parallel API family.
- Future Customer 360 additions must compose an existing authority or establish a separately
  approved domain boundary first.

## Rejected alternatives

- Customer snapshot or denormalized Customer 360 tables: rejected because they duplicate facts and
  complicate concurrency and evidence ownership.
- A second conversation-history endpoint: rejected because the Inbox query already owns message
  access and only required an exact Contact filter.
- Attribute-derived KYC/SIM/Activation badges: rejected because attributes are not operational
  evidence.
- Customer 360 mutation endpoints: rejected because deep links preserve source-workflow approval,
  concurrency, and audit boundaries.
