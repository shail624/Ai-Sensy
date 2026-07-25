# CRM Feature Gap Analysis
### Self-Hosted WhatsApp Business Platform — Enterprise CRM Lens

| | |
|---|---|
| **Document** | 13 — CRM Feature Gap Analysis (addendum to Docs 01–12) |
| **Version** | 1.0 — **DRAFT FOR OWNER APPROVAL** (freezes on approval, per Doc 12 governance) |
| **Date** | 2026-07-22 |
| **Status** | 🟡 Proposed — becomes part of the frozen architecture once approved |
| **Preceded by** | Doc 02 — Expanded Feature Matrix (v1.0, frozen); `FR-CAM-11-GAP-ANALYSIS.md` |
| **Verified against** | Docs 01–12 (frozen) · `frontend/openapi.json` (103 paths) · `backend/app/models/*` · migration head `0023` |
| **Governance** | Additive only. Proposes **no** backend, OpenAPI, or architecture changes. Each accepted item becomes a normal, independently-committable milestone. |

> **Purpose.** Docs 02/research compared this platform against WhatsApp **BSP** tools
> (AiSensy, WATI, Interakt, Gallabox, Zoko, Respond.io, Twilio). This document adds the
> **full-CRM lens** — HubSpot, Zoho CRM, Freshsales, Kommo — to surface *only* the
> enterprise CRM capabilities that are **genuinely valuable for a WhatsApp-first business**
> **and genuinely absent** from our frozen architecture. The goal is **not** parity and
> **not** cloning; it is a disciplined, traceable roadmap of what to add, what to defer,
> and — just as important — **what to deliberately refuse**.

---

## 2026-07-25 implementation-state addendum

This document remains the historical gap analysis produced against the 103-path, migration-0023
repository. The current source of truth is OpenAPI 3.1.0 with 133 paths and migration head `0027`.
The following corrections prevent architecture intent from being mistaken for executable behavior:

- **GAP-01 is delivered.** First-class tasks, activities, due/overdue work queues, assignment,
  outcomes, and timeline integration exist in the current contracts and UI.
- **GAP-04 is partially delivered.** Synchronized custom inbox views and pins exist. Saved lead-board
  views do not, because the current API exposes pipeline/stage configuration but not lead-card listing.
- **GAP-09 is delivered.** The inbox supports bulk status, assignment, and label actions through the
  existing conversation contracts.
- Pipeline and stage administration are executable, but a customer/lead Kanban cannot truthfully
  load cards, mutate stage placement, or persist board views without additive lead-placement APIs.
- Workflow automation and AI are architecture designs, not runtimes. No automation definition/run
  contract or AI provider/interaction/approval contract exists; Phase 3 therefore exposes only
  disabled, human-controlled composition seams.
- Contact-linked document records, KYC decisions, SIM orders/activation, scan batches/results, and
  payments remain genuine contract gaps. Existing media, CRM attributes, tasks, campaigns, segments,
  and analytics are reused rather than duplicated or reinterpreted as those records.

The verified Phase 3 realization and exact remaining contract backlog are recorded in
`docs/design/18-PHASE-3-REACTIVATION-AUTOMATION-PLATFORM.md`. The original competitive analysis and
priorities below are retained unchanged as a point-in-time decision record.

---

## Executive summary

Measured against four full CRMs, our WhatsApp platform is **already at or beyond CRM standard on
almost every axis** — inbox, pipeline+Kanban, notes/@mentions, segmentation, campaigns,
automation, AI, cost analytics, audit and RBAC are all present in the frozen architecture. The
CRM lens exposes **one structural weakness and a short tail of refinements**, not a long backlog.

**The one thing that matters (P0):** we track follow-up as a *single date on a conversation*,
whereas a reactivation/CPOS team needs a **first-class Task & Activity system with a per-agent
work queue** — many timed, typed, assignable actions per lead, and a cross-lead "today" view.
This is the spine of every CRM we compared (Kommo, Freshsales, HubSpot, Zoho) and the highest-ROI
addition available. It is the **only** gap that genuinely blocks a functional v1.

**The verdict in one line:**

| Bucket | Count | Items |
|---|---|---|
| **P0 — required before v1** | **1** | Task & Activity Management + agent work queue |
| **P1 — strongly recommended** | **4** | Lead scoring · CSAT · Saved views · Scheduled report delivery |
| **P2 — nice to have** | **5** | Goals · Record-level visibility · Field-level perms/PII masking · Bulk conversation actions · Custom report builder |
| **Future — conditional** | **6** | SSO/SCIM · Deal-value forecast · Meeting booking · Company/Account object · NPS · 1:1 cadences |
| **Rejected — do not add** | **10** | Email marketing · full omni-CRM · telephony · web-form/CMS · CPQ/invoicing · territory engine · gamification · multi-tenant/portal · 2nd flow builder · AI auto-send |

Everything recommended is **additive** — it reuses existing primitives, changes no frozen
contract, and ships as an independent milestone. The rejected list is as important as the
recommended one: it protects the WhatsApp-first focus and the complexity budget. **Net: add one
capability now, four soon, and refuse ten — rather than chase parity.**

---

## 0. Method & ground rules (how a "gap" was decided)

A feature is reported as a **gap only if it passed all four tests**:

1. **Present in ≥1 reference platform** at a level a WhatsApp-first operator would actually use.
2. **Not already in our frozen architecture** — verified against Docs 01–12, the 103-path
   OpenAPI surface, and the ORM models. Anything marked **"⏭ Later / architecture-ready"**
   in Doc 02 is treated as **present** (it is in the architecture; only its build is phased)
   and is therefore **excluded**.
3. **Aligned with our declared identity** — single-tenant, self-hosted, WhatsApp-first,
   direct Meta Cloud API, no reseller markup, run by an internal Reactivation/CPOS team.
4. **Net-positive** — the value clearly exceeds the maintenance and complexity cost it adds
   (SRS §1.3 out-of-scope items and low-value bloat are rejected, not smuggled in as "Future").

**Legend used throughout**

| Axis | Values |
|---|---|
| **Priority** | **P0** Required before v1 · **P1** Strongly recommended · **P2** Nice to have · **Future** Post-v1 / conditional · **Rejected** Should not be added |
| **Complexity** | **L** Low (days, reuses existing) · **M** Medium (a module milestone) · **H** High (new subsystem / cross-cutting) |
| **Impact** | **L / M / H** business impact for *this* product (reactivation + CPOS ops), not for a generic CRM |
| **Reuse** | Existing frozen primitives the feature builds on (proves it fits the architecture) |

**What "already present" means here.** Before writing a single P0, the following competitor
capabilities were confirmed **already in the frozen architecture** and are therefore **not**
reported as gaps (Appendix A lists the evidence): shared team inbox, assignment/routing,
internal notes **with @mentions**, quick/saved replies, conversation tags & status, unread/read
+ agent-collision presence, **lead pipelines & stages with a drag-and-drop Kanban board**
(`lead_pipelines`/`lead_stages`, Doc 07 §19/§23), **per-conversation reminder / due-date /
follow-up-date / SLA fields** (`conversation_lead`), contact CRM + tags + segments + typed
custom attributes + dedupe + import/export + activity timeline (`contact_events`), campaign
engine (broadcast, drip/sequence, recurring, schedule, pause/resume, retry, cost engine),
templates + media library, granular RBAC + immutable audit + sessions + API keys, the
**AI suite** (reply drafting, RAG KB, summarization, auto-tagging, sentiment, translation —
Doc 09), the **automation/workflow engine** (keyword replies, business hours, auto-assign,
and a rules engine for *follow-ups, reminders, verification chases, SLA nudges* — Doc 09 §41),
analytics (delivery/read/failure, campaign, cost, click-tracking, agent performance, failure-by-error-code),
notification center, backup/restore, retention, monitoring, dark mode, global search, command
palette. **None of these are re-listed below.**

---

## 1. The CRM lens — why these four platforms change the picture

The BSP tools we already benchmarked are *messaging* products with a light CRM bolted on.
HubSpot, Zoho, Freshsales and Kommo are *CRMs* with messaging bolted on. They are strong in
exactly the areas a messaging tool is historically weak — and those areas map directly onto
the owner's stated priorities (productivity, follow-up, reporting, enterprise readiness).

| Platform | CRM core strength (the lens it brings) | What it exposes in our design |
|---|---|---|
| **HubSpot CRM** | Tasks/activities, sequences, meeting links, custom report & dashboard builder, teams, field-level permissions | We have follow-up *fields* but no follow-up *engine of record* (task/activity objects); reporting is fixed, not user-built |
| **Zoho CRM** | Workflow + assignment across records, **scoring rules**, role hierarchy + data-sharing (record-level access), custom modules, SLA/escalation | We have route-level RBAC but not **record-level visibility**; no lead scoring |
| **Freshsales** | Built-in **contact/deal scoring**, activity timeline, sales sequences, territory/team, goals | Scoring + goal-tracking are absent; team hierarchy absent |
| **Kommo (amoCRM)** | Messenger-first **pipeline with tasks that can't be skipped**, "no lead left without a next task", Salesbot | Reinforces the P0: a lead must always carry a *next action*, which a single `reminder_at` cannot guarantee |

The recurring theme across all four is the same missing muscle: **an explicit, first-class
system for "who does what, to which lead, by when — and did it happen."** That is the spine
of the P0 recommendation.

---

## 2. Module-by-module gap audit

Each module states **what the frozen architecture already provides**, the **competitor delta**,
and a **verdict**. Modules where we are already at or beyond CRM standard are recorded as
**"No gap"** — this is deliberate, to prove features were verified rather than assumed.

### 2.1 Onboarding · WABA · Phone numbers — **No gap**
Frozen: multi-WABA, multi-number, quality rating, tier tracking, health, display-name/profile
(Doc 02 §A; `/waba`, `/phone-numbers`). CRMs do not touch this WhatsApp-native surface.
**Verdict: No CRM gap.**

### 2.2 Authentication · Users · RBAC — **Gaps: record-level access, SSO/SCIM, field-level perms**
Frozen: Argon2id login, JWT + rotation + server-side revocation, unlimited users, fully custom
roles, **granular `resource:action` permissions**, password policy/lockout, sessions/device mgmt,
2FA (⏭ Later) (Doc 02 §B; `/roles`, `/permissions`, `/auth/*`).
Competitor delta (Zoho/Freshsales/HubSpot enterprise): **role hierarchy + record-level data
sharing** ("an agent sees only their leads; a manager sees the team's"), **field-level
permissions / PII masking**, and **SSO (SAML/OIDC) + SCIM** provisioning.
Our RBAC gates *routes and actions*, not *which rows a user may see*, and identity is local-only.
**Verdict: Gaps → GAP-07 (record-level visibility, P2), GAP-08 (field-level perms/PII masking, P2), GAP-11 (SSO/SCIM, Future).**

### 2.3 Contacts · Segmentation — **Gap: lead scoring (contact prioritization)**
Frozen: unlimited contacts, CSV/Excel import w/ progress, dedupe (E.164 + merge/skip/overwrite),
bulk edit/delete, unlimited tags, dynamic segments, typed custom attributes, advanced AND/OR
search, opt-in/out + auto-STOP, **activity timeline** (`contact_events`), export (Doc 02 §C).
Competitor delta (Freshsales/Zoho/HubSpot): **rule-based (and predictive) scoring** to rank
contacts/leads by propensity; **lifecycle stage** as a first-class field (we approximate this
with pipeline stage on the conversation, so it is **not** re-flagged).
**Verdict: Gap → GAP-02 (lead scoring, P1).** Company/Account object considered → Rejected-for-now / Future (see §6, §7).

### 2.4 Templates · Media — **No gap**
Frozen: Meta sync + approval status, full component authoring, interactive buttons/lists/CTA,
media headers, preview, hash-deduped media library, pluggable storage (Doc 02 §D). CRMs are
weaker here. **Verdict: No gap.**

### 2.5 Messaging (message types) — **No gap**
Frozen: template, free-form (24h), media, interactive, reactions, location/contact, inbound
media store, **24-hour window enforcement with UI countdown** (Doc 02 §E). **Verdict: No gap.**

### 2.6 Campaign engine (broadcasts) — **No gap for CRM**
Frozen: broadcast to segment/tag/list/upload, eligibility pre-checks, timezone scheduler,
**recurring**, **drip/sequence**, rate-limited queue, pause/resume, cancel, smart retry,
crash-safe resume, per-recipient ledger, **exact cost engine**, save-as-template, pacing
(Doc 02 §F). This already exceeds the CRMs' bulk-WhatsApp features. **Verdict: No gap.**
*(Note: 1:1 sales "sequences/cadences" are handled below under Follow-up, not here — broadcast drip ≠ per-agent cadence.)*

### 2.7 Shared inbox · Conversation management — **Gaps: CSAT, saved views, bulk actions**
Frozen: real-time shared inbox, persisted history, assignment/reassignment, **quick replies
(personal + shared)**, **internal notes with @mentions**, window-aware reply, tags, status
(open/pending/resolved), unread/read, **agent collision/presence**, routing rules
(round-robin/by-tag), auto-assign on inbound, SLA timers (⏭ Later) (Doc 02 §G/§H; `/conversations/*`).
Competitor delta:
- **CSAT / post-conversation feedback** (WATI/Respond/HubSpot Service): a 1-tap satisfaction
  survey after resolution — **absent** (`CSAT`/`survey` appear nowhere in Docs 01–12).
- **Saved / custom list views** for the inbox and lead board (personal + shared): we have
  reusable *segments for contacts*, but no saved filtered views for *conversations/leads*.
- **Bulk conversation actions** (bulk assign/resolve/tag): contacts have bulk ops; conversations do not.
**Verdict: Gaps → GAP-03 (CSAT, P1), GAP-04 (saved views, P1), GAP-09 (bulk conversation actions, P2).**

### 2.8 Follow-up & task management — **PRIMARY GAP**
Frozen: `conversation_lead` carries **`reminder_at`, `due_date`, `follow_up_date`, `sla_at`,
`priority`, `owner_agent`** (Doc 07 §19/§23), and the Doc 09 workflow engine can *create a
reminder* as an automated action. So the **primitive for "one next date on one conversation"
exists.**
Competitor delta (Kommo, Freshsales, HubSpot, Zoho — this is their spine): a **first-class
Task/Activity object** — *many* tasks per lead/contact, each with type (call/message/verify/
meeting), assignee, due time, status and outcome; **logged activities** (call/meeting outcomes)
on the timeline; and a **per-agent work queue** ("My day: Overdue / Due today / Upcoming")
that spans *all* the agent's leads. Kommo's defining rule — *no lead may sit without a next
task* — is impossible to enforce with a single mutable `reminder_at` field.
**Why our fields are not enough:** a reactivation agent runs a lead through *multiple* timed
touches (call Tue → chase docs Thu → verify Mon). One `reminder_at` per conversation cannot
hold a queue, cannot be assigned to a second person, has no type/outcome, and offers no
cross-lead "today" view — so follow-up (this team's core job) is unmanaged at the fleet level.
**Verdict: PRIMARY Gap → GAP-01 (Task & Activity Management + agent work queue, P0).**

### 2.9 Automation & workflow — **No gap**
Frozen: keyword/rule auto-replies, business-hours/away, auto opt-out on STOP, auto-assignment,
and a full **rules engine** (trigger → condition → action) for follow-ups, reminders,
verification chases and SLA nudges, with internal/safe actions auto-running and risky actions
gated (Doc 02 §H; Doc 09 §41). Visual flow builder is ⏭ Later (architecture-ready). This
matches Zoho/HubSpot workflow automation. **Verdict: No gap** (the *tasks* those workflows
create need GAP-01 as their store of record, but the automation itself is covered).

### 2.10 Artificial Intelligence — **No gap**
Frozen: AI reply drafting, RAG knowledge base, summarization, campaign/template generators,
auto-tagging, sentiment, translation, with a hard **human-approval-before-send** rule (Doc 02 §I;
Doc 09). This exceeds the AI in all four CRMs. **Verdict: No gap.**

### 2.11 Analytics — **Gap: goal/target tracking**
Frozen: delivery/read/failure reports, campaign analytics with drill-down, **exact cost
analytics**, first-party click/URL tracking, real-time webhook-driven dashboard, **agent
performance reports**, failure-by-Meta-error-code, exports; funnels/attribution ⏭ Later
(Doc 02 §J). Stage transitions already emit domain events for analytics (Doc 07 §19), so
**pipeline funnel/velocity is architecture-ready** and is *not* re-flagged.
Competitor delta (Freshsales/Zoho/HubSpot): **goals / targets** — set a per-agent or per-team
target (e.g., reactivations/week) and track attainment against it. Absent today.
**Verdict: Gap → GAP-06 (goal & target tracking, P2)** (packaged with reporting, below).

### 2.12 Reporting — **Gaps: scheduled delivery, custom report/dashboard builder**
Frozen: fixed report set + CSV/Excel/JSON export + a real-time dashboard (Doc 02 §J/§N).
Competitor delta (all four): **scheduled report delivery** (email/WhatsApp a digest on a
cadence — no login required) and a **self-service custom report & dashboard builder**
(pick metric, dimension, filter; save; share). We have neither; every new report is currently
an engineering change.
**Verdict: Gaps → GAP-05 (scheduled report delivery, P1), GAP-10 (custom report/dashboard builder + goals, P2).**

### 2.13 Integrations & developer API — **No new gap**
Frozen: webhook mgmt with dead-letter + replay, outbound webhooks, first-class public REST API;
Zapier/CRM/e-commerce connectors ⏭ Later (Doc 02 §K). Because we expose a real API + outbound
webhooks, third-party CRM sync is buildable without new architecture. **Verdict: No gap** (connectors are already Later).

### 2.14 Admin · Ops · Maintainability — **Covered by §2.2 gaps**
Frozen: settings, **immutable/tamper-evident audit**, structured logs, full-stack monitoring,
scheduled backup + verified restore, retention + lifecycle (archive/soft/hard/erasure),
partitioning, feature flags (Doc 02 §N; `/audit-logs`, `/settings`, `/feature-flags`). The only
enterprise-maintainability deltas are identity/access (SSO/SCIM, record-level, field-level) —
already captured as GAP-07/08/11. **Verdict: No additional gap.**

### 2.15 Platform UX — **No gap**
Frozen: dark mode, responsive, **keyboard shortcuts + command palette**, global search,
skeletons/optimistic UI, virtualized lists, design-system tokens, WCAG 2.1 AA; i18n ⏭ Later
(Doc 02 §O). Meets or beats the CRMs. **Verdict: No gap.**

---

## 3. Consolidated gap register

Eleven genuine gaps survived all four tests. Sorted by priority; full write-ups follow in §4–§7.

| ID | Gap | Category | Priority | Complexity | Impact | Primary competitors | Reuses |
|---|---|---|---|---|---|---|---|
| **GAP-01** | **Task & Activity Management + agent work queue** | Follow-up · Productivity | **P0** | M | **H** | Kommo, Freshsales, HubSpot, Zoho | `conversation_lead`, `owner_agent`, notifications, `contact_events` |
| **GAP-02** | Lead / contact **scoring & prioritization** | CRM workflow · Productivity | **P1** | M | **H** | Freshsales, Zoho, HubSpot | custom attributes, segments, stage events |
| **GAP-03** | **CSAT** / post-conversation feedback | Conversation mgmt · Analytics | **P1** | L | M | WATI, Respond, HubSpot | templates, webhooks, `conversation`, analytics |
| **GAP-04** | **Saved / custom list views** (inbox + lead board) | Productivity · Conversation mgmt | **P1** | L–M | M | HubSpot, Zoho, Kommo | segment filter engine, list UI |
| **GAP-05** | **Scheduled report delivery** (digests) | Reporting | **P1** | L | M–H | all four | analytics (Ph8), scheduler (built) |
| **GAP-06** | **Goal & target tracking** | Analytics · Reporting | **P2** | L–M | M | Freshsales, Zoho, HubSpot | agent-performance analytics |
| **GAP-07** | **Record-level visibility** (own/team/all) | Enterprise readiness | **P2** | M–H | M | Zoho, Freshsales | RBAC, `owner_agent`, roles |
| **GAP-08** | **Field-level permissions + PII masking** | Enterprise · Compliance | **P2** | M | M | Zoho, HubSpot | RBAC, schemas |
| **GAP-09** | **Bulk conversation actions** | Productivity | **P2** | L | M | HubSpot, Zoho | contacts bulk pattern, inbox |
| **GAP-10** | **Custom report / dashboard builder** | Reporting | **P2** | H | M | HubSpot, Zoho, Freshsales | analytics store, exports |
| **GAP-11** | **SSO (SAML/OIDC) + SCIM provisioning** | Enterprise readiness | **Future** | M–H | M | HubSpot, Zoho enterprise | auth, users, roles |

Additional items evaluated and **routed to Future or Rejected** (deal-value/forecast,
Company/Account object, meeting booking, NPS, telephony, email/omni-CRM, web-form/CMS,
CPQ/invoicing, territory engine, gamification) are handled in §7 and §8 — none are silently dropped.

---

## 4. Recommended P0 — required before v1

P0 is deliberately **a single capability**. Overloading P0 would violate the "no unnecessary
features" rule; exactly one gap genuinely blocks a *functional* reactivation/CPOS operation.

### GAP-01 — Task & Activity Management + agent work queue  ·  Complexity M · Impact H

**What.** A first-class **Task** object (and light **Activity** log) layered on the existing
lead model: many tasks per contact/lead/conversation, each with `type` (call · message ·
collect-docs · verify · meeting · custom), `assignee`, `due_at`, `status`
(open/done/skipped), `priority`, and an `outcome` note on completion. Completed tasks and
manual activities (e.g., "called — no answer") append to the existing `contact_events`
timeline. A per-agent **work queue** view — *Overdue · Due today · Upcoming* — spans all of
an agent's leads, and a manager rollup shows the team's load.

**Why it matters (this product specifically).** The users are a **follow-up-driven** team;
their job *is* multi-touch pursuit of each lead to activation. The frozen model gives each
conversation exactly one `reminder_at`/`follow_up_date` — enough for "ping me once," not for
running a book of business. Without a task queue there is (a) no way to see an agent's actual
day across leads, (b) no assignment of a follow-up to a *different* person, (c) no type/outcome
history, and (d) no enforcement of Kommo's proven discipline: *no lead sits without a next
action*. This is the difference between a messaging tool and a CRM, and it is the highest-ROI
thing we can add.

**Competitors.** Kommo (task-per-lead is mandatory), Freshsales (activities + sequences),
HubSpot (tasks/queues), Zoho (activities + follow-up rules).

**Reuses (fits the architecture).** `conversation_lead.owner_agent` for default assignee;
`contact_events` (append-only, partitioned) as the activity timeline sink; the notification
center (Doc 5 F7) for due/overdue alerts; the Doc 09 workflow engine as an *automated task
creator* (e.g., "on stage → Documents Pending, create a 'collect-docs' task due +2d"). No new
subsystem — it is a new table + endpoints + two views.

**Scope guard.** Ship **lean**: tasks, the three-bucket agent queue, completion→timeline, and
workflow-created tasks. **Defer** rich activity types, calendar UI, and cadence templates to
P1/Future so P0 stays a single committable milestone.

---

## 5. Recommended P1 — strongly recommended (build right after v1 core)

### GAP-02 — Lead / contact scoring & prioritization  ·  Complexity M · Impact H
**What.** A transparent, rule-based score per contact/lead (recency of engagement, inbound
replies, stage, tenure, custom-attribute signals), surfaced as a sortable column and a queue
ranker. Optional AI-assisted scoring later reuses the Doc 09 AI layer.
**Why.** Agent capacity is finite; a reactivation list is long. Scoring points the team at the
leads most likely to convert *today*, and directly orders the GAP-01 work queue. Freshsales and
Zoho treat this as core; it is the single biggest productivity multiplier after tasks.
**Reuses.** Typed custom attributes, segment predicate engine, stage-transition events.
**Guard.** Start rules-only + explainable ("why this score"); avoid opaque ML for v1.

### GAP-03 — CSAT / post-conversation feedback  ·  Complexity L · Impact M
**What.** After a conversation is resolved, optionally send a 1-tap satisfaction template;
capture the reply as a score on the conversation/contact; roll up into agent-performance analytics.
**Why.** A support/reactivation team with no quality signal is flying blind. CSAT is the
standard voice-of-customer metric (WATI, Respond, HubSpot Service ship it), it feeds the
already-planned agent analytics (Phase 8), and it flags at-risk conversations for the Doc 09
sentiment/at-risk logic. Very cheap given templates + webhooks already exist.
**Reuses.** Template registry, inbound webhook processor, `conversation`, analytics pipeline.

### GAP-04 — Saved / custom list views (inbox + lead board)  ·  Complexity L–M · Impact M
**What.** Let users save named, filtered, sorted, column-configured views of the inbox and the
lead Kanban (personal + shared) — e.g., "My overdue reactivations," "Docs pending > 3 days."
**Why.** The inbox/lead board is the team's primary workspace; they re-filter it dozens of times
a day. Contacts already have reusable *segments*; conversations/leads have no equivalent. This
is a low-cost, high-frequency productivity win and a prerequisite for team-wide consistency.
**Reuses.** The segment filter engine (generalized to conversations/leads), existing list UI + virtualization.

### GAP-05 — Scheduled report delivery (digests)  ·  Complexity L · Impact M–H
**What.** Schedule existing analytics/reports to be delivered on a cadence (daily/weekly) by
email and/or WhatsApp to a manager or channel — no dashboard login required.
**Why.** Reporting only drives behavior if people actually see it. Every one of the four CRMs
offers scheduled reports; for a manager running a reactivation floor, a 7am "yesterday's
numbers" digest is a daily habit-former. It reuses the **already-built** scheduler
(`campaign_schedule_service`, Celery crontab) and the Phase-8 report data — near-trivial to add.
**Reuses.** Reporting (Phase 8), the campaign scheduler, notification/email + WhatsApp send.
**Guard.** Deliver **existing** reports on a schedule; do **not** couple this to GAP-10 (custom builder).

---

## 6. Recommended P2 — nice to have (value clear, not urgent)

### GAP-06 — Goal & target tracking  ·  Complexity L–M · Impact M
Set per-agent/per-team targets (e.g., reactivations/week, docs collected/day) and track
attainment on the dashboard. Turns analytics from descriptive into managed. Reuses agent-performance
analytics; naturally bundles with GAP-10. *Guard: keep it a thin layer over existing metrics.*

### GAP-07 — Record-level visibility (own / team / all)  ·  Complexity M–H · Impact M
Scope which rows a user may see/edit by ownership and a manager→agent hierarchy, so an agent
sees their own leads and a manager sees the team's. Our RBAC gates *actions*, not *rows*; this
is the enterprise data-sharing model Zoho/Freshsales consider baseline. Reuses roles +
`owner_agent`. *Guard: a simple own/team/all scope, not a full geographic territory engine (see §8).*

### GAP-08 — Field-level permissions + PII masking  ·  Complexity M · Impact M
Restrict or mask sensitive fields (phone, KYC/verification documents) per role, complementing
route-level RBAC. Directly relevant for a **telecom** handling identity documents; strengthens
the compliance posture already central to the design. Reuses RBAC + response schemas.

### GAP-09 — Bulk conversation actions  ·  Complexity L · Impact M
Multi-select in the inbox to bulk assign / resolve / tag, mirroring the bulk operations contacts
already have. Small, obvious productivity win for high-volume days. Reuses the contacts bulk pattern.

### GAP-10 — Custom report / dashboard builder  ·  Complexity H · Impact M
Self-service builder (pick metric + dimension + filter, save, share dashboards), so new reports
stop being engineering tickets — a **maintainability** win as much as a reporting one. High effort;
sequence **after** the fixed Phase-8 reports and scheduled delivery prove the data model.
Reuses the analytics store + export layer. Bundle GAP-06 goals as a widget type.

---

## 7. Future roadmap — post-v1 or conditional

These are real, but either lower-impact for a WhatsApp-first reactivation team or dependent on a
future business direction. Kept in the architecture's line of sight, not built for v1.

| Item | Why later / conditional | Complexity | Impact |
|---|---|---|---|
| **GAP-11 — SSO (SAML/OIDC) + SCIM** | Genuine enterprise-IT requirement; Doc 12 already lists SSO as *Future*. Trigger: corporate identity mandate or team scale-up. SCIM auto-provisions/deprovisions agents. | M–H | M |
| **Deal / activation value + weighted forecast** | Only valuable **if** a reactivation carries a tracked monetary/ARPU value. Our pipeline is an *activation funnel* (New → … → Activation Pending → Completed), not a revenue-deal funnel. Add a `value`+`probability` on the lead **only** if finance wants forecasting — otherwise it is ceremony. | M | M (conditional) |
| **Meeting / appointment booking links** | Self-service slot booking (verification callbacks). Useful but secondary to outbound pursuit; revisit after tasks land. | M | L–M |
| **Company / Account (B2B) object** | Grouping contacts under an account matters for **B2B/CPOS-partner** management, not for B2C subscriber reactivation. Build **only if** the CPOS/partner direction becomes first-class. Avoids imposing a B2B schema on a B2C tool now. | H | L (today) |
| **NPS relationship surveys + verbatim analysis** | Relationship-level VoC beyond per-conversation CSAT; sequence after CSAT (GAP-03) proves the survey plumbing. | M | L–M |
| **Cadence/sequence templates for 1:1 follow-up** | Pre-built multi-step task sequences ("reactivation playbook") on top of GAP-01 + the Doc 09 workflow engine. A productivity accelerant once tasks exist. | M | M |

---

## 8. Features intentionally rejected (and why)

Refusing the wrong features protects focus, complexity budget, and maintainability as much as
adding the right ones. Each below is offered by ≥1 competitor and is **deliberately declined**.

| Rejected feature | Offered by | Why we should NOT add it |
|---|---|---|
| **Native email marketing / bulk email** | HubSpot, Zoho, Freshsales | Off-mission. We are **WhatsApp-first**; email as a marketing channel dilutes the product and doubles the sending/compliance surface for little gain to a reactivation team. |
| **Full omnichannel CRM inbox (email/SMS/social as first-class channels)** | HubSpot, Zoho, Respond | Our channel abstraction is *already* omnichannel-ready (Doc 02 §G12, SRS §1.3 Later). Building a general multi-channel CRM **now** trades our sharp WhatsApp focus for surface area. Defer to the planned omnichannel path, don't front-load it. |
| **Built-in telephony / power dialer** | Freshsales (Freshcaller), Zoho | A whole new real-time media subsystem (SIP, recording, carrier billing) far outside a WhatsApp platform's remit. Log calls as GAP-01 activities instead. |
| **Landing-page / web-form builder + CMS** | HubSpot | We are not a marketing website platform. Lead capture is a **webhook** into `/contacts` (already supported); a page builder is scope creep with heavy maintenance. |
| **CPQ / quotes / invoicing / multi-currency** | Zoho, Freshsales | Commerce/payments are explicitly out of scope (SRS §1.3); only WhatsApp-native payment message types are permitted. A quoting engine is a different product. |
| **Full geographic territory management engine** | Zoho, Freshsales | Over-engineered for one internal team. The real need — "see my/my team's leads" — is met by the lighter **GAP-07** record-level scope. |
| **Gamification (leaderboards / badges / points)** | Freshsales, some BSPs | Vanity mechanics; low durable value, ongoing upkeep. Goal tracking (GAP-06) delivers the useful part (targets) without the game layer. |
| **Multi-tenant / customer portal / public self-sign-up** | HubSpot, Zoho | **Explicitly excluded** by SRS §1.3 (single-tenant, self-hosted, no public sign-up). Non-negotiable identity of the product. |
| **Second visual flow/chatbot builder** | AiSensy, WATI, Kommo (Salesbot) | Already **architecture-ready** (Doc 02 §H4). Adding a parallel builder would duplicate a planned surface — a direct violation of the "no duplication" rule. |
| **AI auto-send without human approval** | some "AI agent" tools | Violates the frozen safety invariant (Doc 02 §I10: never auto-send; human approval + audit). Rejected on principle. |

---

## 9. Implementation roadmap (order & dependencies)

Sequenced by **impact ÷ complexity** and by dependency. Every item remains an **independent,
buildable milestone** that touches no backend contract retroactively and adds only additive
migrations/endpoints — consistent with the frozen governance model.

| Order | Gap | Priority | Attaches to / after | Depends on | Migration/API footprint |
|---|---|---|---|---|---|
| **1** | GAP-01 Task & Activity + work queue | **P0** | Inbox/Lead module (Phase 7) | `conversation_lead`, notifications | +tables `tasks`, `activities`; task/queue endpoints |
| **2** | GAP-03 CSAT | P1 | Inbox + Analytics (Ph 7→8) | templates, webhooks | +`csat` fields/table; 1 webhook path reuse |
| **3** | GAP-04 Saved views | P1 | Inbox/Lead board (Phase 7) | segment filter engine | +`saved_views` table; list endpoints |
| **4** | GAP-05 Scheduled report delivery | P1 | Analytics (Phase 8) | scheduler (built), reports | +`report_schedules` table; scheduler hook |
| **5** | GAP-02 Lead scoring | P1 | Contacts + Analytics (Ph 3→8) | attributes, segments, stage events | +score rules table + computed field |
| **6** | GAP-09 Bulk conversation actions | P2 | Inbox (Phase 7) | GAP-04 (selection UX) | endpoints only (no schema) |
| **7** | GAP-06 Goal & target tracking | P2 | Analytics (Phase 8) | agent-performance analytics | +`goals` table |
| **8** | GAP-08 Field-level perms + PII masking | P2 | Admin/RBAC (Phase 10) | RBAC | permission metadata + schema masking |
| **9** | GAP-07 Record-level visibility | P2 | Admin/RBAC (Phase 10) | roles, `owner_agent` | scope column on roles + query filters |
| **10** | GAP-10 Custom report/dashboard builder | P2 | Analytics (post Phase 8) | GAP-05, GAP-06 | +builder tables; query API |
| **11** | Future (SSO/SCIM, deal value, meetings, account obj, NPS, cadences) | Future | Post-v1 | per §7 | as triggered |

**Reading of the order:** #1 alone is the v1 gate. #2–#5 are the high-ROI P1 cluster that
rides the Phase 7–8 work already on the board. #6–#10 harden reporting and enterprise access.
Future items wait for an explicit business trigger (§7).

---

## 10. Self-review record (applied before submission)

- **Every gap verified absent**, not assumed — checked against Docs 01–12, 103 OpenAPI paths,
  and ORM models. Terms `CSAT`, `NPS`, `survey`, `territory`, `SAML`, `OIDC`, `SCIM`, `lead
  scoring`, `report builder`, `opportunity` return **zero** design-doc hits. ✔
- **No already-present feature reported.** Kanban board, @mentions, quick replies, reminder/
  due-date/SLA fields, drip sequences, funnels, flow builder, 2FA, i18n, connectors — all
  confirmed **present or Later** and **excluded** (Appendix A). ✔
- **Scope respected.** SRS §1.3 exclusions (multi-tenant, public sign-up, non-WhatsApp payments,
  unofficial APIs) are in **Rejected**, never smuggled into Future. ✔
- **Additive only.** Nothing here renames an API, edits a frozen doc, or alters backend
  contracts; every item is an independent additive milestone. ✔
- **Restraint shown.** P0 is a single capability; ten competitor features are explicitly
  **rejected** with reasons. ✔
- **Grounded in this product**, not a generic CRM: impact rated for a reactivation/CPOS team. ✔

---

## Appendix A — Competitor features confirmed ALREADY in our architecture (excluded from gaps)

Evidence that these were verified, not overlooked (so they are correctly **not** gaps):

| Competitor feature | Where it already lives |
|---|---|
| Shared inbox, assignment, routing, presence/collision | Doc 02 §G1–G10; `/conversations/*` |
| Internal notes **with @mentions** | Doc 05 §F12 / L1490; Doc 07 §816–823 |
| Quick/saved replies (personal + shared) | Doc 02 §G4; `/quick-replies` |
| Conversation tags & status | Doc 02 §G7; `/conversations/{id}/tags`,`/status` |
| **Pipeline + stages + Kanban board** | `lead_pipelines`,`lead_stages`; Doc 07 §19/§23; Kanban §742 |
| Per-lead **reminder / due-date / follow-up / SLA** fields | `conversation_lead` (Doc 07 §23) |
| Contact CRM, tags, segments, typed attributes, dedupe, timeline | Doc 02 §C; `/contacts/*`, `contact_events` |
| Broadcast + **drip/sequence** + recurring + schedule + cost | Doc 02 §F; `/campaigns/*` |
| Workflow automation (follow-ups, reminders, SLA nudges) | Doc 09 §41 |
| AI drafting, RAG KB, summarize, auto-tag, sentiment, translate | Doc 02 §I; Doc 09 |
| Agent-performance + delivery/cost/click analytics | Doc 02 §J; `/audit`, analytics (Ph 8) |
| Immutable audit, sessions, API keys, granular RBAC | Doc 02 §B/§N; `/audit-logs`,`/roles`,`/api-keys` |
| Notification center, dark mode, global search, command palette | Doc 02 §M/§O |
| Funnels, A/B, flow builder, omnichannel, connectors, i18n, 2FA | Doc 02 (all marked **⏭ Later** — in architecture) |

## Appendix B — Out of scope by SRS §1.3 (rejected, not deferred)

Unofficial WhatsApp APIs / scraping · Meta-policy-violating features · reselling / multi-company
SaaS tenancy / public sign-up · payment processing beyond WhatsApp-native message types.

---

*End of Document 13 — CRM Feature Gap Analysis. Additive addendum to the frozen architecture;
awaiting owner approval to freeze. No backend, OpenAPI, or Doc 01–12 change is proposed or implied.*



