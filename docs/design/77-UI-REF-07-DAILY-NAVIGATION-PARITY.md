# UI-REF-07 — Daily navigation parity

Date: 2026-09-20

## Observed reference

The owner opened the authenticated reference dashboard. Its permitted navigation includes
Dashboard, Live Chat, History, Contacts with Segments, Campaigns, Flows, Manage and Developer.
Ads, payments, billing, referrals, upgrades, marketplace/store and multi-project surfaces remain
excluded by product scope.

## Implementation

- Segments is now a visible daily rail destination beside Contacts rather than being discoverable
  only through Manage.
- Developer is now a direct permission-gated rail destination to the existing API credential
  surface. The underlying Operations destination remains available for broader system operators.
- The compact rail retains icon-and-caption navigation, original Vi identity, truthful maturity
  badges, keyboard behavior and RBAC filtering.
- Rail expansion now animates its width and honors reduced-motion preferences. The adjacent Manage
  panel has clearer visual separation without changing its focus, Escape or route behavior.
- No route, API, model, permission, migration, placeholder or captured asset was added.

## Deliberate non-matches

AI Agent and Lists were observed but are not added as navigation placeholders: the repository has
no approved autonomous-agent service or standalone static-list domain. Excluded commercial
surfaces remain absent. The internal operational dashboard remains Vi-specific because the
reference dashboard is dominated by SaaS onboarding, plan and promotional content.

## Validation

- PASS: focused navigation/layout suite, 34/34.
- PASS: full frontend, 61 files / 1,013 tests.
- PASS: TypeScript, ESLint and production build.
- PENDING – Host Machine Validation: authenticated local desktop/mobile visual comparison with
  representative tenant permissions and data.
