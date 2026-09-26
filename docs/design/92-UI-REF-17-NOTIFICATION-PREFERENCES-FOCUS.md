# UI-REF-17 — Notification Preferences focus

Date: 2026-09-21  
Status: Repository validated

## Decision

The authenticated AiSensy Notification Preferences screen and approved capture 0055 were inspected
read-only. The applicable navigation gap was that real per-user notification-category controls
were available only inside the notification centre. The personal settings route is now a dedicated
Notification Preferences workspace that exposes those server-synced category controls first and
preserves the existing advanced personal preference store below them.

Category choices save immediately, apply only to the signed-in user and continue to use the real
notification settings contract. Hidden items remain recorded and can reappear unread when their
category is restored.

## Reference boundary

Sound, browser push and device enrolment are not implemented and remain undecided/gated, so no fake
toggles, device list or success state was added. Reference launch cards, ads and commercial surfaces
remain absent. The UI uses original components and Vi styling.

## Validation

- PASS: focused Settings/notifications/navigation regression, 3 files / 139 tests.
- PASS: complete frontend, 63 files / 1,022 tests.
- PASS: TypeScript, ESLint and production build.
- PASS: no backend, OpenAPI, generated-client, migration, permission or dependency delta.
- PENDING – Host Machine Validation: authenticated local populated visual acceptance and
  mobile/browser matrix.

