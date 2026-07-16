# Changelog

All notable changes to **frozen** design documents and (later) released modules are recorded
here. Frozen documents are not edited silently; any change to a frozen document must be
logged as an entry below, with date, document, rationale, and the nature of the change.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project
will adopt semantic-ish versioning per document (e.g., `SRS v1.1`) once changes occur.

---

## [Unreleased]

### Design documents — status
- **Doc 12 — Enterprise Governance** — `v1.1` (`12-ENTERPRISE-GOVERNANCE.md`; §1–§55 = v1.0 baseline, §56–§66 added in the governance-handbook enhancement pass; 66 sections, 22 diagrams). Master governance / single entry point referencing Docs 1–11 without duplication.
- **Doc 11 — Operations Runbook** — delivered, awaiting owner approval (`11-OPERATIONS-RUNBOOK.md`; 85 sections, 15 diagrams, OD1–OD40). Operational-only; references Docs 1–10 without redefining them.
- **Doc 9 — AI & Automation Architecture** — delivered, awaiting owner approval (`09-AI-AUTOMATION-ARCHITECTURE.md`; 52 sections, AD1–AD43). Additive; no frozen doc edited.
- **Doc 10 — Testing & QA Architecture** — `v1.1` **FROZEN** on 2026-07-15 (`10-TESTING-QA-ARCHITECTURE.md`; §1–§60 = v1.0 baseline, §61–§72 added in pass; 72 sections, 18 diagrams, TD1–TD65). Additive; references Docs 1–9 without duplication.
- **Doc 1 — SRS** — `v1.0` **FROZEN** on 2026-07-15 (authoritative specification).
- **Doc 2 — Expanded Feature Matrix** — `v1.0` **FROZEN** on 2026-07-15.
- **Doc 3 — Database Design** — `v1.1` **FROZEN** (v1.0 baseline; **§21 Business Event Ledger & Enterprise Event Taxonomy** added in the final additive pass).
- **Doc 4 — API Design Specification** — `v1.0` **FROZEN** on 2026-07-15 (incl. enhancement pass: §29–§36 + subsections §23.1/§24.1/§27.1/§27.2).
- **Doc 5 — UI/UX Design Specification** — `v1.1` **FROZEN** (v1.0 = Parts A–F incl. F1–F15; **Part G Executive Business Dashboard** added in the final additive pass).
- **Doc 6 — Queue & Scheduler Design** — `v1.2` **FROZEN** (pass 1 §21–§34 at v1.0; pass 2 §35–§46 → v1.1; final additive pass **§47 Enterprise Domain Event Bus** + **§48 Business KPI Metric Catalog** → v1.2).
- **Doc 7 — Integrations & Channel Architecture** — delivered, awaiting owner approval. Realizes the dual-channel / Support Connector spec that frozen Doc 6 forward-references as "Doc 6.5" (content in `07-INTEGRATIONS-CHANNEL-ARCHITECTURE.md`; Doc 6 unedited). Defines new **additive** entities (connector registry/session/health, lead pipelines/stages, conversation tags, assignment rules) and additive columns (`connector_id`, lead references) to be applied via migration when built — no frozen doc edited.
- **Doc 8 — Deployment & DevOps Architecture** — `v1.2` **FROZEN** (`08-DEPLOYMENT-DEVOPS.md`; §1–§41 = v1.0 baseline, §42–§55 added in the enhancement pass; **§56 Platform Portability Appendix** added in the final additive pass; DD1–DD41).

### 2026-07-15 — Major requirement: dual-channel (Support Connector) architecture
**Reason:** Owner requires two channels — Channel 1 (Official Meta WhatsApp Cloud API) and Channel 2 (vendor-neutral **Support Connector** abstraction) — unified in one CRM, with the whole platform depending only on a Channel Abstraction Layer, never a specific connector implementation.
**Decision (owner Option 3):** Keep Docs 1–6 **frozen**; centralize all dual-channel design in a **dedicated Doc 6.5**. Docs 7+ reference Doc 6.5 rather than modifying frozen docs.
**Compliance advisory (logged):** The current QR-based connector is treated strictly as a swappable implementation detail; the architecture is designed around the abstraction only, not any specific unofficial implementation. Concrete adapters must comply with their channel's terms of service; official adapters are recommended where available. This advisory is retained so Doc 1 CMP-01 ("official API only") is read together with the dual-channel decision.
**Impact:** No edits to frozen Docs 1–6; new concepts (connector registry/session/health, lead management, connector dashboard, connector endpoints) live in Doc 6.5 and are referenced by later docs.
- **Doc 7 — Deployment Architecture** — not yet started.
- **Doc 8 — Development Roadmap** — not yet started.

### 2026-07-15 — Document order adjusted
**Reason:** Owner chose to design the UI/UX before the Queue & Scheduler internals.
**Changed:** Doc 5 = UI/UX Design; Doc 6 = Queue & Scheduler Design (was Doc 5); Docs 7–8 unchanged.
**Impact:** No change to frozen Docs 1–4.

### Notes
- No changes to frozen documents yet. When a major business requirement changes a frozen
  document, add a dated entry here (e.g., `### 2026-08-01 — SRS v1.0 → v1.1`) describing
  what changed and why, then bump that document's version header.

---

## Module releases

### 2026-07-16 — **Module 6 — Queue Engine Foundation** FROZEN (`v0.3.0-queue-foundation`)
**Scope delivered (branch `feature/module6-queue-engine`, migration 0009):** Celery application
(Redis broker/backend; `task_acks_late` + `task_reject_on_worker_lost` + `prefetch_multiplier=1`
= at-least-once with no hoarding, Doc 6 §3.4/D7); **queue registry** encoding the Doc 6 §2.3
master specification as data (18 queues with purpose/priority/pool/retry/timeouts/failure
destination) — routing, worker pools and the Queue Monitor all read this one source; **smart
retry framework** (Doc 6 §6: failure classes, per-class attempt caps, exponential backoff with
full jitter, pluggable per-channel error maps); **worker framework** (`TrackedTask`: durable
`job_metadata` state, structured logging, smart retry, terminal DLQ park); **DLQ foundation**
(Doc 6 §7: durable parked-task store, fingerprint grouping, replay through the same idempotent
processor, discard — all audited); **Redis worker registry + TTL heartbeat** (§3.4); **queue
health** from live broker depth + fleet (§13.2). APIs: `GET /jobs`, `GET /jobs/{id}`,
`POST /jobs/{id}/cancel`, `GET /queues` (`system:read`/`system:manage`).

**State at freeze:** 180 backend tests passing, ruff clean, migrations 0001–0009 reversible,
zero drift, OpenAPI 49 paths. Celery added to the environment (was declared, not installed).

**Deliberately not built (they bind to this fabric in their own modules):** domain tasks for
sends, webhooks, imports, exports, media, AI and the Support Connector; Celery Beat schedules;
rate gate / circuit breaker (Doc 6 §5/§6.4 — belong with the send pipeline);
`monitoring_metrics` time-series (Doc 3 §11.7 — Monitoring module).

### 2026-07-16 — **Module 2 — CRM Foundation** FROZEN (`v0.2.0-crm-foundation`)
**Scope delivered (branch `feature/module2-contacts-crm`, migrations 0005–0008):**
- **Step 1** (`v0.2.0-module2-step1`) — `contacts` (Doc 3 §6.1): CRUD, dedup by `(org, wa_id)`, E.164
  validation, opt-in transitions, optimistic concurrency, soft delete, keyset pagination, search,
  filters, whitelisted sorting.
- **Step 2** (`v0.2.0-module2-step2`) — `tags` + `contact_tags` (Doc 3 §6.2, FR-CON-09),
  `contact_events` timeline (Doc 3 §6.5, FR-CON-14), `lead_pipelines` + `lead_stages`
  configuration with the default pipeline (Doc 7 §19.2, §23.2).
- **Step 3** (`v0.2.0-module2-step3`) — `segments` + `segment_rules` (Doc 3 §6.4, FR-CON-10):
  saved dynamic filters, rule tree, preview, cached counts.
- **Step 4** (`v0.2.0-module2-step4`) — `custom_attribute_definitions` + `contact_attribute_values`
  (Doc 3 §6.3, FR-CON-11) and `POST /contacts/search` (FR-CON-12).

**State at freeze:** 153 backend tests passing, ruff clean, migrations 0001–0008 reversible, zero
model↔migration drift. RBAC uses only seeded catalog permissions (`contacts:*`, `segments:*`).

**Deferred by dependency (owner-approved; NOT missing — scheduled to their prerequisite module):**
| Deferred | Reason | Lands with |
|---|---|---|
| Contact Import / Export | Doc 4 §14.1 mandates async `202 + job`; FR-CON-05 requires async progress + error report | Queue Engine + Storage |
| Bulk update / delete, Duplicate merge | Doc 4 §14.1 `202 + job` (bulk class) | Queue Engine |
| Internal Notes, Contact Assignment, `conversation_lead`/`lead_stage_transitions` | Frozen docs scope these to `conversations` (Doc 3 §9.5 `internal_notes.conversation_id NOT NULL`; SRS FR-INB-03/05) | Inbox / Messaging |
| Auto opt-out on "STOP" (FR-CON-13) | Requires inbound message handling | Messaging |

### 2026-07-16 — **Module 1 — Foundation** FROZEN (`v0.1.0-foundation`)
Auth, RBAC, users, organization, settings/feature-flags, API keys, audit read API, preferences.
110 tests, 91% coverage, migrations 0001–0004 reversible, OpenAPI 3.1.0 valid. Deferred to their
designated modules: password reset (email), MFA (Doc 12 §56 "Future"), user activity feed
(`activity_logs`), inbound API-key authentication (future public API).

---

## Change log entries

### 2026-07-16 — FINAL architecture additive pass (A–E) — architecture PERMANENTLY FROZEN
**Reason:** Owner-approved final enterprise additions (A–E). Purely additive; existing content, numbering,
and section IDs preserved. After this pass **the architecture is permanently frozen** and implementation
(Module 1) resumes.
**Changed (append-only, before each doc's end marker; headers version-bumped):**
- **A — Business Event Ledger → Doc 3 (v1.0 → v1.1).** Appended **§21 Business Event Ledger & Enterprise
  Event Taxonomy**: `business_event_types` catalog + immutable, time-partitioned `business_events` ledger (DDL),
  a 25-event canonical taxonomy (`lead.created` … `customer.reactivated`, `ai.approved/rejected`, `data.exported`,
  …), append-only/versioned/replay-ready properties, and its relationship to `audit_logs` / `contact_events`.
- **B — Domain Event Bus → Doc 6 (→ v1.2).** Appended **§47 Enterprise Domain Event Bus & Extension Points**:
  durable-first bus over the ledger, event envelope, topics, publish/subscribe, per-subject ordering, idempotency,
  retry/DLQ, replay, fan-out (mermaid), decisions D35–D37.
- **C — Business KPI Metric Catalog → Doc 6 (→ v1.2).** Appended **§48 Business KPI Metric Catalog**: 15 KPIs
  (Reactivation Rate, Revenue Recovery, Cost per Reactivation, Campaign ROI, Lead Funnel/Velocity, AI Acceptance,
  Agent Productivity, Forecast Metrics, …) with Purpose / Formula / Source events / Refresh / Owner / Future
  columns; decision D38. Single source of truth for all business KPIs.
- **D — Executive Business Dashboard → Doc 5 (v1.0 → v1.1).** Appended **Part G — Executive Business Dashboard**:
  executive KPI cards, business trend charts, conversion funnel, revenue recovery, campaign ROI, lead-pipeline
  overview, agent performance, forecast widgets, business-health score; filters (date/campaign/agent/region/
  channel = Meta / Support Connector); export (PDF/Excel/scheduled reports); reads **only** the KPI Catalog
  (Doc 6 §48) from pre-aggregated rollups — **no operational-widget duplication** (those remain in B2).
- **E — Platform Portability Appendix → Doc 8 (v1.1 → v1.2).** Appended **§56 Platform Portability Appendix**:
  Full Data Export Guarantee, Data Ownership, Vendor Independence, Exit Strategy, open Export Formats,
  Validation/Audit/Integrity Verification, Backup Compatibility, Future Migration Readiness — an architecture
  guarantee built on existing backups (§9), storage (§10) and export APIs (Doc 4 §20).
**New governance items (additive to the Doc 4 §4.3 permission catalog; seeded when the corresponding module is
built, not now):**
- Permission **`analytics:executive`** — gates the Executive Business Dashboard (roles: Executive, Owner, Admin).
  Finance-sensitive figures (ROI/revenue/cost) additionally gated by existing **`finance:read`** (Doc 6 §37).
**Explicitly NOT created (per the owner's final ruling):** Plugin SDK / marketplace / general plugin framework,
legacy migration/ETL engine, data warehouse, MDM, or any additional standalone governance document.
**Impact:** Additive only — no existing section edited, renumbered, or deleted. Docs 3, 5, 6, 8 version headers
and end markers updated. **Architecture is now permanently frozen; Module 1 implementation resumes.**


### 2026-07-15 — Doc 12 (Enterprise Governance) v1.0 → v1.1
**Reason:** Owner-requested governance-handbook enhancement pass.
**Changed:** Appended **§56–§66** with no edits to §1–§55: §56 Enterprise Module Manifest, §57 Feature-to-Module Mapping, §58 Enterprise Permission Matrix, §59 Configuration Inventory, §60 Naming Standards, §61 Technology Dependency Inventory, §62 Software Lifecycle, §63 Documentation Ownership Matrix, §64 Readiness Scorecard, §65 Product Version Roadmap, §66 Enhancement Review. Added 2 diagrams (lifecycle, version roadmap).
**Impact:** Additive only; no frozen document edited. Makes Doc 12 the definitive governance handbook.


### 2026-07-15 — Doc 10 (Testing & QA) v1.0 → v1.1
**Reason:** Owner-requested first post-freeze additive enhancement pass.
**Changed:** Appended **§61–§72** with no edits to §1–§60: §61 Test Case Management, §62 Defect & Bug Management, §63 Release Certification Framework, §64 UAT, §65 Exploratory Testing, §66 Production Verification, §67 Certification Matrix, §68 Test Data Governance, §69 Cross-Document Traceability, §70 Testing Maturity Model, §71 Decision Appendix (TD52–TD65), §72 Final 15-perspective Review. Added 5 diagrams and 14 decision records; extended glossary + cross-references.
**Impact:** Additive only; no frozen document edited.


### 2026-07-15 — Doc 9 (AI & Automation Architecture) started
**Reason:** Owner requested the AI architecture document (`09-AI-AUTOMATION-ARCHITECTURE.md`, v1.0).
**Changed:** New document; architecture-only; plugs into frozen Docs 1–8 without modifying them. Any new data fields (AI interaction record: confidence/reasoning/sources/cost/latency/model_version) are **additive** extensions to Doc 3's AI tables, applied via migration when built.
**Impact:** No frozen document edited.


### 2026-07-15 — Doc 6 (Queue & Scheduler) v1.0 → v1.1
**Reason:** Owner-requested second additive enhancement pass (post-freeze), per the changelog-versioning policy.
**Changed:** Appended **§35–§46** with no edits to §1–§34: §35 Queue Analytics Engine, §36 Predictive Capacity Planning, §37 Cost Analytics Engine, §38 Queue Simulation Engine, §39 Queue Versioning Strategy, §40 Maintenance Mode, §41 Disaster Replay Architecture, §42 Enterprise SLA Matrix, §43 Queue Governance, §44 Queue Audit Architecture, §45 Architectural Decision Appendix (RabbitMQ/Kafka/Redis Streams/SQS/Pub-Sub/Service Bus/Temporal/BullMQ/NATS), §46 self-review. Added decisions D24–D34.
**Impact:** Additive only. Two new permissions flagged for the Doc 4 catalog (`finance:read` for cost data, `ops:emergency` + `ops:dlq_delete` for break-glass ops) — to be seeded when Module 1 RBAC is built; no edits to frozen Docs 1–5.

### 2026-07-15 — Doc 8 (Deployment & DevOps) v1.0 → v1.1
**Reason:** Owner-requested additive enhancement pass.
**Changed:** Appended **§42–§55** with no edits to §1–§41: §42 Environment Strategy (full lifecycle), §43 CI/CD Architecture, §44 Infrastructure Inventory, §45 Configuration Management, §46 Release Management, §47 Business Continuity Planning, §48 Compliance Architecture (GDPR/DPDP), §49 Dependency Governance, §50 Cost Optimization, §51 Production Readiness Checklist, §52 Operational KPIs, §53 Orchestrator Decision Appendix, §54 Cross-Document Traceability, §55 Final Self-Review. Added decisions DD33–DD41.
**Impact:** Additive only; no frozen doc edited.

### (older entries below)

<!-- Add newest entries at the top, using this template:

### YYYY-MM-DD — <Document> <old-version> → <new-version>
**Reason:** <business/requirement driver>
**Changed:**
- <bullet describing the change>
**Impact:** <downstream documents/modules affected>

-->
