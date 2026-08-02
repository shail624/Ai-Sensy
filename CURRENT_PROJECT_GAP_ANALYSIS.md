# Current Source Project — Gap Analysis

This audit compares the uploaded old source project with the approved Private Vi Reactivation Operations Platform scope.

## Owner-approved lightweight CRM correction

As of CORE-05, the canonical operating model is one Reactivation case with exactly one primary
status, multiple flexible labels, dated Task-backed reminders, assignment, notes, Audit, and
Customer Timeline. The completed CORE-02/04 KYC, SIM, and Activation backend foundations are
preserved, but separate new heavyweight SIM fulfilment and Activation Queue products are not a
remaining gap unless the owner explicitly reauthorizes them. SIM Required and Activation Pending
are current case statuses; Follow-up and Name Change are labels with governed dates. A concept is
never stored as both a current status and a label.

## GOV-02 quality and experience lens

This remaining-work baseline is unchanged. GOV-02 adds the permanent acceptance lens in ADR-0012
and Design Document 25: a route, shell, generic page, projected metric, browser-local substitute, or
visual placeholder does not close a product gap. Completion requires real authorized backend state,
the approved workflow, shared enterprise components, responsive and accessible behavior, complete
loading/empty/error/permission states, relevant tests, and premium original presentation.

The owner-approved local AiSensy capture library may be used only as a Git-ignored workflow and
visual-quality benchmark for the approved categories and active milestone. It is not implementation
truth and may not supply copied code, text, assets, branding, design tokens, or layouts. Conditional
AI and Automation references remain gated to their own approved milestones; prohibited ads,
payments, billing, marketplace, SaaS, reseller, multi-project, and commerce references cannot close
or create a gap.

## Already present and usable foundations

- Authentication and private-user shell
- Premium responsive layout
- Dark/light theme support
- Dashboard
- Shared Inbox / Live Chat
- Conversation filters, assignment, tags, notes, and quick replies
- Contacts, CSV import, bulk actions, tags, attributes, and segments
- Customer 360 profile converged over persisted identity, exact-contact conversations/messages,
  Reactivation CRM, reminders, notes, documents, tasks, KYC/SIM/Activation facts, campaigns, Audit,
  and Customer Timeline, with source-workflow deep links and no synthetic metrics
- Campaign management and campaign wizard
- WhatsApp template management
- Analytics foundation
- Simplified/versioned automation foundation
- Team, roles, permissions, API keys, and audit log
- Document storage, versions, verification, and signed access
- Global search and Ctrl+K command palette
- Browser-local favourites and recent destinations
- Tasks and reusable pipeline configuration
- Reactivation navigation shell
- Scan Studio shell
- API and webhook operations
- MySQL, Redis, Celery, FastAPI, and React/Vite architecture

## Present but incomplete / foundation-only

### Reactivation

The real tenant-scoped case, nine-status Kanban/list, assignment, immutable stage history, notes,
eligibility, reservation/family/conversion/SLA facts, six labels, Follow-up/Release dates, shared
Task reminders, due counters, filters, concurrency, Audit, Timeline, responsive drawer and factual
states are complete. Remaining gaps are server-shared saved views/pagination at scale, Notification
Center fan-out/unread/SSE, final analytics, and representative-data visual/WCAG/performance evidence.

### KYC

The dedicated KYC authority, protected document checklist references, Task appointments,
original-holder/Delhi/active-number checks, separated reviewer/manager decisions, structured
rejections, immutable evidence, and Customer 360 projection are complete and preserved. Remaining
work is shared saved views/pagination and target-host protected-media, accessibility, and scale
commissioning—not another KYC authority.

### SIM Orders

The CORE-02 SIM order/event, delivery, ownership, serial, failure, confirmation, SLA, audit and API
foundation exists and remains preserved. The owner-approved daily CRM represents operational need
with the `SIM Required` primary case status and optional `Prepaid Required` label. A separate heavy
fulfilment workspace is intentionally not planned without a later explicit owner instruction.

### Activation

The CORE-02 Activation record, transition, approval/completion/rejection, RBAC, audit and API
foundation exists and remains preserved. The lightweight CRM uses `Activation Pending`, `Completed`
and `Not Required` case dispositions instead of a new standalone Activation Queue. Rich standalone
operations are owner-deferred rather than an active gap.

### Executive reporting

Existing analytics are mainly messaging-based. Missing domain dimensions for:

- Revenue
- Reactivation conversion
- KYC turnaround
- SIM Required and Activation Pending status outcomes
- SLA violations

### Notifications

Preferences exist, but a full server-backed Notification Center with unread state, deep links, SSE/push, and mark-read actions is not yet implemented.

### Saved views and favourites

Some browser-local support exists. Server-synchronised saved views and enterprise sharing are not complete.

### Approval workflows

**CORE-08 — Skipped: Not required by product owner.** A generic
Approval Center, approval framework, queue, escalation system, or new approval authority is not a
product gap and must not be built. Existing KYC-specific approval logic, campaign/automation
authorization concepts, requester/reviewer separation, RBAC, tenant isolation, and completed
authorization safeguards remain preserved and must not be deleted or rewritten.

### Integrations

- Webhook infrastructure exists.
- Google Sheets integration is not implemented.

### Chat History

Conversation history exists inside Inbox and Customer 360, but a dedicated Chat History navigation page with agent/date/media/audit filters is not yet present.

### Customer 360

CORE-07 completes the factual Contact workspace by composing the existing persisted authorities for
identity and attributes, exact-contact WhatsApp threads/messages, Reactivation status/labels,
reminders, assignment, notes, Documents, Tasks, KYC/SIM/Activation facts, Campaign participation,
Audit, and Customer Timeline. It introduces no snapshot table, duplicate record, synthetic metric,
or parallel workflow. Remaining Customer 360 work is limited to final target-device/WCAG and
production-scale commissioning plus future facts added by separately approved source milestones.

### Lower-severity maintenance findings

- The owner-bootstrap CLI currently accepts reserved `.test` email addresses that the login request
  schema rejects. This does not affect valid production addresses or tenant isolation, but the two
  validation boundaries should be aligned in a later maintenance milestone.

### Download Center

Export jobs exist at backend level, but a unified user-facing Download Center is not complete.

## Explicitly excluded

The following must not be added:

- Ads Manager
- WhatsApp Payments
- SaaS billing and subscriptions
- Multi-project tenancy
- Public signup
- Reseller tools
- Integration marketplace
- Promotional/trial/upgrade screens

## Correct first engineering milestone

1. Lock navigation and remove unrelated product concepts.
2. Add server-owned domain models:
   - ReactivationCase
   - ReactivationStageEvent
   - EligibilityCheck
   - KycCase and KycDecision
   - SimOrder and SimOrderEvent
   - ActivationRecord
   - SlaPolicy and SlaEvent
3. Add migrations, repositories, services, schemas, RBAC, and APIs. **Complete through `0034`.**
4. Connect Reactivation Kanban to real cases and transitions. **Complete.**
5. Deliver protected KYC operations and Customer 360 projection. **Complete and preserved.**
6. Apply the owner-approved lightweight status/label/Task-reminder CRM correction. **Complete.**
7. Converge remaining factual CRM projections in Customer 360 without adding heavy standalone
   SIM/Activation products. **Complete.**
8. **CORE-08 — Skipped: Not required by product owner.**
9. Build CORE-09, the shared server-backed Notification Center over existing due evidence.
10. Add dedicated Chat History and remaining roadmap capabilities.
