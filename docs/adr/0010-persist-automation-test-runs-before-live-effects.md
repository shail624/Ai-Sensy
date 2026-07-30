# ADR-0010 — Persist automation test runs before enabling live effects

- **Status:** Accepted — 2026-07-30
- **Scope:** MD5 Phase 2B deterministic test runtime, run evidence, retry and recovery
- **Runtime/API/schema change:** additive tables, queue, task and routes; no live trigger or domain effect

## Context

Phase 2A provides immutable published definitions but deliberately cannot execute them. The roadmap
requires a run ledger, step attempts, correlation, idempotency, retry/DLQ and operator-readable
history before any automation can affect customers or business records. Enabling live triggers and
actions in the same change would make it difficult to prove the execution engine itself is
deterministic and recoverable.

The existing queue framework already owns task tracking, bounded smart retry and durable DLQ
parking. A second retry mechanism would split operational authority and violate Design Book 06.

## Decision

- Add tenant-scoped `automation_runs` and `automation_step_attempts`. Every run pins one immutable
  published version and every step transition is durably checkpointed.
- Introduce the already-reserved `automation.run` queue in the Jobs pool and one tracked Celery task.
  It uses the existing queue registry, retry classification, job metadata and DLQ machinery.
- Require a UUID `Idempotency-Key` for test-run creation and enforce it durably in MySQL. Reusing a
  key with the same request returns the original run; reusing it for different input fails closed.
- Execute the published DAG in stable topological order with a maximum of 100 nodes. Test mode
  evaluates deterministic conditions and records sanitized inputs/outputs, but simulates every
  action node and performs no external or domain side effect.
- A redelivered task resumes from successful step checkpoints. An interrupted running attempt is
  closed before a new numbered attempt begins; terminal histories are never rewritten.
- Expose permission-scoped run creation, list and detail APIs and enable the existing Run test
  control only when an immutable version exists and the draft is clean.
- Do not ingest live domain events, schedule runs, mutate contacts/tasks/assignments, invoke
  webhooks/providers/campaigns, create approval proposals, hand off conversations or send messages.

## Consequences

- Operators can test, trace and recover the execution substrate using real production queues
  without creating a hidden customer-impacting path.
- Task registration increases by one and the Jobs worker consumes one additional isolated queue.
- Run history is durable across Redis loss and worker restarts; Celery remains transport, not truth.
- Phase 2C must add live event/schedule receipts and internal action authorities. Customer-facing
  proposals remain blocked until the approval/handoff contract is implemented and can reach
  `SendService` only after explicit human approval.
