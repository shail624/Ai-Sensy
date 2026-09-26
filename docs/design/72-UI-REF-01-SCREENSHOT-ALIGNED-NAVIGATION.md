# UI-REF-01 — Screenshot-aligned navigation

2026-09-13. Local implementation, not a released or owner-accepted full-parity milestone.

## Owner direction

The owner reaffirmed that supplied AiSensy screenshots, tabs, buttons and layouts are the target,
alongside the Vi features. An unrelated polished dashboard is not sufficient. Approved screen
organization should match closely; code, logo, assets, authentication and domain authorities stay
repository-owned. Captured HTML/MHTML/assets are never imported or bundled.

This change covers shared navigation and Settings entry points, not every AiSensy feature.
Earlier excluded ads, payments, SaaS billing and marketplace modules have not been added.
Literal all-product parity conflicts with those earlier exclusions and is not claimed.

## Reference comparison

Reviewed the ignored capture gallery/index and supplied Live Chat viewport, Campaigns full
capture and Tags full/viewport pair: `0001_live_chat_active_viewport.png`,
`0010_campaigns_tab_all_full.png`, `0054_manage_tags_create_full.png` and
`0054_manage_tags_create_viewport.png`. The archive has 73 states, not 73 verified matches.

| Area | Implemented here | Remaining difference |
|---|---|---|
| Daily navigation | 84px icon-and-caption rail; Dashboard, Live Chat, History, Contacts, Campaigns, Flows, Manage | Repository-owned brand/icons/tokens; excluded product destinations are absent |
| Manage | Persistent adjacent panel; Template Message, Opt-in Management, Live Chat Settings, User Attributes, Canned Messages, Team, Tags, Analytics | Contacts & Campaigns settings and dedicated notification-preference screen remain unmatched |
| Settings | Active section heading; duplicate desktop tab row hidden, mobile tabs retained | Detailed reference forms and buttons are not matched by this shell change |
| Consent/chat policy | Deep links scroll and focus real existing controls; saves/validation unchanged | Entry points share the existing editor, not separate fully matched forms |
| Vi tools | Reactivation, segments, tasks, downloads, media, pipelines, channels and administration remain reachable | Their detailed workflows still require individual acceptance |
| Live Chat | Updated shared rail | Tab-strip hierarchy, three columns and selected/empty/action states need comparison |
| Contacts/Campaigns | Updated shared rail | Filter/action menus, forms, launch controls, reports and tables need comparison |

## Implementation contract

Extends Sidebar, AppLayout, navigation metadata, SettingsPage and ApplicationPanel; reuses
Settings/Admin permissions. No backend API, model, migration, permission, UI primitive or
production fixture was added. Specific/hash links have one current destination. Route changes
reveal Manage. Escape closes it and restores focus; Right Arrow enters it. Mobile keeps its
focus-managed drawer and explicit close. Captions and honest foundation/future labels remain.

The v4 browser preference defaults to compact. Users can still expand and save that choice.
The old v3 value was automatically written as an expanded default and was not reliable evidence
of an explicit preference. No customer record or production setting was changed. The isolated
local preview-owner credential was refreshed only in the disposable preview database.

Existing loading, empty, error, permission, validation, pending, success and destructive
confirmation behavior remains in the domain components. Navigation does not invent success.
Preview tags are genuinely empty and policy uses server defaults; clicking a consent link does
not save policy. No reference illustration, branding or captured code is bundled.

## Evidence

- PASS: full frontend **47 files / 882 tests**, zero failures, 7.69s.
- PASS: TypeScript, ESLint and production build. Existing mixed-import warnings remain.
- PASS: direct-link focus, visible compact captions, Manage order, unique destinations,
  permission filtering, active hash selection, keyboard entry/close and focus restoration tests.
- PASS: authenticated 1440x900 desktop Tags/navigation; consent receives focus and is the only
  current Manage item; document width equals viewport width.
- PASS: 390x844 mobile drawer, focus on Close navigation, explicit close and no document overflow.
- PASS: 768x1024 tablet Tags page loaded with visible heading, section navigation and controls;
  document width is 768px with no horizontal document overflow. Temporary viewport override reset.
- PENDING – Host Machine Validation: populated workflow comparisons, full device/screen-reader/
  contrast matrix, owner acceptance and all-screen/button/workflow parity. The full twenty-point
  screen Definition of Done is not certified by these bounded checks.

Actual screenshots: `output/previews/ui-ref-01-manage-desktop.png` and
`output/previews/ui-ref-01-manage-mobile.png`.

GitHub/local baseline: `1865f4b6657d644a247750949d8cae3f2aa28450`, branch
`ui/taste-modernization`, verified read-only. No commit, push or deployment.
Separate unfinished GROW-03 segment changes at `0062_segment_domain_predicates` remain in the
worktree; OpenAPI remains 235 paths. Two optional-array typing errors in its tests were corrected
without weakening assertions. Prior focused evidence: 15 backend and 69 segment-UI tests.
Old PAR-VIEW-05 full-backend/static and prior Docker gates do not certify the cumulative tree.

## Next acceptance work

Live Chat states 1–3, Contacts 4–9, Campaigns 10–17, then Manage 44–55. Inventory each tab,
button, form and backend behavior and compare actual desktop/mobile screenshots. Missing
functionality remains a gap, not a decorative button. No module percentage increases here:
the historical **77.0% approved-scope estimate is not screenshot parity**.
