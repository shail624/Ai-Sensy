# Phase 2 — Customer Engagement Platform

**Status:** RELEASE READY
**Scope:** Premium engagement workflows composed from the existing production contracts.
**Architecture impact:** Frontend extension only; no backend, schema, migration, permission, queue, provider, or OpenAPI change.

## Objective

Phase 2 turns the Phase 1 workspace into a more complete day-to-day customer engagement product.
It extends the shared inbox, Customer 360, campaign/template/segment workflows, analytics, and
assistive UI without creating a second CRM, campaign engine, audience engine, analytics store, or
AI execution path.

## Capability realization

| Area | Phase 2 result | Source of truth |
|---|---|---|
| Shared Inbox | Server-synchronized custom inboxes and pins, quick folders, advanced name/number search, multi-agent assignment, labels, explicit snooze status, teammate mention insertion, customer/notes/AI context, unread/SLA signals, and bulk status/assignment/label actions | Existing conversation, note, tag, user-preference, and message APIs |
| Contact CRM | Customer 360 continues to unify identity, attributes, tags, lifecycle, assignment context, tasks/reminders, notes, campaign history, conversation access, recent interactions, documents/KYC placeholders, and activity timeline | Existing contact, timeline, task, campaign, and conversation APIs |
| Campaign Builder | Audience → Template → Preview → Schedule → Approval → Confirmation → Analytics journey; reusable campaign patterns remain ordinary duplicate drafts; audience preview and cost evidence remain server-owned | Existing campaign create/update/preview/estimate/schedule/dispatch APIs |
| Template Center | Search, category/language/status filters, preview/editor, variables, version history, approval/quality state, and per-user favorites | Existing template APIs plus presentation preferences |
| Segments | Dynamic rule builder, reusable audiences, cached audience estimation, search/filter/sort, and record-level recent-item tracking | Existing segment and workspace preference behavior |
| Broadcast Center | Dedicated marketer view over the existing campaign engine; no duplicate dispatch or schedule path | Existing `CampaignList` and campaign permissions |
| Analytics | Sticky dashboard navigation, delivery/read trends, campaign and employee performance, factual delivery funnel, exports, and honest template-performance boundary | Existing analytics rollups and report export APIs |
| AI foundations | Reply, summary, campaign, template, audience, and analytics integration seams with explicit provider-not-connected and human-approval states | UI only; the deferred AI service is not simulated |
| Enterprise UX | Responsive context panels, sticky navigation, keyboard inbox search, skeleton/empty states, motion with reduced-motion support, bulk actions, favorites, recents, and accessible labels | Existing design system and permission guards |

## Contract-gated boundaries

- Conversation merge is visible but disabled because no audited merge contract exists. Reusing contact
  deduplication or moving partitioned messages would change business behavior and is explicitly rejected.
- Snooze uses the existing server-owned `snoozed` status. A wake-up timer is not claimed because the
  current contract stores no `snooze_until` value.
- Typing/presence remains absent because the reserved WebSocket transport is not implemented; polling is
  still labelled accurately as ten-second refresh.
- Teammate mentions are persisted in internal-note text. Notification delivery is not claimed by the
  current note contract.
- Template-level analytics is not inferred: the rollup contract exposes no template dimension.
- AI never generates, mutates, approves, or sends. The UI states the missing provider/policy/interaction-
  record/approval dependencies and preserves the mandatory human-control invariant.

## Validation evidence

- Canonical release profile passed all 20 stages on 2026-07-25: Ruff, strict mypy across 227
  backend source files, OpenAPI drift, ESLint, TypeScript, browser-test types, 902 backend tests,
  590 frontend tests, production frontend build, SAST, dependency audits, source/security/IaC scan,
  both Compose contracts, production image rebuilds, image contracts, HIGH/CRITICAL image scans,
  and CycloneDX SBOM generation.
- OpenAPI remains 3.1.0 with 133 paths. No backend route, schema, migration, permission, queue,
  provider, tenant-isolation, or business-rule change was introduced.
- The isolated ten-service production gate passed login, queued contact import, persisted profile,
  Broadcast Center, Analytics engagement-funnel, and 390 × 844 mobile Broadcast Center checks.
  It found no horizontal overflow or HTTP 500 response and cleaned up its disposable stack.
- Production readiness returned 503 when Redis was intentionally stopped; runtime request evidence
  remained correlated and free of the gate's synthetic secrets/PII. The authenticated 30-read
  performance canary passed at p95 7.2 ms against the <300 ms standard-read budget.
- A live browser accessibility/responsive audit passed at 1280 × 720 and 390 × 844: one clear H1,
  associated form labels, correct autocomplete purposes, 44 px mobile controls, no horizontal
  overflow, and no runtime error. The known React Router v7 future-flag warning remains debt.
