# ADR-0014: Tenant-scoped Vi domain foundation

- **Status:** Accepted
- **Date:** 2026-08-02
- **Milestone:** CORE-02
- **Decision owners:** Repository owner and Vi Reactivation engineering

## Context

The approved final scope requires durable reactivation, eligibility, KYC, SIM fulfilment,
activation, and SLA authorities. The repository already owns contacts, configurable lead-pipeline
metadata, documents, tasks, RBAC, audit logs, Customer Timeline events, and a durable business-event
ledger. Replacing any of those authorities or treating the existing Reactivation UI blueprint as
operational data would violate repository continuity.

## Decision

Add one coherent tenant-scoped domain foundation with ten records:

- mutable, versioned aggregates: `ReactivationCase`, `KycCase`, `SimOrder`, `ActivationRecord`,
  and `SlaPolicy`;
- immutable evidence: `ReactivationStageEvent`, `EligibilityCheck`, `KycDecision`,
  `SimOrderEvent`, and `SlaEvent`.

The approved fifteen-stage reactivation lifecycle is a fixed Vi operational contract. It does not
replace the existing configurable `LeadPipeline`/`LeadStage` authority, which continues to serve
general CRM configuration. Customer documents remain in the governed document aggregate; CORE-02
only verifies their existence/status at lifecycle gates.

All commands are scoped by `organization_id`. APIs accept public UUIDs and repositories always
resolve them with the authenticated tenant. Mutable updates require `expected_row_version`.
Create/decision/event commands use UUID idempotency keys plus a canonical request hash; a replay
returns the existing result, while reuse with different content fails with `409`.

Stage/status transition matrices fail closed. Terminal states do not transition. Eligibility,
document, KYC, SIM-delivery/customer-confirmation, and activation prerequisites are checked before
the related reactivation transition. Database checks, uniqueness rules, foreign keys, and positive
SLA duration/order constraints provide a second enforcement layer.

Approval authority is explicit:

- KYC review uses `kyc:decide`; manager approval uses the separate `kyc:approve` command.
- SIM lifecycle transitions require `sim:manage`.
- Activation preparation uses `activation:write`; approval/completion use the separate
  `activation:approve` command and a required approval reference.
- Eligibility overrides require an approval reference and the governed reactivation-transition
  permission. CORE-08 will later generalize cross-module approval requests without rewriting these
  immutable domain decisions.

Every material command appends audit evidence and a Customer Timeline projection in the same
transaction. Automation facts reuse the existing `BusinessEvent` ledger and receipt projection;
no second event bus or automation authority is introduced.

Migration `0032_vi_domain_foundation` is additive from `0031_automation_trigger_receipts`. It adds
the ten tables, fifteen permissions, and seven governed business-event types. The OpenAPI contract
moves forward from 153 to 182 paths and the TypeScript contract is regenerated.

## Consequences

- CORE-03 through CORE-06 can consume real server-owned records without mock operational data.
- Immutable evidence grows append-only and must be retained according to later retention policy.
- List serialization currently resolves related public identifiers through the shared session;
  CORE-07 must enforce an explicit query budget when building cross-domain Customer 360 views.
- The generic SQLite `alembic check` remains noisy because of pre-existing repository-wide
  server-default/constraint reflection differences. The authoritative migration gate is the real
  upgrade/downgrade/re-upgrade test plus the deployed MySQL migration run, both of which pass.
- No Reactivation Kanban, KYC workspace, SIM fulfilment UI, or Activation Queue is delivered here.

## Rejected alternatives

- Reuse configurable lead stages as the Vi lifecycle authority: rejected because it permits tenant
  configuration to invalidate the approved fixed workflow.
- Store decisions on mutable case rows only: rejected because attribution and approval history
  would be overwritten.
- Add a second timeline, document store, approval engine, or event bus: rejected as duplicate
  authority.
- Build placeholder operational UI against synthetic records: rejected by the permanent
  no-placeholder product rule and the CORE-02 milestone boundary.
