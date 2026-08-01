# MD5 Phase 2C — Durable Automation Trigger Receipts

**Status:** RELEASE READY — 2026-07-30
**Roadmap item:** PAR-AUTO-03, third reversible slice
**Scope:** `business_events`, first canonical publisher, immutable-version flow matching, durable
trigger receipts, read API and builder evidence.
**Explicitly out:** live runs, schedules, delays/waits, tasks/tags/assignment/notification effects,
webhooks, campaigns, approvals, handoff, sends, AI, Forms and commerce.

## Objective

Prove that a real business fact is captured once and matched to the correct active immutable flow
version before any automation can change a business record or contact a customer.

## Existing authorities reused

| Concern | Authority |
|---|---|
| Event envelope | Design Book 03 §21 `business_events` |
| Fan-out rules | Design Book 06 §47 durable-first Domain Event Bus |
| Definition | Phase 2A immutable active flow version |
| Runtime boundary | Phase 2B run/attempt ledger remains test-only |
| Contact creation | Existing Contact and Conversation services/transactions |
| Identity/tenant | Existing organization-scoped repositories |
| Permission | `automations:read` |

## Data contract

### `business_event_types`

Governed versioned taxonomy. This slice seeds `contact.created` version 1 in the `lead` category
with `contact` subject and an internal schema reference. New types are additive.

### `business_events`

Append-only partitioned ledger using the frozen envelope: stable UUID/dedup identity, organization,
type/version, occurred and recorded times, actor/subject/channel references, correlation/trace,
source and bounded JSON payload. Partitioned rows have no database foreign keys.

`contact.created` payload contains public contact identity, source and opt-in state only; phone,
name, message content and credentials are never copied into the automation envelope.

### `automation_trigger_receipts`

Tenant-scoped projection containing public UUID, flow, immutable version, business-event UUID/type,
`received` status and receipt time. `(flow_id, version_id, event_uuid)` is unique. The source event
is referenced by UUID rather than a foreign key because the ledger is partitioned.

## Matching contract

1. The contact publisher appends a stable `contact.created` event in the same transaction as the
   contact, contact timeline and audit record.
2. The matcher selects only same-tenant flows with status `published`, an active version and no
   unpublished content drift.
3. The immutable active graph must contain exactly one root trigger whose event equals the incoming
   type. Validation remains owned by Phase 2A.
4. One receipt is inserted per matched version. Re-recording the same logical event is a no-op.
5. Disabled flows and unsupported trigger types produce no receipt.
6. No task is dispatched and no graph node is executed in this milestone.

## API and UI contract

| Method | Path | Permission | Purpose |
|---|---|---|---|
| GET | `/automations/{automation_id}/trigger-receipts` | `automations:read` | Recent real matches |

The builder labels receipts as trigger evidence, not runs. It shows event type, pinned version,
source and timestamps, and explicitly says that no action has executed.

## Invariants

1. A business event is immutable and contains no customer message body or credential.
2. A receipt pins the version that was active when the event was recorded.
3. Cross-tenant events, flows and receipts can never match or be read.
4. Dirty drafts, drafts and disabled flows never receive live receipts.
5. Receipt replay never duplicates a row.
6. Contact creation retains its current validation, permission, audit and transaction behavior.
7. No live run or business/customer effect is created.

## Validation contract

- API/import/system contact creation records one event atomically.
- Matching, disabled/dirty exclusion, replay, tenant isolation and permission denial are covered.
- Migrations remain linear/reversible and MySQL partition rules are validated.
- OpenAPI/generated TypeScript, builder receipt history, static/pre-merge/release/deployed gates pass.

## Release evidence

- 932 backend tests and 628 frontend tests pass.
- Ruff, strict mypy across 247 files, ESLint, TypeScript, OpenAPI drift and production build pass.
- Migration `0031` is linear/reversible; the isolated MySQL stack applies it successfully.
- Rebuilt backend/frontend images pass contracts, vulnerability scans and SBOM generation; the
  backend retains 24 registered Celery tasks and exposes 153 OpenAPI paths.
- All API, worker and queue health checks pass. The deployed browser journey publishes a flow,
  imports a second contact through Celery, observes one `contact.created` receipt, and verifies the
  UI's no-action-executed boundary.
- Playwright reports 1 passed/0 failed and the 30-sample read canary records p95 19.002 ms against
  the 300 ms threshold.
