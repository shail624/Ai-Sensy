# ADR-0001 — Job artifacts are served by their own route, not the media route

- **Status:** Accepted (implemented in `c86d11c`, 2026-07-23; recorded 2026-07-24)
- **Scope:** backend, storage signing
- **Contract change:** none to existing paths; one additive route

## Context

Three background jobs produce a downloadable file: a contact export, an import error report, and a
bulk-operation error report. Each signs a URL through `StorageProvider.signed_url(key, media_id=…)`
using a **kind-prefixed** id — `export-<uuid>`, `import-<uuid>`, `bulk-<uuid>` — because the file is
not a `media_assets` row and has no media id to give.

`LocalStorageProvider.signed_url` pointed every signature at `/media/{media_id}/download`. That route
is typed `media_id: UUID` and resolves the id against `media_assets`, so a prefixed id could not even
parse: every completed export, import report and bulk report handed the user a link that returned
**422**. The SPA renders `download_url` as a plain `href`, so the failure was user-visible.

## Root cause

Neither side was wrong on its own:

- the **frontend** renders whatever `download_url` the API returns — correct;
- the **backend** signs a prefixed id because a job artifact genuinely is not a media asset — correct;
- the **contract** was consistent — `/media/{id}` has always been UUID-typed;
- what was missing was a **route for the other id shape**. The signer sent both kinds to one route.

## Decision

Route by id shape at the point of signing, and give artifacts their own endpoint:

- `_download_path()` parses the id: a bare UUID signs onto `/media/{id}/download`, anything else onto
  `/artifacts/{artifact_id}/download`.
- `GET /api/v1/artifacts/{artifact_id}/download` resolves the storage key from the owning job through
  a declarative `kind → resolver` map (`export` / `import` / `bulk`), so a fourth artifact kind is one
  entry rather than another branch.
- The route is **signature-authenticated, not Bearer-authenticated**, matching the media download
  route: the signature binds the artifact id to an expiry, so a leaked link expires on its own and
  cannot be edited to address a different artifact.

## Alternatives rejected

1. **Give every artifact a `media_assets` row.** Pollutes the media library with files no operator
   would ever browse, and inherits media's MIME/size rules for machine-generated output.
2. **Loosen `/media/{id}` to `str` and branch inside.** Widens a stable public contract and puts two
   unrelated lookups behind one path.
3. **Sign a bare UUID and disambiguate by lookup order.** Three tables would have to be probed per
   download, and a uuid collision across kinds would resolve arbitrarily.

## Consequences

- Export, import-error and bulk-error downloads work; covered end-to-end by
  `tests/test_api_export.py::test_export_download_url_serves_the_csv`, which fetches the signed URL
  with no `Authorization` header and asserts the CSV bytes.
- `/media/{id}/download` still 422s for a prefixed id. That is correct and now unreachable: nothing
  signs a prefixed id onto it.
- Adding an artifact kind means one resolver entry plus the prefix its service signs.
