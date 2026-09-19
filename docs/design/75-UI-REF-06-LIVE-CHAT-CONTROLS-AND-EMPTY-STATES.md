# UI-REF-06 — Live Chat controls and empty states

Date: 2026-09-20

## Scope

This milestone closes the five local differences recorded by UI-REF-05 for the approved Live Chat
empty state. The implementation remains original and preserves the existing Inbox contract,
category semantics, permissions, filters, pagination, assignment, sending and profile authorities.

- The advanced-filter trigger is compact and icon-only, with its purpose retained as an accessible
  name and tooltip.
- Search has a filled circular action. It focuses the search field when empty and becomes the
  existing clear action when a query is present.
- A desktop-only control collapses and restores the conversation-list column. Mobile behavior is
  unchanged.
- The empty list uses an original product icon composition through the governed EmptyState
  component.
- The unselected conversation pane uses an original token-driven dot ground; no reference asset,
  code, colour, illustration or pattern was copied.

## Verification

- PASS: focused Inbox tests, 33/33.
- PASS: complete frontend suite, 61 files / 1,012 tests.
- PASS: TypeScript, ESLint and production build.
- PASS: changed-file whitespace check.
- PENDING – Host Machine Validation: the local production preview reached the truthful sign-in
  boundary, but no authenticated local browser session was available for populated visual review.

No backend, API, migration, permission, dependency, customer data, excluded surface or module
percentage changed. Full Live Chat populated-flow, browser/device and target-host acceptance remain
open.
