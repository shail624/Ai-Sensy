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

## Genuine gaps that require new contracts

These must not be represented by mock cards or fake data.

| Gap | Required foundation before UI | Planned track |
|---|---|---|
| Executable chatbot/automation flows | Versioned flow schema, run ledger, approvals, retry/DLQ and permissions | PAR-AUTO |
| WhatsApp Forms and webviews | Form/version/submission contracts, consent, hosting and webhook projection | PAR-FORM |
| Click-to-WhatsApp Ads / Ads Manager | Meta Ads authorization, account/campaign/creative models and spend sync | PAR-ADS |
| WhatsApp payments | Provider abstraction, order/payment/refund ledger and regional compliance | PAR-PAY |
| AI agents | Provider policy, knowledge sources, tool permissions, evaluation and human handoff | PAR-AI |
| Commerce and abandoned-cart journeys | Product/cart/order domain plus Shopify/WooCommerce adapters | PAR-COM |
| Broad integration catalog | Credential vault, connector lifecycle, sync cursors and failure operations | PAR-INT |

## Delivery sequence

### UX-1 — Compact engagement shell

- Compact desktop task rail by default; a user can expand it at any time.
- Six daily destinations remain visible. Advanced and administrative routes live behind one
  permission-aware `More` panel rather than becoming a long icon catalog.
- Original teal engagement palette replaces the generic purple dashboard theme.
- Existing mobile bottom navigation, routes, permissions and keyboard shortcut remain intact.

### UX-2 — Live Chat simplicity

- **Delivered:** Requests, Active and My chats views map truthfully onto the existing open-status,
  unassigned and current-user assignment filters; no chatbot or handoff state is simulated.
- **Delivered:** advanced status/assignee/label filters and saved views remain available on demand;
  compact rows prioritize customer, message, unread and wait signals.
- **Delivered:** the default thread keeps status and assignment visible while customer context,
  editable labels, notes, AI assistance, pinning and Customer 360 stay one click away. Bulk controls
  still appear only after explicit conversation selection.

### UX-3 — Campaign and retargeting shortcuts

- **UI-3A delivered:** the existing six-step builder now uses a compact, scroll-free progress rail,
  guided step headers, audience and delivery choice cards, customer-facing message previews, and a
  concise final review. Optional AI foundations remain available but collapsed by default.
- **UI-3B remaining:** marketer-friendly audience presets over existing segment and message-event
  facts.
- Keep the existing governed Audience → Template → Preview → Schedule → Approval → Confirmation →
  Analytics path as the only dispatch authority.

### PAR tracks — additive product domains

Execute PAR-AUTO, PAR-FORM, PAR-ADS, PAR-PAY, PAR-AI, PAR-COM and PAR-INT only after their API,
schema, permission, tenant, audit, failure and test contracts are approved. Each track ships behind
its own quality evidence and never alters the completed send path.

## Acceptance standard

- A first-time operator can identify Live Chat, Contacts, Campaigns and Templates immediately.
- Common work requires no navigation through platform administration.
- No duplicate dispatch, CRM, inbox, analytics or permission implementation is introduced.
- All new surfaces use real server-owned data and preserve tenant isolation and auditability.
- Desktop and mobile pass keyboard, focus, contrast, touch-target and no-overflow checks.
- The result is recognizably this product, not a copied competitor interface.
