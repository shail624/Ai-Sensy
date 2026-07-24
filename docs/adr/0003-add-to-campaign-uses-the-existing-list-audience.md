# ADR-0003 — "Add to campaign" reuses the existing list audience; no backend extension

- **Status:** Accepted (frontend wiring not yet implemented)
- **Scope:** contacts bulk actions (Doc 05 B3.1), campaigns
- **Backend change:** **none**

## Context

B3.1 lists "add to campaign" among the contact bulk actions. It was left out of increment 3 because
`BULK_ACTIONS` is `add_tags | remove_tags | set_attributes`, and the standing invariant forbids
shipping a control with nothing behind it. That reasoning was right about `/contacts/bulk-update`
and wrong about the platform: the capability exists on the campaign side.

## What the backend already provides

- `AudienceRef` (frozen contract) carries `segment_id`, `tag_ids` **and `contact_ids`**.
- `audience_type` accepts `segment | tag | list | upload`.
- `AudienceService._from_list()` resolves `audience_ref.contact_ids` to active contacts and fails
  loudly when any id does not resolve (`"N of M resolved"`), so a stale selection cannot silently
  shrink an audience.
- `PATCH /campaigns/{id}` accepts a new `audience_ref` under `row_version` optimistic concurrency and
  refuses a campaign that is past editing (`"A {status} campaign cannot be edited."`).
- The campaign wizard's audience step **already** renders a `list` audience with a contact picker
  built on the shared contact search.

Nothing is missing. There is no job to add, no queue to reuse, and no endpoint to write.

## Decision

Wire the action to the endpoints that exist, in two paths:

1. **New campaign from this selection** — hand the selected ids to the existing campaign wizard as a
   pre-seeded `list` audience. `POST /campaigns` also requires `phone_number_id` and `template_id`,
   which the wizard already collects; re-asking for them inside a contacts dialog would duplicate it.
2. **Add to an existing draft** — list the campaigns that are still editable, then `PATCH` the chosen
   one with the union of its current `contact_ids` and the selection, passing `row_version`. A 409
   surfaces as "someone changed this campaign, reload", which is what the concurrency guard means.

The action is gated on `campaigns:write`, which is what the API enforces; without it the button is
absent, as with every other bulk action.

## Alternatives rejected

- **A fourth `BULK_ACTIONS` verb (`add_to_campaign`).** A parallel workflow for something the campaign
  API already models, and it would put audience composition behind the contacts service.
- **Creating a segment from the selection.** Segments are rule-based; a frozen id list is exactly what
  `audience_type: "list"` is for.

## Consequences

- Closes the B3.1 gap with frontend work only (~half a day: dialog, campaign picker, merge + PATCH).
- Only draft/editable campaigns can be extended — a running campaign's audience stays frozen, which
  is the behaviour the dispatch engine depends on.
- The 409 path needs a visible message; the bulk dialog already has the shape for it.
