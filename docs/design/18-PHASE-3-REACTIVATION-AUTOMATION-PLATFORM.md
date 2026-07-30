# Phase 3 — Reactivation Platform and Automation Foundations

**Status:** RELEASE READY
**Scope:** Premium reactivation, Customer 360, scan, reporting, and automation composition over
the existing production contracts.
**Architecture impact:** Frontend extension only; no backend, schema, migration, permission,
tenant-isolation, queue, provider, business-rule, or OpenAPI change.

## Objective

Phase 3 makes the product's reactivation journey legible and operable without inventing a second
CRM, document store, pipeline engine, analytics store, campaign dispatcher, provider adapter, or
automation runtime. Contract-backed functions use the existing services; unbuilt domains are
visible only as explicit, disabled integration boundaries.

## Capability realization

| Area | Phase 3 result | Source of truth |
|---|---|---|
| Reactivation workspace | Permission-aware routes for Eligible Numbers, Bulk Eligibility, Interested Customers, Customer Pipeline, KYC, Document Center, SIM Orders, Activation Queue, Completed, and Reports | Existing route/permission shell; contract-gated domain seams |
| Customer pipeline | Canonical Lead → Eligibility Check → Interested → Documents Received → Verification → KYC Approved → SIM Ordered → Activation Pending → Activated → Completed blueprint; pipeline selector and search use existing pipeline/stage data | Existing pipeline and stage APIs; lead-card movement remains unavailable |
| Customer 360 | Overview, Timeline, Conversation, Campaign History, Documents, KYC, SIM, Payments, Tasks, Internal Notes, Audit, Activity, and AI Assistant | Existing contact/timeline/conversation/campaign/task APIs plus explicit gaps |
| Document Center | Existing media list, upload, preview, and storage behavior embedded in the reactivation workflow | Existing media API and permissions |
| KYC and SIM | Typed CRM attributes can be projected without claiming a workflow record; verification, approval, ordering, and activation mutations remain unavailable | Existing contact attributes only |
| Scan Studio | Separate operator surface and adapter/queue blueprint; never represented as the official Meta Cloud channel | UI boundary only; CRM import/segments remain the supported adjacent workflows |
| Automation | Accessible in-memory visual blueprint with palette, selection, drag reorder, keyboard reorder, removal, and mandatory human-approval nodes | UI only; save and run are disabled |
| Reports | Real last-30-day analytics KPIs, engagement funnel, and exports; reactivation/KYC/SIM/scan dimensions are not inferred | Existing analytics and report-export APIs |
| AI foundations | Reply, summary, document-summary, campaign, audience, and analytics seams remain human-controlled | UI only; provider execution remains deferred |
| Enterprise UX | Responsive routes, breadcrumbs, contextual navigation, skeleton/empty states, clear architecture notices, accessible controls, and route-level code splitting | Existing design system and permission guards |

## Contract-gated boundaries

- Pipeline configuration and ordered stages are real. The API does not list lead cards by stage or
  provide an audited lead-stage transition, so the board displays zero verified cards and does not
  permit drag/drop mutation, assignment, SLA timers, activity feeds, or saved lead views.
- Media upload, list, preview, and storage are real. Contact-linked document records, versions,
  verification decisions, expiry, and document workflow statuses are not in the contract.
- KYC records, identity-verification decisions, SIM orders, activation records, completion records,
  payment records, and their reporting dimensions do not exist and are never simulated.
- Scan Studio is deliberately separate from the official WhatsApp Cloud channel. No scan batch,
  adapter, classification, retry, comparison, progress, export, or result contract exists yet.
- The automation canvas is a local design aid. No versioned workflow schema, persistence API,
  runtime, run ledger, retry/DLQ path, webhook executor, scheduling authority, or approval API is
  present. Save and Run remain disabled and nothing can execute or send.
- AI never generates, mutates, approves, or sends. Every future customer-facing effect must pass a
  human approval and the existing audited send authority.

## Validation evidence

- The canonical release profile passed all 20 stages on 2026-07-25: Ruff, strict mypy across 227
  backend source files, OpenAPI drift, ESLint, TypeScript, browser-test types, 902 backend tests,
  595 frontend tests, production frontend build, SAST, dependency audits, tracked-source security/
  secret/IaC scanning, both Compose contracts, production image rebuilds, image contracts,
  HIGH/CRITICAL image scans, smoke validation, and CycloneDX SBOM generation.
- OpenAPI remains 3.1.0 with 133 paths. No route, schema, migration, permission, task registration,
  queue behavior, tenant isolation, provider behavior, or business rule changed.
- The production build route-splits Scan Studio (6.49 kB), Automation (9.67 kB), and Reactivation
  (18.75 kB). The main chunk is 652.85 kB / 159.56 kB gzip, below the Phase 2 baseline.
- The isolated ten-service production gate passed service health, migrations, owner bootstrap,
  Celery worker/task registration, queue initialization, login, queued CSV import, persisted
  Customer 360, Broadcast Center, Analytics, Reactivation, Automation, Scan Studio, and the
  390 × 844 no-horizontal-overflow check. It recorded no HTTP 500 response and cleaned up fully.
- The authenticated 30-read performance canary passed at p95 12.6 ms against the <300 ms budget.
  Readiness returned 503 when Redis was intentionally stopped; correlated runtime logs remained
  free of the gate's synthetic secrets and PII.
- A live browser audit passed at 1440 × 900 and 390 × 844 with one clear H1, labelled controls,
  no horizontal overflow, and no runtime error. React Router v7 future warnings remain known debt.

## Phase 4 contract backlog

Phase 3 deliberately does not authorize Phase 4 implementation. Any later milestone must begin
with additive, reviewed contracts for the specific domain it intends to make operational:

1. Contact-linked document records, versions, verification, expiry, and status history.
2. KYC decisions and audit evidence; SIM order, activation, and completion lifecycle records.
3. Lead-card listing, assignment, SLA metadata, audited stage transitions, and saved board views.
4. Scan adapter/batch/result contracts with queue ownership, retry/DLQ, deduplication, export, and
   separation from the Meta Cloud provider adapter.
5. Versioned automation definitions, permissions, approval policy, run ledger, scheduler/runtime,
   retries/DLQ, and audited integration execution.
6. Payment records and reactivation-specific analytics dimensions only if separately approved.
7. AI provider, policy, interaction-record, approval, and audit contracts; never autonomous send.

Phase 4A realized item 1 on 2026-07-30 through the additive contract in Design Document 19 and
ADR-0008. Items 2–7 remain unimplemented and contract-gated; Phase 3 itself remains unchanged.
