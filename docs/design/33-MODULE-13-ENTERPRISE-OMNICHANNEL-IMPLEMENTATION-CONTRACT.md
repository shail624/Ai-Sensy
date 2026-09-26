# Module 13 — Enterprise Omnichannel Channel Manager Implementation Contract

| Field | Value |
|---|---|
| Document | 33 — Module 13 implementation contract |
| Milestone | M13-00 — Architecture & Provider Lock |
| Status | Frozen; Repository Validated when the M13-00 governance commit is synchronized |
| Date | 2026-08-04 |
| Repository baseline | `ui/taste-modernization` at `7e503a3f2e1d35d54548d9d8fe95e82591e26be1` |
| Architecture decision | ADR-0020 |
| Implementation | Not started |
| Next milestone | M13-01 only after a separate owner instruction and all recorded prerequisite gates |

## 1. Purpose and authority

This document is the complete engineering handoff for the owner-approved Enterprise Omnichannel
Channel Manager. It converts the approved Module 13 plan into an implementation contract without
changing its architecture, scope, abstractions or milestone order.

It is additive to, and must be read with:

- `ENGINEERING_STANDARDS.md`
- `REPOSITORY_RULES.md`
- `PROJECT_STATE.md`
- `ROADMAP.md`
- `MODULE_STATUS.md`
- `IMPLEMENTATION_TRACKER.md`
- `VALIDATION_RESULTS.md`
- `docs/design/07-INTEGRATIONS-CHANNEL-ARCHITECTURE.md`
- `docs/adr/0020-enterprise-omnichannel-channel-manager.md`

Where older frozen documents conflict with a later explicit owner decision, ADR-0020 records the
narrow additive resolution. No frozen historical document is silently rewritten.

M13-00 is documentation and validation only. Nothing in this document authorizes implementation of
QR authentication, session runtime, connection management, schema migrations, API endpoints,
backend services, frontend routes, Inbox changes or Customer 360 changes.

## 2. Frozen scope

### 2.1 In scope for Module 13

- Official Meta WhatsApp Business Cloud API as the existing official provider.
- One or more separately managed QR-connected WhatsApp Multi-Device connections through an approved
  provider adapter.
- One provider-neutral control plane for connections, endpoints, credentials, sessions, devices,
  health, diagnostics and history synchronisation.
- One canonical Contact, Customer 360 and customer Timeline across providers.
- Separate provider/endpoint conversations under the same Contact.
- Existing Inbox, assignment, internal notes, tags, media, search, notifications, analytics and audit
  extended to provider-aware facts.
- Capability-gated provider behavior.
- Future adapter readiness for Instagram, Messenger, Telegram, RCS and SMS through separately
  approved milestones.

### 2.2 Explicitly out of scope

- Implementing Meta + QR functionality during M13-00.
- A second CRM, Contact table, Inbox, Timeline, notification system, analytics store or media store.
- QR campaigns, broadcasts, bulk sending or unattended mass automation.
- Automatic cross-provider failover.
- Silent continuation from one business number/provider to another.
- Fuzzy or name-based automatic Contact merges.
- Public signup, reseller, multi-project, marketplace, billing, ads, payments or commerce.
- Selecting a QR provider without objective evidence.
- Implementing Instagram, Messenger, Telegram, RCS or SMS within Module 13.
- Rewriting existing migrations or breaking current Meta APIs.

## 3. Repository alignment and reuse contract

### 3.1 Existing authority that must remain in place

| Concern | Existing authority to extend |
|---|---|
| Channel seam | `app.channels.base.ChannelAdapter` and adapter registry |
| Capabilities | `app.channels.capabilities.Capability` |
| Canonical provider objects | `app.channels.models` |
| Official provider | Existing Meta Cloud adapter and WABA services |
| Durable inbound | Existing webhook/event persist-first path and dead-letter handling |
| Contact resolution | Existing Contact repository and ConversationService resolution flow |
| Conversation state | Existing Conversation model/repository/service |
| Message ledger | Existing Message and MessageStatusHistory records/services |
| Outbound delivery | Existing SendService, queue task and retry classification |
| Media | Existing `media_assets`, object storage and media queue |
| Operator collaboration | Existing Inbox, assignment, internal notes and tags |
| Customer context | Existing Customer 360 and Customer Timeline |
| Notifications | Existing unified Notification Center |
| Analytics | Existing message ledger and rollup infrastructure |
| Security | Existing authentication, RBAC, organization scoping, audit and encryption pattern |
| API | Existing `/api/v1`, RFC 7807, UUID, pagination, idempotency and OpenAPI conventions |
| Async execution | Existing Celery/Redis queue registry, locks, retries and monitoring |

### 3.2 Prohibited duplication

Implementation must not create provider-specific alternatives such as `QrContact`, `QrConversation`,
`QrMessage`, `QrInbox`, `QrNotification`, `QrTimeline`, `QrMediaLibrary` or a second send/event
service. Provider-native payloads stop at the existing adapter boundary.

### 3.3 Single-adapter consistency correction

The repository already defines one capability-based `ChannelAdapter`. Module 13 extends that
interface with approved optional methods and capability values where required. It does not create a
second interface hierarchy. This resolves ambiguous planning language while preserving the approved
provider-neutral architecture.

## 4. Target architecture

```text
Official Meta Cloud API ── existing Meta adapter ──┐
                                                   │
Approved QR provider ───── QR adapter ─────────────┼─ existing ChannelAdapter registry
                                                   │
Future approved providers ─ future adapters ──────┘
                         ↓ canonical provider events/messages
                existing durable ingestion and queue fabric
                         ↓
         Contact resolution → Conversation → Message ledger → Media
                         ↓
 Inbox · Customer 360 · Timeline · Assignment · Notes · Tags
 Search · Notifications · Analytics · Audit
```

### 4.1 Control plane

The provider-neutral control plane owns durable configuration and lifecycle facts:

- channel connection;
- business endpoint;
- encrypted provider secret;
- QR session revision and lease;
- linked-device observations;
- history-sync checkpoint;
- connection health and diagnostics;
- desired state and observed state;
- audit and notification evidence.

### 4.2 Data plane

The data plane uses existing message and event authorities:

- outbound intent is persisted before provider delivery;
- inbound provider events are persisted before interpretation;
- adapters normalize native payloads;
- existing services resolve Contacts, conversations, messages and media;
- retries are idempotent and provider/endpoint scoped;
- live traffic has priority over history synchronisation.

### 4.3 Failure-domain rule

A provider, connection, endpoint or session failure affects only its own queue/session lane. Meta,
other QR connections and the rest of the CRM remain operational.

## 5. Provider capability matrix

The matrix defines product behavior. A provider may expose an action only when its connection declares
the capability and the user has permission.

| Capability | Meta Cloud API | QR Multi-Device | Operator rule |
|---|---|---|---|
| Text send/receive | Required | Required | Canonical text ledger |
| Media send/receive | Required | Required | Existing media authority and provider limits |
| Interactive messages | Existing supported forms | Optional; provider-evaluated | Hide when absent |
| Reactions | Existing Meta capability | Optional; provider-evaluated | Hide when absent |
| Approved templates | Required | Not permitted | Meta only |
| Campaigns/broadcasts | Required | Not permitted | Meta only; QR cannot be selected |
| Bulk/unattended sending | Required for governed Meta campaigns | Not permitted | No QR bypass |
| Official webhooks | Required | Not applicable | Meta signature verification |
| Session event stream | Not applicable | Required | Authenticated QR runtime stream |
| Token authentication | Required | Optional/provider-specific | Secret-vault pattern |
| QR authentication | Not applicable | Required | Short-lived, no-store pairing flow |
| History synchronisation | Official API capability if available; not required by M13 | Required | Bounded, checkpointed, no false unread |
| Linked-device status | Not applicable | Required when provider exposes it | Factual status only |
| Connection health | Required | Required | Shared health vocabulary, provider-specific signals |
| Reconnect/session replacement | Not applicable to stateless Meta delivery | Required | Authorized and audited |
| Official conversation/window facts | Required | Not claimed | Meta compliance remains server enforced |
| Official pricing/cost | Required where available | Not available | Never infer QR cost |
| Official analytics | Required where available | Not available | QR operational metrics remain separate |
| Calls/call metadata | Only when separately enabled | Optional; future enhancement | Not required for M13 completion |
| Location/contact cards | Existing capability-dependent behavior | Optional; provider-evaluated | Hide when absent |

### 5.1 Required new capability values

The existing capability enum may be extended additively during implementation with values equivalent
to:

- `qr_auth`
- `session_stream`
- `history_sync`
- `devices`
- `session_reconnect`
- `session_logout`

These are additions to the existing capability mechanism, not new abstractions. Exact enum naming is
an implementation naming decision only when it does not alter the frozen semantics above.

## 6. QR provider evaluation and selection gate

No QR provider is selected by this document. A candidate must be evaluated using a documented test
account and representative device before any QR implementation milestone can enable real delivery.

### 6.1 Required — pass/fail criteria

A candidate fails selection if any Required item is unsupported or cannot be evidenced.

| Area | Required evidence |
|---|---|
| Legal and policy position | Documented authorization to use the connector for the approved internal use; licensing and data-processing terms reviewed |
| Stable identity | Stable business endpoint identity and stable customer identity mapping |
| Message identity | Stable provider message ID or equivalent idempotency token for inbound and outbound events |
| Inbound replay | Duplicate/redelivered events can be recognized safely |
| Ambiguous send handling | Provider offers acknowledgement/reconciliation sufficient to prevent blind resend |
| Session persistence | Session can be encrypted, restored or explicitly requires safe re-pair after restart |
| Single-holder safety | Provider supports one active runtime holder without competing event streams |
| QR lifecycle | Pair, expiry, refresh, success, invalidation, logout and remote logout are observable |
| Reconnect behavior | Bounded reconnect and clear re-authentication signal |
| History sync | Bounded pagination/checkpoints and stable ordering or cursors |
| Live events | Reliable message/status event stream with reconnect semantics |
| Media | Secure inbound/outbound media retrieval with type/size metadata |
| Health | Connection/session state and enough signals for Healthy/Warning/Critical/Re-auth Required |
| Error model | Retryable, throttled, authentication and terminal failures are distinguishable |
| Security | No plaintext session logging; supports secret isolation and runtime-only plaintext |
| Tenant isolation | Every configured connection can be bound to one organization and endpoint scope |
| Operational support | Version policy, incident path and security-update process are documented |
| Testability | Sandbox/test number or controlled test environment supports certification |

### 6.2 Recommended criteria

- Provider-supplied client nonce for outbound reconciliation.
- Device-list and device-revocation events.
- Backfill range controls and message-count estimates.
- Exportable diagnostics that exclude secrets.
- Published rate limits and maintenance windows.
- Supported horizontal session distribution model.
- Strong typed SDK or stable documented protocol.
- Enterprise support SLA.

A Recommended gap does not automatically reject a provider, but it must have a documented mitigation
and owner approval before production enablement.

### 6.3 Future enhancement criteria

- Call metadata.
- Presence/typing indicators.
- Message edits or deletes.
- Advanced interactive content.
- Provider-native labels.
- Additional linked-device administration.

These capabilities cannot delay Module 13 unless separately promoted by the owner.

### 6.4 Selection record

Provider selection requires a separate evidence record containing:

- candidate and version;
- evaluation date and evaluator;
- every Required result;
- Recommended gaps and mitigations;
- threat-model deltas;
- operational support details;
- owner approval;
- adapter certification result.

A provider name, SDK or dependency must not be committed before this record is approved.

## 7. Threat model

### 7.1 Protected assets

- Meta access tokens, app secrets and webhook secrets.
- QR session material, refresh material and QR payloads.
- Customer identities, phone numbers, profile information and message content.
- Attachments and signed media URLs.
- Provider message IDs and history checkpoints.
- Connection/device state and diagnostics.
- Operator permissions, assignments, notes and audit evidence.
- Tenant/organization boundaries.

### 7.2 Trust boundaries

1. Browser ↔ API edge.
2. API ↔ database/Redis/object storage.
3. API/worker ↔ Meta Cloud API.
4. Session runtime ↔ QR provider.
5. Session runtime ↔ database/queue/event path.
6. Worker ↔ object storage/media source.
7. Administrator ↔ credential/pairing operations.
8. Organization A ↔ Organization B, even though production is currently a private single-organization deployment.

### 7.3 Threat register

| Threat | Example | Required control |
|---|---|---|
| Spoofing | Fake provider event or stolen runtime identity | Provider/session authentication, internal service authentication, endpoint binding |
| Tampering | Modified QR session ciphertext or event payload | Authenticated encryption, signatures where available, integrity checks, immutable audit |
| Repudiation | Operator denies logout/re-pair/session replacement | Actor, target, request ID, before/after and outcome audit evidence |
| Information disclosure | QR/session secret in API, log, trace or cache | Write-only secrets, redaction, no-store, runtime memory only, secret-scanning tests |
| Denial of service | Reconnect storm or history sync starves live chat | Circuit breaker, bounded retry, connection lanes, live-priority queues, quotas |
| Elevation of privilege | Agent triggers pairing or reads diagnostics | Dedicated permissions, object authorization, step-up authentication recommendation |
| Cross-tenant access | Foreign connection ID or stale cache reveals messages | Organization predicates at repository/service/API/cache/job boundaries |
| Split brain | Two runtimes drive one session | Lease, fencing token, heartbeat expiry and stale-holder rejection |
| Duplicate send | Retry after ambiguous acknowledgement | Client/provider identity reconciliation; never blind resend |
| Wrong customer merge | Same display name merged across providers | Exact scoped identities only; restricted manual conflict resolution |
| Malicious media | Crafted archive/script/image | MIME inspection, size caps, malware policy, signed delivery, active-content restrictions |
| SSRF | Provider-controlled media URL targets internal network | URL allowlist/provider fetch client, private-IP denial, bounded redirects |
| Supply chain | Compromised QR SDK/container | Pinning, SBOM, vulnerability scan, provenance and provider security process |
| Stale authorization | QR page remains visible after role/session change | Server authorization every request, cache isolation, no-store, session invalidation |

### 7.4 Security acceptance boundary

Any verified credential disclosure, cross-tenant read, hidden-action API bypass, session split brain,
wrong Contact merge or duplicate customer send is a Blocker and prevents production enablement.

## 8. Security architecture

### 8.1 Secret separation

Secrets are independently typed and encrypted:

- `meta_system_user_token`
- `meta_app_secret`
- `meta_webhook_verify_token`
- `qr_session_material`
- `qr_refresh_material`
- future provider credentials

Secret APIs accept new values but never return them. Read models expose only factual metadata such as
`configured`, `key_version`, `rotated_at` and expiry.

### 8.2 Encryption and key management

- Use the existing authenticated-encryption pattern.
- Use a unique nonce per encryption operation.
- Persist key version and support rotation.
- Reject integrity-check failure; never attempt partial recovery.
- Decrypt QR session material only within the active runtime process.
- Encrypt backups and test restore with key availability.
- Exclude plaintext from audit, logs, metrics, traces, exceptions and job payloads.

Production key-management selection is an external dependency. A local development key may not be
used as production evidence.

### 8.3 RBAC contract

Provider-neutral permissions are planned as:

- `channels:read`
- `channels:manage`
- `channels:authenticate`
- `channels:credentials`
- `channels:diagnose`
- `channels:history_sync`
- `channels:devices`
- `channels:audit`

Existing `waba:read` and `waba:manage` remain compatible during migration. Mapping must not silently
grant pairing, credential or device privileges.

### 8.4 Object authorization

Every read and command must verify:

- actor organization;
- connection organization;
- endpoint belongs to connection;
- conversation belongs to endpoint and Contact;
- job/checkpoint belongs to connection;
- authentication session belongs to connection and actor has current permission;
- credential/device operations use their dedicated permission;
- bulk requests contain only authorized objects.

Unknown and foreign identifiers follow the repository's non-disclosure behavior.

### 8.5 QR response security

QR authentication responses use:

- short TTL;
- one active authentication revision per connection;
- `Cache-Control: no-store`;
- no browser persistence;
- no analytics capture;
- immediate invalidation after success, cancel or expiry;
- server authorization on every poll/refresh;
- sanitized audit metadata without QR content.

## 9. Session lifecycle contract

### 9.1 Durable connection states

- `created`
- `awaiting_authentication`
- `awaiting_qr`
- `pairing`
- `connected`
- `degraded`
- `reconnecting`
- `paused`
- `disabled`
- `awaiting_reauthentication`
- `logged_out`

### 9.2 Legal transitions

```text
created → awaiting_authentication
awaiting_authentication → awaiting_qr
awaiting_qr → pairing | awaiting_qr (refresh) | created (cancel)
pairing → connected | awaiting_qr | awaiting_reauthentication
connected → degraded | reconnecting | paused | disabled | logged_out
paused → connected | disabled | logged_out
 degraded → connected | reconnecting | awaiting_reauthentication | disabled
reconnecting → connected | awaiting_reauthentication | disabled
awaiting_reauthentication → awaiting_qr | disabled | logged_out
disabled → created | logged_out
logged_out → created
```

No removal is allowed while a live holder or active command exists. Historical conversations and
messages remain after connection disable/logout/removal.

### 9.3 Desired versus observed state

- API commands change durable desired state after authorization and version checks.
- Runtime/health processing reports observed state.
- A reconciliation loop moves observed state toward desired state.
- Stale runtime reports are rejected by session revision/fencing token.
- State transitions are versioned, audited and notification-aware.

### 9.4 Single-holder lease

A session record stores:

- connection ID;
- session revision;
- encrypted secret reference;
- holder runtime ID;
- lease expiry;
- fencing token;
- last heartbeat;
- reconnect attempts;
- last successful activity;
- validity/re-authentication state.

Only the holder with the current fencing token may emit live events or mutate session-observed state.

### 9.5 Recovery policy

| Failure | Recovery |
|---|---|
| Transient network drop | Bounded reconnect with jitter |
| Runtime crash | Lease expires; healthy runtime acquires a new fencing token |
| Deployment restart | Graceful drain, release/expiry, reattach from encrypted state |
| Remote logout/session invalid | Stop sends; `awaiting_reauthentication`; notify authorized users |
| Repeated reconnect failure | Open circuit; preserve queued intent; require diagnostics/re-auth |
| Provider outage | Mark degraded/critical; isolate lane; Meta and other connections continue |

## 10. Customer identity resolution contract

### 10.1 Identity key

A provider identity is unique by:

```text
organization_id + identity_namespace + identity_scope + normalized_value
```

Examples:

| Namespace | Scope | Value |
|---|---|---|
| `whatsapp_phone` | global | normalized E.164/WhatsApp telephone identity |
| `whatsapp_lid` | provider connection | provider LID |
| `instagram_user` | business account | scoped user identifier |
| `messenger_psid` | page | page-scoped identifier |
| `telegram_user` | provider | Telegram user identifier |
| `sms_phone` | global | normalized E.164 |

### 10.2 Resolution algorithm

1. Validate organization, connection and endpoint.
2. Normalize provider-native identity into namespace/scope/value.
3. Find an exact active `contact_identity`.
4. For WhatsApp telephone identity, check the canonical existing Contact `wa_id`/phone identity.
5. Reuse the linked Contact and add missing provider alias when safe.
6. Create a new Contact only when no authoritative match exists.
7. On conflicting authoritative identities, create no merge; record a restricted conflict.
8. Emit factual Contact/Timeline/Audit evidence.

### 10.3 Merge and split policy

- No automatic fuzzy merge.
- Merge/split requires a dedicated privileged command in a separately approved milestone if the
  existing Contact duplicate-resolution authority cannot safely perform it.
- Historical messages, conversations, provider identities and audit links must remain traceable.
- A provider identity cannot belong to two active Contacts.

## 11. Unified conversation and message contract

### 11.1 Conversation identity

Operational conversation identity becomes:

```text
organization_id + channel_endpoint_id + contact_id + optional provider_thread_key
```

A Contact may have multiple conversations through different endpoints. The operator sees them in one
Customer 360, not as one falsely merged provider thread.

### 11.2 Message normalization

Every stored message retains:

- organization;
- conversation;
- Contact;
- endpoint;
- direction;
- canonical message type/content;
- provider message ID in the existing physical provider-ID field during compatibility migration;
- provider occurrence time;
- ingestion origin: live, history sync, API, campaign or automation;
- canonical status and immutable status history;
- media reference;
- campaign/template facts where applicable.

### 11.3 Deduplication contract

The effective key is endpoint/connection plus provider message ID. The implementation must use the
existing durable event/idempotency authorities, scoped locks and repository checks so concurrent
redelivery is a no-op. Adapter certification must prove stable IDs. Because current high-volume
partitioned tables cannot accept arbitrary global unique indexes safely, the exact database/index
mechanism is an M13-01 implementation detail only if it preserves this frozen invariant and passes
concurrent duplicate tests; it is not permission to add a second message ledger.

### 11.4 History import contract

- Asynchronous Job authority.
- Bounded page size and durable checkpoint.
- Stable source ordering/cursor.
- Lower priority than live inbound/outbound.
- Idempotent resume after crash.
- Provider original timestamp retained.
- Imported old messages do not increment live unread or emit new-message notifications.
- A `live_cutover_at` boundary prevents imported/live overlap.
- Partial or unsupported history is disclosed, not labelled complete.
- Attachments use the existing media queue.

## 12. API contract

All resources are additive under `/api/v1`, authenticated unless explicitly documented, use UUID
public IDs, RFC 7807 errors, cursor pagination, row versions, request IDs and generated OpenAPI types.

### 12.1 Connection resources

```text
GET    /channel-connections
POST   /channel-connections
GET    /channel-connections/{connection_id}
PATCH  /channel-connections/{connection_id}
DELETE /channel-connections/{connection_id}
```

Collection filters include provider type, channel family, status, health and endpoint.

### 12.2 Lifecycle commands

```text
POST /channel-connections/{id}/connect
POST /channel-connections/{id}/pause
POST /channel-connections/{id}/resume
POST /channel-connections/{id}/reconnect
POST /channel-connections/{id}/logout
POST /channel-connections/{id}/replace-session
POST /channel-connections/{id}/health-check
POST /channel-connections/{id}/diagnostics
```

Side-effectful commands require `Idempotency-Key` and expected row/session version. Illegal state
returns conflict, not a fake success.

### 12.3 QR authentication resources

```text
POST   /channel-connections/{id}/authentication-sessions
GET    /channel-connections/{id}/authentication-sessions/{auth_id}
POST   /channel-connections/{id}/authentication-sessions/{auth_id}/refresh
DELETE /channel-connections/{id}/authentication-sessions/{auth_id}
```

The read response may contain only an active ephemeral QR representation and expiry metadata. It
never contains session credentials.

### 12.4 Endpoints, devices and health

```text
GET /channel-endpoints
GET /channel-endpoints/{endpoint_id}
GET /channel-connections/{id}/endpoints
GET /channel-connections/{id}/devices
GET /channel-connections/{id}/health
GET /channel-capabilities
```

### 12.5 History synchronisation

```text
POST /channel-connections/{id}/history-sync
GET  /channel-connections/{id}/history-sync/{job_id}
POST /channel-connections/{id}/history-sync/{job_id}/cancel
```

The existing Jobs API remains the authoritative progress/error surface.

### 12.6 Conversation send route

```text
POST /conversations/{conversation_id}/messages
```

This route derives provider and endpoint from the conversation. It prevents a client from pairing an
unrelated number/provider with the conversation. Existing `/messages/send` and current Meta/WABA APIs
remain compatible until separately approved deprecation.

### 12.7 Inbox/search filters

Conversation/search resources gain additive provider-aware filters:

- `channel_family`
- `provider_type`
- `channel_connection`
- `channel_endpoint`
- `connection_health`
- `ingestion_origin`

### 12.8 Event vocabulary

- `channel.connection.updated`
- `channel.authentication.qr_ready`
- `channel.authentication.qr_expired`
- `channel.health.changed`
- `channel.session.reauthentication_required`
- `channel.history_sync.progress`
- `channel.history_sync.failed`

Exact path count is estimated at +18–26 and must be verified during the first API-bearing milestone.
M13-00 changes no OpenAPI document.

## 13. Database migration strategy

### 13.1 Approved new records

#### `channel_connections`

- identifiers, organization, channel family, provider type;
- display name;
- desired/observed state;
- capability snapshot;
- health state/score;
- last activity/error;
- optimistic row version, audit and soft-delete fields.

#### `channel_endpoints`

- connection and organization;
- endpoint type and normalized address;
- display address/name;
- provider-native endpoint ID;
- default/enabled state;
- provider health/limit metadata where factual;
- row version and audit fields.

#### `channel_secrets`

- connection and organization;
- secret type;
- encrypted payload;
- key version;
- expiry/rotation metadata;
- never returned through read schemas.

#### `channel_sessions`

- connection and organization;
- session revision;
- encrypted secret reference;
- holder, lease expiry, fencing token, heartbeat;
- reconnect count, validity and observed state;
- row version and audit fields.

#### `channel_devices`

- connection/session and organization;
- provider-native device identifier;
- display/device metadata supported by provider;
- state and last seen;
- no fabricated device detail.

#### `contact_identities`

- organization and Contact;
- namespace, scope, normalized value;
- provider connection/endpoint references where applicable;
- verification/source timestamps;
- unique active identity ownership.

#### `channel_sync_checkpoints`

- connection/endpoint and organization;
- job reference;
- sync type, cursor/checkpoint, watermark/cutover;
- status, progress, error summary and row version.

#### `media_channel_references`

- media asset, organization and endpoint;
- provider media identifier;
- expiry, upload/download state and last verification;
- one media asset may have different provider references.

### 13.2 Existing-table additions

| Table | Additive change |
|---|---|
| `whatsapp_business_accounts` | Link to generic Meta connection while preserving current fields/APIs |
| `phone_numbers` | Link to generic endpoint; current WABA relation remains during compatibility period |
| `conversations` | Add endpoint and optional provider thread scope; backfill Meta endpoints |
| `messages` | Add endpoint/origin/provider occurrence/sync metadata without renaming physical `wamid` in place |
| `webhook_events` | Add provider connection/endpoint and ingress-source context |
| `media_assets` | Provider-specific cache references migrate to `media_channel_references` while existing Meta fields remain compatible until contract stage |

### 13.3 Migration stages

1. **Expand:** create generic tables and nullable links; no read-path change.
2. **Meta backfill:** one connection per current WABA/account context and one endpoint per existing phone number.
3. **Identity backfill:** create canonical WhatsApp identities from existing Contacts; report conflicts.
4. **Conversation backfill:** map every current conversation to its Meta endpoint in bounded batches.
5. **Message/event backfill:** add endpoint/origin context in resumable bounded jobs.
6. **Dual write:** existing Meta paths write old and generic links.
7. **Parity verification:** counts, foreign links, tenant boundaries and sampled ledger equivalence.
8. **Read switch:** generic connection/endpoint lookup becomes canonical behind flags.
9. **QR additions:** only after Meta parity, provider selection and owner authorization.
10. **Contract:** remove compatibility assumptions only in a separately approved milestone after rollback window.

### 13.4 Migration safety

- New revisions begin after `0035_notification_center`.
- No applied migration is modified or renumbered.
- High-volume table changes use expand/contract and production rehearsal.
- Backfills are restartable, observable and rate-limited.
- Foreign/unknown/incomplete mappings stop the switch and produce evidence.
- Migration downgrade never deletes historical conversation/message evidence.

Estimated impact remains 3–4 additive revisions, eight new tables and 5–7 existing-table alterations,
subject to exact implementation review without changing the approved logical contract.

## 14. Rollback strategy

### 14.1 General rule

Rollback means disabling new behavior and returning reads/writes to verified Meta paths. It does not
mean deleting imported messages, rewriting migration history or destroying audit evidence.

### 14.2 Stage rollback

| Stage | Rollback action |
|---|---|
| Generic schema deployed | Leave additive tables unused; old Meta path remains authoritative |
| Meta dual-write | Disable generic-read flag; reconcile failed generic writes |
| Generic read switched | Switch reads back to legacy WABA/phone-number joins; preserve generic rows |
| QR pairing pilot | Disable QR create/auth flags; stop new pairing; preserve encrypted state |
| QR inbound pilot | Stop session runtime; keep imported/live messages and mark connection disabled |
| QR outbound pilot | Disable QR send capability; preserve accepted/failed message evidence |
| Unified UI enabled | Hide provider controls through server flags; Meta Inbox remains available |

### 14.3 Rollback prerequisites

- Feature flags are server-owned and audited.
- Meta parity tests remain continuously runnable.
- Old columns/relations are not removed before rollback window closes.
- Queue drains and session shutdown are documented.
- Rollback does not trigger cross-provider resend.

## 15. Feature flag strategy

All flags default off in production and are organization/connection scoped where appropriate.

| Flag | Purpose |
|---|---|
| `omnichannel_connections_read` | Generic connection/endpoint read model |
| `omnichannel_connections_write` | Generic connection control plane mutations |
| `omnichannel_meta_dual_write` | Write Meta facts to generic links |
| `omnichannel_meta_read` | Read Meta through generic connection/endpoint authority |
| `omnichannel_identity_resolution` | Provider-neutral Contact identity resolver |
| `omnichannel_qr_provider` | Registers approved QR adapter for selected organizations |
| `omnichannel_qr_auth` | Enables pairing lifecycle |
| `omnichannel_qr_history` | Enables bounded history sync |
| `omnichannel_qr_inbound` | Enables live QR inbound |
| `omnichannel_qr_outbound` | Enables approved manual QR sends |
| `omnichannel_unified_ui` | Provider markers/filters and Channel Manager surfaces |
| `omnichannel_analytics` | Provider dimensions and connection metrics |

Flags cannot bypass RBAC, object authorization or provider capability checks. Flag changes are
permissioned and audited. QR outbound depends on provider, auth, inbound and security gates; it cannot
be enabled independently.

## 16. Production rollout plan

1. **Contract approval:** M13-00 Repository Validated and owner-approved.
2. **Prerequisite completion:** Reactivation Mission Control, Customer 360, Unified Inbox and
   Notification Center meet recorded Production Ready gates.
3. **Provider selection:** all Required provider criteria pass and owner approves the candidate.
4. **Generic schema:** deploy additive records with all flags off.
5. **Meta shadow/backfill:** dual-write and compare without changing operator behavior.
6. **Meta generic read:** limited organization/owner cohort; verify campaigns, templates, webhooks,
   Inbox, media and analytics parity.
7. **QR pairing pilot:** one controlled non-production/test connection; no outbound.
8. **QR history pilot:** bounded import; verify identity, ordering, attachments, unread and Timeline.
9. **QR live inbound pilot:** restricted operators; observe reconnect and health.
10. **QR manual outbound pilot:** restricted role and explicit connection; soak test duplicate safety.
11. **Unified UI cohort:** provider labels/filters and Channel Manager for trained operators.
12. **Connection-by-connection expansion:** monitor SLOs and incidents.
13. **Production acceptance:** security, performance, browser, accessibility, operator journey, DR and
    rollback evidence complete.

Every stage has a stop/go decision. Failure returns to the prior stable stage; rollout never skips
provider or security gates.

## 17. Disaster recovery considerations

### 17.1 Durable recovery data

Backups must include:

- connection/endpoint configuration;
- encrypted secret and session records;
- key version metadata;
- Contact identities;
- sync checkpoints;
- conversations/messages/status history;
- media metadata and object bytes;
- audit, notification and job evidence.

Redis, runtime memory and leases are rebuildable and are not the only source of truth.

### 17.2 Recovery scenarios

| Scenario | Required behavior |
|---|---|
| Database restore | Restore connections, identity and ledger consistently; resume only after integrity checks |
| Redis loss | Rebuild queues/cache/leases from durable state; no duplicate send |
| Session runtime node loss | Lease expires; new holder fences stale runtime |
| Object storage loss | Restore media; text/messages remain visible while media unavailable |
| Encryption-key outage | Fail closed; do not expose or overwrite secrets |
| QR provider outage | Keep Meta and CRM operational; preserve queued intent and health alerts |
| Meta outage | Keep QR/manual CRM operations independent where approved; no automatic route change |
| Total-site recovery | Start database/object storage, then API/queues, then Meta, then session runtimes connection by connection |

### 17.3 DR evidence

Before Production Ready:

- backup and restore rehearsal;
- key-availability and rotation rehearsal;
- Redis flush recovery;
- runtime failover/fencing test;
- session reattach or honest re-pair behavior;
- checkpoint resume;
- no-duplicate verification;
- documented RPO/RTO measured in the target environment.

Provisional targets require owner/operations ratification during the first deployment milestone; M13-00
does not invent target-host evidence.

## 18. Monitoring and observability

### 18.1 Required dimensions

Every metric/log/trace uses safe identifiers and includes where applicable:

- organization;
- provider type;
- connection public ID;
- endpoint public ID;
- queue/task type;
- session revision/runtime ID;
- request/correlation ID;
- outcome/error class.

Secrets, QR payloads, message bodies and raw customer identifiers are excluded.

### 18.2 Metrics

- connection state count by provider;
- health state and score;
- heartbeat age;
- active holder/lease age;
- reconnect attempts and exhaustion;
- re-authentication required count;
- live event lag;
- history sync lag/progress/failures;
- inbound-to-ledger and inbound-to-Inbox latency;
- outbound accepted-to-provider acknowledgement latency;
- send success/failure/ambiguous result;
- duplicate events suppressed;
- media download/upload failure and latency;
- queue depth/age by connection lane;
- identity conflicts and manual-resolution backlog;
- provider-specific availability.

### 18.3 Alerts

| Alert | Initial severity |
|---|---|
| Credential/session disclosure indicator | Blocker/P0 security incident |
| Cross-tenant access indicator | Blocker/P0 security incident |
| Duplicate outbound customer message | Blocker/P0 |
| Two active holders/fencing violation | Blocker/P0 |
| Re-authentication required | Actionable operator notification |
| Reconnect exhausted | Major/P1 |
| Event lag above SLO | Major/P1 |
| History sync stalled | Major/P2 unless live traffic affected |
| Media failure spike | Major/P2 |
| Provider outage | Provider-specific; other providers remain healthy |

### 18.4 Logs and diagnostics

Diagnostics are structured, permission-restricted and redacted. They may include state, timestamps,
versions, queue/lease facts and provider error classes. They may not include credentials, QR content,
session bytes, full message bodies or unrestricted customer PII.

## 19. Performance objectives

These are implementation acceptance targets, not current measurements.

| Measure | Objective |
|---|---:|
| Normal channel-control API p95 | < 300 ms on target stack |
| Meta webhook durable acknowledgement | Preserve existing < 200 ms design boundary |
| QR event durable handoff p95 | < 200 ms inside platform after runtime receives event |
| Live inbound to visible Inbox update p95 | < 2 seconds |
| Connection-health freshness | < 30 seconds while active |
| Critical connection alert | < 60 seconds |
| Runtime failover after holder loss | < 60 seconds when session remains valid |
| History sync effect on live p95 | No Major regression; live lanes remain priority |
| Duplicate customer sends in retry/failover suite | 0 |
| Unbounded list/history reads | 0 |

Each implementation milestone records FCP, LCP, interaction responsiveness, bundle/chunk size and
render stability for materially changed UI against the prior milestone under
`ENGINEERING_STANDARDS.md`.

## 20. Testing strategy

### 20.1 Contract and unit tests

- Adapter capability declaration and unsupported-action behavior.
- Native-to-canonical message/status/media normalization.
- Connection/session state transition matrix.
- Identity normalization and exact resolution.
- Provider/endpoint-scoped message idempotency.
- Retry/error classification.
- Health-state derivation.
- Secret redaction and serializer exclusion.

### 20.2 Repository/service/API integration tests

- Organization and object isolation for every new resource.
- RBAC matrix for read/manage/authenticate/credential/device/history/diagnostic actions.
- Deep-link, URL and ID manipulation.
- Optimistic concurrency and command idempotency.
- Meta backfill/dual-write/read parity.
- Contact identity conflict handling.
- Conversation endpoint scoping.
- History checkpoint resume and live cutover.
- Imported history does not create unread/notifications.
- Media download failure does not lose text.
- Notification lifecycle for health/re-auth failures.
- Analytics metric availability and provider dimensions.

### 20.3 Migration tests

- Upgrade from `0035` through every new revision.
- Downgrade where safe without historical data loss.
- Empty, representative and high-volume fixture backfills.
- Conflict/partial-backfill stop behavior.
- Index/query plans for endpoint/contact/message lookups.
- Upgrade/downgrade/re-upgrade.
- Legacy Meta API/read compatibility throughout expand stages.

### 20.4 Provider certification tests

- Pair, expiry, refresh, cancel, logout and remote logout.
- Session restart and reattach/re-pair.
- Single-holder/fencing rejection.
- Inbound duplicate and out-of-order events.
- Ambiguous outbound acknowledgement.
- Live reconnect and event replay.
- History pagination/checkpoint/resume.
- Media types/limits/failure.
- Provider throttling and terminal authentication failure.

### 20.5 Security tests

- Cross-organization connection/endpoint/conversation/job access.
- Pairing URL after permission removal/logout.
- Direct API replay of hidden/disabled actions.
- Credential read/export attempts.
- QR/session/log/trace/cache leak inspection.
- Bulk request with foreign objects.
- Runtime identity and lease takeover attempts.
- SSRF and malicious media cases.
- Dependency/SBOM/container scans for provider runtime.

### 20.6 Operator and host tests

For every materially changed workflow:

- Chrome, Edge and Firefox;
- desktop 1920×1080 and mobile approximately 390 px;
- keyboard-only completion and screen-reader evidence;
- first-use and repeated operator timing/click measurements;
- provider labels visible within five seconds;
- loading, empty, error, degraded, disconnected, re-authentication and long-content states;
- performance comparison with previous milestone;
- no unresolved Blocker or Major defect.

### 20.7 Failure and DR tests

- provider outage;
- Redis loss;
- worker/runtime crash;
- stale holder;
- database failover/restore;
- object storage/media outage;
- key unavailable;
- history sync interruption;
- rollout flag rollback;
- zero duplicate send assertion.

## 21. Acceptance criteria

Module 13 implementation is complete only when all criteria are evidenced:

1. Meta and approved QR connections operate concurrently and independently.
2. Failure of one connection/provider does not stop another.
3. Current Meta templates, campaigns, broadcasts, webhooks, conversations and analytics regressions pass.
4. QR pairing, reconnect, logout, session replacement, device state and health work through authorized audited commands.
5. Same authoritative WhatsApp identity resolves to one Contact across Meta and QR.
6. Provider identity uniqueness is enforced organization-scoped.
7. Different endpoints retain separate conversations under one Customer 360.
8. Inbox rows, thread headers, messages and mobile views identify provider and endpoint accessibly.
9. Customer 360 and Timeline aggregate provider facts without duplicate customer records.
10. Assignment, notes and tags reuse existing authorities.
11. Search groups provider matches under one customer result.
12. History sync is bounded, resumable, idempotent and creates no false unread/notification.
13. Attachments use existing media/object storage and preserve text on failure.
14. Retry/reconnect/failover tests produce zero duplicate customer sends.
15. Ambiguous acknowledgement never causes blind resend.
16. Templates/campaigns/bulk actions cannot route through QR.
17. Cross-provider continuation is never automatic.
18. Secrets/session material are encrypted, write-only and absent from logs/errors/metrics/audit.
19. Exactly one runtime holder controls each QR session.
20. Tenant, role, object, direct URL/API, cache and bulk security tests pass.
21. Every lifecycle/credential action has redacted immutable audit evidence.
22. Unsupported provider metrics render unavailable, not zero.
23. Channel alerts reuse the existing Notification Center.
24. OpenAPI/generated-client and migration history remain synchronized.
25. Upgrade, rollback, backup/restore and feature-disable procedures pass.
26. Mandatory browser, responsive, accessibility, UX, operator, security and performance gates pass.
27. Governance and remote Git HEAD are synchronized.

## 22. Gap analysis

### 22.1 Required before implementation or production enablement

| Gap | Why required | Closure point |
|---|---|---|
| Concrete QR provider not selected | Provider capabilities are external facts; implementation cannot assume IDs, sessions or replay | Before provider dependency or QR code is introduced |
| Provider legal/policy review | Unapproved connector could create business and account risk | Provider selection gate |
| Production key-management choice | QR sessions and Meta secrets require recoverable managed encryption | Before production credential/session storage |
| Exact Meta backfill/cardinality review | Current WABA/phone models are Meta-specific | M13-01 design review before migration |
| High-volume message/event migration plan with query evidence | Existing partitioned ledgers require safe expand/backfill/index work | Before first high-volume schema revision |
| Provider-scoped idempotency proof | Stable exactly-once effect is mandatory | Adapter certification and concurrent integration tests |
| Session runtime deployment topology | Single-holder, fencing, scaling and DR require target deployment facts | Before runtime milestone implementation |
| Contact identity conflict workflow | Conflicts must not cause unsafe auto-merge | Before identity resolver enablement |
| Target RPO/RTO ratification | DR goals require owner/operations acceptance | Before Production Ready |
| Recorded prerequisite milestones | Governance currently blocks Module 13 until named workflows are Production Ready | Before M13-01 starts |
| Separate owner instruction | M13-00 completion does not authorize engineering | Before M13-01 starts |

### 22.2 Recommended

| Gap | Benefit | Treatment |
|---|---|---|
| Step-up authentication for pairing/credential rotation | Reduces privileged-session takeover risk | Add to security milestone unless existing MFA/session policy already satisfies it |
| Formal provider support SLA | Improves incident recovery | Include in vendor selection where available |
| Dedicated provider conformance test harness | Makes adapter upgrades repeatable | Build within provider adapter milestone, not as a new product abstraction |
| Capacity model per QR connection | Supports runtime sizing | Establish during load/performance milestone |
| Operator training and runbook | Reduces pairing/re-auth mistakes | Required for rollout even if documentation is operational rather than code |

### 22.3 Future Enhancement

- Calls/call metadata.
- Presence and typing state.
- Message edit/delete synchronization.
- Advanced QR interactive content.
- Additional future-provider adapters.
- Cross-channel recommendation UI; any actual continuation remains explicit and audited.
- Expanded device administration beyond provider-supported factual state.

Future Enhancements do not block Module 13 and must not enter implementation without separate approval.

## 23. Known risks

| Risk | Severity | Mitigation/decision |
|---|---|---|
| Provider terms or policy are unacceptable | Blocker | Reject candidate; do not implement |
| Same physical number cannot safely coexist on Meta and QR | Blocker | Default to separate endpoints unless provider evidence and owner approval say otherwise |
| Provider lacks stable message identity | Blocker | Reject for outbound/live ingestion |
| Session cannot be safely restored or invalidated | Blocker | Reject or require explicit safe re-pair model |
| Split-brain runtime | Blocker | Lease/fencing and stale-holder tests |
| Wrong Contact merge | Blocker | Exact scoped identity; manual conflict |
| High-volume migration locks or corrupts ledger | Major/Blocker | Expand/backfill/query rehearsal and rollback |
| Reconnect storm overloads queues/provider | Major | Circuit breaker, bounded retry and per-connection lanes |
| History import creates unread/notifications | Major | Import origin, cutover and focused tests |
| QR metrics appear equivalent to official analytics | Major | Provider-specific availability semantics |
| QR dependency compromise | Blocker | Pinning, provenance, SBOM, scans and rapid disable flag |
| Secret appears in logs/telemetry | Blocker | Redaction, no-store and leak tests |
| UI hides action but API permits it | Blocker | Server RBAC/object authorization and direct API tests |
| Older Doc 07 Instagram exclusion conflicts with later owner scope | Governance inconsistency resolved | ADR-0020 permits future evaluation only; no implementation authorized |

## 24. External dependencies

- Owner-approved QR provider candidate and version.
- Provider test account, test number/device and controlled event history.
- Legal/policy/data-processing review.
- Provider SDK/container provenance and licensing.
- Production KMS/key-management and backup-key process.
- Target infrastructure for session runtime placement and scaling.
- MySQL production-like migration rehearsal environment.
- Redis/queue and object-storage target environment.
- Chrome, Edge, Firefox and representative operator accounts/data.
- Security review capacity and incident/runbook ownership.
- Completion of recorded prerequisite product workflows.
- Explicit owner instruction to start each implementation milestone.

## 25. Frozen implementation sequence

| Milestone | Scope | Start gate |
|---|---|---|
| M13-00 | ADR, provider criteria, threat/security/session/identity/API/DB/rollback/flag/rollout/DR/monitoring/performance/testing contract | Current documentation milestone only |
| M13-01 | Generic channel connection/endpoint/secret foundation and Meta backfill | Owner instruction plus prerequisites |
| M13-02 | Contact identity convergence and conflict handling | M13-01 Repository Validated |
| M13-03 | Session/connection durable control plane and runtime foundation | Approved provider and M13-02 |
| M13-04 | QR pairing, device status, health, reconnect and re-authentication | M13-03 security/runtime gates |
| M13-05 | QR inbound, history synchronisation and media | Certified provider event/history contract |
| M13-06 | Provider-neutral conversation send and approved QR manual outbound | Inbound/idempotency/ambiguous-send evidence |
| M13-07 | Unified Inbox, Customer 360, Timeline, assignment, notes, tags and search | Source APIs and identity complete |
| M13-08 | Provider-aware notifications, analytics and diagnostics | Unified operator sources stable |
| M13-09 | Security, performance, DR, browser, accessibility, operator and staged production validation | All implementation milestones Repository Validated |

Exactly one milestone is delivered per reviewed commit. M13-00 does not start M13-01.

## 26. M13-00 validation checklist

M13-00 reaches `Repository Validated` when:

- ADR-0020 and this document exist and agree.
- All 19 requested contract areas are explicit.
- Existing ChannelAdapter, CRM, ledger, media, notification, analytics, RBAC and audit reuse is named.
- No product source, migration, API contract, generated file, dependency or route changes exist.
- Provider choice is not fabricated and has objective pass/fail criteria.
- Older Instagram exclusion inconsistency is resolved additively through ADR-0020.
- Module 13 remains 0% implemented.
- Required, Recommended and Future Enhancement gaps are classified.
- Root governance records agree on lifecycle status, baseline, prerequisites and next-step boundary.
- Final target branch contains one Conventional Commit and remote HEAD is verified.

Host, browser, runtime and performance evidence are not applicable to a documentation-only milestone
and are not claimed. They become mandatory in the implementation milestones that change those
surfaces.

## 27. Engineering handoff rule

An engineer beginning M13-01 must not make an architectural choice that contradicts this contract.
When a concrete provider or production environment reveals a verified blocker, work stops and the
blocker is recorded. Any change to scope, abstraction, provider topology, identity semantics,
conversation ownership, security invariants, migration sequence or milestone order requires explicit
owner approval and an additive ADR before implementation continues.
