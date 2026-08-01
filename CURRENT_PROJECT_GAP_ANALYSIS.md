# Current Source Project — Gap Analysis

This audit compares the uploaded old source project with the approved Private Vi Reactivation Operations Platform scope.

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
- Customer 360 profile with timeline, conversations, campaigns, documents, notes, KYC/SIM projections, tasks, audit, activity, and AI placeholder tabs
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

The navigation and UI shell exist, but dedicated production records and APIs are still missing for:

- Eligibility cases
- Reactivation cases
- Real Kanban lead cards and drag/drop transitions
- Stage-event history
- Number reservation
- Family-plan requirements
- Conversion records
- Reactivation-specific SLA calculations

### KYC

Current UI is a foundation/projection. Missing:

- Dedicated KYC model and API
- Checklist and appointment records
- Original-holder and Delhi-presence verification
- Reviewer decision workflow
- Manager approval
- KYC-specific audit events

### SIM Orders

Current UI is a foundation shell. Missing:

- SIM order model and API
- Dispatch/delivery lifecycle
- Delivery agent assignment
- SIM serial and activation linkage
- Delivery SLA and failure reasons

### Activation

Current UI is a foundation shell. Missing:

- Activation record
- Activation queue
- Verification hand-off
- Completion decision
- Activation audit events

### Executive reporting

Existing analytics are mainly messaging-based. Missing domain dimensions for:

- Revenue
- Reactivation conversion
- KYC turnaround
- SIM fulfilment
- Activation success
- SLA violations

### Notifications

Preferences exist, but a full server-backed Notification Center with unread state, deep links, SSE/push, and mark-read actions is not yet implemented.

### Saved views and favourites

Some browser-local support exists. Server-synchronised saved views and enterprise sharing are not complete.

### Approval workflows

Automation approval concepts exist, and campaign approval UI exists, but a general approval engine for KYC, eligibility overrides, SIM issue, activation completion, exports, and document downloads is incomplete.

### Integrations

- Webhook infrastructure exists.
- Google Sheets integration is not implemented.

### Chat History

Conversation history exists inside Inbox and Customer 360, but a dedicated Chat History navigation page with agent/date/media/audit filters is not yet present.

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
3. Add migrations, repositories, services, schemas, RBAC, and APIs.
4. Connect Reactivation Kanban to real cases and transitions.
5. Connect KYC, Documents, SIM, Activation, and Customer 360.
6. Build server-backed Notification Center.
7. Add dedicated Chat History.
8. Add tests for transitions, approvals, permissions, audit, and tenant isolation.
