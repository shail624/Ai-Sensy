# ADR-0008 — Reuse media storage for customer documents with immutable lineage

- **Status:** Accepted — 2026-07-30
- **Scope:** Phase 4A customer-document records, versions, verification and signed preview
- **Runtime/API/schema change:** additive tables, permissions and routes only

## Context

Phase 3 exposed the existing media library in the Reactivation workspace but correctly did not
infer customer ownership, document status, verification, expiry or versions from filenames. The
Phase 4 backlog now authorizes that first missing contract.

The platform already has one validated, scanned, content-addressed, tenant-scoped file authority:
`media_assets` plus the configured storage provider. Storing document bytes in a new table, adding
a second upload pipeline, or making a media asset mutable would duplicate security behavior and
break content deduplication.

## Decision

- Represent a logical customer document in `contact_documents` and keep its file lineage as
  append-only `contact_document_versions` rows referencing existing `media_assets`.
- Keep verification state and expiry on the document aggregate; keep every lifecycle decision in
  append-only `contact_document_events` and project material events to `contact_events`.
- Increase `media_assets.usage_count` for every retained version so referenced evidence cannot be
  removed through the media API.
- Deliver content only by delegating to the existing signed URL service after a tenant-scoped
  document/version lookup. Never return storage keys.
- Split permissions into `documents:read`, `documents:write`, and `documents:verify`. Do not grant
  general `media:write` implicitly to a document writer.
- Keep expiry mutation explicit. Reads compute `is_expired` but never create audit history as a side
  effect.

## Consequences

- Customer documents gain real ownership, versions, reviewer decisions, expiry and history while
  file validation, scanning, storage, signing and deduplication stay single-source.
- Replacing a document means adding a version; earlier evidence remains accessible and attributable.
- Agents can collect/link existing eligible files and managers can verify. Uploading new generic
  media remains governed by the existing storage permission.
- The document domain adds no queue or provider work and changes no existing route, response,
  permission, database table, send behavior or business rule.
- A future automated expiry scheduler may call the same transition service, but Phase 4A does not
  add a schedule or mutate records during reads.
