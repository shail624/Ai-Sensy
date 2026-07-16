# Software Requirements Specification (SRS)
### Self-Hosted WhatsApp Business Platform

| | |
|---|---|
| **Document** | 1 of 8 — Software Requirements Specification |
| **Version** | 1.0 — **FROZEN** (authoritative baseline) |
| **Date** | 2026-07-15 (frozen after owner-requested enhancement pass) |
| **Status** | ✅ Approved & frozen — authoritative specification for the project |
| **Owner** | Internal (single-company, self-hosted) |
| **Preceded by** | `docs/research/COMPETITOR_ANALYSIS.md`, `docs/research/FEATURE_MATRIX.md` |
| **Followed by** | Doc 2 — Expanded Feature Matrix |

> **Reading note for a non-developer:** Sections **1, 2, and 7** are plain-language and
> tell you *what* the system does and the rules it must obey. Sections **3–6** are the
> engineering detail. Every requirement has an **ID** (e.g., `FR-CAM-04`), a **priority**
> (Must / Should / Could), and a **Phase** (which module delivers it). You approve the
> *what*; the *how* is my responsibility.

---

## 1. Introduction

### 1.1 Purpose
This document defines the complete requirements for a **production-grade, self-hosted
WhatsApp Business Platform** for internal company use. It is the authoritative statement
of *what* the system must do and the qualities it must have. It is the reference against
which every later design document, module, and test is measured.

### 1.2 Product summary
A single-tenant web application that connects **directly to the Official Meta WhatsApp
Cloud API** to run WhatsApp marketing and support operations: manage contacts, build and
send broadcast campaigns, operate a shared team inbox, automate replies, and analyze
delivery and cost — all without a third-party reseller and without per-message markup.

### 1.3 Scope

**In scope (this program of work):**
- Authentication, users, roles, granular permissions (RBAC).
- Contact management: import (CSV/Excel), duplicate detection, bulk operations, tags,
  segments, custom attributes, advanced search/filters.
- Template & media management synced with Meta.
- Broadcast campaign engine: scheduling, recurrence, queueing, pause/resume, smart retry,
  resume-interrupted, cost calculator.
- WhatsApp infrastructure: multiple WABAs, multiple phone numbers, webhook management,
  quality/limit monitoring, webhook-based active detection.
- Shared inbox: conversations, history, quick replies, internal notes, assignment,
  24-hour window awareness.
- Automation (rule/keyword based) and, in a later phase, a **visual flow builder**.
- AI Assistant + Knowledge Base (suggested/drafted replies, RAG answers).
- Analytics: delivery/read/failure, campaign, cost, click/URL tracking, real-time dashboard.
- Administration & operations: audit logs, system logs, performance monitoring, backup &
  restore, settings, notifications, exports (CSV/Excel/JSON).
- Platform UX: responsive design, dark mode, keyboard shortcuts.

**In scope for architecture, later phase for implementation** (per owner's directive to
design for everything valuable and Cloud-API-feasible without future rewrites):
- Visual chatbot / flow builder (WhatsApp Flows + internal automation graph).
- Commerce: product catalog messages, cart/order-event triggered campaigns.
- Click-to-WhatsApp Ads attribution (referral webhooks).
- Channel abstraction that does not preclude future **omnichannel** (Instagram, Messenger)
  via other official Meta APIs.

**Out of scope (explicitly excluded):**
- Anything requiring **unofficial WhatsApp APIs**, web-scraping, or unofficial libraries.
- Any feature violating Meta WhatsApp Business Platform policies.
- Reselling, multi-company SaaS tenancy, or public sign-up.
- Payment processing beyond WhatsApp-native payment message types (deferred; region-limited).

### 1.4 Definitions & glossary

| Term | Meaning |
|---|---|
| **Cloud API** | Meta's official WhatsApp Business Cloud API (Meta-hosted). |
| **WABA** | WhatsApp Business Account — container for phone numbers and templates. |
| **Phone Number ID** | Meta identifier for a registered sending number. |
| **Template** | Pre-approved message format required for business-initiated messages. |
| **Category** | Template/message class: marketing, utility, authentication, service. |
| **Service window / 24-hour window** | Period after a user's inbound message during which free-form (non-template) replies are allowed. |
| **Messaging tier / limit** | Meta cap on unique customers messaged per rolling 24h (1K/10K/100K/unlimited). |
| **Quality rating** | Meta health signal per number (green/yellow/red). |
| **Opt-in / Opt-out** | User's recorded consent / withdrawal to receive messages. |
| **Segment** | Dynamic, filter-defined group of contacts. |
| **Campaign** | A broadcast of a template to an audience, one-off or recurring. |
| **BSP** | Business Solution Provider (reseller) — we are **not** one; we connect directly. |
| **RBAC** | Role-Based Access Control. |
| **RPO / RTO** | Recovery Point / Time Objective (backup/restore targets). |

### 1.5 References
- Meta WhatsApp Cloud API documentation (pricing, webhooks, templates, messaging limits).
- Competitor research: `docs/research/COMPETITOR_ANALYSIS.md`, `docs/research/FEATURE_MATRIX.md`.
- OWASP ASVS (security), IEEE-830 (SRS structure, adapted).

---

## 2. Overall Description

### 2.1 Product perspective
The platform is **self-hosted** and **single-tenant**: it runs on the company's own
infrastructure via Docker, stores all data in the company's own MySQL database, and talks
directly to Meta. There is no intermediary. This yields three defining properties:
**(1)** no reseller subscription or message markup, **(2)** full data ownership, and
**(3)** the ability to compute exact costs from Meta's public rate card.

### 2.2 System context

```
        ┌────────────────────────────────────────────────────────────┐
        │                    Company infrastructure                    │
        │                                                              │
  Staff │   Browser ──HTTPS──►  Nginx ──►  Frontend (React SPA)        │
  users │                          │                                   │
        │                          └──►  Backend API (FastAPI)         │
        │                                   │      │        │          │
        │                             MySQL │ Redis│ Celery │          │
        │                                   │      │ workers│          │
        └───────────────────────────────────┼──────┼────────┼─────────┘
                                             │      │        │
                    outbound  ◄──────────────┘      │        └──► outbound sends
              (send messages, manage templates)     │
                                                     ▼
                              ┌──────────────────────────────────┐
   Meta  ── inbound webhooks ─►   Official Meta WhatsApp Cloud API │
 servers  (messages, statuses) └──────────────────────────────────┘
                                             │
                                             ▼
                                     WhatsApp end users
```

### 2.3 Logical component overview
The backend is organized into cohesive modules over shared infrastructure (config, DB,
security, logging). Full detail is in Doc 3 (DB) and Doc 4 (API); the deployment/runtime
view is in Doc 7.

- **Identity & Access** — auth, users, roles, permissions, sessions.
- **Contacts** — contacts, tags, segments, custom attributes, import/export, dedup.
- **Messaging Core** — WABA/number registry, template & media sync, Cloud API client,
  webhook ingestion, message ledger.
- **Campaigns** — builder, scheduler, queue orchestration, retry/resume, cost engine.
- **Inbox** — conversations, assignment, quick replies, notes, window tracking.
- **Automation** — keyword/rule engine now; visual flow engine later.
- **AI & Knowledge** — assistant, knowledge base, retrieval.
- **Analytics** — reporting, cost analytics, click tracking, real-time metrics.
- **Administration** — settings, audit, system logs, monitoring, backup/restore, notifications.

### 2.4 User classes (default roles — fully customizable)

| Role | Description | Typical permissions |
|---|---|---|
| **Owner** | Superuser; the business owner. | Everything, including settings, numbers, billing view, user management. |
| **Administrator** | Runs the platform day to day. | Manage users/roles, numbers, templates, settings; no destructive billing. |
| **Campaign Manager** | Marketing operator. | Contacts, segments, templates, campaigns, analytics. |
| **Agent** | Front-line support. | Inbox, conversations, quick replies, notes; assigned chats only (configurable). |
| **Analyst** | Read-only insights. | Dashboards, analytics, reports, exports. |
| **Auditor** | Compliance/oversight. | Audit logs, system logs (read-only). |

Roles are **presets**, not hard-coded tiers — administrators can create custom roles and
assign any subset of granular permissions (`resource:action`).

### 2.5 Operating environment
- **Server:** Linux host running Docker + Docker Compose (Nginx, FastAPI/uvicorn, MySQL 8,
  Redis 7, Celery worker + beat).
- **Clients:** Evergreen desktop browsers (Chrome, Edge, Firefox, Safari); responsive to
  tablet and mobile widths.
- **Runtime:** Python 3.13 (backend), Node build toolchain for the React/TypeScript frontend.

### 2.6 Design & implementation constraints
- **Tech stack is fixed:** FastAPI, SQLAlchemy 2.0 (async), Alembic, MySQL, Redis, Celery,
  Pydantic v2, httpx; React + TypeScript + Vite + TailwindCSS + React Query + Chart.js;
  Docker/Compose/Nginx; JWT + RBAC.
- **Official API only:** all WhatsApp interaction via the Meta Cloud API. No unofficial APIs.
- **Meta policy compliance is mandatory** (Section 7).
- **Clean Architecture, SOLID, Repository pattern, DI, async, type-safety** throughout.
- **No secrets in code**; configuration via environment.

### 2.7 Assumptions & dependencies
- The company holds a verified Meta Business account, at least one **WABA**, and one or more
  registered phone numbers with system-user access tokens.
- A public HTTPS endpoint is available for Meta to deliver webhooks.
- An SMTP server (optional) is available for email notifications.
- An AI model provider (default: latest Claude models) is available for the AI Assistant.
- Recipients are messaged only with valid **opt-in**; the company is responsible for consent.

---

## 3. Functional Requirements

Priority = **M**ust / **S**hould / **C**ould. **Phase** = delivery module (see Doc 8).
IDs are stable and will be traced through design, code, and tests.

### 3.1 Authentication & Access Control (AUTH)

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-AUTH-01 | Users authenticate with email + password; passwords stored using Argon2id. | M | 1 |
| FR-AUTH-02 | Issue short-lived JWT access tokens and long-lived refresh tokens; refresh rotation. | M | 1 |
| FR-AUTH-03 | Logout invalidates the active refresh token (server-side revocation list). | M | 1 |
| FR-AUTH-04 | Enforce password policy (length, complexity) and lockout after repeated failures. | M | 1 |
| FR-AUTH-05 | RBAC: users have roles; roles have granular `resource:action` permissions. | M | 1 |
| FR-AUTH-06 | Every protected endpoint enforces required permission(s); Owner bypasses via superuser. | M | 1 |
| FR-AUTH-07 | Admins manage users (create, edit, deactivate, reset password, assign roles). | M | 1 |
| FR-AUTH-08 | Admins manage custom roles and permission assignments. | M | 1 |
| FR-AUTH-09 | Self-service profile: change own name, password; view own sessions. | S | 1 |
| FR-AUTH-10 | Optional two-factor authentication (TOTP). | C | 10 |

### 3.2 Contacts, Tags, Segments, Attributes (CON)

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-CON-01 | CRUD contacts with WhatsApp phone (E.164 normalized), name, locale, and metadata. | M | 3 |
| FR-CON-02 | Unlimited contacts; list is paginated, sortable, and fast at 1M+ rows. | M | 3 |
| FR-CON-03 | Import from CSV with column mapping and per-row validation. | M | 3 |
| FR-CON-04 | Import from Excel (`.xlsx`) with the same mapping/validation. | M | 3 |
| FR-CON-05 | Large imports run asynchronously with progress and an error report. | M | 3 |
| FR-CON-06 | Duplicate detection on normalized phone (and configurable keys) with skip/merge/overwrite. | M | 3 |
| FR-CON-07 | Bulk edit (add/remove tags, set attributes) across a selection or a whole filter. | M | 3 |
| FR-CON-08 | Bulk delete (soft delete) with confirmation and audit. | M | 3 |
| FR-CON-09 | Unlimited **tags**; assign/remove; filter by tags. | M | 3 |
| FR-CON-10 | **Segments**: reusable, dynamic filters over attributes/tags/engagement/opt-in. | M | 3 |
| FR-CON-11 | Unlimited typed **custom attributes** (text/number/date/boolean/enum). | M | 3 |
| FR-CON-12 | Advanced search + composable filters (AND/OR groups). | M | 3 |
| FR-CON-13 | Opt-in/opt-out status per contact; automatic opt-out on user "STOP" keyword. | M | 3 |
| FR-CON-14 | Contact activity timeline (messages, campaigns, status changes). | S | 3 |
| FR-CON-15 | Export contacts/segment to CSV/Excel/JSON. | M | 3 |

### 3.3 Templates & Media (TPL)

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-TPL-01 | Sync templates and their approval status from Meta per WABA. | M | 5 |
| FR-TPL-02 | Create/submit templates (category, language, header/body/footer/buttons, variables). | M | 5 |
| FR-TPL-03 | Track approval state (approved/pending/rejected) and rejection reasons. | M | 5 |
| FR-TPL-04 | Support interactive components: reply buttons, list, CTA-URL, quick replies, up to Meta limits. | M | 5 |
| FR-TPL-05 | Support WhatsApp Flows references in templates (architecture-ready). | S | 5/later |
| FR-TPL-06 | Media library: upload, store, dedup by hash, reuse; cache Meta media IDs. | M | 5 |
| FR-TPL-07 | Validate media type/size against Cloud API limits before upload. | M | 5 |
| FR-TPL-08 | Preview a template with sample variable values before use. | S | 5 |

### 3.4 WhatsApp Infrastructure (WA)

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-WA-01 | Register and manage multiple **WABAs**. | M | 4 |
| FR-WA-02 | Register and manage multiple **phone numbers** per WABA. | M | 4 |
| FR-WA-03 | Store credentials/tokens securely (encrypted at rest). | M | 4 |
| FR-WA-04 | Display each number's **quality rating**, **messaging tier/limit**, and status. | M | 4 |
| FR-WA-05 | Webhook endpoint: verify Meta signature; respond `200` immediately; process async. | M | 4 |
| FR-WA-06 | Ingest inbound messages (all types) and status callbacks (sent/delivered/read/failed). | M | 4 |
| FR-WA-07 | Idempotent webhook processing (dedupe by message/status id). | M | 4 |
| FR-WA-08 | Webhook dead-letter capture + replay tooling. | S | 4 |
| FR-WA-09 | **Active detection:** mark a contact "active/reachable" on inbound webhook events. | M | 4 |
| FR-WA-10 | Send messages: template, text (in-window), media, interactive, reactions. | M | 4 |
| FR-WA-11 | Download inbound media by Meta media ID and store it. | M | 4 |
| FR-WA-12 | Enforce the **24-hour window** rule server-side (block free-form outside window). | M | 4 |
| FR-WA-13 | Auto-throttle sends to stay within a number's messaging tier and MPS limit. | M | 4/6 |

### 3.5 Campaign Engine (CAM)

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-CAM-01 | Create a broadcast: choose number, template, audience (segment/tag/list/upload), variable mapping. | M | 6 |
| FR-CAM-02 | Validate audience opt-in and template eligibility before send. | M | 6 |
| FR-CAM-03 | **Schedule** a campaign for a future time (timezone-aware). | M | 6 |
| FR-CAM-04 | **Recurring** campaigns (cron-style) and **drip** sequences. | S | 6 |
| FR-CAM-05 | Enqueue per-recipient send jobs; rate-limited to Meta tier/MPS. | M | 6 |
| FR-CAM-06 | **Pause** and **Resume** a running campaign without duplicate sends. | M | 6 |
| FR-CAM-07 | **Cancel** a campaign; stop pending sends. | M | 6 |
| FR-CAM-08 | **Smart retry**: classify Cloud API errors; retry only retryable ones with backoff. | M | 6 |
| FR-CAM-09 | **Resume interrupted** campaigns after a crash/restart from the last checkpoint. | M | 6 |
| FR-CAM-10 | Per-recipient message ledger with live status (queued→sent→delivered→read/failed). | M | 6 |
| FR-CAM-11 | **Cost calculator**: pre-send estimated spend from the rate card (by category/country). | M | 6 |
| FR-CAM-12 | Campaign templates: save a campaign config as a reusable template. | S | 6 |
| FR-CAM-13 | Throttle/spread sends to protect quality rating (configurable pacing). | S | 6 |
| FR-CAM-14 | Event-triggered campaigns (e.g., referral/order webhooks) — architecture-ready. | C | later |

### 3.6 Shared Inbox (INB)

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-INB-01 | Unified inbox of conversations across numbers; real-time updates. | M | 7 |
| FR-INB-02 | Full threaded conversation history persisted locally. | M | 7 |
| FR-INB-03 | Assign/reassign conversations; "unassigned" and "mine" views. | M | 7 |
| FR-INB-04 | **Quick replies** (canned messages), personal and shared. | M | 7 |
| FR-INB-05 | **Internal notes** visible only to staff. | M | 7 |
| FR-INB-06 | Send replies (free-form within window; template outside window) with window countdown UI. | M | 7 |
| FR-INB-07 | Conversation tags, status (open/pending/resolved), and filters. | S | 7 |
| FR-INB-08 | Typing/read indicators and unread counts. | S | 7 |
| FR-INB-09 | Assignment rules / routing (round-robin, by tag). | C | 7/10 |
| FR-INB-10 | SLA timers and first-response metrics. | C | 8 |

### 3.7 Automation & AI (AUT / AI)

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-AUT-01 | Keyword/rule auto-replies (e.g., greeting, STOP, business hours). | S | 7/9 |
| FR-AUT-02 | Visual **flow builder** for multi-step automations (WhatsApp Flows + internal graph). | C | later |
| FR-AI-01 | AI Assistant suggests/drafts replies from conversation context. | S | 9 |
| FR-AI-02 | **Knowledge Base** documents power AI answers via retrieval (RAG). | S | 9 |
| FR-AI-03 | **AI conversation summarization** of long threads (context handoff, TL;DR). | S | 9 |
| FR-AI-04 | Guardrails: AI drafts are reviewable before send by default. | M | 9 |
| FR-AI-05 | **AI campaign generator**: draft campaign copy + variable suggestions from a prompt and audience context. | S | 9 |
| FR-AI-06 | **AI template generator**: draft policy-compliant, category-aware template content for submission to Meta. | S | 9 |
| FR-AI-07 | **AI auto-tagging**: suggest/apply contact & conversation tags from message content. | C | 9 |
| FR-AI-08 | **AI sentiment analysis**: score conversation sentiment; surface it in the inbox and analytics. | C | 9 |
| FR-AI-09 | **AI translation**: translate inbound/outbound messages and reply drafts across languages. | C | 9 |
| FR-AI-10 | **Human-in-the-loop (hard rule)**: AI **never auto-sends** a customer message without explicit human approval (approval may be configured per rule); every AI action is audited. | M | 9 |

### 3.8 Analytics & Reporting (AN)

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-AN-01 | Delivery, read, and failure reports per campaign and per number. | M | 8 |
| FR-AN-02 | Campaign analytics: sent/delivered/read/failed/replied, rates, over time. | M | 8 |
| FR-AN-03 | **Cost analytics**: real spend by category, country, number, campaign, date. | M | 8 |
| FR-AN-04 | **Click/URL tracking** via first-party short links; per-link/per-contact clicks. | M | 8 |
| FR-AN-05 | Real-time dashboard with live counters driven by webhook events. | M | 2/8 |
| FR-AN-06 | Exportable reports (CSV/Excel/JSON). | M | 8 |
| FR-AN-07 | Failure analysis grouped by Meta error code with guidance. | S | 8 |

### 3.9 Administration & Operations (ADM)

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-ADM-01 | Settings: organization, numbers, security, notification preferences. | M | 10 |
| FR-ADM-02 | **Audit log**: immutable record of who changed what, when (all mutations). | M | 10 |
| FR-ADM-03 | **System logs**: structured, queryable application/error logs. | M | 10 |
| FR-ADM-04 | **Performance monitoring**: queue depth, send throughput, API latency, error rates, health. | M | 10 |
| FR-ADM-05 | **Backup**: scheduled database backups. | M | 10 |
| FR-ADM-06 | **Restore**: guided restore from a backup. | M | 10 |
| FR-ADM-07 | **Notifications**: in-app + optional email/webhook for key events (failures, quality drops). | M | 10 |
| FR-ADM-08 | Global exports (CSV/Excel/JSON) for major datasets. | M | 10 |
| FR-ADM-09 | Data retention policies (message/log retention windows). | S | 10 |

### 3.10 Platform UX (UX)

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-UX-01 | Responsive design (desktop-first; tablet/mobile usable). | M | 2 |
| FR-UX-02 | **Dark mode** with full theming and persistence. | M | 2 |
| FR-UX-03 | Global command palette + **keyboard shortcuts** for power users. | S | 2 |
| FR-UX-04 | Global advanced search across contacts/conversations/campaigns. | S | 2/8 |
| FR-UX-05 | Consistent design system (tokens, components) across all screens. | M | 2 |
| FR-UX-06 | Accessible (WCAG 2.1 AA target: focus states, contrast, keyboard nav). | S | 2 |
| FR-UX-07 | **Loading skeletons** and optimistic UI for perceived performance during fetches. | S | 2 |
| FR-UX-08 | **Infinite scrolling / virtualized lists** for large datasets (contacts, inbox, message history). | S | 2/3 |

### 3.11 Media Management (MED)

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-MED-01 | **Images** (jpg/png): validate type/size to Cloud API limits; generate thumbnails; reuse via Meta media-ID cache. | M | 5 |
| FR-MED-02 | **Video** (mp4/3gp): validate to Cloud API limits; store; stream/preview in the UI. | M | 5 |
| FR-MED-03 | **Documents** (pdf/office/text): validate to limits; preview or download in the UI. | M | 5 |
| FR-MED-04 | **Audio** (aac/mp3/amr/ogg): validate to limits; play in the UI (inbound voice notes supported). | M | 5 |
| FR-MED-05 | **Duplicate detection**: dedupe by content hash (SHA-256); one stored blob reused across templates/campaigns/messages. | M | 5 |
| FR-MED-06 | **Storage architecture**: pluggable backend — local volume by default, S3-compatible object storage optional; the database stores metadata + reference, never blobs. | M | 5 |
| FR-MED-07 | **Meta media-ID caching**: cache uploaded media IDs, handle expiry, and re-upload transparently when expired. | M | 5 |
| FR-MED-08 | **Retention policy**: configurable retention for inbound/campaign media; orphaned/expired media auto-cleaned. | S | 5/10 |
| FR-MED-09 | **Access control**: media served only to authorized users via signed, expiring URLs. | M | 5 |

### 3.12 Data Lifecycle Management (DL)

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-DL-01 | **Soft delete**: user-facing deletions are recoverable (flagged & hidden) during a grace period. | M | 3/10 |
| FR-DL-02 | **Hard delete**: permanent purge on retention expiry or explicit privacy request; safe cascades; audited. | M | 10 |
| FR-DL-03 | **Archive**: move old, low-access data (closed conversations, old campaigns) to an archived state/store. | S | 10 |
| FR-DL-04 | **Restore**: recover soft-deleted or archived records within the retention window. | S | 10 |
| FR-DL-05 | **Retention policies**: configurable per data class (messages, media, logs, audit, campaigns). | M | 10 |
| FR-DL-06 | **Automatic cleanup**: scheduled jobs enforce retention (archive/purge) with a dry-run mode and full audit. | M | 10 |
| FR-DL-07 | **Partitioning strategy**: high-volume tables (message ledger, webhook/status events, audit log) are time-partitioned (monthly range) for fast queries and cheap pruning. | M | 3/6 |
| FR-DL-08 | **Privacy erasure**: erase all data for a specific contact on request while preserving anonymized aggregates. | S | 10 |

### 3.13 Monitoring & Health (MON)

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-MON-01 | **Queue health**: per-queue depth, oldest-job age, throughput, and backlog alerts. | M | 10 |
| FR-MON-02 | **Celery worker health**: liveness, active/reserved task counts, failure rate, restarts; alert on worker loss. | M | 10 |
| FR-MON-03 | **Redis health**: connectivity, memory usage, latency, eviction rate. | M | 10 |
| FR-MON-04 | **MySQL health**: connectivity, connection count, slow queries, replication lag (if used), disk headroom. | M | 10 |
| FR-MON-05 | **API latency**: per-endpoint p50/p95/p99 and error-rate metrics. | M | 10 |
| FR-MON-06 | **Webhook latency**: ingestion-to-processed time and end-to-end status-update lag. | M | 10 |
| FR-MON-07 | **Failed-webhook monitoring**: dead-letter count, retry backlog, replay status; alert on spikes. | M | 4/10 |
| FR-MON-08 | **Campaign progress monitoring**: live per-campaign sent/delivered/read/failed + ETA; stalled-campaign alerts. | M | 6 |
| FR-MON-09 | **Health/readiness endpoints**: `/health` (liveness) and `/ready` (dependency checks) for orchestration. | M | 1 |
| FR-MON-10 | **Alerting**: thresholds route to in-app + email/webhook notifications (ties to FR-ADM-07). | S | 10 |

---

## 4. External Interface Requirements

### 4.1 User interfaces
- A single-page React application served behind Nginx; detailed screen-by-screen design in
  Doc 6. Must meet FR-UX-01…06.

### 4.2 Meta WhatsApp Cloud API interface
- **Outbound (HTTPS/httpx):** send messages (`/messages`), manage templates
  (`/message_templates`), upload/download media (`/media`), read number metadata
  (quality, tier), all authenticated with the system-user access token.
- **Inbound (webhooks):** a signed webhook endpoint receiving `messages` and `statuses`
  events. Must verify `X-Hub-Signature-256`, ack within a strict time budget, and process
  asynchronously. Must tolerate Meta's retry behavior (up to 7 days) via idempotency.
- **Rate limits:** respect per-number MPS and business-level throughput; back off on `429`.

### 4.3 Software interfaces
- **MySQL 8** (primary datastore), **Redis 7** (broker, cache, rate-limit, real-time pub/sub),
  **Celery** (async workers + beat scheduler), **SMTP** (optional email), **AI provider**
  (latest Claude models) for the assistant, **object/file storage** (local volume or S3-compatible) for media.

### 4.4 Communication interfaces
- HTTPS everywhere (TLS terminated at Nginx). WebSocket or SSE for real-time UI updates.
  Outbound webhooks (optional) for company integrations.

---

## 5. Non-Functional Requirements (NFR)

### 5.1 Performance
| ID | Requirement | Target |
|---|---|---|
| NFR-PERF-01 | Standard API read latency (p95), excluding heavy exports. | < 300 ms |
| NFR-PERF-02 | Webhook acknowledgment time. | < 200 ms (process async) |
| NFR-PERF-03 | Campaign send throughput. | Saturate Meta tier/MPS; queue not the bottleneck |
| NFR-PERF-04 | Contact list operations at scale. | Smooth at ≥ 1,000,000 contacts |
| NFR-PERF-05 | Message ledger at scale. | Efficient at ≥ 10,000,000 messages (indexed/partitioned) |
| NFR-PERF-06 | Dashboard initial load (p95, from cached aggregates). | < 1.5 s |
| NFR-PERF-07 | Campaign creation/save (configuration, excluding the send itself). | < 1 s |
| NFR-PERF-08 | CSV/Excel import throughput. | ≥ 10,000 contacts / minute (async, streamed) |
| NFR-PERF-09 | Export generation (contacts / reports). | ≥ 50,000 rows / minute; streamed, non-blocking |
| NFR-PERF-10 | Search / filter latency (p95, indexed) over the contact base. | < 500 ms at 1,000,000 contacts |
| NFR-PERF-11 | Concurrent active staff users supported. | ≥ 200 concurrent, with horizontal headroom to grow |
| NFR-PERF-12 | Maximum single campaign size. | ≥ 1,000,000 recipients per campaign (chunked & queued) |

### 5.2 Scalability
- Stateless API and workers scale horizontally; Celery worker pool scales independently of
  the web tier. Redis and MySQL are the shared state. Design must allow adding workers to
  increase send throughput without code changes.

### 5.3 Reliability & availability
- **Idempotency** on sends and webhook processing (no duplicate messages, no double-count).
- **Smart retry** with backoff for retryable errors only.
- **Resumable campaigns**: checkpointed progress survives restarts/crashes.
- Availability target **99.9%** (self-hosted best-effort); graceful degradation if Redis or
  AI provider is temporarily unavailable.

### 5.4 Security
- Argon2id password hashing; JWT with rotation and server-side refresh revocation.
- RBAC enforced on every protected route; least privilege by default.
- Secrets/tokens **encrypted at rest**; never logged; configuration via environment.
- Input validation (Pydantic) on all boundaries; output encoding on the frontend.
- Webhook signature verification; protection against replay via idempotency keys.
- Standard hardening: rate limiting, CORS policy, security headers, SQL-injection-safe ORM,
  audit trail of sensitive actions. Target **OWASP ASVS L2**.

| ID | Control | Requirement |
|---|---|---|
| NFR-SEC-01 | **CSRF** | API auth uses the `Authorization: Bearer` header (not ambient cookies), which is not CSRF-exploitable; any cookie-based surface must use `SameSite=Strict` + anti-CSRF tokens. |
| NFR-SEC-02 | **XSS** | React auto-escaping; sanitize any rich/HTML content; forbid `dangerouslySetInnerHTML` with untrusted data; escape user content in templates/notes. |
| NFR-SEC-03 | **CSP & headers** | Strict `Content-Security-Policy` (default-src 'self' + explicit allowlist), plus HSTS, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`. |
| NFR-SEC-04 | **Rate limiting** | Per-IP and per-user limits on auth and all write endpoints; exponential back-pressure and lockout on abuse. |
| NFR-SEC-05 | **IP allow/block** | Configurable IP allowlist/blocklist, applied selectively (e.g., admin and webhook surfaces). |
| NFR-SEC-06 | **Session management** | Refresh-token rotation + server-side revocation; idle and absolute timeouts; "log out of all sessions"; per-user active-session/device list. |
| NFR-SEC-07 | **Secure audit logging** | Append-only, tamper-evident audit records; actor-attributed and time-synced; minimal PII; not user-editable. |
| NFR-SEC-08 | **Secrets management** | All secrets from environment/secret store; encrypted at rest; rotatable; never in logs, error responses, or the client bundle. |

### 5.5 Compliance & privacy
- See Section 7 for Meta-specific policy. Additionally: honor opt-out immediately; support
  data export and deletion for a contact (privacy requests); configurable data retention.

### 5.6 Maintainability
- Clean Architecture layering; SOLID; repository pattern; dependency injection; typed code;
  ≥ 80% test coverage target on business logic; documented modules; Alembic-managed schema.

### 5.7 Observability
- Structured JSON logs with request/correlation IDs; metrics for queue depth, throughput,
  latency, error rates; health/readiness endpoints; audit and system log surfaces in-app.

### 5.8 Usability & accessibility
- Consistent design system; dark mode; keyboard shortcuts; responsive; WCAG 2.1 AA target.

### 5.9 Portability & operations
- Fully containerized; one-command bring-up via Docker Compose; environment-based config;
  reproducible builds; documented backup/restore; runs on any Docker-capable Linux host.

### 5.10 Data retention & backup
- **RPO ≤ 24h** (daily backups; configurable to more frequent), **RTO ≤ 1h** for restore.
- Retention windows configurable for messages, logs, and audit records.

### 5.11 Disaster Recovery & Business Continuity
| ID | Requirement | Target / behavior |
|---|---|---|
| NFR-DR-01 | Automated database backups. | Nightly full + configurable incrementals; at least one off-host/off-site copy. |
| NFR-DR-02 | Recovery Point Objective (RPO). | ≤ 24h by default; configurable to ≤ 1h using incremental backups / binlog. |
| NFR-DR-03 | Recovery Time Objective (RTO). | ≤ 1h to restore service from a verified backup. |
| NFR-DR-04 | Restore verification. | Backups periodically **test-restored** to a scratch instance with an integrity check; alert on any failure (a backup is not "good" until a restore is proven). |
| NFR-DR-05 | Database corruption recovery. | Documented runbook: detect → isolate → restore latest verified backup → reconcile → **resume interrupted campaigns from checkpoints**; no duplicate sends. |
| NFR-DR-06 | Redis failure behavior. | Redis is treated as **rebuildable state**: on loss, cache repopulates and workers reconnect; durable truth (campaign checkpoints, ledger) lives in MySQL, so no messages are lost; idempotency keys prevent double sends during recovery. |
| NFR-DR-07 | Celery worker recovery. | Crashed/restarted workers resume from durable checkpoints; in-flight tasks are idempotent and safely re-driveable; no data loss and no double send. |
| NFR-DR-08 | Graceful degradation. | If Redis / AI provider / SMTP is temporarily down, core read paths and the inbox remain available; campaign sends **pause safely** and auto-resume on recovery. |

### 5.12 Future Readiness & Extensibility
| ID | Requirement |
|---|---|
| NFR-EXT-01 | **WhatsApp Flows**: the template/message model and inbox support Flows (interactive multi-screen forms) without a schema rewrite. |
| NFR-EXT-02 | **Additional official Meta channels**: a channel abstraction (channel type on numbers/conversations/messages) lets Instagram/Messenger be added later without reworking inbox or campaigns. |
| NFR-EXT-03 | **New Meta API capabilities**: the Cloud API client is versioned and adapter-based; new message types/fields are added via adapters, not core rewrites. |
| NFR-EXT-04 | **AI enhancements**: AI features sit behind a provider-abstracted service; models/providers are swappable via configuration. |
| NFR-EXT-05 | **Additional automation modules**: automation is event-driven over an internal event bus, so new triggers/actions and a future visual flow engine plug in without touching existing modules. |
| NFR-EXT-06 | **Modular, low-coupling design**: modules communicate through service interfaces and events, enabling new modules to be added with minimal blast radius. |

---

## 6. Data Requirements (high level)
Authoritative schema is Doc 3. Principal data domains: identity (users/roles/permissions/
sessions), contacts (contacts/tags/segments/attributes/opt-in), messaging (WABAs/numbers/
templates/media), campaigns (campaigns/recipients/message-ledger), inbox (conversations/
messages/notes/quick-replies), analytics (aggregates/click-events/cost-records), and
operations (audit-log/system-log/notifications/backups). Requirements: referential
integrity, soft-delete where recovery matters, immutable audit records, indexing for the
scale targets in 5.1, and partitioning strategy for the message ledger.

---

## 7. Compliance & Policy Requirements (Meta WhatsApp Platform)

These are **mandatory** and enforced by the system where technically possible.

| ID | Requirement |
|---|---|
| CMP-01 | **Official API only.** No unofficial WhatsApp APIs, automation of the consumer app, or scraping. |
| CMP-02 | **Opt-in required.** Business-initiated messages only to contacts with recorded opt-in. |
| CMP-03 | **Honor opt-out.** Detect opt-out (e.g., "STOP") and immediately suppress further marketing. |
| CMP-04 | **Templates for business-initiated messages.** Free-form only inside the 24-hour service window. |
| CMP-05 | **Category correctness.** Templates submitted under the correct category (marketing/utility/auth). |
| CMP-06 | **Respect messaging limits & quality.** Throttle to the number's tier; surface quality drops; pause on red. |
| CMP-07 | **Rate-limit compliance.** Honor MPS and back off on `429`/throttling signals. |
| CMP-08 | **Prohibited content.** Do not facilitate content banned by Meta commerce/messaging policies. |
| CMP-09 | **Data protection.** Encrypt credentials at rest; support contact data export/deletion. |
| CMP-10 | **No misrepresentation.** Display name and templates must not impersonate or mislead. |

---

## 8. Acceptance & Traceability
- Every requirement ID is traced forward into Doc 2 (feature matrix phase), Doc 3–7 (design),
  and finally into module code and tests. A requirement is "met" only when its acceptance
  tests pass in the delivering module.
- **Module Definition of Done:** all Must requirements for the module implemented; unit +
  integration tests green; security & performance checks for the module passed; documented;
  owner-approved.

---

## 9. Self-review record (Architect / Security / QA / DBA / DevOps lenses)
Applied before presenting; issues found were folded into the text above:
- **Completeness vs. brief:** every feature in the original brief is represented by at least
  one FR (traceable). ✔
- **Completeness vs. research:** competitor strengths (interactive richness, saved replies,
  internal notes, drip, reporting) added as FRs; paywalled-elsewhere features marked **Must**. ✔
- **Compliance gap check:** added explicit opt-in/opt-out, 24-hour window, messaging-limit,
  and quality-rating requirements (CMP-02…07, FR-WA-12, FR-CAM-02). ✔
- **Reliability gap check:** idempotency, smart retry, resume-interrupted, and async webhook
  processing are **Must** (FR-WA-05/07, FR-CAM-08/09, NFR-REL). ✔
- **Security lens:** Argon2id, token rotation+revocation, encryption at rest, ASVS L2 target. ✔
- **Scale lens:** explicit 1M contacts / 10M messages targets and partitioning requirement. ✔
- **Future-proofing:** flow builder, commerce, event-triggered campaigns, and channel
  abstraction included as architecture-level requirements so no rewrite is needed later. ✔

### 9.1 Enhancement pass — v1.0 freeze (owner-requested)
Targeted additions made **without rewriting** the document; items already covered were left unchanged:
- **Performance KPIs** → NFR-PERF-06…12 (dashboard load, campaign create, import/export throughput, search latency, concurrent users, max campaign size).
- **Disaster Recovery & BC** → §5.11 NFR-DR-01…08 (backup frequency, RPO/RTO, restore verification, DB-corruption runbook, Redis & Celery recovery, graceful degradation).
- **AI** → FR-AI-05…10 (campaign generator, template generator, auto-tagging, sentiment, translation, explicit *human-approval-before-send*). Reply suggestions / summarization / RAG were already present (FR-AI-01/03/02).
- **Media** → §3.11 FR-MED-01…09 (image/video/document/audio handling, SHA-256 dedupe, pluggable storage, media-ID caching, retention, signed access).
- **Data Lifecycle** → §3.12 FR-DL-01…08 (archive/restore/soft+hard delete, retention, auto-cleanup, time partitioning, privacy erasure).
- **Monitoring** → §3.13 FR-MON-01…10 (queue/Celery/Redis/MySQL health, API + webhook latency, failed-webhook + campaign-progress monitoring, health endpoints).
- **UI/UX** → FR-UX-07/08 (loading skeletons, infinite/virtualized lists). Dark mode, global search, keyboard shortcuts, accessibility, responsive, design system were already present (FR-UX-01…06).
- **Security** → §5.4 NFR-SEC-01…08 (CSRF, XSS, CSP/headers, rate limiting, IP allow/block, session management, secure audit logging, secrets).
- **Future readiness** → §5.12 NFR-EXT-01…06 (WhatsApp Flows, additional Meta channels, adapter-based API evolution, AI provider abstraction, event-driven automation, modular low-coupling design).

**Baseline frozen as Version 1.0 — the authoritative specification for the remainder of the project.**

---

*End of Document 1 — SRS (Version 1.0, FROZEN). Proceeding to Document 2 — Expanded Feature Matrix.*
