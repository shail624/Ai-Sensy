# Design Document 37 — CORE-11C Inactivity Auto-Resolve

**Status:** Repository implementation record

**Milestone:** CORE-11C (third bounded delivery inside CORE-11)

**Authority:** ADR-0012, Design Documents 25, 35 and 36, `ROADMAP.md`, and the existing Settings,
Conversation, Task, Audit, Business Event and scheduler authorities

## Purpose and boundary

CORE-11C adds one optional organization-level timer that resolves eligible Inbox conversations
after sustained inactivity. The control is disabled by default and is a real runtime policy: the
existing scheduler scans the reserved Inbox Operations setting, row-locks candidates, rechecks
their current facts, and changes only safe open or pending conversations.

This milestone does not add a workflow engine, task replacement, SLA calculation, pipeline stage,
notification rule, AI action, campaign preference, provider feature, or a second conversation
state machine. Those remain separate approved slices.

## Reuse and ownership map

| Need | Existing authority reused | CORE-11C extension |
|---|---|---|
| Policy persistence | Reserved `inbox.operations.v1` organization setting | Adds validated `auto_resolve.enabled` and `inactive_after_hours`; no table, migration or route. |
| Inactivity facts | Conversation `last_message_at`, `updated_at`, `unread_count`, `status` | A candidate must be inactive on both message and operational-update clocks. |
| Follow-up protection | Existing Task status and conversation link | Any active, non-deleted open Task excludes the conversation. |
| Concurrency | Existing Conversation row and repository lock | Candidate discovery is followed by locked current-state revalidation. |
| Scheduling | Existing Celery Beat and `scheduler.tick` control queue | One minute-cadence bounded scanner; no second scheduler or queue. |
| Evidence | Existing Audit and Business Event ledgers | System status change plus deterministic `conversation.auto_resolved` fact. |
| Inbound lifecycle | Existing Message/Conversation inbound transaction | A genuinely new current inbound reopens a resolved conversation; duplicates and older replay do not. |
| UI/client | Existing Settings → Application panel and generated contract | Original responsive timer control; OpenAPI remains 208 paths. |

## Policy contract

- `enabled` defaults false.
- `inactive_after_hours` defaults to 72 and accepts whole values from 1 through 720.
- the existing `settings:manage` permission remains the mutation authority;
- the generic settings write cannot bypass validation of the reserved policy;
- the policy adds no required migration because existing JSON persistence is its approved owner.

## Eligibility and safety rules

A conversation is eligible only when every condition holds at the locked recheck:

1. it belongs to the organization whose persisted policy is being evaluated;
2. it is active and currently `open` or `pending`;
3. it has zero unread customer messages;
4. it has a real `last_message_at` at or before the policy cutoff;
5. its `updated_at` is also at or before the cutoff, so recent assignment/status/manual activity
   postpones resolution;
6. it has no active, non-deleted open Task linked to it.

Resolved and snoozed conversations are never candidates. Unread messages and open follow-up tasks
are explicit hard protections rather than presentation hints.

## Bounded scan, concurrency and idempotency

The minute tick reads only organizations with the reserved policy and scans at most 100 candidates
per organization per execution. The database query applies the complete stable eligibility filter
and excludes open Tasks so protected rows cannot fill and starve a batch. Each candidate is then
locked and the same rules plus Task protection are rechecked before mutation.

Overlapping Beat deliveries are therefore safe: one worker changes and commits the row; a waiter
refreshes under the lock, sees `resolved`, and performs no second mutation. Each successful change
increments the Conversation version, records system Audit evidence, and appends a deterministic
Business Event derived from organization, conversation and the inactivity-cycle activity anchor.
Re-running the same tick creates no second status change, Audit row, or event.

Commits occur per candidate. If a later candidate fails, earlier completed rows and their evidence
remain atomic; task retry safely resumes from current state.

## Inbound reopen behavior

Auto-resolve is useful only if later customer activity returns to the active Inbox. A newly inserted
inbound Message therefore changes a resolved Conversation back to `open` inside the same inbound
transaction and records a system status-change Audit entry. This decision occurs only after stored-
message dedupe and only when the inbound timestamp is at least as current as the conversation's
latest Message. A broker retry or older webhook replay cannot reopen a resolved thread.

## Operator experience and originality

Settings → Application now contains a dedicated “Automatic conversation resolution” section with
an explicit enable switch, a bounded hours field, protection wording, automatic-reopen guidance,
permission-aware disabled state, and responsive stacking. The approved Live Chat Settings capture
informed only the workflow expectation that conversation lifecycle controls belong near other
Inbox operations settings. All React/Python code, wording, tokens, spacing, icon choice, validation
and layout are original; no AiSensy code, text, asset, branding or pixel layout is used.

## Validation boundary

Repository coverage proves safe defaults and bounds, persisted UI payloads, candidate filtering,
open-Task protection, row-locked recheck semantics, Audit and deterministic event evidence,
idempotent repeated scans, scheduler registration/queue ownership, fresh-inbound reopen, duplicate/
stale non-reopen, generated contracts, lint, strict types, regression tests and production build.

The real local settings route redirects an unauthenticated session to sign-in and no credential was
entered. Authenticated representative-data desktop/mobile screenshots, keyboard-only and screen-
reader review, target-host MySQL contention, live Celery Beat observation and production operator
acceptance remain `PENDING – Host Machine Validation`; no host or production claim is inferred.

## Remaining CORE-11 work

- campaign preferences, pipeline/SLA, notification, security and audit settings;
- team online presence, workload reporting, login history and permission audit;
- required/active attribute-definition controls and their domain enforcement.
