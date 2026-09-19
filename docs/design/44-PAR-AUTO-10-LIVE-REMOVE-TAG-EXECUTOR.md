# PAR-AUTO-10 — Live Remove Tag Executor

**Status:** Repository Implemented  
**Date:** 2026-08-21  
**Scope:** One internal `Remove tag` effect in the automatic inbound runtime

## Decision

The bounded live runtime now accepts `Trigger → Remove tag` and
`Trigger → Condition → Remove tag` alongside Human handoff, Create task, Apply tag and Assignment.
The action resolves the immutable published tag UUID inside the receipt organization and detaches
it from the inbound Contact through the existing CRM Tag service. It adds no second tag/contact
authority, API route, permission, queue, provider operation, customer message or migration.

Only an active same-tenant Contact and active same-tenant Tag can be used. Missing, deleted,
malformed, nil or foreign references fail closed before a CRM mutation. The existing builder tag
picker remains the authoring source and publication rejects its nil placeholder.

## Durable effect and replay

The canonical `contact_tags` association, Tag usage counter, Contact Timeline and tamper-evident
Audit log remain authoritative. A new automatic removal writes one `tag_removed` Timeline event and
one `contact.untagged` system Audit entry, decrements usage without crossing zero and commits the
association change atomically. Existing user-authored removal keeps user attribution and its
existing not-attached error contract.

The Contact and Tag rows are locked before the association decision. If the tag is already absent,
the live action succeeds with `already_absent` evidence and writes no Timeline, Audit or counter
change. If a worker stops after the CRM transaction but before completing its Automation attempt,
the stale receipt can run again and converge on that same no-op without duplicate evidence.

## Conditional behavior and operator contract

The privacy-safe condition allowlist is unchanged. A match continues to Remove tag. A non-match
records the step as `skipped` with `condition_not_matched` and leaves the existing association
untouched. Successful attempt evidence is limited to public Contact/Tag identity, tag name and the
`removed|already_absent` outcome.

The Automation builder exposes a distinct live `Remove tag` step using the existing CRM tag picker
and explains its replay-safe no-op behavior. Safe test mode remains deterministic and
side-effect-free.

## Explicit boundary

Multiple effects, general branching, waits/delays, notification/campaign/webhook and
customer-message executors, other live event consumers, retry/DLQ operator controls and
reconciliation UI remain future PAR-AUTO scope. This milestone does not claim that the general
AiSensy chatbot/automation engine is complete.

## Validation

- Live runtime including direct, conditional and crash-replay Remove tag paths: **13/13 passed**.
- Live runtime plus existing Tag API/contact/bulk regression: **45/45 passed**.
- Full frontend: **40 files / 821 tests**; focused Automation **11/11**.
- Static profile: **6/6 passed**; strict mypy covers **305 source files**.
- OpenAPI/generated TypeScript: **211 paths**, drift-free.
- Migration head remains `0045` (**46 revisions**); no migration or API path was added.
- Production build: PASS; AutomationPage **39.68 kB / 10.12 kB gzip**.
- Canonical backend: **1476 passed / 6 MySQL skips / 1 known Redis-only failure**.
- Applicable backend: **1476 passed / 6 MySQL skips / 1 Redis-only deselection**.
