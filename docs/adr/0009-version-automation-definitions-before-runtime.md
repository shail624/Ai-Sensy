# ADR-0009 — Version automation definitions before enabling runtime

- **Status:** Accepted — 2026-07-30
- **Scope:** MD5 Phase 2A automation authoring, validation, publication, rollback and disablement
- **Runtime/API/schema change:** additive tables, permissions and routes; no task or send path

## Context

The existing Automation screen is deliberately a browser-only blueprint. Design Document 21 makes
the next roadmap boundary a real, versioned automation system with deterministic execution,
idempotency, retries/DLQ, run evidence, loop protection and human approval before any
customer-facing effect. Enabling a Run control before those authorities exist would create an
unrecoverable and unaudited execution path.

Automation authors still need a durable contract on which the runtime can safely depend. Mutable
JSON without immutable publication snapshots would make an in-flight or historical run impossible
to reproduce, audit or roll back.

## Decision

- Add tenant-scoped `automation_flows` for mutable drafts and
  `automation_flow_versions` for immutable published snapshots.
- Validate request structure with typed node configurations and validate graph semantics before
  publication: one trigger, unique node/edge identifiers, valid endpoints, no cycles, and every
  node reachable from the trigger.
- A published version is content-addressed and immutable. Editing a published flow changes only its
  draft; the active version remains unchanged until an authorized publish.
- Restoring a historical version copies its snapshot into the draft. It never activates or executes
  the restored definition without a separate publish.
- Split permissions into `automations:read`, `automations:write`, and `automations:publish` and audit
  create, update, publish, restore, disable and enable mutations.
- Do not register `automation.run`, create execution records, schedule triggers, call domain
  services, invoke webhooks, create approval proposals or send messages in this milestone.

## Consequences

- The visual builder becomes a real, recoverable authoring surface and the future runtime receives a
  stable immutable input contract.
- Drafts may be incomplete and remain saveable; publication is fail-closed until semantic validation
  passes.
- Disablement controls future runtime eligibility but has no runtime side effect in Phase 2A.
- Existing APIs, queues, Celery task registration, sends, provider adapters, permissions and
  business rules remain unchanged except for the additive automation surface.
- Phase 2B must add the run/attempt ledger, trigger ingestion, idempotency, retry/DLQ and loop
  controls before any flow can execute. A later approval milestone must be the only path from a
  customer-facing proposal to the existing `SendService`.
