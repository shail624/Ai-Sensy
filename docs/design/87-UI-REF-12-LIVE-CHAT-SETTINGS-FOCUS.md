# UI-REF-12 — Live Chat Settings focus

Date: 2026-09-21  
Status: Repository validated

## Decision

The authenticated AiSensy Live Chat Settings screen and owner-approved capture 0047 were inspected
read-only. The product already had the applicable real behavior: local unread policy, governed
provider read receipts, first-window welcome replies, bounded off-hours replies, organization
working hours and protected inactivity resolution. The visible gap was that the Manage deep link
also exposed routing, consent and generic advanced settings.

The `#inbox-policy` destination now presents only Live Chat behavior. Read-state controls lead the
screen, followed by the existing automated-reply and working-hours editor, inactivity resolution
and one contextual save action. The broader Application settings route retains every original
control, so no authority or capability moved or duplicated.

## Reference boundary

Typing indicators are not represented by the current provider-neutral contract and therefore are
not shown as an executable-looking toggle. Reference launch cards, ads and AI shortcuts remain
excluded. Labels, component composition and styling remain original to the Vi design system.

## Validation

- PASS: focused Settings and navigation regression, 2 files / 130 tests.
- PASS: complete frontend, 63 files / 1,021 tests.
- PASS: TypeScript, ESLint and production build.
- PASS: no backend, OpenAPI, generated-client, migration, permission or dependency delta.
- PENDING – Host Machine Validation: authenticated local populated visual acceptance and
  mobile/browser matrix.

