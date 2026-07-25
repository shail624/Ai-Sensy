# Changelog

All notable changes to **frozen** design documents and (later) released modules are recorded
here. Frozen documents are not edited silently; any change to a frozen document must be
logged as an entry below, with date, document, rationale, and the nature of the change.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project
will adopt semantic-ish versioning per document (e.g., `SRS v1.1`) once changes occur.

---

## [Unreleased]

### 2026-07-25 — Phase 1 enterprise product transformation

**Added**
- Added a business-first premium shell with responsive navigation, command palette, cross-module
  search, favorites, recents, quick-create actions, keyboard shortcuts, and live attention signals.
- Added customer-360 context, inbox saved views/pins/bulk actions and unread-wait SLA signals, an
  approval-ready campaign journey, Operations control center, permission catalog, and honest
  Automation/Reactivation foundations.
- Added Phase 1 architecture-boundary regression coverage and the verified transformation record in
  `docs/design/16-PHASE-1-ENTERPRISE-PRODUCT-TRANSFORMATION.md`.

**Changed**
- Reorganized navigation around business workflows and upgraded dashboard, sign-in, contacts,
  customer profile, inbox, campaigns, Operations, Administration, Tasks, and Analytics presentation.
- Backend APIs, OpenAPI, database schema, permissions, tenant isolation, queue behavior, Celery task
  registration, provider behavior, and business rules are unchanged.

### 2026-07-25 — Module 11 defensive observability contracts

**Added**
- Added canonical structured `http_request` events with request-id, method, path, status, and
  duration fields. Safe bounded client correlation ids are preserved across nginx and the API;
  unsafe values are replaced.
- Added formatter-boundary redaction for sensitive fields and recognizable credentials, email
  addresses, and international phone numbers in both JSON and text logs. ADR-0007 records the
  repository-versus-environment observability boundary.
- Extended the isolated deployed gate to prove edge and API runtime logs share correlation ids,
  contain none of its synthetic secret/PII values, and report Redis down with a 503 from `/ready`
  after that dependency is stopped.

**Changed**
- Disabled the duplicate uncorrelated Uvicorn access record; application middleware is now the
  canonical API access logger. The release contract also syntax-checks the actual mounted edge
  configuration with the digest-pinned production nginx image.
- API routes, response contracts, permissions, tenant scope, business behavior, and schema are
  unchanged.

### 2026-07-25 — Module 11 deployed-stack E2E and performance canary

**Added**
- Added the cumulative `deployed` quality profile. It starts the unchanged ten-service production
  topology under a unique Compose project with synthetic secrets and disposable volumes, bootstraps
  an Owner through the existing CLI, captures evidence, and guarantees project-scoped cleanup.
- Added a digest-pinned Playwright 1.61.1 Chromium runner and one focused real-UI journey: login →
  Contacts → CSV upload/mapping → queued import → persisted contact search/profile. This exercises
  nginx, the SPA, API, MySQL, Redis broker, and jobs worker without a provider or customer send.
- Added a 30-sample authenticated standard-read canary using nearest-rank p95 and the frozen <300 ms
  target; the first isolated run passed at 7.9 ms. ADR-0006 records the boundary from full load tests.

**Changed**
- Pinned the production MySQL 8.0 image by immutable manifest digest. The release contract now
  rejects unpinned third-party service images as well as unpinned application Dockerfile stages.
- Corrected the deployment smoke runbook to use the existing Contacts import UI instead of referring
  to a nonexistent direct-create control; APIs, permissions, routing, and product behavior are unchanged.

### 2026-07-25 — Module 11 security and release-gate automation

**Added**
- Added cumulative, provider-neutral `static`, `pre-merge`, and `release` quality profiles covering
  Ruff, strict mypy, OpenAPI drift, frontend lint/types, both full test suites, production build,
  Bandit SAST, dependency audits, tracked-source vulnerability/secret/IaC scanning, Compose/image
  contracts, production image scans, smoke checks, and CycloneDX SBOM evidence.
- Added deterministic tests for fail-fast orchestration, tracked-only scanner snapshots, Compose
  invariants, synthetic secret handling, and non-root/health image metadata. ADR-0005 records the
  gate boundaries and scanner pin.

**Security**
- The first blocking audit found `asyncmy` 0.2.11 affected by critical unpatched SQL injection
  (`GHSA-qhqw-rrw9-25rm`). Replaced only the SQLAlchemy driver boundary with pinned `aiomysql`
  0.3.2 / PyMySQL 1.2.0; application layering, SQLAlchemy repositories, schema, routes, permissions,
  queue behavior, and the 133-path contract are unchanged.
- Production application image tags now fail closed when `IMAGE_TAG` is absent, and the deployment
  template demonstrates the immutable release tag `1.0.0-rc1` instead of `latest`.
- Backend and frontend build/runtime bases, plus the production Redis and edge-nginx images, are
  pinned by immutable manifest digest. The application runtimes use current Alpine layers; both
  rebuilt application images pass the blocking HIGH/CRITICAL scan and emit CycloneDX SBOMs.
- The tracked source snapshot is clean at HIGH/CRITICAL across vulnerability, secret, and IaC
  scanning; backend SAST and production dependency audit are clean. Moderate React Router
  advisories remain visible and require an explicit later v7 migration.

### 2026-07-25 — Module 11 strict typing completion

**Added**
- Added precise SQLAlchemy result/expression types, analytics fact-model unions, callback/iterator
  contracts, JSON container types, and focused invariant tests across repository and service seams.
- Missing linked templates, WABAs, or campaign sending numbers now take explicit existing domain
  outcomes instead of surfacing as attribute errors; malformed internal priority cursors are rejected.

**Changed**
- Eliminated the remaining 120 strict-mypy findings across 45 files. Raw `mypy app` now passes for
  all 227 backend source files under the unchanged strict configuration and pinned mypy 2.3.0.
- Retired the temporary baseline, wrapper, and wrapper tests exactly as ADR-0004 required once the
  direct strict gate became clean. ADR-0004 is retained as a superseded transition record.
- Runtime APIs, routes, permissions, tenant scoping, SQL queries, queue behavior, database schema,
  migrations, and the 133-path OpenAPI contract remain unchanged.

### 2026-07-25 — Module 11 strict-mypy ratchet

**Added**
- Added a deterministic strict-mypy ratchet (`backend/scripts/check_mypy.py`) with a versioned
  baseline and focused tests. New or increased path/error-code allowances fail; reductions mark the
  baseline stale until it is explicitly lowered, and same-version writes cannot raise allowances.
- Added ADR-0004 to record the transitional baseline policy, exact checker-version requirement,
  and removal condition once raw strict mypy is clean.

**Changed**
- Pinned the development checker to mypy 2.3.0 while leaving the repository's strict mypy settings
  unchanged. The backend README now documents both the enforced ratchet and the raw-debt audit.
- Reduced strict findings from 251 across 67 files to 120 across 45 files by typing the existing
  Celery/async task boundary and SQLAlchemy model metadata/JSON containers. Runtime behavior,
  queues, retries, database schema, API routes, permissions, and contracts are unchanged.
- Remaining repository/service findings are retained as explicit Module 11 debt behind the ratchet,
  not suppressed or globally disabled. Count granularity avoids line churn; review remains the
  backstop for a same-code replacement within one file.

### 2026-07-25 — Excel import inspection (FR-CON-04)

**Added**
- Added the permission-gated `POST /api/v1/contacts/import/inspect` contract for workbook headers,
  one sample row, worksheet name, estimated data-row count, and non-mutating header validation.
- The inspection path reuses the importer's existing openpyxl parser and cell rendering, runs its
  synchronous workbook work outside the async request loop, and applies a 25 MB inspection ceiling.
- The contact import wizard now accepts `.xlsx`, uploads it for inspection before mapping, and keeps
  the existing browser parser for CSV. No SheetJS or second workbook parser was introduced.

**Changed**
- ADR-0002 moved from proposed to accepted. Docs 4 §14.1 and 5 B3.3 record the additive inspection
  API; the existing async import endpoint and its request contract are unchanged.
- Recovered the canonical project state from Git and executable gates: synchronized the README,
  implementation tracker, roadmap statuses, and deployment guide with the post-RC1 repository.
- Excluded generated `.pytest-run*` directories from Git and the backend Docker build context; an
  unreadable local pytest directory can no longer block production image packaging.

### 2026-07-23 — Docker deployment validation (first execution of the containerised stack)

The production stack was built and run for the first time. Four defects were reproduced in the
running deployment and fixed; none were visible to static review or to the test suite, because
each only manifests in a worker process or at the edge proxy.

**Fixed**
- **All async background work failed after the first task in each worker process.** Every task
  runs under its own `asyncio.run(...)`, which creates and then closes an event loop, while the
  SQLAlchemy engine and Redis client were cached in module globals. The second task in a process
  inherited a connection pool bound to a closed loop and raised
  `got Future attached to a different loop`. `scheduler_tick` was failing every minute; campaign
  dispatch, webhooks, imports, exports, media and analytics rollups were all dead. The engine and
  the Redis client are now rebuilt when the running loop changes
  (`app/db/session.py`, `app/core/redis.py`).
- **Storage backend unavailable in workers.** `app.storage.local` registers itself on import, and
  the only import lived in `app.main` — which a worker never loads. Every worker-side write failed
  with `storage backend 'local' is not available; registered: ()`. Registration moved into
  `app/storage/__init__.py` so it holds for every process.
- **nginx served 502 after any container recreation.** A statically named `upstream` server is
  resolved once at config load and cached for the process lifetime, so `docker compose up -d` —
  the documented upgrade step — left the edge proxying to the previous container's address.
  Reproduced (nginx held `172.19.0.7` while the API had moved to `172.19.0.6`) and fixed with a
  `resolver` plus request-time resolution; verified by moving the API to a new address and
  observing recovery with no reload. Costs the upstream keepalive pool, which open-source nginx
  cannot combine with re-resolution.
- **Duplicate security headers on `/health` and `/ready`.** The probe locations lacked the
  `proxy_hide_header` set that `/api/` already had, so each probe returned two copies of every
  security header and leaked the API's HSTS over plain HTTP.

**Correction (2026-07-24)** — this entry originally closed with a "Known, not fixed" note about
`ExportService.download_url` signing `export-<uuid>` onto a UUID-typed media route and returning 422.
That defect **was** fixed later the same day, in `c86d11c`, which added
`/api/v1/artifacts/{artifact_id}/download` and made `LocalStorageProvider.signed_url` route by id
shape; the note was simply never removed. Verified on 2026-07-24 against the running stack (the
artifacts route answers 400 for a missing signature rather than 404) and by
`tests/test_api_export.py::test_export_download_url_serves_the_csv`, which downloads a real export
with no `Authorization` header and asserts its bytes. Recorded as `docs/adr/0001`.

---

## [1.0.0-rc1] — 2026-07-23

First release candidate. Everything recorded below this heading is included in the tag
`v1.0.0-rc1`; entries above it are post-RC1 work.

### Added
- **Task & Activity Engine** (Doc 14) — models, migration `0026_tasks`, RBAC scopes, 15 endpoints.
- **Analytics & Reporting** (Doc 15) — migration `0027_analytics`, rollup pipeline, query service,
  report exports, 16 endpoints.
- **Frontend application** — authentication, dashboard, contacts, inbox, campaigns, templates,
  media, WhatsApp accounts, segments, pipelines, tasks, analytics, operations, admin, settings.
- **Production deployment** — multi-stage backend and frontend images, `docker-compose.production.yml`
  (10 services), edge and SPA nginx configuration, `deploy/DEPLOYMENT.md`, `.env.production.example`.
- `LICENSE` (proprietary, matching the terms already declared in `backend/pyproject.toml`).

### Fixed
- **Startup blocker** — `CORS_ORIGINS` was JSON-decoded by pydantic-settings before validators ran,
  so the empty and comma-separated forms both raised `SettingsError` at import. Every backend
  process (api, three worker pools, beat, migrate) failed to start. Now `Annotated[..., NoDecode]`.
- **Celery task registration** — workers imported no task modules, so every pool started with an
  empty registry and rejected all work. `include=TASK_MODULES` now registers all 23 tasks.
- **JSON logging** — the parent `uvicorn` logger held a plain stderr handler with `propagate=False`,
  so request lines never reached the JSON handler despite `LOG_JSON=true`.
- **`list` shadowing in `TaskService`** — a method named `list` shadowed the builtin for annotations
  later in the class body, so those signatures resolved to the method. Harmless at run time under
  deferred annotations, but it broke type resolution and `typing.get_type_hints()`.
- **`_fail` return type** in the segment compiler — annotated `NoReturn`, so the existing
  `if spec is None: _fail(...)` guard narrows as the code already reads.
- **`.gitignore`** — `.env.production.example` was matched by the broad `.env.*` rule and excluded
  from the repository, although `deploy/DEPLOYMENT.md` §2 begins by copying it.

### Changed
- Version aligned to `1.0.0-rc1` across `pyproject.toml` (PEP 440 `1.0.0rc1`), `app/__init__.py`,
  `Settings.app_version`, and `package.json`. `frontend/openapi.json` regenerated — the only
  semantic change is `info.version`.
- Frontend production build emits `sourcemap: "hidden"` and splits framework vendor chunks.

### Known limitations
- **The containerised deployment has never been executed.** No image has been built and no
  container started in any environment available to date. See §Remaining Blockers in the RC1
  report and `deploy/DEPLOYMENT.md`, which is written as a commissioning procedure.
- `tests/test_analytics_rollup.py` hard-codes `NOW = 2026-07-23 14:30`; two tests fail when real
  UTC falls inside the derived `[08:00, 14:00)` window on that date. Fixture defect, not a product
  defect.

---

### 2026-07-18 — Amendment: Message Reactions (Doc 7 → v1.1, Doc 4 v1.3 → v1.4, Doc 3 v1.3 → v1.4) — **FROZEN**
**Reason:** Phase 7 Step 9 (Message Reactions) was **blocked by a frozen-doc conflict.** Doc 4 §18.2
defines `POST /messages/{uuid}/reaction` (send a reaction), but Doc 7 §5.2's Meta capability column
declared `text/media/interactive/template/bulk` only — reaction was **deliberately undeclared** (the
Meta adapter surfaces `ChannelNotSupported`), so no channel could fulfil the endpoint. The canonical
seam (`MessageType`) and SendService likewise had no reaction path.

**Decision (owner):** amend additively so reaction is **adapter-capability-driven**; the Meta adapter
declares it (Meta Cloud API supports outbound reactions). Invent no behaviour beyond the frozen contract.

**Changed — Doc 7 (Integrations & Channel Architecture) → v1.1**
- **New §5.2a** — the Meta adapter additionally declares `send_reaction` (capability-flagged); the §5.2
  baseline matrix is unedited. Decision **CD20** (reaction is adapter-declared, not assumed).

**Changed — Doc 4 (API Design) v1.3 → v1.4**
- **§18.2** — appended the full `POST /messages/{uuid}/reaction` contract: `{emoji}` payload (empty =
  remove), single-emoji validation (`invalid_emoji`), `Idempotency-Key` required, `messages:send`, the
  24-hour free-form window rule (`window_closed`), `not_reactable`/`opt_out`, the `202` accept→deliver
  flow through SendService→Meta adapter, and failure handling. §18.2 table row unedited.

**Changed — Doc 3 (Database Design) v1.3 → v1.4**
- **New §9.2a** — confirms reaction storage: `message_type='reaction'` (already enumerated) + the
  `content_json` reaction format `{reaction:{message_id:<target wamid>, emoji}}`, target referenced by
  the target's `wamid`. **No new column, no migration.** §9.2 schema unedited.

**Decision records added:** Doc 7 **CD20**.
**Compatibility:** additive only — no schema/migration, no code (implementation follows on approval).
Docs 1, 2, 5, 6, 8–12 unedited.

### 2026-07-18 — Amendment (backfill log): Conversation Tags (FR-INB-07) — Doc 3 v1.2 → v1.3, Doc 4 v1.1 → v1.3 — **FROZEN**
**Backfilled.** The conversation-tags amendment shipped in commit `4ec1c34` with in-document `v1.3`
markers but was not logged here at the time; governance (top of file) requires every frozen-doc change
be recorded, so it is logged now.
**Changed — Doc 3:** new **§9.7 `conversation_tags`** (M:N junction reusing the `tags` taxonomy) + §12.3
M:N row, §13.2 reverse-index row, §19 sizing row. **Changed — Doc 4:** **§18.1** conversation-tag
endpoints (`POST`/`DELETE /conversations/{uuid}/tags`), the additive `tags[]` array on list/detail
reads, and the single-valued `tag` filter.
**Compatibility:** additive; realized by migration `0025_conversation_tags` (Phase 7 Step 5, HEAD
`16c65e2`). The Doc 4 marker used `v1.3` in lockstep with Doc 3 (Doc 4 `v1.2` is unused).

### 2026-07-17 — Amendment: FR-CAM-11 rate card & cost estimation (Doc 3 → v1.2, Doc 4 → v1.1) — **FROZEN**
**Reason:** Phase 6 Step 5 (Cost Engine) was **blocked**. The frozen set defined the cost engine's
*consumers* (`campaigns.estimated_cost`, `messages.cost_*`, `pricing_model`, `is_billable`) but never
its *source*: no rate-card entity or schema existed in Doc 3, Doc 7 contained no pricing content, and
Doc 12 §53 places Meta's pricing under "External … not restated here". Doc 4 §17 specified
`estimate-cost` by sample response only, with a bare `422` and no machine code. Gap analysis:
`docs/design/FR-CAM-11-GAP-ANALYSIS.md`.

**Decision (owner):** amend with the **minimum** required to unblock **pre-send estimation only**.
Invent no pricing data and no billing semantics.

**Changed — Doc 3 (Database Design) v1.1 → v1.2**
- **New §8.5 `rate_cards`** — entity, storage model, schema, resolution & money rules, country
  resolution, and an explicit deferred list. Global (no `organization_id`, per Doc 4 §17's "no
  reseller markup"), operator-managed, **ships empty**, versioned by effective dating (supersede,
  never mutate).
- **New §12.4a** — `rate_cards` value joins (no FK to contacts/templates/campaigns) + tenancy note.
- **§12.2** — `users` → `rate_cards` (`created_by`), the card's only FK.
- **§13.2** — rate-card lookup + uniqueness indexes.
- **§16 entity map** — Rate Card row added.

**Changed — Doc 4 (API Design) v1.0 → v1.1**
- **§17** — `POST /campaigns/{uuid}/estimate-cost` upgraded from sample to full contract: request,
  `200` shape with the `recipients == Σ breakdown[].count + unresolved.count` invariant, money
  serialization, the `campaigns.estimated_cost` side effect, and errors.
- **§17 wire format** — monetary fields (`unit`, `subtotal`, `estimated_total`) are **fixed-scale
  JSON strings**, not numbers: a JSON number carries no scale and most clients parse it into a
  binary float, the one representation money must not pass through. The v1.0 sample illustrated them
  as numbers; v1.1 makes the string format normative.
- **§17 route table** — bare `422` → `422(rate_card_not_configured)`, `404`.
- **New §17.1** — rate-card administration (the operator update mechanism). Requires **elevated
  administrative authority** (platform-level, never tenant-level, since the card is global); the
  concrete RBAC mapping is **left to the authorization model**, not frozen here. **Specified for
  future administration — not implemented in Phase 6 Step 5**, which delivers the read path only.
- **§31** — bulk `/estimate` cross-reference pinned to §17 as the single rate-card contract.

**Money rules fixed:** single-currency card (no FX); `unit_price DECIMAL(12,6)`; subtotals exact
(no intermediate rounding); total rounded **once** to 4 dp **ROUND_HALF_UP** at the storage boundary.

**Country resolution fixed:** `contacts.country_code IS NULL` ⇒ recipient is *unresolved* — counted
and reported, excluded from the total, **never** silently dropped and **never** derived from the
`wa_id` E.164 prefix (no prefix→country dataset is specified).

**Contradictions resolved:**
1. `messages.category` permits `service` while `ck_tpl_category` permits only three categories — a
   campaign always sends a template, so `service` is unreachable from an estimate. Doc 4 §17's sample
   note referencing free-tier **service** conversations was incorrect and is **corrected**.
2. Rate card treated as internal authority but declared external (Doc 12 §53) — resolved by making it
   operator-managed data that ships empty, with the platform restating no Meta pricing.
3. "No reseller markup" (global card) vs per-row `cost_currency` (per-tenant currency) — resolved by
   the single-currency invariant: `cost_currency` *records* the card's currency, it does not select one.
4. Precision mismatch (`DECIMAL(12,6)` per message vs `DECIMAL(14,4)` per campaign) — resolved by the
   round-once-at-the-boundary rule.

**Explicitly DEFERRED / OUT OF SCOPE** (unchanged, still undefined — Doc 3 §8.5.5):
`messages.pricing_model`, `messages.is_billable`, `messages.cost_*`, `campaign_recipients.cost_amount`,
**`campaigns.actual_cost` population**, the Meta pricing **webhook payload**, billing reconciliation,
and finance reporting.

> **Rationale — `campaigns.actual_cost` remains unset:** `campaigns.actual_cost` must represent the
> provider-authoritative charge. Computing it from the local rate card would produce another estimate
> rather than the provider's billed amount. Estimated and actual values may legitimately diverge due
> to provider pricing rules, discounts, credits, or future pricing changes. Therefore
> `campaigns.actual_cost` remains unset until an authoritative provider pricing source and contract
> are defined.

**Impact:** documentation only — no code, schema migration, or pricing data in this change. Docs 1, 2,
5–12 unedited. Implementation of Phase 6 Step 5 resumes from this amended specification on approval.

### Design documents — status
- **Doc 12 — Enterprise Governance** — `v1.1` (`12-ENTERPRISE-GOVERNANCE.md`; §1–§55 = v1.0 baseline, §56–§66 added in the governance-handbook enhancement pass; 66 sections, 22 diagrams). Master governance / single entry point referencing Docs 1–11 without duplication.
- **Doc 11 — Operations Runbook** — delivered, awaiting owner approval (`11-OPERATIONS-RUNBOOK.md`; 85 sections, 15 diagrams, OD1–OD40). Operational-only; references Docs 1–10 without redefining them.
- **Doc 9 — AI & Automation Architecture** — delivered, awaiting owner approval (`09-AI-AUTOMATION-ARCHITECTURE.md`; 52 sections, AD1–AD43). Additive; no frozen doc edited.
- **Doc 10 — Testing & QA Architecture** — `v1.1` **FROZEN** on 2026-07-15 (`10-TESTING-QA-ARCHITECTURE.md`; §1–§60 = v1.0 baseline, §61–§72 added in pass; 72 sections, 18 diagrams, TD1–TD65). Additive; references Docs 1–9 without duplication.
- **Doc 1 — SRS** — `v1.0` **FROZEN** on 2026-07-15 (authoritative specification).
- **Doc 2 — Expanded Feature Matrix** — `v1.0` **FROZEN** on 2026-07-15.
- **Doc 3 — Database Design** — `v1.4` **FROZEN** (v1.0 baseline; **§21 Business Event Ledger** → v1.1; **§8.5 `rate_cards`** + §12.4a/§12.2/§13.2/§16 → v1.2 on 2026-07-17; **§9.7 `conversation_tags`** + §12.3/§13.2/§19 → v1.3 on 2026-07-18; **§9.2a reaction payload** → v1.4 on 2026-07-18).
- **Doc 4 — API Design Specification** — `v1.4` **FROZEN** (v1.0 on 2026-07-15 incl. enhancement pass §29–§36 + §23.1/§24.1/§27.1/§27.2; **§17 estimate-cost** + **§17.1 rate-card admin** → v1.1 on 2026-07-17; **§18.1 conversation tags** → v1.3 on 2026-07-18; **§18.2 reaction contract** → v1.4 on 2026-07-18).
- **Doc 5 — UI/UX Design Specification** — `v1.1` **FROZEN** (v1.0 = Parts A–F incl. F1–F15; **Part G Executive Business Dashboard** added in the final additive pass).
- **Doc 6 — Queue & Scheduler Design** — `v1.2` **FROZEN** (pass 1 §21–§34 at v1.0; pass 2 §35–§46 → v1.1; final additive pass **§47 Enterprise Domain Event Bus** + **§48 Business KPI Metric Catalog** → v1.2).
- **Doc 7 — Integrations & Channel Architecture** — `v1.1` (delivered v1.0, awaiting owner approval; **§5.2a Meta `send_reaction` capability** amendment + decision **CD20** added on 2026-07-18 → v1.1). Realizes the dual-channel / Support Connector spec that frozen Doc 6 forward-references as "Doc 6.5" (content in `07-INTEGRATIONS-CHANNEL-ARCHITECTURE.md`; Doc 6 unedited). Defines new **additive** entities (connector registry/session/health, lead pipelines/stages, conversation tags, assignment rules) and additive columns (`connector_id`, lead references) to be applied via migration when built — no frozen doc edited.
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

### 2026-07-17 — **Module 2 — CRM COMPLETE** FROZEN (`v0.5.4-module2-foundation`)
Closes the module opened by `v0.2.0-crm-foundation`, whose async half was deferred by dependency to
the Queue Engine + Storage. **Every mandatory SRS contact requirement is now built:** FR-CON-01/02
(CRUD, keyset pagination at 1M+), **03/04** (CSV **and Excel** import with column mapping + per-row
validation), **05** (async import: progress + downloadable error report), **06** (duplicate detection
with `skip`/`merge`/`overwrite` on import, plus a standalone dedup scan/merge), **07/08** (bulk edit
and bulk soft-delete over a selection or filter), **09** (tags), **10** (segments), **11** (typed
custom attributes), **12** (advanced AND/OR search), **14** (activity timeline), **15** (export to
**CSV / Excel / JSON**).

**Steps:** 1–4 = `v0.2.0-crm-foundation` (sync surface) · 5A `v0.5.0-module2-import` · 5B
`v0.5.1-module2-export` · 5C `v0.5.2-module2-bulk` · 5D `v0.5.3-module2-formats`.
**Migrations:** 0005–0008 (contacts, tags/events/leads, segments, custom attributes), 0011 (imports),
0012 (exports), 0013 (bulk_jobs).
**State at freeze:** 249 backend tests passing, ruff clean, migrations 0001–0013 reversible, zero
model↔migration drift, OpenAPI 3.1.0 valid (62 paths / 87 operations). RBAC uses only seeded catalog
permissions (`contacts:*`, `segments:*`).

**Architectural note.** The async CRM is deliberately thin: every bulk path (import, export,
bulk-update/delete, merge) resolves its audience through the **same rule compiler** as segments and
search, walks it in **keyset batches**, and applies each item **through the CRM's own services** — so
a row created by an import and a row edited in bulk obey exactly the same validation, timeline and
audit rules as one touched through the single-contact API. Format is only a rendering choice
(`app/crm/formats.py`); the audience and columns are shared.

**Still deferred (unchanged, by dependency — NOT missing):**
| Deferred | Reason | Lands with |
|---|---|---|
| Auto opt-out on "STOP" (FR-CON-13, the requirement's second half; status field itself is built) | Needs inbound message handling | Messaging (M4) |
| Internal notes, contact assignment, `conversation_lead`/`lead_stage_transitions` | Frozen docs scope these to `conversations` | Inbox (M7) |
| `Idempotency-Key` (Doc 04 §8), `bulk`/`read`/`write` rate classes (Doc 04 §9) | **Cross-cutting** — belong to every side-effectful POST, not to contacts alone; import/export/bulk all shipped without them | Own hardening step |
| Doc 04 §30's wider bulk family (`/contacts/bulk` create, `bulk-tag`, `bulk-attributes`, `/campaigns/bulk-action`, `/templates/bulk`) | Out of §14.1's contact scope | Their own modules |

### 2026-07-17 — **Module 2 — Step 5D: Excel import, Excel & JSON export** (`v0.5.3-module2-formats`)
**Scope delivered (no migration, no new endpoint):** **`.xlsx` import** (FR-CON-04) and **Excel/JSON
export** (FR-CON-15) — the last two mandatory CRM requirements, and ones the schema already promised:
`exports.format`'s `ck_exports_format` constraint (Doc 03 §11.6) and Doc 06 §2.3 (`exports` =
"CSV/Excel/JSON") declared all three formats while the services accepted only CSV.

**Reuse over reimplementation:** `read_xlsx` returns the **same header-keyed rows** as `read_csv`, so
the import pipeline's mapping, validation and error report are format-agnostic and untouched; the
export gains a per-format **writer** while the audience, `EXPORT_COLUMNS` and keyset streaming loop
stay shared. CSV output is byte-for-byte unchanged (asserted by test). Excel quirks handled at the
reader: a phone typed as a number renders as `14155550001`, never `1.4155550001e+10`; blank trailing
rows are dropped. Adds `openpyxl` (read-only / write-only modes, so neither direction builds a full
cell graph). **State:** 249 tests passing (+11), ruff clean.

### 2026-07-17 — **Module 2 — Step 5C: bulk operations & duplicate merge** (`v0.5.2-module2-bulk`, migration 0013)
**Scope delivered:** the last CRM items deferred to the Queue Engine (CHANGELOG 2026-07-16 deferral
table) — **bulk update** (FR-CON-07: `add_tags` / `remove_tags` / `set_attributes`), **bulk delete**
(FR-CON-08, soft), and **duplicate scan / merge** (FR-CON-06, `report` or `merge`). All three are
async-only per Doc 04 §14.1: `POST /contacts/bulk-update`, `POST /contacts/bulk-delete`,
`POST /contacts/deduplicate` return **`202` + job** and run on the Queue Engine; progress and the
**§29 partial-success envelope** are polled at `GET /contacts/bulk/{uuid}`. RBAC `contacts:write`
(already seeded — no catalog change); every operation audited (`bulk.started`, `bulk.completed`,
`contact.merged`).

**Design decisions (each traceable to a frozen doc):**
- **Addressing** follows Doc 04 §30's two mutually-exclusive modes — explicit `ids` or a `filter` —
  with the optional **`expected_count` safety guard** (resolved count differs → **409**, act on
  nothing). Filters reuse the **same rule compiler** segments/search/export use, so one audience
  definition serves all four.
- **Per-item commit** (Doc 04 §29): a rejected contact lands in `errors[]` (capped at 100) plus a
  signed, downloadable `error_report_url`, and never rolls back the rest.
- **Idempotent by construction** (Doc 06 §8): attaching a present tag, deleting a deleted contact and
  merging an already-merged group are all no-ops, so at-least-once redelivery converges without
  snapshotting a million-row selection. Every action is applied **through the CRM's own services**, so
  a bulk edit obeys the same validation/timeline/audit rules as the single-contact endpoints.
- **Merge semantics** (FR-CON-06): the **oldest** contact of a group survives; blanks are filled from
  duplicates (a set primary field is never overwritten), tags and attribute values move across, the
  duplicate is soft-deleted, and the merge is recorded on the survivor's timeline (`contact_merged`).
  `wa_id`/`phone_e164` are never merged — they are the survivor's identity.
- **Memory-bounded**: the audience is walked in keyset batches and the dedup scan pages over *groups*,
  so a 1M-row table never materialises.

**State:** 237 backend tests passing (+16), ruff clean, migrations 0001–0013 reversible, zero
model↔migration drift, OpenAPI 3.1.0 valid (62 paths / 87 operations).

**Deferred (unchanged by this step):** `Idempotency-Key` (Doc 04 §8) and the `bulk`/`read`/`write`
rate classes (Doc 04 §9) are **cross-cutting** and remain unbuilt — import/export shipped without
them too. They should be retrofitted across every side-effectful POST in one step, not bolted onto
contacts alone. Doc 04 §30's wider bulk family (`/contacts/bulk` create, `/contacts/bulk-tag`,
`/contacts/bulk-attributes`, `/campaigns/bulk-action`, `/templates/bulk`) belongs to its own module;
this step delivers only the three endpoints Doc 04 §14.1 scopes to contacts.

### 2026-07-16 — **Module 2 — Step 5B: contact export (async)** (`v0.5.1-module2-export`, migration 0012)
*(Backfilled 2026-07-17: the tag shipped without its changelog entry, which the governance policy
above requires.)*
**Scope delivered:** `exports` (Doc 03 §11.6) + `POST /contacts/export` → **`202` + job** and
`GET /contacts/export/{uuid}` → progress + **signed, expiring download URL** (FR-CON-15, CSV at this
step; Excel/JSON landed in 5D). Runs on the Doc 06 §2.3 `exports` queue. The filter resolves through
the **same compiler** segments/search use, so an export returns exactly what its preview showed, and
the result is walked in **keyset batches** rendered incrementally — a 1M-row export never
materialises 1M ORM objects. The artifact is written through the **Storage** abstraction and bounded
by `expires_at` (an expired export stops serving a URL). Re-running regenerates rather than
duplicating (Doc 06 §8). RBAC `contacts:export`; audited (`export.started` / `export.completed`).
**State at the time:** 213 tests passing, ruff clean, zero drift.

### 2026-07-16 — **Module 2 — Step 5A: contact import (async)** (`v0.5.0-module2-import`, migration 0011)
*(Backfilled 2026-07-17: the tag shipped without its changelog entry, which the governance policy
above requires.)*
**Scope delivered:** `imports` (Doc 03 §11.6) + `POST /contacts/import` → **`202` + job** and
`GET /contacts/import/{uuid}` → progress + **downloadable error report** (FR-CON-03/05/06). The
request path never parses a byte: the file is uploaded first via Media (§16) and referenced by
`upload_id`; the work runs on the Doc 06 §2.3 `imports` queue. Rows stream through the CRM's own
`ContactService`, so an imported contact is validated, deduped, timelined and audited by exactly the
same rules as one created through the API — no duplicated business logic. A bad row is collected
into the error report and **never aborts the import**; progress is committed as it goes and
already-imported rows are no-ops under `skip`/`merge`, so a retried task converges (Doc 06 §8).
Dedup `skip`/`merge`/`overwrite` on normalized `wa_id` (FR-CON-06). RBAC `contacts:import`; audited
(`import.started` / `import.completed`).
**State at the time:** 203 → 213 tests passing, ruff clean, zero drift.

### 2026-07-16 — **Storage Foundation** FROZEN (`v0.4.0-storage-foundation`)
**Scope delivered (migration 0010):** storage abstraction + provider registry (Doc 8 §14,
FR-MED-06, DD16) with a **local volume provider** (default) and an **S3-compatible provider
contract** that registers without touching callers — selecting an unregistered backend fails
loudly rather than degrading; **signed URL framework** (FR-MED-09: HMAC binds media id to
expiry, constant-time verify, expired→410 distinct from invalid→403); **media validation**
(FR-MED-01..04: per-type MIME allow-lists + Cloud API size ceilings → 413/415/422 *before* any
bytes are stored); **virus scan interface** (Doc 8 §26 — contract + hook only, no scanner ships,
fail-closed if a configured scanner errors); **upload/download services** (validate → scan →
hash → dedup → store → record; SHA-256 dedup per org, FR-MED-05). `media_assets` (Doc 3 §7.2)
holds metadata + a reference — **never blobs**. APIs: `POST /media/upload`, `GET /media`,
`GET /media/{id}`, `GET /media/{id}/content` (signed URL), `GET /media/{id}/download`
(signature-authenticated), `DELETE /media/{id}`. RBAC `media:read`/`media:write`; audited.

**Security fix (found by test):** the local provider stripped `..` textually, which could yield
an absolute path that re-rooted the join and escaped the storage root. Keys are now resolved and
required to stay under the root.

**State at freeze:** 203 backend tests passing, ruff clean, migrations 0001–0010 reversible,
zero drift.

**Not built (their own modules):** media processing (thumbnails/transcode), Meta media-id
refresh/caching (FR-MED-07), retention sweeps (FR-MED-08), a concrete S3 provider, a concrete
virus scanner.

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

### 2026-07-17 — Implementation order: frontend (M2) deferred — backend-first until the APIs are complete
**Reason:** Owner ruling. The frontend is deliberately deferred until the backend API surface is
complete, so the SPA is built once against a settled contract rather than chased across modules.
**Deviation from:** Doc 12 §15 / §42, which order delivery **M1 → M2 (Frontend Shell + Auth UI) →
M3 (Contacts) → M4 …**. Implementation has instead run M1 → M3 (Contacts) → Queue Engine → Storage
→ M3 async completion, leaving **M2 unbuilt** (`frontend/` holds only the scaffold committed with
M1: shell, theme, React Query, two routes — no login, no protected routing).
**Why this is safe:** Doc 12 §14's dependency graph is **not** violated — M2 depends on M1 (built),
and nothing built so far depends on M2. Only the *order* changed, not the dependency rule. The
Queue Engine and Storage Foundation were likewise built ahead of their manifest position because
M3's import/export/bulk items depend on them (Doc 04 §14.1 mandates `202 + job`).
**Impact:** No frozen document edited. §15/§42 remain the canonical order; this entry records the
approved departure. M2 re-enters the sequence once the backend APIs are complete.
**Naming note (no code impact):** commit/tag labels do not match the Doc 12 §56 manifest — "Module 2"
in git history is manifest **M3 (Contacts)**, and "Module 6 — Queue Engine" is the async fabric, not
manifest **M6 (Campaigns)**, which is not started. The manifest remains authoritative.

### 2026-07-17 — Module 2 Step 5C — additive deviations required to deliver bulk operations
**Reason:** Delivering Doc 04 §14.1's `bulk-update` / `bulk-delete` / `deduplicate` surfaced two gaps
in the frozen set. Recorded here per the §27 change-management rule; **no frozen document edited**.
1. **New table `bulk_jobs`** (migration 0013), additive, reversible, sitting beside `imports`/`exports`
   in the Doc 03 §11.6 job-record family. *Why:* Doc 04 §30 says async bulk ops report
   `processed/total/succeeded/failed`, but Doc 03 §11.7's `job_metadata` has **no progress columns
   and no `organization_id`**, and `imports` cannot be reused (`format` is `NOT NULL`, and its
   `source_key`/`mapping_json` are file-import specific). Doc 12 §56 lists no bulk table for M3
   because §30 assumed `job_metadata` would carry this; it cannot.
2. **Poll endpoint `GET /contacts/bulk/{uuid}`** (`contacts:write`) instead of Doc 04 §30's
   "poll `GET /jobs/{uuid}`". *Why:* §22 gates `/jobs/{uuid}` behind **`system:read`** and
   `job_metadata` is organization-blind, so that route can serve neither a `contacts:write` operator
   nor tenant scoping — §30 and §22 contradict each other. The chosen shape is the one §14.1 already
   defines for the import/export progress endpoints.
3. **Queue placement:** bulk work runs on the existing **`imports`** queue — Doc 06 §2.3 scopes it to
   long-running CRM "parse, validate, dedup, upsert" work (P3, Jobs pool, 300s/600s,
   `job=failed + error report`), and Doc 12 §56 grants M3 no other write queue. **No queue was added**
   to the frozen §2.3 taxonomy; the three operations stay independently traceable via distinct task
   names.
**Impact:** Additive only. Docs 3/4/6/12 unedited; if the owner wants the frozen text reconciled to
match, that is a separate documentation pass.

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
