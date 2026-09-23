# CORE-13 — first-message tag rules

## Decision

An organization tag may carry an optional list of exact-match first-message keywords. The inbound
rule evaluator applies every matching configured tag only when a channel conversation receives its
first accepted inbound text message. Matching ignores case, repeated whitespace and surrounding
whitespace; it does not treat a keyword as a substring of a longer message.

Rule configuration belongs to the tag itself. This prevents a deleted tag from leaving an enabled,
stale rule in a separate settings document and keeps create, edit and delete ownership in the
existing tag authority.

## Scope boundary

- Add enabled state and normalized keywords to the organization-scoped tag contract and Tags UI.
- Evaluate the rule for both Meta-owned and provider-neutral inbound conversations.
- Attach through the canonical contact-tag authority so usage count, timeline and audit behavior
  remain identical to manual or automation-driven tagging.
- Record the applied effect as a deterministic event on the existing immutable business-event
  ledger.
- Preserve duplicate webhook safety through the existing provider-message and tag-junction keys.

## Deliberately unchanged

This is exact first-message matching, not AI classification, substring search, tag groups, journey
inclusion or general multi-step automation. It adds no parallel rule table, event table, navigation
placeholder or conversation-tag side effect. Later messages cannot trigger the rule, including a
new service window on an existing conversation.

## Persistence

Migration `0071_tag_first_message_rules` adds a disabled boolean and a non-null JSON keyword list
to tags. Existing tags migrate disabled with an empty list. Downgrade removes only these two new
columns.

## Acceptance evidence

- Backend coverage proves normalization, validation, editability, first-message-only execution,
  exact matching, duplicate safety, usage count, contact timeline and business-event recording.
- Frontend coverage proves create/edit request shape and truthful enabled-rule display.
- OpenAPI and generated TypeScript remain synchronized at 247 paths.
- Full-suite and host limitations are recorded in `VALIDATION_RESULTS.md`.
