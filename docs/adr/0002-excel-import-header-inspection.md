# ADR-0002 — How the import wizard learns an Excel file's column headers

- **Status:** **Proposed — awaiting owner decision.** Nothing implemented.
- **Scope:** contact import (Doc 05 B3.3), API surface, frontend bundle
- **Decision needed because:** B3.3 promises "CSV/Excel"; the shipped wizard is CSV-only.

## Context

The mapping step's keys *are* the file's header row: the wizard must know the headers before it can
offer a mapping, and the server rejects an import whose mapping lacks `phone_e164`. For CSV the
wizard reads the first bytes in the browser. `.xlsx` is a ZIP container — it cannot be read without a
parser.

### What already exists (researched, not assumed)

| Question | Answer |
|---|---|
| Endpoint that inspects an uploaded Excel file? | **No.** `/media/*` offers upload, list, metadata, content, delete. No headers/preview route anywhere. |
| Does the backend parse XLSX already? | **Yes.** `app/crm/formats.py::read_xlsx()` — **openpyxl ≥3.1**, already a declared dependency, `read_only=True` streaming, row 1 is the header, and it deliberately renders numeric cells as text so `+14155550001` does not become `1.4155550001e+10`. Used by both import and export. |
| Does the frontend need more than headers? | **No** — headers, plus one sample row per column for the preview. |

So the capability exists; only its *reach* is missing.

## Option A — lazy-load SheetJS in the browser

| Criterion | Assessment |
|---|---|
| Bundle | ~130–140 KB gzip in an on-demand chunk. Doc 05 F15 caps a route chunk at 150 KB gzip, so one wizard step would consume ~90% of that budget. Eager bundle unaffected. |
| Runtime | Parsing a large workbook on the main thread blocks; F15 forbids long tasks >50 ms during interaction, so a Web Worker becomes mandatory, not optional. |
| Maintenance | A **second** XLSX implementation. Its cell coercion must match openpyxl's exactly or the headers the operator maps differ from the headers the importer sees — the phone-number-as-float case is a live example of that risk. |
| Licensing / supply chain | Community Edition is Apache-2.0, but the maintainers no longer publish to npm: `npm i xlsx` resolves to **0.18.5 (2022)**, which carries a prototype-pollution advisory (fixed 0.19.3) and a ReDoS advisory (fixed 0.20.2). A current build requires configuring the vendor's own registry — a standing supply-chain and CI burden. |
| Complexity | Moderate: dependency + worker + format branch + a parity test suite against openpyxl. |
| Stack fidelity | Adds a runtime dependency to a frozen stack. |

## Option B — backend header-inspection endpoint

| Criterion | Assessment |
|---|---|
| API change | One additive route, e.g. `POST /api/v1/contacts/import/inspect` taking `{upload_id, format}` and returning `{headers: string[], sample_rows: string[][], total_rows?: int}`. No existing path or schema changes. Permission: `contacts:import`, matching the import it precedes. |
| Backend effort | Small. `read_xlsx` already streams in read-only mode; the new work is stopping after N rows and returning headers instead of every row (~60–100 lines with tests). CSV reuses the same shape. |
| Frontend effort | *Less* than today's CSV path: upload, ask for headers, reuse the existing mapping UI. Removes the browser parser for `.xlsx` entirely. |
| Performance | One extra round trip per import. openpyxl read-only reads only the rows requested; cost is bounded by N, not by file size — after the ZIP directory is read. |
| Scalability | Inspection runs in the API process. A 100 MB workbook still has to be unzipped, so the route needs a size ceiling (or a worker hand-off) to stay off the request path's tail latency. |
| Consistency | **One parser.** The headers shown are by construction the headers the importer will use. |
| Stack fidelity | No new dependency, client or server. |

## Recommendation — **Option B**

Ranked on objective criteria:

1. **Correctness** — a single parser removes an entire class of "the preview disagreed with the
   import" defects. Option A creates two implementations that must be kept in lockstep by testing.
2. **Security** — Option A's only npm-installable version ships with known advisories; Option B adds
   no new supply-chain surface.
3. **Budget** — Option B costs the client 0 KB; Option A spends ~90% of a route-chunk budget.
4. **Stack** — the stack is frozen; Option B respects that, Option A amends it.
5. **Effort** — comparable (~1 day either way), but Option B lands in code that already has tests,
   fixtures and an owner.

Accepted trade-offs: one extra round trip, server CPU per inspection, and a file that reaches the
server before the operator commits — mitigated by a size ceiling and by the fact that the file has to
be uploaded to be imported at all.

**If the answer is instead "Excel is out of scope",** the smaller change is to amend Doc 05 B3.3 to
say CSV, and the shipped wizard is already conformant.

## Not decided here

Whether inspection runs inline in the API or is handed to the existing job queue. Inline is simpler
and adequate under a size ceiling; the queue is the escape hatch if operators routinely import
workbooks large enough to matter.
