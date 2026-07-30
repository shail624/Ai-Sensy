# AiSensy-Comparable Product — Five-Phase Execution Plan

| Field | Value |
|---|---|
| Status | Proposed execution plan; each phase requires owner approval before implementation |
| Date | 2026-07-30 |
| Companion roadmap | Design Document 20 — AiSensy-Inspired Product Parity Roadmap |
| Repository baseline | OpenAPI 3.1.0, 141 paths, migration `0028`, 912 backend tests, 612 frontend tests |
| Product boundary | Comparable business outcomes and simplicity with original branding, UI, assets and code |

## 1. Goal

Build a WhatsApp engagement platform that a business can use for the same important jobs as
AiSensy, while retaining this repository's stronger queue safety, tenant controls, auditability,
data ownership and governed operations.

“Match” means:

- the same customer job can be completed with equal or fewer steps;
- the capability is backed by real server-owned data and executable behavior;
- permissions, audit, failure recovery and tenant isolation are production-grade;
- the interface is simple, consistent and original;
- no competitor branding, layout, assets, copy or source code is reproduced.

It does **not** mean pixel-for-pixel cloning or adding non-functional feature cards.

## 2. Current benchmark

The benchmark was refreshed from AiSensy's official pages on 2026-07-30:

- [Platform features](https://aisensy.com/features)
- [Multi-agent WhatsApp support](https://aisensy.com/features/whatsapp-support)
- [WhatsApp automation](https://aisensy.com/features/whatsapp-automation)
- [WhatsApp retargeting](https://aisensy.com/features/whatsapp-retargeting)
- [WhatsApp AI agents](https://aisensy.com/features/whatsapp-ai-agents)

The official feature set currently groups the product around broadcasts and segmentation,
multi-agent support, chatbot automation, forms/webviews, payments, Click-to-WhatsApp advertising,
AI agents, retargeting/click tracking, acquisition tools, commerce and integrations.

## 3. Verified position today

| Business job | Repository position | Decision |
|---|---|---|
| Contacts, import/export, attributes, tags and Customer 360 | Production | Preserve |
| Segments and reusable campaign audiences | Production | Add marketer-friendly presets |
| Template broadcasts, scheduling, approval, pacing and retry | Production | Preserve dispatch authority |
| Multi-agent inbox, assignment, labels, notes and quick replies | Production | Continue UX convergence only |
| Delivery/read/failure/cost analytics and exports | Production | Add simpler retargeting journeys |
| Multiple WABAs/numbers and channel health | Production | Preserve |
| RBAC, audit, jobs, queues, API keys and observability | Production | Reuse in every new domain |
| Executable chatbot/automation flow runtime | Contract gap | Phase 2 |
| WhatsApp Forms and governed webviews | Contract gap | Phase 2 |
| Click-to-WhatsApp Ads and Ads Manager | Contract gap | Phase 3 |
| Payment/order/refund processing | Contract gap | Phase 4 |
| Catalog, cart and abandoned-cart journeys | Contract gap | Phase 4 |
| Governed conversational AI agents | Contract gap | Phase 5 |
| Managed integration catalog | Contract gap | Phase 5 |

Placeholder tabs, architecture documents and disabled AI seams are not counted as implemented
features. Only executable contracts and validated production behavior count.

## 4. Delivery rules

Every phase must follow these rules:

1. Reuse the existing repository → service → API layering.
2. Keep `SendService` as the only message-send authority.
3. Keep provider payloads inside the Meta adapter.
4. Keep the Retry Engine and Rate Gate as the only retry/pacing authorities.
5. Add schemas and APIs only through an approved ADR/design change.
6. Make new records tenant-scoped, permission-gated and audited.
7. Use idempotency for every external write, webhook and queued execution.
8. Generate frontend types from OpenAPI; never hand-write contract types.
9. Show no feature in navigation until its real end-to-end path works.
10. Ship one independently reversible milestone at a time.

## 5. Five-phase plan

### Phase 1 — Simplicity, retargeting and acquisition foundation

**Objective:** close the visible day-to-day UX gap using existing capabilities before creating new
platform domains.

**Deliverables**

- Finish the common-screen simplicity audit for Dashboard, Contacts, Templates and Analytics.
- Add marketer-friendly audience presets over verified segment and message-event facts, such as
  read, clicked, failed, recently engaged and inactive audiences where the current contract supports
  them.
- Provide a direct campaign → result → retarget → duplicate journey without creating a second
  campaign engine.
- Standardize empty, loading, error, onboarding and first-success states across daily workflows.
- Audit carousel-message and acquisition-link/QR support. If missing, approve small additive
  contracts before exposing these features.
- Record task-click and completion-time baselines for first broadcast, reply and retargeting.

**No new behavior may bypass:** segments, campaign approval, `SendService`, pacing or consent.

**Exit gate**

- A first-time marketer can import contacts, build an audience, send an approved campaign and create
  a retargeting campaign without entering administration.
- Desktop and mobile pass keyboard, focus, contrast, touch-target and overflow checks.
- Existing APIs, permissions and dispatch behavior remain compatible.

**Size:** Medium. **Next milestone:** `UX-3B — audience and retargeting presets`.

### Phase 2 — Automation, chatbot flows and WhatsApp Forms

**Objective:** deliver a real, versioned automation runtime rather than a decorative flow canvas.

**Contract foundation**

- Versioned flow definitions, drafts, published versions and rollback.
- Typed triggers, conditions and actions with schema validation.
- Immutable execution/run ledger, step attempts, correlation IDs and replay controls.
- Idempotency, retry/DLQ policy, pause/disable controls and loop protection.
- Automation permissions, approvals, audit events and per-tenant quotas.
- Form definitions, versions, fields, consent evidence, submissions and webhook projection.
- Governed webview hosting, origin policy, expiry and submission security.

**Product experience**

- Original drag-and-drop builder with test mode, validation and publish review.
- Human-readable run history and failure recovery.
- Bot-to-human handoff into the existing Live Chat assignment workflow.
- Form builder, preview, response inbox and contact/timeline projection.

**Exit gate**

- A published flow can execute deterministically, survive retries, hand off to a human, and be
  traced from trigger through message result.
- Duplicate webhooks cannot duplicate actions or messages.
- Forms preserve consent and tenant boundaries end to end.

**Size:** Extra large. **Tracks:** `PAR-AUTO`, then `PAR-FORM`.

### Phase 3 — Click-to-WhatsApp Ads, acquisition and attribution

**Objective:** connect paid acquisition to WhatsApp leads and measurable outcomes.

**Contract foundation**

- Meta authorization lifecycle and encrypted credential storage.
- Business, ad-account, campaign, ad-set, creative and lead-attribution models.
- Read/sync cursors, webhook ingestion, reconciliation and token-health operations.
- Spend, click, lead and conversion facts with currency/timezone handling.
- Ad permissions, approval checkpoints, budget limits and immutable audit evidence.

**Product experience**

- Guided Click-to-WhatsApp campaign setup using real Meta-owned assets.
- Creative/template preview and destination-number validation.
- Acquisition dashboard from spend → conversation → qualified lead → conversion.
- Retargeting from attributed audiences through the existing campaign engine.

AI-assisted ad recommendations remain drafts until a user explicitly approves them.

**Exit gate**

- An authorized account can create or synchronize a CTWA campaign, receive attributed WhatsApp
  conversations and reconcile spend without cross-tenant leakage.
- Token expiry, Meta rejection, partial sync and webhook replay have tested recovery paths.

**Size:** Extra large. **Track:** `PAR-ADS`.

### Phase 4 — Payments, catalog and commerce journeys

**Objective:** support conversion inside WhatsApp with a provider-neutral financial ledger.

**Contract foundation**

- Provider abstraction for payment links/requests and verified callbacks.
- Orders, order items, payment attempts, settlements, refunds and immutable status history.
- Product/catalog, cart and checkout references without duplicating external commerce ownership.
- Signed webhooks, idempotency keys, amount/currency validation and reconciliation jobs.
- Regional compliance, retention, least-privilege access and PII redaction.
- Shopify/WooCommerce-style adapter boundaries for catalog, checkout and abandoned-cart events.

**Product experience**

- Payment request composer using approved message paths.
- Customer 360 order/payment timeline backed only by ledger records.
- Failed/pending payment follow-up and abandoned-cart journeys through Phase 2 automation.
- Refund/reconciliation operations with explicit human authority.

**Exit gate**

- Payment and order state is reproducible from signed provider evidence.
- Replayed callbacks cannot duplicate charges, orders, refunds or outbound messages.
- No card or bank secrets are stored outside the provider-approved boundary.

**Size:** Extra large. **Tracks:** `PAR-PAY`, then `PAR-COM`.

### Phase 5 — Governed AI agents and integration ecosystem

**Objective:** add contextual AI and connectors without weakening human control or operational
reliability.

**Contract foundation**

- Provider/model policy, knowledge sources, retrieval scopes and evaluation datasets.
- Agent definitions, tool allowlists, confidence/risk policy and human-handoff rules.
- Interaction/run records containing sources, model version, cost, latency and decisions.
- Prompt-injection defenses, PII policy, rate/cost limits and kill switches.
- Connector definitions, encrypted credentials, scopes, sync cursors and failure operations.
- Webhook/API connector SDK with versioning, quotas, idempotency and tenant isolation.

**Product experience**

- Knowledge management and evaluation workspace.
- AI-drafted replies and summaries with source visibility and explicit approval.
- Carefully approved autonomous actions only if a later ADR changes the current human-approval
  invariant; until then, AI never sends directly.
- Integration catalog with connection health, last sync and recoverable errors.

**Exit gate**

- AI quality, safety, cost and handoff thresholds pass a versioned evaluation suite.
- Every AI/tool action is permission-scoped, attributable and auditable.
- Connector outage or AI-provider failure cannot block core messaging.

**Size:** Extra large. **Tracks:** `PAR-AI`, then `PAR-INT`.

## 6. Quality gate for every phase

A phase is not RELEASE READY until all applicable evidence passes:

- approved gap analysis, design and ADRs;
- linear migration integrity and rollback/recovery plan;
- OpenAPI export, drift check and generated frontend types;
- backend tests, Ruff and raw strict mypy;
- frontend tests, ESLint, TypeScript and production build;
- API, permissions, tenant-isolation and audit regression tests;
- queue registration, worker startup, retry/idempotency and DLQ tests;
- Docker production image build and smoke validation;
- accessibility and responsive browser journeys;
- dependency/source/image security gates when affected;
- tracker, changelog, runbook and operational evidence updates.

## 7. Recommended implementation order

Start only with Phase 1 milestone `UX-3B`. Do not start multiple contract-heavy phases together.
After each milestone:

1. verify the existing baseline is unchanged;
2. implement the smallest complete vertical slice;
3. prove it with automated and production-container evidence;
4. update the tracker and changelog;
5. commit only when every applicable gate passes;
6. request approval for the next contract boundary.

Phase 2 is the first major new product subsystem. Phases 3–5 depend on approved external-provider,
credential, compliance and operational decisions and must not be represented as already available.

## 8. Final definition of comparable

The product is AiSensy-comparable when all five phases are release-ready and a business can perform
the benchmark jobs—acquire, segment, broadcast, converse, automate, collect, convert, analyze and
integrate—using real governed behavior. The final experience should remain recognizably this
platform: simpler where possible, stronger in reliability and governance, and never a clone.
