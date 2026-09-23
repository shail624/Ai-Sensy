# UI-REF-18 — Developer API Keys focus

Date: 2026-09-21  
Status: Repository validated

## Decision

The authenticated AiSensy Developer Hub and approved captures 0070–0073 were inspected read-only.
The applicable navigation gap was that the direct Developer entry opened under a generic Operations
heading and exposed unrelated operational tabs. The API-credential deep link now opens as a focused
Developer Hub, identifies the workspace as Project API keys and uses a direct Create API key action.

The existing governed credential behavior remains authoritative: permission-gated access, named
keys, scopes, optional expiry, one-time secret display, state and last-use facts, rotation/revocation
and audit integration are unchanged.

## Reference boundary

API-triggered campaigns are architecturally separate and remain gated. Outbound project webhooks
are not implied by inbound WhatsApp webhook operations and were not faked. The generated OpenAPI
contract remains authoritative; no competing documentation definition or portal was created. The UI
uses original components and Vi styling.

## Validation

- PASS: focused foundations/Admin/Operations regression, 3 files / 103 tests.
- PASS: complete frontend, 63 files / 1,022 tests.
- PASS: TypeScript, ESLint and production build.
- PASS: no backend, OpenAPI, generated-client, migration, permission or dependency delta.
- PENDING – Host Machine Validation: authenticated local populated visual acceptance and
  mobile/browser matrix.

