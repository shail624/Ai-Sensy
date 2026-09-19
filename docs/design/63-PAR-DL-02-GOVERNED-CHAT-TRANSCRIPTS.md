# Design 63 — PAR-DL-02 Governed Chat History Transcript Exports

**Status:** Repository implemented  
**Date:** 2026-08-24  
**Depends on:** Dedicated Chat History, message ledger, PAR-DL-01, shared export/storage/queue/audit

## Decision

Chat History transcripts are a new entity in the existing export system, not a second document or
download subsystem. A selected conversation produces one personal, expiring artifact through the
current `exports` table, `exports` queue, format writers, storage provider, signed-link resolver,
audit actions and Download Center history.

The new `inbox:export` permission is intentionally separate from `inbox:read`. Reading a shared
thread does not automatically authorize extracting it. The Chat History route still requires
`inbox:read`; its export action additionally appears only to `inbox:export`. Direct API creation,
progress and Download Center transcript visibility enforce the export permission independently.

## Contract

- `POST /api/v1/conversation-transcripts/export`
  - selected `conversation_id`;
  - `pdf`, `csv`, `xlsx` or `json`;
  - optional `from` inclusive and `to` exclusive instants;
  - always returns the shared `202 JobAcceptedResponse`.
- `GET /api/v1/conversation-transcripts/export/{export_id}`
  - tenant-, requester-, entity- and permission-scoped;
  - returns the shared progress envelope and a fresh signed link only when ready/unexpired.
- Download Center category `chat_history`
  - personal jobs only;
  - governed by current `inbox:export` access;
  - uses existing status, expiry, polling and keyset history behavior.

The UI converts an optional through-calendar-date to the next local midnight, making the selected
day inclusive while preserving the server's unambiguous half-open range. An empty range means the
complete persisted thread.

## Worker and query discipline

The request path validates tenant ownership of the conversation, writes job/queue/audit records and
dispatches; it never reads message rows. The worker resolves the conversation again inside the job
tenant and streams messages oldest-first in 500-row `(created_at, id)` keyset batches. Optional
range predicates use the existing conversation/time index. Progress commits after each batch.

This preserves bounded memory for very large threads and prevents a browser's currently loaded
message pages from becoming an incomplete export authority.

## Artifact shape and privacy

Every row contains:

- UTC timestamp;
- inbound/outbound direction;
- customer label or `Business` participant role;
- message type;
- human-readable canonical content;
- delivery status;
- platform public message ID.

Content readers cover text, media caption/filename, template, reaction, location and interactive
reply shapes. Provider message IDs, provider media IDs, private/signed media links and internal
storage references are never copied into the artifact. Unsupported canonical content receives a
truthful type label instead of raw JSON. The shared writers neutralize formula-leading spreadsheet
cells. Artifacts retain the configured export expiry and signed-link TTL.

## Permission and role behavior

Migration `0053_conversation_transcript_exports` inserts `inbox:export` idempotently without a new
table. The default owner/admin catalog includes every permission and the shipped manager preset
includes transcript export; the agent and analyst presets do not. Existing custom roles remain
administrator-controlled rather than being silently widened.

## UI behavior

The selected-thread header adds `Export transcript` only when authorized. Its responsive sheet
contains:

- customer context and privacy explanation;
- format selection;
- optional from/through date inputs with invalid-range refusal;
- queued/preparing/failed/ready states;
- direct ready download;
- deep link to `Download Center?category=chat_history`.

Closing the sheet never cancels the durable job; Download Center continues polling and preserves
history. Live Chat remains the only place for reply, assignment, status, notes, tags or reactions.

## Migration and release contracts

- Head: `0053_conversation_transcript_exports`.
- Revisions: 54, one linear head.
- OpenAPI: 221 paths, generated TypeScript synchronized.
- Worker inventory: 31 application tasks, including
  `app.crm.tasks.run_conversation_transcript_export` on `exports`.
- No new table, storage provider, queue, customer send, campaign execution or provider call.

## Validation evidence

- Focused backend: 35/35.
- Focused Chat History/Download/navigation UI: 50/50.
- Complete backend: 1537 passed, 6 MySQL-only skipped, zero failed in 445.40s.
- Complete frontend: 41 files / 845 tests.
- Static gate: 6/6; strict mypy across 310 source files.
- Migration upgrade/downgrade/re-upgrade and single-head checks pass.
- OpenAPI drift and generated client pass.
- Vite 8.2.2 production build passes; Chat History is 15.34 kB / 4.90 kB gzip.

## Explicit remaining work

- list-level Chat History date filters;
- campaign-generated, media-only and audit-scoped list filters;
- server-shared Chat History saved views;
- campaign, compliant Scan and generated-document artifact sources;
- Docker/security release-profile rerun for the changed tree;
- authenticated representative-data device/WCAG review and target-host commissioning.

`Production Ready` remains **NO** until the external release/host acceptance gates close.
