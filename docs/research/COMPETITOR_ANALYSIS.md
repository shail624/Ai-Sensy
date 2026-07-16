# Competitor & Platform Research

> Phase 1 research. Purpose: identify the strongest publicly documented ideas
> across the leading WhatsApp Business platforms and the Official Meta Cloud API,
> so we can combine and improve on the best of each.
> Research date: **2026-07-15**. Sources listed at the end.

---

## 0. The most important strategic fact

Every commercial platform below (AiSensy, WATI, Interakt, Gallabox, Zoko, Respond.io)
is a **Business Solution Provider (BSP) / reseller** that sits between you and Meta.
They add a **monthly subscription** *and*, in most cases, a **per-message markup** on
top of Meta's raw rates. WATI, for example, is repeatedly reported to cost **3–5×**
its headline plan once message markup, extra agents, and chatbot sessions are added.

**Our platform connects directly to the Official Meta WhatsApp Cloud API.**
That means:

- **No subscription** — we self-host.
- **No per-message markup** — you pay Meta's raw rate and nothing more.
- **Full data ownership** — contacts, conversations, and analytics live in *your* database.
- We can build a **cost engine on Meta's real rate card**, so cost analytics are exact
  rather than an opaque reseller estimate.

This reframes the goal: we are not just cloning features — we are removing the
reseller tax while matching or beating their capabilities.

---

## 1. Platform-by-platform profiles

### AiSensy — *broadcast & marketing at scale (India-first)*
- **Positioning:** Affordable WhatsApp marketing; strong in high-volume broadcasting.
- **Standout features:** Broadcast to very large audiences (bypasses the 256-contact app limit); **smart audience segmentation & retargeting** (filter-based, no re-uploading Excel each time); drag-and-drop **chatbot builder** with human handover; **multi-agent live chat**; Click-to-WhatsApp Ads manager; catalog; WhatsApp payments (Razorpay/PayU); WhatsApp forms.
- **Pricing:** Free-forever tier ($0 + $1 conversation credit, 10 tags, 5 custom attributes); Basic ~$45/mo; Pro ~$99/mo. **Broadcast scheduling and campaign analytics are gated to the Pro plan**; chatbot builder is a paid add-on (~₹2,000–2,500/mo).
- **Take for us:** Their broadcast + segmentation UX is the benchmark. We make **scheduling and campaign analytics standard**, not a paywalled tier.

### WATI — *support-led shared inbox + no-code automation*
- **Positioning:** Customer engagement / support with an omnichannel inbox.
- **Standout features:** **Shared team inbox** with chat assignment, **quick replies**, broadcast; **no-code chatbot & workflow automation**; template management; CRM / Zapier / Google Sheets integrations; message & campaign analytics dashboards; omnichannel (WhatsApp, Instagram, Facebook, web chat).
- **Pricing:** Growth $59/mo (5 users, 1,000 conversations); Pro $119/mo; Business ~$279–349/mo. **Message costs are billed on top** with markup; total often 3–5× headline.
- **Take for us:** Their inbox operating model (assignment, tagging, quick replies, analytics) is the reference for our Shared Inbox module. We remove the markup.

### Interakt — *all-in-one CRM + campaigns + rich interactive messaging*
- **Positioning:** CRM + campaign management + sales channel (Shopify-friendly).
- **Standout features:** Bulk campaigns with segmentation by purchase history/location/behavior; delivery & engagement tracking; **team inbox**; no-code chatbot; **AI Agents** (powered by Haptik) for free-text conversations and actions; **rich interactive replies** — interactive lists, custom replies, workflows, up to **10 buttons**, WhatsApp Forms, WhatsApp Pay, opt-out flows. **No cap on contacts.**
- **Pricing:** Growth ~$49–55/mo; Advanced ~$63–69/mo; Meta fees separate.
- **Take for us:** Best reference for **interactive message richness** (buttons/lists/CTAs/forms) and **unlimited contacts as a baseline expectation**.

### Respond.io — *deepest automation + reporting, true omnichannel*
- **Positioning:** Mid-market/enterprise conversation management.
- **Standout features:** Unified inbox across WhatsApp, Messenger, Instagram, SMS, email, TikTok, voice; **visual Flow Builder** for arbitrarily complex automation (trigger → branching actions); **conversation merging** across channels into one contact; **WhatsApp Coexistence** (use the WhatsApp Business app + API on the same number); **AI Agents** (autonomous, role-based, multimodal — text/image/PDF/voice); strong reporting and lifecycle/CRM updates.
- **Take for us:** The benchmark for **automation depth, reporting rigor, and inbox polish**. Our automation can start rule-based and grow toward a flow model.

### Gallabox — *collaboration-first inbox + drip campaigns*
- **Standout features:** Shared team inbox with **assignment rules, internal notes, saved replies**; no-code drag-drop chatbot; WhatsApp flows/forms; **drip campaigns** (time/behavior-based sequences); broadcast to segments; integrations (Shopify, HubSpot, Zoho, Razorpay) and webhook triggers.
- **Take for us:** Reference for **internal notes + saved replies + assignment rules**, and for **drip/sequence campaigns** (a natural extension of our recurring-campaign engine).

### Zoko — *WhatsApp commerce for Shopify*
- **Standout features:** Product catalog + order management; **prebuilt commerce flows** via Zoko Flows — abandoned-cart recovery, COD confirmation, reorder reminders, review collection, shipping updates; broadcast; multi-agent; customer segmentation.
- **Take for us:** Commerce is **out of our declared scope**, but their **event-triggered campaign** pattern (order/cart events → templated message) informs our campaign trigger design for later.

### Twilio (WhatsApp) — *raw programmable API, developer-grade reliability*
- **Standout features:** Programmable send/receive, template messages, one-way alerts and two-way conversations, SDKs, robust delivery-status handling and sender management. **No dashboard, no visual flow builder, no prebuilt commerce** — you build it.
- **Take for us:** The reference for **API design discipline, delivery-status/webhook handling, idempotency, and reliability** — exactly the qualities our backend must have. We provide the polished product layer Twilio deliberately omits.

---

## 2. The Official Meta WhatsApp Cloud API (our foundation)

Meta hosts the API **for free** (no per-message markup — you pay only messaging fees).
Key capabilities and rules that shape our design:

**Message categories & billing (post-2025 model):**
- Categories: **marketing, utility, authentication, service**.
- Billing moved from **per-conversation to per-message**, effective **July 1, 2025** —
  you are charged **per delivered template message**.
- **Service** conversations are **free & unlimited** since **Nov 1, 2024**.
- **Utility** templates are **free when delivered inside an open 24-hour service window** (since July 1, 2025).
- **Free tier:** first **1,000 service conversations per number per month**.
- Rates vary by country and category (e.g., marketing ≈ $0.0094 India, $0.025 US,
  $0.0305 Mexico, $0.0499 UAE, $0.0625 Brazil, ~$0.048 UK, ~$0.124 Germany).
- Further pricing changes announced for **Aug 1, 2026** and **Oct 1, 2026**; India moved to local-currency billing Jan 2026. → *Our cost engine must be rate-card-driven and easy to update.*

**Messaging mechanics we must implement natively:**
- **Messaging tiers / limits:** unique-customer send limits per rolling 24h (1K → 10K → 100K → unlimited) that scale with quality.
- **Quality rating** per number (green / yellow / red) and phone-number status.
- **24-hour customer service window:** free-form messages only allowed inside it; outside it you must use approved templates.
- **Template management:** create/submit templates, categories, approval status, rejection reasons; components (header/body/footer/buttons), variables, media headers.
- **Message types:** text, media (image/video/doc/audio/sticker), location, contacts, **interactive** (reply buttons, list, CTA-URL, WhatsApp Flows), reactions, and **template** messages.
- **Webhooks:** inbound messages + **status callbacks** (`sent` → `delivered` → `read`, plus `failed` with error codes). Meta retries non-200 responses with decreasing frequency for up to **7 days** → *our webhook endpoint must be fast, idempotent, and return 200 immediately while processing async.*
- **Media:** upload to Meta (get media ID) and download inbound media by ID.
- **Multiple WABAs and multiple phone numbers** under a business — must be first-class in our data model.

---

## 3. Cross-platform takeaways (what we combine & improve)

| Capability | Best public reference | What we do |
|---|---|---|
| High-volume broadcast + segmentation | AiSensy | Match; make scheduling + analytics **standard**, not paywalled |
| Shared inbox (assignment, quick replies, notes) | WATI + Gallabox | Match; add SLA timers + internal notes + saved replies |
| Interactive message richness (buttons/lists/CTA/forms) | Interakt | Match natively via Cloud API |
| Automation depth + reporting | Respond.io | Start rule-based; reporting parity from day one |
| Delivery-status reliability, idempotency | Twilio | Match engineering rigor; async webhook + smart retry |
| Drip / sequence campaigns | Gallabox | Fold into recurring-campaign engine |
| Exact cost analytics | *(none — resellers hide markup)* | **Beat everyone:** direct Meta rate-card cost engine |
| Data ownership | *(none — all are SaaS)* | **Beat everyone:** self-hosted, your DB |

**Design principles inherited from the research:**
1. **Contacts are unlimited** and segmentation is filter-based (no re-uploading lists).
2. **Every paywalled "premium" feature elsewhere is standard here** (scheduling, analytics, multi-agent).
3. **Reliability is a feature:** async webhooks, idempotent status handling, a smart retry engine, and resumable campaigns are core, not afterthoughts.
4. **Cost transparency is a differentiator:** a rate-card-driven cost calculator and cost analytics.
5. **Multi-WABA / multi-number** from the schema up.

---

## Sources

- AiSensy — [aisensy.com](https://aisensy.com/), [Features](https://aisensy.com/features), [Pricing/Reviews 2026](https://www.positioniseverything.net/aisensy-pricing-reviews-2026/), [G2](https://www.g2.com/products/aisensy/reviews)
- WATI — [wati.io](https://www.wati.io/), [Pricing](https://www.wati.io/en/pricing/), [Pricing analysis (flowcart)](https://www.flowcart.ai/blog/wati-pricing), [Capterra](https://www.capterra.com/p/204314/WATI/)
- Interakt — [interakt.shop](https://www.interakt.shop/whatsapp-business-api/free/overview/), [Pricing (US)](https://www.interakt.shop/pricing-us/), [respond.io review](https://respond.io/blog/interakt-review)
- Respond.io — [respond.io](https://respond.io/), [Team Inbox](https://respond.io/team-inbox), [AI Agents](https://respond.io/ai-agents), [Chatimize review](https://chatimize.com/reviews/respond-io/)
- Gallabox — [gallabox.com](https://gallabox.com/), [Docs: Manage Inbox](https://docs.gallabox.com/conversations/manage-inbox), [G2](https://www.g2.com/products/gallabox/reviews)
- Zoko — [zoko.io](https://www.zoko.io/), [respond.io review](https://respond.io/blog/zoko-review)
- Twilio WhatsApp — [twilio.com/docs/whatsapp](https://www.twilio.com/docs/whatsapp), [API overview](https://www.twilio.com/docs/whatsapp/api)
- Meta WhatsApp Cloud API — [Pricing docs](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing), [Status webhooks](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/reference/messages/status), [Set up webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/set-up-webhooks/), [Pricing 2026 analysis (Blueticks)](https://blueticks.co/blog/whatsapp-business-api-pricing-2026)
