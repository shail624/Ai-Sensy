# Premium Product Experience Standard

**Status:** Approved governance standard

**Milestone:** GOV-02

**Authority:** `VI_REACTIVATION_FINAL_PRODUCT_SCOPE.md` and ADR-0012

## Experience principles

1. **Operational truth first.** Every value, count, status, permission, and action reflects real
   authorized state.
2. **Workflow familiarity.** Approved AiSensy references inform task order, density, discoverability,
   and state transitions, while the product keeps an original identity and implementation.
3. **Enterprise clarity.** Primary actions, ownership, stage, risk, SLA, and next steps are apparent
   without interpretation.
4. **Progressive disclosure.** Frequent work stays immediately available; advanced controls remain
   discoverable without crowding the default path.
5. **One component language.** Shared primitives, tokens, states, and responsive behavior apply
   across modules.
6. **Accessible by default.** Keyboard, focus, semantics, contrast, touch targets, reduced motion,
   and screen-reader names are design inputs, not release cleanup.
7. **Resilient feedback.** Loading, empty, error, partial, stale, offline, disabled, and success
   states explain what is happening and what the user can do next.

## Approved reference review process

Before implementing or materially changing an approved screen, the milestone record must:

1. Confirm that the screen belongs to the final product scope.
2. Confirm its reference category is approved for the active milestone.
3. Review `capture_gallery.html` and `capture_index.json` from the ignored local library.
4. Review the `_full.png` capture for complete hierarchy and page flow.
5. Review the `_viewport.png` capture for density, visible actions, and interaction emphasis.
6. Use rendered HTML/MHTML and metadata only to understand semantics and states.
7. Inventory the screen's user goal, entry points, primary action, secondary actions, filters,
   table/list/form structure, state transitions, and exit paths.
8. Record loading, empty, error, disabled, permission-denied, success, and destructive states.
9. Map every observed behavior to an approved requirement and real repository capability.
10. Remove prohibited, promotional, SaaS, payment, billing, marketplace, and commerce concepts.
11. Search the repository for reusable layouts, primitives, and domain components before designing.
12. Produce an original interaction and visual treatment using repository-owned tokens and assets.
13. Compare the implementation at matched desktop and mobile viewports for hierarchy and usability,
    not pixel identity.
14. Record differences, accessibility evidence, responsive evidence, backend-state evidence, tests,
    and the premium screen Definition of Done result.

Each comparison record identifies: milestone; product route; reference filenames; approved
requirements; patterns retained; patterns rejected; original design decisions; shared components;
real data sources; loading/empty/error/permission behavior; desktop/mobile findings; accessibility
findings; test evidence; unresolved limitations; and reviewer approval.

## Reference classification

- **Approved now:** captures 1–17, 44–55, and 70–73 for their in-scope workflow categories.
- **Conditional:** captures 19–20 only in an approved AI milestone; captures 32–34 only in an
  approved Automation milestone.
- **Prohibited:** capture 18; captures 21–31, 35–43, and 56–69. They are classification evidence
  only and must not become layout, workflow, copy, or feature targets.

The local `.reference/aisensy/` directory is ignored, never committed, never bundled, and never an
implementation source. No captured code, text, assets, branding, tokens, or layouts may be copied.

## GOV-02 reference inventory record

GOV-02 indexed `capture_gallery.html`, `capture_index.json`, and the paired `_full.png` and
`_viewport.png` assets for all 73 captured states. It used rendered HTML/MHTML and JSON only for
semantic/state classification. Representative viewport captures visually reviewed for the quality
standard were `0001_live_chat_active_viewport.png`, `0008_contacts_filter_viewport.png`,
`0016_campaigns_create_csv_broadcast_viewport.png`, `0053_manage_team_add_team_member_viewport.png`,
and `0072_developer_tab_project_webhooks_viewport.png`.

The approved state stems registered for future milestone-specific full/viewport review are:

- `0001_live_chat_active`, `0002_live_chat_requesting`, `0003_live_chat_intervened`;
- `0004_contacts_add_contact`, `0005_contacts_import_menu`, `0006_contacts_import_contacts`,
  `0007_contacts_actions_menu`, `0008_contacts_filter`, `0009_contacts_create_segment`;
- `0010_campaigns_tab_all`, `0011_campaigns_tab_broadcast`, `0012_campaigns_tab_api`,
  `0013_campaigns_tab_scheduled`, `0014_campaigns_tab_qrscan`,
  `0015_campaigns_create_api_campaign`, `0016_campaigns_create_csv_broadcast`, and
  `0017_campaigns_create_qr_campaign`;
- `0044_manage_template_message_create`, `0045_manage_optin_add_more`,
  `0046_manage_optin_configure`, `0047_manage_live_chat_settings_configure`,
  `0048_manage_user_attributes_tab_contact_attributes`,
  `0049_manage_user_attributes_tab_form_attributes`, `0050_manage_user_attributes_add_attribute`,
  `0051_manage_canned_message_create`, `0052_manage_team_manage_team_members`,
  `0053_manage_team_add_team_member`, `0054_manage_tags_create`, and
  `0055_manage_notification_preferences_add_device`;
- `0070_developer_tab_api_campaign_key`, `0071_developer_tab_project_api_keys`,
  `0072_developer_tab_project_webhooks`, and `0073_developer_tab_documentation`.

Conditional stems `0019_campaigns_quick_generate_ai_template`,
`0020_campaigns_quick_create_ai_agent`, and `0032_flows_tab_your_flows` through
`0034_flows_tab_test_numbers` were classified but not adopted as current targets. Prohibited state
18, states 21–31, 35–43, and 56–69 were classified only to enforce exclusions and were not used as
workflow or visual targets.

No application route was changed in GOV-02, so component/backend reuse, workflow parity,
responsive implementation, accessibility implementation, and tests-added fields are not applicable
to a product screen in this record. Those fields are mandatory in the affected milestone's own ADR
or design comparison record.

## Shared enterprise component catalogue

Before adding a component, inspect and reuse or extend the established repository primitive for:

- application shell, navigation rail, page header, breadcrumbs, command palette, and global search;
- data table, compact list, card grid, Kanban, pagination, sorting, filters, saved views, bulk actions,
  and selection state;
- tabs, segmented controls, stepper, timeline, activity feed, status badge, SLA indicator, and owner
  identity;
- form fields, field groups, validation summaries, search/combobox, date/range controls, uploads,
  drawers, dialogs, confirmation, and destructive actions;
- metric cards, charts, legends, comparisons, report controls, and export/download status;
- skeletons, progress, empty states, inline errors, banners, toasts, retry controls, and unavailable
  capability notices;
- permission boundaries, approval state, audit evidence, sensitive-data reveal, and redaction;
- responsive tables/cards, mobile drawers, touch actions, focus management, and keyboard shortcuts.

New primitives require a documented gap, reusable API, accessibility contract, state coverage, and
tests. A one-off visual variation is not a sufficient reason.

## State and data standard

- Loading preserves page structure and does not present zeros as facts.
- Empty states distinguish “no records,” “no results for these filters,” and “not yet configured.”
- Errors retain user input where safe, identify the failed operation, and provide a valid recovery.
- Disabled actions explain the missing permission, prerequisite, or state when disclosure is safe.
- Optimistic changes expose pending and rollback behavior; irreversible actions require explicit
  confirmation.
- Live counts and timelines use backend-owned facts and refresh without inventing interim success.
- Sample data exists only in tests, Storybook, or clearly labelled development/demo environments.

## Responsive and accessibility acceptance

Every changed route is reviewed at the repository's supported desktop, tablet, and mobile widths.
Content order, primary actions, filters, tables, drawers, dialogs, and overflow behavior must remain
usable. Keyboard-only completion, visible focus, logical focus restoration, semantic headings,
labelled controls, error association, status announcements, contrast, touch targets, zoom/reflow,
reduced motion, and screen-reader names are required.

## Premium screen Definition of Done

A screen passes only when all twenty checks pass or a limitation is truthfully recorded and owner-
approved:

1. It maps to an approved final-scope requirement.
2. Its data comes from real backend contracts and authorized state.
3. Its primary user goal and next action are unambiguous.
4. Navigation, title, hierarchy, and information density are consistent.
5. Existing shared components were reused or extended.
6. No copied AiSensy code, assets, branding, text, tokens, or layout is present.
7. No excluded or milestone-gated feature is exposed.
8. Loading behavior is intentional and non-deceptive.
9. Empty and no-result states are distinct and helpful.
10. Error and retry behavior is actionable.
11. Disabled and permission-denied behavior is truthful.
12. Success, pending, stale, and destructive states are explicit.
13. Forms preserve input, validate clearly, and prevent accidental duplicate actions.
14. Tables/lists/Kanban support the required density, filters, selection, and overflow.
15. Desktop, tablet, and mobile layouts pass the supported viewport review.
16. Keyboard, focus, semantics, contrast, announcements, and touch targets pass accessibility review.
17. RBAC, tenant isolation, audit, timeline, and sensitive-data handling remain intact.
18. Relevant unit, integration, contract, component, and journey tests pass.
19. Performance budgets, bounded queries, pagination, and rendering behavior remain acceptable.
20. The reference comparison record and governance ledgers are complete and truthful.

## Continuous quality boundary

An approved feature milestone may include small, directly related quality corrections that improve
shared consistency, accessibility, responsive behavior, error handling, or reuse. Such corrections
must remain inside the milestone's routes/components, preserve architecture and contracts, and be
tested. Cross-product redesigns, new product behavior, dependency/platform migrations, or changes to
scope require their own approved milestone.
