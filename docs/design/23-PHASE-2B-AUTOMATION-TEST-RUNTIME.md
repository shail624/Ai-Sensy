# MD5 Phase 2B — Deterministic Automation Test Runtime

**Status:** RELEASE READY — verified 2026-07-30
**Roadmap item:** PAR-AUTO-02, second reversible slice
**Scope:** Immutable-version test runs, run/attempt ledger, durable idempotency, queue execution,
checkpoint/resume, retry/DLQ integration, run history API and test-mode UI.
**Explicitly out:** live events, schedules, delays/waits, CRM/task/tag/assignment mutations,
outbound webhooks, campaign dispatch, approval proposals, human handoff, sends, AI, Forms and commerce.

## Objective

Turn the disabled test control into a real, recoverable execution proof without creating a live
automation path. The runtime must demonstrate deterministic version pinning, step evidence,
at-least-once safety and operational visibility before later milestones may attach business effects.

## Existing authorities reused

| Concern | Authority |
|---|---|
| Definition | Phase 2A immutable `automation_flow_versions` |
| Transport | Existing Celery application and `TrackedTask` |
| Retry/DLQ | Queue registry, smart retry classifier and `dead_letter` store |
| Job visibility | Existing `job_metadata` lifecycle and Operations queue views |
| Identity/tenant | Authenticated user and organization-scoped repositories |
| Permissions | `automations:read` and `automations:write` |
| Audit | Existing immutable `audit_logs` |

## Data contract

### `automation_runs`

One durable execution envelope containing public UUID, organization, flow, immutable version,
`test` mode, status, UUID idempotency key, request hash, correlation/task id, bounded trigger input,
creator, timestamps, terminal error and counters. Organization plus idempotency key is unique.

### `automation_step_attempts`

One numbered attempt per run/node containing public UUID, node id/kind, status, sanitized input and
output, error code/detail and timestamps. `(run_id, node_id, attempt_no)` is unique. A successful
attempt is the durable checkpoint that makes redelivery a no-op for that step.

## Execution contract

1. Test creation requires a valid UUID `Idempotency-Key`, an existing immutable active version and
   a clean draft. Disabled definitions may be tested because test mode cannot create effects.
2. The API commits the run and matching `job_metadata` before enqueueing `automation.run` with the
   correlation id as Celery task id.
3. The worker validates the pinned graph and derives a stable topological order using node id as the
   tie-breaker. Cycles, missing nodes or more than 100 nodes fail closed.
4. Trigger nodes record the manual-test envelope. Conditions evaluate bounded dotted input fields
   using the published typed operator. All other nodes record an explicit `simulated` result.
5. Each attempt is committed independently. Redelivery skips successful nodes, closes an interrupted
   attempt and resumes at the first incomplete node.
6. Unexpected failures use the existing smart retry policy. Exhaustion marks the run failed and the
   tracked task parks through the existing DLQ authority.
7. A run becomes `succeeded` only after every published node has a successful checkpoint.

## API contract

| Method | Path | Permission | Purpose |
|---|---|---|---|
| POST | `/automations/{automation_id}/test-runs` | `automations:write` | Create/replay-safe test run |
| GET | `/automations/{automation_id}/runs` | `automations:read` | List recent runs for a flow |
| GET | `/automation-runs/{run_id}` | `automations:read` | Read run and ordered attempts |

Run creation returns `202` for a new queued run and `200` for an idempotent replay. Foreign
organization identifiers are indistinguishable from missing records.

## UI contract

- Run test is enabled only for writers when a published version exists, the draft is saved and no
  run request is pending.
- The builder shows recent run status, pinned version, creator/time and a compact step timeline.
- Test mode is labelled clearly: action nodes were simulated and no customer or business record was
  changed.
- Run errors remain visible and link to durable attempt evidence rather than disappearing as a toast.

## Invariants

1. A run always uses the immutable version captured at creation, never the mutable draft.
2. An idempotency key cannot create two runs or be reused for different input.
3. A successful node is never executed twice for the same run.
4. Test mode cannot import or call domain services, providers, webhooks, campaigns or `SendService`.
5. Retry and DLQ remain owned by the existing queue framework.
6. Run and attempt lookups are tenant-scoped.
7. No task payload contains the trigger input; Celery receives only the internal run primary key.

## Validation contract

- Backend: version pinning, idempotent replay/conflict, deterministic order, condition evaluation,
  checkpoint resume, terminal failure, permission denial, tenant isolation, audit and OpenAPI.
- Queue: registry/pool routing, task registration, unchanged retry/DLQ behavior and production worker
  consumption.
- Frontend: gated run control, run submission, polling/history and safe-mode explanation.
- Completion requires applicable static/pre-merge/release/deployed gates with a real browser test run.

## Release evidence

- Migration `0030_automation_test_runtime` applied in the isolated production stack.
- OpenAPI 3.1.0 exports 152 paths; the generated TypeScript contract has no drift.
- 928 backend tests, Ruff and strict mypy across 242 source files passed.
- 627 frontend tests, ESLint, TypeScript and the production build passed.
- Production backend/frontend images rebuilt; 24 backend tasks and the `automation.run` Jobs-pool
  route passed image and worker-startup contracts.
- The ten-service deployed gate passed API/queue/worker health, a real safe test run through Celery,
  readiness degradation, observability correlation/redaction, and a 18.423 ms p95 read canary.
- Source and image HIGH/CRITICAL vulnerability scans passed and CycloneDX SBOMs were generated.
