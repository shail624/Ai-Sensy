# Project State

## VAL-01 — the suite runs against the database production uses (2026-09-16)

The full backend suite now passes with **zero skips**: **1,623 passed**, where every previous run in
this repository reported "6 MySQL-only skips". Those six were never a rounding error. They are the
tests that prove the 63-revision migration chain against a *real* MySQL 8 rather than SQLite, and a
test that never runs proves nothing — it simply stops asking.

A MySQL 8.0.46 server was brought up and the whole chain applied to it from base: 93 tables and 76
seeded permissions, upgrade and downgrade, with the owner bootstrap idempotent on rerun. The API
was then booted against that database with Redis behind it and answered `/health`.

Docker was never the requirement, only the convenience. `docker compose up -d` remains the easy
route, but the tests need a server that speaks MySQL 8, not a container runtime. The skip message
and module docstring now say so, and the README carries the four commands that get there from a
plain package install. A skip that names only the route you do not have is a skip nobody clears.

**`scripts/live_api_read_sweep.py`** is added as a gate, because the hermetic suite runs on SQLite
and MySQL disagrees with SQLite exactly where it is most expensive to find out late:
`ONLY_FULL_GROUP_BY` is on by default in MySQL 8 and absent in SQLite, the date and JSON function
sets differ, and `FILTER (WHERE ...)` has no MySQL equivalent. A query that is wrong for MySQL
therefore passes every test and fails the first time an operator opens the page. The sweep asks a
running server, on its real database, for every read the contract declares: **203 requests across
69 parameterless GET paths, zero 5xx**. It fails only on a 5xx or a transport error — a 400 refusing
an unbounded date range is the endpoint working, not a defect.

It also reports what it could *not* reach. Three analytics paths require a parameter whose accepted
values the contract does not enumerate (`breakdown`'s `dimension`, `series` and `trends`' `metrics`),
so they are listed under `not_exercised` rather than counted as answered: their 422 proves
validation works, not that the query underneath is sound, and calling that a pass would be the
false comfort this gate exists to remove. All three were then exercised by hand — `breakdown` over
`error_code` and `message_type`, `series` at day, week and month, `trends` — and all returned 200
against MySQL. The remaining 400s are correct domain rules ("no metrics of dimension
'assigned_user_id' were requested"; "an 'hour' range may span at most 7 days").

No product code changed. This milestone alters a test docstring, a skip message, the README, and
adds one script plus its evidence. It does not raise any module percentage: proving what was
already built is not building more, and the completion table has always said so.

PASS: backend **1,623 passed, 0 skipped** (was 1,617 passed / 6 skipped); live-MySQL file 12/12;
frontend 901 passed across 51 files; production build clean; Bandit 0 high / 0 medium / 34 low,
unchanged; Ruff and mypy clean on the new script.

## CORE-20 — a user's sign-in history (2026-09-16)

`GET /api/v1/users/{user_id}/login-history` returns one user's successful sign-ins, rejected
passwords and lockouts, newest first, each with its time and source address. Contract 237 → 238
paths. No migration, no new permission, no change to what any existing endpoint returns.

It reads the audit trail rather than keeping a second copy. The login path already writes all three
outcomes there with their source address; a parallel table would be a second version of the same
truth, and two versions of one truth drift.

Returning all three together is the point. A list of successes answers "when did they last sign
in". Only the failures answer "is somebody trying to get in" — so a history that quietly dropped
them would look healthiest exactly during an attack.

Gated on `users:read`, the same permission as viewing the user, and scoped to the caller's
organization, so no tenant can read another's sign-in activity. An unknown user is a 404 before any
audit row is read. `limit` and `cursor` are declared per Doc 04 §6, so the page is reachable from
the generated TypeScript client, and an out-of-range page size is refused rather than clamped —
the CORE-18/19 rule, applied here from the start.

The audit repository gained one filter, `actions` (a set), kept distinct from the existing `action`
(exactly one) rather than overloading it. Nothing else on the audit read path changed.

This closes "login history" under Team Management. Audit Timeline's "device/login" item is half
closed: the login evidence is now addressable per user, but the entries carry the source address,
not a device identity, so that half of the item stands.

PASS: full backend suite **1617 passed**, 6 MySQL tests skipped for want of a server — including 8
new tests here covering the outcome shown, failures included, time and address present, other
users excluded, unrelated actions excluded, declared bounded pagination, unknown user 404 and the
permission gate. Full frontend suite 901 passed. Regenerated OpenAPI and TypeScript types with no
drift; Ruff, endpoint mypy and TypeScript clean.

## CORE-19 — declare pagination across the remaining collections (2026-09-16)

Six more handlers now declare their spec'd query parameters instead of reading them off the raw
request: contacts, the contact timeline, users, jobs, media and the segment contact preview.
Contract remains 237 paths; no migration, no new permission, no change to what any endpoint
returns. Routes declaring `limit` rise from 6 to 35.

This completes the pattern begun in CORE-18. Doc 04 section 6 fixes `limit` and `cursor` for every
collection and section 1 requires the API to be fully OpenAPI-describable; undeclared, those
parameters never reach the generated TypeScript client, which is the only contract the frontend
may use. `q` and `sort` are declared with them where a handler supports them (sections 7.2-7.3).

The `filter[field][op]` grammar of section 7.1 stays on the raw request in every one of these
handlers, and each says so in its docstring. It spans any field crossed with eleven operators, so
there is no finite parameter set to declare; a later reader "completing" the job by declaring it
would break the documented grammar.

Two defects fixed as a side effect. The media list parsed its limit with a bare `int()` on the raw
value, so `?limit=abc` raised and returned 500 rather than a rejected request; the declaration
makes it a 422. And as in CORE-18, out-of-range page sizes are now refused rather than silently
clamped — a client asking for 9999 rows has a defect, and quietly returning 200 hides it.

Not changed: phone-numbers and templates read only `filter[...]` and a legacy alias, so they have
no plain parameters to declare. Every collection that has them now declares them.

PASS: full backend suite **1609 passed**, 6 MySQL tests skipped for want of a server; 198 focused
contact/user/job/media/segment/audit tests pass. Full frontend suite 901 passed; regenerated
OpenAPI and TypeScript types with no drift; Ruff, endpoint mypy, ESLint and TypeScript clean.

PENDING - Host Machine Validation: deployed MySQL and authenticated preview were not run. No
module completion percentage is increased and no source-of-truth document changed.


## CORE-18 — declare audit-log pagination (2026-09-16)

`GET /api/v1/audit-logs` now declares `limit` and `cursor` as typed contract parameters instead of
reading them off the raw request. Contract remains 237 paths; no migration, no new permission, no
change to what the endpoint returns.

Doc 04 section 6 fixes `limit` and `cursor` for every collection and section 1 requires the API to
be fully OpenAPI-3.1-describable. Undeclared, they never reach the generated TypeScript client —
the only contract the frontend is permitted to use — so paging the audit trail from the UI was
impossible without hand-writing a query string, which repository rules forbid.

The `filter[field][op]` grammar of section 7.1 deliberately stays on the raw request and is
covered by its own test. It spans any field crossed with eleven operators, so there is no finite
parameter set to declare; treating it as an oversight and "fixing" it would break the documented
grammar. The distinction is recorded in the handler docstring so the next reader does not undo it.

Behaviour change, recorded rather than slipped in: an out-of-range page size is now refused with
422 instead of being silently clamped to the maximum. A client asking for 9999 rows has a defect,
and quietly returning 200 hides it. No existing test depended on the clamping; the new bound is
pinned by test.

Systematic finding, not yet acted on: eight further collection endpoints read the same spec'd
`limit`/`cursor` off the raw request — contacts, contact timeline, jobs, media, segment contacts,
templates, users and phone numbers. Only six routes in the whole contract currently declare both.
The same mechanical change applies to each, and the 422 decision above should be reviewed before
it is applied eight more times.

PASS: full backend suite **1609 passed**, 6 MySQL tests skipped for want of a server; 2 new tests
covering the declared bounds and the filter grammar's continued absence from the generated query.
Full frontend suite 901 passed; regenerated OpenAPI and TypeScript types; ESLint, Ruff and
endpoint mypy pass.

PENDING - Host Machine Validation: deployed MySQL and authenticated preview were not run. No
module completion percentage is increased and no source-of-truth document changed.


## CORE-17 — server-owned workspace favourites (2026-09-16)

Navigation favourites now persist per user through the existing `GET/PUT /users/me/preferences`
contract, under a namespaced `workspace_favorites` key. No new path, no migration, no new
permission: the preferences document already stores a free object. Contract remains 237 paths.

Favourites were browser-local, so an agent who starred Templates or a Contacts view lost them on
another machine or after clearing site data. Both consumers — the templates list and the command
palette — read the same store, so this fixes them together.

Recents deliberately stay local. They record what was opened *on this device*; syncing them would
let a phone reorder a desktop's list, and the value of the list is that it is local.

The browser copy of favourites is kept as a cache, not a second source of truth: it renders
immediately on a cold load and stands in when the read fails, so a network problem degrades the
list to what this device last saw rather than to empty — the one outcome that would look to the
operator like their favourites had been deleted. Absent and empty are treated as different
answers: an empty stored list means "starred nothing" and is never overwritten from a stale
device, while a first read with the key absent adopts whatever this browser holds, so nobody loses
favourites they set before these became server-owned.

Two defects were found and fixed during implementation. Cache alignment raced the optimistic
write: a toggle wrote through the cache, then the still-stale server read reverted it, so the star
flipped back under the cursor until the refetch landed. Alignment is now suppressed while a save
is in flight. Separately, the first write of this file emitted NUL bytes in place of two spaces
inside a string separator; TypeScript and the tests accepted it, but the file was classified as
binary and was invisible to grep and diff. The comparison no longer needs a separator at all.

PASS: full frontend suite **901 passed / 51 files**, 7 new tests covering server precedence,
first-read seeding, the empty-versus-absent distinction, read-failure fallback, toggle
persistence and removal, and recents staying local. TypeScript, ESLint clean.

No backend file, contract or migration changed, so the 1607-test backend result from CORE-16
stands unaltered. PENDING - Host Machine Validation: authenticated multi-device preview was not
run. No module completion percentage is increased and no source-of-truth document changed.


## CORE-16 — API key rotation (2026-09-14)

Adds `POST /api/v1/api-keys/{key_id}/rotate`, replacing a key's secret in place. The contract
moves 236 -> 237 paths; no migration, no new permission (`apikeys:manage` already governs this
family), no change to authentication.

Why it exists: revoke-then-create discards the key's identity, name, scopes and audit history,
so every consumer must be reconfigured with a new credential and the trail splits across two
records. Rotation keeps the record and swaps only the secret.

Trade recorded, not resolved: the existing admin UI composes planned rotation client-side as
create-then-revoke, deliberately overlapping so no window exists in which neither key is valid.
This endpoint makes the opposite trade — one atomic swap with no two-live-keys hazard, at the
cost of cutting the old secret off immediately. That is the right shape for a *leaked* key, where
instant cutover is the objective. The planned path is left unchanged; which rotation an operator
should get, and whether both belong in the UI, is an open product decision. The stale comment
asserting no rotate endpoint exists was corrected.

A revoked key is not rotatable: reviving one would return a working secret for a credential
somebody deliberately retired. Rotation is audited as `api_key.rotated` recording only the old and
new prefixes — never either secret.

PASS: full backend suite **1607 passed**, 6 MySQL tests skipped for want of a server; 6 new
rotation tests covering identity retention, listing, revoked and unknown keys, audit content and
permission enforcement. Frontend admin suite 42 passed; TypeScript, ESLint, Ruff and endpoint
mypy pass. Two 236-path contract guards moved to 237.

PENDING - Host Machine Validation: deployed MySQL, authenticated preview and E2E commissioning
were not run. No module completion percentage is increased and no source-of-truth document
changed.


## CORE-11 — inbox category counts (2026-09-14)

Adds `GET /api/v1/conversations/counts`, returning active, requesting and intervened totals for
the signed-in viewer. The contract moves 235 -> 236 paths; no migration, no new permission, no
change to any category's meaning.

Scope decision recorded: the counts accept `q` and nothing else. Activating a chip replaces
status, assignee and tag and carries only the search across, so a count computed with the current
filters applied would advertise a list the click never produces — and a contradictory status such
as `closed` would pin active and requesting to a permanent zero. The three totals overlap by
construction (requesting is a subset of active) and are never summed.

One aggregate over one scan rather than three round trips; `ix_conv_org_status` and
`ix_conv_assignee` already cover the predicates. The inbox search predicate is now shared by the
list page and the counts, so a badge cannot come to describe different fields than the list it
labels. While the read is in flight the badge is omitted rather than shown as zero, which would
assert an emptiness the inbox has not established.

PASS: full backend suite **1601 passed**, 6 MySQL tests skipped for want of a server;
6 new backend contract/semantics tests. Full frontend suite **894 passed / 50 files**; 3 new badge
tests. TypeScript, ESLint, Ruff, endpoint mypy and the OpenAPI drift gate all pass. Two
hard-coded 235-path contract guards were updated to 236 — they are deliberate guards and this
path addition is the conscious act they exist to catch.

PENDING - Host Machine Validation: deployed MySQL, authenticated populated preview, browser and
E2E commissioning were not run. No module completion percentage is increased and no
source-of-truth document changed.


## UI-REF-04 — Live Chat category semantics (2026-09-14, local)

Restores the owner's category definitions: Active = open; Requesting = open and
unassigned; Intervened = current assignment ownership across statuses. Switching
categories preserves only search. Reference-style captions are retained.
PASS: 32 focused inbox tests and frontend TypeScript checking. Added regression
coverage for conflicting status/assignee/tag filters while retaining search.
PENDING – Host Machine Validation: authenticated populated preview and release.
No completion percentage increase. Uncommitted on the existing dirty checkout;
this entry does not certify or commit the unrelated local work or full UI parity.


## UI-REF-03 — manual contact creation (2026-09-13)

Added permission-gated Add Contact and a responsive Create Contact form using the existing
POST /api/v1/contacts endpoint. Name, international mobile number and source are supported;
consent remains unknown. Pending submission is guarded; server errors remain visible and
successful creation refreshes contact search without changing active filters.

PASS: 48 files / 887 frontend tests (8.22s), ESLint, TypeScript and production build.
PASS: local preview created one explicitly named test contact in the isolated preview database;
desktop/mobile form screenshots saved under output/previews/ui-ref-03-create-contact-*.png.
No production data, backend contracts, migrations, GitHub or deployment changed.

Still pending: reference-equivalent DOB/tag entry, country picker, Contacts/Segments secondary
navigation, full action/filter menus and cumulative production acceptance. No completion
percentage increase or claim of full AiSensy parity. See design document 74.

Latest checkpoint: **UI-REF-02** Live Chat shell; frontend **883/883**, types/build/lint and
desktop/mobile preview PASS. Design Document 73 records remaining populated-flow/full-parity
checks. API 235, unfinished segment migration 0062 and Git baseline unchanged. No deployment.

Previous working delta (2026-09-13): **UI-REF-01**, screenshot-aligned rail/Manage and real settings
deep links. Frontend **882/882**, types/lint/build and desktop/mobile preview: PASS. Full parity,
cumulative backend/release revalidation and production acceptance remain pending. Separate
unfinished segment work is at **0062**; OpenAPI **235**. Design Document 72 is the current UI
comparison record; earlier detailed gate results below remain historical. No commit/push/deploy.

> Current repository snapshot. GitHub is the implementation source of truth. `HEAD` is symbolic
> because a commit cannot embed its own final hash; resolve it after push with `git rev-parse HEAD`.

## MAINT-02 — typed campaign list filters (2026-09-13)

Latest milestone: MAINT-02. Branch: `claude/sweet-darwin-5i66uq`; approved starting
HEAD: `6d755f250eb3cd1b2e3126ba2ba26ff32f8516b2`. Delivery HEAD is this milestone's
single commit (resolve from Git). Repository version remains `1.0.0-rc1`.

PASS: the approved branch reproduced an empty query-parameter declaration in live OpenAPI,
despite frozen API design section 17 requiring campaign name/status filtering. No frozen
requirement calls for the undeclared shape. The route now declares optional typed q/status;
status validation derives from the existing campaign status tuple. The existing legacy
status-filter spelling remains accepted with its existing precedence, without adding it
to the public generated query shape.

PASS: regenerated OpenAPI and frontend types; the generated client sends filters and query
cache keys include them. Removed duplicate client-side search/status filtering. Existing
local sorting and paging remain; no server pagination, new tabs, campaign kinds, migrations,
execution, scheduling, audience or dispatch changes. Empty filtered results are distinguished
from an empty registry; filter controls remain mounted while results load.

PASS: full backend suite **962 passed**, no failures/skips (176.71s); focused new backend
contract/filter/status/tenant checks **14 passed**. Frontend campaign tests **48 passed**;
full frontend suite **657 passed / 33 files** (5.64s). TypeScript, production build,
ESLint, changed-backend Ruff, endpoint mypy and OpenAPI drift check passed.
Build bundle-size and runtime/tool deprecation warnings remain non-blocking.
Initial sandbox restrictions on dependency installation/bundler startup were resolved;
the completed runs above are the acceptance results.

OpenAPI remains **193 paths**, migration head remains **0035_notification_center**.
No source-of-truth document changed. Existing module completion estimates are not increased.
PENDING – Host Machine Validation: deployed MySQL/browser/E2E commissioning was not run;
this bounded contract milestone is not a new production-readiness certification.

Design note: `docs/design/MAINT-02-CAMPAIGN-LIST-FILTER-CONTRACT.md`.
Decision: `docs/adr/0020-maint-02-campaign-list-filter-contract.md`.
Scope limited to MAINT-02; other local work was excluded through an isolated worktree.
Next action after the single commit/push: STOP; no next milestone is authorized.

## Historical records below — retained, not current MAINT-02 evidence

> Current repository snapshot. Update this file at every milestone closeout and whenever the
> milestone baseline changes. `HEAD` is kept symbolic because a Git commit cannot embed its own
> final hash; resolve it from the authoritative checkout with `git rev-parse HEAD`.

| Field | Current value |
|---|---|
| Current branch | `ui/taste-modernization` |
| Latest change | `UI-REF-02 — Live Chat strip and empty-workspace layout; GROW-03 segment delta remains unfinished.` |
| M13-05 starting baseline | `5d7ea154588418410611de4f568e978c2e3caba9` (`feat(channels): add session manager foundation`) |
| Current Git HEAD | `1865f4b6657d644a247750949d8cae3f2aa28450` baseline plus uncommitted CORE-11A/11B/11C and UI-parity follow-up changes; no commit or push was authorized. |
| Current milestone | `UI-REF-02 — local Live Chat shell implemented`; full populated screen acceptance pending. `GROW-03` remains unfinished. Prior backend/release evidence remains historical. |
| Current phase | `Screenshot-by-screenshot Live Chat, Contacts, Campaigns and Manage acceptance; preserve unfinished segment work and complete cumulative release/host validation.` |
| Repository version | `1.0.0-rc1` |
| Consolidated release evidence | Last complete Docker/security release profile is PAR-AUTO-22: **23/23 PASS in 685.9s**, with **1521 backend / zero skips**, **832 frontend**, lint/types/OpenAPI/build, scans, image contracts/SBOMs and certified WAHA runtime. Historical PAR-VIEW-05 source tree passed **1579 backend / 6 MySQL-only skips / 0 failures in 413.35s**, **875 frontend tests**, static **6/6**, strict mypy **322 files**, synchronized **235-path** OpenAPI and production build; its Docker/security release rerun remains pending. Preserved pre-PAR-AUTO-19 deployed evidence is **25/25 in 597.4s**, including canary **5.764ms p95 / 300ms**, Redis-down readiness **503 degraded**, and zero synthetic-secret/PII leaks. |
| Full-scope completion | The 31 canonical rows sum to 2,389: simple unweighted average **77.1%**, recalculated median **87%**. This is distinct from the green source-validation gate and is not a 100% AiSensy parity claim. |
| Migration head | `0062_segment_domain_predicates` (**63 linear revisions**) from separate unfinished segment work. UI-REF-01 adds no migration. Prior 0061 Reports-view evidence remains historical. |
| OpenAPI | `3.1.0` · **`238` paths**. PAR-VIEW-05 adds list/create/delete Reports saved-view contracts; canonical export and generated TypeScript are synchronized. |
| Backend evidence (QR-08, historical) | Ruff PASS · strict mypy PASS (300 files) · 1380 full pytest tests PASS (1367 before QR-08; +13) · Bandit PASS (only pre-existing Low findings) |
| Backend evidence (QR-09B release gate) | **1397 passed, 0 skipped** · Ruff PASS · strict mypy PASS (300 files) · Bandit PASS · `pip-audit` no known vulnerabilities · full release gate **21/21 PASS**, including certified WAHA runtime health, Compose/release contracts, image contracts and scans |
| Backend evidence (QR-09C release gate) | **1399 passed, 0 skipped** · Ruff PASS · strict mypy PASS (300 files) · Bandit PASS · `pip-audit` no known vulnerabilities · full release gate **22/22 PASS**, including provider-generated signed webhook/retry/restart runtime evidence |
| Backend evidence (QR-09E release gate) | **1407 passed, 0 skipped** · Ruff PASS · strict mypy PASS (300 files) · Bandit PASS · `pip-audit` no known vulnerabilities · full release gate **23/23 PASS**, including exact-certified-runtime JSON/PNG content-negotiation evidence |
| Backend evidence (QR-09F release gate) | **1408 passed, 0 skipped** · Ruff PASS · strict mypy PASS (300 files) · Bandit PASS · `pip-audit` no known vulnerabilities · full release gate **23/23 PASS**, including genuine provider-outage/recovery and certified WAHA runtime evidence |
| Backend evidence (QR-09G release gate) | **1418 passed, 0 skipped** · Ruff PASS · strict mypy PASS (300 files) · Bandit PASS · `pip-audit` no known vulnerabilities · full release gate **23/23 PASS** in 506.1s, including the paused never-paired recovery, transition-before-lease ordering and certified WAHA runtime evidence |
| Backend evidence (QR-09D closure gate) | **1418 passed, 0 skipped** · Ruff PASS · strict mypy PASS (300 files) · Bandit PASS · `pip-audit` no known vulnerabilities · full release gate **23/23 PASS** in 635.1s on the combined QR-09G backend + QR-09D frontend tree, including certified WAHA health/QR/webhook runtime evidence |
| Backend evidence (QR-09H release gate) | **1431 passed, 0 skipped** · Ruff PASS · strict mypy PASS (300 files) · Bandit PASS · `pip-audit` no known vulnerabilities · full release gate **23/23 PASS** in 508.9s, including the certified expired-QR stop/start recovery and truthful reached-provider conflict classification |
| Backend evidence (QR-09I release gate) | **1436 passed, 0 skipped** · Ruff PASS · strict mypy PASS (300 files) · Bandit PASS · `pip-audit` no known vulnerabilities · **23/23 PASS**: canonical premerge 14/14 in 369.6s plus 9 release/runtime gates. The canonical live WAHA restart script was intentionally not run because it would restart the owner-linked session; an isolated container at the exact certified digest instead proved health success/failure and restart survival without touching live storage. |
| Backend evidence (QR-09J applicable gates) | **1437 passed, 0 skipped** · frontend **806 passed** · canonical premerge **14/14 PASS** in 684.7s · applicable release/runtime **8/8 PASS** in 87.9s, including exact-digest QR and provider-generated signed-webhook validators, production contracts/builds, image scans and SBOM. The unchanged health validator was not rerun because its canonical implementation restarts the protected linked WAHA service; QR-09I's isolated exact-digest health evidence remains current. |
| Backend evidence (QR-09L applicable gates) | **1444 passed, 0 skipped** · frontend **806 passed** · canonical premerge **14/14 PASS** in 433.6s · strict mypy **301 files** · applicable release/runtime **8/8 PASS** in 70.7s, including exact-digest QR and provider-generated signed-webhook/ACK validators, production contracts/builds, image scans and SBOM. The restart-bearing health validator was not pointed at the protected linked service; QR-09I's approved isolated exact-digest proof remains current and no health/deploy code changed. |
| CORE-11A evidence | Focused backend Settings/inbound selection **33 passed**; corrected path-count regressions **2/2 passed**; Ruff, strict mypy (302 files) and OpenAPI drift PASS. Frontend ESLint, TypeScript, **39 files / 809 tests**, and production build PASS. Applicable backend suite **1443 passed / 6 MySQL skipped / 1 Redis-dependent test deselected**; the unfiltered result and environmental exception are recorded in `VALIDATION_RESULTS.md`. |
| CORE-11B evidence | Focused backend Settings/inbound selection **40 passed**; final delivery/Inbox regression **73 passed / 1 known Redis case deselected**; Ruff, strict mypy (302 files), OpenAPI drift and static gate **6/6 PASS**. Frontend ESLint, TypeScript, **39 files / 810 tests**, and production build PASS. Applicable backend suite **1450 passed / 6 MySQL skipped / 1 Redis-dependent test deselected**. |
| CORE-11C evidence | Focused Settings/conversation/scanner/scheduler selection **48 passed**; Ruff, strict mypy (302 files), OpenAPI drift and static gate **6/6 PASS**. Frontend ESLint, TypeScript, **39 files / 811 tests**, and production build PASS. Applicable backend suite **1453 passed / 6 MySQL skipped / 1 Redis-dependent test deselected**; canonical unfiltered preserves the same 1453 passes and known Redis-only failure. |
| UI parity follow-up evidence | Intervention backend **24/24**, combined path/runtime regression **26/26**, focused intervention/thread frontend **37/37**, complete frontend **40 files / 816 tests**, ESLint, TypeScript and production build PASS. Applicable backend **1457 passed / 6 MySQL skipped / 1 known Redis-dependent test deselected**. No migration, permission-code, dispatch or provider change. Authenticated reference/local visual comparison remains pending at sign-in. |
| PAR-AUTO-04 evidence | Automation/Inbox backend **76/76** and focused definition/handoff **14/14** PASS; complete frontend **40 files / 817 tests** PASS. Applicable backend **1462 passed / 6 MySQL skipped / 1 known Redis-dependent test deselected**; Ruff, strict mypy **304 files**, OpenAPI drift and static gate **6/6** PASS. No migration, new permission code, queue, provider or customer send. |
| PAR-AUTO-05 evidence | Final focused Automation/Inbox regression **40/40**; complete frontend **40 files / 817 tests**; static gate **6/6**, strict mypy **305 files**, OpenAPI drift and migration round-trip **5/5** PASS. Canonical backend **1465 passed / 6 MySQL skips / 1 known unavailable-Redis failure**; applicable backend **1465 passed / 6 MySQL skips / 1 Redis deselection**. |
| PAR-AUTO-06 evidence | Conditional runtime/migration **10/10**; complete frontend **40 files / 818 tests**, focused Automation **8/8**; static gate **6/6**, strict mypy **305 files**, OpenAPI drift and migration round-trip **5/5** PASS. Canonical backend **1468 passed / 6 MySQL skips / 1 known unavailable-Redis failure**; applicable backend **1468 passed / 6 MySQL skips / 1 Redis deselection**. |
| PAR-AUTO-07 evidence | Live runtime **7/7** and Task API **45/45**; complete frontend **40 files / 818 tests**, focused Automation **8/8**; static gate **6/6**, strict mypy **305 files**, OpenAPI **211 paths** and production build PASS. Canonical backend **1470 passed / 6 MySQL skips / 1 known unavailable-Redis failure**; applicable backend **1470 passed / 6 MySQL skips / 1 Redis deselection**. |
| PAR-AUTO-08 evidence | Live runtime **9/9** and combined Tag regression **32/32**; complete frontend **40 files / 819 tests**, focused Automation **9/9**; static gate **6/6**, strict mypy **305 files**, OpenAPI **211 paths** and production build PASS. Canonical backend **1472 passed / 6 MySQL skips / 1 known unavailable-Redis failure**; applicable backend **1472 passed / 6 MySQL skips / 1 Redis deselection**. |
| PAR-AUTO-09 evidence | Live runtime **11/11** and combined Automation/Inbox regression **45/45**; complete frontend **40 files / 820 tests**, focused Automation **10/10**; static gate **6/6**, strict mypy **305 files**, OpenAPI **211 paths** and production build PASS. Canonical backend **1474 passed / 6 MySQL skips / 1 known unavailable-Redis failure**; applicable backend **1474 passed / 6 MySQL skips / 1 Redis deselection**. |
| PAR-AUTO-10 evidence | Live runtime **13/13** and combined runtime/Tag regression **45/45**; complete frontend **40 files / 821 tests**, focused Automation **11/11**; static gate **6/6**, strict mypy **305 files**, OpenAPI **211 paths** and production build PASS. Canonical backend **1476 passed / 6 MySQL skips / 1 known unavailable-Redis failure**; applicable backend **1476 passed / 6 MySQL skips / 1 Redis deselection**. |
| PAR-AUTO-11 evidence | Live runtime **15/15** and combined Notification Center/lifecycle/migration regression **23/23**; focused Automation/Notification frontend **14/14**, complete frontend **40 files / 821 tests**, production build, static gate **6/6**, strict mypy **305 files**, frontend lint/types and OpenAPI **211 paths** PASS. Canonical backend **1478 passed / 6 MySQL skips / 1 known unavailable-Redis failure**; applicable backend **1478 passed / 6 MySQL skips / 1 Redis deselection**. Automation advances **94% → 96%**. |
| PAR-AUTO-12 evidence | Sequential live runtime **19/19** and combined Automation/Tasks/Tags/Notifications/migration regression **88/88**; focused Automation frontend **12/12**, complete frontend **40 files / 822 tests**, production build, static gate **6/6**, strict mypy **305 files**, frontend lint/types and OpenAPI **211 paths** PASS. Canonical backend **1482 passed / 6 MySQL skips / 1 known unavailable-Redis failure**; applicable backend **1482 passed / 6 MySQL skips / 1 Redis deselection**. No migration or route; Automation advances **96% → 98%**. |
| PAR-AUTO-13 evidence | Durable Delay runtime/scheduling **22/22** and wider Automation/Tasks/Tags/Notifications regression **166/166**; focused Automation frontend **13/13**, complete frontend **40 files / 823 tests**, production build, static gate **6/6**, strict mypy **305 files**, frontend lint/types and OpenAPI **211 paths** PASS. Canonical backend **1485 passed / 6 MySQL skips / 1 known unavailable-Redis failure**; applicable backend **1485 passed / 6 MySQL skips / 1 Redis deselection**. No migration, route, permission or queue; Automation advances **98% → 99%**. |
| PAR-AUTO-14 evidence | Contact Created live runtime **26/26**, focused trigger/scheduler/runtime **35/35** and wider Automation/Tasks/Tags/Notifications regression **175/175**; focused Automation frontend **14/14**, complete frontend **40 files / 824 tests**, production build, static gate **6/6**, strict mypy **305 files**, frontend lint/types and OpenAPI **211 paths** PASS. Canonical execution preserves **1489 passes / 6 MySQL skips / 1 known unavailable-Redis failure**; applicable backend **1489 passed / 6 MySQL skips / 1 Redis deselection** in **217.62s**. No migration, route, permission or queue; Automation remains **99%**. |
| PAR-AUTO-15 evidence | Conversation Auto-Resolved live runtime **29/29**, combined Automation/auto-resolve/trigger/API/scheduler regression **50/50** and wider Automation/Inbox/Tasks/Tags/Notifications regression **180/180**; focused Automation frontend **15/15**, complete frontend **40 files / 825 tests**, production build, static gate **6/6**, strict mypy **305 files**, frontend lint/types and OpenAPI **211 paths** PASS. Applicable backend **1492 passed / 6 MySQL skips / 1 Redis deselection** in **212.83s**; the unchanged unavailable-Redis case remains separately recorded. No migration, route, permission or queue; Automation remains **99%**. |
| PAR-AUTO-16 evidence | Durable Schedule projection/runtime/dispatcher **4/4**, combined Automation definition/live runtime **42/42** and wider Automation/Inbox/Tasks/Tags/Notifications regression **222/222**; focused Automation frontend **16/16**, complete frontend **40 files / 826 tests**, production build, static gate **6/6**, strict mypy **305 files**, frontend lint/types and OpenAPI **211 paths** PASS. Applicable backend **1496 passed / 6 MySQL skips / 1 Redis deselection** in **376.13s**. Additive migration `0047`; no route, permission, queue, provider or customer send; Automation remains **99%**. |
| PAR-AUTO-17 evidence | Durable Wait event/timeout/isolation **3/3**, combined Automation/API/Schedule/migration **55/55** and wider Inbox/message/provider/Task regression **112/112**; focused Automation frontend **17/17**, complete frontend **40 files / 827 tests**, production build, static gate **6/6**, strict mypy **305 files**, frontend lint/types and OpenAPI **211 paths** PASS. Applicable backend **1499 passed / 6 MySQL skips / 1 Redis deselection** in **400.25s**; final late-event temporal edge **3/3** PASS. Additive migration `0048`; no route, permission, queue, provider or customer send; Automation remains **99%**. |
| PAR-AUTO-18 evidence | Deterministic completion-cycle/live-Wait **4/4**, Task/Wait **53/53** and combined Automation/Task/API/Notification/KYC regression **130/130**; focused Automation frontend **18/18**, complete frontend **40 files / 828 tests**, production build, static gate **6/6**, strict mypy **305 files**, frontend lint/types and OpenAPI **211 paths** PASS. Applicable backend **1501 passed / 6 MySQL skips / 1 Redis deselection** in **377.10s**. No migration, route, permission, queue, provider or customer send; Automation remains **99%**. |
| PAR-AUTO-19 evidence | Live Lead-stage trigger/Wait runtime **35/35** and combined Automation/Reactivation/migration regression **56/56**; focused Automation frontend **19/19** and complete release profile **23/23 PASS in 389.1s**. Full backend **1512 passed / zero skips**; full frontend **40 files / 829 tests**; static, strict mypy **305 files**, OpenAPI **211 paths**, production build, SAST/dependency/source/image scans, image contracts and SBOMs PASS. No migration, route, permission, queue, provider or customer send; Automation remains **99%**. |
| PAR-AUTO-20 evidence | Bounded branch live/safe runtime **45/45** and combined Automation live/runtime/API/migration regression **60/60**; focused Automation frontend **20/20** and complete release profile **23/23 PASS in 417.8s**. Full backend **1515 passed / zero skips**; full frontend **40 files / 830 tests**; static, strict mypy **305 files**, OpenAPI **211 paths**, production build, SAST/dependency/source/image scans, image contracts and SBOMs PASS. No migration, route, permission, queue, provider or customer send; Automation remains **99%**. |
| PAR-AUTO-21 evidence | Multi-step bounded branch live/safe runtime **48/48** and combined Automation live/runtime/API/migration regression **75/75**; focused Automation frontend **21/21** and complete release profile **23/23 PASS in 609.3s**. Full backend **1518 passed / zero skips**; full frontend **40 files / 831 tests**; static, strict mypy **305 files**, OpenAPI **211 paths**, production build, SAST/dependency/source/image scans, image contracts and SBOMs PASS. No migration, route, permission, queue, provider or customer send; Automation remains **99%**. |
| PAR-AUTO-22 evidence | Shared-follow-up live/safe runtime **51/51** and combined Automation live/runtime/API/migration regression **78/78**; focused Automation frontend **22/22** and complete release profile **23/23 PASS in 685.9s**. Full backend **1521 passed / zero skips**; full frontend **40 files / 832 tests**; static, strict mypy **305 files**, OpenAPI **211 paths**, production build, SAST/dependency/source/image scans, image contracts and SBOMs PASS. No migration, route, permission, queue, provider or customer send; Automation remains **99%**. |
| PAR-AUTO-23 evidence | Shared-Delay live/safe runtime **54/54** and Automation/API/trigger/Schedule/migration regression **77/77**; focused Automation frontend **23/23**. Full backend **1524/1524 in 475.70s**; full frontend **40 files / 833 tests**; static **6/6**, strict mypy **305 files**, OpenAPI **211 paths** and production build PASS. Docker/security release rerun remains pending after approval-usage exhaustion; no migration, route, permission, queue, provider or customer send; Automation remains **99%**. |
| PAR-DL-01 evidence | Download API **5/5** and corrected path-count/API regression **7/7**; focused Download/navigation UI **14/14**. Full backend **1523 passed / 6 MySQL-only skips / 0 failed in 326.78s**; full frontend **41 files / 838 tests**; static **6/6**, strict mypy **306 files**, OpenAPI **212 paths** and production build PASS. No migration, permission code, queue, storage provider or customer send; Download Center advances **30% → 65%**. |
| PAR-REP-01 evidence | Focused Analytics/report/format/export/Download/migration backend **139/139** and focused Analytics/Download UI **36/36**. Full backend **1525 passed / 6 MySQL-only skips / 0 failed in 434.13s**; full frontend **41 files / 839 tests**; static **6/6**, strict mypy **306 files**, OpenAPI **212 paths** and production build PASS. Three-page Poppler visual plus structural/text checks PASS; head advances to `0049` (**50 revisions**), Executive Reports to **35%**, Download Center to **70%**. |
| PAR-REP-02 evidence | Scheduled-report lifecycle/runtime/notification **5/5** and combined Analytics/Notification/smoke/contracts **71/71**; focused Analytics UI **34/34**. Full backend **1530 passed / 6 MySQL-only skips / 0 failed in 425.43s**; full frontend **41 files / 841 tests**; static **6/6**, strict mypy **309 files**, OpenAPI **214 paths** and production build PASS. Head advances to `0050` (**51 revisions**), Executive Reports to **50%**, Download Center to **72%**, Notifications to **86%**, API to **90%**, and full scope to **70.6%**. |
| PAR-REP-03 evidence | Domain rollup/query/API/export/schedule/migration **144/144** and focused Analytics UI **35/35**. Full backend **1532 passed / 6 MySQL-only skipped / 0 failed in 426.19s**; full frontend **41 files / 842 tests**; static **6/6**, strict mypy **309 files**, OpenAPI **217 paths** and production build PASS. Head advances to `0051` (**52 revisions**), Analytics to **75%**, Executive Reports to **65%**, Download Center to **73%**, API to **91%**, and full scope to **71.8%**. |
| PAR-REP-04 evidence | Workload/Analytics/schedule/migration/contract **79 passed / 6 MySQL-only skipped** and focused Analytics UI **36/36**. Full backend **1534 passed / 6 MySQL-only skipped / 0 failed in 367.01s**; full frontend **41 files / 843 tests**; static **6/6**, strict mypy **310 files**, OpenAPI **219 paths** and production build PASS. Head advances to `0052` (**53 revisions**), Analytics to **82%**, Executive Reports to **75%**, Download Center to **74%**, Team Management to **86%**, API to **92%**, and full scope to **72.5%** (median **85%**). |
| PAR-DL-02 evidence | Transcript authorization/ownership/range/artifact/migration/Download/contract **35/35** and focused Chat History/Download/navigation UI **50/50**. Full backend **1537 passed / 6 MySQL-only skipped / 0 failed in 445.40s**; full frontend **41 files / 845 tests**; static **6/6**, strict mypy **310 files**, OpenAPI **221 paths**, **31-task** source image contract and production build PASS. Head advances to `0053` (**54 revisions**), Chat History to **70%**, Download Center to **80%**, API to **93%**, and full scope to **73.3%** (median **85%**). |
| PAR-HIST-01 evidence | Advanced filter/shared-view API **10/10**, existing Inbox/conversation/QR regression **77/77**, migration **5/5** and Chat History UI **41/41** PASS. Full backend **1547 passed / 6 MySQL-only skipped / 0 failed in 458.04s**; full frontend **41 files / 850 tests**; static **6/6**, strict mypy **314 files**, OpenAPI **223 paths** and production build PASS. Head advances to `0054` (**55 revisions**), Chat History to **88%**, Saved Views to **42%**, API to **94%**, and full scope to **74.1%** (median **85%**). |
| PAR-DL-03 evidence | Campaign/export regression **106/106**, provider/OpenAPI/smoke/image **32/32**, migration **5/5** and focused Campaign/Download/navigation UI **63/63** PASS. Full backend **1552 passed / 6 MySQL-only skipped / 0 failed in 475.58s**; full frontend **42 files / 854 tests**; static **6/6**, strict mypy **314 files**, OpenAPI **225 paths**, **32-task** source image contract and production build PASS. Head advances to `0055` (**56 revisions**), Campaigns to **90%**, Download Center to **88%**, API to **95%**, and full scope to **74.5%** (median **85%**). |
| PAR-CAM-01 evidence | Campaign/migration regression **107/107** and focused Campaign UI **51/51** PASS. Full backend **1553 passed / 6 MySQL-only skipped / 0 failed in 476.67s**; full frontend **43 files / 857 tests**; static **6/6**, strict mypy **314 files**, OpenAPI **225 paths** and Vite **8.2.2** production build PASS. Head advances to `0056` (**57 revisions**), Campaigns to **94%** and full scope to **74.7%**. Current-table median is **86%** (the prior 85% summary was corrected). |
| PAR-VIEW-01 evidence | Reactivation view/migration/API **13/13** and focused Reactivation UI **12/12** PASS. Full backend **1559 passed / 6 MySQL-only skipped / 0 failed in 459.36s**; full frontend **43 files / 860 tests**; changed-file Ruff, strict mypy **317 files**, OpenAPI **227 paths**, lint/types and Vite **8.2.2** production build PASS. Head advances to `0057` (**58 revisions**), Reactivation to **96%**, Saved Views to **55%**, API to **96%** and full scope to **75.2%** (median **86%**). |
| PAR-VIEW-02 evidence | Shared Contacts/Reactivation view/API/migration **16/16** and focused UI **19/19** PASS. Full backend **1564 passed / 6 MySQL-only skipped / 0 failed in 506.04s**; full frontend **44 files / 863 tests**; static **6/6**, strict mypy **319 files**, OpenAPI **229 paths** and Vite **8.2.2** build PASS. Head advances to `0058` (**59 revisions**), Contacts to **98%**, Saved Views to **65%**, API to **97%** and full scope to **75.6%** (median **86%**). In-app local-page access was denied, so authenticated visual/WCAG/device review remains pending rather than PASS. |
| PAR-VIEW-04 evidence | Focused KYC API/migration/OpenAPI/permission contracts **12/12** and focused KYC UI **2 files / 8 tests** PASS. Full backend **1574 passed / 6 MySQL-only skipped / 0 failed in 450.05s**; full frontend **46 files / 870 tests**; static **6/6**, strict mypy **321 files**, OpenAPI **233 paths** and Vite **8.2.2** build PASS. Head advances to `0060` (**61 revisions**), KYC to **90%**, Saved Views to **85%**, API to **99%** and full scope to **76.5%** (median **86%**). Protected-media/scale and authenticated visual/WCAG/device review remain host gates. |
| PAR-VIEW-05 evidence | Focused Reports saved-view API/migration/OpenAPI/permission contracts **12/12** and focused Analytics UI **41/41** PASS. Full backend **1579 passed / 6 MySQL-only skipped / 0 failed in 413.35s**; full frontend **47 files / 875 tests**; static **6/6**, strict mypy **322 files**, OpenAPI **235 paths** and Vite **8.2.2** build PASS. Authenticated local desktop/390px previews verified a team view and responsive management sheet with factual empty report data. Head advances to `0061` (**62 revisions**), Executive Reports to **80%**, Saved Views to **95%** and full scope to **77.0%** (median **88%**). Representative-data WCAG/scale and target-host gates remain pending. |
| Frontend evidence | ESLint PASS · TypeScript PASS · **47 Vitest files / 875 tests** PASS · production build PASS. |
| Bundle evidence | Current Analytics chunk `433.88 kB` / gzip `122.56 kB`; production build PASS. |
| Automation bundle evidence | `AutomationPage` chunk `52.47 kB` / gzip `13.23 kB`; production build PASS. |
| M13 contract | ADR-0020, ADR-0021 and Design Document 33 remain frozen and authoritative |
| Module 13 implementation | `52%` evidence-based estimate — **unchanged**. Remediation restores intended behaviour and adds a deployment definition; it delivers no new product capability |
| QR provider | WAHA 2026.7.2 (CORE, NOWEB, Apache-2.0) — **CONDITIONALLY CERTIFIED — REMAINING HOST/PHONE EVIDENCE REQUIRED**, unchanged by QR-09L. The pinned digest has real pairing and inbound-text evidence, but the new correlated outbound/ACK, persistence/logout and target-host gates are incomplete, so certification approval does not advance. Declared capabilities remain `HEALTH`, `QR_AUTH`, `SESSION_STREAM`, `TEXT`, `SESSION_RECONNECT`, `SESSION_LOGOUT`; `BULK`/`CAMPAIGNS`/`TEMPLATE` permanently prohibited and test-enforced. No MEDIA/INTERACTIVE/REACTION/LOCATION/CONTACT. |
| Next Module 13 milestone | Send exactly one new QR09-L-ACK text from the actual Unified Inbox, then wait for the owner to receive/read and reply `QR09L ACK TEST READ`. Only genuine emitted ACKs may be correlated. Linked-session restart/reconnect, logout/re-authentication, Meta rotation and supported-browser/target-host evidence remain pending. |
| Host evidence | Repository/local-host evidence plus a fresh disposable production-topology run: real MySQL/Redis, migration, API, three workers, scheduler, frontend and edge all healthy; real Chromium journey, 30-sample canary, Redis-down readiness and correlated-log checks pass. Genuine target-host TLS/secrets/monitoring/backup-restore/UAT and the full browser/device matrix remain pending; no live-host Production Ready claim. |
| Worktree expectation | CORE-11A/11B/11C plus UI parity and PAR-AUTO-04/05/06/07/08/09/10/11/12/13/14/15/16/17/18/19/20/21 validate Settings/Inbox/Contact/Message/Task/Tag/Notification/Reactivation lifecycle behavior, intervention actions, five bounded automatic trigger paths, one optional approved Condition on event-backed paths, one Yes/No split with one or two ordered distinct internal effects per side, up to four linear event-safe internal effects, one durable Delay and same-customer Message-received, Task-completed or Lead-stage-changed Wait. Migrations `0044`–`0048` are additive; no new RBAC code, queue, provider configuration, customer send, session storage, QR, physical-phone action, reference artifact or `.claude/` ownership change. |
| Last update | `2026-09-13` (Asia/Kolkata) |

## QR-09F — Provider-Outage QR Availability Projection Remediation (REPOSITORY/RUNTIME VALIDATED)

- **QR-09-D8 (Major) reproduced:** with the real WAHA container stopped and one existing provider
  session, the application projected `provider_status: SCAN_QR_CODE` and `qr_available: true` from
  durable/stale facts. The frontend mounted the QR flow and repeatedly attempted the provider QR
  route during the outage.
- **Remediation:** reconciliation returns typed observation outcomes. QR availability requires a
  current live `SCAN_QR_CODE` observation; an outage projects null provider status, no action,
  `provider_unavailable` and safe retry text. Durable pairing/reauthentication truth is unchanged,
  and provider-session-missing remains its own state. Frontend outage priority prevents QR,
  creating, connecting and reconnect views from outranking current reachability.
- **Real runtime proof:** real MySQL, Redis, backend/frontend and the exact certified WAHA digest.
  A genuine outage remained active for more than three polling intervals with zero QR-handler
  requests. Restart restored the same container, persistent volume, single provider session and
  durable application session; a legitimate in-memory application QR fetch then returned PNG with
  private/no-store controls. No QR was shown, printed, stored or scanned.
- **UI evidence:** actual local 1920×1080 and 390×844 browser captures show the truthful unavailable
  state, no QR/action, no horizontal overflow and keyboard-reachable retry. This is not target-host
  or full supported-browser evidence.
- **Regression/gates:** focused backend 31 PASS and frontend QR 28 PASS. Full release gate **23/23
  PASS** in 474.4s: backend **1408 passed**, frontend **798 passed**, OpenAPI drift, builds,
  SAST/audits, source secret/IaC, certified WAHA health/QR/webhook gates, production contracts,
  image scans and SBOMs.
- **Boundary:** QR-09D remains externally preserved, unapplied and `PARTIAL`; QR-09 remains
  `PARTIAL (BLOCKED)`. Meta rotation is **PENDING — OWNER DEFERRED**. `Host Validated`,
  `Provider Validated`, `Production Ready`: NO; provider certification/approval is unchanged.

## QR-09E — WAHA QR Content Negotiation Remediation (REPOSITORY/RUNTIME VALIDATED)

- **QR-09-D7 (Major) reproduced:** the QR request inherited the WAHA client's JSON default
  `Accept` header. The exact certified provider therefore returned `200 application/json` from
  `?format=image`; the adapter correctly rejected that non-image and the application surfaced a
  truthful `409` rather than exposing or persisting the response body.
- **Remediation:** JSON API calls retain `Accept: application/json`; only the binary QR request now
  sends `Accept: image/png`. Authentication, timeout/error mapping, no-store HTTP response controls,
  transient challenge handling and fail-closed content-type validation are unchanged.
- **Certified runtime proof:** a disposable, loopback-only container at the exact digest reported
  `2026.7.2` / `NOWEB` / `CORE`. JSON negotiation reproduced `200 application/json`; the repository
  client returned `200 image/png` with a valid PNG signature in memory. Two live application fetches
  also returned PNG with `no-store`/private cache controls. Exactly one provider session and one
  durable connection/session remained; no duplicate was created.
- **Privacy/storage boundary:** QR bytes were never displayed, logged, printed, written to disk or
  committed and no physical scan occurred. The disposable regression mounted no session volume;
  the governed `waha-sessions:/app/.sessions` volume was not removed or altered.
- **Regression/gates:** request-header, exact-byte, non-image, auth, provider-error, timeout and
  transport regressions pass. Full release gate **23/23 PASS** in 800.3s: backend **1407 passed**,
  frontend **796 passed**, OpenAPI drift, builds, SAST/audits, source secret/IaC, certified WAHA
  health/QR/webhook runtime checks, production contracts, image scans and SBOMs.
- **Boundary:** UI preview is not applicable; frontend source is unchanged. QR-09D remains separately
  preserved and `PARTIAL`; it was not reapplied. QR-09 remains `PARTIAL (BLOCKED)`. Meta rotation is
  **PENDING — OWNER DEFERRED**. `Host Validated`, `Provider Validated`, `Production Ready`: NO;
  provider certification/approval is unchanged.

## QR-09C — WAHA Webhook Delivery Wiring and Credential Hygiene (PARTIAL)

- **QR-09-D5 (Major):** the signed backend receiver existed, but neither Compose service configured
  WAHA's sender. No global or per-session URL/events/HMAC were present, so provider events had no
  path into the existing webhook/MessageService/Unified Inbox authorities.
- **Design:** one global webhook only. Production callback is private `api:8000`; development uses
  Docker's internal host gateway. Events are exactly `message`, `message.any`, `message.ack`.
  Per-session webhooks remain absent because WAHA combines both modes (duplicate delivery) and would
  persist the HMAC key with session configuration.
- **Authentication/retry:** a dedicated `WAHA_WEBHOOK_HMAC_SECRET` feeds the provider sender and the
  unchanged fail-closed backend verifier. Raw-body SHA-512 is preserved. Retry configuration is
  explicit: 15 attempts, constant two-second delay. No Meta credential is reused.
- **Runtime evidence:** the exact certified image's own `WebhookSender` reached a private `api:8000`
  receiver, produced valid raw-body SHA-512 HMAC, retried one controlled `503` with byte-identical
  body/stable request id, then delivered a signed ACK after restart. Exact provider identity remained
  `2026.7.2` / `NOWEB` / `CORE`; zero sessions before/after; no QR or phone interaction.
- **Regression/gates:** full release gate **22/22 PASS** in 525.3s; backend 1399/0 skipped, frontend
  796, source secret/IaC, dependency, build, Compose, release, image, vulnerability and SBOM gates.
- **META WEBHOOK_VERIFY_TOKEN ROTATION:** **PENDING — OWNER DEFERRED**
- **Classification:** `QR-09C: PARTIAL — D5 REMEDIATED, META TOKEN ROTATION PENDING` ·
  `QR-09: PARTIAL (BLOCKED)` · `Host Validated: NO` · `Provider Validated: NO` ·
  `Production Ready: NO`. Provider certification/approval is unchanged.

## QR-09B — WAHA Runtime Healthcheck Remediation (REPOSITORY VALIDATED)

- **QR-09-D4 (Major) reproduced:** both Compose files invoked `wget`, which does not exist in the
  exact certified image; Docker health output was `exec: "wget": executable file not found in
  $PATH`, so the container remained `starting` although the provider API was responsive.
- **Certified-image inventory:** entrypoint `/usr/bin/tini --` with `/entrypoint.sh`; Node
  `v24.11.1` (built-in fetch available), `/bin/sh`, Bash `5.2.15`, and curl `7.88.1` exist; wget,
  BusyBox and Python do not. `/health` and `/api/server/status` require authentication (`401`
  without a key); provider-owned `/ping` is unauthenticated and returns `200 {"message":"pong"}`.
- **Remediation:** exec-form curl probe against loopback `/ping`, `--fail`, five-second maximum.
  It exposes no key and asserts process/API liveness only, not pairing/session `WORKING` state.
- **Runtime proof:** exact digest is WAHA `2026.7.2` / `NOWEB` / `CORE`; Docker transitions to
  `healthy`, the exact command succeeds against `/ping`, the same command returns non-zero against
  unavailable `127.0.0.1:1`, and Docker returns to `healthy` after restart.
- **Topology/storage:** development remains loopback-only; production publishes no WAHA port;
  restart policy is unchanged; the same named `waha-sessions` volume remains at `/app/.sessions`
  with no pre-existing file removed. No service depends on WAHA health, so no coupling was added.
- **Regression/gates:** `scripts/validate_waha_healthcheck.py` enforces the Compose and real-runtime
  contract in the release gate. All 21 release gates pass: backend 1397, frontend 796, source
  secret/IaC and dependency scans, builds, Compose/release/image contracts, app-image scans/SBOMs.
  The exact WAHA image separately passes the pinned Trivy image gate.
- **Boundary:** no QR displayed/scanned, no physical-phone evidence, no application/UI/capability
  change. QR-09 remains `PARTIAL (BLOCKED)`; provider certification approval and Host/Provider/
  Production Ready classifications are unchanged.

## QR-09A — Production Validation Remediation (REPOSITORY VALIDATED)

- **Scope:** exactly the blockers QR-09 recorded — nothing else. QR-09's own failure evidence is
  preserved verbatim below; a remediation milestone fixes causes, it does not retroactively pass the
  validation that found them.
- **D1 — `0043` is reversible on real MySQL.** The downgrade released `uq_conv_endpoint_contact`
  before `fk_conv_channel_endpoint`, but InnoDB borrows that index for the foreign key (MySQL 1553).
  All conversation-side drops now run in one batch in dependency order. **No new revision**: only the
  broken `downgrade()` body changed. A live-MySQL up/down/up regression proves seeded Meta data
  survives byte-for-byte, the recorded version is truthful at each step, and no `0043` column, index
  or constraint is left behind.
- **D2 — provider-up/session-absent is a recoverable state, not a 500.** `WahaSessionNotFound`
  narrows the provider's 404 at the client boundary; the service treats it as an observation and
  leaves durable pairing truth untouched, projecting the divergence instead. A previously paired
  connection is told it needs a fresh scan; a fresh one gets the ordinary connect-and-scan path.
  Reconnect refuses with `409`. A status read is proven to issue no write and fetch no QR. Genuine
  outages still report `provider_unavailable`, so QR-06 semantics are intact. The UI no longer
  renders this as "Starting the session…".
- **D3 — oversized delivery answers `413`.** The 1 MiB refuse-before-hashing bound is unchanged;
  only the missing HTTP mapping was added. This stops WAHA's at-least-once retry from looping on a
  `5xx`.
- **G1 — required OpenAPI drift gate is green.** Artifact regenerated canonically; 207 paths
  unchanged, one additive D2 property, generated client types back in sync. The historical
  "key-order/resolver" explanation is annotated as inaccurate rather than rewritten.
- **I1 — WAHA has a governed deployment.** Digest-pinned service in both compose files behind a
  `waha` profile, publishing **no port** in production, with a persistent `waha-sessions` volume at
  `/app/.sessions` and a full operator runbook (`deploy/DEPLOYMENT.md` §15). A real
  `docker compose restart waha` preserved the session; the same image without the volume returned
  `404 Session not found` — confirming the volume is what closes D2's underlying cause.
- **S1 — `cryptography` advisory resolved.** Floor raised `>=43` → `>=50` (no lock file exists, so
  the floor is the only guard); `pip-audit` reports no known vulnerabilities.
- **Unchanged:** migration head and revision count, OpenAPI path count, RBAC catalog, WAHA
  capabilities and prohibited capabilities, Meta behaviour, and the provider certification record.
- **Still outstanding (why QR-09 stays PARTIAL):** physical-phone provider E2E — including whether
  scanned credentials survive a restart, which was **not** demonstrated (only pre-pairing session
  persistence was) — and the supported-browser/target-host matrix. Running-app screenshots could not
  be captured in this environment; the state was verified live through the rendered DOM at desktop
  and mobile viewports instead.
- **Classification:** `Repository Validated: YES` for QR-09A · `Host Validated: NO` ·
  `Provider Validated: NO` · `Production Ready: NO`.

## QR-09 — Production Validation (PARTIAL — BLOCKED)

- **Scope:** validate QR-08's contract against production-representative infrastructure — real
  MySQL, real Redis, the real pinned WAHA container — instead of QR-08's own SQLite-only preview
  evidence. Validation only; no feature, migration, route, or capability work.
- **Environment:** MySQL `8.0.46` and Redis `7.4.9` via this repository's own `docker compose`;
  WAHA `2026.7.2`/`NOWEB`/`CORE` at the exact certified digest
  (`sha256:33ecd1b782b2708db2ff1d366f51608889a036e76332dceae3fbbe3f10f2d75e`). No physical handset
  was available, so physical-phone pairing/inbound/outbound/ACK-chain evidence is not claimed.
- **Closed a QR-08 evidence gap:** QR-08's preview recorded a `503 idempotency_unavailable` because
  its throwaway environment had no Redis. Against real Redis: normal send succeeds; a duplicate
  `Idempotency-Key` replays the original response with no second row; 6 concurrent requests sharing
  one key produce exactly one message; a Redis outage fails closed (`503`, zero rows); a Redis
  restart recovers.
- **Proved the decisive QR-08 dedupe claim on real MySQL, not only SQLite:** one underlying provider
  message delivered as `message`×2 + `message.any`×2 (4 deliveries) produced 4 `webhook_events` rows
  (event-layer persistence is intentionally at-least-once) but exactly **1** stored `messages` row.
- **QR-09-D1 (Major, open):** `0043_conversation_channel_endpoints`'s `downgrade()` fails on real
  MySQL — `uq_conv_endpoint_contact` is dropped before the foreign key that depends on it
  (`MySQL 1553`). The upgrade path itself is unaffected and independently verified to preserve
  existing Meta data byte-for-byte. Same defect class as the pre-existing, separately tracked
  `0036`/`0040` real-MySQL downgrade defect.
- **QR-09-D2 (Major, open):** `GET /channels/whatsapp-qr/session` returns `HTTP 500` when the real
  provider is reachable but the named session no longer exists there (reproduced deterministically
  after a provider restart with no persistent session storage) — `ChannelApiError`/404 is not
  translated into a truthful recoverable status, unlike genuine provider outage, which is handled
  correctly and distinctly.
- **QR-09-D3 (Minor, open):** an oversized webhook body is correctly refused before hashing but
  surfaces as `500` instead of a 4xx.
- **Required OpenAPI drift gate genuinely fails**, but this milestone **corrects** the previously
  recorded explanation: investigation proved generation is deterministic and the committed/generated
  JSON parse to exactly-equal objects (207 paths both); the sole byte difference is ASCII-escaping.
  Not a resolver key-order artifact as previously stated elsewhere in this repository's governance.
- **Unchanged:** migration head, OpenAPI path count, RBAC catalog, WAHA capabilities, prohibited
  capabilities, the WAHA selection/certification record. QR-01 through QR-08 unaffected; QR-08
  remains `COMPLETE`.
- **Classification:** `Repository Validated: NO` (a required gate is red and two Major defects are
  open) · `Host Validated: NO` · `Provider Validated: NO` · `Production Ready: NO`.
- **Next milestone (not started):** `QR-09A — Production Validation Remediation` — fix D1/D2/D3,
  regenerate `openapi.json` with consistent ASCII-escaping, add a WAHA compose/deployment service
  with persistent session storage, triage the `cryptography` advisory, rerun QR-09, then pursue
  physical-phone and full browser/host evidence.

## QR-08 — Unified Inbox integration

- **Scope:** wires QR-04's inbound and QR-05's outbound/ack translation into the **same** existing
  `Conversation`/`Message`/`MessageService`/`ConversationService`/`InboxQueryService`/`SendService`
  authorities Meta already uses — not a second Inbox. Reuses the M13-03 `channel_endpoints` table
  QR-07 never populated (`WhatsAppQrService.connect()` now creates one idempotently).
- **Additive migration (`0043`):** `conversations`/`messages`/`webhook_events` gain a nullable
  `channel_endpoint_id`; `conversations.phone_number_id` widens to nullable, guarded by
  `ck_conv_endpoint_owner` (exactly one owner). No column dropped or renamed; no existing row
  changed.
- **Inbound stored-message dedupe is endpoint-scoped + canonical-provider-id, independent of
  event-level dedupe:** `message`/`message.any` (same envelope, two valid events per QR-04) collapse
  to one stored row; a same-event redelivery collapses too; the same provider id on two different
  endpoints does not collide.
- **Outbound routing is entirely server-derived.** `SendService.accept_for_conversation` resolves
  the provider from the conversation's own durable ownership; `MessageSendRequest.conversation_id`
  carries no provider field for a client to forge. A WAHA send that cannot be confirmed is marked
  `failed`/`indeterminate`, never auto-retried.
- **WAHA composer refuses to send truthfully** when the session is not `ACTIVE`+`PAIRED`, reusing
  QR-07's own live status read (no automatic reconnect from opening a conversation).
- **OpenAPI 206 → 207 paths** — `POST /webhooks/waha`, the WAHA analogue of the pre-existing
  `/webhooks/whatsapp` route QR-04 never got an HTTP route wired to.
- **Two real defects found and fixed**, both pre-existing in already-shipped QR-06/QR-07 code:
  QR-07's `_REAUTH_PAIRING` incorrectly included `UNPAIRED` (diverged from QR-06's own canonical
  definition); QR-04's `message.ack` classified `UNKNOWN` despite QR-05 already having built the
  translator for it.
- **Unchanged:** Meta behaviour, RBAC catalog, prohibited capabilities
  (`BULK`/`CAMPAIGNS`/`TEMPLATE`), no MEDIA/INTERACTIVE/REACTION/LOCATION/CONTACT for WAHA.
- **Still pending:** QR-09 production validation. History and media transfer remain unimplemented
  and are not assigned to a delivered milestone.
- **Known limitation:** the existing Meta-number-scoped analytics rollup excludes WAHA
  conversations rather than counting them under a fabricated dimension; QR-08 adds no WAHA
  analytics.

## QR-07 — WhatsApp Scan/Connect interface

- **Scope:** the first real operator-facing screen over the WAHA adapter (QR-01..06), bridging its
  live provider I/O to the existing M13-03/04/05 connection/session/pairing control plane. 6 new
  routes, gated on the pre-existing `channels:read`/`channels:authenticate` permissions.
- **Single-organization scope (ADR-0021):** one `WAHA_ORGANIZATION_ID`; every other organization,
  and an unconfigured deployment, see the identical `configured=false`.
- **No new persistence:** reuses `channel_connections`/`channel_sessions` from M13-03/04. No
  migration.
- **QR still never persisted:** fresh per request, `no-store`, held client-side only as a
  revoked-on-replace object URL.
- **Real M13-05 constraints surfaced and respected while integrating** (not worked around):
  pairing transitions require the session to still be `INITIALIZING`/`WAITING_FOR_PAIRING`;
  `PairingState.PAIRED` is terminal (logout registers a fresh revision rather than reversing one);
  `SessionManager.acquire_lock` refuses a `PAUSED` session.
- **OpenAPI 200 → 206 paths** — authorized by this milestone, unlike QR-01..06's own invariant.
- **Unchanged:** migration head `0042` (43 revisions), RBAC catalog, Meta behaviour, prohibited
  capabilities. No Production Ready, Host Validated or M13-07 claim.
- **Still pending:** QR-08 Unified Inbox integration, QR-09 production validation. History and
  media transfer remain unimplemented and are not assigned to a delivered milestone.
- **Known limitation:** retrying an expired, never-scanned QR surfaces the provider's real
  "session already exists" error rather than a fabricated retry success; a dedicated provider
  restart path is not built in this milestone.

## QR-06 — WAHA session recovery, health and teardown

- **Scope:** start/stop/logout behind a runtime lease, bounded reconnect planning, and a
  session-scoped health projection. Declares `SESSION_RECONNECT` and `SESSION_LOGOUT`.
- **Never guesses from ambiguous status:** reconnect is planned from the platform's durable pairing
  record, so the provider's `STARTING` — which QR-02 proved means either a fresh session or a paired
  one resuming — can never be read as evidence a session is unpaired.
- **Outage-safe:** an unreachable provider is "unknown", never "unpaired"; durable truth survives.
- **STOP keeps credentials; LOGOUT invalidates them** and deliberately produces re-auth-required
  truth that nothing auto-repairs. Session deletion is not exposed.
- **Ownership reuses the existing lease/fencing authority** — no second runtime ownership system.
- **Runtime registration is opt-in:** importing the package still registers no runtime.
- **Unchanged:** migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200
  paths with zero QR routes, RBAC, generated types, frontend, prohibited capabilities. No Production
  Ready, Host Validated or M13-07 claim.
- **Still pending:** QR-07 UI, QR-08 Unified Inbox, QR-09 production validation. History and media
  transfer remain unimplemented, and there is still no QR route or operator UI.

## QR-05 — WAHA send path and delivery-state reconciliation

- **Scope:** outbound text through the configured session, canonical provider-id capture,
  acknowledgement translation onto the platform's existing monotonic status vocabulary, and an
  endpoint-scoped reconcile-before-resend primitive. Declares `TEXT`.
- **Monotonic by reuse:** `STATUS_RANK`/`advances()` already make delivery one-way, so QR-05 only
  maps provider acks onto it. The certified out-of-order `DEVICE → SERVER → READ` ends at `read`;
  duplicate acks are no-ops; unknown acks make no state change.
- **Never blindly resends:** an uncertain transport outcome is surfaced as indeterminate. A resend
  is permitted only when reconciliation proves absence; a failed lookup stays indeterminate.
- **Endpoint-scoped:** one endpoint can never confirm or advance another's message, and no global
  provider-message lookup exists.
- **Unchanged:** migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200
  paths with zero QR routes, RBAC, generated types, frontend, prohibited capabilities, and the
  absence of a WAHA entry in `ProviderRuntimeRegistry`. No Production Ready, Host Validated or
  M13-07 claim.
- **Still pending:** QR-06 reconnect/health/teardown, QR-07 UI, QR-08 Unified Inbox, QR-09
  production validation. Media, history, interactive, reaction, location and contact are all
  unimplemented, and there is still no QR route or operator UI.

## QR-04 — WAHA webhook ingestion

- **Scope:** verify and normalize provider deliveries onto the **existing** `ChannelAdapter` webhook
  seam and `webhook_events` ingest authority. Declares `SESSION_STREAM`.
- **No parallel ingest path, no new route, table or migration** — the persist-first durability,
  dedupe and dead-letter behaviour already owned by `WebhookService` is reused, not duplicated.
- **Dedupe identity:** scoped by session and provider event type. Certification proved
  `envelope.id` alone is unsafe (one message arrives as both `message` and `message.any` sharing
  it) and that delivery is at-least-once with retries repeating every id. Determinism is proven by
  a concurrent test because `messages` is partitioned and MySQL cannot enforce the constraint.
- **Security:** signature verified before parsing, over raw bytes, constant-time, body bounded
  before hashing, unset secret rejects everything, unknown/malformed shapes fail closed to
  `UNKNOWN` and are dead-lettered rather than dropped.
- **Not pulled forward:** acknowledgements and outbound echoes are recorded, never applied —
  delivery state is QR-05. No teardown, history or media execution.
- **Unchanged:** migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200
  paths with zero QR routes, RBAC, generated types, frontend, prohibited capabilities, and the
  absence of a WAHA entry in `ProviderRuntimeRegistry`. No Production Ready, Host Validated or
  M13-07 claim.
- **Still pending:** QR-05 send, QR-06 reconnect/health/logout, QR-07 UI, QR-08 Unified Inbox,
  QR-09 production validation. There is still no QR route or operator UI.

## QR-03 — WAHA QR pairing

- **Scope:** create a WAHA session with the certified store configuration, fetch the transient QR
  challenge a handset scans, and report provider-neutral pairing state. Declares `QR_AUTH`.
- **Up, never down:** no stop, restart, logout or delete exists on adapter or client. Teardown is
  QR-06, so nothing shipped so far can destroy a working pairing.
- **QR is never persisted or logged:** `WahaQrChallenge` is a transient value that redacts its own
  bytes, preserving M13-05's boundary that QR images and challenge bytes are deliberately absent
  from persistence.
- **`fullSync` camelCase, centrally built:** certification proved the snake_case spelling is
  accepted and then silently ignored, leaving a healthy-looking session with no history.
- **Pairing safety:** an ambiguous provider status (`STARTING`/`STOPPED`/`FAILED`) yields no pairing
  claim, so durable pairing truth is never overwritten by inference.
- **Unchanged:** migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200
  paths with **zero** QR routes, RBAC, generated types, frontend, prohibited capabilities, and the
  absence of a WAHA entry in `ProviderRuntimeRegistry`. No Production Ready, Host Validated or
  M13-07 claim.
- **Still pending:** QR-04 webhook ingestion, QR-05 send, QR-06 reconnect/health/logout, QR-07 UI,
  QR-08 Unified Inbox, QR-09 production validation. There is still no QR route or operator UI, so
  QR login is not usable by an operator and is not claimed to be.

## QR-02 — WAHA session lifecycle read and provider-neutral mapping

- **Scope:** read one named WAHA session's status and translate it into the platform's own
  `SessionState`/`PairingState` vocabulary. One authenticated read; a pure mapping; no runtime.
- **Read-only and capability-neutral:** nothing is created, started, stopped, restarted, paired or
  logged out; capabilities remain exactly `HEALTH`. Adapter and client are asserted to expose no
  session-mutation or QR method.
- **Mapping:** `SCAN_QR_CODE → waiting_for_pairing/pairing_available`; `WORKING → active/paired`;
  `STARTING`, `FAILED`, `STOPPED` → `initializing`/`degraded`/`paused` with **no** pairing claim,
  because the status alone cannot determine whether credentials exist. `FAILED` is deliberately not
  terminal — certification recovered it with a controlled restart.
- **Evidence basis:** every status and transition encoded here was observed during physical-phone
  certification against `devlikeapro/waha@sha256:33ecd1b7…` (2026.7.2 / NOWEB / CORE), not read off
  documentation. Tests are hermetic; the payloads they assert are the captured real shapes.
- **Unchanged:** migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200
  paths, RBAC, generated types, frontend, and the absence of a WAHA entry in
  `ProviderRuntimeRegistry`. No Production Ready, Host Validated or M13-07 claim.
- **Still pending at QR-02:** QR-03 QR pairing (since delivered), QR-04 webhook ingestion, QR-05
  send, QR-06 reconnect/health, QR-07 UI, QR-08 Unified Inbox, QR-09 production validation.

## QR-01 — WAHA provider adapter foundation

- **Scope:** a registered `waha` adapter that can perform **one thing** — an authenticated probe of
  the WAHA *server* (version/engine banner and `/health`) — plus deterministic error mapping and an
  engine/version guard. Nothing else. No WhatsApp session is created, resumed or inspected; no QR is
  requested, generated, persisted or logged; no phone is paired; no webhook is received; no message
  is sent or ingested; no media or history is transferred; no session worker or reconnect runtime
  exists. `ProviderRuntimeRegistry` deliberately has **no** WAHA runtime.
- **Connector identity:** `connector_type = "waha"`, `channel_type = "whatsapp"` — a second
  *implementation* of the same channel family behind the existing `ChannelAdapter` seam, never a
  second channel and never a parallel hierarchy (ADR-0020 invariant 1).
- **Capabilities are deliberately minimal.** Only `HEALTH` is declared, because only `HEALTH` is
  both implemented here and evidenced end to end. The QR-00 spike proved the *provider* supports QR
  pairing, sessions, media and history, but a provider endpoint existing is not the same as this
  adapter being able to use it, and neither is the same as a paired account working. Declaring
  `QR_AUTH`, `SESSION_*`, `TEXT`, `MEDIA*`, `HISTORY_SYNC`, `INTERACTIVE`, `REACTION`, `LOCATION` or
  `CONTACT` would let the CRM offer an action that cannot run, so all are withheld until the
  milestone that implements them.
- **Permanently prohibited:** `BULK`, `CAMPAIGNS`, `TEMPLATE` — forbidden for this provider forever
  (ADR-0020 section 5, ADR-0021, owner Class B approval), recorded in `PROHIBITED_CAPABILITIES` and
  enforced by tests no later milestone may quietly relax.
- **Server health is not session health.** `authenticate()`/`status()` return `connected=False` with
  an explicit "No WhatsApp session" detail, and `health_signal()` states it reports server health
  only. A perfectly healthy WAHA server with zero paired sessions cannot message, and the adapter
  never implies otherwise.
- **Configuration:** `WAHA_BASE_URL`/`WAHA_API_KEY` are empty by default with **no default key**;
  the application boots normally with neither set. Registration is inert — it opens no socket, needs
  no credential and starts no runtime — so the provider is resolvable but disabled. Every QR feature
  flag remains off by default.
- **Deterministic error mapping** (each shape observed against the real certified build): timeout
  and unavailable map to `ChannelTransportError` with distinct messages; 401/403 to
  `ChannelAuthError`; 5xx and other reached errors to `ChannelApiError` carrying the status;
  malformed JSON, unexpected content type (the real server answers `text/html` on the root path) and
  non-object JSON to `ChannelApiError`. Unconfigured raises `ChannelConfigError` *before* any socket
  is opened.
- **Version/engine safety:** certified baseline `2026.7.2`; only `NOWEB` approved. An unexpected
  engine **fails closed** (`WahaEngineNotApproved`) because payload shapes differ between engines.
  Version drift is *reported, never auto-corrected* — nothing upgrades a provider on its own, and
  the evidence spike pinned an immutable digest rather than a floating tag.
- **Security:** the API key is sent only as `X-Api-Key`, never logged, never echoed into an
  exception, and masked in `repr`. Provider error bodies are never quoted (they are
  attacker-influencable); the error log records status and path only. No QR material exists to
  persist. Meta behaviour and the QR-00 endpoint-scoped provider-message identity are untouched.
- **Real validation:** an isolated `devlikeapro/waha:noweb-2026.7.2`
  (digest `sha256:33ecd1b7...`) was run locally, bound to `127.0.0.1` on its own network, and the
  committed adapter/client driven against it — 11/11 checks passed covering authenticated
  version/engine, authenticated health, wrong-key and missing-config rejection, unavailable, timeout,
  non-JSON handling and the engine guard. **No session was created, no QR requested, no phone paired,
  nothing sent or received.** The provider was then torn down and all spike credentials and artefacts
  removed; the repository's committed `docker-compose.yml` was not edited.
- **Unchanged:** migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200
  paths, RBAC, generated types, frontend. No Production Ready, Host Validated, provider-certified or
  M13-07 claim.
- **Still pending at QR-01:** QR-02 session lifecycle (since delivered), QR-03 QR endpoint/state,
  QR-04 webhook ingestion, QR-05 send, QR-06 reconnect/health, QR-07 UI, QR-08 Unified Inbox,
  QR-09 production validation, and physical-phone certification evidence (since PASSED 2026-08-08).

## QR-00 — WAHA Class B provider selection and provider-message identity foundation

- **Scope:** foundation only. QR-00 adds a provider-selection governance record, hardens
  provider-message identity/tenant isolation, and adds a provider-neutral re-authentication health
  projection. **It does not implement QR login.** No WAHA adapter, client, Docker service, provider
  runtime registration, QR API, QR image endpoint, QR persistence, QR frontend, webhook endpoint,
  inbound ingestion, outbound send, history sync, media sync, session worker or reconnect runtime
  exists. Only `meta_cloud` is a registered adapter.
- **Provider selection:** WAHA 2026.7.2 (tier CORE, engine NOWEB, Apache-2.0) is selected as the
  ADR-0021 Class B candidate and is **CONDITIONALLY CERTIFIED — HOST/PHONE EVIDENCE REQUIRED**. The
  owner's Architecture Approval, Security Approval and explicit Risk Acceptance — including
  acceptance that WhatsApp may restrict or permanently ban connected numbers — are recorded verbatim
  in `docs/evidence/provider-evaluations/waha-class-b-selection-record.md`. NOWEB was chosen because
  it is the engine the certification spike actually exercised.
- **Message identity root cause:** `MessageRepository.get_by_wamid(wamid)` resolved a provider
  message id **globally**, with no organization, connection or endpoint filter. Meta's `wamid` is
  globally unique so this was survivable with a single provider; a QR/multi-device provider's ids are
  session-scoped and may legitimately repeat across endpoints, which would have allowed a second
  provider to resolve — or a delivery receipt to advance — another endpoint's or another tenant's
  message. Contradicted ADR-0020 ("provider message identity is scoped by connection/endpoint").
- **Fix:** replaced by `get_by_provider_message_id(provider_message_id, *, phone_number_id)`. The
  endpoint scope is keyword-only and required, so an unscoped lookup cannot be written; there is
  deliberately no global variant. `phone_numbers.organization_id` is `NOT NULL`, so the endpoint
  transitively pins the tenant. All three call sites (inbound dedupe, status reconciliation, dev
  fixtures) pass an endpoint they already held; `apply_status` now takes the endpoint the callback
  arrived on.
- **No backfill was required.** `messages.organization_id` and `messages.phone_number_id` have been
  `NOT NULL` since `0016_conversations_messages`, so every existing row already carries explicit,
  authoritative endpoint ownership — nothing had to be derived or invented. Verified against the
  live database: 191 messages, 0 null owners, 0 orphaned endpoints, 0 organization mismatches, 0
  duplicate `(phone_number_id, wamid)` pairs.
- **A UNIQUE constraint is impossible, and that is recorded rather than worked around.** `messages`
  is `PARTITION BY RANGE COLUMNS(created_at)`; MySQL requires every unique key on a partitioned table
  to contain the partitioning columns (error 1503, reproduced on MySQL 8.0.46 against this schema).
  Including `created_at` would permit the very duplicate the rule exists to prevent. Uniqueness
  therefore remains enforced by the scoped read plus the persist-first ingestion path, exactly as it
  already is for Meta. Migration `0042_scope_provider_message_identity` adds only the supporting
  non-unique index `ix_msg_endpoint_wamid (phone_number_id, wamid)`.
- **Re-authentication health:** implemented as a **derived projection**, not a new persisted state.
  `app/channels/attention.py` projects the existing `ProviderHealthState` + `SessionState` +
  `PairingState` into the four Doc 33 §6.1 operator signals (Healthy / Warning / Critical /
  Re-auth Required). Adding a fourth stored health value would have duplicated information those
  columns already carry and required widening `CHECK` constraints on three columns across three
  tables. Re-auth outranks observed health; `TERMINATED` never reports re-auth.
- **Meta compatibility:** unchanged. Meta webhook ingestion, inbound dedupe, delivery/read
  reconciliation and the Inbox are all covered by the existing suites, which pass unmodified.
  OpenAPI remains 200 paths; no route, schema, RBAC entry or generated type changed.
- **Still pending, unchanged by QR-00:** QR-01 provider adapter, QR-02 session lifecycle, QR-03 QR
  endpoint/state, QR-04 webhook ingestion, QR-05 send, QR-06 reconnect/health, QR-07 UI, QR-08
  Unified Inbox integration, QR-09 production validation, and physical-phone certification evidence.
  No Production Ready, Host Validated, provider-certified or M13-07 claim is made.

## Alembic version-table MySQL fix — support long revision ids

- **Verified failure:** `alembic upgrade head` on a real MySQL 8 database (the repository's own
  `docker compose up -d` MySQL/Redis, per `README.md`) failed transitioning
  `0035_notification_center → 0036_customer_identity_resolution` with
  `DataError: Data too long for column 'version_num'`. Root cause: Alembic's own bookkeeping table
  (`alembic_version.version_num`) defaults to `VARCHAR(32)`; this repository's revision identifiers
  are descriptive slugs, not short hashes, and `0036_customer_identity_resolution` (33 characters)
  is the first to exceed it. No real MySQL deployment had ever advanced past `0035_notification_center`.
- **Repair:** inserted `0035a_widen_version_table`, a new revision between `0035_notification_center`
  and `0036_customer_identity_resolution`, widening `alembic_version.version_num` to `VARCHAR(255)`
  on MySQL only (SQLite has no such enforcement; PostgreSQL is not part of this stack).
  `0036_customer_identity_resolution`'s `down_revision` was retargeted to point at it — its own
  revision id, schema body and behaviour are byte-for-byte unchanged. No revision was renamed,
  renumbered, squashed, reordered, or stamped past. The migration head remains
  `0041_channel_sync_control_plane`; the chain remains linear with a single head (42 revisions, was 41).
- **Verified on real MySQL 8** (`docker compose up -d`, throwaway per-test databases): a fresh
  database walks base→head cleanly; a database stamped at `0035_notification_center` (the exact
  historical failure point) upgrades to head cleanly; `python -m app.cli create-owner` succeeds
  immediately afterward. Also reproduced manually via the documented CLI workflow against a fresh
  `docker compose` MySQL instance (not just the automated tests) — identical result.
- **Regression coverage:** `backend/tests/test_migrations.py` gained three hermetic (SQLite)
  checks — single head, linear chain (no merges), and every revision id fits the widened column,
  with a tighter early-warning margin. `backend/tests/test_migrations_mysql.py` is new: three tests
  against a real, throwaway-per-test MySQL 8 database (fresh base→head, `0035`→head, create-owner
  after upgrade), skipped cleanly — never failed — when no MySQL server is reachable, so the
  hermetic default suite gains no new external dependency.
- **Preserved:** no application endpoint, model, schema, RBAC definition, OpenAPI path or generated
  frontend type changed; `scripts/export_openapi.py --check` and the full static quality gate both
  pass unchanged. Frontend untouched.
- **Remaining blocker, unchanged by this fix:** a real, populated `/chat-history` UI preview is
  still blocked — now solely by the separate, pre-existing absence of any approved development
  fixture mechanism for conversation/message data (creating real conversations requires either live
  Meta WhatsApp Business API credentials this environment does not have, or fabricating data
  outside approved commands, which remains out of scope). This migration fix removes the schema/
  auth blocker only; it does not by itself unblock the UI preview. No Host Validated or Production
  Ready claim is made.
- **Evidence scope correction (this follow-up):** the MySQL migration evidence above is
  repository/local-host evidence (a local `docker compose` MySQL 8 container), not genuine
  target-host validation; the "Host evidence" row previously overstated this as "target-host"
  verified, which has been corrected. Independently of this fix, a real-MySQL downgrade defect
  was found at `0036_customer_identity_resolution` and `0040_channel_sync_media_foundation`
  (`DROP INDEX ... needed in a foreign key constraint`) — pre-existing, not introduced by this
  commit, and recorded as a separate open defect; its remediation is not part of this follow-up.
  Automated CI execution of the live-MySQL migration tests also remains pending — no CI pipeline
  exists in this repository, so `test_migrations_mysql.py` currently only runs when a developer
  manually starts MySQL first.

## Dedicated Chat History read workspace over the existing conversation and message contract

- Added a `/chat-history` route (`inbox:read`) and matching navigation entry — a read-only
  list/detail workspace over the same `GET /conversations`, `GET /conversations/{id}` and
  `GET /conversations/{id}/messages` endpoints Live Chat and Customer 360 already read, reusing
  `useConversations`/`useConversation`/`useMessages`/`useAssignableUsers` from
  `features/inbox/api.ts` verbatim rather than opening a second query authority.
- Supports search, status, assignee, tag and a new `number` (channel) filter — the `number` field
  is an additive entry on the shared `InboxFilters`/`toListQuery` types Live Chat's own filters
  also use, so both surfaces read it from one definition. Cursor pagination for the conversation
  list and the existing infinite-query "Load older messages" control are both reused as-is.
- No assignment, status, tag, note or send control is exposed; a deep link opens the selected
  conversation in Live Chat, and a second deep link to the audit trail is shown only to
  `audit:read` holders.
- Date-range filtering and transcript export are honestly disclosed in the UI as not yet
  available, rather than offered as disabled controls — neither is backed by the current contract.
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path, RBAC
  definition or generated type changed. Closes the frontend half of `ROADMAP.md`'s `CORE-10`; its
  backend "Conversation query extensions" and export capability remain open follow-up.

## User Attributes management interface over the existing Custom Attribute contract

- Added a Settings → User Attributes panel over the existing `GET/POST/PATCH/DELETE
  /api/v1/custom-attributes` endpoints. The contract was already complete, but the frontend only
  ever issued the list read consumed by the Contacts filter bar, campaign audience rules and
  segment predicates, so no organization could define a typed field from the product itself.
- Create, edit and delete for `contacts:write` holders; `key_name` and `data_type` are immutable
  after creation, shown as read-only facts in the edit dialog via the same `DefinitionRow` pattern
  Canned Messages already established.
- Search, a data-type filter, and `Indexed`/`PII` shown as informational badges; the delete
  confirmation accurately states that every contact's stored value for the definition is removed
  too.
- Writes invalidate the exact `["custom-attributes"]` cache key the Contacts page already reads,
  plus the campaign/segment picker's key prefix, so a new attribute is selectable in both without a
  reload.
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path or generated
  type changed. Not a roadmap milestone, not M13-07.

## Canned Messages management interface over the existing Quick Reply contract

- Added a Settings → Canned Messages panel over the existing `GET/POST/PATCH/DELETE
  /api/v1/quick-replies` endpoints. The contract was already complete, but the frontend only ever
  issued the list read from the Message Composer's `/shortcut` picker, so the canned-message
  vocabulary could not be populated from the product on a new organization.
- Create, edit and delete for `inbox:write` holders; `shared` (Personal/Shared) is selectable only at
  creation and shown as read-only information in the edit dialog, matching the contract's
  immutable-after-creation rule.
- Search, a scope filter and a body preview over supported fields only; `usage_count` is read but not
  shown, since no send path increments it yet.
- Writes invalidate the exact `["quick-replies"]` cache key the composer already reads, so a new
  canned message is selectable there without a reload; a permission-correct link was added to the
  composer's empty state for `inbox:write` agents only.
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path or generated
  type changed. Not a roadmap milestone, not M13-07.

## Focused Tag Management audit follow-up: regression coverage and accessibility/error-state hardening

- Reset stale `create`/`update`/`delete` mutation state when a dialog opens, so a previous failure
  cannot resurface as a false error in a freshly opened dialog for a different tag.
- Moved the failed-delete error into the confirmation modal itself; it previously rendered behind
  the still-open modal's backdrop and was not genuinely visible at the moment of failure.
- Added regressions for cross-feature cache invalidation (real `useTags` hooks, one shared
  `QueryClient`, no new cache-key system), a duplicate-name conflict, a failed delete with retry, an
  explicit loading state, per-tag accessible row-action names, and a dedicated proof that a failed
  attempt's error does not resurface when a dialog is later opened for a different tag.
- Frontend only. Not a roadmap milestone, not M13-07; Settings/Tags/Attributes completion claims are
  unchanged from the prior remediation.

## Tag management interface delivered as a verified UI remediation

- Added a Settings → Tags panel over the existing `GET/POST/PATCH/DELETE /api/v1/tags` endpoints.
  The contract was already complete and permission-scoped, but the frontend only ever issued the list
  read, and attaching a tag takes the id of one that already exists — so the tag vocabulary could not
  be populated from the product and every shipped tagging surface stayed empty on a new organization.
- Create, rename, recolour, describe and delete are offered to `contacts:write` holders only; readers
  get the same table with no write control rendered at all.
- Only contract fields are shown. Tags have no status column, so the filter is usage derived from the
  existing `usage_count`; no backend field was invented and no reference-specific concept was copied.
- Frontend only: no backend file, migration, endpoint, permission definition, OpenAPI path or
  generated type changed. This is not a roadmap milestone, not M13-07, and does not complete Settings.

## M13-06B delivered provider-neutral history and media control plane

- Added lifecycle commands and factual observations over M13-06A persistence without introducing a
  provider executor, queue task, event consumer, API or frontend surface.
- Dedicated `channels:history_sync` RBAC and `omnichannel_qr_history` default-off flag protect writes;
  organization, endpoint ownership, declared capability and optimistic versions fail closed.
- Checkpoints enforce legal state transitions, monotonic counts/watermarks, live cutover boundaries and
  distinct resumable-failure versus fresh-completed-run behavior.
- Media references reuse existing `MediaAsset`/endpoint authorities, are idempotent by provider identity,
  require media capability and accept only non-secret factual observations.
- Workflow `31038662241` validates 985 backend tests, unchanged 200-path OpenAPI and unchanged frontend.

## UI-TASTE-05 completed owner review and merge readiness

- Full repository review found one verified Major release-candidate defect in the campaign lazy import
  graph; direct module imports remove the Rollup circular execution-order risk without changing behavior.
- Workflow `30982637585` passes all applicable repository gates, with main JavaScript at `199.78/54.87 kB gzip`.
- No verified repository-scope Blocker or Major defect remains. Moderate dependency advisories and all
  authenticated target-host visual/device/screen-reader/performance evidence remain explicitly pending.
- The branch is ready for explicit Owner Approval and Merge; it is not Host Validated or Production Ready.

## UI-TASTE-04 delivered responsive, accessibility and performance regression

- Added destination-specific KYC route protection under the existing Reactivation permission shell.
- Debounced global record search, kept empty keyboard state valid and reused shared modal focus
  behavior for the shortcut guide.
- Shared modal background scrolling and shared pagination narrow-layout overflow are corrected.
- Authenticated route modules now split behind the existing shell and guards; main JavaScript is
  199.78/54.87 kB gzip.
- Removed only the verified unused `ComingSoonPage`; no feature, API, migration, permission,
  architecture, governance or provider behavior changed.

## UI-TASTE-03B delivered Reactivation operational hierarchy

- `/reactivation` now resolves to the real CRM; primary section navigation exposes only connected
  destinations allowed by existing route permissions.
- Pipeline filters/work views/display/page are URL-backed, use shared controls, and request 25
  tenant-scoped records through an additive offset query under the existing stable ordering.
- Historical foundation routes redirect to factual filtered CRM or Contact import authorities.
- Existing transitions, assignment, reminders, KYC, Documents, Audit, Customer Timeline and
  optimistic concurrency are unchanged.
- Reactivation is `94%`; Module 13 remains `44%` and all provider-dependent behavior remains blocked.

## M13-06A delivered provider-neutral sync and media persistence foundation

- Added `channel_sync_checkpoints` for organization/connection/endpoint-scoped opaque cursor, watermark, cutover, progress, status, error and optimistic-concurrency facts.
- Added `media_channel_references` to map existing `MediaAsset` records to endpoint-scoped provider media identifiers with expiry, verification and transfer-state facts.
- Added tenant-scoped repositories, non-secret metadata enforcement, bounded list queries and database constraints using the existing model/repository authorities.
- No provider runtime, adapter, queue task, history execution, media fetch/upload, event consumer or API was introduced.

## M13-05 delivered provider runtime and pairing foundation

- Added provider-neutral runtime metadata, lifecycle, event and health contracts plus a thread-safe runtime registry that resolves executable behavior only through the existing `ChannelAdapter` seam.
- Added `ProviderRuntimeManager` registration/discovery/ownership, capability publication, health/lifecycle reporting, heartbeat integration, restart/recovery metadata and durable `ChannelSession` projection.
- Added a no-store `PairingManager` abstraction with governed `UNPAIRED`, `PAIRING_REQUESTED`, `PAIRING_AVAILABLE`, `PAIRING_EXPIRED`, `PAIRING_CANCELLED`, `PAIRED` and `ACTIVE` transitions; no QR payload, image, token or provider credential is persisted.
- Reused M13-04 lease/fencing, optimistic concurrency, session ownership, health, heartbeat, restart/recovery and Audit authorities rather than creating a second runtime truth table.
- Added disabled-by-default runtime/pairing flags, runtime/pairing RBAC permissions, additive migration `0039_qr_pairing_provider_runtime_foundation` and tenant-scoped expiry sweeps bounded to 1–1000 records.

## Preserved completed foundations

- M13-01 provider metadata/capability registries, M13-02 Contact identity, M13-03 connection/endpoint/encrypted-secret persistence and M13-04 session lifecycle/lease/fencing remain authoritative.
- Existing Contact, Inbox, Customer 360, Timeline, Notification Center, Analytics, message, media and Audit authorities remain unchanged.

## Preserved boundaries

- No QR image generation/scanning, WhatsApp login or protocol, provider adapter, history/message synchronization, incoming/outgoing messages, webhook runtime, routing, Inbox, Customer 360, Analytics or frontend behavior exists.
- No public API route, OpenAPI path, generated client surface, provider dependency, provider-specific table or runtime message storage was added.
- Pairing persistence contains state, timestamps and constrained reason codes only; secret references continue to use existing encrypted credential records.

## Validation boundary

Repository validation proves provider-neutral registry/runtime/pairing contracts, tenant/RBAC/flag
boundaries, durable session integration, lease/fencing enforcement, bounded expiry, health, heartbeat,
restart/recovery metadata, Audit redaction, additive migration, lint, typing, full regressions, source
security scans and unchanged frontend/API semantics. OpenAPI generation under the current unpinned
FastAPI/Pydantic resolver has a pre-existing JSON key-order mismatch at the untouched M13-04 baseline;
semantic schemas are equal and M13-05 introduces no route or schema.
<!-- Annotation (QR-09A, 2026-08-08): the attributed cause above is now known to be wrong, and is
     left in place as the historical record rather than rewritten. QR-09 proved OpenAPI generation
     is deterministic (identical SHA-256 across processes) and that key order was identical; the
     committed artifact differed only by JSON ASCII-escaping, because it had been written with
     `ensure_ascii=True` while the exporter emits `ensure_ascii=False`. QR-09A regenerated the
     artifact through the canonical exporter and the drift gate now passes. No resolver or
     dependency was pinned or upgraded to achieve this. -->
It does not prove a live provider,
QR scan/login, target-host multi-node runtime behavior, provider certification, production monitoring,
disaster recovery or rollout.

## Required remaining contract work

Target-host commissioning and provider certification remain mandatory. Live inbound events, history
execution, media transfer/processing, outbound messaging and unified operator experience remain
later gated milestones. M13-06A persistence plus M13-06B lifecycle controls do not satisfy provider certification or execute live work.

## Existing UI modernization state

UI-TASTE-03A, UI-TASTE-03B, UI-TASTE-04 and UI-TASTE-05 are repository-validated. Authenticated representative-data
visual/reference, screen-reader/device, and production-scale performance review remains pending.

## Maintenance rule

Written at M13-06B closeout. Provider certification PASSED on 2026-08-08 and the owner authorized the QR sequence, so certification no longer blocks the adapter and ingestion paths: QR-01 (adapter), QR-02 (session lifecycle), QR-03 (pairing) and QR-04 (webhook ingestion) are delivered. Still gated on a separate owner instruction each: QR-05 messaging/send, QR-06 reconnect/teardown, QR-07 provider UI, QR-08 Unified Inbox, QR-09 production validation. History retrieval and media-byte transfer remain unimplemented; no Production Ready or Host Validated claim is made.
