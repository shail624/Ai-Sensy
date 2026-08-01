# ADR-0013: Governed Navigation Shell

- **Status:** Accepted
- **Date:** 2026-08-02
- **Milestone:** CORE-01
- **Supersedes:** Nothing
- **Extends:** ADR-0012 and Design Documents 05, 20, 21, and 25

## Context

The repository already had a responsive application shell, complete route catalogue, permission
guards, workspace search, and six-item task rail. CORE-01 had to make that foundation final without
recreating routes or implying that incomplete product domains were complete. The approved private
AiSensy captures provide a workflow-density benchmark only. They also contain Ads, Payments,
Billing, marketplace, multi-project, and commerce concepts that are outside the approved Vi scope.

## Decision

1. `navigation.ts` remains the canonical signed-in destination catalogue. The primary rail keeps
   the completed six-item order: Dashboard, Live Chat, Contacts, Campaigns, Templates, Analytics.
2. Every other entitled destination is available through one grouped **More** surface and workspace
   search. Mobile keeps the four highest-frequency destinations plus More.
3. Navigation, search, and create actions are filtered by the authenticated permission catalogue.
   Superuser behavior continues to be owned by `AuthProvider`; the shell does not invent roles.
4. The shared create catalogue owns Campaign, Template, and Contact Import actions so the top bar
   and command palette cannot drift.
5. Approved foundations are labelled `Foundation`; the compliance-gated Scan Studio is labelled
   `Future`. No unavailable route is presented as a completed product.
6. A permanent exclusion guard rejects Ads Manager, Meta Ads, Payments, Billing, subscriptions,
   marketplace, public-signup/reseller/multi-project, catalog, cart, checkout, order, refund, and
   commerce navigation concepts. Route registration remains independently permission guarded.
7. The original Vi Reactivation shell uses its own VR mark, icons, language, spacing, and dark-green
   design tokens. No reference HTML, CSS, JavaScript, logo, screenshot, exact icon, exact color,
   typography, wording, or pixel value is imported.
8. Desktop rail collapse, More, create/account menus, command palette, and mobile navigation are
   keyboard operable. Dialogs trap focus, close on Escape, restore focus, expose state through ARIA,
   and maintain 44px minimum mobile targets.
9. CORE-01 adds no API path, migration, persisted data, permission, or backend behavior.

## Consequences

- Modules reuse one navigation and quick-action authority instead of maintaining local lists.
- Adding a route requires an approved scope decision, a real route, appropriate permission, honest
  maturity, and an exclusion-guard test.
- The compact rail has familiar hierarchy and density while remaining an original Vi design.
- Future module completion can replace a maturity label in place; it must not create a duplicate
  destination.

## Verification

- Focused navigation/RBAC/keyboard/mobile tests cover the catalogue, exclusions, menus, active
  states, focus return, and responsive drawer.
- TypeScript, ESLint, Vitest, Playwright, production build, OpenAPI drift, migration, backend, and
  infrastructure results are recorded in `VALIDATION_RESULTS.md`.
- The screen-by-screen comparison and originality record is Design Document 26.
