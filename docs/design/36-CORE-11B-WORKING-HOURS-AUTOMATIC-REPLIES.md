# Design Document 36 — CORE-11B Working Hours and Automatic Replies

**Status:** Repository implementation record

**Milestone:** CORE-11B (second bounded delivery inside CORE-11)

**Authority:** ADR-0012, Design Documents 25 and 35, `ROADMAP.md`, and the existing Organization,
Settings, Inbox, Message, Business Event, Audit, queue, and channel-adapter authorities

## Purpose and boundary

CORE-11B adds organization working hours plus optional welcome and off-hours text replies to the
validated Inbox Operations policy delivered by CORE-11A. The setting is a real runtime control:
fresh accepted inbound messages evaluate it inside the inbound transaction, persist at most one
policy-selected outbound Message, and dispatch that durable row only after commit.

All three capabilities are disabled by default. This milestone does not add a chatbot, AI reply,
template authoring, campaign send, auto-resolve timer, SLA clock, notification rule, provider
capability, or second automation engine. Those remain separate approved slices.

## Reuse and ownership map

| Need | Existing authority reused | CORE-11B extension |
|---|---|---|
| Local clock | `Organization.timezone` | The effective Inbox policy exposes this value read-only; no duplicate timezone setting. |
| Policy persistence | Reserved `inbox.operations.v1` organization setting | Adds a validated seven-day schedule and two optional reply definitions; no migration or new route. |
| Customer window | Existing Conversation `last_inbound_at` and 24-hour window logic | The locked inbound open operation returns whether this message opened a new window. |
| Reply ledger | Existing outbound `Message` and conversation preview authorities | A system-authored accepted text is stored with the source conversation's exact channel owner. |
| Idempotency evidence | Existing `BusinessEvent` store | A deterministic source-message/kind event links the inbound row to the one accepted reply. |
| Delivery | Existing `send_message` task and `SendService` adapters | Dispatch occurs after inbound commit and reuses the provider-specific delivery path. |
| Evidence | Existing Audit and automation-event projection | System send metadata identifies `inbox_operations`, reply kind, and source message. |
| UI/client | Existing Settings → Application panel and generated API contract | Original responsive schedule/reply editor; canonical OpenAPI remains 208 paths. |

## Policy contract

- `working_hours.enabled` defaults false.
- `days` contains each weekday exactly once. Each local interval uses validated `HH:MM` values;
  enabled days cannot have equal start/end values. An end at or before its start crosses midnight.
- enabling working hours requires at least one enabled day and a valid IANA organization timezone.
- welcome and off-hours bodies are trimmed, limited to 1,000 characters, and required only when
  their corresponding switch is enabled.
- off-hours replies cannot be enabled unless working hours are enabled.
- disabling working hours in the UI also clears off-hours enablement before save.

The existing organization timezone is the sole interpretation authority. A schedule such as Monday
22:00–06:00 remains open at Tuesday 01:00; the evaluator checks both the current and previous local
day so an overnight interval is not split or misclassified.

## Decision and safety rules

One fresh inbound message can select at most one reply:

1. opted-out Contacts never receive an automatic reply;
2. inbound timestamps older than ten minutes or more than five minutes in the future are ledger-only,
   preventing delayed webhook replay from unexpectedly contacting a customer;
3. when working hours are enabled and the timestamp is outside every active interval, the off-hours
   reply takes precedence;
4. an off-hours reply is limited to one per conversation in a rolling 24-hour period;
5. welcome is considered only inside working hours (or when hours are disabled) and only when the
   accepted inbound opens a new 24-hour customer-service window;
6. invalid runtime timezone data fails closed with no reply.

Consent processing remains earlier in the same inbound path. Therefore an exact opt-out keyword
updates the Contact before reply selection and suppresses the reply immediately.

## Atomicity, idempotency, and recovery

The conversation is locked while its inbound window is evaluated and updated. The inbound Message,
conversation changes, automatic outbound Message, system Audit evidence, and deterministic Business
Event are committed together. The deterministic event UUID is derived from organization,
conversation, source message, and reply kind; duplicate provider deliveries recover the already
accepted reply id instead of creating another row.

Only after commit does the task enqueue `send_message`. If the task is redelivered after a lost
post-commit handoff, it selects the same durable reply. Delivery serializes on the Message row and
the existing provider id check makes later executions no-ops once the provider has accepted the
send. WAHA's existing indeterminate-send rule remains unchanged: an unconfirmed provider outcome is
recorded failed and is not silently retried.

## Operator experience and originality

Settings → Application extends the original Inbox Operations card with the organization timezone,
one master hours switch, seven compact day/time rows, overnight guidance, independent welcome and
off-hours cards, character counts, explanatory rate/window text, validation, permission-aware
disabled state, and responsive stacking.

Approved capture `0047_manage_live_chat_settings_*` informed only the workflow expectation that
hours and messaging controls belong together with explicit enablement and visible message editing.
All Python/React code, wording, validation, components, tokens, spacing, icons, and layout are
original to this repository. No AiSensy code, text, asset, branding, token, or pixel layout is used.

## Validation boundary

Repository coverage proves safe defaults, timezone projection, overnight persistence, schedule and
message validation, off-hours precedence/rate limiting, new-window welcome behavior, stale replay
suppression, immediate opt-out suppression, source-event idempotency, transactional persistence,
post-commit task dispatch, generated contracts, frontend persistence, lint, strict types, regression
tests, and production build.

The real local route redirects to the authentication screen and no credential was entered.
Authenticated representative-data desktop/mobile screenshots, keyboard-only and screen-reader
review, target-host database/queue concurrency, production delivery observation, and browser matrix
remain `PENDING – Host Machine Validation`; no host or provider acceptance is inferred.

## Remaining CORE-11 work

- auto-resolve timers and broader assignment rules;
- campaign preferences, pipeline/SLA, notification, security, and audit settings;
- team online presence, workload reporting, login history, and permission audit;
- required/active attribute-definition controls and their domain enforcement.
