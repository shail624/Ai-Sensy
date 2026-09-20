# Document 85 — CORE-10 Chat History Acceptance

## Reconciliation result

The dedicated read-only Chat History workspace, bounded conversation/message retrieval, advanced
filters, organization-shared views, audit deep link, Live Chat handoff and governed transcript
exports already exist. CORE-10 does not create a second history query or duplicate those workflows.

## Authenticated reference observation

The permitted AiSensy History surface was inspected in the owner's authenticated browser. Its
primary pattern is a searchable conversation list with compact filter actions, circular contact
identity, last-message preview and a selected conversation detail. The existing internal product
already follows that interaction and offers additional governed filters and exports.

## Decision

Close the remaining repository-visible hierarchy gap by adding a derived contact initial and a
clear selected-row rail to the existing list. The initial is derived from the already-displayed
contact label and is decorative, so it adds no data contract or assistive-technology noise.

No reference count badge is copied: the conversation contract does not expose an equivalent
historical message count, and presenting the shared unread counter as that fact would be misleading.

## Scope boundary

- No new endpoint, query authority, permission, migration or generated type.
- No mutation controls in the read-only History workspace.
- No fake message count, unsupported filter or duplicate export flow.
- No changes to Live Chat polling or write behavior.

## Host acceptance boundary

The local UI server was opened successfully, but authenticated representative-data preview was
blocked because this host has no running MySQL service. Automated representative-fixture, route,
responsive, focus, accessibility, filtering, pagination and export coverage remains the repository
evidence. Live MySQL/browser-matrix and production-scale query commissioning remain release gates.
