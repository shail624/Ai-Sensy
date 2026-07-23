# Implementation Tracker (canonical)

> Single source of truth for project state. **Every new session must read this first.**
> Update it after each verified milestone. Keep it short — state, not narrative.

_Last updated: 2026-07-22 · verified by full suite (722 passed, ruff clean, app boots)._

## Current state
- **Branch:** `feature/module6-queue-engine`
- **HEAD commit:** `a0fed9b`
- **Migration head:** `0026_tasks` (26 revisions, linear, base `0001`)
- **OpenAPI paths:** 115 (live app; `frontend/openapi.json` regenerated to match)
- **Tests:** 722 passed · **Ruff:** clean · **TypeScript:** clean

## Completed & committed
| Milestone | Commit | Migration |
|---|---|---|
| Module 1 — Foundation / Auth / RBAC / Audit | frozen | 0001–0004 |
| Module 2 — CRM (contacts, tags, segments, attrs, import/export, bulk) | frozen | 0005–0013 |
| Queue Engine + Storage | frozen | 0009–0010 |
| M4 S1–S2 — Channel abstraction, WABAs, phone numbers | `4e30a87` | 0014 |
| M4 core — webhooks, conversations/ledger, outbound, media | `8a842b2` | 0015–0016 |
| M5 — Template registry & template messaging | `af8dce8` | 0017 |
| Rate gate & adaptive throttling | `ab24087` | — |
| Phase 6 S1 — Campaign registry & audience | `32bdb63` | 0018 |
| Phase 6 S2 — Dispatch engine | `960513a` | 0019 |
| Phase 6 S3 — Campaign lifecycle | `5dfd2dd` | 0020 |
| Phase 6 S4 — Campaign scheduling | `2aa0cf2` | 0021 |
| Phase 6 S5 — Campaign cost engine | `c8e309e` | 0022 |
| Phase 7 — Shared inbox core (assignment, status, notes) | `f099cce` | 0023 |
| Phase 7 — Conversation read endpoints (list, detail, history) | `84b33d1` | — |
| Phase 7 — Mark-read resets shared unread count | `ab99419` | — |
| Phase 7 — Quick replies CRUD (personal & shared) | `8a58012` | 0024 |
| Phase 7 — Conversation tags (FR-INB-07) | `16c65e2` | 0025 |
| Phase 7 — Message reactions | `9f0694f` | — |
| Frontend foundation — OpenAPI client & tooling | `bad4081` | — |
| Frontend foundation — extensible customer profile | `f8e8451` | — |
| Frontend foundation — contacts module | `a0fed9b` | — |

## Uncommitted working tree (Doc 14 — Task & Activity Engine)
Backend complete and verified; **not yet committed**.

| Area | State |
|---|---|
| Models (`task.py`, `task_event.py`), `contact_event` constants | done |
| Migration `0026_tasks` (file `alembic/versions/0026_tasks.py`) | done |
| RBAC — `tasks:read` / `tasks:write` / `tasks:assign` + role bundles | done |
| Schemas, repository, service, 15 endpoints | done |
| Tests — `test_task_service.py` (48), `test_api_tasks.py` (45) | done |
| B7 — `frontend/openapi.json` regenerated (103 → 115 paths) | done |
| B8 — `src/lib/api/schema.d.ts` regenerated, `tsc --noEmit` clean | done |
| B9/B10 — frontend feature, route, nav, widget, profile section | **not started** |

## In progress / next
- **Doc 14 Phase B** — backend + generated types are done. Next approved step is the frontend
  feature (`features/tasks/`, `/tasks` route, nav item, `MyWorkQueue`, profile section) per
  Doc 14 §9–§11/§15 — **awaiting owner approval.**
- **Phase 7 — Shared Inbox** remaining G/H items per Doc 02 Phase 7 / Doc 04 §18.1 /
  Doc 07 §19–§23 — awaiting owner's next approved step.

## Permanent invariants (never violate)
Repository→Service→API layering · all sends through SendService · provider payloads stay in the Meta adapter · Retry Engine is the single authority on classify/backoff · Rate Gate never opens (fail-safe pacing) · persist-first webhooks · campaign status controls dispatch · frozen modules never modified · unbuilt surfaces absent (not stubbed) · partitioned tables carry no FKs · frontend API types are **generated only**, never hand-written.

## Notes for the next session
- Run everything via `backend/.venv/Scripts/python.exe`.
- `alembic check` needs live MySQL (asyncmy absent); migration integrity is covered by `tests/test_migrations.py` instead — bump its head assertion + `_EXPECTED_TABLES` with every new migration.
- Cron is Celery's `celery.schedules.crontab` (reused), in `campaign_schedule_service.py`. Do **not** hand-roll a cron evaluator.
- Regenerate the API contract with `python -m scripts.export_openapi` (backend) then `npm run gen:api` (frontend). Never hand-edit `openapi.json` or `schema.d.ts`.
- Task state transitions are guarded by `TaskService._check_transition` (Doc 14 §4.4 → 409 `task_state`); `create_timeline_note` surfaces the completion note on the **contact timeline** only — it never writes an internal note.
