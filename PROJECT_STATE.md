# Project State

> Current repository snapshot. GitHub is the implementation source of truth. `HEAD` is symbolic
> because a commit cannot embed its own final hash; resolve it after push with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `ui/taste-modernization` |
| M13-00 starting baseline | `7e503a3f2e1d35d54548d9d8fe95e82591e26be1` (`docs(governance): freeze approved Module 13 architecture`) |
| Current Git HEAD | `HEAD` (M13-00 documentation-only closeout; resolve after push) |
| Current milestone | `M13-00 — Architecture & Provider Lock — REPOSITORY VALIDATED` |
| Current phase | `Module 13 implementation contract frozen; implementation remains unstarted and gated` |
| Repository version | `1.0.0-rc1` |
| Migration head | `0035_notification_center` (35 linear revisions; unchanged) |
| OpenAPI | `3.1.0` · `193` paths · generated TypeScript authority unchanged |
| Backend evidence | Existing CORE-09 baseline: Ruff clean, strict mypy clean across 258 files, 948 pytest tests; backend unchanged and not re-run for documentation-only M13-00 |
| Frontend evidence | Existing UI-TASTE-03A baseline: ESLint PASS · TypeScript PASS · 34 Vitest files / 661 tests PASS · production build PASS; frontend unchanged and not re-run |
| Dependency evidence | Dependencies unchanged; existing production audit boundary remains two moderate React Router advisories and no high/critical production finding |
| M13-00 contract | ADR-0020 and Design Document 33 are accepted, frozen and repository-validated |
| Module 13 implementation | `0%` — no product source, API, migration, generated contract, route, runtime or deployment implementation exists |
| QR provider | Not selected; Required provider evaluation is an explicit external gate, not a fabricated decision |
| Next existing-roadmap implementation | `UI-TASTE-03B — Reactivation operational hierarchy`; previously approved and not started on the target branch |
| Next Module 13 milestone | `M13-01`; not authorized and blocked by recorded prerequisite, provider and separate owner-instruction gates |
| Host evidence | Not applicable to this documentation-only milestone; no Host Validated or Production Ready claim |
| Worktree expectation | ADR/design/governance Markdown only; no application, migration, API, dependency, generated-client, route or architecture implementation change |
| Last update | `2026-08-04T11:20:00+05:30` (Asia/Kolkata) |

## M13-00 delivered contract

- Accepted and froze ADR-0020 for the Enterprise Omnichannel Channel Manager.
- Added Design Document 33 as the complete implementation contract covering the provider
  capability matrix, QR provider evaluation, threat model, security, session lifecycle,
  identity resolution, API/database evolution, rollback, feature flags, rollout, disaster
  recovery, monitoring, performance, testing, acceptance, risks and dependencies.
- Confirmed that the existing capability-based `ChannelAdapter`, canonical message/event
  model, Contact, Conversation/Message, Inbox, Customer 360, media, Notification Center,
  Analytics, RBAC, tenant and Audit authorities are extended rather than duplicated.
- Resolved two documentation inconsistencies additively: Module 13 retains the single existing
  adapter seam, and ADR-0020 permits Instagram only as a future separately approved adapter
  possibility despite the older Doc 07 exclusion. No future-provider implementation is authorized.
- Classified all discovered gaps as Required, Recommended or Future Enhancement.
- Froze objective provider pass/fail criteria without inventing a provider selection.

## Implementation boundary

- No QR login, QR provider dependency, session runtime, Channel Manager, schema migration,
  API endpoint, backend service, frontend route, Inbox change or Customer 360 change was made.
- M13-00 reaches `Repository Validated` only. It cannot be Host Validated, Production Ready or
  Released because it intentionally contains no executable workflow.
- M13-01 does not start automatically. The existing prerequisite workflows must reach their
  recorded status, a QR provider must pass Required evaluation, and the owner must issue a
  separate implementation instruction.
- Any deviation from ADR-0020 or Design Document 33 requires explicit owner approval and an
  additive ADR before engineering continues.

## Existing UI modernization state

UI-TASTE-03A remains implemented and repository-validated with authenticated representative-
data host review pending. UI-TASTE-03B remains the next previously approved implementation
milestone on the existing roadmap and was not started or changed by M13-00.

## Maintenance rule

Continue from the latest approved Git HEAD. Preserve the frozen Module 13 contract, existing
architecture and one-milestone boundary. Do not begin M13-01 or any later Module 13 milestone
without a separate explicit owner instruction.
