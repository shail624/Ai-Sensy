# UI-REF-16 — Tags first-message column

Date: 2026-09-21  
Status: Repository validated

## Decision

The authenticated AiSensy Tags screen and approved capture 0054 were inspected read-only. The
applicable information-hierarchy gap was that the reference exposes first-message behavior as a
dedicated table fact. The Tags table now separates Tag name and First message, showing the real
rule state and exact-match keyword count instead of burying it below the tag description.

The existing governed contract remains authoritative: name, colour, description, maintained usage
count, create/edit/delete, exact-match first-message rules and permission-aware actions are
unchanged.

## Reference boundary

Tag categories/groups are not part of the current contract and were not faked. Launch cards, ads,
billing and other excluded commercial surfaces remain absent. The UI uses original components and
Vi styling.

## Validation

- PASS: focused Settings/navigation regression, 2 files / 130 tests.
- PASS: complete frontend, 63 files / 1,022 tests.
- PASS: TypeScript, ESLint and production build.
- PASS: no backend, OpenAPI, generated-client, migration, permission or dependency delta.
- PENDING – Host Machine Validation: authenticated local populated visual acceptance and
  mobile/browser matrix.

