# AiSensy-Inspired Product Parity Roadmap

**Status:** Active roadmap

**Benchmark refreshed:** 2026-07-30

**Product boundary:** Comparable workflow simplicity and capability coverage; original branding,
visual language, source code, information architecture, and assets.

**Execution plan:** [Design Document 21](21-AISENSY-PARITY-5-PHASE-EXECUTION-PLAN.md) — five
governed delivery phases from UX convergence through integrations.

## Objective

Make the platform feel as simple and commercially complete as a leading WhatsApp engagement suite
while preserving the stronger repository architecture already delivered. “Parity” means users can
complete the same business job with equal or fewer steps. It does not mean copying another
product's screens or presenting features for which this repository has no governed data contract.

Official benchmark sources used for this refresh:

- https://aisensy.com/features
- https://aisensy.com/features/whatsapp-support
- https://aisensy.com/features/whatsapp-retargeting
- https://aisensy.com/en/features/whatsapp-automation
- https://aisensy.com/features/whatsapp-ai-agents

## Verified parity already present

| Customer job | Repository capability | Status |
|---|---|---|
| Manage WhatsApp customers | Contacts, Excel/CSV import, tags, attributes, Customer 360 | Production |
| Build reusable audiences | Dynamic segments, estimates, filters and campaign audiences | Production |
| Broadcast at scale | Campaign builder, scheduling, approval, queueing, pacing and lifecycle | Production |
| Retarget engaged audiences | Delivery/read/click facts plus reusable segment and campaign paths | Production foundation |
| Support customers as a team | Shared inbox, assignment, labels, notes, quick replies and bulk actions | Production |
| Manage message templates | Authoring, variables, Meta sync, approval state and history | Production |
| Track performance | Delivery/read/failure, campaign, conversation, cost and export analytics | Production |
| Operate multiple channels | Multiple WABAs/numbers, quality, limits, health and token state | Production |
| Govern an enterprise workspace | Custom RBAC, audit, jobs, queues, API keys and observability | Production |

The repository also exceeds the benchmark in campaign retry/resume safety, queue isolation,
tenant controls, auditable operations, governed customer documents, and data ownership.

## Genuine gaps and explicit scope exclusions

Planned gaps must not be represented by mock cards or fake data. Excluded domains must not appear
as roadmap deliverables, navigation, placeholders or integration promises.

| Gap | Required foundation before UI | Planned track |
|---|---|---|
| Executable chatbot/automation flows | Versioned flow schema, run ledger, approvals, retry/DLQ and permissions | PAR-AUTO |
| WhatsApp Forms and webviews | Form/version/submission contracts, consent, hosting and webhook projection | PAR-FORM |
| Click-to-WhatsApp Ads / Ads Manager | Meta Ads authorization, account/campaign/creative models and spend sync | PAR-ADS |
| WhatsApp payments | Explicitly excluded by the product owner | Not planned |
| AI agents | Provider policy, knowledge sources, tool permissions, evaluation and human handoff | PAR-AI |
| Commerce and abandoned-cart journeys | Explicitly excluded by the product owner | Not planned |
| Broad integration catalog | Credential vault, connector lifecycle, sync cursors and failure operations | PAR-INT |

## Delivery sequence

### UX-1 — Compact engagement shell

- Named desktop navigation is expanded by default so a first-time operator can see Dashboard, Live
  Chat, Chat History, Campaigns, Contacts, Automation and Analytics without interpreting icons. A
  user can still choose the compact task rail at any time.
- Templates, audiences, channels, Vi operations and administration live behind one permission-
  aware `Manage` section rather than becoming an unstructured icon catalog.
- Original teal engagement palette replaces the generic purple dashboard theme.
- Existing mobile bottom navigation, routes, permissions and keyboard shortcut remain intact.

### UX-2 — Live Chat simplicity

- **Delivered:** Requested, Active and Intervened views map truthfully onto the existing pending,
  open and current-user assignment facts; no chatbot or handoff state is simulated.
- **Delivered:** a requested chat can be claimed through one `Intervene` action. The claim is
  row-locked, assigns the current agent, rejects a second agent without stealing ownership and is
  safe to retry. The owner can `Resolve`; both the dedicated action and legacy status route enforce
  owner-only resolution. Existing status, assignment and Audit facts remain authoritative.
- **Delivered:** advanced status/assignee/label filters and saved views remain available on demand;
  compact rows prioritize customer, message, unread and wait signals.
- **Delivered:** the default thread keeps status and assignment visible while customer context,
  editable labels, notes, AI assistance, pinning and Customer 360 stay one click away. Bulk controls
  still appear only after explicit conversation selection.
- **Delivered:** a clean published automation may define a typed `Human handoff` node. A governed
  idempotent execution request places the referenced same-tenant conversation into `Requested`,
  while a replay after agent intervention cannot requeue or steal the chat. The builder labels the
  live contract and safe test mode continues to simulate every step.
- **Delivered:** a newly accepted inbound message now produces a privacy-safe durable receipt. An
  exact published Trigger → Human handoff graph consumes it once through a pinned live run with
  step evidence; webhook/worker replay converges and unsupported inbound graphs fail closed.
- **Delivered:** that pinned inbound run may contain one privacy-safe Condition before handoff.
  Matching continues into Requested; non-matching records a skipped no-effect branch. Private fields,
  unsupported operators and non-linear graphs fail closed.
- **Delivered:** an exact inbound Trigger → Create task path, optionally after that privacy-safe
  Condition, creates one real Task linked to the Contact/Conversation. It reuses existing Task,
  history, Timeline and Audit ownership, assigns the active publisher, and recovers the same Task
  after worker replay through a receipt-keyed command contract.
- **Delivered:** an exact inbound Trigger → Apply tag path, optionally after that privacy-safe
  Condition, attaches one existing tenant-scoped CRM tag to the Contact. Contact/Tag locks,
  idempotent association semantics, usage count, Timeline and system Audit evidence converge under
  concurrent or crash replay without duplicate effects.
- **Delivered:** an exact inbound Trigger → Assignment path, optionally after that privacy-safe
  Condition, assigns the Conversation to an execution-time validated specific Inbox user or a
  deterministic per-flow round robin. The Conversation lock preserves an existing owner; a new
  assignment and system Audit commit together, and crash replay cannot duplicate either.
- **Delivered:** an exact inbound Trigger → Remove tag path, optionally after that privacy-safe
  Condition, detaches one existing tenant-scoped CRM tag from the Contact through the same locked
  association, usage counter, Timeline and Audit authorities. Already-absent and crash-replayed
  removals complete safely without duplicate effects.
- **Delivered:** an exact inbound Trigger → Notification path, optionally
  after that privacy-safe Condition, creates one Contact-linked internal Notification Center
  delivery for the active eligible publisher. Receipt/node deduplication prevents duplicate
  delivery; repository runtime, frontend, migration, static and production-build gates pass.
- **Delivered:** one inbound Trigger may execute up to four distinct supported internal effects in
  connected order, optionally after that privacy-safe Condition. Completed nodes checkpoint worker
  retry; branches, repeated effect kinds, larger sequences and unsupported/external actions fail
  closed before an effect.
- **Delivered:** one bounded Delay may pause that connected live sequence for 60 seconds to 30
  days. The running attempt stores the resume deadline, the existing Automation worker schedules
  continuation, early delivery cannot advance, and due resume preserves completed checkpoints.
- **Delivered:** Contact Created is the second bounded live event. It can apply/remove an existing
  CRM tag and create an internal Notification, optionally behind source/opt-in Condition metadata
  and one Delay. The existing scheduler queue now claims received or genuinely stale receipts for
  idempotent worker dispatch while excluding paused Delay rows.
- **Delivered:** Conversation Auto-Resolved is the third bounded live event. It may create a
  publisher-assigned follow-up Task, apply/remove a CRM tag and create an internal Notification,
  optionally behind previous-status/inactivity-threshold metadata and one Delay. Handoff and
  Assignment remain rejected on the resolved chat.
- **Delivered:** Schedule is the fourth bounded live trigger. A clean published five-field cron
  persists indexed UTC `next_run_at` in the organization timezone. The minute heartbeat row-locks
  one deterministic slot/event/receipt and advances to the first future occurrence. Its live path
  is one workspace-only publisher Notification with one optional Delay; Conditions and every
  contact/conversation/external/customer effect fail closed.
- **Delivered:** one bounded live Wait on event-backed paths persists same-Contact
  `message.received` or privacy-safe `task.completed` matching and a required
  60-second-to-30-day deadline. Match and timeout resume the original receipt/run from checkpoints
  through the existing receipt dispatcher; wrong-Contact and duplicate events cannot produce
  duplicate effects. Reopened/re-completed Tasks emit a distinct immutable completion cycle.
- **Delivered:** the existing immutable Reactivation transition fact is projected as the live
  `lead.stage_changed` alias without a duplicate CRM event. It supports from/to-stage Conditions,
  Contact-linked follow-up Task, tag changes and internal Notification, plus same-customer Wait
  resume. Private transition reasons are excluded; Handoff, Assignment, external and customer
  actions remain fail-closed.
- **Delivered:** one event-backed Condition may split into exactly one terminal Yes effect and one
  terminal No effect. Only the selected edge executes; the other receives durable skipped evidence,
  safe test mode follows the same decision, and receipt/worker replay cannot duplicate the chosen
  internal action. The list builder labels both branches and can return them to a linear gate.
- **Delivered:** either side of that exact split may append one second ordered distinct internal
  effect under the unchanged four-effect ceiling. Selected bodies resume from durable checkpoints,
  every unselected node is skipped, and the builder exposes separate Yes/No addition controls.
- **Delivered:** both sides of that exact split may converge on one optional terminal trigger-safe
  internal effect under the same four-effect ceiling. Only the selected branch and shared node
  execute; alternate-only nodes stay durably skipped. The builder exposes `+ Both` and labels the
  shared node `After both` while safely inserting or removing branch terminals before the merge.
- **Delivered:** that shared follow-up may have one durable Delay immediately before it. The
  selected body checkpoints before pausing; early/duplicate delivery reuses one timer, and due
  resume executes the shared effect exactly once. The builder labels `Shared delay` and cannot
  leave the timer terminal when the dependent follow-up is removed.
- **Contract-gated:** the general live chatbot/flow runtime, multiple/nested Conditions, branch
  bodies longer than two effects, branch-specific Delay/Wait, multiple timers, arbitrary or multiple merges, further event consumers,
  campaign/webhook and customer-message actions, capacity/skill
  routing, recipient/team notification routing, and operational retry/DLQ/reconciliation remain
  future PAR-AUTO work.

### UX-3 — Campaign and retargeting shortcuts

- **UI-3A delivered:** the existing six-step builder now uses a compact, scroll-free progress rail,
  guided step headers, audience and delivery choice cards, customer-facing message previews, and a
  concise final review. Optional AI foundations remain available but collapsed by default.
- **UI-3B delivered:** four marketer-friendly quick-start audiences over supported contact and
  engagement facts; preset-shaped saved segments surface as one-click choices in the campaign
  builder, and the existing duplicate flow remains the governed follow-up path. Campaign-specific
  read/click/failed cohorts are not inferred from the paginated recipient UI and remain gated on a
  separately approved complete-audience contract.
- **UI-3C delivered:** a completed campaign labels the existing fresh-draft composition path as
  `Create follow-up`, keeps the source definition, and requires the operator to review the new
  audience, template, timing and approval before anything can send.
- **PAR-CAM-01 delivered:** Campaign Detail's recipient tab filters and cursor-pages the complete
  persisted roster on the server, shows tenant-safe current identity plus safe failure/retry/
  lifecycle facts, and confirms the exact failed-recipient boundary before invoking the existing
  retry authority. This is an operational results view, not a browser-inferred retarget audience.
- **PAR-VIEW-01 delivered:** Reactivation's existing search/owner/status/label/reminder/date and
  board/list state can be saved privately or published to the tenant by permission. Definitions are
  validated, audited and server-owned; applying one never carries stale pagination or changes cases.
- **PAR-VIEW-02 delivered:** Contacts now saves its existing search/tag/enum-attribute filters as
  private or permission-published team definitions. It reuses the Reactivation workspace-view
  authority, drops stale cursors on apply and leaves search, bulk and export audience truth intact.
- Keep the existing governed Audience → Template → Preview → Schedule → Approval → Confirmation →
  Analytics path as the only dispatch authority.

### UX-4 — Chat acquisition utility

- **Delivered:** a real phone number can generate its public `wa.me` link, optional prefilled
  message and downloadable QR entirely in the browser. It performs no shortening, persistence,
  tracking or third-party QR request and therefore needs no new backend authority.
- **Contract-gated:** tracked acquisition campaigns and carousel templates remain absent. The
  current template interpretation and send mapping do not define complete carousel-card variables,
  media and button payloads, so the UI must not claim that support.

### PAR tracks — additive product domains

Execute PAR-AUTO, PAR-FORM, PAR-ADS, PAR-AI and PAR-INT only after their API,
schema, permission, tenant, audit, failure and test contracts are approved. Each track ships behind
its own quality evidence and never alters the completed send path.

Payments, product catalogs, carts, checkout, orders, refunds and commerce journeys are deliberately
outside this product roadmap and must not be introduced by a future parity effort.

## Acceptance standard

- A first-time operator can identify Live Chat, Contacts, Campaigns and Templates immediately.
- Common work requires no navigation through platform administration.
- No duplicate dispatch, CRM, inbox, analytics or permission implementation is introduced.
- All new surfaces use real server-owned data and preserve tenant isolation and auditability.
- Desktop and mobile pass keyboard, focus, contrast, touch-target and no-overflow checks.
- The result is recognizably this product, not a copied competitor interface.
