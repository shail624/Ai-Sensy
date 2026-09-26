# Document 83 — CORE-14 Read Receipt Policy

## Decision

Provider read receipts are a channel capability, independently controlled by the organization-level
inbox policy. The existing `auto_mark_read` setting remains a user-interface behavior: it decides
whether opening a conversation invokes the mark-read action. The new `send_read_receipts` setting
decides whether that action also acknowledges the newest receiptable inbound message to a supported
provider.

## Scope boundary

CORE-14 adds the capability contract, Meta Cloud implementation, policy control, UI control and
read-action orchestration. Existing business hours, welcome/off-hours replies and local shared
unread counters are reused unchanged. No migration is required because inbox policy is already a
validated value in the organization settings authority.

## Failure and idempotency

The provider acknowledgement happens before the local unread counter is committed. A provider
failure therefore cannot create a false local success. Retrying may repeat the provider request,
which is safe because marking the same provider message read is idempotent. An already-read local
conversation remains a no-op and sends no further provider request.

Connectors that do not declare read-receipt capability retain fully functional local unread state
without pretending to have acknowledged the message externally. A missing provider message id also
falls back to the local reset because there is no truthful remote target.

## Security and tenancy

The conversation is resolved inside the authenticated tenant. Its phone-number and WABA ownership
are rechecked before an adapter is created. Provider credentials remain inside the existing WABA
adapter factory and are never returned by this workflow.

## Exclusions

- No business-hours or automatic-reply redesign.
- No WAHA read-receipt claim without a certified connector capability.
- No per-agent read markers or schema change.
- No delivery/read analytics change.
