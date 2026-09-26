# UI-REF-10 — Template creation focus

## Decision

Template creation keeps the existing original split editor and live preview as the primary work
surface. The Vi AI template helper remains available but is collapsed by default in a clearly
optional disclosure, matching the focused form-and-preview hierarchy observed in the approved
reference without removing a Vi capability.

## Scope boundary

- Change only the new/clone template route presentation.
- Keep the editor, live preview, validation, draft save, Meta submission and clone behavior intact.
- Reuse the same accessible disclosure pattern as campaign creation.
- Do not copy reference branding, styling tokens or marketing text.

## Deliberately absent

Template TTL remains an open, gated product decision. Billing/credit content and commercial
upgrade surfaces are excluded. This milestone makes no backend, OpenAPI, migration, permission,
template lifecycle or provider behavior change.

## Acceptance evidence

- Focused Template/page regression: 4 files / 62 tests pass.
- Full frontend: 63 files / 1,018 tests pass.
- TypeScript, ESLint and the Vite production build pass.
- Authenticated representative-data desktop/mobile visual acceptance remains host work.
