# Delivery Roadmap

Each module is delivered **complete**: source, models, migration, endpoints,
business logic, validation, logging, exception handling, unit + integration
tests, Docker changes, and documentation. A module is only "done" when its
tests pass. Modules build strictly on top of the ones before them.

| # | Module | Delivers | Status |
|---|--------|----------|--------|
| **1** | **Foundation + Authentication & RBAC** | Repo scaffold, Docker stack, config, DB/session, Alembic, structured logging, exception framework, Users/Roles/Permissions, JWT login/refresh/logout, RBAC dependency, seed admin, unit + integration tests | **Complete** |
| 2 | Frontend Shell + Auth UI | React/TS/Vite/Tailwind app, login, protected routing, layout, dark mode, dashboard, React Query client | **Complete** |
| 3 | Contacts | CRUD, CSV/Excel import, duplicate detection, bulk edit/delete, tags, segments, custom attributes | **Release ready** |
| 4 | WhatsApp Cloud API Core | WABA + phone-number management, webhook management + verification, inbound/outbound messages, media upload/download, active-detection | **Complete** |
| 5 | Templates + Media Library | Template sync/create/status, media library, cost metadata | **Complete** |
| 6 | Broadcast Campaigns | Scheduler, recurring, queue, pause/resume, smart retry engine, resume-interrupted, per-message tracking | **Complete** |
| 7 | Shared Inbox | Conversations, history, quick replies, internal notes, assignment | **Complete** |
| 8 | Analytics & Reports | Delivery/read/failure reports, cost analytics, report exports, campaign analytics | **Complete** |
| 9 | AI Assistant + Knowledge Base | AI chat assistant, knowledge base, suggested replies | Deferred beyond RC1 |
| 10 | Admin & Ops | Audit logs, operations monitoring, settings, API keys, exports | **Complete for RC1 scope** |
| 11 | Hardening & Deployment | E2E tests, load tests, observability, security review, production deployment guide | **In progress** |

## Working agreement

1. Build one module at a time; finish before starting the next.
2. No placeholders, no "implement later", no omitted code.
3. Self-review across all engineering roles before presenting.
4. Run the test suite; fix until green.
5. You (the owner) test and approve each module before we proceed.
