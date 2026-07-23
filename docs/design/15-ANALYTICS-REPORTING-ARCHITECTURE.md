# Analytics & Reporting — Architecture
### Self-Hosted WhatsApp Business Platform — Phase 8

| | |
|---|---|
| **Document** | 15 — Analytics & Reporting (Phase 8) |
| **Version** | 1.0 — **DRAFT FOR OWNER APPROVAL** (freezes on approval, per Doc 12 governance) |
| **Date** | 2026-07-22 |
| **Implements** | Doc 02 §J **J1–J8** (J9 funnels deferred), FR-AN-01…FR-AN-07, NFR-PERF-06 |
| **Extends (does not edit)** | Doc 03 (DB), Doc 04 (API), Doc 05 (UI/UX), Doc 06 (Queue), Doc 12 (RBAC), Doc 14 (Tasks) |
| **Verified against** | `queue/registry.py` (`analytics.rollup` declared, P3/maintenance/3×/120s/300s/park) · `models/job_records.py` (`ExportJob`, `BulkJob`) · `rbac/catalog.py` (`analytics:read` seeded) · `db/{mixins,types,base}.py` · Doc 03 §6.5/§8.3/§8.5/§9.1/§9.2/§9.3/§9.6/§11.6/§11.7 · migration head `0026_tasks` · `frontend/openapi.json` (115 paths) |
| **Governance** | **Purely additive.** New tables, endpoints, permissions and one frontend feature. **Zero** modifications to any frozen table, endpoint, schema, or Doc 01–14. |

> **Purpose.** Every operational module now writes durable, queryable history — the message ledger,
> the delivery log, the campaign recipient log, the conversation record, the task engine, and the
> contact timeline. Nothing reads it back as *insight*. This document specifies the analytics layer
> completely — event sources, rollup strategy, tables, cadence, KPI definitions, API, exports,
> permissions and operations — so that Phase 8 implementation is **mechanical**: build to this
> document, regenerate types from the updated OpenAPI, and verify.
>
> **The central discipline of this design is that analytics never becomes a second source of
> truth.** Rollups are derived, disposable and rebuildable; the operational tables remain
> authoritative. Any rollup can be dropped and recomputed from source at any time.

---

## 1. Traceability & requirement IDs

| ID | Requirement | Doc 02 |
|---|---|---|
| **FR-AN-01** | Delivery / read / failure reporting over the message ledger. | J1 |
| **FR-AN-02** | Campaign analytics (rates over time, drill-down) and agent performance. | J2, J6 |
| **FR-AN-03** | Cost analytics — real spend, rate-card exact. | J3 |
| **FR-AN-04** | Click / URL tracking via a first-party shortener. | J4 |
| **FR-AN-05** | Real-time-feeling dashboard with live stats. | J5 |
| **FR-AN-06** | Exportable reports (CSV / Excel / JSON). | J8 |
| **FR-AN-07** | Failure analysis grouped by Meta error code, with guidance. | J7 |
| **FR-AN-08** | *(new here)* Customer/CRM metrics — growth, opt-in health, reactivation. | — |
| **FR-AN-09** | *(new here)* Task & follow-up metrics, redeeming the Doc 14 §12 reservation. | — |

---

## 2. Scope

**In scope (Phase 8):** the rollup pipeline, the analytics tables, the read API, report exports,
and the frontend Analytics module.

**In scope but separable (Phase 8b):** click tracking (J4). Its tables are already designed
(Doc 03 §9.6) but it additionally needs a **public redirect endpoint** and link-rewriting in the
send path — a different shape of work from the read-only analytics API. It is specified here (§13)
and scheduled as its own milestone (§26) so the core analytics milestone stays read-only.

**Explicitly NOT built:** funnels / conversion attribution (J9, deferred by Doc 02), AI-generated
insights (Doc 09, Phase 9), scheduled report email delivery (needs the Notification Center,
Doc 05 F7 / Phase 10), and any OLAP/warehouse engine (§24).

**Decoupling contract.** As Doc 14 §2: the frontend consumes **only** generated types from the
updated OpenAPI (`npm run gen:api`). No hand-written API types. The backend remains the single
source of truth for the contract.

---

## 3. Design principles & reuse map

Analytics is assembled almost entirely from primitives that already exist.

| Concern | Reused frozen primitive | New? |
|---|---|---|
| Identity, timestamps, audit | `IntPKMixin`, `UUIDMixin`, `TimestampMixin`, `AuditMixin` (`db/mixins.py`) | reuse |
| Cross-dialect types | `big_id()`, `datetime6()`, `int_id()`, `MYSQL_TABLE_ARGS` (`db/types.py`) | reuse |
| Index/constraint naming | `NAMING_CONVENTION` (`db/base.py`) | reuse |
| Background execution | `analytics.rollup` queue — **already declared** in `queue/registry.py` | reuse |
| Periodic triggering | `scheduler.tick` (P0/control) + `celery.schedules.crontab`, as `campaign_schedule_service` does | reuse |
| Export artifacts | `exports` table + `ExportJob` + `ExportService` + `exports` queue (Doc 03 §11.6) | reuse |
| Cursor pagination | `Page`, `encode_cursor`/`decode_cursor` (`api/pagination.py`) | reuse |
| Error envelope | RFC 7807 problem+json (Doc 04 §5) | reuse |
| Permissions | `resource:action` catalog + `require_permissions()` | reuse (+2 new) |
| Response mapping | Pydantic `XxxResponse.of(view)` | reuse pattern |
| Cost authority | `rate_cards` (Doc 03 §8.5) + the Phase 6 S5 cost engine | reuse |
| Click tracking tables | `short_links`, `link_clicks` (Doc 03 §9.6) | reuse (build in 8b) |
| Ops metrics | `monitoring_metrics` (Doc 03 §11.7) | reuse |
| Page shell, sections, charts | `PageContainer`, `PageHeader`, `Section`, `EmptyState`, `ErrorState`, `Spinner` | reuse |
| Data fetching | TanStack Query + `openapi-fetch` client | reuse |

**Six rollup tables + one control table. Two new permissions. One new frontend feature. Zero frozen
edits. Zero new queues.**

---

## 4. Overall architecture

```
 OPERATIONAL TRUTH                ROLLUP PIPELINE                 READ PATH
 ─────────────────                ───────────────                 ─────────
 messages ─────────────┐
 message_status_history┤          scheduler.tick (P0)
 campaign_recipients ──┤                 │ every 15 min
 conversations ────────┼──►  enqueue ────┴──► analytics.rollup (P3, maintenance)
 tasks / task_events ──┤                          │
 contacts ─────────────┤                          │ read closed buckets
 contact_events ───────┤                          │ delete-then-insert window
 link_clicks (8b) ─────┘                          ▼
                                        analytics_*_rollups  ──► AnalyticsQueryService
                                        analytics_rollup_runs        │
                                              (watermarks)           ├─► GET /analytics/* (JSON)
                                                                     └─► exports queue ──► ExportJob
                                                                              │
                                                                              ▼
                                                                     storage_key → download
```

Four properties follow from this shape:

1. **Derived, never authoritative.** Every rollup row is a pure function of source rows in a closed
   time bucket. Losing the rollup tables costs compute, not data.
2. **The read path never touches a partitioned high-volume table.** Dashboards read only small,
   indexed rollup tables. This is what makes the p95 targets in §22 achievable against a 10M+ row
   ledger.
3. **The write path is decoupled.** No operational transaction is slowed by analytics; the send
   path, webhook path and inbox path are untouched.
4. **One queue, already reserved.** `analytics.rollup` was declared in the registry from the start
   with exactly the right profile (background priority, maintenance pool, park on failure).

---

## 5. Event sources

Analytics reads only tables that already exist. Nothing is instrumented, no new event bus.

| Source | Doc 03 | Grain | Feeds |
|---|---|---|---|
| `messages` | §9.2 (partitioned, 10M+) | one row per message | volume, direction, type, cost |
| `message_status_history` | §9.3 (partitioned, 100M+) | one row per status transition | delivery/read/failure, latency, error codes |
| `campaign_recipients` | §8.3 (partitioned, 100M+) | one row per recipient | campaign funnel, per-campaign cost |
| `conversations` | §9.1 | one row per thread | open/resolved, response & resolution time, agent load |
| `tasks`, `task_events` | Doc 14 §5 | task + immutable history | completion rate, on-time %, throughput |
| `contacts` | §6.1 | one row per customer | growth, opt-in health, reactivation |
| `contact_events` | §6.5 (partitioned) | timeline events | engagement, lifecycle transitions |
| `link_clicks` | §9.6 (partitioned) | one row per click | click-through (Phase 8b) |
| `rate_cards` | §8.5 | pricing authority | cost analytics (value join, §12.4a) |

**Decision AN-CD1 — no event-sourcing layer.** A dedicated `analytics_events` stream was
considered and rejected: it would duplicate `contact_events`, `message_status_history` and
`task_events`, add a write-path dependency to every module, and create a second version of the
truth. The existing append-only logs *are* the event stream. This mirrors Doc 14 TA-CD1, which
rejected a parallel `activities` table for the same reason.

---

## 6. Rollup strategy

### 6.1 Grain

**All fact tables are stored at hourly grain in UTC.** Day, week, month and quarter are derived at
read time by summing hours.

This single choice resolves several problems at once:

- **Timezone correctness.** Organizations have a timezone (`organizations.timezone`); users have
  their own. A day boundary is a *presentation* concern. Storing UTC hours and folding to local
  days at read time gives correct local-day totals without storing a rollup per timezone — the same
  approach Doc 14 §7.3 took for task buckets.
- **Late data.** Delivery receipts arrive minutes to hours after the send. Hourly buckets can be
  recomputed cheaply within a trailing window (§8.2).
- **Volume.** 24 buckets/day × dimension combinations is small enough that the rollup tables stay
  in memory and need no partitioning (§21).

### 6.2 Additivity — the correctness rule

**Rollup columns store only additive components: counts and sums. Never ratios, never averages.**

A stored average cannot be re-aggregated: the mean of hourly means is not the daily mean. So
`analytics_conversation_rollups` stores `first_response_seconds_sum` **and**
`first_response_count`, and the API divides at read time. Every rate (delivery rate, completion
rate, on-time %) is likewise computed at read time from two stored counters.

This is the rule that makes arbitrary date ranges and granularities correct by construction.

**Decision AN-CD2 — no separate dimension tables.** A star schema with
`dim_agent`/`dim_campaign`/`dim_date` was considered and rejected. The operational tables (`users`,
`campaigns`, `phone_numbers`, `contacts`, `tags`) already *are* conformed dimensions, they are
small, and they are already joined everywhere else in the platform. Facts carry the internal
`BIGINT` id; names are resolved at read time exactly as `InboxQueryService` and `TaskService`
already resolve assignees and contacts. A duplicated dimension table would need its own sync job
and would drift.

### 6.3 Idempotency — delete-then-insert

Each rollup run, for each `(organization_id, bucket_hour)` it touches, **deletes that bucket's rows
and re-inserts them inside one transaction.** Re-running a window is therefore always safe and
always converges on the same answer.

**Decision AN-CD3 — delete-then-insert over UPSERT.** `INSERT … ON DUPLICATE KEY UPDATE` (MySQL)
and `ON CONFLICT` (SQLite) have different syntax, and the platform's test suite runs the same models
on SQLite (Doc 10). Delete-then-insert is dialect-neutral, needs no dialect branching in the
service, and is trivially correct when a dimension combination disappears from a recomputed bucket
(an UPSERT would leave a stale row behind). The delete is a narrow indexed range on a small table.

### 6.4 Watermarks

`analytics_rollup_runs` records, per organization and per rollup kind, the last bucket successfully
computed plus the outcome of the last attempt. The scheduler uses it to decide what to compute;
operators use it to see freshness; recovery uses it to replay (§23).

---

## 7. Queue integration

**No registry change is required.** The queue already exists with the correct specification:

```
QueueSpec(ANALYTICS_ROLLUP, "Build pre-aggregated dashboard/report rollups.",
          Priority.P3, Pool.MAINTENANCE, 3, 120, 300, DEST_PARK)
```

| Property | Value | Why it fits |
|---|---|---|
| Priority | P3 (background) | Never competes with sends, webhooks or control traffic. |
| Pool | `maintenance` | Isolated from `send-priority`/`webhook` pools; a slow rollup cannot slow delivery. |
| Max attempts | 3 | A transient DB blip retries; a persistent bug parks rather than spins. |
| Soft / hard timeout | 120 s / 300 s | §22 budgets an incremental run well inside 120 s. |
| Failure destination | `park` | Analytics failure is **not** data loss (§4.1) — parking for inspection beats a DLQ replay storm. |

**Tasks** (registered on `analytics.rollup`, following the existing `app/channels/tasks.py` pattern):

| Task | Trigger | Work |
|---|---|---|
| `analytics.rollup_incremental` | beat, every 15 min | Recompute the trailing window (§8.2) for every active org. |
| `analytics.rollup_backfill` | manual / operator | Recompute an explicit `[from, to)` range, one kind or all. |
| `analytics.rollup_prune` | beat, daily | Drop rollup rows past retention (§21). Runs on `cleanup` semantics but stays in this queue for locality. |

**Triggering** reuses `scheduler.tick` (P0, control pool) with `celery.schedules.crontab`, exactly
as `campaign_schedule_service` does. Per the tracker's standing rule: **do not hand-roll a cron
evaluator.**

**Concurrency — deterministic re-derivation, not locking.** No lock is taken. The delete-then-insert
bucket replacement of §6.3 is idempotent by construction: a bucket's rows are a pure function of the
source rows in it, so any number of overlapping runs converge on the same answer. Two concurrent
runs may duplicate *work* and briefly contend on the same rows; neither can produce a wrong figure.
This is the same strategy the campaign dispatcher uses for the identical problem — a redelivered
task re-derives what is still owed rather than holding a lock. The platform has no general-purpose
distributed-lock utility, and this design deliberately does not introduce one.

---

## 8. Aggregation cadence

### 8.1 Schedule

| Kind | Cadence | Window recomputed |
|---|---|---|
| Incremental | every 15 min | trailing **6 hours**, closed buckets only |
| Nightly consolidation | daily 02:15 UTC | trailing **48 hours** |
| Prune | daily 03:00 UTC | rows older than retention (§21) |
| Backfill | on demand | operator-specified range |

### 8.2 Why a trailing window

A bucket is *closed* when its hour has elapsed, but rows can still land in it afterwards: a delivery
receipt for a 10:59 send may arrive at 11:05, and the retry engine can deliver hours late. Rather
than track per-row arrival, the incremental run simply recomputes the last 6 hours every time —
cheap, self-healing, and immune to clock skew. The nightly 48-hour pass catches anything later than
that (e.g. a webhook backlog drained after an outage).

### 8.3 Live figures

Doc 02 J5 asks for a dashboard that feels live. Rollups are at best 15 minutes stale, which is fine
for trends and wrong for "how many are waiting right now".

**Decision AN-CD4 — split trend from state.** *Trend* metrics (anything over a time range) read
rollups. *State* metrics (open conversations now, unassigned now, overdue tasks now) are **live
counts against the operational tables**, which are cheap because they are bounded by current work,
not history — precisely what `GET /tasks/stats` already does (Doc 14 §11). The dashboard composes
both; the API keeps them in separate endpoints (§16) so the caching story stays honest. Live panels
poll on the existing frontend interval convention (`POLL_INTERVAL_MS`).

---

## 9. Rollup tables

Six fact tables plus one control table. All use the frozen mixins and cross-dialect types, so a
single model renders Doc-03-exact types on MySQL 8 and portable equivalents on SQLite.

Shared columns on every fact table:

| Column | Type | Notes |
|---|---|---|
| `id` | BIGINT UNSIGNED PK AI | `IntPKMixin` |
| `organization_id` | BIGINT UNSIGNED | FK → `organizations.id` ON DELETE CASCADE |
| `bucket_start` | DATETIME(6) | start of the UTC hour |
| `created_at` / `updated_at` | DATETIME(6) | `TimestampMixin` |

No `uuid` (rollups are never addressed individually by a client), no soft delete (they are
regenerated, not retired), no `row_version` (no concurrent editing — one writer).

### 9.1 `analytics_message_rollups` — FR-AN-01

Dimensions: `phone_number_id`, `direction`, `message_type`.

| Measure | Type | Meaning |
|---|---|---|
| `accepted_count` | INT UNSIGNED | messages accepted by the platform |
| `sent_count` | INT UNSIGNED | reached the provider |
| `delivered_count` | INT UNSIGNED | delivery receipt seen |
| `read_count` | INT UNSIGNED | read receipt seen |
| `failed_count` | INT UNSIGNED | terminal failure |
| `cost_micros` | BIGINT UNSIGNED | rate-card cost, micro-units of org currency |
| `delivery_latency_ms_sum` | BIGINT UNSIGNED | Σ (delivered_at − sent_at) |
| `delivery_latency_count` | INT UNSIGNED | denominator for the above |

**Index:** `ix_amr_org_bucket` (organization_id, bucket_start) ·
`uq_amr_grain` UNIQUE (organization_id, bucket_start, phone_number_id, direction, message_type).

### 9.2 `analytics_failure_rollups` — FR-AN-07

Dimensions: `phone_number_id`, `error_code` VARCHAR(24).

| Measure | Type |
|---|---|
| `failure_count` | INT UNSIGNED |

**Index:** `ix_afr_org_bucket_code` (organization_id, bucket_start, error_code) ·
`uq_afr_grain` UNIQUE (organization_id, bucket_start, phone_number_id, error_code).

Error-code **guidance** (the "⭐ Improve" in J7) is a static lookup shipped in code
(`analytics/error_guidance.py`), keyed by Meta error code → cause + operator action. Not a table:
it is reference data that ships with the release, like `rbac/catalog.py`.

### 9.3 `analytics_campaign_rollups` — FR-AN-02, FR-AN-03

Dimension: `campaign_id`.

| Measure | Type |
|---|---|
| `targeted_count`, `sent_count`, `delivered_count`, `read_count`, `failed_count`, `skipped_count` | INT UNSIGNED |
| `click_count` | INT UNSIGNED (Phase 8b) |
| `cost_micros` | BIGINT UNSIGNED |

**Index:** `ix_acr_org_campaign_bucket` (organization_id, campaign_id, bucket_start) ·
`uq_acr_grain` UNIQUE (organization_id, bucket_start, campaign_id).

### 9.4 `analytics_conversation_rollups` — FR-AN-02 (agent), inbox metrics

Dimensions: `phone_number_id`, `assigned_user_id` (nullable = unassigned).

| Measure | Type | Meaning |
|---|---|---|
| `opened_count` | INT UNSIGNED | conversations entering `open` |
| `resolved_count` | INT UNSIGNED | conversations entering `resolved` |
| `inbound_message_count` / `outbound_message_count` | INT UNSIGNED | volume by direction |
| `first_response_seconds_sum` / `first_response_count` | BIGINT / INT UNSIGNED | agent responsiveness |
| `resolution_seconds_sum` / `resolution_count` | BIGINT / INT UNSIGNED | time to resolve |
| `handled_count` | INT UNSIGNED | distinct conversations the agent sent into this hour |

**Index:** `ix_acvr_org_bucket_user` (organization_id, bucket_start, assigned_user_id) ·
`uq_acvr_grain` UNIQUE (organization_id, bucket_start, phone_number_id, assigned_user_id).

Agent performance (§17) is this table grouped by `assigned_user_id`, joined with §9.5 for the task
side. **There is no separate agent rollup table** — an agent is a dimension, not a fact.

### 9.5 `analytics_task_rollups` — FR-AN-09, redeeming Doc 14 §12

Dimensions: `assigned_agent_id`, `task_type`.

| Measure | Type | Meaning |
|---|---|---|
| `created_count` | INT UNSIGNED | tasks created |
| `completed_count` | INT UNSIGNED | tasks completed |
| `completed_on_time_count` | INT UNSIGNED | `completed_at ≤ due_at` |
| `skipped_count` / `cancelled_count` / `reopened_count` | INT UNSIGNED | lifecycle outcomes |
| `overdue_entered_count` | INT UNSIGNED | open tasks whose `due_at` passed in this hour |
| `time_to_complete_seconds_sum` / `time_to_complete_count` | BIGINT / INT UNSIGNED | average time-to-complete |

Source is `task_events` (immutable history, Doc 14 §5.2) rather than `tasks`, so a task edited after
the fact does not rewrite history — exactly the property Doc 14 §12 promised ("metrics are
reconstructable and auditable after the fact").

**Index:** `ix_atr_org_bucket_agent` (organization_id, bucket_start, assigned_agent_id) ·
`uq_atr_grain` UNIQUE (organization_id, bucket_start, assigned_agent_id, task_type).

### 9.6 `analytics_contact_rollups` — FR-AN-08

No dimension beyond the org (customer metrics are org-wide; segment breakdowns drill down live).

| Measure | Type | Meaning |
|---|---|---|
| `created_count` | INT UNSIGNED | new customers |
| `opted_in_count` / `opted_out_count` | INT UNSIGNED | consent transitions |
| `reactivated_count` | INT UNSIGNED | inbound after ≥ 30 days silent |
| `active_count` | INT UNSIGNED | distinct contacts with any message this hour |

**Index:** `uq_actr_grain` UNIQUE (organization_id, bucket_start).

### 9.7 `analytics_rollup_runs` — control

| Column | Type | Notes |
|---|---|---|
| `id` | BIGINT UNSIGNED PK AI | |
| `organization_id` | BIGINT UNSIGNED | FK → organizations, CASCADE |
| `kind` | VARCHAR(32) | `messages·failures·campaigns·conversations·tasks·contacts` |
| `watermark_at` | DATETIME(6) | last successfully closed bucket |
| `last_run_at` | DATETIME(6) | attempt timestamp |
| `last_status` | VARCHAR(16) | `ok·failed·skipped` |
| `last_error` | TEXT NULL | truncated failure detail |
| `duration_ms` | INT UNSIGNED NULL | last run duration, feeds §23 monitoring |

**Index:** `uq_arr_org_kind` UNIQUE (organization_id, kind).

---

## 10. Time-series model

Every series endpoint returns the same envelope, so one frontend chart component renders all of them:

```json
{
  "granularity": "day",
  "from": "2026-07-01T00:00:00Z",
  "to": "2026-07-22T00:00:00Z",
  "timezone": "Asia/Kolkata",
  "series": [
    { "key": "delivered", "label": "Delivered",
      "points": [ { "t": "2026-07-01", "v": 1840 }, { "t": "2026-07-02", "v": 2013 } ] },
    { "key": "failed", "label": "Failed",
      "points": [ { "t": "2026-07-01", "v": 12 }, { "t": "2026-07-02", "v": 31 } ] }
  ],
  "totals": { "delivered": 41230, "failed": 402, "delivery_rate": 0.9903 }
}
```

Rules:

- **Buckets are dense.** Hours or days with no activity return `v: 0`, never a gap. Charts must not
  have to guess.
- **`t` is the local bucket label** in the resolved timezone; the range bounds stay ISO-UTC. There
  is exactly one place (§14) that resolves a timezone.
- **`totals` carries derived ratios**, computed from summed components per §6.2 — never summed from
  per-bucket ratios.
- Granularity ∈ `hour · day · week · month`, server-validated against the range (§14.3).

---

## 11. KPI definitions

Every KPI is defined here as an exact formula over §9 measures. This section is the contract
between backend and frontend: no metric is computed twice with two definitions.

### 11.1 Messaging & delivery (FR-AN-01)

| KPI | Formula |
|---|---|
| Messages sent | Σ `sent_count` (direction = outbound) |
| Messages received | Σ `accepted_count` (direction = inbound) |
| Delivery rate | Σ `delivered_count` / Σ `sent_count` |
| Read rate | Σ `read_count` / Σ `delivered_count` |
| Failure rate | Σ `failed_count` / Σ `sent_count` |
| Avg delivery latency | Σ `delivery_latency_ms_sum` / Σ `delivery_latency_count` |

> Read rate divides by *delivered*, not sent: a message that never arrived cannot be read, and
> dividing by sent silently blends two different failures.

### 11.2 Conversation & inbox

| KPI | Formula |
|---|---|
| Conversations opened / resolved | Σ `opened_count` / Σ `resolved_count` |
| Avg first response time | Σ `first_response_seconds_sum` / Σ `first_response_count` |
| Avg resolution time | Σ `resolution_seconds_sum` / Σ `resolution_count` |
| Resolution rate | Σ `resolved_count` / Σ `opened_count` |
| Open now · Unassigned now · Awaiting reply now | **live** (§8.3) |

### 11.3 Task & follow-up (FR-AN-09, Doc 14 §12)

| KPI | Formula |
|---|---|
| Tasks created / completed | Σ `created_count` / Σ `completed_count` |
| Completion rate | Σ `completed_count` / Σ `created_count` |
| On-time completion % | Σ `completed_on_time_count` / Σ `completed_count` |
| Avg time to complete | Σ `time_to_complete_seconds_sum` / Σ `time_to_complete_count` |
| Throughput per agent | Σ `completed_count` grouped by `assigned_agent_id` |
| Overdue now | **live** — reuses `GET /tasks/stats` |

### 11.4 Customer (FR-AN-08)

| KPI | Formula |
|---|---|
| New customers | Σ `created_count` |
| Net opt-in change | Σ `opted_in_count` − Σ `opted_out_count` |
| Opt-out rate | Σ `opted_out_count` / Σ `created_count` (range-scoped) |
| Reactivated | Σ `reactivated_count` |
| Active customers | Σ `active_count` (hour grain; de-duplicated per hour only — labelled *active hours*, not unique customers, see §25 Q3) |

### 11.5 Campaign (FR-AN-02)

| KPI | Formula |
|---|---|
| Reach | Σ `delivered_count` |
| Delivery / read / failure rate | as §11.1, scoped to `campaign_id` |
| Click-through rate | Σ `click_count` / Σ `delivered_count` (Phase 8b) |
| Cost per delivered | Σ `cost_micros` / Σ `delivered_count` |

### 11.6 Cost (FR-AN-03)

| KPI | Formula |
|---|---|
| Total spend | Σ `cost_micros` / 1e6, in org currency |
| Spend by category | Σ `cost_micros` grouped by conversation category from the rate card |
| Cost per conversation / per campaign | Σ `cost_micros` / Σ (conversations \| campaigns) |
| Forecast vs actual | campaign estimate (Phase 6 S5) vs Σ `cost_micros` |

Cost is **never recomputed** by analytics. The Phase 6 S5 cost engine is the pricing authority; the
rollup copies the cost already recorded against the message/recipient. One pricing implementation,
one answer.

---

## 12. Executive dashboard

The executive view (gated on `analytics:executive`, §15) is a composition of existing metrics, not
new ones:

| Panel | Source |
|---|---|
| Spend this month vs last | §11.6 |
| Delivery health (rate + trend) | §11.1 |
| Customer growth & opt-in health | §11.4 |
| Campaign ROI proxy (cost per delivered/read) | §11.5, §11.6 |
| Team throughput (conversations + tasks per agent) | §11.2, §11.3 |
| Top failure causes | §9.2 + guidance |

---

## 13. Click tracking (J4, Phase 8b)

Tables are **already designed** (Doc 03 §9.6) and are not redesigned here. What Phase 8b adds:

1. **Link rewriting** in the send path — outbound URLs replaced with `short_links.code`. This
   touches `SendService`, hence its own milestone and its own approval.
2. **Public redirect** `GET /r/{code}` — unauthenticated, outside `/api/v1`, 302 to `target_url`,
   writes `link_clicks`, increments the denormalized `short_links.click_count`.
3. **Rollup** — `click_count` folded into `analytics_campaign_rollups` (§9.3).

Privacy: `link_clicks.ip_hash` is a hash, never a raw IP (Doc 03 §9.6, Doc 12 P-series).

---

## 14. Date-range handling

### 14.1 Resolution order

Timezone resolves as: explicit `timezone` query parameter → the caller's `users.timezone` → the
org's `organizations.timezone` → UTC. One helper owns this, mirroring Doc 14's `_day_bounds_utc`.

### 14.2 Range parameters

| Param | Type | Meaning |
|---|---|---|
| `from` / `to` | ISO-8601 datetime | half-open `[from, to)`. Required unless `preset` is given. |
| `preset` | enum | `today · yesterday · last_7d · last_30d · this_month · last_month · this_quarter` — resolved server-side against the timezone. |
| `granularity` | enum | `hour · day · week · month` |
| `timezone` | IANA name | optional override |
| `compare` | enum | `previous_period · previous_year` — returns a second `series` set for delta display |

### 14.3 Guards

- Maximum span per granularity: `hour` ≤ 7 days, `day` ≤ 400 days, `week` ≤ 3 years, `month` ≤ 5
  years. Exceeding it is `400` with the limit stated — bounded work per request.
- `from` must precede `to`; both are clamped to the retention horizon (§21).
- A range extending past `now` is truncated silently — asking for tomorrow is not an error.

---

## 15. Permissions

Two new permissions, following the frozen catalog grammar. `analytics:read` **already exists** and
is already bundled to Owner/Admin/Manager/Analyst — no bundle is rewritten, only extended.

| Permission | Grants | Status |
|---|---|---|
| `analytics:read` | Operational dashboards & reports: messaging, conversations, tasks, customers, campaigns | **exists** |
| `analytics:export` | Start a report export and download the artifact | **new** |
| `analytics:executive` | Cost analytics, spend, and the executive dashboard | **new** |

**Role-bundle deltas** (additive only):

| Role | Added |
|---|---|
| Owner / Admin | `analytics:export`, `analytics:executive` |
| Manager | `analytics:export` |
| Analyst | `analytics:export` |
| Agent | *(unchanged — no analytics access)* |

`analytics:executive` gating cost is deliberate: spend is commercially sensitive and a support agent
or analyst has no operational need for it. The catalog's own comment anticipated this permission by
name.

**Enforcement.** Every endpoint declares `require_permissions(...)` exactly as `tasks.py` does.
Reads → `analytics:read`; cost and executive paths → `analytics:executive`; exports →
`analytics:export`. Record-level scoping ("only my own performance") is **not** introduced here —
that is Doc 13 GAP-07 (P2), platform-wide.

---

## 16. API architecture

All paths carry the frozen `/api/v1` prefix, return the standard envelopes (Doc 04 §3), and use RFC
7807 errors (§5). Public ids are UUID strings on the wire.

Three endpoint families, deliberately distinguished:

1. **`/analytics/summary/*`** — scalar KPI cards for a range. Cheap, cacheable.
2. **`/analytics/series/*`** — the §10 time-series envelope. Chart data.
3. **`/analytics/breakdown/*`** — grouped tables (per agent, per campaign, per error code). Sorted,
   limited, and the entry point to drill-down.

Live-state reads stay on their owning modules (`/tasks/stats`, `/conversations`) per AN-CD4 — the
analytics API never re-implements an operational list read.

**Caching.** `summary` and `series` responses carry `Cache-Control: private, max-age=60` and an
`ETag` derived from the max `watermark_at` of the contributing rollups: when nothing has been
rolled up, a conditional request is a `304`. Live endpoints are `no-store`.

---

## 17. Endpoint catalogue

| Method | Path | Permission | Purpose |
|---|---|---|---|
| GET | `/api/v1/analytics/summary` | `analytics:read` | Headline KPIs for a range → `AnalyticsSummaryResponse` |
| GET | `/api/v1/analytics/series` | `analytics:read` | Generic series by `metric[]` → `AnalyticsSeriesResponse` |
| GET | `/api/v1/analytics/messages` | `analytics:read` | Delivery/read/failure summary + series (J1) |
| GET | `/api/v1/analytics/failures` | `analytics:read` | Grouped by error code + guidance (J7) |
| GET | `/api/v1/analytics/conversations` | `analytics:read` | Inbox metrics (J1, J6) |
| GET | `/api/v1/analytics/tasks` | `analytics:read` | Follow-up metrics (Doc 14 §12) |
| GET | `/api/v1/analytics/customers` | `analytics:read` | Growth, opt-in health (FR-AN-08) |
| GET | `/api/v1/analytics/campaigns` | `analytics:read` | Campaign table + series (J2) |
| GET | `/api/v1/analytics/campaigns/{campaign_id}` | `analytics:read` | One campaign's funnel & trend (drill-down) |
| GET | `/api/v1/analytics/agents` | `analytics:read` | Agent performance table (J6) |
| GET | `/api/v1/analytics/costs` | `analytics:executive` | Spend breakdown (J3) |
| GET | `/api/v1/analytics/executive` | `analytics:executive` | Executive dashboard composite (§12) |
| POST | `/api/v1/analytics/reports/export` | `analytics:export` | Start a report export → `202` `ExportProgressResponse` |
| GET | `/api/v1/analytics/reports/{export_id}` | `analytics:export` | Poll export progress (reuses the export envelope) |
| GET | `/api/v1/analytics/freshness` | `analytics:read` | Rollup watermarks per kind → honest "data as of" |

Fifteen endpoints. `/freshness` exists because a dashboard that silently shows 20-minute-old numbers
as if they were live is a correctness problem, not a cosmetic one (§22).

---

## 18. OpenAPI considerations

Generated from FastAPI, as always. Two lessons from the Phase 7 hardening milestone are binding
here:

1. **Every query parameter must be declared as a FastAPI parameter.** The inbox endpoints read
   filters off the raw `Request`, which made them invisible to the contract and forced a frontend
   workaround. Analytics has a *large* filter surface (§14). Every one is a declared `Query`
   parameter with an enum or scalar type — no raw `request.query_params` access anywhere in this
   module.
2. **Enums render as OpenAPI enums** via `Literal`, kept in lockstep with the model constants and
   asserted equal by a test (as `schemas/task.py` does).

**New component schemas:** `AnalyticsSummaryResponse`, `AnalyticsSeriesResponse`, `SeriesPoint`,
`Series`, `AnalyticsBreakdownResponse`, `BreakdownRow`, `MessageAnalyticsResponse`,
`FailureAnalyticsResponse`, `FailureRow`, `ConversationAnalyticsResponse`, `TaskAnalyticsResponse`,
`CustomerAnalyticsResponse`, `CampaignAnalyticsResponse`, `CampaignAnalyticsRow`,
`AgentPerformanceResponse`, `AgentPerformanceRow`, `CostAnalyticsResponse`, `CostRow`,
`ExecutiveDashboardResponse`, `AnalyticsFreshnessResponse`, `ReportExportRequest`.

`ExportProgressResponse` and `Page` are **reused unchanged**. No existing schema is modified.

Regeneration runs through `backend/scripts/export_openapi.py`, and `--check` must pass in CI.

---

## 19. Export architecture (J8)

**Decision AN-CD5 — reuse the export pipeline wholesale.** The platform already has an async export
system: the `exports` table (`ExportJob`), the `exports` queue, `ExportService`, storage-key
artifacts with `expires_at`, and the `ExportProgressResponse` polling envelope (Doc 03 §11.6,
Doc 04 §14.1). A report export is an export.

What Phase 8 adds is **rows in that system, not a second system**:

- `exports.entity` gains values `report:messages`, `report:campaigns`, `report:agents`,
  `report:tasks`, `report:customers`, `report:costs`, `report:failures`. The column is already a
  free `VARCHAR(40)` defaulting to `contacts` — no schema change.
- `exports.filters_json` carries the resolved range, granularity, timezone and dimension filters, so
  an artifact is reproducible and self-describing.
- Formats `csv · xlsx · json` are already the table's CHECK constraint. Unchanged.
- The generator streams from the rollup tables (never from the ledger), so a year-long report is
  bounded work.
- Download reuses the existing artifact download path and expiry.

`POST /analytics/reports/export` therefore always returns `202` with an `ExportProgressResponse` —
the same contract `POST /contacts/export` already honours. Synchronous report downloads are
deliberately **not** offered: a large report is exactly the request that should not hold a worker.

**Scheduled/emailed reports are out of scope** — they need the Notification Center (Phase 10). The
seam is reserved: a future scheduler enqueues the same export task.

---

## 20. Database schema summary

One additive Alembic revision **`0027_analytics`** (successor to head `0026_tasks`), creating the
seven tables of §9 and inserting the two new permissions idempotently — following the
`0026_tasks` pattern exactly, including the code-existence guard so a fresh migrate does not
conflict with the dynamic catalog seed. Per the standing rule, bump
`tests/test_migrations.py` head assertion and `_EXPECTED_TABLES`.

Phase 8b adds **`0028_click_tracking`** (`short_links`, `link_clicks`) per Doc 03 §9.6.

No existing migration is edited; the chain stays linear.

---

## 21. Indexing, partitioning & retention

### 21.1 Indexing

Every fact table carries exactly two indexes:

- the **grain UNIQUE** — enforces one row per bucket per dimension combination and makes the
  delete-then-insert window (§6.3) an indexed range delete;
- the **read index** — `(organization_id, bucket_start[, primary_dimension])`, which serves every
  §17 endpoint as an indexed range scan.

No speculative indexes. Rollup tables are read with a narrow, known query set; extra indexes would
only slow the writer.

### 21.2 Partitioning

**Rollup tables are not partitioned.** At hourly grain a busy organization produces on the order of
10⁴–10⁵ rows per table per year — small enough that partitioning would add operational cost
(partition maintenance, the FK prohibition of Doc 03 §1.8) for no benefit. Because they are not
partitioned they **keep real foreign keys** to `organizations`, matching `tasks` and
`internal_notes`.

The **sources** stay partitioned as already designed (`messages`, `message_status_history`,
`campaign_recipients`, `contact_events`, `link_clicks`). Analytics reads them by time range, which
is exactly what their partitioning optimizes — the rollup job is partition-pruning-friendly by
construction.

### 21.3 Retention

| Data | Retention | Mechanism |
|---|---|---|
| Hourly rollups | **90 days** | `analytics.rollup_prune`, indexed range delete |
| Daily-and-coarser reads | **26 months** | served by monthly consolidation rows (§21.4) |
| `analytics_rollup_runs` | permanent (one row per org × kind) | — |
| Export artifacts | existing `exports.expires_at` policy | unchanged |
| Source tables | unchanged (Doc 03 per-table policy) | unchanged |

### 21.4 Consolidation

Keeping hourly rows for two years is wasteful; discarding them makes long ranges impossible. So the
nightly job also writes **daily consolidation rows** (`bucket_start` at midnight UTC, same tables,
distinguished by a `grain` column `hour|day`). Hourly rows are pruned at 90 days; daily rows live
26 months. The query planner in `AnalyticsQueryService` picks the coarsest grain that satisfies the
requested granularity — transparent to the caller.

---

## 22. Performance targets

| Operation | Target | Basis |
|---|---|---|
| `GET /analytics/summary` (30 days) | **p95 < 250 ms** | ~720 hourly rows scanned via the read index |
| `GET /analytics/series` (90 days, day grain) | **p95 < 400 ms** | ~90 consolidated rows per series |
| `GET /analytics/agents` (30 days) | **p95 < 300 ms** | grouped scan + small user join |
| `GET /analytics/freshness` | **p95 < 50 ms** | single indexed row per kind |
| Incremental rollup (6 h window, 1 org) | **< 30 s** | well inside the 120 s soft timeout |
| Nightly consolidation (48 h) | **< 120 s** | inside soft timeout; parks if exceeded |
| Report export (1 year, CSV) | **< 5 min** | inside the `exports` queue 300 s soft / 600 s hard |

**Freshness is part of the contract.** Every summary and series response carries
`data_as_of` (the contributing watermark). The UI displays it. A dashboard that cannot say how
stale it is will eventually be trusted when it should not be.

---

## 23. Failure recovery & monitoring

### 23.1 Recovery

| Failure | Behaviour |
|---|---|
| Rollup task raises | Celery retries (3×, per the queue spec), then **parks**. `last_status='failed'`, `last_error` recorded. Serving continues from existing rollups. |
| Rollup lags / stops | The watermark stops advancing; `/analytics/freshness` and the UI show stale `data_as_of`. No silent wrong numbers. |
| Corrupt or doubted rollup | `analytics.rollup_backfill` over the range. Delete-then-insert makes it idempotent; no cleanup step needed. |
| Total rollup loss | Backfill from source over the retention horizon. Rollups are derived (§4.1) — this is slow, not lossy. |
| Source backfill (webhook backlog drained) | The trailing window and nightly 48 h pass absorb it automatically; older than that needs an explicit backfill. |

### 23.2 Monitoring

Reuses `monitoring_metrics` (Doc 03 §11.7) and the existing Queue Monitor — no new monitoring
system:

| Signal | Alert |
|---|---|
| `analytics.rollup.lag_seconds` (now − watermark) | warn > 1 h, critical > 6 h |
| `analytics.rollup.duration_ms` | warn > 60 s |
| `analytics.rollup.failed_runs` | any parked run |
| `analytics.query.latency_ms` per endpoint | breach of §22 |
| `analytics.export.failed` | any failed report export |

---

## 24. Future extensibility

Reserved seams, none implemented here:

- **New metric** — add measures to an existing fact table plus a KPI row in §11; no new table, no
  API shape change (`series?metric=` is already a list).
- **New dimension** — add a column and extend the grain UNIQUE; the delete-then-insert window
  handles the transition, and a backfill repopulates.
- **Funnels / attribution (J9)** — a new fact table beside these; the query service gains a family,
  the envelope is unchanged.
- **AI insight narration (Doc 09)** — Phase 9 reads these endpoints; it needs no new storage.
- **Scheduled report delivery** — Phase 10 Notification Center enqueues the §19 export task.
- **Warehouse / OLAP export** — if volume ever outgrows MySQL rollups, the rollup tables are already
  the extract boundary: a CDC or nightly dump feeds an external engine without touching the API.
- **Real-time streaming** — AN-CD4's live-state split means a future socket transport upgrades the
  live panels only; trend panels stay on rollups.

---

## 25. Open questions for the owner

| # | Question | Recommendation |
|---|---|---|
| **Q1** | Should `analytics:executive` (cost/spend) be withheld from the Analyst role? | **Yes** — as specified. Analysts get operational analytics; spend stays with Owner/Admin. Reversible via role editing (FR-AUTH-08). |
| **Q2** | Is 90-day hourly / 26-month daily retention right? | Reasonable default. Longer hourly retention is a storage decision, not a design change. |
| **Q3** | "Active customers" is de-duplicated per hour, so summing a month counts a customer once per active hour — not unique customers. True unique-count needs either HyperLogLog sketches or a live `COUNT(DISTINCT)` over the ledger. | Ship the additive metric labelled **"active customer-hours"**, plus a live `COUNT(DISTINCT)` for the current month only. Avoids a misleading number; defers sketch complexity. |
| **Q4** | Should Phase 8b (click tracking) ship with Phase 8 or later? | **Later.** It modifies `SendService` — a frozen, high-risk path — and the core analytics milestone is read-only. Separate approval. |
| **Q5** | Is a 15-minute rollup cadence acceptable for J5 "real-time"? | Yes, given AN-CD4: live counters are live, trends are 15 min stale, and the UI states `data_as_of` explicitly. |

---

## 26. Implementation plan (Phase 8, after approval)

Ordered so each step builds and tests green before the next. Backend-first, so OpenAPI exists before
any frontend line. Each block is independently committable.

| # | Step | Files (new unless noted) | Verify |
|---|---|---|---|
| A1 | **Models** | `models/analytics.py` (6 facts + runs); register in `models/__init__.py` | import + unit |
| A2 | **Migration** | `alembic/versions/0027_analytics.py`; bump `tests/test_migrations.py` | `pytest tests/test_migrations.py` |
| A3 | **Permissions** | 2 perms + role bundles in `rbac/catalog.py` | rbac tests |
| A4 | **Rollup service** | `services/analytics_rollup_service.py` (delete-then-insert, watermarks) | service unit, idempotency |
| A5 | **Queue tasks** | `analytics/tasks.py` on `analytics.rollup`; beat entries via `scheduler.tick` | task unit |
| A6 | **Query service** | `services/analytics_query_service.py` (grain planner, ranges, ratios) | service unit, boundary math |
| A7 | **Schemas** | `schemas/analytics.py` (§18 components) | schema unit |
| A8 | **Endpoints** | `api/v1/endpoints/analytics.py`; register in router | API integration tests |
| A9 | **Report exports** | extend `ExportService` with report entities | export tests |
| A10 | **Regenerate OpenAPI + types** | `scripts/export_openapi.py`; `npm run gen:api` | `--check`, `tsc --noEmit` |
| A11 | **Frontend** | `features/analytics/*`, `pages/AnalyticsPage.tsx`, `/analytics` route + nav | component tests |
| A12 | **Full verify** | — | `ruff` · `pytest` · `tsc` · `eslint` · `vitest` · `vite build` |
| B1 | **Phase 8b** (separate approval) | `0028_click_tracking`, redirect endpoint, `SendService` link rewriting | full suite |

**Test matrix:** rollup idempotency (run twice → identical rows); late-arriving data absorbed by the
trailing window; additivity (hourly sums equal the daily consolidation); timezone boundary math
across local midnight and a DST transition; range/granularity guards; permission gates
(read/export/executive); dense-bucket output; export envelope; freshness watermark reporting.

**Chart library note.** The frontend has **no chart dependency today** (`package.json` carries none)
and Doc 05 does not mandate one. A1–A10 add no frontend dependency. A11 must either add one
lightweight charting library or render SVG directly — an owner decision at A11 time, not a
prerequisite for the backend.

---

## 27. Self-review record

- **Additive-only verified.** New: 7 tables, 2 permissions, 15 endpoints, 1 frontend feature.
  **Edited frozen artifacts: none.** No Doc 01–14 change; no existing table, endpoint or schema
  altered. ✔
- **Reuse maximized** — `analytics.rollup` queue was already declared with the right spec; exports
  reuse `ExportJob`/`ExportService`/`exports` queue; click-tracking tables reuse Doc 03 §9.6; cost
  reuses the Phase 6 S5 engine; dimensions reuse operational tables (AN-CD2); no new queue, no new
  export system, no new monitoring system. ✔
- **No second source of truth** — rollups are derived and rebuildable; cost is copied, never
  recomputed; the event stream is the existing append-only logs (AN-CD1). ✔
- **Correctness by construction** — additive-only measures (§6.2), delete-then-insert idempotency
  (§6.3), dense buckets, ratios computed at read time, freshness surfaced in every response. ✔
- **Phase 7 lesson applied** — every query parameter is a declared FastAPI parameter (§18), so the
  contract cannot go blind again. ✔
- **Scope discipline** — J9 deferred per Doc 02; J4 separated because it touches `SendService`; AI,
  notifications and scheduled delivery left to their own phases with seams reserved. ✔

---

*End of Document 15 — Analytics & Reporting Architecture. Additive addendum to the frozen
architecture; **awaiting owner approval before Phase 8 implementation**. No backend, OpenAPI,
frontend, or Doc 01–14 change has been made — this document is specification only.*
