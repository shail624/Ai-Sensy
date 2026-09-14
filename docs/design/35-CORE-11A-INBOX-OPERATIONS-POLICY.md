# Design Document 35 — CORE-11A Inbox Operations Policy

**Status:** Repository implementation record

**Milestone:** CORE-11A (first bounded delivery inside CORE-11)

**Authority:** ADR-0012, Design Document 25, `ROADMAP.md`, and the existing Settings, Inbox,
Contact, RBAC, Audit, and Customer Timeline authorities

## Purpose and boundary

CORE-11A replaces a real administrative gap with one validated organization policy for three
connected Inbox behaviors: how a newly created conversation is assigned, whether opening a thread
automatically clears shared unread state, and whether exact inbound keywords update Contact consent.

The milestone deliberately does not send welcome/off-hours messages, resolve conversations on a
timer, define working hours, create SLA/pipeline rules, or add notification/security/team-presence
controls. Those remain later CORE-11 slices because each requires its own safe runtime consumer.
No customer-facing auto-reply is implied by the consent control.

## Reuse and ownership map

| Need | Existing authority reused | CORE-11A extension |
|---|---|---|
| Organization persistence | Typed/scoped `settings` table and `SettingRepository` | Reserved `inbox.operations.v1` JSON value behind a Pydantic contract; no migration. |
| Authorization | Existing `settings:manage` and authenticated-user dependency | Every signed-in user may read the non-secret effective policy; only managers may update it. |
| New-thread assignment | Existing `Conversation.assigned_user_id`, users, roles and permissions | `least_open` selects an active `inbox:read` user by unresolved workload; `manual` preserves unassigned behavior. |
| Read state | Existing `POST /conversations/{id}/read` and shared `unread_count` | Inbox auto-clears only when enabled; when disabled, a visible manual action remains available. |
| Consent | Existing Contact opt-in fields and inbound Message transaction | Exact normalized text can move the Contact to opted-in/out only after explicit enablement. |
| Evidence | Existing `AuditService` and `ContactEventService` | Policy updates, system assignment, and consent transitions are recorded atomically. |
| API/client | Existing Settings router and generated OpenAPI pipeline | One path with GET/PUT operations; generated TypeScript remains authoritative. |

The advanced key/value endpoint rejects the reserved policy key. This prevents a caller from
bypassing keyword, enum, list-bound, and overlap validation while preserving every existing generic
setting contract.

## Policy contract

- `assignment_mode`: `manual` or `least_open`; manual is the safe default.
- `auto_mark_read`: defaults true to preserve the shipped Inbox behavior.
- `consent.enabled`: defaults false; text is never interpreted as consent until a manager enables it.
- opt-in/out keywords: 1–40 characters each, at most 20 per list, normalized by case/whitespace,
  de-duplicated, and forbidden from overlapping.
- keyword matching is exact after normalization. A sentence that contains `STOP` is not a match.
- non-text messages and already-current consent states are no-ops.

Assignment considers active same-organization users whose effective permissions include
`inbox:read`, including the existing Owner bypass. Resolved conversations do not count as open
workload. Ties are stable by user id. The rule runs only when the thread is first created, so later
inbound messages never steal a manually reassigned conversation.

## Operator experience

Settings → Application now leads with an original responsive Inbox Operations surface:

1. a clear routing selector with plain-language workload behavior;
2. an explicit automatic-read checkbox;
3. an explicit consent enablement checkbox and keyword fields;
4. one primary save action, permission-truthful read-only state, safe defaults, validation errors,
   loading/retry behavior, and configuration status;
5. the schemaless store retained below as advanced configuration, with the reserved policy hidden.

On the thread surface, automatic clearing waits for the policy query. If disabled, unread state is
left intact and a keyboard-reachable Mark read action appears. A failed policy read therefore fails
safe without silently clearing state.

## Reference and originality review

The approved ignored captures reviewed before implementation were the Manage/settings and team
sequence `0045`–`0055`, with focused attention on:

- `0046_manage_opt_in_management_configure_*` for explicit configured-state hierarchy;
- `0047_manage_live_chat_settings_*` for grouped messaging controls and focused editing;
- `0053_manage_team_create_member_viewport.png` for compact administrative form density;
- `0055_manage_notification_preferences_add_device_*` for clear toggle state and mobile stacking.

Only workflow goals and quality signals were retained: distinct categories, visible state,
explanatory copy, bounded forms, one obvious action, and responsive stacking. The billing/seat
purchase modal and promotional Billing/Ads/AI cards visible in `0052` were explicitly rejected as
outside approved scope. The implementation uses original React/Python, Vi wording, Lucide icons,
repository tokens, spacing, layout, and service rules. No proprietary code, asset, branding, text,
token, pixel layout, screenshot, or reference file is copied or committed.

## Security and correctness

- Organization ownership is derived only from the authenticated user or persisted conversation.
- Policy mutation requires `settings:manage`; policy values contain no secret.
- Generic settings writes cannot mutate the reserved key.
- Consent updates, Timeline evidence, Audit evidence, Contact version, Message, and conversation
  changes share the inbound transaction.
- Automatic assignment records a system Audit entry and never targets an inactive, deleted,
  cross-tenant, or permission-ineligible user.
- Defaults preserve existing behavior except for new optional capabilities, which remain off.
- No migration, permission code, queue, scheduler, provider capability, or parallel authority is
  introduced.

## Validation boundary

Repository tests cover defaults, authentication/management permissions, normalization, overlapping
keyword rejection, generic-write bypass rejection, Audit evidence, exact consent application,
eligible least-open assignment, settings UI persistence, and automatic/manual read behavior.
OpenAPI regeneration, generated types, lint, strict types, frontend regression and production build
are required gates.

The in-app browser reached the real local application but the authenticated Settings screen was not
opened because no credential was entered during this repository-only pass. Authenticated
representative-data visual comparison, mobile/desktop screenshots, keyboard-only and screen-reader
review, target-host MySQL concurrency/load behavior, and production commissioning remain
`PENDING – Host Machine Validation`; no visual or host acceptance is fabricated.

## Remaining CORE-11 work

- working hours plus safe welcome/off-hours message delivery;
- auto-resolve timers and broader assignment rules;
- campaign preferences, pipeline/SLA, notification, security and audit settings;
- team online presence, workload reporting, login history and permission audit;
- required/active attribute-definition controls and their domain enforcement.
