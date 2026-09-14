# ADR-0020: Enterprise Omnichannel Channel Manager

- **Status:** Accepted and frozen
- **Date:** 2026-08-04
- **Milestone:** M13-00 — Architecture & Provider Lock
- **Decision owners:** Product owner and repository governance
- **Implementation status:** Not started
- **Baseline:** `ui/taste-modernization` at `7e503a3f2e1d35d54548d9d8fe95e82591e26be1`

## Context

The platform already operates the Official Meta WhatsApp Business Cloud API through a provider-neutral,
capability-gated `ChannelAdapter`, a canonical conversation/message model, shared Inbox, Customer 360,
media, assignment, notes, tags, notifications, analytics, RBAC, tenant scoping and audit authorities.
The approved Module 13 plan adds QR-connected WhatsApp Multi-Device as a second independent provider
while preserving one operator experience and one customer record.

The owner approved the Module 13 architecture and froze it as the implementation contract. M13-00 is
documentation and validation only. It does not authorize QR login, a session runtime, Channel Manager,
database migrations, API routes, backend services, frontend changes, Inbox changes or Customer 360
changes.

## Decision

Module 13 will deliver an Enterprise Omnichannel Channel Manager in which Official Meta Cloud API and
an approved QR Multi-Device provider coexist as independent channel connections behind the existing
channel abstraction.

The architecture is governed by these invariants:

1. **One existing channel seam.** The existing `ChannelAdapter`, capability vocabulary, canonical
   channel objects and adapter registry remain authoritative. Provider-specific operations are added
   only as capability-gated methods and data. No parallel adapter hierarchy or provider-specific CRM
   service family is created.
2. **One Contact authority.** A customer is represented by one canonical Contact. Provider identities
   link to that Contact; they are not separate customer records.
3. **Separate conversations, unified customer.** Each connection/endpoint keeps its own operational
   conversation because provider rules, sender identity and health differ. All conversations appear in
   one Customer 360 and one customer Timeline.
4. **One message ledger and event path.** Meta webhooks, QR live events and QR history synchronisation
   normalize into the existing durable ingestion, conversation, message, media, notification,
   analytics and audit authorities.
5. **Capability-driven behavior.** Templates, campaigns, broadcasts, official webhooks, official
   analytics and Meta compliance remain Meta capabilities. QR permits only approved human
   conversation, media, history and session capabilities declared by the selected adapter.
6. **No automatic cross-provider failover.** A Meta message is never silently resent through QR and a
   QR message is never silently resent through Meta. Provider or connection changes require an
   explicit, authorized and audited operator action.
7. **Independent failure domains.** Failure, throttling, disconnection or re-authentication of one
   connection must not stop another connection or the rest of the CRM.
8. **Durable control plane, isolated session runtime.** Connection desired/observed state, session
   revision, leases, fencing, health and audit evidence are durable. QR plaintext session material is
   present only in the active session holder's memory.
9. **Additive evolution.** Existing Meta routes, WABA/phone-number records, migrations, generated
   contracts and business workflows remain compatible while generic connection/endpoint records are
   introduced through expand/backfill/switch/contract migration stages.
10. **No implementation without gates.** A concrete QR provider must pass the frozen provider
    evaluation and security criteria. Module 13 implementation also remains subject to the prerequisite
    and separate owner-instruction gates recorded in repository governance.

## Reused authorities

Module 13 must extend, not duplicate:

- `app.channels.ChannelAdapter`, capability checks, canonical channel models and adapter registry;
- Official Meta adapter and WABA/phone-number services;
- Conversation, Message, Webhook/Event, Send and Media services;
- Celery/Redis queue, retry, idempotency, dead-letter and monitoring infrastructure;
- Contacts, Customer 360, Customer Timeline, Inbox, assignment, notes, tags and search;
- Notification Center, Analytics, Audit, RBAC and organization isolation;
- existing API conventions, generated OpenAPI client and migration history.

## Provider and endpoint model

The approved vocabulary is:

- **channel family:** customer-facing network such as `whatsapp`, later `instagram`, `messenger`,
  `telegram`, `rcs` or `sms`;
- **provider type:** concrete adapter implementation such as `meta_cloud` or the approved QR provider;
- **channel connection:** tenant-configured provider account or authenticated session;
- **channel endpoint:** addressable business identity, such as a Meta phone number or paired QR number;
- **contact identity:** a normalized provider identity linked to one Contact;
- **conversation:** the thread between one Contact and one endpoint;
- **provider message id:** an endpoint-scoped native message identifier.

Core business logic must ask whether a connection declares a capability. It must not branch throughout
the CRM on provider names.

## Customer identity decision

Identity resolution is exact and organization-scoped:

1. Normalize the provider identity using its namespace and scope.
2. Resolve an existing `contact_identity`.
3. For WhatsApp telephone identities, resolve the canonical normalized phone identity.
4. Reuse the linked Contact when an authoritative identity exists.
5. Create a Contact only when no authoritative match exists.
6. Never merge on display name, profile name, avatar, email similarity or fuzzy matching.
7. Route conflicts to a restricted manual-resolution workflow; never guess.

A scoped identity can belong to only one active Contact. Merges and splits are privileged, audited
operations and must preserve historical references.

## Session and connection decision

Each QR connection has a durable lifecycle:

`Created → Awaiting Authentication → Awaiting QR → Pairing → Connected`

From `Connected`, the connection may become `Degraded`, `Reconnecting`, `Paused`, `Disabled`,
`Logged Out` or `Awaiting Re-authentication`. Illegal transitions fail closed and every transition is
versioned and audited.

Exactly one runtime holder may drive a QR session. A durable lease plus fencing token prevents
split-brain. Session material is encrypted at rest, never returned by APIs, never logged and decrypted
only in the active holder's memory. A revoked or invalid session stops outbound work and requires an
authorized re-pair; it is not retried indefinitely.

## Message, media and retry decision

- Live and imported provider events enter the existing persist-first event path and are normalized
  before reaching CRM services.
- Provider message identity is scoped by connection/endpoint. Redelivery and reconnect must be
  idempotent and must never create a duplicate customer message.
- History synchronisation is bounded, checkpointed, resumable and lower priority than live traffic.
  Imported history does not create false unread counts or new-message notifications.
- All attachments use the existing `media_assets` and object-storage authority. Provider media
  references are connection/endpoint scoped.
- Transient failures use bounded exponential backoff with jitter. Terminal or ambiguous outcomes are
  reconciled before another send; there is no blind resend.

## Security decision

- Meta credentials, QR session material and future provider credentials are distinct encrypted secret
  types with key versioning and rotation.
- QR payloads are short-lived, no-store, authorization-bound and invalidated after success or expiry.
- Connection, endpoint, credential, authentication, device, history and diagnostic operations have
  explicit RBAC and object authorization.
- Organization isolation applies to every new record, query, event, cache key, job and audit entry.
- Sensitive values are excluded from serializers, logs, errors, metrics, traces and audit payloads.
- Session runtimes use least-privilege credentials, authenticated internal communication, leases and
  fencing.

## API and database evolution decision

Implementation uses additive `/api/v1` resources, UUID public identifiers, RFC 7807 errors, cursor
pagination, idempotency keys, optimistic concurrency and generated OpenAPI contracts.

The approved logical records are:

- `channel_connections`
- `channel_endpoints`
- `channel_secrets`
- `channel_sessions`
- `channel_devices`
- `contact_identities`
- `channel_sync_checkpoints`
- `media_channel_references`

Existing WABA, phone-number, conversation, message, webhook/event and media records are linked and
backfilled additively. Existing high-volume tables are changed only through expand/backfill/verify/
switch/contract stages with tested rollback. Applied migrations are never rewritten.

## Future-provider consistency decision

Frozen Design Document 07 named future channels but explicitly excluded Instagram. The later
owner-approved Module 13 scope includes Instagram, Messenger, Telegram, RCS and SMS as future adapter
possibilities. This ADR records that later owner decision as an additive future-extensibility override
of the Instagram exclusion only.

It does not authorize implementation of any future provider in Module 13. Each provider still
requires a separate roadmap milestone, capability contract, compliance review, adapter certification
and owner approval. Public signup, reseller, marketplace, multi-project, billing, ads, payments and
commerce remain excluded.

## Provider selection boundary

M13-00 freezes the objective provider evaluation contract but does not fabricate a provider choice.
A QR candidate is acceptable only after evidence proves stable message identity, idempotent event
replay, session export/recovery, secure credential handling, media support, bounded history sync,
health reporting, reconnect semantics, operational support, licensing and policy acceptability.

Until a candidate passes every Required criterion, QR implementation and production enablement remain
blocked. Selecting or replacing the provider does not permit changes to the frozen CRM, identity,
conversation, security or operator architecture.

## Consequences

- Meta remains fully operational during every migration and rollout stage.
- QR is introduced connection by connection behind disabled-by-default feature flags.
- Operators receive one Inbox and one Customer 360 with explicit provider/endpoint markers.
- Analytics distinguish shared ledger facts from provider-only facts; unavailable metrics are not
  rendered as zero.
- Additional schema, runtime and operational complexity is accepted to obtain isolation, recovery and
  secure session ownership.
- No implementation milestone may claim Production Ready without repository, host, security,
  performance, browser, accessibility, operator-journey and deployment evidence required by
  `ENGINEERING_STANDARDS.md`.

## Rejected alternatives

- **Separate QR CRM or Inbox:** rejected because it duplicates Contacts, conversations and operator
  workflows.
- **Provider branches throughout services:** rejected because the existing capability-based adapter is
  the frozen seam.
- **Automatic Meta↔QR failover:** rejected for duplicate-send, consent, sender-identity, compliance and
  audit risk.
- **Fuzzy automatic customer merging:** rejected because a wrong merge exposes private customer data.
- **QR campaigns or bulk automation:** rejected because Module 13 does not use QR to bypass official
  channel controls.
- **Redis-only session truth:** rejected because restarts or failover would lose authoritative state.
- **Selecting an unevaluated provider:** rejected because vendor capability is an external fact, not a
  planning assumption.

## Implementation authorization boundary

This ADR and Design Document 33 complete the M13-00 implementation contract. They do not start
M13-01. Any architecture, scope, abstraction, milestone-order or provider-topology deviation requires
explicit owner approval and a new additive ADR before implementation proceeds.
