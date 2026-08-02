# Design Document 27 — CORE-02 Vi Domain Foundation

## Purpose and boundary

CORE-02 establishes the real server-owned Vi operational records required by the approved product
scope. It is deliberately a backend and generated-contract milestone. Existing Reactivation,
Customer 360, KYC, SIM, and Activation screens remain honest foundations until their later
milestones connect them to these APIs.

This design extends—not replaces—the existing contact, document, task, RBAC, audit, Customer
Timeline, job, and business-event infrastructure.

## Domain ownership

| Authority | Mutability | Ownership and invariants |
|---|---|---|
| `ReactivationCase` | Versioned aggregate | One case per tenant/contact; fixed fifteen-stage Vi lifecycle; tenant owner; terminal close reason. |
| `ReactivationStageEvent` | Immutable | Every initial/stage transition; attributed actor, reason, idempotency and request hash. |
| `EligibilityCheck` | Immutable | Rules/manual/override result; overrides require approval reference; latest result gates stage movement. |
| `KycCase` | Versioned aggregate | Holder, Delhi-presence and active-Delhi-number checks; appointment and assigned owner. |
| `KycDecision` | Immutable | Review and manager-approval decisions are distinct append-only records. |
| `SimOrder` | Versioned aggregate | Delhi NCR address/owner/serial/dispatch/delivery/failure/customer confirmation. |
| `SimOrderEvent` | Immutable | Every initial and fulfilment transition with attribution and reason. |
| `ActivationRecord` | Versioned aggregate | SIM linkage, preparation, approval reference, approver, completion/rejection evidence. |
| `SlaPolicy` | Versioned aggregate | Tenant/domain/trigger unique scope; positive target; escalation cannot precede target. |
| `SlaEvent` | Immutable | Started/breached/resolved evidence for a validated tenant-owned domain entity and contact. |

## Lifecycle rules

The reactivation matrix follows the approved order from New Lead through Completed, Not Eligible,
or Not Interested. Controlled correction exists only from Verification back to Documents Pending.
Eligibility results gate Eligible/Not Eligible. Documents Received requires a governed document;
Confirmed requires manager-approved KYC; SIM Order requires a real order; Activation Pending
requires delivered and customer-confirmed SIM fulfilment plus an activation record; Completed
requires a completed activation record.

KYC preparation permits pending, documents-pending, and under-review transitions. Approval requires
all three Vi verification flags and at least one verified governed document. A review approval does
not finalize the case; a separately authorized manager decision does.

SIM transitions are requested → approved → assigned → dispatched → delivered, with controlled
failed retry and cancellation branches. Dispatch requires an owner and unique serial. Activation
transitions are pending → verification → ready → approved → completed, with rejection branches.
Approval/completion are accepted only through the approval permission boundary.

## Transaction and concurrency contract

Each service command owns one database transaction. It writes the aggregate/evidence together with
its audit and Customer Timeline projections, then commits once. Business-event facts are appended
before commit and continue through the existing automation receipt projection.

Mutable commands require the current `row_version`, increment it exactly once, and return `409
version_conflict` on stale input. Idempotent commands carry a caller UUID and canonical SHA-256
request hash. Same-key/same-command retries return the stored outcome; different content fails with
`409 idempotency_conflict`.

## Tenant and permission contract

Every repository lookup combines the authenticated `organization_id` with the public UUID. A
cross-tenant identifier is indistinguishable from a missing record. Internal integer identifiers are
never accepted by or exposed from the public API.

Fifteen additive permissions cover read/write/transition or approval boundaries for Reactivation,
KYC, SIM, Activation, and SLA. Owner/admin retain the entire catalog. Manager receives the full Vi
set. Agent receives operational preparation permissions but no manager KYC/activation approval,
SIM management, or SLA management. Analyst receives read-only Vi permissions.

## API and contract surface

The foundation adds 29 OpenAPI paths across:

- contact/case Reactivation collection, detail, update, transition, stage-event, and eligibility
  resources;
- contact/case KYC collection, detail, preparation, review-decision, and manager-approval resources;
- case/SIM collection, detail, preparation, transition, and immutable event resources;
- case/Activation collection, detail, preparation, transition, and approval resources;
- SLA policy and immutable SLA event resources.

OpenAPI 3.1.0 now contains 182 paths. `frontend/openapi.json` and
`frontend/src/lib/api/schema.d.ts` are generated from the live FastAPI application. No handwritten
frontend operational client or screen is introduced in CORE-02.

## Migration and event taxonomy

`0032_vi_domain_foundation` advances the single migration line from `0031`. It adds ten tables,
their tenant/lifecycle/uniqueness indexes and constraints, fifteen permission rows, and seven
business-event taxonomy entries. It does not alter or downgrade an existing table or event.

Customer Timeline projections use the existing partitioned `contact_events` table with new event
and reference constants. Automation facts use the existing partitioned `business_events` ledger.
The implementation adds no competing generic history store.

## Validation

- focused service tests cover idempotency, stale versions, transition gates, approval separation,
  immutable evidence, audit, timeline, SIM/activation/SLA lifecycles;
- API tests cover RBAC denial, read permissions, tenant isolation, and generated contract paths;
- migration tests cover upgrade, full table/permission integrity, downgrade, and repeat upgrade;
- the canonical pre-merge and release profiles pass all static, application, security, contract,
  Compose, image, and vulnerability gates;
- the isolated MySQL/Redis/Celery/nginx deployment applies migration `0032`, passes Playwright, and
  records p95 16.5 ms across 30 authenticated reads.

## Explicit deferrals

CORE-03 owns the real Reactivation Kanban and workflow UI. CORE-04 owns the protected KYC workspace.
CORE-05 owns SIM fulfilment UI. CORE-06 owns Activation Queue UI. CORE-07 owns query-budgeted
Customer 360 convergence. CORE-08 owns the generalized approval request/decision engine.
