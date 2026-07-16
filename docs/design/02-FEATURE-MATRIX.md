# Expanded Feature Matrix
### Self-Hosted WhatsApp Business Platform

| | |
|---|---|
| **Document** | 2 of 8 — Expanded Feature Matrix |
| **Version** | 1.0 — **FROZEN** |
| **Date** | 2026-07-15 |
| **Status** | ✅ Approved & frozen — do not edit; record changes in `CHANGELOG.md` |
| **Preceded by** | Doc 1 — SRS (v1.0, frozen) |
| **Followed by** | Doc 3 — Database Design |

> This is the **feature bible**: a comprehensive catalog of every capability found across the
> reference platforms and the Official Meta Cloud API, with an explicit decision and delivery
> phase for each. It expands the research-phase matrix into a formal, traceable specification
> and is the master checklist we build against.

---

## How to read this document

**Platform columns** — which reference platforms publicly offer the feature (research as of 2026-07; approximate):

| Code | Platform | | Code | Platform |
|---|---|---|---|---|
| **AS** | AiSensy | | **GB** | Gallabox |
| **WT** | WATI | | **ZK** | Zoko |
| **IN** | Interakt | | **TW** | Twilio (WhatsApp) |
| **RI** | Respond.io | | **META** | Native in Meta Cloud API |

**Cloud API feasibility** — ✅ Native (Cloud API provides it directly) · 🟨 App-side (we build it; API permits it) · 🔶 Partial (API constrains it) · ⛔ Not possible via official API.

**Our decision** — ✅ **Include** · ⭐ **Improve** (we go beyond the best reference) · ⏭ **Later** (in architecture now, built post-v1.0) · ❌ **Excluded** (with reason).

**Phase** — delivering module (Doc 8 roadmap). **SRS** — traceability to Doc 1 requirement IDs.

---

## A. Onboarding, WABA & Phone Number Management

| # | Feature | Platforms | Best | Cloud API | Our decision | Phase | SRS |
|---|---|---|---|---|---|---|---|
| A1 | Connect multiple **WABAs** | RI, WT, IN | RI | ✅ | ✅ Include | 4 | FR-WA-01 |
| A2 | Manage multiple **phone numbers** per WABA | RI, WT, IN, AS | RI | ✅ | ✅ Include | 4 | FR-WA-02 |
| A3 | Secure token/credential storage (encrypted) | all | — | 🟨 | ⭐ Improve (encrypt at rest, rotate) | 4 | FR-WA-03, NFR-SEC-08 |
| A4 | **Quality rating** display (green/yellow/red) | WT, IN, RI | RI | ✅ | ✅ Include | 4 | FR-WA-04 |
| A5 | **Messaging tier / limit** display & tracking | WT, IN | WT | ✅ | ⭐ Improve (auto-throttle to tier) | 4/6 | FR-WA-04, FR-WA-13 |
| A6 | Phone number status / registration health | WT, IN, RI | RI | ✅ | ✅ Include | 4 | FR-WA-04 |
| A7 | Display-name & profile management | AS, WT, IN | WT | ✅ | ✅ Include | 4 | FR-WA-04 |
| A8 | Embedded signup / self-onboarding flow | WT, IN, RI | RI | 🔶 | ⏭ Later (manual token setup for v1.0) | later | — |

## B. Authentication, Users, Roles, Permissions

| # | Feature | Platforms | Best | Cloud API | Our decision | Phase | SRS |
|---|---|---|---|---|---|---|---|
| B1 | Email/password login | all | — | 🟨 | ✅ Include (Argon2id) | 1 | FR-AUTH-01 |
| B2 | JWT access + refresh, rotation | all | — | 🟨 | ⭐ Improve (server-side revocation) | 1 | FR-AUTH-02/03 |
| B3 | Multi-user / multi-agent | all | RI | 🟨 | ✅ Include (unlimited) | 1 | FR-AUTH-07 |
| B4 | Roles (agent/admin/manager) | WT, IN, RI | RI | 🟨 | ⭐ Improve (fully custom roles) | 1 | FR-AUTH-05/08 |
| B5 | Granular permissions | RI | RI | 🟨 | ⭐ Improve (`resource:action` per route) | 1 | FR-AUTH-05/06 |
| B6 | Password policy + lockout | WT, RI | RI | 🟨 | ✅ Include | 1 | FR-AUTH-04 |
| B7 | Two-factor auth (TOTP) | RI, WT | RI | 🟨 | ⏭ Later | 10 | FR-AUTH-10 |
| B8 | Session/device management | RI | RI | 🟨 | ✅ Include | 1/10 | NFR-SEC-06 |

## C. Contacts, Audience & Segmentation

| # | Feature | Platforms | Best | Cloud API | Our decision | Phase | SRS |
|---|---|---|---|---|---|---|---|
| C1 | Contact CRM (unlimited contacts) | IN, all | IN | 🟨 | ⭐ Improve (unlimited, 1M+ scale) | 3 | FR-CON-01/02 |
| C2 | **CSV import** (column mapping, validation) | all | WT | 🟨 | ✅ Include | 3 | FR-CON-03 |
| C3 | **Excel import** | IN, WT | IN | 🟨 | ✅ Include | 3 | FR-CON-04 |
| C4 | Async import w/ progress + error report | WT, IN | WT | 🟨 | ⭐ Improve (streamed, 10k/min) | 3 | FR-CON-05, NFR-PERF-08 |
| C5 | **Duplicate detection** (phone normalize) | WT | WT | 🟨 | ⭐ Improve (E.164 + merge/skip/overwrite) | 3 | FR-CON-06 |
| C6 | **Bulk edit** (tags/attributes) | WT, IN | WT | 🟨 | ✅ Include | 3 | FR-CON-07 |
| C7 | **Bulk delete** (soft) | WT, IN | WT | 🟨 | ✅ Include (audited) | 3 | FR-CON-08 |
| C8 | **Tags** | AS, WT, IN, GB | GB | 🟨 | ⭐ Improve (unlimited; AS caps free tier at 10) | 3 | FR-CON-09 |
| C9 | **Segments** (dynamic filters) | AS, IN | AS | 🟨 | ✅ Include (reusable in campaigns) | 3 | FR-CON-10 |
| C10 | **Custom attributes** (typed) | AS, IN, GB | IN | 🟨 | ⭐ Improve (unlimited typed; AS caps free at 5) | 3 | FR-CON-11 |
| C11 | **Advanced search + filters** (AND/OR) | RI | RI | 🟨 | ⭐ Improve (composable groups) | 3 | FR-CON-12, FR-UX-04 |
| C12 | **Opt-in / opt-out** tracking + auto-STOP | IN, WT | IN | 🟨 | ⭐ Improve (auto-suppress on STOP) | 3 | FR-CON-13, CMP-02/03 |
| C13 | Contact activity timeline | RI, IN | RI | 🟨 | ✅ Include | 3 | FR-CON-14 |
| C14 | Export contacts/segments (CSV/Excel/JSON) | WT, IN | WT | 🟨 | ✅ Include | 3 | FR-CON-15 |

## D. Templates & Media

| # | Feature | Platforms | Best | Cloud API | Our decision | Phase | SRS |
|---|---|---|---|---|---|---|---|
| D1 | Sync templates + approval status from Meta | WT, IN, AS | WT | ✅ | ✅ Include | 5 | FR-TPL-01/03 |
| D2 | Create/submit templates (all components) | WT, IN | IN | ✅ | ✅ Include | 5 | FR-TPL-02 |
| D3 | Interactive: reply buttons / list / CTA-URL | IN, AS | IN | ✅ | ✅ Include | 5 | FR-TPL-04 |
| D4 | Up to 10 buttons / quick replies | IN | IN | ✅ | ✅ Include | 5 | FR-TPL-04 |
| D5 | WhatsApp **Flows** in templates | RI, IN | RI | ✅ | ⏭ Later (architecture-ready) | 5/later | FR-TPL-05, NFR-EXT-01 |
| D6 | Media headers (image/video/doc) | AS, WT, IN | — | ✅ | ✅ Include | 5 | FR-TPL-04, FR-MED-01..04 |
| D7 | Template preview with sample vars | WT, IN | WT | 🟨 | ✅ Include | 5 | FR-TPL-08 |
| D8 | **Media library** (reuse, organize) | AS, ZK | AS | 🟨 | ⭐ Improve (hash dedupe, ID cache) | 5 | FR-TPL-06, FR-MED-05/07 |
| D9 | Media type/size validation | — | — | 🟨 | ✅ Include | 5 | FR-TPL-07, FR-MED-01..04 |
| D10 | Pluggable media storage (local/S3) | — | — | 🟨 | ⭐ Improve (own your storage) | 5 | FR-MED-06 |

## E. Messaging Capabilities (message types)

| # | Feature | Platforms | Best | Cloud API | Our decision | Phase | SRS |
|---|---|---|---|---|---|---|---|
| E1 | Template (business-initiated) messages | all | — | ✅ | ✅ Include | 4 | FR-WA-10 |
| E2 | Free-form text (in 24h window) | all | — | ✅ | ✅ Include | 4 | FR-WA-10/12 |
| E3 | Media messages (image/video/doc/audio) | all | — | ✅ | ✅ Include | 4 | FR-WA-10 |
| E4 | Interactive messages (buttons/list/CTA) | IN, AS | IN | ✅ | ✅ Include | 4 | FR-WA-10 |
| E5 | Reactions (emoji) | RI | RI | ✅ | ✅ Include | 4 | FR-WA-10 |
| E6 | Location & contact messages | RI, TW | — | ✅ | ✅ Include | 4 | FR-WA-10 |
| E7 | Inbound media download & store | all | — | ✅ | ✅ Include | 4 | FR-WA-11, FR-MED-* |
| E8 | **24-hour window** enforcement | IN | IN | ✅ | ⭐ Improve (UI countdown, server block) | 4/7 | FR-WA-12, FR-INB-06 |
| E9 | Product / catalog messages | AS, ZK, IN | ZK | ✅ | ⏭ Later (commerce) | later | NFR-EXT-* |

## F. Campaign Engine (Broadcasts)

| # | Feature | Platforms | Best | Cloud API | Our decision | Phase | SRS |
|---|---|---|---|---|---|---|---|
| F1 | **Broadcast** to segment/tag/list/upload | AS, WT, IN | AS | ✅ | ✅ Include | 6 | FR-CAM-01 |
| F2 | Opt-in + template eligibility pre-checks | IN | IN | 🟨 | ⭐ Improve | 6 | FR-CAM-02 |
| F3 | **Scheduler** (timezone-aware) | AS(Pro), WT | AS | 🟨 | ⭐ Improve (standard, not paywalled) | 6 | FR-CAM-03 |
| F4 | **Recurring** campaigns | GB | GB | 🟨 | ⭐ Improve (cron-style) | 6 | FR-CAM-04 |
| F5 | **Drip / sequence** campaigns | GB, ZK | GB | 🟨 | ✅ Include | 6 | FR-CAM-04 |
| F6 | **Campaign queue** (rate-limited) | (BSP internal) | — | 🟨 | ⭐ Improve (Celery, tier-aware) | 6 | FR-CAM-05, FR-WA-13 |
| F7 | **Pause / Resume** running campaign | rare | — | 🟨 | ⭐ Improve (safe, no dupes) | 6 | FR-CAM-06 |
| F8 | **Cancel** campaign | AS, WT | — | 🟨 | ✅ Include | 6 | FR-CAM-07 |
| F9 | **Smart retry** (error-class aware, backoff) | TW-grade | TW | 🟨 | ⭐ Improve | 6 | FR-CAM-08 |
| F10 | **Resume interrupted** (crash-safe) | rare | — | 🟨 | ⭐ Improve (checkpointed) | 6 | FR-CAM-09, NFR-DR-05/07 |
| F11 | Per-recipient **message ledger** + live status | WT, IN | WT | ✅(status) | ✅ Include | 6 | FR-CAM-10 |
| F12 | **Cost calculator** (pre-send estimate) | none transparent | — | 🟨 | ⭐ Improve (real rate card) | 6 | FR-CAM-11 |
| F13 | Save campaign as reusable **template** | AS, WT | — | 🟨 | ✅ Include | 6 | FR-CAM-12 |
| F14 | Send pacing / throttle to protect quality | AS | AS | 🟨 | ⭐ Improve | 6 | FR-CAM-13, CMP-06 |
| F15 | A/B testing of template variants | RI, WT | RI | 🟨 | ⏭ Later | 8/later | — |
| F16 | Event-triggered campaigns (cart/referral) | ZK, AS | ZK | ✅(referral wh) | ⏭ Later (architecture-ready) | later | FR-CAM-14, NFR-EXT-05 |

## G. Shared Inbox & Conversations

| # | Feature | Platforms | Best | Cloud API | Our decision | Phase | SRS |
|---|---|---|---|---|---|---|---|
| G1 | **Shared team inbox** (real-time) | WT, GB, RI | RI | ✅ | ✅ Include | 7 | FR-INB-01 |
| G2 | Full conversation **history** (persisted) | all | RI | 🟨 | ✅ Include | 7 | FR-INB-02 |
| G3 | **Assignment / reassignment** | WT, GB | WT | 🟨 | ✅ Include | 7 | FR-INB-03 |
| G4 | **Quick replies / saved replies** | WT, GB | GB | 🟨 | ✅ Include (personal + shared) | 7 | FR-INB-04 |
| G5 | **Internal notes** | GB, RI | GB | 🟨 | ✅ Include | 7 | FR-INB-05 |
| G6 | Reply (free-form in window / template outside) | all | IN | ✅ | ⭐ Improve (window-aware UI) | 7 | FR-INB-06 |
| G7 | Conversation tags / status (open/pending/resolved) | WT, RI | RI | 🟨 | ✅ Include | 7 | FR-INB-07 |
| G8 | Unread counts / read indicators | all | RI | 🟨 | ✅ Include | 7 | FR-INB-08 |
| G9 | **Routing rules** (round-robin, by tag) | WT, RI | RI | 🟨 | ✅ Include | 7/10 | FR-INB-09 |
| G10 | Agent collision detection (who's typing/viewing) | RI | RI | 🟨 | ✅ Include | 7 | FR-INB-08 |
| G11 | **SLA timers** / first-response metrics | RI, WT | RI | 🟨 | ⏭ Later | 8 | FR-INB-10 |
| G12 | Conversation merging across channels | RI | RI | 🔶 | ⏭ Later (needs omnichannel) | later | NFR-EXT-02 |

## H. Automation & Chatbot

| # | Feature | Platforms | Best | Cloud API | Our decision | Phase | SRS |
|---|---|---|---|---|---|---|---|
| H1 | Keyword / rule auto-replies | WT, GB, AS | WT | 🟨 | ✅ Include | 7/9 | FR-AUT-01 |
| H2 | Business-hours / away messages | WT, GB | GB | 🟨 | ✅ Include | 7 | FR-AUT-01 |
| H3 | Auto opt-out on STOP | IN | IN | 🟨 | ✅ Include | 3/7 | FR-CON-13 |
| H4 | **Visual flow / chatbot builder** | AS, WT, GB, RI | RI | 🟨 | ⏭ Later (event-bus ready) | later | FR-AUT-02, NFR-EXT-05 |
| H5 | Auto-assignment on inbound | WT, RI | RI | 🟨 | ✅ Include | 7 | FR-INB-09 |

## I. Artificial Intelligence

| # | Feature | Platforms | Best | Cloud API | Our decision | Phase | SRS |
|---|---|---|---|---|---|---|---|
| I1 | **AI reply suggestions / drafting** | RI, IN | RI | 🟨 | ✅ Include (latest Claude) | 9 | FR-AI-01 |
| I2 | **Knowledge base** + RAG answers | RI | RI | 🟨 | ✅ Include | 9 | FR-AI-02 |
| I3 | **Conversation summarization** | RI | RI | 🟨 | ✅ Include | 9 | FR-AI-03 |
| I4 | **AI campaign generator** | (emerging) | — | 🟨 | ⭐ Improve | 9 | FR-AI-05 |
| I5 | **AI template generator** (compliant) | (emerging) | — | 🟨 | ⭐ Improve | 9 | FR-AI-06 |
| I6 | **AI auto-tagging** | RI | RI | 🟨 | ✅ Include | 9 | FR-AI-07 |
| I7 | **AI sentiment analysis** | RI | RI | 🟨 | ✅ Include | 9 | FR-AI-08 |
| I8 | **AI translation** | RI | RI | 🟨 | ✅ Include | 9 | FR-AI-09 |
| I9 | Autonomous AI agents that act | RI, IN(Haptik) | RI | 🟨 | ⏭ Later (after flow engine) | later | NFR-EXT-04 |
| I10 | **Human approval before AI sends** (hard rule) | (safety) | — | 🟨 | ⭐ Improve (never auto-send; audited) | 9 | FR-AI-04/10 |

## J. Analytics & Reporting

| # | Feature | Platforms | Best | Cloud API | Our decision | Phase | SRS |
|---|---|---|---|---|---|---|---|
| J1 | **Delivery / read / failure** reports | WT, IN | WT | ✅ | ✅ Include | 8 | FR-AN-01 |
| J2 | **Campaign analytics** (rates over time) | AS(Pro), WT | WT | 🟨 | ⭐ Improve (standard, drill-down) | 8 | FR-AN-02 |
| J3 | **Cost analytics** (real spend breakdown) | none transparent | — | 🟨 | ⭐ Improve (rate-card exact) | 8 | FR-AN-03 |
| J4 | **Click / URL tracking** (link shortener) | BSP link-wrap | — | 🟨 | ⭐ Improve (first-party) | 8 | FR-AN-04 |
| J5 | **Real-time dashboard** + live stats | RI | RI | 🟨 | ⭐ Improve (webhook-driven) | 2/8 | FR-AN-05, NFR-PERF-06 |
| J6 | Agent performance reports | WT, RI | RI | 🟨 | ✅ Include | 8 | FR-AN-02 |
| J7 | Failure analysis by Meta error code | — | — | ✅ | ⭐ Improve (grouped + guidance) | 8 | FR-AN-07 |
| J8 | Exportable reports (CSV/Excel/JSON) | WT, IN | WT | 🟨 | ✅ Include | 8 | FR-AN-06 |
| J9 | Funnels / conversion attribution | RI | RI | 🟨 | ⏭ Later | later | — |

## K. Integrations & Developer API

| # | Feature | Platforms | Best | Cloud API | Our decision | Phase | SRS |
|---|---|---|---|---|---|---|---|
| K1 | **Webhook management** (verify, async) | TW | TW | ✅ | ⭐ Improve (dead-letter + replay) | 4 | FR-WA-05/08 |
| K2 | Outbound webhooks to company systems | GB, RI | RI | 🟨 | ✅ Include | 10 | FR-ADM-07 |
| K3 | Public REST API (for own integrations) | TW, WT, IN | TW | 🟨 | ✅ Include (our API is first-class) | 4+ | Doc 4 |
| K4 | CRM / Zapier / Sheets connectors | WT, GB, RI | RI | 🟨 | ⏭ Later | later | — |
| K5 | E-commerce (Shopify/Woo) connectors | ZK, IN, GB, AS | ZK | 🟨 | ⏭ Later (commerce) | later | NFR-EXT-05 |

## L. Commerce (deferred domain — architecture-ready)

| # | Feature | Platforms | Best | Cloud API | Our decision | Phase | SRS |
|---|---|---|---|---|---|---|---|
| L1 | Product **catalog** | AS, ZK, IN | ZK | ✅ | ⏭ Later | later | NFR-EXT-05 |
| L2 | Abandoned-cart recovery | ZK, AS | ZK | 🟨 | ⏭ Later | later | FR-CAM-14 |
| L3 | COD confirmation / order flows | ZK | ZK | 🟨 | ⏭ Later | later | FR-CAM-14 |
| L4 | **WhatsApp Pay** / payments | IN, AS | IN | 🔶 (region) | ❌ Excluded for now (region-limited) | — | out-of-scope |
| L5 | Click-to-WhatsApp **Ads** manager | AS | AS | 🔶 (Ads API) | ⏭ Later (separate Meta Ads API) | later | — |

## M. Notifications & Alerts

| # | Feature | Platforms | Best | Cloud API | Our decision | Phase | SRS |
|---|---|---|---|---|---|---|---|
| M1 | In-app notifications | WT, RI | RI | 🟨 | ✅ Include | 10 | FR-ADM-07 |
| M2 | Email / webhook alerts (failures, quality drop) | WT | WT | 🟨 | ✅ Include | 10 | FR-ADM-07, FR-MON-10 |
| M3 | Quality-rating / limit-change alerts | WT, IN | WT | ✅ | ⭐ Improve | 10 | FR-MON-02..08 |

## N. Administration & Operations

| # | Feature | Platforms | Best | Cloud API | Our decision | Phase | SRS |
|---|---|---|---|---|---|---|---|
| N1 | Settings (org, security, notifications) | all | RI | 🟨 | ✅ Include | 10 | FR-ADM-01 |
| N2 | **Audit logs** (who/what/when) | RI (enterprise) | RI | 🟨 | ⭐ Improve (immutable, tamper-evident) | 10 | FR-ADM-02, NFR-SEC-07 |
| N3 | **System logs** (structured, queryable) | — | — | 🟨 | ✅ Include | 10 | FR-ADM-03 |
| N4 | **Performance monitoring** (all subsystems) | — | — | 🟨 | ⭐ Improve (queue/Celery/Redis/MySQL/API/webhook) | 10 | FR-ADM-04, FR-MON-01..10 |
| N5 | **Backup** (scheduled) | SaaS-managed | — | 🟨 | ⭐ Improve (you own it) | 10 | FR-ADM-05, NFR-DR-01 |
| N6 | **Restore** (guided + verified) | SaaS-managed | — | 🟨 | ⭐ Improve (test-restore) | 10 | FR-ADM-06, NFR-DR-04 |
| N7 | Global exports (CSV/Excel/JSON) | WT, IN | WT | 🟨 | ✅ Include | 10 | FR-ADM-08 |
| N8 | Data retention + auto-cleanup | enterprise | — | 🟨 | ⭐ Improve (per-class policies) | 10 | FR-DL-05/06 |
| N9 | Archive / soft-delete / hard-delete / erasure | enterprise | — | 🟨 | ⭐ Improve (full lifecycle) | 3/10 | FR-DL-01..08 |
| N10 | DB **partitioning** for scale | — | — | 🟨 | ⭐ Improve (time-partitioned ledger) | 3/6 | FR-DL-07, NFR-PERF-05 |

## O. Platform UX

| # | Feature | Platforms | Best | Cloud API | Our decision | Phase | SRS |
|---|---|---|---|---|---|---|---|
| O1 | **Dark mode** | RI | RI | 🟨 | ✅ Include | 2 | FR-UX-02 |
| O2 | **Responsive** (desktop/tablet/mobile) | all | RI | 🟨 | ✅ Include | 2 | FR-UX-01 |
| O3 | **Keyboard shortcuts** / command palette | RI | RI | 🟨 | ⭐ Improve | 2 | FR-UX-03 |
| O4 | **Global search** | RI | RI | 🟨 | ✅ Include | 2/8 | FR-UX-04 |
| O5 | **Loading skeletons** / optimistic UI | RI | RI | 🟨 | ✅ Include | 2 | FR-UX-07 |
| O6 | **Infinite scroll / virtualized lists** | RI, WT | RI | 🟨 | ✅ Include | 2/3 | FR-UX-08 |
| O7 | Design-system consistency | RI | RI | 🟨 | ⭐ Improve (tokens + component lib) | 2 | FR-UX-05 |
| O8 | Accessibility (WCAG 2.1 AA) | RI | RI | 🟨 | ✅ Include | 2 | FR-UX-06 |
| O9 | Multi-language UI (i18n) | RI, WT | RI | 🟨 | ⏭ Later | later | — |

## P. Security & Compliance

| # | Feature | Platforms | Best | Cloud API | Our decision | Phase | SRS |
|---|---|---|---|---|---|---|---|
| P1 | Opt-in enforcement | IN | IN | 🟨 | ⭐ Improve | 3/6 | CMP-02 |
| P2 | Opt-out / STOP handling | IN, WT | IN | 🟨 | ⭐ Improve (auto-suppress) | 3 | CMP-03 |
| P3 | 24-hour window compliance | IN | IN | ✅ | ⭐ Improve (enforced) | 4/7 | CMP-04, FR-WA-12 |
| P4 | Messaging-limit / quality compliance | WT, IN | WT | ✅ | ⭐ Improve (auto-throttle, pause on red) | 4/6 | CMP-06 |
| P5 | RBAC / least privilege | RI | RI | 🟨 | ⭐ Improve (granular) | 1 | FR-AUTH-05/06 |
| P6 | Encryption at rest (secrets/tokens) | all(SaaS) | — | 🟨 | ✅ Include | 4 | NFR-SEC-08 |
| P7 | CSRF / XSS / CSP / headers | all(SaaS) | — | 🟨 | ✅ Include | 1/2 | NFR-SEC-01..03 |
| P8 | Rate limiting + IP allow/block | enterprise | — | 🟨 | ✅ Include | 1/10 | NFR-SEC-04/05 |
| P9 | Data ownership / self-hosting | **none** | — | — | ⭐ **Only we do this** | all | §2.1 |

---

## Q. Coverage summary — us vs. each reference

| Platform | Their core strength | Do we match? | Where we exceed |
|---|---|---|---|
| **AiSensy** | High-volume broadcast + segmentation | ✅ Yes | Scheduling & analytics standard (not Pro-gated); exact cost engine |
| **WATI** | Shared inbox + no-code automation | ✅ Yes | No message markup; reliability (retry/resume); data ownership |
| **Interakt** | Rich interactive messages + unlimited contacts | ✅ Yes | Granular RBAC; cost transparency |
| **Respond.io** | Automation depth + reporting + inbox polish | ✅ Core, ⏭ flow builder later | Self-hosted; cost analytics; no per-seat pricing |
| **Gallabox** | Notes + saved replies + drip | ✅ Yes | Crash-safe campaigns; monitoring depth |
| **Zoko** | Shopify commerce | ⏭ Later (architecture-ready) | Not our v1 focus; designed not to preclude it |
| **Twilio** | Programmable API + reliability | ✅ Match rigor | Full product UI Twilio omits; visual everything |

**Net:** we reach **feature parity or better on every item in the brief**, ship everything competitors paywall as **standard**, and hold three durable advantages no reseller can match — **exact cost analytics, crash-safe campaign reliability, and full data ownership**.

---

## R. Phase rollup (what each phase delivers — detail in Doc 8)

| Phase | Module | Feature groups delivered |
|---|---|---|
| 1 | Foundation + Auth & RBAC | B1–B8, FR-MON-09, security baseline (P5–P8) |
| 2 | Frontend shell + Auth UI + Dashboard skeleton | O1–O8, J5 (skeleton) |
| 3 | Contacts | C1–C14, P1–P2, FR-DL-01/07 |
| 4 | WhatsApp Core (WABA/numbers/webhooks/send/receive/media) | A1–A7, E1–E8, K1, P3–P4/P6 |
| 5 | Templates + Media Library | D1–D10 |
| 6 | Campaigns | F1–F14, cost engine, throttling |
| 7 | Shared Inbox | G1–G10, H1–H3/H5 |
| 8 | Analytics & Reporting | J1–J8, F15(A/B start) |
| 9 | AI Assistant + Knowledge Base | I1–I8, I10 |
| 10 | Admin & Ops | M1–M3, N1–N10, FR-MON-01..10, B7, FR-DL-* |
| 11 | Hardening & Deployment | E2E, load tests, security review, deploy |
| Post-v1.0 | Extensions | H4 flow builder, L1–L3/L5 commerce, G12/I9 omnichannel & agents, K4–K5 connectors, O9 i18n |

---

## S. Self-review record
Applied before presenting:
- **Every brief feature catalogued** and cross-checked against Doc 1 SRS IDs (traceability column complete). ✔
- **Every researched competitor capability** represented — including ones outside the brief (commerce, flow builder, ads) marked ⏭ Later so nothing valuable is lost. ✔
- **Cloud API feasibility validated** per row; nothing marked Include that the official API can't support; unofficial-API features excluded (none present). ✔
- **Compliance features are first-class** (Section P), not afterthoughts. ✔
- **Phasing is consistent** with the roadmap and dependencies (e.g., campaigns after core + templates). ✔
- **No paywall inheritance:** features competitors gate behind premium tiers are all marked ✅/⭐ standard. ✔

---

*End of Document 2 — Expanded Feature Matrix. Awaiting owner approval before generating Document 3 (Database Design).*
