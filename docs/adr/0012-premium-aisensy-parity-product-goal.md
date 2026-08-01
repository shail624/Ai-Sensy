# ADR-0012: Premium AiSensy-Parity Product Goal

- **Status:** Accepted
- **Date:** 2026-08-02
- **Milestone:** GOV-02
- **Decision owners:** Product owner and repository governance

## Context

The repository already contains substantial enterprise WhatsApp and Vi Reactivation capability.
The remaining work needs one durable quality target so that functional completion does not produce
generic pages, disconnected shells, invented data, or inconsistent interaction patterns.

The owner has approved AiSensy as a private visual and workflow benchmark for the included product
areas. That approval does not authorize copying AiSensy's implementation, branding, assets, design
tokens, text, or excluded product surfaces.

## Decision

The permanent product goal is an original, private, enterprise-grade WhatsApp Business Platform for
the Vi Reactivation Team, with workflow depth, usability, reliability, and visual quality comparable
to or better than AiSensy and presentation appropriate to an approximately ₹50,000-per-month
enterprise product.

Functionality and presentation are equally mandatory. A workflow that works but is visually
generic, inconsistent, inaccessible, or operationally unclear is not complete. A polished screen
that is not backed by real authorized state is also not complete.

Implementation will:

1. Preserve approved navigation, workflows, information density, and operational familiarity while
   using original code, branding, components, assets, colors, typography, spacing, and layouts.
2. Prefer existing shared components and extend them when necessary; a module must not create a
   parallel primitive where a governed shared primitive can satisfy the requirement.
3. Use only real backend state in production. Empty states must be honest. Unavailable actions must
   be absent, visibly disabled with an explanation, or clearly marked as future scope.
4. Apply the premium screen Definition of Done in
   `docs/design/25-PREMIUM-PRODUCT-EXPERIENCE-STANDARD.md` to every new or materially changed screen.
5. Permit continuous quality improvements within an approved milestone when they are local,
   reusable, tested, do not change architecture or product scope, and do not conceal incomplete
   functionality. Broader redesigns require separate owner approval.

## Reference-versus-copying boundary

The owner-approved local capture library is a benchmark only. It is stored under Git-ignored
`.reference/aisensy/`, never staged or committed, and never imported into a build. Captured HTML,
MHTML, JSON, images, text, code, assets, design tokens, and brand identity must not be copied into
the product.

Approved reference categories are Live Chat, Contacts, Campaigns, Template Message, Opt-in, Live
Chat Settings, Attributes, Canned Messages, Team, Tags, Notifications, and Developer/API/Webhooks.
AI and Automation captures are conditional and may be reviewed only within their separately
approved milestones. Ads, payments, billing, subscriptions, trials, upgrades, marketplace,
multi-project, reseller, catalog, cart, checkout, orders, refunds, and other commerce captures are
prohibited implementation targets.

## No-placeholder decision

Production routes must not contain fabricated records, metrics, success states, executable-looking
controls, or mock integrations. Sample data is limited to tests, Storybook, and explicitly labelled
development/demo fixtures. A route shell does not count as module completion.

## Consequences

- Roadmap milestones retain their approved scope but acquire a mandatory premium experience gate.
- Module completion percentages do not increase from visual polish alone.
- Reference comparison records become review evidence, not product assets.
- Existing architecture, RBAC, tenant isolation, audit, timeline, generated contracts, migrations,
  and real service authorities remain binding.
- The current exclusions remain permanent unless the owner explicitly changes product scope.

## Rejected alternatives

- **Pixel-copying AiSensy:** rejected for originality, maintainability, licensing, and identity
  reasons.
- **Function-first with deferred UX:** rejected because workflow clarity and presentation are part
  of enterprise acceptance.
- **Polished placeholders:** rejected because they misrepresent system capability and state.
- **Per-module component systems:** rejected because they create drift and compound maintenance.
