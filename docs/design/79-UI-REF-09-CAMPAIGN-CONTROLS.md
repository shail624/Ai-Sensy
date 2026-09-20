# UI-REF-09 — Campaign list controls

## Decision

The Campaign list gains the supported reference interactions without presenting capabilities the
product does not own. `All` and `Scheduled` are direct, URL-backed status shortcuts. The complete
status selector remains available for the richer existing lifecycle. Refresh re-runs the current
server query. Export-authorized users can open the existing Campaign-filtered Download Center, and
campaign writers see a single `Launch campaign` action.

## Scope boundary

- Reuse the existing campaign list, server `q`/`status` contract, saved views and Download Center.
- Preserve the search term, sort and other URL state when a category shortcut changes status.
- Reset local page state when changing category, matching all other filter changes.
- Keep all controls permission-aware and usable at compact widths.

## Deliberately absent

`Broadcast` is not duplicated because it would be identical to `All`. API-triggered and QR-origin
campaigns have no approved domain model, so this milestone adds no empty tabs or invented data.
Ads, commerce and reference marketing cards remain excluded. No backend, OpenAPI, migration,
campaign execution, scheduling, audience or dispatch behavior changes.

## Acceptance evidence

- Campaign regression: 5 files / 64 tests pass.
- Full frontend: 62 files / 1,017 tests pass.
- TypeScript, ESLint and the Vite production build pass.
- Backend and generated API types are unchanged.
- Authenticated representative-data desktop/mobile visual acceptance remains host work.
