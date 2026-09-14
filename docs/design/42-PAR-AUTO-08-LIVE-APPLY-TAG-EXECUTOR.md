# PAR-AUTO-08 — Live Apply Tag Executor

**Status:** Repository Implemented  
**Date:** 2026-08-21  
**Scope:** One internal `Apply tag` effect in the automatic inbound runtime

## Decision

The bounded live runtime now accepts `Trigger → Apply tag` and
`Trigger → Condition → Apply tag` alongside Human handoff and Create task. The action resolves the
immutable published tag UUID inside the receipt organization and attaches it to the inbound Contact
through the existing CRM Tag service. It does not add another tag/contact authority, API route,
permission, queue, provider operation, customer message, or migration.

Only an active same-tenant Contact and active same-tenant Tag can be used. Missing, deleted,
malformed, nil, or foreign references fail closed before a CRM mutation. The existing builder tag
picker remains the authoring source and publication still rejects its nil placeholder.

## Durable effect and concurrency

The canonical `contact_tags` association, Tag usage counter, Contact Timeline and tamper-evident
Audit log remain authoritative. Automated attachment records `tagged_by = null`, one
`tag_added` Timeline event, and one `contact.tagged` system Audit entry. Existing user-authored tag
operations retain their user attribution.

Tag attachment now locks the Contact and referenced Tag rows. Multi-tag API writes acquire Tag
locks in stable identifier order. Concurrent or replayed attachment of the same tag therefore
converges on one association, one usage-count increment, one Timeline event and one Audit entry. An
already-present tag is a successful no-op with `already_present` evidence, not an error.

If a worker stops after the CRM transaction but before completing its Automation attempt, the
stale receipt can run again. The association check reports `already_present`; no second domain
effect is written, and the recovered attempt/run finishes successfully.

## Conditional behavior and evidence

The PAR-AUTO-06 privacy-safe condition allowlist is unchanged. A matching decision continues to
Apply tag. A non-match records the Tag step as `skipped` with `condition_not_matched` and writes no
association, counter change, Timeline event, or Tag Audit entry. Successful attempt evidence is
limited to public Contact/Tag identity, tag name and `applied|already_present` outcome; message
content, provider identity and customer credentials remain absent.

## Operator contract

The existing Automation builder labels Apply tag as a live contract, uses the existing CRM tag
picker, explains replay/no-duplicate behavior, and presents the exact Trigger → optional Condition
→ Human handoff/Create task/Apply tag boundary. Safe test mode remains deterministic and
side-effect-free.

## Explicit boundary

Remove tag, multiple effects, general branching, waits/delays, assignment/notification/campaign/
webhook and customer-message executors, other live event consumers, retry/DLQ operator controls,
and reconciliation UI remain future PAR-AUTO scope. This milestone does not claim that the general
AiSensy chatbot/automation engine is complete.

## Validation

- Live runtime including direct, conditional and crash-replay Tag paths: **9/9 passed**.
- Live runtime plus existing Tag API and bulk-tag regression: **32/32 passed**.
- Full frontend: **40 files / 819 tests**; focused Automation **9/9**; ESLint and TypeScript pass.
- Static profile: **6/6 passed**; strict mypy covers **305 source files**.
- OpenAPI/generated TypeScript: **211 paths**, drift-free.
- Migration head remains `0045` (**46 revisions**); no migration or API path was added.
- Production build: PASS; AutomationPage **37.93 kB / 9.84 kB gzip**.
- Canonical backend: **1472 passed / 6 MySQL skips / 1 known Redis-only failure**.
- Applicable backend: **1472 passed / 6 MySQL skips / 1 known Redis-only deselection**.
