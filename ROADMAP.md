# Final Product Implementation Roadmap

## DASH-01 — WhatsApp sending status on the operations desk (2026-09-17)

The dashboard now opens with whether WhatsApp will accept sends: each connected number, its
standing, what its messaging tier permits, and when those figures were last checked. No backend
change, no migration, no contract change — `GET /phone-numbers` already returned
`quality_rating`, `messaging_tier`, `throughput_level`, `mps_limit`, `status` and `last_synced_at`.
Every field was stored, synced and reachable, and none of it was on the screen an operator opens
first.

That was the defect. A number Meta flagged overnight stayed invisible until a campaign failed,
because seeing it required navigating to Channels — a screen nobody visits on a good day. Sending
capacity is a precondition for most of the work below it on this page, which is why the strip sits
above the attention queue rather than in a settings screen.

Three decisions worth recording:

- **Worst first.** The numbers are ordered by severity — disconnected, then RED, then YELLOW — so
  on an account with several numbers the healthy ones cannot push the broken one off the end of
  the row. The one case the strip exists for is the one that would have been truncated.
- **It says when it last looked.** These values are what the last sync wrote, not a live call to
  Meta. A green badge with no timestamp reads as "fine now" when it may mean "fine on Tuesday",
  and a strip that is trusted while stale is worse than no strip. "Never checked" is stated
  plainly rather than rendered as healthy.
- **A failed lookup is not healthy silence.** If the channel service cannot be reached the strip
  says so and offers a retry, because an empty row and a broken query look identical otherwise and
  call for opposite actions.

`TIER_10K` is rendered as "10,000 customers / 24h". The enum name hides the only part an operator
needs before scheduling tomorrow's send.

**Not included: a remaining-quota count.** The reference product shows messages left in the rolling
24-hour window; this platform stores the tier cap but nothing counts sends against a rolling
window, and "today's count" is a different number that would be wrong near midnight. An
approximation on a status strip is worse than an omission, because it would be believed. Building
it properly means a real rolling-window count, which is its own milestone.

Gated on `waba:read`, the same permission as the Channels screen it links to.

PASS: frontend **934 passed across 54 files** (was 926/53), including 8 new tests covering the tier
rendering, the staleness label, "never checked", a RED number, a disconnected number outranking any
quality rating, worst-first ordering, the no-numbers case and a failed lookup. Backend unchanged at
**1,663 passed, 0 skipped**; contract unchanged at 242 paths. ESLint, TypeScript and the production
build clean.

## VAL-02 — a zero-skip run should not depend on remembering (2026-09-17)

`scripts/local_services.sh` starts MySQL 8 and Redis if they are not already running, and says so.
Idempotent, safe before every suite.

VAL-01 cleared the six live-MySQL skips by standing a server up by hand. A restart put them back.
The run still reported **exit 0** — 1,657 passed, 6 skipped — because a skipped test is not a
failing test, and the skip reason scrolls past in a wall of dots. That is the failure mode the
skips had in the first place: they are invisible when they matter and nobody is lying, so nothing
draws attention to the gap.

A script does not fix the invisibility, but it removes the reason to shrug at it: bringing the
services back is now one command that can be run before every suite rather than a procedure to
remember. The README says plainly that a machine which restarted turns a zero-skip run back into
six skips with no failure to notice.

PASS: services restarted, `tests/test_migrations_mysql.py` back to **12 passed**, and the full
backend suite re-run at **1,663 passed, 0 skipped**. No product code, no contract change.

## GSHEET-01 — import contacts from a Google Sheet tab (2026-09-16)

`POST /api/v1/contacts/import/google-sheet` reads one tab with a configured service account and
stores it as a CSV upload. Contract 241 → 242 paths. No migration, no new permission: it requires
`contacts:import`, the same permission as uploading a file, because it is the same act — choosing
which rows become customers.

**The sheet joins the existing import; it does not get its own.** The returned `upload_id` is the
one `/contacts/import/inspect` and `/contacts/import` already take, so mapping, dedup strategy, the
per-row error report, job progress, the timeline events and the audit trail are the machinery that
was already there and already tested. A second import path would be a second set of rules to keep
in step, and the one that drifted would be the one nobody was watching. This service parses
nothing, validates no contact and writes no contact.

Unlike CORE-22 there is no frozen design to follow: the scope document keeps Google Sheets under
"Integrations — Limited" but Doc 03 and Doc 04 specify neither schema nor endpoint, so the design
below is a decision, recorded as one.

**No new dependency.** The whole protocol is a signed JWT exchanged for a bearer token and one
`GET`, which PyJWT and httpx — both already here — do in about eighty lines. A client library for
that would be more code to audit, not less, and every dependency on the ingest side of a
customer-data path is one more thing to keep patched.

**A service account, not an operator's Google login.** A personal account's password change, 2FA
enrolment or departure would stop every sync, and the failure would look like an empty sheet rather
than a broken credential. The key is read from `GOOGLE_SERVICE_ACCOUNT_JSON`, is never logged,
never returned by any endpoint and never written to the database; what is persisted is the sheet's
*content*, as an ordinary import. Two tests assert that a rejected credential and a malformed key
do not quote themselves back into the message.

Details that are the difference between working and nearly working:

- **Ragged rows are padded.** Google omits trailing empty cells entirely rather than sending them
  as blanks. Left ragged, a row that happened to end early would have fewer CSV columns than its
  header, and every field mapped to the right of the gap would silently read the wrong column.
- **`QUOTE_ALL` on the CSV.** A sheet holds free text; an unquoted cell containing a comma would
  split into two columns and shift everything after it.
- **A pasted link is accepted, not just an id.** The id sits in the middle of a long URL, and
  asking an operator to extract it by eye is asking for a transcription error that surfaces later
  as "sheet not found" — sending them to look at sharing settings instead of at what they pasted.
  An unusable paste is refused locally with what to paste instead, rather than relayed to Google.
- **The errors name the fix.** Not shared → the exact address to share with. Unknown id → where in
  the URL the id lives. Wrong tab → the tab name, quoted.

The wizard gains a second source beside the drop zone, and the journey after it is unchanged.

PASS: backend **1,663 passed, 0 skipped**, including 11 new tests that exercise the real request
building, real RS256 signing and real error mapping against a fake transport — only the network is
replaced. Frontend **926 passed across 53 files** (was 918) with 8 new tests. Regenerated OpenAPI
and TypeScript with no drift; Ruff, strict mypy, ESLint, TypeScript and the production build clean.

**Not yet usable in production:** the owner has to create the service account and share the sheet.
`backend/.env.example` carries the three steps. Everything else is done and tested, so the
integration works the moment that key exists.

## CORE-22 — webhook delivery and dead-letter visibility (2026-09-16)

`GET /api/v1/webhooks/events` and `GET /api/v1/webhooks/dead-letter` expose the inbound webhook
record to operators, both gated on `webhooks:manage` per Doc 04 §23 and tenant-scoped. Contract
239 → 241 paths. No migration.

The ingest path has always written every delivery to `webhook_events` and parked every
unprocessable one in `webhook_dead_letter` after its retries were exhausted. Nothing read either.
The operations screen said so in as many words — *"the repository has no webhook-event query
endpoint"* — so the parking was real but the human it was parked for was never told. That is the
failure this closes: not a missing record, a missing reader.

**Ownership lives in the route, not the row.** Neither table carries an `organization_id`.
`webhook_events` is written on the ack path, before anything is interpreted, and is range-
partitioned with no foreign keys. A delivery belongs to whoever owns the route it arrived on, and
there are two of those: Meta routes by `phone_number_id`, WAHA by `channel_endpoint_id` (QR-08).
Both are matched, because an operator shown half their traffic would read the quiet half as
silence — the exact wrong conclusion when diagnosing a stalled stream. A dead letter inherits its
source event's owner; one whose source has already aged out (90 days against the dead letter's
180, §23.1) can no longer be attributed and is shown to nobody, since showing it to everybody
would be a tenant leak dressed as helpfulness.

**No payloads.** `payload_json` is the provider's raw body — customer numbers and message text.
Returning it here would put a second copy of the conversation behind a different permission than
the Inbox's `inbox:read`, quietly widening who can read customers' messages for the sake of a
health screen. What the view answers instead is the operational question: are deliveries arriving,
did their signatures verify, and are they reaching `processed`. A test asserts the payload never
appears in the response body.

The routes live in a new `webhook_ops.py` rather than in `webhooks.py`. That module's whole
contract is "everything here is public and unauthenticated, gated only by the provider's
signature", and being able to read that invariant off the file is worth more than co-location.

The UI replaces the placeholder that documented the gap. `/operations/webhooks` is reachable with
`waba:read` while the tables need `webhooks:manage`, so the tables are gated rather than the page:
hiding everything would tell a legitimate reader the screen was broken. Parked events are counted
where someone scanning the page will see it, and an empty delivery log reads differently from a
failed query, because those call for opposite actions — check the channel, or check the platform.

**Found while building, reported not worked around:** Doc 04 §23 specifies
`POST /webhooks/events/{uuid}/replay`, but `webhook_events` has no public UUID and cannot easily be
given a unique one. Proven against the live MySQL 8, not inferred: `ALTER TABLE ... ADD UNIQUE KEY
(uuid)` is refused with *ERROR 1503 — a UNIQUE INDEX must include all columns in the table's
partitioning function*, because the table is `RANGE COLUMNS(created_at)` partitioned. A non-unique
index is accepted, and so is `UNIQUE (uuid, created_at)`. Event replay therefore needs an explicit
decision and is left for its own milestone; dead-letter replay and discard are unaffected, since
that table already carries a UUID. This is the kind of finding only a real MySQL surfaces, which
is what VAL-01 bought.

A stale comment in `features/operations/api.ts` is corrected in passing: it claimed `GET /jobs`
declares no query parameters, which CORE-19 made untrue. The hook's behaviour is unchanged — it
still asks for the default page — but the reason is now "doesn't", not "can't".

PASS: backend **1,652 passed, 0 skipped**, including 11 new tests covering both routing paths,
cross-tenant isolation on each table, the unattributable dead letter, status filtering, declared
bounded pagination, the permission gate and the payload never appearing. Frontend **918 passed
across 53 files** with 8 new tests. Regenerated OpenAPI and TypeScript with no drift; Ruff, strict
mypy, ESLint, TypeScript and the production build clean. Verified live against MySQL 8 with seeded
rows in the partitioned table: both deliveries returned newest first, the status filter narrowed to
the failed one, the dead letter carried its error, and the payload did not appear.

## CORE-21 — per-user notification categories (2026-09-16)

`GET` and `PUT /api/v1/notifications/settings` let each operator choose which of the six
notification categories appear in their own Notification Center. Contract 238 → 239 paths. No
migration: the value is a display choice, so it lives beside the other per-user preferences as the
reserved `notification_settings` key rather than in a table of its own.

**Muting hides, it never drops.** The obvious implementation — skip the `emit` — was rejected, and
the reasons are worth recording because they are not visible from the happy path:

- This is an operations tool. The categories are follow-up due, release date due, case assigned,
  case status changed, automation attention, report ready. Every one of them is *work*. Dropping
  the row would make that work invisible permanently, not quietly deferred.
- The notification list has a team view. A lead with `tasks:assign` can read a teammate's queue.
  Suppressing at emit would let an agent's personal tidying erase rows from their supervisor's
  review — a setting that doubles as a way to hide from oversight.
- Unmuting has to mean something. Because the rows were only filtered, turning a category back on
  returns what was missed, still unread.

So the mute is applied at read, and only when the reader is the recipient: `_muted_for_own_view`
returns the empty set for a team view. Three call sites share one repository predicate
(`_mute_clause`) — the page, the unread count and mark-all-read — for the reason CORE-11 shares
`_customer_match`: a badge that counts what the list refuses to show teaches operators to stop
believing the badge, and a mark-all-read that clears what was never shown consumes the evidence
before anyone sees it.

The key is reserved from `PUT /users/me/preferences`, exactly as `INBOX_OPERATIONS_KEY` already is
from the organization settings endpoint. That endpoint takes a free-form dict, so without the guard
a client could store a shape the typed endpoint would never accept, and the notification list would
then be filtered by something no validator had seen. The read defends itself as well: a stored
value that is not a list of known category names mutes nothing, which fails towards showing the
operator too much rather than too little — a user setting outlives the code that wrote it.

The UI asks "show me", not "mute": a checked box is a category you see. The stored value is the
complement, because an absent setting has to mean "show everything". The panel says in plain words
that hidden notifications are still recorded and the team lead still sees them, and it is offered
only on the personal view — showing it while reading a teammate's queue would imply it changes what
*they* see. A save in flight holds the just-toggled box rather than letting the server's older
answer snap it back under the operator's finger.

PASS: backend **1,641 passed, 0 skipped** (was 1,629), including 12 new tests covering the badge
agreeing with the list, mark-all-read leaving muted rows unread, unmuting restoring them, the
supervisor's view staying unfiltered, per-user isolation, unknown categories refused, the reserved
key guarded and a corrupt stored value. Frontend **910 passed across 52 files** (was 901/51), with
9 new tests. Regenerated OpenAPI and TypeScript with no drift; Ruff, strict mypy across 322 files,
ESLint and TypeScript clean; production build clean. Verified live against MySQL 8: defaults,
save, read-back, refusal of an unknown category, the reserved-key guard and unmute; the read sweep
is 204 requests across 70 paths with no 5xx.

## MAINT-03 — an owner the CLI creates is an owner who can sign in (2026-09-16)

`create-owner` accepted any string as an email. It lowercased it, wrote it to `users` as an Owner
superuser, printed "Owner created" and exited 0. `LoginRequest.email` is an `EmailStr`, so the
address was then refused at the sign-in boundary — the account was unusable from the moment it
existed, and the only symptom arrived later as a 422 that never said the address was the problem.

Reproduced end to end before the fix, against a real MySQL 8: `create-owner --email
'this is not an email'` succeeded, and the row landed in `users` verbatim. `ghost@vi.test` did the
same. Neither could ever sign in.

This matters more than its size suggests. `create-owner` is the first command run against a new
deployment, usually once, often by whoever is least able to debug it, and a typo there produces a
superuser nobody can use with no signal that anything went wrong.

`validate_sign_in_email` now sits in `app/core/security.py` beside `validate_password_policy`, and
for the same stated reason: one rule, applied at both boundaries. It validates through the very
`EmailStr` adapter `LoginRequest` uses, so the two cannot drift — a future change to the schema's
address rule moves the CLI with it. It returns the normalised address, so `bootstrap_owner` no
longer repeats the trimming and lowercasing itself. A refusal exits 2 and names the reason, so a
deployment script stops rather than continuing against an owner that will never work.

The gap analysis recorded this as "the owner-bootstrap CLI currently accepts reserved `.test`
email addresses". It was wider than that: there was no validation at all, and `.test` was simply
the example someone happened to try.

Six tests added: five addresses that could never sign in (a plain typo, reserved `.test` and
`.invalid`, `localhost`, a truncated address), each asserting that nothing was written before the
refusal, and one stating the property directly rather than by example — an address
`bootstrap_owner` accepts is an address `LoginRequest` accepts. No existing test changed; every
address the suite already bootstrapped with passes the new rule.

PASS: full backend suite **1,629 passed, 0 skipped**; bootstrap/dev-fixture/live-MySQL/auth/security
files 63 passed; strict mypy across 322 files; Ruff clean. No migration, no contract change, no new
permission; the contract stays at 238 paths.

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

This is the canonical forward roadmap from the current repository baseline. It is additive to, and
does not overwrite, the historical module roadmap in `docs/ROADMAP.md` or the frozen design records
under `docs/design/`.

Last synchronized: `2026-09-13`.

UI-REF-02 closes the bounded Live Chat search/view-strip/empty-column shell change, not complete
Live Chat equivalence. Frontend **883/883**, types/build/lint and desktop/mobile preview pass.
Populated chat/action/profile acceptance remains, followed by Contacts and Campaigns comparisons.
See Design Document 73. Backend/API/migration/delivery state and module estimates are unchanged.

## Latest UI priority — UI-REF-01

Screenshot-aligned compact rail and persistent Manage panel implemented. Next acceptance work:
Live Chat states 1–3, Contacts 4–9, Campaigns 10–17, then Manage 44–55, including real controls
and previews. See Design Document 72. Frontend **882/882**, types/lint/build and bounded
desktop/mobile checks pass; full parity and cumulative release/production validation remain
pending. Unfinished GROW-03 segment changes at migration **0062** are preserved, not completed.

## Current release-candidate checkpoint

PAR-AUTO-22 remains the last worktree to pass the complete release quality profile **23/23 in
685.9s**: **1521 backend tests with zero skips**, **832 frontend tests**, complete static, security,
dependency, image-contract/SBOM and certified WAHA runtime gates. `REL-CERT-01`'s pre-PAR-AUTO-19
cumulative deployed evidence remains **25/25 in 597.4s**, including the disposable ten-service
browser, performance, dependency-failure and log-correlation gates. Its 30-read canary was
**5.764ms p95** against a **300ms** budget. The exact current PAR-VIEW-05 tree separately passes
focused Reports saved-view contracts **12/12**, **875 frontend tests**, static **6/6**, strict mypy
across **322 files**, synchronized **235-path** OpenAPI and production build. Full backend is
**1579 passed / 6 MySQL-only skipped / 0 failed in 413.35s**. Its
Docker/security release rerun remains pending.
This closes repository/local-deployment release blockers only for the last fully gated tree.

It does not reorder or silently complete the roadmap below. The 31 canonical module estimates have
a simple unweighted mean of **77.0%** (recalculated median **88%**). Product gaps remain in the named GROW/ENT
milestones, and REL-01 accessibility/UAT, the remaining REL-02 capacity/restore evidence, and
REL-03 target-host TLS/secrets/monitoring/rollback/acceptance are still pending. No commit, push,
release tag, or live deployment was performed.

## Authority and baseline

- Final product intent: `VI_REACTIVATION_FINAL_PRODUCT_SCOPE.md`.
- Remaining-work baseline: `CURRENT_PROJECT_GAP_ANALYSIS.md`.
- UI Taste Modernization branch: `ui/taste-modernization`.
- UI Taste Modernization lineage baseline: `62d4daa50617e2e0c8fff9f5ec9a514848a77f98`.
- Priority 1 starting baseline: `9043fe03a80b682a010304c88c5d29d8ec77d1fa`.
- GOV-02 starting baseline: Git `0ea14d6`, repository `1.0.0-rc1`, migration `0031`, OpenAPI 3.1.0
  with 153 paths, 932 backend tests, and 628 frontend tests.
- Current live baseline after CORE-09: repository `1.0.0-rc1`, migration
  `0035_notification_center`, OpenAPI 3.1.0 with 193 paths, and 948 backend tests.
- Existing functionality is reused. A milestone may close a verified gap but may not rebuild a
  completed module.
- GitHub remains the only implementation source of truth. The owner-approved AiSensy capture archive
  may be inspected only from Git-ignored `.reference/aisensy/` as a private workflow and visual-
  quality benchmark under ADR-0012 and Design Document 25. It is never staged, committed, bundled,
  copied, or treated as implementation truth. Cached repositories and previous implementation
  snapshots must not be consulted. Excluded ads, payments, billing, subscriptions, marketplace,
  signup, reseller, multi-project, promotional, and commerce surfaces are never in scope.
- Every implementation milestone includes the premium screen Definition of Done for each new or
  materially changed route. Functionality, original presentation, real state, shared-component
  reuse, responsive behavior, accessibility, reliability, and test evidence are co-equal acceptance
  requirements; this gate does not change the approved feature sequence below.
- Estimated path and migration changes are planning figures. The milestone design review must
  verify exact additive contracts before implementation.
- Exactly one implementation milestone is closed per reviewed commit. Stop after each milestone for
  owner approval.

Current milestone status: `CORE-11C — Inactivity Auto-Resolve` is repository-implemented inside the
still-`PARTIAL` CORE-11. On top of CORE-11A/11B operations, it adds an opt-in bounded inactivity
scanner, open-Task/unread protection, row-locked idempotent resolution evidence and safe fresh-
inbound reopen without a migration, new route or duplicate workflow authority. The remaining
CORE-11 settings/team/SLA work stays in the row below. `CORE-09 — Unified Notification Center`
remains complete, and
**CORE-08 — Skipped: Not required by product owner** remains unchanged. No generic approval
authority or Approval Center will be built; existing KYC-specific approval logic and completed
authorization safeguards remain preserved.

`UI-TASTE-01` documentation/audit and `UI-TASTE-02` shared design-system modernization are complete. `UI-TASTE-03A` operator-first Dashboard is implemented and repository-validated from baseline `7d826987`; authenticated representative-data visual/reference review remains pending. `UI-TASTE-03B` Reactivation operational hierarchy, `UI-TASTE-04` responsive/accessibility/performance regression and `UI-TASTE-05` owner review/merge readiness are Repository Validated. UI-TASTE-05 remains Repository Validated; the owner has separately authorized only M13-06B provider-neutral control-plane work.

The 2026-08-21 owner clarification makes AiSensy-style named tabs and workflows the visible product
baseline while retaining original branding/assets and the permanent exclusions. The repository-
validated follow-up expands named daily navigation by default, organizes existing additional routes
under `Manage`, and labels the existing Live Chat filters `Requested`, `Active` and `Intervened` over
real pending/open/current-assignee facts. The next repository-validated slice makes that operator
lifecycle executable: a row-locked, audited and idempotent `Intervene` action claims a request;
another agent cannot steal it; and only the owner can `Resolve`, including through the older generic
status route. PAR-AUTO-04 supplies the governed `Human handoff` effect, and PAR-AUTO-05 now connects
the first automatic path: a privacy-safe real inbound event creates one locked receipt and pinned
Trigger → Human handoff live run, placing the conversation in `Requested` once. Unsupported graph
shapes fail closed and test mode stays simulated. PAR-AUTO-06 adds one optional privacy-safe
Condition before that handoff. A match continues; a non-match records a skipped effect. PAR-AUTO-07
adds Create task as the first internal work effect: direct or conditional inbound paths create one
existing tenant-scoped Task with publisher assignment, immutable due time and receipt-keyed replay
recovery. PAR-AUTO-08 adds Apply tag as the second internal effect: the immutable existing CRM tag
is attached once through row-locked Tag/Contact, Timeline and Audit authorities; replay and an
already-present tag cannot duplicate evidence. PAR-AUTO-09 adds Assignment as the third internal
work effect: a published specific user is revalidated at execution, or durable per-flow receipt
order rotates across eligible Inbox members. The Conversation row lock preserves any existing
owner, and crash replay cannot duplicate the system Audit. PAR-AUTO-10 adds Remove tag as the
fourth internal work effect: the immutable CRM tag is detached through the same locked Contact/Tag,
usage, Timeline and Audit authorities; already-absent and replayed removal are safe no-ops.
PAR-AUTO-11 completes internal Notification as the fifth internal work effect: one Contact-linked
delivery goes to the active eligible publisher through the existing Notification Center and
receipt/node replay converges without duplication. Backend, migration, static, frontend and
production-build gates pass; Automation advances to **96%**. Migration is `0046`; no route,
permission code, provider action, customer send or parallel authority is added. PAR-AUTO-12 then
adds bounded sequential execution: one to four distinct proven effects run in connected order, and
completed node attempts checkpoint worker retry without duplicating domain work. Branches,
repeated effect kinds and larger sequences still fail closed; Automation advances to **98%**.
PAR-AUTO-13 activates one bounded durable Delay in that linear sequence: the worker records a
running checkpoint, schedules the same receipt task and cannot execute downstream effects before
the due time. Early/duplicate delivery converges, and due resume does not repeat upstream work;
Automation advances to **99%**. PAR-AUTO-14 then promotes Contact Created to a second bounded live
event for Apply tag, Remove tag and internal Notification, with event-safe Condition fields and the
existing Delay. A minute receipt scanner on the existing scheduler queue recovers new and genuinely
stale work while leaving paused delays to their scheduled continuation; Automation remains **99%**.
General branching, Wait-for-event, further live event consumers, campaign/webhook/customer-message
effects, capacity/skill routing, SLA presentation and authenticated host/browser acceptance remain
future work. PAR-AUTO-15 adds Conversation Auto-Resolved as a third bounded live event: it creates
safe internal follow-up Tasks, changes tags or notifies the publisher from tenant-checked event
lineage, while Handoff and Assignment fail closed on the resolved chat. The existing receipt
dispatcher provides recovery, and Automation remains **99%**.
PAR-AUTO-16 promotes Schedule to a fourth bounded live trigger. A clean published cron persists an
indexed next UTC run in the organization timezone; the minute heartbeat claims one deterministic
slot/event/receipt, advances past missed occurrences and reuses existing receipt recovery. Its live
path is limited to one workspace-only publisher Notification with one optional Delay. Migration is
`0047`; general branching, Wait-for-event, external/customer actions and reconciliation remain
future work, so Automation remains **99%**. PAR-AUTO-17 then promotes one Wait node to a durable
live checkpoint on event-backed paths: it persists the original receipt/run/node and Contact,
resumes only on that customer's future Message Received event, and requires a 60-second-to-30-day
timeout plus a later approved internal effect. The existing minute receipt heartbeat owns timeout
and enqueue-failure recovery. Migration is `0048`; additional wait/event projections, general
branching and external/customer actions remain future work, so Automation remains **99%**.
PAR-AUTO-18 activates the existing Task completed Wait choice. Single and bulk Task completion now
append one deterministic, privacy-safe `task.completed` Business Event in the authoritative Task
transaction; a reopened/re-completed Task receives a distinct revision fact. Only a future
same-organization/Contact completion can resume the original run, while timeout and failed-enqueue
recovery continue through the existing receipt heartbeat. At that checkpoint, Lead-stage
projection, general branching, external/customer actions and reconciliation remained future work,
so Automation remained **99%**.
PAR-AUTO-19 now consumes the authoritative immutable Reactivation stage transition as the live
`lead.stage_changed` alias rather than duplicating CRM state. Previous/New stage conditions may
drive a Contact-linked Task, tag changes or an internal Notification through the existing Delay or
same-customer Wait. Private transition reasons and internal case/stage identifiers are excluded,
and no Conversation is fabricated. Handoff, Assignment, general branching, external/customer
actions, recipient/team routing and reconciliation remain future work, so Automation remains
**99%**.
PAR-AUTO-20 adds one bounded terminal Yes/No split to event-backed Conditions. Explicit `yes` and
`no` edges each end at one already-approved internal effect; only the selected action executes and
the other is durably skipped. Safe test mode follows the same decision, and the builder labels and
locks the split while offering a return to linear mode. Multiple Conditions, nested or multi-step
branches, Delay/Wait within branch bodies, external/customer actions, recipient/team routing and
reconciliation remain future work, so Automation remains **99%**.
PAR-AUTO-21 extends each side of that exact split to one or two ordered distinct internal effects
under the unchanged four-effect ceiling. Selected steps resume from durable checkpoints, every
unselected node is skipped explicitly, and safe test mode mirrors the body without mutation. The
builder exposes a dedicated Yes/No effect palette and safe terminal removal. Multiple/nested
Conditions, longer bodies, branch Delay/Wait or merging, external/customer actions, recipient/team
routing and reconciliation remain future work, so Automation remains **99%**.
PAR-AUTO-22 adds one optional shared follow-up after that exact split. Both branch terminals may
converge on one trigger-safe terminal effect under the same four-effect ceiling. Only the selected
branch and shared node execute; alternate-only nodes stay durably skipped and replay cannot
duplicate the shared domain effect. The builder exposes `+ Both`/`After both` and preserves the
merge while inserting or removing a branch terminal. Arbitrary/multiple merges, multiple/nested
Conditions, longer bodies, branch Delay/Wait, external/customer actions, recipient/team routing
and reconciliation remain future work, so Automation remains **99%**.
PAR-AUTO-23 allows that exact shared follow-up to pause once through a durable Delay immediately
before its action. The selected branch checkpoints first; early/duplicate delivery reuses one
running Delay attempt, and due resume executes the shared effect exactly once before completing
alternate-only skip evidence. The builder inserts/removes the `Shared delay` without leaving a
terminal timer. Branch-specific Delay/Wait, multiple timers, arbitrary/multiple merges, multiple/
nested Conditions, longer bodies, external/customer actions, recipient/team routing and
reconciliation remain future work, so Automation remains **99%**.
PAR-DL-01 partially delivers GROW-06's artifact home by projecting existing contact and analytics
CSV/XLSX/JSON exports into one personal, tenant- and current-permission-scoped Download Center.
It adds normalized status/expiry, fresh signed links, URL filters, polling and keyset history without
duplicating the export pipeline. PAR-REP-01 adds real paginated PDF artifacts for all seven existing
analytics report families through that same pipeline. PAR-REP-02 adds personal daily/weekly/monthly
schedule management, row-locked automatic export generation and ready notifications. New
executive/domain metrics remain governed by PAR-REP-03/04. PAR-DL-02 adds permission-scoped
complete/date-bounded conversation transcripts in four formats through the same personal artifact
home. Campaign/scan and generated-document sources remain in GROW-06 and their source milestones.

## Module 13 — Enterprise Omnichannel Channel Manager

**Current status: QR-09D, QR-09G, QR-09H, QR-09I, QR-09J and QR-09L — REPOSITORY/RUNTIME VALIDATED; QR-09 remains PARTIAL — BLOCKED**

ADR-0020, ADR-0021 and Design Document 33 remain frozen. M13-01 supplies provider-neutral contracts
and registries; M13-02 exact Contact identity; M13-03 persistent connection/endpoint/encrypted-secret
records; M13-04 durable session lifecycle/lease/fencing; M13-05 runtime/pairing control-plane facts;
M13-06A adds inert sync checkpoints/media references; and M13-06B adds repository-owned lifecycle,
permission, flag, concurrency and Audit controls over those records. WAHA remains uncertified and no
live login, event ingestion, provider history retrieval or media-byte transfer exists.

Provider adapters, QR image generation/scanning, WhatsApp protocol, live synchronization, media-byte
transfer, messaging, webhook, routing and operator UI remain outside this milestone.

| Milestone | Objective | Status / start gate |
|---|---|---|
| M13-00 — Architecture & Provider Lock | Freeze architecture, provider, security, session, identity, API/database, rollback, rollout and validation contracts | **REPOSITORY VALIDATED** |
| M13-01 — Generic Channel Foundation | Add provider-independent domain contracts, registries, validation, generic flags and DI while reusing `ChannelAdapter` | **REPOSITORY VALIDATED**; no provider/runtime/persistence workflow |
| M13-02 — Customer identity convergence | Add exact scoped provider identities and conflict handling without duplicate Contacts | **REPOSITORY VALIDATED**; immutable aliases, review queue and non-destructive recommendations delivered |
| M13-03 — Persistent Channel Connections & Endpoint Records | Add organization-owned provider-neutral connection/endpoint records and encrypted versioned/revocable credentials with tenant isolation, lifecycle/health metadata, soft delete, locking, flags and Audit references | **REPOSITORY VALIDATED**; migration `0037`; no API/provider/runtime/UI behavior |
| M13-04 — QR Session Manager Foundation | Durable provider-neutral session state, lifecycle, heartbeat/expiration, recovery/restart metadata, capability references, tenant/RBAC/flags/Audit and lease/fencing concurrency controls | **REPOSITORY VALIDATED**; migration `0038`; no provider, live runtime, QR/login, API or UI behavior |
| M13-05 — QR Pairing & Provider Runtime Foundation | Provider-neutral runtime registry/manager, no-store pairing lifecycle, health/events/capabilities, heartbeat/restart/recovery and session persistence integration | **REPOSITORY VALIDATED**; migration `0039`; no provider adapter, QR image/login, messaging, API or UI behavior |
| M13-06 — QR inbound, history and media | Canonical live events, checkpointed history and existing-media reuse | **M13-06A persistence and M13-06B provider-neutral lifecycle control plane REPOSITORY VALIDATED**; certification PASSED 2026-08-08, and the provider adapter (QR-01) and live event ingestion (QR-04) are delivered. Provider history retrieval and media-byte transfer remain unimplemented |
| M13-07 — Provider-neutral outbound | Conversation-scoped send and approved manual QR messaging | Blocked by idempotency and ambiguous-send evidence |
| M13-08 — Unified operator experience | Provider-aware Inbox, Customer 360, Timeline, assignment, notes, tags and search | Blocked by stable source milestones |
| M13-09 — Notifications, analytics and diagnostics | Reuse existing authorities with factual provider dimensions | Blocked by stable unified sources |
| M13-10 — Production validation | Security, performance, browser, accessibility, operator, DR and staged rollout evidence | Blocked by all implementation milestones |

The M13-06B stop gate has since been released: physical-phone certification **PASSED** on
2026-08-08 and the owner instructed the QR sequence to proceed. QR-01 (adapter foundation),
QR-02 (session lifecycle mapping) and QR-03 (QR pairing) are delivered under that release.

QR-04 (webhook ingestion) is also delivered: verification and normalization onto the existing
`webhook_events` authority, with no new route, table or migration.

QR-05 (text send and delivery-state reconciliation) is also delivered, reusing the existing
monotonic `messages` status authority rather than adding a second ordering.

QR-06 (session recovery, health and teardown) is also delivered, reusing the existing session
lease/fencing authority rather than adding a second runtime ownership system.

QR-07 (WhatsApp Scan/Connect interface) is delivered: the first real operator UI over the WAHA
adapter, bridging it to the existing M13-03/04/05 connection/session/pairing control plane. This is
also the first milestone in the QR sequence to add public API routes (OpenAPI 200 → 206 paths),
which is expected and authorized at this stage rather than a drift regression.

QR-08 (Unified Inbox integration) is also delivered: Meta and WAHA conversations share the same
existing Inbox, Conversation/Message ledger and Contact authorities rather than a second Inbox.
Adds one additive migration (`0043`, nullable `channel_endpoint_id` alongside the existing
`phone_number_id`) and one route (`POST /webhooks/waha`, OpenAPI 206 → 207 paths) — the WAHA
webhook HTTP endpoint QR-04 built the verification/parsing logic for but never wired.

QR-09L remediates **QR-09-D13 (application defect)** without changing the approved sequence or
provider capabilities. Persisted endpoint-owned ACKs now select their connector through the
durable endpoint/connection relationship rather than inheriting a task-local Meta default.
Provider-native WAHA reply identity is preserved in the existing scoped Contact identity authority:
`@lid` stays `@lid`, and `@c.us`/`@s.whatsapp.net` stay exact when observed; only a factual phone JID
can link canonical telephone identity. Outbound Inbox replies reuse that exact endpoint route and
never manufacture `@c.us` from LID digits. No migration, route or OpenAPI change is required.
Canonical premerge 14/14 and applicable release/runtime 8/8 pass (backend 1444, frontend 806). The
protected provider remains WORKING/paired with restart count zero. Application remediation is
validated, but QR-09 remains blocked until the one new QR09-L-ACK Inbox message produces genuine
correlated physical ACK evidence; persistence/logout, Meta rotation and target-host/browser gates
also remain pending. Certification approval does not advance.

QR-09J closes **QR-09-D12 (Blocker)** without changing the approved sequence. A real external
message reached both signed certified WAHA event variants but failed before the shared Inbox because
the provider timestamp was aware UTC and repository/MySQL time is naive UTC. The adapter now
normalizes the provider epoch at its boundary. Preserved events were redriven through the existing
idempotent queue and produced exactly one accepted Inbox message with unread count one; the original
dead-letter records remain historical evidence. Canonical premerge 14/14 and applicable
release/runtime 8/8 pass (backend 1437, frontend 806). The linked provider was never restarted and
remains WORKING/active/paired/connected. QR-09 remains blocked on outbound/ACK, linked-session
persistence, logout/re-authentication, Meta rotation and target-host/browser evidence; approval
status does not advance.

QR-09I closes **QR-09-D11 (Blocker)** without changing the approved feature sequence. The
short-lived pairing representation expired after the physical scan while the same configured WAHA
session had already reached identity-bearing `WORKING`; equal-state pairing requests could not
renew that window and the ordinary expired-transition guard correctly refused convergence.
Explicit pairing requests now renew only the availability expiry under existing lease/fence/version
controls, while polling never renews. A narrow provider-confirmed completion accepts only a fresh
same-session `WORKING` observation with identity, preserves the pairing revision and emits redacted
Audit evidence. The linked real session converged to active/paired/connected without a provider
restart, logout, delete, create, new QR, rescan, message or database backdoor. Canonical premerge
14/14 plus nine release/runtime gates pass (backend 1436, frontend 806). QR-09 remains blocked on
the external phone, ACK, restart/reconnect, logout/re-authentication, Meta-rotation and target-host
gates; provider certification and Host/Provider/Production status do not advance.

QR-09H closes **QR-09-D10 (Blocker)**. An unscanned QR lapses to `FAILED` while the provider
session object survives, so every governed "Get a new QR code" retry hit the provider's
`already exists` refusal, which the service reported as an outage; `reconnect` refused because
nothing was paired and `connect` was an idempotent no-op, so after the first expiry the channel
could never issue another QR without direct provider intervention.

Certified behavior was measured on the exact digest rather than assumed: `start` alone answers
`201` and changes nothing on a `FAILED` session, while `stop` then `start` reaches `SCAN_QR_CODE`
with the session count at one, `me` still `None` and the stored configuration byte-identical. A new
`prepare_pairing()` applies exactly that non-destructive pair — never a delete, recreate or logout —
and leaves `begin_pairing()` create-only so QR-03's no-guessing-on-conflict principle and its
regression still stand. It reuses an already QR-eligible session, skips a redundant stop, and
refuses both a provider-reported linked account and a durably `PAIRED` connection; every provider
mutation runs under the governed runtime lease. Error classification is corrected so a reached
provider yields a truthful conflict instead of a false outage, with provider wording never echoed.
A genuinely expired QR recovered through the actual frontend under a single lease, and the
application QR returned `200 image/png` with no-store/private/no-cache. All 23 release gates pass
(backend 1431, frontend 806, unchanged). Migration/OpenAPI/RBAC/capabilities/digest, persistent
storage and provider approval remain unchanged; no frontend source was touched.

QR-09D closes **QR-09-D6 (Major)** on top of the committed QR-09G backend. With a durable
application session present and the provider reachable but holding none, the screen projected
`ready-to-connect` and re-offered an idempotent `connect()` that provably cannot create provider
state, so `POST /session/pair` was operationally unreachable and every poll re-asserted the dead
end. The durable application session is now the boundary between the two honest operator actions:
a provider-neutral `ready-to-pair` state offers "Begin pairing" wired to `POST /session/pair`,
while no durable session still yields `ready-to-connect`. QR-09F outage truth still outranks it,
and a previously paired connection still resolves earlier as `reauth-required`.

Frontend regressions were reconciled by hand against the QR-09F suite rather than by applying the
conflicting historical patch, so every outage regression is preserved alongside the new D6
coverage. Real MySQL/Redis/application/exact-WAHA evidence: `ready-to-pair` held across eight live
three-second polls with Connect WhatsApp absent; the actual UI action issued exactly one
`/session/pair` and zero `/session/connect`; two application QR requests returned `200 image/png`
with no-store/private/no-cache and the bytes were never displayed, persisted or scanned; a genuine
outage produced zero new QR requests and recovered without duplication; and the QR-09G paused
never-paired recovery was re-proven through the same UI. Actual local desktop/mobile captures show
ready-to-pair with no QR, no horizontal overflow, visible keyboard focus and a compliant mobile
touch target; these do not constitute target-host acceptance. All 23 release gates pass (backend
1418, frontend 806). Migration/OpenAPI/RBAC/capabilities/digest, persistent storage and provider
approval remain unchanged. Physical-phone QR-09 validation follows, gated on explicit
dedicated-account safety confirmation.

QR-09G remediates **QR-09-D9 (Blocker)** without absorbing QR-09D. `STOPPED` is an ordinary WAHA
status, `map_session_status` turns it into durable `PAUSED`, and a `PAUSED` row cannot acquire a
runtime lease. For a never-paired connection that closed every exit: status reconciliation stopped
permanently and reported an outage that was not happening, `pair` returned 409, `reconnect`
returned 409 instructing the operator to pair, and `connect` was an idempotent no-op — the channel
was unrecoverable without direct database intervention, because the documented
`PAUSED → INITIALIZING` escape sat behind `can_reconnect`, which requires durable `PAIRED`.

`begin_pairing()` now reuses the exact control-plane pattern `reconnect()` established: the legal,
lease-free `PAUSED → INITIALIZING` transition first, then the ordinary runtime lease. The
`SessionManager` PAUSED lease prohibition is unchanged, and recovery is narrow to non-`PAIRED`
pairing states so durable credentials stay in the reconnect/re-authentication domain. A row that
cannot be leased is still read, so missing-session and outage facts are truthful while nothing is
created, started or mutated from a `GET`. Real MySQL/Redis/application/exact-WAHA evidence replayed
the preserved D9 reproduction: `pair` returned 200, the audit trail shows `transitioned` before
`lock_acquired`, exactly one provider session reached `SCAN_QR_CODE`, one durable
connection/session remained, and no database intervention was needed. All 23 release gates pass
(backend 1418, frontend 798). Migration/OpenAPI/RBAC/capabilities/digest, persistent storage and
provider approval remain unchanged. QR-09G is backend/control-plane only, so no UI preview evidence
is claimed. QR-09D closure and physical-phone QR-09 validation follow separately.

QR-09F remediates **QR-09-D8 (Major)** without absorbing QR-09D. A genuine provider outage could
inherit actionable QR truth from durable `pairing_available` state and stale `SCAN_QR_CODE`
metadata; the frontend then mounted QR retrieval while WAHA was unreachable. Reconciliation now
distinguishes current observation, missing session and transport outage. Only a current live
`SCAN_QR_CODE` observation advertises QR availability; the outage projection fails closed without
mutating durable pairing/reauthentication facts. Frontend outage priority suppresses every stale QR,
creating, connecting or reconnect action.

Real MySQL/Redis/application/exact-WAHA evidence held a genuine outage for more than three polling
intervals with no QR-handler request, then recovered the same container, volume, provider session
and durable application session. Actual local desktop/mobile browser captures show the unavailable
state with no QR/action or horizontal overflow; these do not constitute target-host acceptance.
All 23 release gates pass (backend 1408, frontend 798). Migration/OpenAPI/RBAC/capabilities/digest,
persistent storage and provider approval remain unchanged. QR-09D stays externally preserved and
unapplied; Meta rotation is `PENDING — OWNER DEFERRED`; QR-09 remains `PARTIAL — BLOCKED`. No
automatic QR-09D or physical-phone QR-09 resume is authorized.

QR-09E remediates **QR-09-D7 (Major)** without absorbing QR-09D: the QR byte request inherited
`Accept: application/json`, and the certified WAHA runtime truthfully returned JSON even with
`?format=image`. JSON API calls retain their JSON default; only QR retrieval now requests
`image/png`. A new release regression starts the exact certified digest in an isolated loopback-only
container, reproduces JSON negotiation, validates PNG negotiation through the repository client and
asserts one ephemeral session with no persistent-volume mount. Repeated live application fetches
also return PNG with no-store/private cache controls and no duplicate provider or durable session.
QR bytes are never displayed, logged, persisted or scanned.

All 23 release gates pass (backend 1407, frontend 796), including health, QR and signed-webhook
certified-runtime checks plus production contracts, image scans and SBOMs. Migration head, OpenAPI,
RBAC, frontend source, capabilities, persistent session storage and provider approval do not change.
QR-09D's separate three-file frontend work remains preserved externally and was not reapplied.
QR-09D and QR-09 remain `PARTIAL — BLOCKED`; Meta rotation is `PENDING — OWNER DEFERRED`, and no
physical-phone or target-host claim is made. No automatic QR-09D or QR-09 resume is authorized.

QR-09C technically remediates **QR-09-D5 (Major)**: both Compose topologies now configure the exact
certified WAHA sender to deliver only `message`, `message.any` and `message.ack` to the existing
HMAC-gated receiver. Production callback traffic stays on the private Compose network; development
uses Docker's internal host gateway while retaining loopback-only provider publication. One global
configuration keeps the dedicated signing key out of session state and avoids the duplicate
deliveries WAHA would produce if global and per-session webhooks were both present. The backend's
raw-body SHA-512 verifier and all application behavior remain unchanged.

The new release regression executes the certified image's own sender, proves provider-generated
HMAC, private callback reachability, a byte-identical retry after controlled failure, and a new
signed ACK delivery after provider restart. The provider remains `2026.7.2` / `NOWEB` / `CORE` with
zero sessions; no QR or phone interaction occurs. All 22 release gates pass (backend 1399/0 skipped,
frontend 796). Migration head, OpenAPI, RBAC, UI, capabilities and provider approval do not change.

**META WEBHOOK_VERIFY_TOKEN ROTATION: PENDING — OWNER DEFERRED.** Therefore QR-09C remains
`PARTIAL — D5 REMEDIATED, META TOKEN ROTATION PENDING`, and QR-09 remains `PARTIAL — BLOCKED`.
`Host Validated`, `Provider Validated` and `Production Ready` remain NO. QR-09 physical-phone
closeout does not resume without separate explicit approval.

QR-09B (WAHA runtime healthcheck remediation) is **REPOSITORY VALIDATED**. It preserves QR-09's
failed-attempt history and records QR-09-D4 (Major): both Compose files called `wget`, which is not
present in the exact certified image. The corrected exec-form, bounded in-image curl probe uses the
provider-owned unauthenticated `/ping` liveness endpoint and deliberately does not assert WhatsApp
pairing state. A real certified-image regression proves Docker healthy before and after restart,
positive and deterministic negative command behavior, loopback-only development exposure, no
production port, and unchanged persistent session-volume/startup semantics. All 21 release gates
pass. No application behavior, migration, OpenAPI, RBAC, capability or provider-certification state
changed.

QR-09A (production validation remediation) is **REPOSITORY VALIDATED**: it repairs exactly the
blockers QR-09 recorded — `0043`'s real-MySQL downgrade (no new revision; up/down/up now proven with
data), the provider-up/session-absent HTTP 500 (now a truthful recoverable state that preserves
durable pairing truth and never auto-recreates a session), the oversized-webhook 500 (now `413`),
the red OpenAPI drift gate (artifact regenerated canonically; 207 paths unchanged), the missing WAHA
deployment definition (digest-pinned, profile-gated, no production port, persistent session volume,
operator runbook), and the `cryptography` advisory (floor raised; `pip-audit` clean). Verified
against real MySQL 8.0.46, Redis 7.4.9 and the real pinned WAHA container. Capabilities, RBAC,
migration head and the provider certification record are unchanged.

**QR-09 itself remains `PARTIAL — BLOCKED`** and is not closed by this: physical-phone provider E2E
(including credential survival across a restart, which was not demonstrated) and the
browser/target-host matrix still require evidence this environment cannot produce.

QR-09 (production validation) was attempted and is `PARTIAL — BLOCKED`: real MySQL `8.0.46`,
real Redis `7.4.9`, and the real pinned WAHA container confirmed the QR-08 dedupe/routing/idempotency
contract, but two Major defects (a real-MySQL `0043` downgrade failure; a `500` on the QR operator
status endpoint when the provider is up but the session is absent) and one genuinely-failing required
gate (OpenAPI drift — investigated and corrected to an ASCII-escaping cause, not the previously
recorded resolver key-order explanation) remain open. No product, migration, OpenAPI, or capability
change was made. Full evidence: `VALIDATION_RESULTS.md` "QR-09 — Production Validation". The
recommended next milestone, `QR-09A — Production Validation Remediation`, is not started.

Still not started, and still requiring their own milestones: provider history retrieval and
media-byte transfer/processing.

## Phase 0 — Governance and scope lock

| Milestone | Objective | Features | Files expected | Tests expected | Completion criteria | Est. OpenAPI increase | Est. migration |
|---|---|---|---|---|---|---:|---|
| GOV-01 — Permanent governance baseline | Establish synchronized, durable repository control without changing product intent. | State, validation, module status, rules, final roadmap, closeout protocol, permitted UI-reference boundary. | Root governance Markdown; `CHANGELOG.md`; `IMPLEMENTATION_TRACKER.md`; optional governance helper under `scripts/`. | Markdown/link/required-field validation; Git/OpenAPI/migration/test-count evidence checks. | All governance records agree with current Git/worktree and source documents remain unchanged; owner approves before CORE-01. | +0 | None |
| GOV-02 — Premium AiSensy-Parity Product Goal Lock | Make premium functionality and presentation a permanent, original, evidence-based product acceptance standard without changing feature scope. | Product goal and priority order; reference-versus-copying boundary; no-placeholder rule; shared-component policy; 14-step review; 20-point premium screen Definition of Done; continuous-quality boundary. | Ten synchronized root governance documents; ADR-0012; Design Document 25; local-only ignored reference evidence. | Markdown structure and links; required-content/exclusion consistency; changed-file boundary; reference-ignore; migration/OpenAPI invariance. | All governance records agree; reference use is approved and bounded; exclusions remain permanent; no product code, migration, API, permission, architecture, or behavior changes. | +0 | None |

## Phase 1 — Core operations and real domain ownership

Phase 1 converts existing honest shells/projections into server-owned Vi operations. Existing
contacts, inbox, documents, auth, RBAC, audit, jobs, and Customer 360 foundations are extended, not
replaced.

| Milestone | Objective | Features | Files expected | Tests expected | Completion criteria | Est. OpenAPI increase | Est. migration |
|---|---|---|---|---|---|---:|---|
| CORE-01 — Navigation, scope, and UI-reference lock | Make approved navigation and design boundaries explicit before domain code. | Final navigation, remove/guard unrelated concepts, premium dark-green tokens, compact AiSensy-inspired permitted patterns, light/dark/responsive shell, no excluded routes. | `frontend/src/components/layout/*`; `frontend/src/routes/*`; shared UI/theme files; design decision record. | Navigation/RBAC/keyboard/mobile tests; excluded-route assertions; accessibility smoke. | Every approved destination is reachable or honestly labelled; no prohibited concept is visible; no existing feature is recreated. | +0 | None |
| CORE-02 — Vi domain foundation | Add the server-owned records required by the approved gap analysis as one coherent transactional domain baseline. | `ReactivationCase`, `ReactivationStageEvent`, `EligibilityCheck`, `KycCase`, `KycDecision`, `SimOrder`, `SimOrderEvent`, `ActivationRecord`, `SlaPolicy`, `SlaEvent`; repositories, services, schemas, RBAC, audit, tenant isolation, lifecycle APIs. | `backend/app/models/*`; repositories/services/schemas/endpoints; RBAC catalog; `backend/alembic/versions/0032_*`; generated OpenAPI/types; domain design/ADR. | Migration up/down/integrity; model constraints; transition matrices; approvals; permissions; audit; tenant isolation; API contract tests. | All listed records are persisted and exposed through additive, permission-scoped APIs; invalid transitions fail closed; OpenAPI/types have no drift. | +28–36 | `0032` domain foundation |
| CORE-03 — Reactivation pipeline | Connect the existing Reactivation workspace to real cases and transitions. | Persisted dashboard/Kanban/list, assignments, immutable history, notes/documents, eligibility/rejection reasons, reservation/family/conversion/SLA facts; the original stage catalogue is superseded by CORE-05 without rewriting history. | `frontend/src/features/reactivation/*`; domain API client hooks; focused backend service/endpoint adjustments. | Kanban keyboard/drag tests; optimistic concurrency; transitions; permissions; empty/loading/error/mobile states. | No mock lead cards remain; refresh preserves state; every transition produces immutable history/audit and respects RBAC/SLA. | +0–4 | None unless a reviewed constraint is missing |
| CORE-04 — KYC operations — COMPLETE | Deliver the complete protected KYC workflow on the shared domain foundation. | Profile, holder/Delhi/active-number checks, checklist, Task-backed appointments, protected Aadhaar/PAN references, structured rejection, reviewer/manager separation, immutable audit/Timeline, SLA and approved Reactivation handoff. | Existing KYC/Task/Document/Reactivation/Customer 360 authorities; dedicated KYC feature; migration `0033_kyc_operations`; generated contracts; ADR-0016; Design Document 29. | Checklist/decision/approval matrices; protected-document/tenant/RBAC denial; concurrency/idempotency; audit/Timeline/handoff; UI/accessibility/responsive states. | COMPLETE — real persisted workflow passes all repository/deployed gates; no identity number, fake data, protected-media bypass, parallel authority, or completed-module rebuild was introduced. | +4 actual | `0033` KYC operations (actual) |
| CORE-05 — Lightweight Reactivation CRM — COMPLETE | Replace the planned heavy SIM/Activation operating products with the owner-approved internal CRM while preserving their backend foundations. | Exactly one of nine primary statuses; six flexible labels; Follow-up/Release dates; Task-backed Upcoming/Due Today/Overdue reminders; Complete/Snooze/Reschedule; assignee, notes, chips, filters, Audit and Timeline. | Existing Reactivation/Task/Contact/User/Audit/Timeline/Celery/frontend authorities; migration `0034_reactivation_crm`; generated contracts; ADR-0017; Design Document 30. | Status/label/date constraints; Task lifecycle/due delivery; tenant/RBAC/concurrency; immutable evidence; filter/count; keyboard/drag; accessible responsive loading/empty/error/read-only UI. | COMPLETE — one factual server-owned CRM persists refreshes, uses no duplicate status/label concept or parallel reminder system, preserves historical evidence/foundations, and adds no fake workflow. | +1 actual | `0034` Reactivation CRM (actual) |
| CORE-07 — Customer 360 domain convergence — COMPLETE | Make the existing profile the authoritative operational workspace. | Real Reactivation/KYC/SIM/Activation facts, reminders, SLA, contact-scoped conversations, messages, campaigns, notes, documents, assignment, Tasks, Audit and Customer Timeline. | Existing Customer Profile, Inbox, Vi domain and shared section implementations; optional exact-Contact filters on existing APIs; generated contracts; ADR-0018; Design Document 31. | Exact-contact/tenant/RBAC API tests; factual composition, denied/read-only/error/no-placeholder tests; desktop/tablet/mobile and keyboard review. | COMPLETE — every section composes persisted source facts, respects permissions, deep-links to its source workflow, and introduces no duplicate record, synthetic metric, migration, or endpoint family. | +0 actual | None (actual) |
| CORE-08 — Skipped: Not required by product owner | General Approval Engine is not required. | Preserve existing KYC-specific approval logic and completed module-level authorization safeguards; do not build an Approval Center, generic approval framework, approval queue, escalation system, or new approval authority. | Governance records only; no product source, API, model, migration, permission, or UI files. | Governance consistency and changed-file boundary only. | SKIPPED — owner decision is recorded consistently and existing safeguards remain unchanged. | +0 actual | None |
| CORE-09 — Unified Notification Center — COMPLETE | Deliver durable, actionable in-app notification evidence over existing Task and Reactivation authorities. | Tenant/user-scoped records, unread count, mark-one/all-read, read-only team filter, source deep links, 15-second polling, Task due and Reactivation assignment/status projections, Audit evidence, lifecycle resolution and revision-safe redelivery. | Notification model/repository/service/endpoints, migration `0035_notification_center`, generated OpenAPI/types, top-nav center, tests, ADR-0019 and Design Document 32. | Tenant/RBAC/read-state/filter/deep-link/idempotency; task reassign/reopen/bulk/delete lifecycle; migration; generated-contract; frontend notification/layout accessibility tests. | COMPLETE — in-app evidence survives refresh/device use, stale task deliveries resolve, the correct recipient/revision can receive a fresh notice, and optional channels are not falsely claimed. | +4 actual | `0035` Notification Center (actual) |
| CORE-10 — Dedicated Chat History — NEAR COMPLETE (`PAR-DL-02`, `PAR-HIST-01`) | Separate operational history from the live inbox. | Delivered: dedicated read route, agent/customer/status/channel/tag/date/campaign/media/audit filters, resolved records, full bounded message history, governed team-shared views, audit deep link and complete/date-bounded transcript exports. Remaining: authenticated representative-data WCAG/device/browser review and production-scale/target-host query commissioning. | Existing conversation/message/audit authorities; chat-history feature; shared export/Download Center pipeline. | Filter/pagination/tenant/permission/query-budget tests; route/sheet/mobile/accessibility tests; target-host performance evidence. | Dedicated page reproduces complete factual history without mutating live-chat queues or loading unbounded conversations. | +0–1 remaining | `0054_chat_history_filters_views` delivered |
| CORE-11 — Core settings, team, tags, and SLA controls — PARTIAL (`CORE-11A/11B/11C` implemented) | Close remaining administrative gaps using existing admin/settings foundations. | **Delivered:** validated least-open/manual assignment, automatic/manual read state, exact opt-in/out keywords, organization-timezone weekly hours, new-window welcome, rate-limited off-hours replies, and protected inactivity auto-resolve with fresh-inbound reopen. **Remaining:** campaign preferences, pipeline/SLA, notification/security/audit settings; online/workload/login/permission audit; required/active attributes. | Existing settings/admin/tag/attribute backend/frontend files; possibly configuration migration. | Settings validation; role matrix; assignment/SLA calculations; audit; backward compatibility; responsive admin UI. | Final CORE-11 completion still requires every remaining approved control to be persisted, permission-scoped, audited and consumed; CORE-11A/11B/11C satisfy that rule for their bounded controls. | +1 actual so far | None for CORE-11A/11B/11C; next additive revision only if later structures require it |

## Approved cross-cutting UI Taste Modernization

This sequence modernizes the existing product without changing feature scope or rebuilding the shell.
The sidebar, permission-aware navigation, routes, generated API contracts, source-domain ownership,
responsive/mobile navigation, keyboard/focus behavior, reduced motion, and semantic light/dark tokens
remain authoritative.

### Audit findings

1. Preserve and refine the strong shell/accessibility foundation rather than replacing it.
2. Reframe Dashboard hierarchy around factual Reactivation operator work, not messaging alone.
3. Separate connected Reactivation workspaces clearly from foundation/future capability.
4. Reduce overuse of large radii, nested cards, soft fills, gradients, and decorative elevation.
5. Converge Inbox, Contacts, and adjacent data-heavy screens on shared controls and state patterns.
6. Clarify role-relevant everyday navigation versus advanced controls without removing approved routes.
7. Require authenticated representative-data visual, responsive, accessibility, bundle, and
   performance evidence; source inspection is not final acceptance.

| Milestone | Objective | Scope | Completion criteria |
|---|---|---|---|
| UI-TASTE-01 — Documentation and audit baseline — COMPLETE | Freeze branch, baseline, findings, boundaries, priorities, and acceptance order before coding. | Governance records only; design variance `4/10`, motion `3/10`, density `8/10`. | COMPLETE at `9043fe03`; documentation-only boundary and remote HEAD were verified. |
| UI-TASTE-02 — Shared design-system modernization — COMPLETE AND OWNER-APPROVED | Establish consistent enterprise density and hierarchy before page work. | Named radius tiers; shared form, toolbar, filter and pagination primitives; Button/Card/PageHeader/PageContainer refinements; adoption in Contacts, Inbox and Notification Center. The later owner-directed parity follow-up expands named daily tabs, adds a permission-aware Manage group and completes a guarded Live Chat intervention/handoff lifecycle. | Current repository gates pass: lint, typecheck, 818 tests and production build. Host visual/reference comparison remains pending; no parallel component system exists. |
| UI-TASTE-03A — Operator-first Dashboard — IMPLEMENTED | Replace the messaging-led first screen with factual operational intelligence. | Cross-domain attention, blocked customers, KYC, SIM/Activation SLA risk, Campaigns, unread conversations, Templates, agent workload, today KPI changes, task snapshot and source actions. | Repository gates pass with 661 tests and split build; no fake metric/backend duplication; authenticated representative-data visual/reference review remains pending. |
| UI-TASTE-03B — Reactivation operational hierarchy — REPOSITORY VALIDATED | Apply the shared system to the highest-value Reactivation operator workflow without rebuilding its authority. | Stage/action hierarchy, due/reminder/SLA prioritization, connected-vs-foundation maturity, saved-view/pagination truth and responsive density. | Resume only from the latest approved Git HEAD when explicitly instructed; real persisted behavior, permissions, source contracts and representative-data review pass. |
| UI-TASTE-04 — Responsive, accessibility, and performance regression — REPOSITORY VALIDATED | Prove repository-verifiable modernization quality without claiming host evidence. | KYC route permission truth, debounced search, empty-result keyboard safety, shared modal focus/scroll behavior, narrow pagination, authenticated route splitting and dead-code removal. | **REPOSITORY VALIDATED** in workflow `30980229127`; main bundle 199.78/54.87 kB gzip; host browser/device/screen-reader evidence remains pending. |
| UI-TASTE-05 — Owner review and merge — REPOSITORY VALIDATED | Determine owner-approval and merge readiness without adding features or changing architecture/governance. | One verified Major campaign chunk-order correction, full repository audit and synchronized validation records. | **REPOSITORY VALIDATED** in workflow `30982637585`; no repository-scope Blocker/Major remains; host evidence stays pending; explicit Owner Approval and Merge are the only next actions. |

## Phase 2 — Messaging, growth, analytics, and integrations

| Milestone | Objective | Features | Files expected | Tests expected | Completion criteria | Est. OpenAPI increase | Est. migration |
|---|---|---|---|---|---|---:|---|
| GROW-01 — Campaign domain completion (PARTIAL: PAR-DL-03/PAR-CAM-01) | Extend the release-ready broadcast engine only for final-scope gaps. | Delivered: governed PDF/CSV/XLSX/JSON results plus complete server-filtered/cursor-paginated recipient failure operations and confirmed retry. Remaining: conversion/campaign-to-reactivation facts and approved recovered-value/revenue/ROI inputs. | Existing campaign/reactivation/analytics authorities; shared Download Center. | Conversion attribution; source-formula truth; end-to-end campaign reply-to-lead; target-scale query plans. | Every approved campaign report is factual; delivery is never mislabeled as conversion/revenue and excluded Meta Ads functionality remains absent. | +1–2 remaining | `0055` export permission and `0056` ledger indexes delivered; future additive revision only for new source facts |
| GROW-02 — Template completion | Close template-management gaps without replacing the registry. | Draft/pending/approved/rejected, text/media/button formats, variables/preview, sync, favourites, categories, usage analytics, non-executing AI generator placeholder. | Existing template backend/frontend; favourite/category/analytics additions; generated contracts. | Meta sync/status/format/variable tests; favourite/permission/preview/accessibility tests. | Every approved template type and state is managed safely; placeholder is explicitly non-executing. | +2–4 | Future additive revision if required |
| GROW-03 — Segments and server-saved views — PARTIAL (`PAR-VIEW-01/02/03/04/05`) | Make approved operational audiences reusable across users. | Delivered for Reactivation, Contacts, Campaigns, KYC and Reports: module-validated filters, personal/team scopes, permission-governed sharing, Audit and portable reopening without stale transient state. Remaining: approved segment predicates/saved filters. | Shared workspace-view authority now serves all five named product workspaces without a parallel model. | Delivered tenant/private/workspace/RBAC/scope/validation/migration/route/UI tests; remaining predicate truth/performance/integration tests follow the Segment slice. | Complete only when the remaining Segment definition is server-owned and reproducible; all five delivered slices independently satisfy that contract. | +1 remaining | `0057_reactivation_saved_views` through `0061_reports_workspace_views` delivered; one future additive revision only if the Segment slice requires persistence changes |
| GROW-04 — Live simplified automation | Consume durable receipts through governed, idempotent effects. | Approved triggers/conditions/actions, delay/reminder, status/label movement, assignment, messages, notifications, stop/archive rules, approvals/handoffs, retries/DLQ, execution history. | Existing automation runtime; effect ledger/worker/services; builder/run UI; additive migration. | Effect idempotency; checkpoint/resume; approval/handoff; safe sends; domain transitions; failure/retry/DLQ; tenant/RBAC/audit; deployed Celery E2E. | The `Trigger → Conditions → Actions` examples in final scope execute through existing authorities with no duplicate side effects. | +5–8 | Future additive revision |
| GROW-05 — Domain analytics — PARTIAL (`PAR-REP-03/04` implemented) | Extend existing rollups with lightweight Vi CRM dimensions and factual team operations. | Delivered: event-derived Reactivation/KYC/SIM/Activation/SLA outcomes plus conversation/task teammate productivity and a separately labelled live pending-work snapshot. Remaining: campaign-to-case attribution, approved recovered-value/revenue/ROI and explicit capacity/utilization inputs. | Existing Analytics rollup/query/export/schedule pipeline; domain business-event ledger; indexed Conversation/Task authorities; additive `0051`/`0052`. | Rollup determinism/rebuild/time-zone/tenant/query-budget; stock-vs-flow truth; metric fixtures; chart/export tests. | Every scope metric has a documented source/formula and no stock value is summed across time or inferred from unrelated facts. | +1–3 remaining | Future additive revision only for approved source facts |
| GROW-06 — Executive reports and Download Center (PARTIAL: PAR-DL-01/02/03, PAR-REP-01/02/03/04) | Finish governed management reporting and extend the implemented personal artifact home. | Delivered: contacts; eleven Analytics families/schedules/notifications; domain outcome and Team Productivity packs; Chat History transcripts; full campaign recipient results; status/history/expiry/permissions. Remaining: revenue, conversion attribution, ROI, approved capacity/utilization, compliant Scan results and generated-document artifacts. | Extend remaining approved projections/source artifacts; reuse the implemented schedule/export/Notification/Download Center authorities. | Formula/time-zone/PDF/CSV/expiry/download-security; worker and UI tests. | Executives can schedule and retrieve every approved report; every artifact is permission-scoped, auditable, expiring, and visible in Download Center. | +1–3 remaining | `0055_campaign_results_exports` delivered; future additive revision only for remaining sources |
| GROW-07 — Google Sheets | Add the only missing approved integration without a marketplace. | Admin connection, secret handling, sheet/range mapping, contact import/sync/export jobs, dedup, retries, status, audit, revocation. | Integration model/service/adapter/endpoints/tasks; additive migration; settings UI; docs. | Credential encryption/redaction; mocked Google API; mapping/dedup/idempotency/retry/revoke/tenant tests; job UI. | Authorized sheets exchange data through queued, auditable jobs; failures are recoverable; no unused integrations are introduced. | +6–9 | Future additive revision |
| GROW-08 — Webhook completion | Extend existing webhook operations for final domain events. | Subscription management, secrets, event selection, delivery logs, signatures, retries/replay, final-domain events, usage visibility. | Existing webhook service/endpoints/worker/UI; event catalog/docs. | Signature/replay/dedup/retry/redaction/permission/tenant tests; final-domain event fixtures. | Consumers can safely subscribe to approved events with observable, replayable delivery; provider webhooks and outbound webhooks remain distinct. | +2–4 | None unless subscription persistence lacks fields |

## Phase 3 — Enterprise completion, API, and compliant future work

| Milestone | Objective | Features | Files expected | Tests expected | Completion criteria | Est. OpenAPI increase | Est. migration |
|---|---|---|---|---|---|---:|---|
| ENT-01 — API management and documentation | Complete the private integration surface over final-domain APIs. | Contact/campaign/reactivation/status-label-reminder/timeline/KYC APIs, preserved foundation APIs, subscriptions, API keys/permissions, usage logs, IP restrictions, regenerate/revoke, interactive docs. | Existing API-key/auth middleware; final-domain endpoints; usage models; developer UI/docs; generated contracts. | Key lifecycle/IP/RBAC/rate/usage/redaction/tenant; OpenAPI examples and compatibility tests. | Every approved resource is documented and permission-scoped; revoked/restricted keys fail immediately; OpenAPI never shrinks silently. | +4–7 | Future additive revision if required |
| ENT-02 — Global search and advanced audit | Index every approved entity and normalize enterprise evidence. | Customers/numbers/chats/campaigns/documents/cases/labels/reminders/notes/agents/tags search; old/new values, device/login, assignment/status/document/campaign/approval audit. | Search/audit services/endpoints/index tasks; command palette; audit timeline UI; possible index migration. | Search authorization/ranking/staleness/tenant; audit immutability/redaction; keyboard/action tests; performance. | Search returns only authorized current data and all approved mutations/access decisions produce attributable audit evidence. | +4–7 | Future additive revision if needed |
| ENT-03 — Command palette and advanced mobile | Complete fast keyboard and field-device operations across final routes. | All approved `Ctrl+K` actions, collapsible sidebar, drawers/modals, notification badges, skeleton/empty states, touch-safe tables/Kanban, responsive Customer 360. | Shared layout/UI primitives and module integrations; no parallel pages. | Keyboard/focus/touch/viewport/reduced-motion/high-contrast tests; route-level visual regression. | Every final route is operable on desktop keyboard and approved mobile widths with consistent, accessible primitives. | +0 | None |
| ENT-04 — WhatsApp Scan authorization contract | Approve a compliant technical method before enabling scan execution. | Provider/legal/security/data-retention contract, allowed results, rate/queue/export/analytics design; explicit ban on unofficial WhatsApp Web enumeration. | ADR/design/security/threat-model documents; feature flag policy. | Contract review, abuse/rate/privacy threat cases; no production execution test yet. | Owner and compliance approve a documented authorized method; otherwise the shell remains non-executing and the implementation milestone is blocked honestly. | +0 | None |
| ENT-05 — Compliant WhatsApp Scan implementation | Deliver the future module only under the approved contract. | Upload lists, batches, duplicates, queue, active/business/invalid results, retries, export, segment creation, analytics. | Scan models/services/adapter/endpoints/tasks; additive migration; existing Scan Studio UI; Download Center/Segments links. | Authorization boundary; dedup/idempotency/rate/retry/tenant/RBAC/audit/privacy; provider mocks; queued deployed E2E. | Every result comes from the approved method, is auditable/exportable, and cannot perform unofficial bulk enumeration. | +8–12 | Future additive revision |

## Phase 4 — Final quality, commissioning, and acceptance

| Milestone | Objective | Features | Files expected | Tests expected | Completion criteria | Est. OpenAPI increase | Est. migration |
|---|---|---|---|---|---|---:|---|
| REL-01 — Full-scope accessibility and UX acceptance | Validate the premium UI with real workflows and data. | WCAG-oriented audit, keyboard/focus, contrast, screen-reader labels, responsive/mobile, loading/empty/error states, final permitted workflow review. | Fixes only in existing components/routes; accessibility evidence and runbook updates. | Automated accessibility plus manual desktop/mobile/browser matrix; workflow UAT. | No critical accessibility issue; every approved route passes owner UX acceptance; excluded surfaces remain absent. | +0 | None |
| REL-02 — Security, resilience, and capacity certification | Prove scale and failure behavior after feature completion. | SAST/dependency/image scans, SBOM, backup/restore, Redis/Celery/provider loss, load/stress/spike/soak, 1M-contact target, bundle/query optimization. | Existing quality/deployment scripts; focused fixes; evidence artifacts/docs. | Full static/pre-merge/release/deployed gates; chaos/recovery/performance lab. | All repository gates pass; capacity budgets and recovery objectives have reproducible evidence; no known high/critical release blocker. | +0 | None unless an additive performance index is reviewed |
| REL-03 — Target-host commissioning and final acceptance | Close environment-only evidence and release the complete private platform. | TLS/host hardening, secrets, migrations, owner bootstrap, MySQL/Redis/Celery/nginx health, monitoring/log shipping/alerts/synthetics, UAT, restore and rollback rehearsal. | Deployment configuration/runbooks; final governance ledgers; release notes/tag. | Target-host smoke/E2E; alerts/dead-man; restore/rollback; acceptance checklist. | Every `VALIDATION_RESULTS.md` item is `PASS`, every module is 100% or explicitly owner-deferred, final scope traceability is complete, and owner approves release. | +0 | Upgrade through final additive head |

## Scope traceability

| Final-scope area | Roadmap coverage |
|---|---|
| Dashboard; Customer 360; Reactivation; KYC; Documents; SIM/Activation status facts; SLA | CORE-02–CORE-05, CORE-07, UI-TASTE-02–UI-TASTE-04, GROW-05, GROW-06; standalone heavy SIM/Activation workspaces require a later explicit owner instruction |
| Inbox; Chat History; Contacts | CORE-01, CORE-07, UI-TASTE-02–UI-TASTE-04, CORE-10, GROW-03 |
| Campaigns; Templates; Segments; Automation | GROW-01–GROW-04 |
| Analytics; Executive Reports | GROW-05–GROW-06 |
| Team; roles; tags; attributes; settings | CORE-11 |
| Notifications | CORE-09, UI-TASTE-03–UI-TASTE-04 |
| Google Sheets; Webhooks | GROW-07–GROW-08 |
| API and API keys | ENT-01 |
| Global Search; Command Palette; Audit Timeline; Saved Views | GROW-03, ENT-02, ENT-03 |
| Module-specific approval safeguards; Download Center | CORE-08 skipped by owner; existing KYC/campaign/automation safeguards preserved; GROW-06 covers Download Center only |
| WhatsApp Scan | ENT-04–ENT-05 |
| Dark/light, mobile, tables, charts, drawers, Kanban, loaders, empty states, badges, keyboard | CORE-01, UI-TASTE-02–UI-TASTE-04, module milestones, ENT-03, REL-01 |
| Accessibility, performance, Docker, Celery, Redis, security, production | Every closeout gate; UI-TASTE-04; REL-01–REL-03 |

## Roadmap completion rule

This roadmap ends only when every included requirement in the final product scope is implemented and
validated, or the owner explicitly approves a documented deferral. A percentage, route shell, mock,
or placeholder is not completion. Excluded features never become roadmap candidates merely because
they appear in reference captures.
