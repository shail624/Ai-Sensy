# Complete Feature Matrix

> Phase 1 deliverable. Every feature from the project brief, mapped to the
> strongest public reference implementation, its feasibility on the **Official
> Meta WhatsApp Cloud API**, and **our planned approach** (Match = parity with the
> best; Improve = we go beyond).
>
> **Legend — Feasibility:** ✅ Native (directly supported by Cloud API) ·
> 🟨 App-side (we build it; API allows it) · 🔶 Partial (Cloud API constrains it) ·
> ⛔ Not possible via Cloud API.
> **Approach:** Match · **Improve** · (scope note).

---

## Phase 3 realization update — 2026-07-25

| Product workflow | Realized state |
|---|---|
| Reactivation workspace | Complete navigation and premium workflow composition for eligibility, interested customers, pipeline, KYC, documents, SIM, activation, completion, and reports |
| Customer pipeline | Existing pipeline/stage configuration is real; the ten-stage reactivation blueprint is visible, while lead cards and transitions remain contract-gated |
| Customer 360 | Complete 13-tab information architecture with existing data reused and absent documents/KYC/SIM/payments/audit domains labelled honestly |
| Document Center | Existing media list/upload/preview/storage reused; contact linking, versions, verification, expiry, and workflow status remain contract-gated |
| Scan Studio | Added as a separate adapter/queue boundary, never merged with the official Meta WhatsApp channel |
| Automation | Accessible visual blueprint is complete; persistence, execution, scheduling, retries, and customer sends remain disabled pending approved contracts |
| Reporting | Existing analytics KPIs, funnel, and exports reused; reactivation/KYC/SIM/scan metrics are not fabricated |
| AI foundations | Document-summary seam added; all AI remains provider-deferred, human-controlled, and unable to mutate or send |

The detailed implementation, release evidence, and Phase 4 contract backlog are recorded in
`docs/design/18-PHASE-3-REACTIVATION-AUTOMATION-PLATFORM.md`.

---

## Phase 2 realization update — 2026-07-25

| Product workflow | Realized state |
|---|---|
| Shared Inbox | Extended: synchronized custom inboxes/pins, folders, multi-agent context, mentions, labels, snooze status, customer sidebar, AI seam, and bulk status/assignment/label actions |
| Customer 360 | Complete on existing contracts: identity, attributes, tags, tasks/reminders, histories, notes, lifecycle, recent interactions, and honest document/KYC states |
| Campaign Builder | Complete: Audience → Template → Preview → Schedule → Approval → Confirmation → Analytics |
| Template Center | Complete: categories, search/filters, preview, variables, version history, approval state, and favorites |
| Segments | Complete: dynamic rules, reusable audiences, estimates, filters, and recents |
| Broadcast Center | Added as a dedicated view over the existing campaign engine |
| Analytics | Extended with engagement funnel, delivery/read, campaign, employee, export, and honest template boundary |
| AI foundations | UI integration complete; provider execution remains deliberately deferred and human approval remains mandatory |

The detailed implementation and contract boundaries are recorded in
`docs/design/17-PHASE-2-CUSTOMER-ENGAGEMENT-PLATFORM.md`.

---

## A. Authentication, Users, Roles, Permissions

| Feature | Best reference | Feasibility | Our approach |
|---|---|---|---|
| Authentication (login/refresh/logout) | All (standard) | 🟨 App-side | Match — JWT access+refresh, rotation, Argon2id hashing |
| Users | All | 🟨 | Match — full CRUD, activate/deactivate, last-login |
| Roles | WATI/Respond.io (agent/admin/manager) | 🟨 | **Improve** — fully custom roles, not fixed tiers |
| Permissions | Respond.io (granular) | 🟨 | **Improve** — fine-grained `resource:action` permissions on every route |

## B. Dashboard & Real-time

| Feature | Best reference | Feasibility | Our approach |
|---|---|---|---|
| Dashboard | AiSensy / Respond.io | 🟨 | Match — KPI tiles, trends, health |
| Real-time Dashboard / Live Statistics | Respond.io | 🟨 | **Improve** — WebSocket/SSE live counters from webhook events |

## C. Contacts & Segmentation

| Feature | Best reference | Feasibility | Our approach |
|---|---|---|---|
| Contacts (unlimited) | Interakt (no cap) | 🟨 | Match — unlimited, indexed for scale |
| CSV Import | AiSensy/WATI | 🟨 | Match — streamed, validated, async for large files |
| Excel Import | Interakt | 🟨 | Match — `.xlsx` parsing with column mapping |
| Duplicate Detection | (varies) | 🟨 | **Improve** — normalize E.164 phone + fuzzy match, merge/skip strategies |
| Bulk Edit / Bulk Delete | WATI | 🟨 | Match — batched, audited |
| Tags | AiSensy (10 tags on free tier) | 🟨 | **Improve** — unlimited tags |
| Segments | AiSensy (smart segmentation) | 🟨 | Match — dynamic filter-based segments, reusable in campaigns |
| Custom Attributes | AiSensy (5 on free tier) | 🟨 | **Improve** — unlimited typed custom attributes |
| Advanced Search / Filters | Respond.io | 🟨 | **Improve** — composable filters across attributes, tags, engagement |

## D. Templates & Media

| Feature | Best reference | Feasibility | Our approach |
|---|---|---|---|
| Campaign/Message Templates | WATI/Interakt | ✅ Native | Match — sync from Meta, create/submit, track approval status & rejection reasons |
| Interactive components (buttons/lists/CTA/forms) | Interakt (10 buttons, forms) | ✅ Native | Match — full component builder with variable mapping |
| Media Library | AiSensy/Zoko | 🟨 | **Improve** — reusable assets, dedup by hash, Meta media-ID caching |

## E. Campaign Engine (Broadcasts)

| Feature | Best reference | Feasibility | Our approach |
|---|---|---|---|
| Broadcast Campaigns | AiSensy | ✅ Native | Match — audience = segment/tag/list, template-based |
| Campaign Scheduler | AiSensy (Pro-only) | 🟨 | **Improve** — scheduling standard, timezone-aware |
| Recurring Campaigns | Gallabox (drip) | 🟨 | **Improve** — cron-style recurrence + drip sequences |
| Campaign Queue | (BSP internal) | 🟨 | **Improve** — Celery/Redis queue, rate-limited to Meta tier |
| Pause / Resume | (rare publicly) | 🟨 | **Improve** — pause/resume mid-send safely |
| Retry Failed / Smart Retry Engine | Twilio-grade reliability | 🟨 | **Improve** — classify errors, exponential backoff, retry only retryable codes |
| Resume Interrupted Campaigns | (rare) | 🟨 | **Improve** — checkpointed progress; resume exactly where it stopped |
| Campaign Cost Calculator | (none — resellers hide markup) | 🟨 | **Improve** — pre-send estimate on Meta's real rate card |

## F. WhatsApp Infrastructure

| Feature | Best reference | Feasibility | Our approach |
|---|---|---|---|
| Multiple WhatsApp Numbers | Respond.io | ✅ Native | Match — many numbers per WABA |
| Multiple WABA | Enterprise BSPs | ✅ Native | Match — many WABAs per install |
| Phone Number Management | Meta | ✅ Native | Match — quality rating, messaging tier/limit, status |
| Webhook Management | Twilio | ✅ Native | **Improve** — verify signature, async processing, dead-letter + replay |
| Webhook-based Active Detection | AiSensy (opt-in signals) | ✅ Native | **Improve** — mark contact "active" on inbound webhook; drives smart sends |
| Quality rating / messaging limits | Meta | ✅ Native | Match — surface + auto-throttle sends to stay within tier |

## G. Shared Inbox & Conversations

| Feature | Best reference | Feasibility | Our approach |
|---|---|---|---|
| Conversation Inbox | WATI/Gallabox/Respond.io | ✅ Native | Match — shared, assignable, real-time |
| Conversation History | All | 🟨 | Match — full threaded history persisted |
| Quick Replies | WATI/Gallabox (saved replies) | 🟨 | Match — personal + shared canned replies |
| Internal Notes | Gallabox | 🟨 | Match — private team notes on conversations |
| 24-hour window awareness | Meta rule | ✅ Native | **Improve** — UI shows window countdown; blocks free-form outside it |
| Assignment / routing | WATI | 🟨 | Match — assign, reassign, unassigned queue |

## H. AI & Knowledge Base

| Feature | Best reference | Feasibility | Our approach |
|---|---|---|---|
| AI Assistant | Respond.io / Interakt (Haptik) | 🟨 | Match — suggested replies + drafting; built on latest Claude models |
| Knowledge Base | Respond.io | 🟨 | Match — KB powering AI answers (RAG) and agent lookup |

## I. Analytics & Reporting

| Feature | Best reference | Feasibility | Our approach |
|---|---|---|---|
| Delivery / Read / Failure Reports | WATI/Interakt | ✅ Native (status webhooks) | Match — per-message status from webhooks |
| Campaign Analytics | AiSensy (Pro-only) | 🟨 | **Improve** — standard, drill-down per campaign |
| Cost Analytics | (none transparent) | 🟨 | **Improve** — real spend by category/country/number/campaign |
| Click Tracking / URL Tracking | (BSP link wrapping) | 🟨 | **Improve** — first-party link shortener + click capture |

## J. Admin, Ops & Platform

| Feature | Best reference | Feasibility | Our approach |
|---|---|---|---|
| Settings | All | 🟨 | Match — org, numbers, notifications, security |
| Notifications | WATI | 🟨 | Match — in-app + optional email/webhook alerts |
| Audit Logs | Enterprise BSPs | 🟨 | **Improve** — immutable who-did-what on every mutation |
| System Logs | (internal) | 🟨 | Match — structured, queryable |
| Performance Monitoring | (internal) | 🟨 | Match — health, queue depth, latency, error rates |
| Backup / Restore | (SaaS-managed) | 🟨 | **Improve** — you own it: scheduled DB backups + restore tooling |
| Export CSV / Excel / JSON | WATI/Interakt | 🟨 | Match — for contacts, campaigns, reports |
| Dark Mode | Respond.io | 🟨 | Match — full theme (Module 2) |
| Responsive Design | All | 🟨 | Match — desktop-first, tablet/mobile responsive |
| Keyboard Shortcuts | Respond.io/Front-style | 🟨 | **Improve** — power-user shortcuts across app |

---

## Out-of-declared-scope ideas seen in research (flagged for your decision)

These are strong in competitors but **not in your feature list**. Noting them so you can
choose to add them later — none are in the current roadmap unless you approve:

| Idea | Seen in | Note |
|---|---|---|
| Visual drag-drop **chatbot / flow builder** | AiSensy, WATI, Gallabox, Respond.io | Big build; our rule-based automation + AI Assistant covers much of the value first |
| **Commerce** (catalog, cart recovery, COD, orders) | Zoko, AiSensy | Feasible via Cloud API but a separate domain; defer unless needed |
| **Click-to-WhatsApp Ads** manager | AiSensy | Requires Meta Ads API integration; separate track |
| **Omnichannel** (Instagram/Messenger/SMS/email) | Respond.io, WATI | Architecture will not preclude it, but scope is WhatsApp-only for now |
| **WhatsApp Pay / payments** | Interakt, AiSensy | Region-limited; defer |
| **WhatsApp Coexistence** (app + API same number) | Respond.io | Niche; defer |

---

## What this matrix commits us to

1. **Feature parity or better** with the best reseller on every item in your brief.
2. **Everything they paywall, we ship as standard** (scheduling, campaign analytics, multi-agent, custom attributes, tags).
3. **Three areas where we deliberately beat the market:** exact **cost analytics**, campaign **reliability** (smart retry + resume + queue control), and **data ownership**.
4. A schema and API designed for **multi-WABA, multi-number, unlimited contacts** from day one.
