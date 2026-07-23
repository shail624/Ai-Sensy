# Task & Activity Management — Architecture Addendum
### Self-Hosted WhatsApp Business Platform — CRM Follow-up Engine

| | |
|---|---|
| **Document** | 14 — Task & Activity Management (addendum to Docs 01–12) |
| **Version** | 1.0 — **DRAFT FOR OWNER APPROVAL** (freezes on approval, per Doc 12 governance) |
| **Date** | 2026-07-22 |
| **Status** | 🟡 Proposed — Phase A (architecture) only. **No code is written until this is approved.** |
| **Implements** | Doc 13 §4 **GAP-01** (P0 — Task & Activity Management + agent work queue) |
| **Extends (does not edit)** | Doc 03 (DB), Doc 04 (API), Doc 05 (UI/UX), Doc 07 (Lead/CRM), Doc 12 (RBAC) |
| **Verified against** | `backend/app/db/{mixins,types,base}.py` · `models/{internal_note,quick_reply,contact_event,lead}.py` · `rbac/catalog.py` · `api/pagination.py` · `schemas/*` · `frontend/openapi.json` (103 paths) · migration head `0023` |
| **Governance** | **Purely additive.** New tables, endpoints, permissions, and one new frontend feature. **Zero** modifications to any frozen table, endpoint, schema, or Doc 01–12. |

> **Purpose.** Doc 13 identified a first-class **Task & Activity system with a per-agent work
> queue** as the single P0 CRM gap. This addendum specifies that capability completely —
> domain model, database, API contract, OpenAPI additions, permissions, and every integration
> point (Timeline, Customer Profile, Reporting, and *reserved* future Notifications) — so that
> **Phase B implementation is mechanical**: build to this document, regenerate types from the
> updated OpenAPI, and verify. This is **not a to-do list**; it is a CRM **follow-up engine**
> that guarantees *no lead is ever left without a next action*.

---

## 1. Traceability & requirement IDs

This addendum introduces the `FR-TASK-*` requirement family, traceable to Doc 13 GAP-01 and to
the Phase-5 build brief.

| ID | Requirement |
|---|---|
| **FR-TASK-01** | A task is a typed, assignable, scheduled follow-up action anchored to a **contact**, optionally linked to a **conversation/lead**. |
| **FR-TASK-02** | Task **types**: Call · WhatsApp · Collect Documents · Verification · Reminder · Meeting · Custom. |
| **FR-TASK-03** | Task **status**: Open · Completed · Skipped · Cancelled (with reopen). |
| **FR-TASK-04** | Task **priority**: Low · Medium · High · Critical. |
| **FR-TASK-05** | Scheduling: **due date** (+ optional **due time**) and an optional **reminder time**. |
| **FR-TASK-06** | Assignment: an **assigned agent** (owner) and a recorded **creator** ("assigned by"). |
| **FR-TASK-07** | Completion captures **completion notes** and may optionally emit a timeline note. |
| **FR-TASK-08** | Immutable **task history** records created/assigned/rescheduled/completed/cancelled/… . |
| **FR-TASK-09** | Every task lifecycle event appears on the **contact activity timeline** (reused). |
| **FR-TASK-10** | **Task List** views: Today · Overdue · Upcoming · Completed · Assigned to me · Assigned by me, with search, filters, sorting, bulk actions. |
| **FR-TASK-11** | **My Work Queue** reusable dashboard widget: Overdue · Due Today · Upcoming · Completed Today, each task actionable (open customer/conversation, complete, reschedule, add note). |
| **FR-TASK-12** | **Customer Profile** integration: open/completed tasks, task timeline, inline create, quick-complete. |
| **FR-TASK-13** | **Reporting** surface: task counts/rates feeding the analytics module (Phase 8) and future goals (Doc 13 GAP-06). |
| **FR-TASK-14** | **Reserved** (not built here): reminder/overdue events feed the future Notification Center and WhatsApp/email reminders. |

---

## 2. Scope of this addendum

**In scope (Phase A — this document):** the complete design for Task & Activity Management.

**In scope for Phase B (after approval, separate milestone):** backend tables + service +
endpoints, OpenAPI regeneration, generated-type regeneration, the frontend feature, and the
verify gates (TypeScript · ESLint · Tests · Build).

**Explicitly NOT built (per Phase-5 "DO NOT BUILD"):** calendar UI, Notification Center
*implementation*, AI, automation rules, email, WhatsApp reminders, and browser notifications.
Where this design *touches* those (§14, §15) it only **reserves the seams** (event names,
nullable fields) so they attach later additively — it implements none of them.

**Decoupling contract (resolves the Phase-5 fork).** The frontend consumes **only** generated
types from the updated OpenAPI (`npm run gen:api`). No hand-written API types, no temporary
frontend-only models. OpenAPI remains the single source of truth, generated from the FastAPI
backend in Phase B.

---

## 3. Design principles & reuse map

The follow-up engine is built almost entirely from primitives that already exist. Nothing below
is re-invented.

| Concern | Reused frozen primitive | New? |
|---|---|---|
| Identity (BIGINT PK + UUIDv7 public id) | `IntPKMixin`, `UUIDMixin` (`db/mixins.py`) | reuse |
| Timestamps / soft-delete / audit / concurrency | `TimestampMixin`, `SoftDeleteMixin`, `AuditMixin`, `VersionMixin` | reuse |
| Cross-dialect types | `big_id()`, `datetime6()`, `MYSQL_TABLE_ARGS` (`db/types.py`) | reuse |
| Index/constraint naming | `NAMING_CONVENTION` (`db/base.py`) | reuse |
| **Activity timeline** | `contact_events` (Doc 03 §6.5) — `ref_type`/`ref_id`/`payload_json` | reuse (new event-type strings only) |
| Cursor pagination | `Page`, `encode_cursor`/`decode_cursor` (`api/pagination.py`) | reuse |
| Error envelope | RFC 7807 problem+json (Doc 04 §5) | reuse |
| Permissions | `resource:action` catalog + `require_permissions()` (`rbac/`) | reuse (3 new perms) |
| Response mapping | Pydantic `XxxResponse.of(view)` (`schemas/*`) | reuse pattern |
| Bulk result | `schemas/bulk.py` result envelope (as used by `/contacts/bulk-*`) | reuse |
| Lead / conversation context | `conversation_lead` (Doc 07 §19.2) — owner, stage, dates | reference (unchanged) |
| Page shell + header | `PageContainer`, `PageHeader` (`components/layout`) | reuse |
| Timeline UI | `TimelineSection` (`features/customer-profile/sections`) | reuse |
| Section/empty/error/spinner/chip | `components/ui/*` | reuse |
| Data fetching | TanStack Query + `openapi-fetch` client (`lib/api`) | reuse |

**Two new tables. Three new permissions. One new frontend feature. Zero frozen edits.**

---

## 4. Domain model

### 4.1 Entities

- **Task** — one typed, scheduled, assignable follow-up action. Anchored to a **Contact**
  (required) and optionally to a **Conversation** (which carries lead/pipeline context via the
  frozen `conversation_lead`). Owned by an **assigned agent**; created by a user (the "assigned
  by"). Carries scheduling (`due_at` + optional time, `reminder_at`), a `status`, a `priority`,
  a `task_type`, an optional `description`, and — on completion — `completion_notes`.
- **TaskEvent** — one immutable entry in a task's **history** (created, assigned, reassigned,
  rescheduled, priority changed, completed, skipped, cancelled, reopened, note added). Append-only.

> **Why no separate `activities` table?** The platform already owns an append-only **activity
> timeline** (`contact_events`, Doc 03 §6.5) and per-conversation **internal notes**. The
> "Activity log" of FR-TASK-09 is realized as **(a)** per-task history in `task_events` plus
> **(b)** contact-level activity rows in `contact_events` (`ref_type="task"`). Adding a third
> parallel log would duplicate frozen infrastructure and violate the reuse mandate. **Decision
> TA-CD1: reuse `contact_events`; do not create an `activities` table.**

### 4.2 Value objects (enumerations)

Stored as `VARCHAR` with canonical string constants + `CHECK` constraints — matching the frozen
convention (`contact_event.EVENT_*`, `lead.DEFAULT_STAGES`), not native DB enums.

| Enum | Values (wire form) |
|---|---|
| `task_type` | `call` · `whatsapp` · `collect_documents` · `verification` · `reminder` · `meeting` · `custom` |
| `status` | `open` · `completed` · `skipped` · `cancelled` |
| `priority` | `low` · `medium` · `high` · `critical` |

### 4.3 Relationships

```
Contact 1 ──── * Task            (Task.contact_id, required — the customer the task is about)
Conversation 1 ── * Task         (Task.conversation_id, optional — links to the lead thread)
User (agent) 1 ── * Task         (Task.assigned_agent_id, required — the owner/doer)
User (creator) 1 ─ * Task        (Task.created_by, required — "assigned by")
Task 1 ──── * TaskEvent          (history, append-only, cascade)
Task 1 ──── * ContactEvent       (timeline projection, ref_type="task")
```

A "lead" in this platform is a **conversation with lead context** (`conversation_lead`, Doc 07
§19.2). A task therefore links to a lead **through `conversation_id`**; the frozen
`conversation_lead` table is **not modified**. Its single `reminder_at`/`follow_up_date` fields
remain a per-conversation summary; the Task engine is the richer, multi-task system layered
beside them.

### 4.4 State machine (status)

```
                 complete            reopen
   ┌──────────┐ ───────────▶ ┌───────────┐ ─────────┐
   │   open   │              │ completed │          │
   │ (active) │ ◀─────────── └───────────┘ ◀────────┘
   └──────────┘   reopen
      │  │  skip / cancel
      │  └───────────────▶ ┌───────────┐  reopen
      │                     │  skipped  │ ─────────▶ open
      │                     └───────────┘
      └────────────────────▶ ┌───────────┐  reopen
                              │ cancelled │ ─────────▶ open
                              └───────────┘
```

**Invariants (TA-INV):**

1. A newly created task is `open`.
2. `completed` sets `completed_at` + `completed_by`; `completion_notes` optional.
3. `skipped`/`cancelled` are business outcomes and remain **fully auditable** (kept, not deleted).
4. `reopen` returns any terminal state to `open` and clears completion fields (logged).
5. **Soft-delete ≠ cancel.** `deleted_at` is data cleanup (mistake/erasure); `cancelled` is a
   deliberate business decision that stays in reporting. Deleted tasks are excluded from all reads.
6. Every state transition writes a `TaskEvent` **and** (for create/assign/reschedule/complete/
   cancel) a `contact_events` row. History is the source of truth for "what happened."
7. Optimistic concurrency via `row_version` guards concurrent reschedule/reassign (409 on conflict).

### 4.5 Services (Phase B)

`TaskService` (mirrors `QuickReplyService`/`CampaignService` layering: repository → service →
API): `create`, `get`, `list` (filtered, cursor), `update`, `complete`, `skip`, `cancel`,
`reopen`, `reschedule`, `reassign`, `bulk_update`, `bulk_delete`, `history`, `stats`. Each
mutating method emits the `TaskEvent` + `ContactEvent` projection in the same transaction
(persist-first, consistent with the frozen webhook/ledger discipline).

---

## 5. Database design (additive — Doc 03 conventions)

Two new InnoDB/utf8mb4 tables. Both use the frozen mixins and cross-dialect types verbatim, so a
single model renders Doc-03-exact types on MySQL 8 and portable equivalents on SQLite (Doc 10 test suite).

### 5.1 `tasks`

| Column | Type (MySQL) | Null | Notes |
|---|---|---|---|
| `id` | BIGINT UNSIGNED PK AI | No | `IntPKMixin` |
| `uuid` | BINARY(16) | No | `UUIDMixin` (UUIDv7 public id) |
| `organization_id` | BIGINT UNSIGNED | No | FK `fk_tasks_organization_id` → `organizations.id` ON DELETE CASCADE |
| `contact_id` | BIGINT UNSIGNED | No | FK `fk_tasks_contact_id` → `contacts.id` ON DELETE RESTRICT (subject must stay attributable) |
| `conversation_id` | BIGINT UNSIGNED | Yes | FK `fk_tasks_conversation_id` → `conversations.id` ON DELETE SET NULL (optional lead link) |
| `assigned_agent_id` | BIGINT UNSIGNED | No | FK `fk_tasks_assigned_agent_id` → `users.id` ON DELETE RESTRICT (owner) |
| `title` | VARCHAR(160) | No | Subject line |
| `description` | TEXT | Yes | Optional detail (≤4096 enforced in schema) |
| `task_type` | VARCHAR(24) | No | CHECK `ck_tasks_task_type` ∈ enum §4.2 |
| `status` | VARCHAR(16) | No | default `open`; CHECK `ck_tasks_status` |
| `priority` | VARCHAR(12) | No | default `medium`; CHECK `ck_tasks_priority` |
| `due_at` | DATETIME(6) | No | Effective due moment (UTC). Drives buckets. |
| `has_time` | BOOLEAN | No | default `true`; `false` = date-only ("Due Date" with no "Due Time" → all-day in UI) |
| `reminder_at` | DATETIME(6) | Yes | Optional reminder moment (feeds future Notifications, §15) |
| `completion_notes` | TEXT | Yes | Set on complete (≤4096) |
| `completed_at` | DATETIME(6) | Yes | Set on complete |
| `completed_by` | BIGINT UNSIGNED | Yes | User who completed (no FK, mirrors `quick_replies.created_by`) |
| `created_by` | BIGINT UNSIGNED | No | `AuditMixin` — the "assigned by" creator |
| `updated_by` | BIGINT UNSIGNED | Yes | `AuditMixin` |
| `row_version` | INT UNSIGNED | No | `VersionMixin` — optimistic concurrency |
| `created_at` / `updated_at` | DATETIME(6) | No | `TimestampMixin` |
| `deleted_at` | DATETIME(6) | Yes | `SoftDeleteMixin` (NULL = active) |

**Indexes** (naming per `NAMING_CONVENTION`):

| Index | Columns | Serves |
|---|---|---|
| `ix_tasks_organization_id_assigned_agent_id_status_due_at` | (organization_id, assigned_agent_id, status, due_at) | **Work-queue** buckets per agent (FR-TASK-11) |
| `ix_tasks_organization_id_status_due_at` | (organization_id, status, due_at) | Team-wide Today/Overdue/Upcoming |
| `ix_tasks_organization_id_contact_id_created_at` | (organization_id, contact_id, created_at) | Customer Profile tasks (FR-TASK-12) |
| `ix_tasks_organization_id_conversation_id` | (organization_id, conversation_id) | Conversation/lead tasks |
| `ix_tasks_organization_id_created_by_status` | (organization_id, created_by, status) | "Assigned by me" (FR-TASK-10) |

**Retention/scale.** Moderate volume (bounded by agents × open follow-ups); **not** partitioned
(unlike `contact_events`). Standard soft-delete + Doc 03 retention policy applies. FKs are safe
here (partitioned tables carry no FKs — this one is not partitioned, so it keeps them, matching
`internal_notes`/`quick_replies`).

### 5.2 `task_events` (immutable task history — FR-TASK-08)

| Column | Type (MySQL) | Null | Notes |
|---|---|---|---|
| `id` | BIGINT UNSIGNED PK AI | No | `IntPKMixin` |
| `organization_id` | BIGINT UNSIGNED | No | scope + retention |
| `task_id` | BIGINT UNSIGNED | No | FK `fk_task_events_task_id` → `tasks.id` ON DELETE CASCADE |
| `event_type` | VARCHAR(32) | No | `created·assigned·reassigned·rescheduled·priority_changed·status_changed·completed·skipped·cancelled·reopened·note_added` |
| `actor_user_id` | BIGINT UNSIGNED | Yes | who acted (system events may be null) |
| `from_json` | JSON | Yes | prior value(s) for the changed field(s) |
| `to_json` | JSON | Yes | new value(s) |
| `note` | TEXT | Yes | free-text (e.g., completion/skip reason) |
| `created_at` | DATETIME(6) | No | `default utcnow` (append-only; no `updated_at`, no soft-delete) |

**Index:** `ix_task_events_task_id_created_at` (task_id, created_at) — the history read, oldest→newest.

### 5.3 Timeline projection — new `contact_events` event-type constants (no schema change)

Additive **string constants only** (added to `models/contact_event.py`), reusing the frozen
partitioned table with `ref_type="task"`, `ref_id=task.id`, and a compact `payload_json`
(`{title, task_type, priority, due_at, status}`):

```
EVENT_TASK_CREATED     = "task_created"
EVENT_TASK_ASSIGNED    = "task_assigned"
EVENT_TASK_RESCHEDULED = "task_rescheduled"
EVENT_TASK_COMPLETED   = "task_completed"
EVENT_TASK_CANCELLED   = "task_cancelled"
```

No column, index, or DDL change to `contact_events` — only new canonical values in the existing
`event_type VARCHAR(40)`. This is the entire "Timeline integration" (FR-TASK-09).

### 5.4 Migration plan (Phase B)

One additive Alembic revision **`0024_tasks`** (successor to head `0023_internal_notes`):
creates `tasks` + `task_events`, seeds the three new permissions (§6). Per the tracker's
standing rule, bump `tests/test_migrations.py` head assertion and `_EXPECTED_TABLES`. No
existing migration is edited; the chain stays linear.

---

## 6. Permissions (RBAC — additive to `rbac/catalog.py`)

Three new `resource:action` permissions, following the frozen catalog grammar (read/write +
elevated action, exactly as `inbox:read`/`inbox:write`/`inbox:assign`).

| Permission | Grants |
|---|---|
| `tasks:read` | View tasks, work queue, history, and stats |
| `tasks:write` | Create/edit tasks; complete/skip/cancel/reopen/reschedule (incl. one's own) |
| `tasks:assign` | Assign or reassign a task to **another** agent; bulk reassign (elevated) |

**Role-bundle deltas** (Doc 12 seed roles; additive):

| Role | Added permissions |
|---|---|
| Owner / Admin | `tasks:read`, `tasks:write`, `tasks:assign` |
| Manager | `tasks:read`, `tasks:write`, `tasks:assign` |
| Agent | `tasks:read`, `tasks:write` (own queue; reassignment stays with managers) |
| Analyst (read-only) | `tasks:read` |

**Enforcement.** Every endpoint declares `require_permissions(...)` exactly like
`quick_replies.py`. Reads → `tasks:read`; mutations → `tasks:write`; `POST …/reassign` and bulk
reassignment → `tasks:assign`. Record-level "see only my tasks" scoping is **not** introduced
here (that is Doc 13 GAP-07, P2); this addendum ships **query-level** ownership filters
(`assignee_id`, `assigned_by_id`) which cover the FR-TASK-10 views without a new access model.

---

## 7. API contract (additive — Doc 04 conventions)

All paths carry the frozen `/api/v1` prefix, return the standard envelopes (Doc 04 §3), use
cursor pagination (§6), RFC 7807 errors (§5), and are fully OpenAPI-3.1 describable. Public ids
(`id`, `contact_id`, …) are UUID strings on the wire, per the frozen response convention.

### 7.1 Endpoint summary

| Method | Path | Permission | Purpose |
|---|---|---|---|
| GET | `/api/v1/tasks` | `tasks:read` | List tasks (filters, buckets, cursor) → `TasksPage` |
| POST | `/api/v1/tasks` | `tasks:write` | Create a task → `TaskResponse` (201) |
| GET | `/api/v1/tasks/{task_id}` | `tasks:read` | Read one task → `TaskResponse` |
| PATCH | `/api/v1/tasks/{task_id}` | `tasks:write` | Edit fields (title/desc/type/priority/due/reminder) → `TaskResponse` |
| DELETE | `/api/v1/tasks/{task_id}` | `tasks:write` | Soft-delete (cleanup, not cancel) → 204 |
| POST | `/api/v1/tasks/{task_id}/complete` | `tasks:write` | Complete (+notes, optional timeline note) → `TaskResponse` |
| POST | `/api/v1/tasks/{task_id}/skip` | `tasks:write` | Skip (+reason) → `TaskResponse` |
| POST | `/api/v1/tasks/{task_id}/cancel` | `tasks:write` | Cancel (+reason) → `TaskResponse` |
| POST | `/api/v1/tasks/{task_id}/reopen` | `tasks:write` | Reopen a terminal task → `TaskResponse` |
| POST | `/api/v1/tasks/{task_id}/reschedule` | `tasks:write` | New `due_at`/`reminder_at` → `TaskResponse` |
| POST | `/api/v1/tasks/{task_id}/reassign` | `tasks:assign` | Reassign to another agent → `TaskResponse` |
| GET | `/api/v1/tasks/{task_id}/history` | `tasks:read` | Immutable task history → `TaskHistoryResponse` |
| GET | `/api/v1/tasks/stats` | `tasks:read` | Work-queue counts (per assignee) → `TaskStatsResponse` |
| POST | `/api/v1/tasks/bulk-update` | `tasks:write` (`tasks:assign` if reassigning) | Bulk status/priority/due/assignee → `BulkSummary` |
| POST | `/api/v1/tasks/bulk-delete` | `tasks:write` | Bulk soft-delete → `BulkSummary` |

The action endpoints (`/complete`, `/skip`, …) mirror the frozen campaign action style
(`/campaigns/{id}/pause|resume|cancel`) so each business transition produces a clean, single
`TaskEvent` + timeline projection rather than an ambiguous PATCH.

### 7.2 List filter grammar — `GET /api/v1/tasks`

| Param | Type | Meaning |
|---|---|---|
| `view` | enum: `today·overdue·upcoming·completed·all` | Server-computed bucket (see §7.3). Default `all`. |
| `assignee_id` | uuid | Owner filter. `assignee_id=<me>` → **Assigned to me** (FR-TASK-10). |
| `assigned_by_id` | uuid | Creator filter. `assigned_by_id=<me>` → **Assigned by me**. |
| `contact_id` | uuid | Tasks for one customer (Customer Profile). |
| `conversation_id` | uuid | Tasks for one conversation/lead. |
| `status` | enum | `open·completed·skipped·cancelled` (repeatable). |
| `type` | enum | task type (repeatable). |
| `priority` | enum | priority (repeatable). |
| `due_from` / `due_to` | datetime | Due-window bounds. |
| `q` | string | Case-insensitive match on `title` (+ `description`). |
| `sort` | enum: `due_at·priority·created_at` (prefix `-` = desc) | Default `due_at` asc (soonest first). |
| `cursor` | string | Opaque keyset cursor (`api/pagination.py`). |
| `limit` | int (1–200, default 50) | Page size. |

### 7.3 Bucket semantics (server-computed, timezone-aware)

Relative to the caller's org timezone at request time:

- **Overdue** = `status=open` AND `due_at < start_of_today`.
- **Due Today** = `status=open` AND `due_at ∈ [start_of_today, end_of_today]`.
- **Upcoming** = `status=open` AND `due_at > end_of_today`.
- **Completed** (Today) = `status=completed` AND `completed_at ∈ today` (for the widget's
  "Completed Today"); the Task-List "Completed" view is all completed unless date-filtered.

### 7.4 Representative payloads

**Create** — `POST /api/v1/tasks`

```json
{
  "contact_id": "018f2a...",
  "conversation_id": "018f2b...",
  "title": "Collect Aadhaar + address proof",
  "task_type": "collect_documents",
  "priority": "high",
  "due_at": "2026-07-24T09:30:00Z",
  "has_time": true,
  "reminder_at": "2026-07-24T08:30:00Z",
  "description": "Customer promised to send by Thursday morning.",
  "assigned_agent_id": "018f2c..."
}
```

`assigned_agent_id` is optional; when omitted it defaults to the caller (self-assignment).

**Task** — `TaskResponse` (returned by create/read/action endpoints)

```json
{
  "id": "018f2d...",
  "contact_id": "018f2a...", "contact_name": "Ramesh K.",
  "conversation_id": "018f2b...",
  "title": "Collect Aadhaar + address proof",
  "task_type": "collect_documents", "status": "open", "priority": "high",
  "due_at": "2026-07-24T09:30:00Z", "has_time": true,
  "reminder_at": "2026-07-24T08:30:00Z",
  "description": "Customer promised to send by Thursday morning.",
  "assigned_agent_id": "018f2c...", "assigned_agent_name": "Priya S.",
  "created_by": "018f2e...", "created_by_name": "Priya S.",
  "completion_notes": null, "completed_at": null,
  "created_at": "2026-07-22T11:00:00Z", "updated_at": "2026-07-22T11:00:00Z",
  "row_version": 0
}
```

**Complete** — `POST /api/v1/tasks/{id}/complete`

```json
{ "completion_notes": "Documents received and verified.", "create_timeline_note": true }
```

**Stats** — `GET /api/v1/tasks/stats?assignee_id=<me>` → `TaskStatsResponse`

```json
{ "overdue": 3, "due_today": 7, "upcoming": 12, "completed_today": 5 }
```

**List** — `TasksPage` = `{ "data": [TaskResponse, …], "page": { "limit": 50, "has_more": true, "next_cursor": "…", "prev_cursor": null } }`

---

## 8. OpenAPI additions (generated in Phase B)

OpenAPI is **generated from the FastAPI backend**; Phase B adds the router + Pydantic schemas
and runs `npm run gen:api`. The resulting additive diff to `frontend/openapi.json` is exactly:

**New paths (15):** the fifteen rows of §7.1.

**New component schemas:**

| Schema | Shape |
|---|---|
| `TaskCreateRequest` | contact_id, conversation_id?, title, task_type, priority?, due_at, has_time?, reminder_at?, description?, assigned_agent_id? |
| `TaskUpdateRequest` | all optional: title, description, task_type, priority, due_at, has_time, reminder_at |
| `TaskCompleteRequest` | completion_notes?, create_timeline_note (bool, default false) |
| `TaskRescheduleRequest` | due_at, has_time?, reminder_at? |
| `TaskReassignRequest` | assigned_agent_id |
| `TaskReasonRequest` | reason? (shared by skip/cancel) |
| `TaskResponse` | full task (§7.4), ids as uuid strings, includes denormalized `*_name` display fields |
| `TasksPage` | `{ data: TaskResponse[], page: Page }` |
| `TaskEventResponse` | id, event_type, actor_user_id?, actor_name?, from, to, note, created_at |
| `TaskHistoryResponse` | `{ data: TaskEventResponse[] }` (bounded, oldest→newest) |
| `TaskStatsResponse` | overdue, due_today, upcoming, completed_today (ints) |
| `TaskBulkUpdateRequest` | task_ids[], set: { status?, priority?, due_at?, assigned_agent_id? } — task-specific settable fields (new) |

Enums (`task_type`, `status`, `priority`) render as OpenAPI `enum` strings. The bulk **request
addressing** (`task_ids[]`) and the **result envelope** reuse the frozen `schemas/bulk.py` —
`BulkDeleteRequest` (ids) for delete and `BulkSummary` (`processed`/`succeeded`/`failed`) for
both; only `TaskBulkUpdateRequest`'s settable `set` block is new. `Page` is likewise reused. No
existing schema is modified.

---

## 9. Customer Profile integration (FR-TASK-12)

The Customer Profile (`features/customer-profile/CustomerProfile.tsx`) is a stack of section
components. This adds **one** new section — `TasksSection` — beside the existing
`TimelineSection`, `NotesSection`, etc. **No existing section is modified.**

`TasksSection` shows, for the profiled contact:

- **Open Tasks** — sorted by `due_at`, each with an overdue/due-today badge and inline actions
  (**Quick Complete**, **Reschedule**, **Add Note**, **Open Conversation**).
- **Completed Tasks** — collapsed by default (most recent first).
- **Create Task** — an inline form (title, type, priority, due date/time, reminder, assignee)
  pre-bound to `contact_id`.
- **Task Timeline** — task lifecycle already flows into the existing `TimelineSection` via the
  `contact_events` projection (§5.3); no separate timeline UI is built.

Data via `GET /api/v1/tasks?contact_id=<id>&status=open` and `…&status=completed`. Mutations via
the action endpoints. Reuses `Section`, `EmptyState`, `ErrorState`, `Spinner`, `TagChip`,
`DefinitionRow`, and the query/client layer — no new primitives.

---

## 10. Task List module (FR-TASK-10)

A new route **`/tasks`** (page `TasksPage`, feature `features/tasks`) built from `PageContainer`
+ `PageHeader` + a shared `TaskTable`. Six views are **saved filter presets over the one list
endpoint** — not six code paths:

| View | Endpoint mapping |
|---|---|
| **Today** | `GET /tasks?view=today&assignee_id=<me>` |
| **Overdue** | `GET /tasks?view=overdue&assignee_id=<me>` |
| **Upcoming** | `GET /tasks?view=upcoming&assignee_id=<me>` |
| **Completed** | `GET /tasks?status=completed&sort=-completed_at` |
| **Assigned to me** | `GET /tasks?assignee_id=<me>` |
| **Assigned by me** | `GET /tasks?assigned_by_id=<me>` |

- **Search** → `q`. **Filters** → `status·type·priority·assignee·due_from/due_to`.
  **Sorting** → `sort` (due/priority/created). **Pagination** → cursor (`keepPreviousData`,
  as `useContactSearch` already does).
- **Bulk actions** → multi-select → `POST /tasks/bulk-update` (complete/skip/cancel/reprioritize/
  reschedule/reassign) or `/tasks/bulk-delete`, mirroring the Contacts bulk UX. Reassign in bulk
  requires `tasks:assign`.
- Nav: add `{ label: "Tasks", path: "/tasks", available: true, glyph: "Tk" }` to
  `components/layout/navigation.ts` (the single nav source shared by sidebar + dashboard).

The row component is shared with the widget (§11) so a task renders identically everywhere.

---

## 11. My Work Queue widget (FR-TASK-11)

A **reusable** component `features/tasks/MyWorkQueue.tsx`, embeddable on the Dashboard and any
future surface. Four sections, each backed by the list endpoint filtered to the current agent:

| Section | Source |
|---|---|
| **Overdue** | `view=overdue&assignee_id=<me>` |
| **Due Today** | `view=today&assignee_id=<me>` |
| **Upcoming** | `view=upcoming&assignee_id=<me>` (next N) |
| **Completed Today** | `status=completed&assignee_id=<me>` (completed_at = today) |

Section counts come from `GET /tasks/stats` (one cheap call) so the header badges render before
the lists resolve. **Each task row supports:** **Open Customer** (→ `/contacts/{id}`), **Open
Conversation** (→ inbox, when `conversation_id` present), **Mark Complete**, **Reschedule**,
**Add Note**. Actions are optimistic (TanStack Query mutation + invalidate), matching the app's
optimistic-UI standard (Doc 05 O5). The widget mounts on `DashboardPage.tsx` **additively**
(the dashboard shell already exists).

---

## 12. Reporting integration (FR-TASK-13)

Task data is a first-class analytics source (Doc 02 §J, Phase 8) and the substrate for the
future Goals capability (Doc 13 GAP-06). This addendum:

- Ships **`GET /tasks/stats`** now (operational counts for the widget/dashboard).
- **Reserves** the reporting metrics the Phase-8 analytics module will compute from `tasks` +
  `task_events`: tasks **created/completed/overdue** per period; **completion rate**; **on-time
  completion %** (`completed_at ≤ due_at`); **average time-to-complete**; **throughput per
  agent**; breakdowns by **type/priority/stage**. These are **defined here, computed in Phase 8**
  — no analytics code is written in the Task milestone.
- Because history is immutable (`task_events`), these metrics are reconstructable and auditable
  after the fact.

---

## 13. Future Notification integration (FR-TASK-14 — RESERVED, NOT BUILT)

Per the Phase-5 "DO NOT BUILD" list, **no** notification, email, WhatsApp reminder, or browser
notification is implemented. The design only **reserves the seam**:

- `reminder_at` and the `due`/`overdue` bucket transitions are the future trigger points.
- The Notification Center (Doc 05 F7, Phase 10) and any future WhatsApp/email reminder worker
  will **subscribe** to the already-emitted task domain events (`task_created`, `task_assigned`,
  `task_rescheduled`, plus a future `task_due`/`task_overdue` sweep) — an additive consumer, no
  change to the Task tables.

This guarantees the later Notification work attaches without reopening this design.

---

## 14. Non-functional requirements

- **Performance.** The composite work-queue index (§5.1) makes every bucket an indexed range
  scan; stats is a small set of `COUNT`s over the same index. Lists are cursor-paginated and the
  UI virtualizes (Doc 05 O6).
- **Concurrency.** `row_version` (optimistic) prevents lost updates when two agents act on one
  task; conflict → `409` (Doc 04 §5), surfaced as a ret/refresh prompt.
- **Consistency.** Task mutation + `TaskEvent` + `ContactEvent` projection commit in one
  transaction (persist-first invariant).
- **Security.** Every route permission-gated (§6); all writes audited via `task_events` +
  the platform audit log; org-scoped queries only.
- **Testability.** Renders Doc-03 types on MySQL and SQLite (hermetic tests, Doc 10). Service,
  API, and frontend are independently unit-testable (frontend tests mock the generated client,
  as `ContactsTable.test.tsx` does).
- **Accessibility & theme.** Reuses the design system → dark mode + WCAG AA inherited.

---

## 15. Frontend architecture

New feature folder `features/tasks/`, structured exactly like `features/contacts/`:

```
src/features/tasks/
  types.ts          // aliases from generated schema — components["schemas"]["TaskResponse"] etc. (NEVER hand-written)
  api.ts            // TanStack Query hooks over the openapi-fetch client (useTasks, useTaskStats, mutations)
  TaskTable.tsx     // shared row/table (used by list + profile + widget)
  TaskFilters.tsx   // search/filter/sort toolbar
  TaskForm.tsx      // create/edit (react-hook-form + zod, as contacts do)
  MyWorkQueue.tsx   // dashboard widget (§11)
  TasksSectionForProfile.tsx  // Customer Profile section (§9)
  index.ts
src/pages/TasksPage.tsx        // route target, composes PageContainer + PageHeader + TaskTable
```

Wiring (all additive): add the `/tasks` route in `routes/router.tsx`; add the nav item in
`navigation.ts`; mount `MyWorkQueue` in `DashboardPage.tsx`; add `TasksSectionForProfile` in
`CustomerProfile.tsx`. **Types come only from `schema.d.ts`** (regenerated in Phase B) — honoring
"never hand-write API types."

---

## 16. Phase B implementation plan (mechanical — after approval)

Ordered so each step builds and tests green before the next. Backend-first, so OpenAPI (the
single source of truth) exists before any frontend line. Each numbered block is independently
committable.

| # | Step | Files (new unless noted) | Verify |
|---|---|---|---|
| B1 | **Models** | `models/task.py`, `models/task_event.py`; add `EVENT_TASK_*` consts to `models/contact_event.py`; register in `models/__init__.py` | import + unit |
| B2 | **Migration** | `alembic/versions/0024_tasks.py`; bump `tests/test_migrations.py` head + `_EXPECTED_TABLES` | `pytest tests/test_migrations.py` |
| B3 | **Permissions** | add 3 perms to `rbac/catalog.py` + role bundles; seeding | rbac tests |
| B4 | **Schemas** | `schemas/task.py` (all §8 components) | schema unit |
| B5 | **Repository + Service** | `repositories/task_repository.py`, `services/task_service.py` (emits `TaskEvent` + `ContactEvent`) | service unit |
| B6 | **Endpoints** | `api/v1/endpoints/tasks.py`; register in `api/v1/router.py` | API integration tests |
| B7 | **Regenerate OpenAPI** | export FastAPI schema → `frontend/openapi.json` | diff = additive only |
| B8 | **Regenerate types** | `npm run gen:api` → `src/lib/api/schema.d.ts` | `tsc --noEmit` |
| B9 | **Frontend feature** | `features/tasks/*` (§15) | component tests |
| B10 | **Wiring** | `router.tsx`, `navigation.ts`, `DashboardPage.tsx`, `CustomerProfile.tsx` | render tests |
| B11 | **Full verify** | — | `tsc` · `eslint .` · `vitest run` · `vite build` · backend `pytest` + `ruff` |

**Test matrix (targets):** state-machine transitions + invariants (TA-INV 1–7); bucket
boundary math (overdue/today/upcoming across the org-timezone midnight); permission gates
(read/write/assign); cursor pagination + filter combinations; optimistic-concurrency 409;
timeline projection emitted on each transition; widget/section render + optimistic complete;
bulk update/delete partial-failure envelope.

**Stop conditions honored:** no backend logic beyond the above; no calendar, notifications, AI,
automation, email, or WhatsApp/browser reminders (Phase-5 DO NOT BUILD).

---

## 17. Traceability matrix

| FR-TASK | Design section(s) | Phase-5 brief item | Doc 13 |
|---|---|---|---|
| 01 anchor/model | §4, §5.1 | Task domain / Task model | GAP-01 |
| 02 types | §4.2, §5.1 | Task Types | GAP-01 |
| 03 status | §4.2, §4.4 | Task Status | GAP-01 |
| 04 priority | §4.2 | Priority | GAP-01 |
| 05 scheduling | §5.1 (`due_at`,`has_time`,`reminder_at`) | Due Date/Time, Reminder | GAP-01 |
| 06 assignment | §5.1, §7 | Assigned Agent / Assigned By | GAP-01 |
| 07 completion | §7.4, §5.1 | Completion Notes | GAP-01 |
| 08 history | §5.2 | Task History | GAP-01 |
| 09 timeline | §5.3, §9 | Task timeline integration | GAP-01 |
| 10 task list | §10 | Task List (all views/filters/bulk) | GAP-01 |
| 11 work queue | §11 | My Work Queue widget | GAP-01 |
| 12 profile | §9 | Customer Profile integration | GAP-01 |
| 13 reporting | §12 | (analytics linkage) | GAP-01 / GAP-06 |
| 14 notifications | §13 | (reserved; DO NOT BUILD) | — |

Every Phase-5 BUILD line maps to a section; every "DO NOT BUILD" line is honored in §13/§16.

---

## 18. Self-review record (applied before submission)

- **Additive-only verified.** New: 2 tables, 3 permissions, 15 endpoints, 5 `contact_events`
  constants, 1 frontend feature. **Edited frozen artifacts: none.** No Doc 01–12 change; no
  existing table/endpoint/schema altered. ✔
- **Conventions matched to source**, not assumed — mixins, `big_id()`/`datetime6()`, naming
  convention, cursor `Page`, `require_permissions`, `Response.of(view)`, campaign-style action
  endpoints, contacts-style bulk. ✔
- **Reuse maximized** — timeline via `contact_events` (no `activities` table, TA-CD1); UI via
  `PageContainer`/`PageHeader`/`TimelineSection`/`ui/*`. ✔
- **Phase-5 fork resolved as instructed** — OpenAPI stays the single source of truth; frontend
  types generated, never hand-written; no temporary frontend models. ✔
- **Scope discipline** — DO-NOT-BUILD list fully respected; only seams reserved (§13). ✔
- **Phase B is mechanical** — ordered steps, files, and verify gates leave no design decisions
  for implementation time. ✔

---

*End of Document 14 — Task & Activity Management Architecture. Additive addendum to the frozen
architecture; **awaiting owner approval before Phase B**. No backend, OpenAPI, frontend, or
Doc 01–12 change has been made — this document is specification only.*



