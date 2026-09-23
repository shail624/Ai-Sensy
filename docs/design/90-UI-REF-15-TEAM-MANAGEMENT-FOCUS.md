# UI-REF-15 — Team Management focus

Date: 2026-09-21  
Status: Repository validated

## Decision

The authenticated AiSensy Team Members screen and approved captures 0052–0053 were inspected
read-only. The applicable parity gap was naming and task hierarchy. The existing user workspace now
opens as Team Members, describes the add/access/sign-in job directly, and uses Add team member and
Create Team Member language for the primary creation flow.

The product's stronger governed account contract remains authoritative: administrator-created
credentials, custom roles, permission-aware reads and writes, explicit enable/disable, protection
against disabling the signed-in account and optimistic concurrency on edits remain intact.

## Reference boundary

Paid seat quotas, buying team members, billing and launch cards are excluded and were not added.
The reference role choices do not replace the live custom-role catalog. No invitation or SSO flow
was invented. The UI uses original components and Vi styling.

## Validation

- PASS: focused Administration/navigation regression, 2 files / 72 tests.
- PASS: complete frontend, 63 files / 1,022 tests.
- PASS: TypeScript, ESLint and production build.
- PASS: no backend, OpenAPI, generated-client, migration, permission or dependency delta.
- PENDING – Host Machine Validation: authenticated local populated visual acceptance and
  mobile/browser matrix.

