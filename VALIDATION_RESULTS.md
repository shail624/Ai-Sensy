# Validation Results

> Status vocabulary is restricted to `PASS`, `FAIL`, and
> `PENDING – Host Machine Validation`. This ledger records the latest applicable evidence and
> separates repository-verifiable engineering gates from target-host visual/commissioning evidence.

Last synchronized: `2026-08-05T03:21:50+05:30`.


## UI-TASTE-03B Reactivation Operational Hierarchy

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Work starts from `5c3414bed1802276e99a9b02605dbde8e1cdcc36` on `ui/taste-modernization`. |
| Architecture and reuse | PASS | Existing Reactivation/Task/KYC/Document/Audit/Timeline and shared UI authorities are recomposed; no duplicate aggregate, reminder, saved-view, SIM, Activation or design-system authority exists. |
| CRM-first hierarchy | PASS | Reactivation root and historical operational links resolve to the real CRM or existing Contact import workflow; foundation placeholder tabs/panels are absent. |
| Permission truth | PASS | KYC, Document and Report navigation uses the same existing permissions as route guards; no RBAC policy changed. |
| Tenant-safe pagination | PASS | Additive non-negative offset uses the existing organization predicates, stable ordering, count query and bounded evidence projection; focused pagination regression passes. |
| URL-backed work context | PASS | Search/status/label/owner/reminder/date/view/page and factual due/overdue/completed work views survive refresh/share without claiming server-shared saved views. |
| Mutation and audit preservation | PASS | Transition, case edit, assignment, Task reminder, Audit, Customer Timeline and optimistic-concurrency paths are unchanged and existing workflow regressions pass. |
| Verified defects | PASS | Placeholder hierarchy, permission disclosure, 200-card render, lost filter context, duplicate filter controls, terminal drag, malformed separator and stale gating copy are corrected. |
| Ruff / mypy | PASS | Ruff and strict mypy pass. |
| Backend tests | PASS | 4 focused Reactivation tests and all 980 backend tests pass in workflow `30953600784`. |
| OpenAPI / generated client | PASS | OpenAPI remains 200 paths with additive `offset`; generated TypeScript and drift checks pass. |
| Frontend gates | PASS | Production audit high threshold, ESLint, TypeScript, 35 Vitest files / 668 tests and production build pass. |
| Security gates | PASS | E2E TypeScript, Bandit, Python dependency audit and tracked-source vulnerability/secret/IaC scan pass. |
| Migration | PASS | No migration is applicable; migration head remains `0040_channel_sync_media_foundation` and existing roundtrip tests pass. |
| Performance | PASS | Pipeline page is bounded to 25 cards; main is 733.97/178.29 kB gzip and Reactivation route is 82.25/19.37 kB gzip. |
| Host validation | PENDING – Host Machine Validation | Authenticated representative-data visual/reference, screen-reader/device/browser matrix and production-scale query timing remain unproven. |
| Provider boundary | PASS | No provider evaluation/certification, WAHA/Evolution, QR runtime/session, live ingestion/history/media, provider dependency or production credential work exists. |
| Milestone boundary | PASS | Exact nineteen-file product/tracking boundary; Module 13 remains 44% and provider-dependent work remains blocked. |

## M13-06A Provider-neutral Sync & Media Persistence Foundation

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Work starts from `2386b50bc1110e88f346ddff028cf1e017ad2503` on `ui/taste-modernization`. |
| Provider-neutral boundary | PASS | Sync/media state, models and repositories contain no WAHA, Meta or concrete provider branch and no executable provider path. |
| Existing-authority reuse | PASS | References existing ChannelConnection, ChannelEndpoint, JobMetadata and MediaAsset records; no duplicate channel, job, message, media or customer authority exists. |
| Tenant isolation | PASS | Every repository query requires organization scope; foreign organization lookups return no record. |
| Secret handling | PASS | Opaque cursor/provider metadata recursively rejects plaintext credential-shaped fields. |
| Persistence integrity | PASS | Scope/provider identity uniqueness, bounded non-negative progress and transfer-state constraints fail closed. |
| Runtime/certification boundary | PASS | No provider is certified; no adapter, runtime, pairing, event consumer, history executor, media transfer or queue task exists. |
| Ruff / mypy | PASS | Ruff and strict mypy pass. |
| Backend tests | PASS | 18 focused channel/sync/media/migration tests and all 979 backend tests pass in workflow `30946554198`. |
| Frontend gates | PASS | Unchanged frontend passes production audit threshold, ESLint, TypeScript, Vitest and production build. |
| OpenAPI / generated client | PASS | OpenAPI remains semantically unchanged at 200 paths and generated TypeScript has no drift. |
| Migration | PASS | Additive `0040_channel_sync_media_foundation` upgrades, downgrades to `0039`, and upgrades again. |
| Dependency / security boundary | PASS | No dependency changed; Bandit and dependency audit pass. |
| Performance impact | PASS | No API query, worker, provider runtime or frontend bundle path changed; indexed bounded repository queries are the only new executable persistence surface. |
| Host validation | PENDING – Host Machine Validation | MySQL migration/rollback, production-scale query plans, real provider runtime, account/device evidence, monitoring, kill switch, recovery and certification remain unproven. |
| Milestone boundary | PASS | Only provider-neutral persistence/contracts/tests/status records changed; live M13-06 remains blocked. |

## M13-05 QR Pairing & Provider Runtime Foundation

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Work starts from `5d7ea154588418410611de4f568e978c2e3caba9` on `ui/taste-modernization`. |
| Provider-neutral runtime abstraction | PASS | Runtime metadata, lifecycle, events, health and pairing contracts contain no provider-specific branch and resolve execution only through the existing adapter seam. |
| Runtime registration/discovery/ownership | PASS | Thread-safe registry and tenant-scoped manager reject duplicate/conflicting runtime registrations, foreign organizations and unauthorized actors. |
| Session and persistence reuse | PASS | Runtime/pairing facts extend existing `ChannelSession` and `ChannelConnection`; no duplicate runtime, connection, credential, message or history authority exists. |
| Pairing lifecycle | PASS | UNPAIRED → PAIRING_REQUESTED → PAIRING_AVAILABLE with governed expiry/cancel/pair/active paths rejects illegal transitions and accepts no QR payload or token. |
| Runtime lifecycle/events/health | PASS | Factual lifecycle, event, health and capability observations persist with timezone-aware evidence and no live-provider claim. |
| Heartbeat, restart and recovery | PASS | Existing session heartbeat, lease/fencing, restart policy and recovery metadata are reused; stale holders and invalid fencing tokens fail closed. |
| Pairing expiry safety | PASS | Availability cannot be accepted after expiry, provider TTL is bounded, and expiry sweeps validate and limit batches to 1–1000 locked rows. |
| Security boundary | PASS | Tenant isolation, RBAC, disabled-by-default flags, constrained reason codes, secret-reference-only storage and Audit redaction are enforced. |
| Audit coverage | PASS | Runtime registration/ownership/lifecycle/health/capability/heartbeat/recovery and every pairing transition emit safe existing Audit evidence. |
| Ruff / mypy | PASS | Ruff and strict mypy pass. |
| Backend tests | PASS | 20 focused channel/session/runtime/migration tests and all 976 backend tests pass in workflow `30933007710`. |
| Frontend gates | PASS | Production audit high threshold, ESLint, TypeScript, 34 Vitest files / 661 tests and production build pass; frontend source is unchanged. |
| OpenAPI / generated client | PASS | Application and committed OpenAPI are semantically identical at 200 paths and generated TypeScript has no drift. Current dependency resolution exposes a pre-existing JSON key-order-only `--check` mismatch on the untouched M13-04 baseline; M13-05 adds no route/schema. |
| Migration | PASS | Additive `0039_qr_pairing_provider_runtime_foundation` upgrades, downgrades to `0038`, and upgrades again without destructive existing-schema changes. |
| Bandit / dependency / source scan | PASS | Bandit high-severity, Python dependency, frontend/browser audit thresholds and tracked-source vulnerability/secret/IaC scan pass. |
| Bundle impact | PASS | No frontend source changed; main remains 733.62/178.16 kB gzip, CSS 49.90/9.90 kB gzip and Operational Dashboard 31.96/8.61 kB gzip; existing >500 kB warning remains. |
| Host validation | PENDING – Host Machine Validation | Target-host MySQL, real multi-node runtime/lease contention, provider certification, runtime supervisor/monitoring, KMS custody and representative tenant/RBAC/flag rollout remain unproven. |
| Milestone boundary | PASS | Exact sixteen-file implementation boundary before governance; M13-01–M13-04 remain authoritative and M13-06, provider adapters, QR image/login, sync, messaging, webhooks, routing and UI are absent. |

## M13-04 QR Session Manager Foundation

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Work starts from `9d8f379f09719820c847be2b7c7df301e1617977` on `ui/taste-modernization`. |
| Provider-neutral session abstraction | PASS | Lifecycle, restart, health and capability contracts contain no Meta, WhatsApp or QR-specific branch and no provider adapter/runtime is registered. |
| Persistence reuse | PASS | One additive `channel_sessions` table links existing organization-owned `ChannelConnection`, optional endpoint/credential references and introduces no duplicate connection, credential, message or history storage. |
| Lifecycle and state transitions | PASS | REGISTERED → INITIALIZING → WAITING_FOR_PAIRING → ACTIVE → DEGRADED → RECONNECTING → PAUSED → EXPIRED → TERMINATED plus governed recovery paths reject illegal or terminal transitions. |
| Registration, discovery and ownership | PASS | Tenant-scoped repository/service registration, discovery and owner validation fail closed for foreign organizations and unauthorized users. |
| Health, heartbeat and expiration | PASS | Factual health/observation, heartbeat, lease expiry and explicit session expiry persist with timezone-aware evidence and no live-provider claims. |
| Recovery and restart policy | PASS | Provider-neutral recovery metadata, attempt counters, next-attempt facts and NEVER/ON_FAILURE/ALWAYS restart policies are durable and validated. |
| Locking and concurrency | PASS | Database leases, holder runtime ids, fencing tokens and optimistic row versions reject concurrent/stale runtime commands and support safe release/reacquisition. |
| Capabilities and provider metadata | PASS | Sessions reference normalized capability ids and existing provider/connection metadata; no new provider authority or provider-specific table exists. |
| Security boundary | PASS | Secret-shaped metadata is rejected, only existing credential references may be stored, Audit payloads serialize safe facts and no provider secret/API exposure exists. |
| Feature flags and RBAC | PASS | Disabled-by-default session read/write flags and `channels:read/manage/diagnose` permissions enforce organization-scoped discovery and mutation. |
| Ruff / mypy | PASS | Ruff passes; strict mypy reports no issues across 279 source files. |
| Backend tests | PASS | 7 focused session/migration tests and all 970 backend tests pass in workflow `30913610932`. |
| Frontend gates | PASS | Production audit high threshold, ESLint, TypeScript, 34 Vitest files / 661 tests and production build pass; frontend source is unchanged. |
| OpenAPI / generated client | PASS | OpenAPI 3.1 remains 200 paths; generated TypeScript authority regenerates without drift. |
| Migration | PASS | Additive `0038_qr_session_manager_foundation` upgrades, downgrades to `0037`, and upgrades again without destructive existing-schema changes. |
| Bandit / dependency audit | PASS | Bandit high-severity gate and Python dependency audit pass; frontend production audit retains two pre-existing moderate React Router advisories and no high/critical failure. |
| Bundle impact | PASS | No frontend source changed; main remains 733.62/178.16 kB gzip, CSS 49.90/9.90 kB gzip and Operational Dashboard 31.96/8.61 kB gzip; existing >500 kB warning remains. |
| Host validation | PENDING – Host Machine Validation | Target-host MySQL migration/rollback, real multi-node lease/fencing contention, runtime heartbeat/expiration/restart/recovery monitoring, KMS secret-reference custody and representative tenant/RBAC/flag rollout remain unproven. |
| Milestone boundary | PASS | Exact eleven-file implementation boundary before governance; M13-01–M13-03 behavior is preserved and M13-05, provider adapters/runtime, QR/login, sync, messaging, webhooks, routing and UI are absent. |

## M13-03 Persistent Channel Connections & Endpoint Records

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Work starts from `283ebe83b53a510ce671f150bfe14fe38a5292f6` on `ui/taste-modernization`. |
| Provider-neutral persistence | PASS | Organization-owned connection, endpoint and credential records contain no Meta, QR or provider-specific schema/branch. |
| Tenant and organization isolation | PASS | Repository/service reads and writes require the actor organization and foreign identifiers disclose no record. |
| Immutable provider identifiers | PASS | Persisted connection and endpoint provider identifiers reject mutation; provider-neutral internal UUID ownership remains stable. |
| Lifecycle, health and metadata | PASS | Desired/observed state, factual health, provider/configuration/endpoint metadata, Audit references and timestamps persist without runtime/provider claims. |
| Soft delete and optimistic locking | PASS | Connections/endpoints/secrets carry deletion evidence and row versions; stale commands fail and logical connection deletion cascades endpoint deletion and credential revocation. |
| Encrypted credentials | PASS | AES-GCM sealed storage keeps ciphertext/nonce/tag only, rejects secret-shaped metadata, redacts representations and supports key/secret versions, rotation lineage, expiry, access evidence and revocation. |
| Secret exposure boundary | PASS | No public API route/schema was added; plaintext is absent from database metadata, Audit payloads, OpenAPI and generated client. |
| Feature flags | PASS | Existing disabled-by-default `omnichannel_connections_read/write` gates fail closed and preserve organization precedence. |
| Ruff / mypy | PASS | Ruff passes; strict mypy reports no issues across 275 source files. |
| Backend tests | PASS | 4 focused persistence regressions and all 965 backend tests pass in workflow `30907651227`. |
| Frontend gates | PASS | Production audit high threshold, ESLint, TypeScript, 34 Vitest files / 661 tests and production build pass; frontend source is unchanged. |
| OpenAPI / generated client | PASS | OpenAPI 3.1 remains 200 paths; generated TypeScript authority regenerates without drift. |
| Migration | PASS | Additive `0037_persistent_channel_connections` upgrades, downgrades to `0036`, and upgrades again with the three new tables and no destructive existing-schema change. |
| Bandit / dependency audit | PASS | Bandit high-severity gate and Python dependency audit pass; frontend production audit has no high/critical failure and retains two pre-existing moderate React Router advisories. |
| Bundle impact | PASS | No frontend source changed; main remains 733.62/178.16 kB gzip, CSS 49.90/9.90 kB gzip and Operational Dashboard 31.96/8.61 kB gzip; existing >500 kB warning remains. |
| Host validation | PENDING – Host Machine Validation | Target-host MySQL migration/rollback, production KMS/key custody, representative multi-tenant persistence, restore/retention policy and staged flag rollout remain unproven. |
| Milestone boundary | PASS | Exact nine-file implementation boundary before governance; M13-01/M13-02 behavior is preserved and M13-04, provider adapters/runtime, QR, sync, messaging, webhooks, routing and UI are absent. |

## M13-02 Customer Identity Resolution

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Work starts from `c238bfa55d050310f865771be4654b90a5a993d2` on `ui/taste-modernization`. |
| Exact canonical identity | PASS | Organization/namespace/scope/value keys resolve only to the canonical Contact; fuzzy/profile-name matching is absent. |
| Immutable aliases and endpoint identities | PASS | Unique tenant-scoped ownership, provider/endpoint metadata and immutable links are enforced. |
| Ambiguity/conflict handling | PASS | Multiple/no authoritative candidates create a tenant-scoped review item; no automatic merge or ownership move occurs. |
| Recommendation decisions | PASS | Pending recommendations support explicit approve/reject with optimistic concurrency and never execute a merge. |
| RBAC, tenant and feature flag | PASS | Contact permissions, organization predicates and disabled-by-default `omnichannel_identity_resolution` fail closed. |
| Audit and Timeline | PASS | Link, conflict, recommendation and decision facts use existing Audit and Contact Timeline authorities. |
| Ruff / mypy | PASS | Ruff passes; strict mypy reports no issues across 271 source files. |
| Backend tests | PASS | 22 focused identity/contact/channel tests and all 961 backend tests pass. |
| Frontend gates | PASS | Production audit, ESLint, TypeScript, Vitest and production build pass; application source is unchanged. |
| OpenAPI / generated client | PASS | OpenAPI 3.1 has 200 paths and generated TypeScript authority is current. |
| Migration | PASS | `0036_customer_identity_resolution` upgrades, downgrades to `0035`, and upgrades again with all three tables present. |
| Bundle impact | PASS | Generated contract only; CSS, main and lazy-route application bundles remain unchanged and the existing >500 kB warning remains. |
| Host validation | PENDING – Host Machine Validation | Target-host MySQL migration, representative operator review, production feature-flag rollout and runtime/security commissioning remain unproven. |
| Milestone boundary | PASS | M13-01 is unchanged and M13-03/provider/runtime/QR/UI work is absent. |


## M13-01 Generic Channel Foundation

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Work starts from `8b878bdbd21877cf3f77eac5e9bb209d6b6022be` on `ui/taste-modernization`. |
| Existing adapter reuse | PASS | Provider metadata resolution delegates to the existing `get_adapter`; no second adapter factory or provider-specific service exists. |
| Provider/capability registries | PASS | Thread-safe registries reject conflicting metadata, expose factual capabilities and remain empty by default. |
| Communication intent and policy | PASS | Immutable organization-aware contracts cover channel, purpose, origin, bulk and required capabilities; policy evaluation fails closed with explicit reasons. |
| Health, lifecycle, metadata and enums | PASS | Immutable provider-independent states validate connector identity, timezone-aware observation, score and retry facts without inventing provider health. |
| Shared validation | PASS | Connector, text, organization, timestamp, score and capability validation use the existing channel error boundary. |
| Feature flags | PASS | `omnichannel_connections_read/write` use existing `feature_flags`; absent is off and organization rows override global rows. |
| Dependency injection | PASS | Cached empty foundation and request-scoped flag resolver are wired through existing API dependency conventions without startup/provider side effects. |
| Focused validation | PASS | Ruff, strict mypy and 46 channel/config tests pass, including seven new foundation regressions. |
| Full backend suite | PASS | 955 pytest tests pass in 260.89 seconds; strict mypy reports no issues across 263 source files. |
| Frontend repository gate | PASS | Unchanged frontend passes production audit high threshold, ESLint, TypeScript, 34 files / 661 tests and production build. |
| Bundle impact | PASS | No frontend source changed; main remains 733.62/178.16 kB gzip and Operational Dashboard remains 31.96/8.61 kB gzip. |
| Migration/API/dependency boundary | PASS | Migration remains `0035_notification_center`, OpenAPI remains 193 paths, generated client and packages are unchanged. |
| Provider/runtime boundary | PASS | No QR/Meta runtime, pairing, session, history, live messaging, provider adapter or provider dependency exists. |
| Shared-authority boundary | PASS | Contact, Inbox, Customer 360, Timeline, Notification Center, Analytics, media, message and audit authorities are unchanged. |
| Exact changed-file boundary | PASS | Seven backend/test files only before governance; no migration, API v1, provider package, model table or frontend file. |
| Host/production evidence | PASS | Correctly limited to Repository Validated; no provider, host workflow, runtime performance, DR, Production Ready or Released claim. |
| Remaining contract gap | PASS | Persistent connection/endpoint/secret records and Meta backfill are explicitly recorded as Required and unimplemented. |
| Milestone boundary | PASS | M13-02 and all provider/runtime work remain unstarted. |

## M13-00 Architecture & Provider Lock

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Documentation work starts from `7e503a3f2e1d35d54548d9d8fe95e82591e26be1` on `ui/taste-modernization`. |
| Architecture decision | PASS | ADR-0020 is accepted and freezes one existing capability-based ChannelAdapter, one Contact/CRM/message ledger, endpoint-scoped conversations, independent provider failure domains and no automatic cross-provider failover. |
| Complete implementation contract | PASS | Design Document 33 covers all requested architecture, capability, provider, threat, security, session, identity, API, database, rollback, flag, rollout, DR, monitoring, performance, testing, acceptance, risk and dependency areas. |
| Existing-authority reuse | PASS | Contract names existing Meta adapter, ChannelAdapter, canonical models, Conversation/Message/Event/Send/Media services, Inbox, Customer 360, Timeline, Notification Center, Analytics, RBAC, tenant and Audit authorities; no duplicate service family is approved. |
| Provider capability matrix | PASS | Meta official capabilities and QR human/session/history/media capabilities are separated; templates, campaigns, broadcasts and bulk automation cannot route through QR. |
| QR provider gate | PASS | No vendor is fabricated. Required pass/fail evidence covers legal/policy, stable IDs, replay, ambiguous acknowledgement, secure session lifecycle, history, media, health, errors, isolation, support and testability. |
| Threat and security architecture | PASS | Assets, trust boundaries and spoofing/tampering/repudiation/disclosure/DoS/elevation/cross-tenant/split-brain/duplicate/merge/media/supply-chain threats have required controls and Blocker criteria. |
| Session lifecycle | PASS | Durable desired/observed states, legal transitions, single-holder lease, fencing, heartbeat, bounded reconnect, re-authentication and recovery rules are explicit. |
| Identity resolution | PASS | Exact organization/namespace/scope/value resolution, one identity-to-Contact ownership, no fuzzy auto-merge and restricted conflict handling are frozen. |
| API contract | PASS | Additive connection, lifecycle, QR-auth, endpoint/device/health, history and conversation-send resources follow existing `/api/v1`, UUID, RFC 7807, pagination, idempotency, concurrency and generated-contract conventions. |
| Database and migration contract | PASS | Eight approved generic records, additive existing-table links and expand/backfill/dual-write/verify/switch/contract stages are explicit; migration remains `0035` in M13-00. |
| Rollback, flags and rollout | PASS | Disabled-by-default server flags, Meta parity-first rollout, controlled QR pilots, explicit stop/go decisions and non-destructive rollback are defined. |
| DR, monitoring and performance | PASS | Durable/rebuildable state, recovery scenarios, safe dimensions/alerts and provisional latency/health/failover/zero-duplicate objectives are documented without claiming target-host measurements. |
| Testing and acceptance | PASS | Unit, API, migration, provider certification, security, browser/accessibility/operator, failure/DR suites and 27 final acceptance criteria are mapped to future executable milestones. |
| Gap analysis | PASS | Missing facts are classified as Required, Recommended or Future Enhancement; provider selection, legal review, production key management, migration evidence, runtime topology, idempotency, identity conflict handling, RPO/RTO, prerequisites and owner instruction are explicit Required gates. |
| Documentation consistency | PASS | The existing ChannelAdapter remains the only adapter abstraction. ADR-0020 additively resolves older Doc 07's Instagram exclusion only for future separately approved evaluation; no future provider is implemented or scheduled inside M13. |
| Product/change boundary | PASS | Diff is limited to ADR/design/governance Markdown. No backend, frontend, API, migration, generated contract, dependency, route, queue, runtime or deployment file changes. |
| Existing application evidence | PASS | Product source is unchanged, so existing `0035` / 193-path / 948-backend-test / 661-frontend-test baseline remains the applicable evidence; application suites are not falsely re-run or re-attributed to M13-00. |
| Host and production evidence boundary | PASS | M13-00 is correctly limited to `Repository Validated`; it claims no provider, browser, screenshot, operator, runtime performance, DR, Host Validated, Production Ready or Released evidence. |
| Milestone boundary | PASS | M13-01 and all implementation milestones remain unstarted and require a separate owner instruction. |

## UI-TASTE-03A operator-first Dashboard

| Validation item | Status | Latest evidence |
|---|---|---|
| Latest Git baseline | PASS | Work begins from `7d826987c272d28038663ba9cb15c832c37e2b02` on `ui/taste-modernization`; no completed work is recreated. |
| Operator question coverage | PASS | Existing authorized sources answer attention, blocked customers, pending KYC, SIM SLA risk, overdue Activation, Campaign action, unread replies, blocked Templates, agent workload and today KPI change. |
| Source truth and boundaries | PASS | Dashboard composes existing APIs only; no backend, duplicate projection, fake count, local persistence or generated-contract edit exists. Failed sources are disclosed and never rendered as zero. |
| Permissions and tenant behavior | PASS | Queries are enabled only when their existing read permission is present; source APIs retain tenant/RBAC authority and deep links. |
| Loading, empty and error states | PASS | Accessible skeletons, factual empty states, partial-source warning, source-specific retry and permission-empty state are implemented. |
| Accessibility and responsive contracts | PASS | Semantic links/buttons/headings/tables, focus-visible treatment, live loading status, touch-safe actions and desktop-table/mobile-card transformations are present; existing layout regressions pass. |
| Decision rules | PASS | Four focused tests cover blockers, KYC/Campaign/Inbox/Template action classification, agent aggregation and metric-aware KPI direction. |
| Full frontend gates | PASS | Production audit, ESLint and TypeScript pass; 34 Vitest files / 661 tests pass; Vite production build passes. |
| Verified bug fixes | PASS | Strict typing caught and fixed KPI sentiment widening; full-suite regression caught and fixed loss of Live Chat/New Campaign link semantics. |
| Performance | PASS | Dashboard is lazy-split to 31.96 kB / 8.61 kB gzip; main chunk improves from 747.91 kB to 733.62 kB, though the existing >500 kB warning remains. |
| Migration/API/dependency boundary | PASS | Migration remains `0035_notification_center`; OpenAPI remains 193 paths; no generated client or package dependency changes. |
| Authenticated representative-data visual/reference review | PENDING – Host Machine Validation | Repository/jsdom/build gates cannot prove final density, long-content overflow, contrast, screen-reader behavior or approved-reference comparison on target devices. |
| Milestone boundary | PASS | Only Dashboard composition, conditional-query support, focused tests and required governance evidence are included; Reactivation redesign is absent. |

## UI-TASTE-02 shared enterprise design system

| Validation item | Status | Latest evidence |
|---|---|---|
| Starting baseline and branch | PASS | Implementation starts from `9043fe03a80b682a010304c88c5d29d8ec77d1fa` and targets `ui/taste-modernization`; the original CORE-09 lineage remains `62d4daa50617e2e0c8fff9f5ec9a514848a77f98`. |
| Shared architecture | PASS | Existing React/Tailwind architecture is extended in place with named radius tiers, forward-ref form controls, toolbar/filter composition, cursor pagination, and refinements to existing Button/Card/PageHeader/PageContainer primitives; no parallel design system exists. |
| Product workflow preservation | PASS | Contacts URL filters/import/bulk flow, Inbox quick views/search shortcut/saved views/bulk mutations/thread flow, and Notification polling/read/team/deep-link behavior are unchanged. |
| Sidebar, navigation and contract boundary | PASS | Sidebar, TopNav structure, command palette, mobile navigation, routes, permissions, backend, migration `0035`, 193-path OpenAPI, generated client, and dependencies are unchanged. |
| Accessibility and responsive contracts | PASS | Shared controls retain labels, forward refs, focus-visible rings, invalid/disabled/busy semantics and mobile targets; existing 21 layout, 24 Inbox, 4 Contacts toolbar and 3 Notification Center tests pass. |
| Focused shared-primitive regression | PASS | Three new tests cover semantic labels/help/errors, invalid state, action slots, cursor pagination disabled/callback behavior, and loading-button accessible name/`aria-busy`. |
| Lint, typecheck and full frontend suite | PASS | ESLint passes; `tsc --noEmit` passes; 33 Vitest files and 657 tests pass. |
| Production build and bundle measurement | PASS | Vite transforms 2,599 modules and builds successfully; CSS is 49.39 kB / 9.79 kB gzip and the main application chunk is 747.91 kB / 181.62 kB gzip. The known >500 kB warning remains recorded debt. |
| Production dependency boundary | PASS | `npm audit --omit=dev --audit-level=high` reports only two moderate React Router advisories and no high/critical production finding. Combined development/build tooling reports 11 transitive findings and requires a separate upgrade milestone. |
| Originality and scope | PASS | Implementation is original, uses existing semantic product tokens and Lucide icons, imports no reference code/assets/branding/layout, adds no fake data/metric/placeholder, and introduces no heavy animation library. |
| Authenticated representative-data visual and reference comparison | PENDING – Host Machine Validation | Source review and jsdom tests cannot prove final visual density, long-content overflow, screen-reader behavior, or desktop/tablet/mobile comparison against the approved reference library. Owner/host review is required before Priority 2. |
| Milestone boundary | PASS | Only Priority 1 shared-system work and required governance evidence are included; Dashboard and all other Priority 2 screen redesign work remain absent. |

## CORE-07 Customer 360 domain convergence

| Validation item | Status | Latest evidence |
|---|---|---|
| One customer identity and source ownership | PASS | The existing public Contact id joins persisted source authorities; Customer 360 introduces no snapshot, duplicate model, local record, synthetic metric, or write authority. |
| Conversations and messages | PASS | Existing Inbox repository/service/API and Message ledger accept an exact tenant-scoped Contact filter; unknown/foreign identifiers disclose no records and malformed ids fail through shared validation. |
| Reactivation and Vi facts | PASS | Existing pipeline/case/Task/note/KYC/SIM/Activation contracts provide real status, labels, owner, reminders, SLA, reservation, family-plan, conversion and immutable evidence facts. |
| Documents, Tasks, Campaigns, Audit and Timeline | PASS | Existing permission-scoped sections and source deep links are reused; Timeline and Audit remain views over their existing immutable authorities. |
| RBAC, tenant isolation and read-only behavior | PASS | Backend exact-contact tenant regressions and frontend denied/error/read-only regressions pass; tag mutations are hidden without `contacts:write`. |
| UI states, accessibility and responsive behavior | PASS | Focused tests cover persisted composition and honest empty/error/denied states; authenticated 1280×720, 768×1024 and 390×844 review found no page overflow or console errors and verified Arrow-key tab navigation. |
| Reference and originality review | PASS | Paired `0001`, `0008`, `0010` and `0048` approved captures were reviewed for contextual hierarchy, density, tabs and activity patterns; no proprietary code, asset, branding, wording, exact styling or reference file is shipped. |
| Focused and full tests | PASS | Focused backend APIs pass 21/21 and Customer 360 passes 5/5; canonical suites pass 945/945 pytest and 651/651 Vitest. |
| Migration and API boundary | PASS | Migration remains the single `0034_reactivation_crm` head; OpenAPI remains 3.1.0 with 189 paths and regenerated TypeScript drift is clean. |
| Deployed runtime | PASS | Static/application/security/release steps passed; after aligning the stale E2E tab assertion, the rebuilt frontend/runner passed Playwright 1/1 in 11.1 seconds against fresh MySQL/Redis/Celery, with p95 10.4 ms across 30 reads. |
| Verified defect regressions | PASS | Tests cover exact-contact history, foreign/malformed filters, permission-safe tag actions, factual/no-placeholder composition and the converged production tab contract. |
| Milestone boundary | PASS | No CORE-08 approval engine, migration, endpoint family, duplicate authority, fake data, copied reference content, or completed-module rebuild was introduced. |

## CORE-05 lightweight Reactivation CRM correction

| Validation item | Status | Latest evidence |
|---|---|---|
| Primary status and labels | PASS | Exactly one of nine constrained current statuses and unique multi-label membership pass model/service/migration tests; current status/label concepts do not overlap and immutable legacy stage events are retained. |
| Follow-up and Release dates | PASS | Follow-up and Name Change require their governed dates, date-bearing labels require an assigned owner, timezone-aware inputs normalize to UTC, and removing a label cannot submit a stale date. |
| Reminder lifecycle | PASS | Existing TaskService owns create/update/Complete/Snooze/Reschedule, keeps overdue work open until resolved, enforces row versions, and records immutable Task, Audit and Customer Timeline evidence. |
| Due delivery and infrastructure | PASS | The existing Celery beat/worker topology registers 25 application tasks; the bounded due adapter uses `scheduler.tick`, marks durable assigned-user due evidence, and the deployed MySQL/Redis/Celery stack is healthy. |
| RBAC, tenant isolation and concurrency | PASS | Permission-scoped Reactivation/Task endpoints, organization-scoped joins/filters, ownership validation, stale versions and duplicate/idempotent commands fail closed in focused and full suites. |
| Real persisted UI | PASS | Existing board/list/drawer consume only generated API contracts and real projections; status/label/assignee/reminder-date filters, due counters, chips, pointer/keyboard movement and Complete/Snooze/Reschedule survive server refreshes. |
| UI states, accessibility and responsive behavior | PASS | Focused tests cover loading, empty, recoverable error, permission/read-only boundaries, labelled controls/dialogs, keyboard movement, desktop dense table/Kanban and mobile list/drawer transformation. |
| Authenticated representative-data visual review | PENDING – Host Machine Validation | Final target-browser/device and screen-reader review requires a host account with representative labels, due/overdue Tasks, users, and cases; repository component and deployed browser gates pass. |
| Reference and originality review | PASS | Four paired approved `_full.png`/`_viewport.png` workflows were reviewed for filters, chips, staff selection, forms and responsive hierarchy; no reference code, asset, branding, text, exact styling or file is shipped. |
| Focused and full tests | PASS | Focused Reactivation/API/KYC backend tests pass 11/11 and Reactivation/Tasks/KYC frontend tests pass 25/25; canonical deployed suites pass 943/943 pytest and 646/646 Vitest. |
| Migration and API boundary | PASS | One additive head `0034_reactivation_crm` advances 34 linear revisions; OpenAPI advances only from 188 to 189 paths (+1), generated contracts/drift pass, and the backend image registers 25 tasks. |
| Verified defect regressions | PASS | Tests cover stale date serialization, versioned reminder actions, owner-only reminder reassignment, server-required Not Required reasons, UTC normalization, populated-data migration rollback, updated image contract and five-entry beat schedule; no test or permission was weakened. |
| Milestone boundary | PASS | No heavy SIM fulfilment/Activation workspace, parallel reminder/notification store, fake data, local-only state, completed-module rebuild, migration downgrade, API removal, reference asset, or `.reference/aisensy/` content was introduced. |

## CORE-04 KYC operations

| Validation item | Status | Latest evidence |
|---|---|---|
| Creation prerequisites and governed checks | PASS | Eligible document-ready Reactivation cases create one tenant-scoped KYC case idempotently; holder, Delhi-presence and active-number checks plus invalid/stale commands pass service/API tests. |
| Protected document checklist | PASS | Aadhaar/PAN checklist entries reference verified same-tenant/same-contact Document Center records; protected-access denial passes and no schema/API/UI/audit field stores identity numbers. |
| Appointment lifecycle | PASS | Creation reuses idempotent TaskService; reschedule, completion and cancellation reuse existing Task commands, immutable events, audit and Customer Timeline evidence. |
| Reviewer/manager authority separation | PASS | Requester cannot review; manager must differ from requester and approved reviewer; structured rejection/information reasons, approval prerequisites and immutable decision history pass. |
| Reactivation handoff | PASS | Only valid manager approval advances the existing case through `kyc_pending` to `verification` using the CORE-02 transition authority, optimistic concurrency and immutable stage/audit/Timeline evidence. |
| RBAC and tenant isolation | PASS | KYC/document/task read-write-decide-approve permissions and cross-tenant denial pass focused service/API tests; UI exposes permission-aware read-only/denied states. |
| Customer 360 and shared reuse | PASS | Existing Reactivation drawer, protected DocumentWorkspace, Task lifecycle, Customer 360 section, Contacts/User directory, Audit, Timeline, RBAC, SLA and design-system states are extended; no parallel authority exists. |
| UI states, accessibility and responsive behavior | PASS | Focused tests cover factual queue/detail, checklist/actions, loading, empty, error, read-only, accessible labels/tabs/drawer, desktop table and mobile-card transformation, and no mock fallback. |
| Authenticated representative-data browser review | PENDING – Host Machine Validation | The local protected route and anonymous redirect were verified; a target-host account with representative KYC/protected-document data and final desktop/tablet/mobile browser matrix is required for authenticated visual/WCAG sign-off. |
| Reference and originality review | PASS | Four paired approved `_full.png`/`_viewport.png` workflows were inventoried for density, filters, forms, action placement and layered workspaces; no proprietary code, asset, branding, exact styling, wording or reference file is shipped. |
| Focused and full tests | PASS | 24 focused backend and 33 focused cross-feature frontend tests pass; canonical suites pass 940/940 pytest and 646/646 Vitest. |
| Migration and API boundary | PASS | One additive head `0033_kyc_operations` fills verified reference/Task/reason constraints; OpenAPI advances only from 184 to 188 paths (+4) and generated TypeScript drift is clean. |
| Milestone boundary | PASS | No SIM fulfilment, Activation Queue, fake operational data, plaintext identity number, duplicate document/task/approval/timeline system, or completed-module rebuild was introduced. |

## CORE-03 Reactivation pipeline

| Validation item | Status | Latest evidence |
|---|---|---|
| Persisted pipeline and factual counts | PASS | Tenant-scoped joined projection returns all fifteen approved stage counts and bounded cards from real cases, contacts, owners, eligibility, tasks, documents, SLA, reservation, family, and conversion facts; no fixture fallback exists. |
| Governed transitions and concurrency | PASS | All permitted/rejected lifecycle moves pass exact matrix tests; drag, keyboard, and drawer actions use the CORE-02 transition service, server-published targets, idempotency, and `row_version`; stale writes return conflict. |
| RBAC and tenant isolation | PASS | Read/write/transition actions are permission-aware; cross-tenant pipeline, note, case, owner, task, and document access fails closed in service/API tests. |
| Assignment and immutable evidence | PASS | Assignment/number edits reuse the versioned CORE-02 update authority; transitions and notes retain immutable stage/audit/Customer Timeline evidence. |
| Shared module reuse | PASS | Existing Contacts/User directory, Customer 360, Tasks/reminders, Documents, Audit, Timeline, SLA, Modal, router, and design system are extended in place; no completed module was rebuilt. |
| UI states and accessibility | PASS | Focused tests cover loading, empty, error, permission, responsive board/list, pointer/keyboard movement, drawer labelling/focus, and no-mock guarantees. Authenticated 1280×720, 768×1024, and 390×844 review found no page-level horizontal overflow. |
| Reference and originality review | PASS | Four paired approved `_full.png`/`_viewport.png` workflows were inventoried for shell, filters, density, modal/drawer and responsive patterns; no proprietary code, asset, branding, exact styling, wording, or reference file is shipped. |
| Focused CORE-03 tests | PASS | 6 focused backend service/API tests and 9 focused Reactivation/foundation frontend tests pass; the full suites pass 938/938 and 641/641. |
| Migration/API boundary | PASS | Migration remains single head `0032`; verified projection/note gaps add only 2 paths, advancing OpenAPI from 182 to 184 with generated TypeScript drift clean. |
| Milestone boundary | PASS | No KYC operations workspace, SIM fulfilment UI, Activation Queue, migration, mock lead card, fake count, local-only workflow state, or duplicate authority was introduced. |

## CORE-02 Vi domain foundation

| Validation item | Status | Latest evidence |
|---|---|---|
| Domain records and constraints | PASS | All ten approved records are registered; tenant/contact/case uniqueness, fixed values, positive/ordered SLA constraints, serial uniqueness, and immutable histories are covered by model/migration tests. |
| Transition and prerequisite rules | PASS | Reactivation, KYC preparation/approval, SIM fulfilment, activation approval/completion, and SLA command tests passed; invalid/stale commands fail closed. |
| Idempotency and concurrency | PASS | Same-key/same-command replays return existing outcomes; mismatched reuse and stale row versions return conflict evidence in focused tests. |
| RBAC and tenant isolation | PASS | Fifteen additive permissions, role defaults, API denial, manager approval boundaries, public UUID scoping, and cross-tenant 404 behavior passed. |
| Audit, Timeline, and durable facts | PASS | Material commands atomically append audit rows, Customer Timeline projections, and existing-ledger business events without introducing a parallel authority. |
| Milestone boundary | PASS | No Reactivation Kanban, KYC workspace, SIM fulfilment UI, Activation Queue, fake data, placeholder workflow, duplicate CRM pipeline, document store, timeline, or event bus was added. |
| Focused CORE-02 tests | PASS | 6 focused service/API/migration tests passed, including migration upgrade/downgrade/re-upgrade. |
| Deployed domain foundation | PASS | MySQL applied `0032`; API, Redis, Celery workers/beat, frontend, and nginx reached healthy state in the isolated ten-service stack. |

## CORE-01 navigation and product shell

| Validation item | Status | Latest evidence |
|---|---|---|
| Permitted navigation catalogue | PASS | Six-item task rail, grouped More surface, shared create actions, honest maturity labels, and permanent scope guard passed focused and full-suite tests. |
| RBAC and excluded concepts | PASS | Permission-filtered navigation/create/search tests passed; Ads, Payments, Billing, marketplace, SaaS/multi-project, and commerce destinations remain absent. |
| Keyboard and focus behavior | PASS | Menus, command palette, and mobile drawer expose state, close on Escape where applicable, trap dialog focus, and restore invoking focus. |
| Responsive active states | PASS | Compact/expanded rail, secondary routes, and primary mobile-overflow routes passed focused tests; mobile targets are at least 44px. |
| Reference and originality review | PASS | Six paired full/viewport workflows were inventoried; authenticated 1280×720 shell, More, and command palette were compared without importing reference code or assets. |
| Authenticated browser smoke | PASS | Dashboard shell and factual downstream-error states rendered at 1280×720 with a 72px rail, 672px command palette, and no horizontal overflow. |
| Focused frontend tests | PASS | 30/30 navigation/foundation tests passed after the final responsive active-state correction. |
| Source/migration/API boundary | PASS | Product scope sources, all 31 migrations, OpenAPI JSON, and generated TypeScript contract are unchanged from the CORE-01 baseline. |

## GOV-02 documentation and governance

| Validation item | Status | Latest evidence |
|---|---|---|
| Required governance files | PASS | All ten required root documents, ADR-0012, and Design Document 25 are present and non-empty. |
| Markdown structure and relative links | PASS | Heading/table structure and repository-relative Markdown links passed the GOV-02 static check. |
| Product-goal and priority consistency | PASS | Scope, rules, roadmap, tracker, ADR, and experience standard agree on the permanent target and ordered priorities. |
| Reference boundary and originality | PASS | Approved/conditional/prohibited categories, local-only ignore policy, fourteen-step review, and no-copy boundary are recorded consistently. |
| Exclusions | PASS | Ads, payments, billing/subscriptions, marketplace, reseller/multi-project, public signup, and commerce remain excluded. |
| No-placeholder and premium screen gate | PASS | Real-state rule, shared-component standard, continuous-quality boundary, and twenty-point Definition of Done are locked. |
| Changed-file boundary | PASS | GOV-02 changes only Markdown governance, ADR, and design files; no source, test, API, migration, configuration, or runtime file changed. |
| Reference library isolation | PASS | `.reference/` is locally ignored and no capture/archive file is tracked or staged. |
| Migration invariance | PASS | Migration head remains `0031_automation_trigger_receipts` with 31 linear revisions. |
| OpenAPI invariance | PASS | `frontend/openapi.json` remains OpenAPI 3.1.0 with 153 paths and is unchanged from the starting Git baseline. |

## Backend

| Validation item | Status | Latest evidence |
|---|---|---|
| Pytest | PASS | Canonical validation passed 945/945 backend tests in 523.29 seconds. |
| Migration validation | PASS | Single head `0034_reactivation_crm`; 34 linear revisions; SQLite upgrade/downgrade/re-upgrade and deployed MySQL upgrade passed. Generic SQLite `alembic check` remains non-authoritative because of pre-existing repository-wide reflection noise. |
| Ruff | PASS | Canonical deployed profile passed Ruff across application, tests, scripts, and root tools. |
| Mypy | PASS | Canonical deployed profile passed strict mypy across 253 backend source files. |
| Python compile | PASS | `compileall` passed for backend application/scripts and root scripts. |

## Frontend

| Validation item | Status | Latest evidence |
|---|---|---|
| TypeScript | PASS | Frontend and Playwright TypeScript checks passed in the canonical deployed profile with regenerated contracts. |
| ESLint | PASS | Frontend ESLint passed without errors or warnings after the final CORE-07 hook-dependency correction. |
| Vitest | PASS | Full suite passed 651/651 tests across 31 files. |
| Playwright | PASS | Isolated production owner journey passed 1/1 against the final CORE-07 images in 11.1 seconds. |
| Production build | PASS | TypeScript and Vite production build passed after final CORE-07 source and generated-contract changes; the known main-chunk warning remains non-blocking. |

## API

| Validation item | Status | Latest evidence |
|---|---|---|
| OpenAPI generation | PASS | Live generation and drift validation passed; OpenAPI 3.1.0 remains at 189 paths with optional exact-Contact filters and no removed path. |
| Generated TypeScript contracts | PASS | Exact-contact Inbox/Reactivation query contracts are regenerated; frontend typecheck and drift checks passed. |

## Infrastructure

| Validation item | Status | Latest evidence |
|---|---|---|
| Docker | PASS | Development/production Compose models, ten-service release contract, production builds, 189-path/25-task backend and frontend image contracts, Trivy source/image scans, SBOMs, and isolated deployment passed. |
| Celery | PASS | Realtime, bulk, and jobs workers plus beat reached healthy state; the backend image registered 25 tasks including due-reminder dispatch, and queued journey evidence passed. |
| Redis | PASS | Isolated Redis reached healthy state and supported the deployed queue/readiness journey. |
| Target production commissioning | PENDING – Host Machine Validation | TLS/host hardening, UAT, restore/rollback rehearsal, receiver delivery, and production approval require the target host. |

## Accessibility

| Validation item | Status | Latest evidence |
|---|---|---|
| Existing responsive/keyboard baseline | PASS | CORE-01/03/04/05 evidence remains green; CORE-07 adds labelled tab panels, Arrow/Home/End behavior, focus-safe source actions, denied/read-only states, zero-overflow desktop/tablet/mobile browser evidence, and no console errors. |
| Full final-scope WCAG regression | PENDING – Host Machine Validation | Must be repeated on every completed final-scope route with real domain data and the target browser/device matrix. |

## Performance

| Validation item | Status | Latest evidence |
|---|---|---|
| Standard-read canary | PASS | Deployed CORE-07 canary recorded p95 10.4 ms across 30 authenticated reads, below the 300 ms budget. |
| Full load/stress/spike/soak and 1M-contact certification | PENDING – Host Machine Validation | Requires the isolated Performance Lab and production-like capacity. |

## Known limitations

| Validation item | Status | Current limitation |
|---|---|---|
| Target observability receivers | PENDING – Host Machine Validation | Log shipping, dashboards, alert firing/dead-man delivery, and external synthetic checks need deployed receivers. |
| Production frontend bundle | PENDING – Host Machine Validation | The main chunk warning is 737.53 kB; further route splitting remains a performance task. |
| Docker-backed source scan | PASS | Trivy vulnerability, secret, and IaC scan passed; production backend/frontend image vulnerability scans and CycloneDX SBOM generation also passed. |
| React Router advisories | PENDING – Host Machine Validation | Two moderate advisories require an explicit React Router 7.18+ upgrade milestone, not a silent dependency change. |
| Customer 360 target commissioning | PENDING – Host Machine Validation | Repository/deployed representative-data checks pass; final target screen-reader/device matrix and production-scale query-budget certification remain host work. |
| Final domain workflows | PENDING – Host Machine Validation | CORE-07 completes Customer 360 convergence; General Approval, Notification Center, Google Sheets, Download Center and later roadmap domains remain. Heavy standalone SIM/Activation workspaces are not planned without explicit owner instruction. |

## Milestone closeout rule

A new result replaces prior evidence only after the exact command has completed. A failure remains
`FAIL` until rerun successfully. Environment-dependent checks stay
`PENDING – Host Machine Validation`; they must never be relabelled `PASS` from repository-only
inference.
