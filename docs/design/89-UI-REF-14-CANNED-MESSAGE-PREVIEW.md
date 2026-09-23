# UI-REF-14 — Canned Message preview

Date: 2026-09-21  
Status: Repository validated

## Decision

The authenticated AiSensy New Canned Message screen and approved capture 0051 were inspected
read-only. The applicable interaction gap was a live message preview beside the existing creation
fields. The editor now renders the exact trimmed message body while the user types and explains the
existing insertion behavior when the body is empty.

The product's richer governed contract remains authoritative: shortcut, title, message body and
personal-or-organization scope are retained. Selecting a saved reply inserts it into the composer
and does not send it automatically.

## Reference boundary

Only text canned messages are supported by the current contract, so no fake media or message-type
selector was introduced. Variable substitution remains gated and absent. Reference marketing,
upgrade and excluded commercial surfaces remain absent. The UI uses original components and Vi
styling.

## Validation

- PASS: focused Settings regression, 2 files / 130 tests.
- PASS: complete frontend, 63 files / 1,021 tests.
- PASS: TypeScript, ESLint and production build.
- PASS: no backend, OpenAPI, generated-client, migration, permission or dependency delta.
- PENDING – Host Machine Validation: authenticated local populated visual acceptance and
  mobile/browser matrix.

