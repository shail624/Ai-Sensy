# PAR-AUTO-04 — Governed Automation Human Handoff

**Status:** Repository implemented — 2026-08-21  
**Scope:** one published automation action that requests an existing conversation in Live Chat.  
**Explicitly out:** general live graph execution, automatic trigger consumption, conditions, waits,
delays, tasks/tags/assignment/notification effects, customer sends, AI agents and Forms.

## Objective

Close the first real bot/automation-to-human seam without weakening the existing separation between
the side-effect-free automation test runtime and production domain mutations. A governed caller can
execute a `Human handoff` node from a clean active immutable automation version. That action places
the referenced same-tenant conversation into Live Chat `Requested`; the existing intervention
lifecycle remains the only authority for an agent to claim and resolve it.

## Existing authorities reused

| Concern | Existing authority |
|---|---|
| Definition and publication | `AutomationFlow` and immutable `AutomationFlowVersion` |
| Test safety | `AutomationRuntimeService` remains side-effect-free |
| Live Chat request | `Conversation.status = pending` |
| Agent ownership | existing `assigned_user_id`, Intervene and owner-only Resolve |
| Tenant and permission | authenticated organization plus `automations:publish` |
| Replay evidence | deterministic UUID in the append-only Business Event ledger |
| Operator evidence | shared tamper-evident Audit ledger |

No migration, new permission code, queue, provider action, customer message or second inbox state
machine is introduced.

## Typed authoring contract

`AutomationNode` gains exactly one additive kind:

```json
{
  "id": "handoff-1",
  "kind": "handoff",
  "label": "Talk to a person",
  "config": { "reason": "Customer requested a human agent" }
}
```

`reason` is trimmed by the typed contract and bounded to 1–160 characters. The node participates in
the existing reachability, single-trigger and cycle checks. Safe test runs return the existing
simulated result and never apply the Live Chat mutation.

## Execution contract

| Method | Path | Permission | Idempotency |
|---|---|---|---|
| POST | `/automations/{automation_id}/handoffs` | `automations:publish` | required UUID `Idempotency-Key` |

The body carries only `conversation_id` and `node_id`. The reason comes from the pinned immutable
version, not from the caller. The service requires that the selected node exists in the active
version. A new execution additionally requires the automation to be published, enabled and free of
unpublished drift. A replay of an already-recorded action remains readable after later draft edits
or disablement and never executes again.

The deterministic Business Event identity binds organization, automation, active version, handoff
node, conversation and caller idempotency key. The first response is `201`; replay is `200` with the
same event identity and `replayed: true`.

## Conversation transition

| Current conversation | Result |
|---|---|
| Unassigned `open`, `resolved` or `snoozed` | `pending`, unassigned, outcome `requested` |
| Unassigned `pending` | unchanged, outcome `already_requested` |
| Assigned active `open` or `pending` | unchanged, outcome `already_intervened` |
| Historical assignee on `resolved`/`snoozed` | assignee cleared and moved to `pending` |

The conversation row is locked before the decision. Successful mutation advances `row_version` and
uses the existing assignment/status Audit actions. Every first action also appends
`conversation.handoff_requested` Business Event evidence and `automation.handoff_requested` Audit
evidence in the same transaction.

## Invariants

1. Another tenant's automation or conversation resolves as not found.
2. An unpublished, disabled or dirty automation cannot create a new handoff.
3. A node outside the active immutable version cannot execute.
4. Duplicate execution cannot duplicate the Business Event, Audit action or conversation mutation.
5. Replaying an old request after an agent intervenes never requeues or unassigns the chat.
6. A new request while an agent owns the chat records `already_intervened` without stealing it.
7. The payload contains no customer message, phone, name, credential or provider data.
8. Safe test mode continues to simulate every action and never changes a business record.

## Validation contract

- Typed node create/publish and generated OpenAPI/TypeScript.
- Publisher permission and same-tenant conversation lookup.
- First request, sequential replay and replay after later draft drift.
- Agent intervention followed by old replay and a new request.
- Resolved/historical-owner requeue with ownership clearing.
- Invalid node and dirty publication fail closed.
- Existing automation authoring/runtime/receipt and Inbox lifecycle regressions.
- Complete backend/frontend, lint, strict types, OpenAPI drift and production build.

## Remaining PAR-AUTO boundary

This endpoint is a real live action contract for a governed caller; it is not a claim that the
current trigger-receipt projector automatically executes published graphs. General production flow
runs, durable effect checkpoints, automatic receipt consumption, retry/DLQ operations, waits and
all other action executors remain future PAR-AUTO milestones.
