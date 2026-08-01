# Design Document 26 — CORE-01 Governed Navigation Shell

**Status:** Implemented and verified

**Milestone:** CORE-01

**Decision:** ADR-0013

**Quality gate:** ADR-0012 and Design Document 25

## 1. Boundary

CORE-01 finalizes the shared authenticated product shell only: desktop navigation, mobile
navigation, More, top-bar menus, workspace command palette, RBAC visibility, active states,
responsive behavior, and accessibility. Existing routes and module implementations are reused.
There is no new API, migration, domain model, permission, placeholder route, or duplicate module.

The ignored `.reference/aisensy/` archive is a private visual/workflow benchmark. It is not a source
of product requirements or implementation assets and is never committed or shipped.

## 2. Reference evidence reviewed

Before implementation and closeout, the following paired captures were opened and inventoried:

| Workflow | Full capture | Viewport capture | Relevant visible patterns |
|---|---|---|---|
| Live chat | `0001_live_chat_active_full.png` | `0001_live_chat_active_viewport.png` | compact persistent rail, active marker, triage/list/detail hierarchy, dense tool placement |
| Contacts/filtering | `0008_contacts_filter_full.png` | `0008_contacts_filter_viewport.png` | primary plus contextual navigation, top actions, compact filters, full-width table, bounded popover |
| Campaign creation | `0016_campaigns_create_csv_broadcast_full.png` | `0016_campaigns_create_csv_broadcast_viewport.png` | persistent rail, header/back action, progress hierarchy, centered form surface, disabled-state clarity |
| Template creation | `0044_manage_template_message_create_full.png` | `0044_manage_template_message_create_viewport.png` | contextual management hierarchy, compact form grouping, preview/action balance |
| Team member modal | `0053_manage_team_add_team_member_full.png` | `0053_manage_team_add_team_member_viewport.png` | dimmed context, bounded modal, stacked form organization, bottom-right actions |
| Developer webhooks | `0072_developer_tab_project_webhooks_full.png` | `0072_developer_tab_project_webhooks_viewport.png` | top guide, horizontal tabs, compact usage state, search/action row, factual empty state |

The reference inventory contained excluded Ads Manager, WhatsApp Payments, Billing & Usage,
purchase, marketplace, and project-switching actions. Those were explicitly rejected rather than
copied, hidden behind another label, or added as placeholders.

## 3. Existing capabilities mapped

| Requirement | Reused repository authority | CORE-01 completion |
|---|---|---|
| Destination catalogue | `components/layout/navigation.ts` | Added maturity and permanent scope guard; retained route order and permissions |
| Desktop rail | `Sidebar.tsx` | Original dark-green rail tokens, clearer active marker, grouped More panel, compact/expanded identity |
| Top actions | `TopNav.tsx` | Shared quick-create authority, dismissible menus, Escape and focus return, mobile ARIA state |
| Mobile shell | `AppLayout.tsx` | Four high-frequency items plus More, active secondary state, dialog semantics, focus trap/return |
| Workspace search | `CommandPalette.tsx` | Shared create actions, honest maturity, permission filtering, list semantics, live result announcement |
| RBAC | `AuthProvider`, route guards, route catalogue | Existing server-provided permissions remain authoritative; no parallel role model |
| Visual identity | `index.css`, Tailwind primitives, Lucide | Original VR identity and Vi tokens; no proprietary reference asset or exact value |

## 4. Workflow and visual parity

An experienced AiSensy user encounters the same broad interaction grammar: a narrow persistent rail,
strong active destination, dense workspace header, one advanced-navigation surface, top-aligned
create/search/account actions, bounded overlays, and responsive transformation instead of a generic
card-only dashboard. At 1280×720 the authenticated shell renders a 72px compact rail and a 288px
More panel without horizontal overflow. The command palette is a centered 672px bounded surface
with quick actions first, navigation results below, and keyboard guidance retained.

The rail’s dark-green hierarchy, subtle grouping, compact control sizes, status pills, and active
indicator improve scan speed while preserving the existing six-task primary loop. Module pages keep
their current loading, empty, error, and data states; CORE-01 does not replace real state with sample
content. Browser review intentionally used unavailable downstream services to prove the shell keeps
its hierarchy while factual error states are visible.

## 5. Intentional originality differences

- The mark, product name, icons, component code, copy, design tokens, color values, typography, and
  spacing are original Vi Reactivation work.
- The approved six-destination task rail is retained rather than copying the reference’s complete
  product menu or its ordering.
- Excluded Ads, Payments, Billing, marketplace, SaaS/multi-project, promotional, and commerce
  surfaces do not exist in navigation or search.
- Mobile uses an accessible bottom task bar and a left navigation dialog suited to this product,
  rather than reproducing any proprietary mobile treatment.
- `Foundation` and `Future` labels make domain maturity explicit; the reference does not govern Vi
  delivery claims.

## 6. Responsive and accessibility acceptance

- Desktop compact and expanded widths share the same catalogue and active-route computation.
- Mobile exposes Dashboard, Live Chat, Campaigns, Contacts, and More with minimum 44px targets.
- Secondary routes mark More as current; opening it exposes a modal navigation drawer.
- The drawer and command palette trap Tab focus, close with Escape, and return focus to the invoking
  control. Menu buttons expose `aria-expanded` and `aria-controls`.
- The route heading receives programmatic focus after navigation and the skip link remains first.
- Search results use list/listitem semantics rather than nesting buttons inside a listbox option.
- The command palette announces result count and current keyboard selection through `aria-live`.
- Focused tests cover mobile dialog controls and state because the available in-app browser session
  used a fixed desktop viewport. The repository Playwright viewport suite supplies browser-level
  responsive evidence.

## 7. Premium screen Definition of Done

| Check | Result |
|---|---|
| Approved route and workflow preserved | PASS |
| Existing backend/frontend capability reused | PASS |
| No fake data or placeholder destination | PASS |
| Reference full/viewport pair reviewed | PASS |
| Layout hierarchy and density compared | PASS |
| Original code and visual identity | PASS |
| Excluded concepts absent | PASS |
| RBAC visibility | PASS |
| Active/deep-route state | PASS |
| Desktop compact/expanded behavior | PASS |
| Mobile navigation behavior | PASS |
| Keyboard operation and focus return | PASS |
| Accessible labels/state/announcements | PASS |
| Loading/empty/error states remain factual | PASS |
| Light/dark token compatibility | PASS |
| Shared-component reuse | PASS |
| Focused automated regression | PASS |
| Browser visual comparison | PASS |
| OpenAPI and migration invariance | PASS |
| Governance synchronized | PASS |

## 8. Remaining visual gaps

- The in-app browser available during closeout was fixed at 1280×720, so mobile visual comparison
  is backed by component tests and the Playwright viewport suite rather than an in-app screenshot.
- Further route-specific visual convergence belongs to each approved module milestone; CORE-01 does
  not restyle or claim completion for unchanged module content.
- The production bundle retains the known large-main-chunk warning; this milestone does not change
  route-level performance architecture.
