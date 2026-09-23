# UI-REF-11 — Opt-in Management focus

Date: 2026-09-21  
Status: Repository validated

## Decision

The authenticated AiSensy Opt-in Management screen was inspected read-only and compared with the
owner-approved captures 0045 and 0046. This product already had the stronger functional contract:
exact whole-message opt-in and opt-out keyword rules, independent acknowledgements, validation,
audit evidence and post-record delivery. The remaining gap was presentation: the Manage deep link
opened those controls inside the wider Inbox operations and advanced-settings workspace.

The `#consent` destination now presents a dedicated consent workspace. It keeps the existing
server-owned policy and save operation, but leads with the enable control, pairs opt-in and opt-out
keyword fields, gives each acknowledgement an editable customer preview, and hides unrelated
routing, hours, automatic-resolution and advanced-store controls on this destination. The broader
Application settings route is unchanged.

## Reference boundary

The reference's launch shortcuts, ads, premium report and API-campaign opt-out are not reproduced.
They are excluded, gated, or unsupported by this product's approved contract. No fake tab, button,
metric or success state was added. Labels and implementation are original and use the existing Vi
design system.

## Validation

- PASS: focused Settings and navigation regression, 2 files / 129 tests.
- PASS: complete frontend, 63 files / 1,020 tests.
- PASS: TypeScript, ESLint and production build.
- PASS: no backend, OpenAPI, generated-client, migration, permission or dependency delta.
- PENDING – Host Machine Validation: authenticated local representative-data visual acceptance and
  mobile/browser matrix.

