# UI-REF-02 — Live Chat shell alignment

2026-09-13; local UI change, not full Live Chat or production certification.

Reference: ignored `0001_live_chat_active_full.png` and the supplied viewport states 1–3.
The approved Live Chat screen has search above an Active / Requesting / Intervened strip,
a conversation list, a central thread area and a right profile area. Those structures guide
this extension; captured source, illustrations, logos and assets are not imported.

## Changed

- Existing ConversationFilters moves above the workspace columns. Search precedes the strip
  in both visual and keyboard order. A screen-reader heading identifies Live Chat.
- Active / Requesting / Intervened appear in reference order with an underlined current view.
  Existing button semantics, keyboard activation and pressed state remain.
- These are the existing filters: open; pending; open assigned to the signed-in user. They do
  not invent chatbot ownership or claim other agents' conversations. Searches survive switching.
- Empty desktop view has list, central conversation area and a separate profile placeholder.
  The profile header is not shown over a selected thread whose Details panel may be closed.
- Advanced filters, saved views, pagination, bulk actions and the selected-thread composer,
  intervention/resolve, assignment and Details behavior remain in their existing authorities.
- Mobile keeps the list and controls; selecting a thread retains the existing Back behavior.

## Truthful boundaries

No grouped-count API is added, so no fabricated `(0)` totals. A bare URL retains the existing
all-status query and therefore does not falsely mark Active selected. No reference illustration
or fake customer is inserted. The existing no-results/error/loading/permission/saving states
are preserved. Empty preview means no conversation records exist in the isolated local fixture.

Selected-thread profile layout, full conversation/action parity, grouped totals, Intervened
subfilters, visual styling details, populated multi-agent journeys, full accessibility/device
acceptance and production commissioning remain open. The twenty-point screen DoD is not fully
certified. Contacts, Campaigns and detailed Manage forms remain separate pending comparisons.

## Verification

- PASS: frontend **47 files / 883 tests**, zero failures, final run 8.26s.
- PASS: TypeScript/production build; ESLint; changed-file whitespace checks.
- PASS: regression checks preserve filter mapping, search, view order and pressed state.
- PASS: authenticated desktop preview at 1440x900. Active writes `status=open`, Requesting
  writes `status=pending`, Intervened writes `status=open` plus the current user's assignee ID.
- PASS: 390x844 preview, no document-width overflow, advanced filters open/close with real
  status/assignee controls. Temporary viewport override reset; preview left open.
- PENDING – Host Machine Validation: populated end-to-end visual/interaction acceptance,
  complete device/screen-reader/contrast review and target-host production validation.

Screenshots: `output/previews/ui-ref-02-live-chat-desktop.png` and
`output/previews/ui-ref-02-live-chat-mobile.png`. These are actual local app states.

No backend, API, migration, permissions, dependencies or customer data changed. The separate
unfinished segment delta remains at migration 0062 (63 revisions), OpenAPI 235. This UI change
does not recertify its backend or historical Docker gates. Branch `ui/taste-modernization`,
baseline `1865f4b6657d644a247750949d8cae3f2aa28450`; no commit/push/deployment. Module estimates
are unchanged; neither the historical 77.0% nor frontend tests measure full AiSensy parity.
