# Document 84 — CORE-15 Download Center Reconciliation

## Reconciliation result

The unified personal Download Center, server-filtered history, keyset pagination, current-permission
filtering, owner isolation, status projection and signed artifact downloads already exist. CORE-15
therefore closes the remaining artifact-authorization gap instead of creating a duplicate job
history or download surface.

## Decision

An export's durable retention timestamp is authoritative over every short-lived signed URL. New
links are capped so their signature cannot outlive artifact retention. The signature-authenticated
download endpoint also rechecks durable retention, revoking a link that was legitimately issued
before the artifact expired.

## Security boundary

Signature verification still occurs before database lookup, preventing unsigned artifact probing.
After verification, expired export artifacts return the same gone response as expired signatures.
Tenant, owner and current-permission filtering remain enforced when a user discovers and requests a
link through Download Center; the signed URL remains the intentionally transferable, time-bounded
credential for the byte download itself.

## Scope boundary

- No second job table, queue, history API or download page.
- No change to import/bulk report retention, because they are not Download Center export records.
- No new artifact family, retry authority, cancellation flow or database migration.
- Gated Scan/generated-document sources remain absent until their source capabilities are approved.

## Acceptance evidence

Focused export, Download Center and analytics coverage verifies history/RBAC behavior, signed-link
delivery, signature tamper rejection, link-expiry capping and revocation after durable retention.
The OpenAPI contract remains unchanged at 247 paths.
