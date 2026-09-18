# Final Product Implementation Roadmap

## SEC-01 — the API explained itself to anyone who asked (2026-09-18)

`/docs`, `/redoc` and `/api/v1/openapi.json` were mounted unconditionally and served without
authentication, in every environment including production. Confirmed against the running stack: all
three answer **200** with no token.

**This is a map, not a breach**, and saying otherwise would overstate it: no endpoint is reachable
without a token, and the schema exposes no data. But it is every path, every payload shape and every
enum of a **private telecom operations platform**, handed to an anonymous visitor — reconnaissance
that costs an attacker one request and tells them exactly which of 247 endpoints to spend their time
on.

`API_DOCS_ENABLED` now decides, and left unset it follows the environment: **on outside production,
off inside it**. The explicit setting wins in both directions, so a team that wants a public
reference says so rather than getting one by default, and a developer loses nothing locally.

Nothing in the product depends on the mount: the frontend reads `frontend/openapi.json`, exported at
build time by `scripts/export_openapi.py`, which builds the schema from the application object
rather than fetching the URL.

**This is not the "published documentation" item** that Audit records as pending for the API module,
and that row does not move. Publishing a reference for integrators is a deliberate act somebody
still has to take; what changed is that not taking it no longer publishes one by accident.

## AUDIT-02 — a trail an investigator can read without translating it (2026-09-18)

`MODULE_STATUS` listed **"normalize remaining old/new values"** as pending on Audit Timeline. The
snapshots the services record are good — `status`, `category`, `reason`, `assigned_user_id` — and the
dialog printed them raw:

| the snapshot said | the screen showed | it now shows |
|---|---|---|
| `null` | `null` | **Not set** |
| `true` | `true` | **Yes** |
| `""` | *(blank cell)* | **Empty** |
| `[]` | `[]` | **None** |
| `["gold","silver"]` | `["gold","silver"]` | **gold, silver** |
| `2026-07-22T09:00:00Z` | `2026-07-22T09:00:00Z` | the reader's own local date and time |
| `checklist_purpose` | `checklist_purpose` | **Checklist purpose** |

Each one is small and each one is a translation the reader had to do in their head, on every row, at
the moment they were trying to follow what happened. `null` printed as the word "null" is the worst
of them: it reads as a value somebody set rather than a field nobody filled.

**Internal numeric ids are deliberately left alone.** Turning `assigned_user_id: 42` into a name
needs the API to carry that name, and inventing one on the client would be a guess presented as
evidence — in the one screen where that is least acceptable. It stays as `42`, and the work to
resolve it stays named in the pending column rather than quietly dropped.

The two helpers live in `selectors.ts` beside `auditChanges`, not in the dialog, so the list and any
later surface read the trail the same way.

Audit Timeline 96% → **98%**.

## ATTR-01 — a field that must not be emptied, and one that has been retired (2026-09-18)

`custom_attribute_definitions` could say a field was indexed and that it held PII. It could not say
either of the two things an operations team actually asks of a field definition: *this one must not
be left blank*, and *we have stopped using this one*. `MODULE_STATUS` listed both as
**"Required/active controls … preserve existing model."**

**"Required" had to be defined before it could be built, and the obvious definition is wrong.**
`PUT /contacts/{id}/attributes` is a **partial** update: it writes the keys it is handed and deletes
the ones passed as `null`. So "required" cannot mean *every write must carry this key* — that reading
would reject every ordinary edit that touches one field, and every contact import in the product,
the moment somebody ticked the box.

It means **it may not be cleared**. Passing `null` for a required attribute is refused; omitting it
is fine, and has its own test saying so, because that distinction is the whole design and would
otherwise be the first thing a later change breaks by accident.

**Retiring is not deleting.** A retired definition accepts no new value, and what was already
recorded stays readable *and stays clearable* — so a field can be wound down and tidied up rather
than deleted out from under the contacts and segment rules that reference it. Deleting a definition
already removes its values; that was the only available exit, and it is a destructive one.

Both refusals arrive through the endpoint's existing field-level 422 envelope, as
`attribute_required` and `attribute_retired` beside the `unknown_attribute` and `invalid_value`
codes already there, so a client that handles one handles these.

**Both defaults preserve every existing row exactly** — nothing becomes required, nothing becomes
retired — so the migration changes no observable behaviour on its own.

In the UI the checkbox says **"Retired"**, not "Active", and is the inverse of the stored flag:
nobody sets out to make a field *not active*, they set out to retire it. Both states show as badges
in the definitions list, so the answer to "why won't this field save?" is visible without opening
the editor. Changing either flag is audited with before and after, because both change what the team
is allowed to record about a customer.

Tags and Attributes 96% → **99%**.

## DOC-01 — the document is the only door to the document (2026-09-18)

`MODULE_STATUS` listed **document-access evidence** as pending on Audit Timeline. Building it turned
up a second, larger thing sitting next to it.

**Reading a customer's identity document left no trace.** Every *change* to a document was audited
— created, version added, verified, rejected, expired, archived — and every *read* was not. That is
the wrong way round for a file that is somebody's Aadhaar or PAN: "who altered this record" is
rarely the question a compliance review opens with, and *"who looked at this customer's identity
document, from where, and when"* had no answer anywhere.

`contact_document.accessed` is now recorded whenever a signed preview URL is minted, following the
`channel_secret.accessed` precedent the codebase already set for an audited read. It carries the
document type, the version number and the file name — and, thanks to AUDIT-01, the address and
device the request came from. **The URL itself is deliberately not recorded**: a signed URL is a
credential for the bytes, so writing one into the audit trail would make the trail a second copy of
the thing it protects.

**And the permission had a second door.** A document is *built on* a media asset and shares the
upload endpoint, so one row in `media_assets` holds either a campaign image or an identity scan.
`documents:read` guarded the document routes and guarded nothing on the media routes. Proved, not
inferred — a user holding only `media:read`:

| | before | after |
|---|---|---|
| `GET /documents/{id}` | 403 ✅ | 403 |
| `GET /documents/…/content` | 403 ✅ | 403 |
| `GET /media` | **lists `aadhaar.png`** | `[]` |
| `GET /media/{id}` | **200, metadata** | 403 |
| `GET /media/{id}/content` | **200, signed URL to the scan** | 403 |

**Severity, stated honestly: latent, not live.** No shipped role holds `media:read` without
`documents:read` — owner, admin, manager and agent all hold both, analyst holds neither — so nothing
is exposed in a default installation. But custom roles are a first-class feature with a permission
matrix built to compose them, and the moment somebody creates a "Media librarian" the second door
opens onto every customer's identity file. Splitting the two permissions means nothing if either
one reaches the same bytes.

**Closed by removing the door, not by duplicating the check.** The media API now refuses an asset
that backs a document outright, rather than re-checking `documents:read` there. The document route
already exists, already checks that permission, and now records the access — one door, guarded and
logged, beats two doors that have to agree with each other forever. Derived live from
`contact_document_versions` rather than flagged on the asset, because a flag can drift from the
truth it copies and a join cannot.

The library listing excludes them for the same reason: a customer's identity document is not
reusable campaign material, and showing it there leaks the file name and invites somebody to attach
it to a broadcast.

**A marker that does not cry wolf.** Protected reads get their own info-toned *Data access* chip in
the audit list and detail, not the red *Security* chip. That one means something went wrong; an
authorised read has not, and marking every one red would drown the failures the chip exists to
surface. But these are the rows a compliance review scans for, and in a list where every other entry
is a change they are easy to walk past.

Documents 87% → **89%**; Audit Timeline 94% → **96%**.

## GATE-01 — the browser gates needed Docker, and now they do not (2026-09-18)

A11Y-01 committed a WCAG gate over 24 authenticated routes, and the release-gate owner journey has
existed since before it. Both live in `e2e/tests/`, and both were reachable only through the
`deployed` quality profile, which builds containers. That is correct for CI and an obstacle
everywhere else — including the environment this milestone was written in. A gate nobody can run is
a gate that quietly stops being true, and the two proved that within hours: A11Y-02 exists because
re-running them found contrast gaps A11Y-01 had left behind.

`scripts/local_stack.sh` starts what they need on top of the existing `local_services.sh` — the
API, a Celery worker, and the **production build** behind the same-origin `/api` proxy that
BUILD-01's `vite preview` config added. Idempotent, returns in 0.06s when everything is already up,
and cold-starts in **24 seconds**.

Writing it surfaced three things that each cost an hour to diagnose, so each is handled in the
script and written down in the README rather than left as folklore:

**A launcher that never returns.** `( cmd & )` is not detachment: the subshell stays the parent and
waits, so the script's stdout is held open by a server that will not exit for hours. From a terminal
that looks like a hang; from a CI step or an agent it *is* one. The first version of this script did
exactly that and sat for ten minutes with every service healthy. Each process now starts under
`setsid` with stdin closed and output redirected.

**The worker is not optional.** Without one the journey reaches "Start import" and waits until it
times out, which reads as a broken import rather than as a missing process.

**Sign-in is rate limited**, to 10 attempts per 5 minutes, and every browser test signs in. One
`playwright test` spends half the budget and a second run inside the window gets `429` on login —
at which point three tests fail on a blank page and look like broken screens. That is how it was
first seen here. The script disables the limiter for this local stack exactly as
`backend/tests/conftest.py` already does, with the reason stated; production keeps the default,
which is on.

Verified the only way that means anything: the whole stack stopped, brought up by the script alone,
and all five browser tests run against it.

## A11Y-02 — the gate caught what A11Y-01 missed (2026-09-18)

Re-running the accessibility gate after BUILD-01, against a database the owner-journey spec had
since filled with automations, produced two failures. Neither came from BUILD-01. Both were gaps in
**A11Y-01's own work**, and finding them is the entire reason that gate is committed rather than
run once and reported.

**The muted tone was only checked against half the backgrounds it lands on.** A11Y-01 cleared
`--color-text-disabled` against the four surface tokens. It never checked the five `-soft` tints,
and the tone lands on those too — the sub-line on a *selected* automation card sits on
`--color-accent-soft`, where the dark theme measured **3.83:1**.

Checking the tone against every background it actually reaches found **three** failures, not one:

| | dark accent-soft | light danger-soft | light info-soft |
|---|---:|---:|---:|
| before | 3.83 | 4.39 | 4.48 |
| after | **4.56** | **4.59** | **4.60** |

Only the first was rendered on the night — a selected automation card needs an automation to exist,
and none did until the release-gate journey created one. The other two sat latent, waiting for a
danger or info tint to carry a muted label. Reporting "zero violations" was true of what rendered;
it was not true of the token.

Fixed at the token, not the component: `#636e85 → #606b81` in light and `#858ead → #949cb7` in
dark. Both are small moves, and both now clear 4.5:1 against **all nine** backgrounds — four
surfaces and five soft tints. The gap to `--color-text-secondary` narrows to about two points of
luminance, which is the same trade A11Y-01 made and is restated in the token's comment rather than
left to be rediscovered: a step in a three-step scale that fails DS-10 is not a step worth keeping.

**A fourth scrollable table.** `BreakdownTable` joins the three A11Y-01 converted to `ScrollRegion`.
It failed for the same reason and only at phone width, and only now that analytics has rows wide
enough to overflow — the same "invisible until the data arrives" shape as the contrast gap above.

All five browser tests pass: WCAG 2.1 AA over 24 routes in the light theme, the same 24 in dark, the
same 24 at 375px, the sign-in screen, and the owner journey end to end.

## BUILD-01 — a third of the entry bundle was a screen almost nobody opens (2026-09-18)

Two production-readiness items that needed no new feature work.

**Rollup had been saying it out loud.** Every build printed
`INEFFECTIVE_DYNAMIC_IMPORT: src/features/operations/index.ts is dynamically imported by
src/routes/router.tsx but also statically imported by ... src/routes/router.tsx`, and the warning
was exactly right. `router.tsx` pulled one constant, `OPERATIONS_PERMISSIONS`, from the feature's
**barrel**; the router lives in the entry chunk; so the barrel — and with it the job list, the queue
monitor, the logs panel, the system-health panel, the webhooks panel and the operations overview —
was in the first thing every user downloads. The six `lazyNamed(...)` calls right below that import
split nothing at all.

`OPERATIONS_PERMISSIONS` lives in `sections.ts`, which is pure data and imports no component.
Taking the three static imports from the modules that define what they need, instead of from the
barrel, is the whole change:

| | before | after |
|---|---:|---:|
| entry chunk, raw | 276 kB | **185 kB** |
| entry chunk, gzip | 70 kB | **50 kB** |
| all JS, raw | 1,808 kB | 1,813 kB |

**20 kB of gzip off first paint, a 29% smaller entry**, and the total barely moves — which is the
point: the code did not disappear, it moved to a chunk that loads when somebody opens Operations.
Measured by reading the entry filename out of the built `index.html` and gzipping it, with the
change stashed and unstashed, rather than by reading Vite's summary and hoping the same chunk was
being compared.

**The dependency audit is clean, and it was already clean where it counts.** `npm audit
--omit=dev` reported **0 vulnerabilities** before any change: nothing shipped to a browser was
affected. Four advisories (3 high, 1 moderate) sat in the build toolchain — `js-yaml` reached
through `@redocly/openapi-core`, plus `browserslist` and `baseline-browser-mapping`. All four were
semver-safe, so `npm audit fix` resolved them with **no change to `package.json`**; only the
lockfile moved.

The one thing worth checking after that bump is the contract: `openapi-typescript` sits inside the
chain that moved. Regenerating `schema.d.ts` produces a **byte-identical** file, so the generated
client is provably the same as the one every screen was written against.

`pip-audit` reports no known vulnerabilities for the backend, and the browser-test package reports
none.

## PERF-02 — the Scan screen cost the whole ledger the moment you filtered it (2026-09-18)

With the stack running on a database carrying **20,043 contacts and 200,000 campaign recipients**,
the contract's read sweep put `/api/v1/scan/reachability` at the top of its slowest list. The
sweep exists to notice exactly that: *"a query that costs what the account weighs rather than what
the page weighs is invisible on an empty database and easy to write by accident."*

**The unfiltered page was 13ms. Every verdict filter was 400–460ms.** Filtering by verdict is the
ordinary way that screen is used — "show me who is not on WhatsApp" is the question it answers — so
the fast path was the one nobody takes.

The aggregate has to read the whole ledger, and that part is not a defect: a verdict is only known
once every receipt for a contact has been read, so there is no page of fifty to narrow to first.
`_evidence()` already documents that split, and the page's own half was optimised in SCAN-01. What
was left is that **none of the columns the aggregate reads were in any index.** Access was served by
`uq_crecip_campaign_contact`, then each of ~200,000 matched rows cost a separate row lookup for
`status`, `error_code`, `delivered_at`, `read_at` and `failed_at`.

`ix_crecip_reachability` covers them. The plan goes from a row lookup per match to index-only:

| | before | after |
|---|---:|---:|
| `verdict=reachable` | 403 ms | **181 ms** |
| `verdict=unreachable` | 396 ms | **183 ms** |
| `verdict=unknown` | 445 ms | **229 ms** |
| `/reachability/counts` | 460 ms | **216 ms** |
| `/templates/usage` (same ledger) | 417 ms | **155 ms** |

Every one moves from over the project's **300ms** budget to inside it, and the read sweep's slowest
path falls from **563.5ms to 226.7ms** across all 210 requests.

**The cost is on the write side, and it was measured rather than assumed.** `delivered_at`,
`read_at` and `failed_at` are in the index and all three are written as receipts arrive, so every
receipt now maintains it. A bulk update of 2,000 recipients went from 57.8ms to 69.6ms — **+21%, or
about six microseconds per receipt.** That is the right way round for a ledger written once per
message and read on every visit to the screen, and it is recorded here so the trade can be revisited
rather than rediscovered.

Non-unique, so MySQL's rule that a unique index must include the partitioning column does not apply
and `created_at` stays out of it.

## OPS-01 — the log line that killed every campaign dispatch (2026-09-18)

Starting a Celery worker to exercise the async paths produced this, immediately, on every campaign
dispatch task:

```
Task app.crm.campaign_tasks.dispatch_campaign raised unexpected:
KeyError("Attempt to overwrite 'created' in LogRecord")
```

`campaign_batch_service.plan()` logged `extra={"created": len(created), ...}`. `created` is a
`LogRecord`'s own timestamp, and `logging.makeRecord` **raises** on any key that would overwrite a
record attribute. It raises *before* any formatter runs, so the JSON formatter's redaction and the
reserved-name filter it already carries cannot help — the exception happens earlier than either.

**Campaigns are what this platform is for, and dispatch died on its way to planning the batches.**
Not degraded, not slow: the task raised, and the log line was the only thing that had gone wrong.

**Why 1,742 tests never saw it.** `Logger.info` checks the level and returns before building the
record, so a log statement above the active level is never executed. The suite ran above INFO,
which means it type-checked every log call in the codebase and executed almost none of them. The
line failed the moment a worker started with `--loglevel=info` — which is every worker.

Set `log_level = "INFO"` in the pytest configuration, and **thirteen existing tests catch it**. They
were always the right tests; they were being run with the failing statement switched off. Every log
statement in the package now executes under test. The full suite is green at INFO: **1,744 passed,
0 skipped** against live MySQL 8.

**A second guard, because one word in a dictionary is easy to repeat.** A test walks the AST of the
whole `app` package and asserts no `extra={...}` key collides with a `LogRecord` attribute. It
prints the file and line, so the fix is obvious from the failure. The sweep found exactly one
collision — this one — and every `extra=` in the codebase is a literal dict, so the sweep sees all
of them.

**The release-gate journey could only ever run once.** With a worker finally running, the existing
`contacts-import` spec passed — then failed on the second run, and on every run after. It imports
two contacts at fixed numbers, and the default duplicate policy is *skip*: against a database that
already holds them nothing is created. The first failure looks like a broken import; the second is
worse, because the assertion that a new contact **fires the automation trigger** cannot hold when no
contact was created, so a reused fixture reads as a broken automation.

Both fixtures are now unique per run. "One contact imported, trigger fired" becomes true every time
rather than true only against a virgin stack — a stronger claim, and one that lets the gate run
against a long-lived environment instead of only a disposable one. Verified by running it three
times in a row against the same database.

## A11Y-01 — the accessibility review every module was waiting on (2026-09-18)

Seven module rows carried some form of *"authenticated representative-data visual/WCAG/device
review"* as pending, and it had stayed pending because it reads like something only a target host
can settle. Most of it is not. The failures live in status chips, table headers, timestamps,
avatars and primary buttons — none of which a signed-out page draws, all of which a signed-in
browser can measure. Chromium and a seeded database are enough.

So: the API against the live MySQL 8, the **production build** served behind it, a real sign-in,
and axe-core over **24 routes** in **both themes** at **1440px and 375px**, plus the sign-in screen.

**The first run found 151 failing nodes.** They reduced to six causes, and every one was a
one-place fix:

**`text-*` was painting with a tone meant for solid marks.** `index.css` already said so — *"the
base tone is tuned for solid marks (dots, bars) and does not reach 4.5:1 as 12px text on its own
tint"* — and already defined `--color-*-on-soft` for the purpose. What the note understated is that
it was not only the soft tint: `text-success` on plain white measures **3.37:1**. A status word
written with the base tone failed everywhere it appeared, in **over three hundred** places.

Fixed at the utility rather than the call sites: `textColor` now maps `text-success` /
`text-warning` / `text-danger` / `text-info` to the on-soft tone, while `bg-*` and `border-*` keep
the base. The accessible tone becomes the default — an author writing `text-danger` gets the
readable red without having to remember that two exist — and fills, borders and marks are
untouched. The explicit `-soft` and `-on-soft` names still work, so nothing that spells the tone
out loses meaning.

**White on the dark theme's accent measured 1.86:1.** Every primary button and every avatar, on
every screen, in the dark theme. The dark accent is a bright teal, so a white label on it was close
to invisible; the light theme was fine at 5.47:1, which is exactly why a light-only pass would
never have reported it. The dark themes now take a deep teal ink (**9.15:1** on the accent, 11.51:1
on its hover tone) that keeps the brand hue rather than dropping to a neutral black.

**`--color-text-disabled` is named for inactive controls and used for readable content** —
timestamps, search hints, column labels, "never checked", the ⌘K hint. At `#99a1b3` that content
measured **2.3–2.6:1**. Darkened to clear 4.5:1 on every surface, in both themes. The cost is a
narrower gap to `--color-text-secondary`; legible beats subtly ranked.

**The destructive fill.** White on the light red sat at 4.37:1 — under the bar by a hair, on the
one button where a misread is expensive. The light fill is darkened and the label comes from a new
`--color-danger-fg`, mirroring the `--color-accent-fg` that already existed. The dark theme keeps
its lighter red, because there the tone is also a border and a mark where the bar is 3:1, and takes
a dark label instead.

**The avatar palette** was commented *"tuned for legible white text in both themes"* and nine of
its ten tones were not: between **2.15:1** and 4.47:1, the amber worst. Each is now the darkest-but-
one step of the hue it started from. A contact whose avatar was blue is still blue.

**Three tables could not be scrolled without a mouse.** A wide table inside a plain
`overflow-x-auto` div has no focusable element, so there is no way to put the caret in it and reach
the columns past the fold — invisible on the desktop it was designed on, and the reason the phone
pass was worth running. `ScrollRegion` is the governed primitive for it: a named, focusable scroll
container. Three call sites adopt it; the gate now catches the other fifty-six if they ever
overflow.

**The gate is committed, not a one-off.** `e2e/tests/accessibility.spec.ts` runs inside the existing
browser-runner image, which already executes every spec in `tests/`, so the deployed-stack profile
picks it up with no change to the runner. A failure prints the offending colours and element, so it
is actionable as printed. Two supporting changes make it runnable outside that container as well:
`E2E_ARTIFACTS_DIR` and `E2E_CHROMIUM_PATH`, and a `preview` proxy so the **built** bundle can be
exercised against a real API without deploying it first — otherwise the artefact that ships
furthest stays out of reach of the checks that run most often.

**What this does not close.** A human visual and taste review, the browser matrix beyond Chromium,
screen-reader narrative quality, and target-host/production-scale work all remain. Automated
conformance is a floor, not a verdict. The seven module rows now say that precisely instead of
carrying "WCAG review" as an open item that had, in fact, been passing nothing.

Shared Enterprise Design System 94% → **96%**.

## AUDIT-01 — where an action came from, and a digest that actually verifies (2026-09-18)

`MODULE_STATUS` listed **device identity** as pending on Audit Timeline: *"entries carry a source
address, not a device."* Building that turned out to be the smaller half of the story.

**Only sign-in ever recorded where an action came from.** `audit_logs.ip_address` has existed since
the schema was written, and exactly one caller filled it — `AuthService`. Every other audited action
in the platform recorded *who* and *what* and nothing about *where*. That gap does not show in a
column list: the column is there, populated for the rows somebody happens to check first, and the
absence is discovered by whoever has to investigate an incident, at the worst possible moment.

The origin now fills itself from a request-scoped context (`client_ip_ctx`, `user_agent_ctx`, set
and reset by the existing `RequestIDMiddleware` alongside the request id it already carried). An
action audited five layers below the route records its origin without every service signature
growing two parameters it has no way to fill. A background job has no request and records no
origin — which is correct; inventing one would be worse than leaving it blank.

`user_agent` is bounded to 400 characters at the context boundary, because a header is
attacker-controlled and unbounded, and an audit write must never fail because somebody sent a long
one. A truncated device string is still useful; losing the record would not be.

**The tamper-evidence digest had never worked.** The test written to prove the new column did not
break the hash chain failed — and not because of the new column. `created_at` was left to the
column default, which SQLAlchemy applies at **flush**, i.e. *after* `record()` takes the digest. So
every row ever written stored a real timestamp under a hash computed over `null`. No row could be
recomputed from its own persisted content, which is the only thing a stored digest is for.

Worse than useless: the one field left uncovered was the timestamp — exactly what a tamperer would
move and exactly what an investigator relies on.

Confirmed against the live database, not only in tests: all **33** rows already in `audit_logs`
classify as `verified_legacy`, and the first row written through the fixed path classifies as
`verified`.

The time is now stamped at construction, so the value hashed is the value stored. The canonical
form is otherwise **unchanged on purpose** — widening it would invalidate the digest of every
historical row, and a scheme that cannot verify yesterday is worth less than one covering slightly
fewer fields. `user_agent` therefore sits outside the hash, as `ip_address` already did.

**A digest nothing recomputes protects nothing** — which is precisely how this went unnoticed for
the whole life of the schema. `AuditService.verify()` now reports one of four verdicts, carried on
every entry the read endpoint returns and shown in the entry dialog:

- `verified` — reproduces exactly; content and timestamp both intact.
- `verified_legacy` — reproduces only under the pre-fix form. Content intact, timestamp never
  covered. Reported apart rather than as tampered: flagging the entire existing history would be a
  false alarm on the day the verdict was first needed, and calling it fully verified would overstate
  what its digest covers.
- `mismatch` — neither form reproduces; the row changed after it was written.
- `unhashed` — no digest was stored, so there is nothing to check against.

**Five unhandled promise rejections, fixed in passing.** The frontend suite reported two escaping
rejections from SIM-01 and APPR-01; the same defect sat in three more places in the automation
builder. `void mutation.mutateAsync(...)` discards the promise **without** attaching a rejection
handler, so a refused transition reached `window.onunhandledrejection` even though the screen
displayed the error correctly. Replaced with `.mutate(...)` — this repository's established pattern,
which routes failures into the `isError` state these components already read. The suite now reports
zero unhandled errors.

Audit Timeline 90% → **94%**. Device identity is done and the origin gap behind it is closed; what
remains is normalizing old/new values, document-access evidence, and the authenticated
representative-data review every module owes.

## APPR-01 — what is waiting on you, in one place (2026-09-17)

The last of the three modules the scope document excluded. `MODULE_STATUS` recorded CORE-08 as
**"Skipped: Not required by product owner"**, refusing *"No Approval Center, generic approval
framework, approval queue, escalation system or new approval authority"*. The owner has asked for
the remaining scope, so this is that work — built to honour the *reason* the original refusal was
right. Frontend 993 → **1,001** across **61 files**; no backend change, no migration, contract
unchanged.

**No new authority, and that is the whole design.** What CORE-08 refused was a second place where
permission to act is decided — a generic framework competing with the modules that already own
their decisions. Nothing here decides anything:

- A KYC item is approved through `POST /kyc-cases/{id}/approvals` under `kyc:approve`.
- An activation item through `POST /activation-records/{id}/approval` under `activation:approve`.
- The **read** permission shows the queue; the **approve** permission draws the button. Somebody may
  legitimately see what is pending and not be the person who signs it off, and a button they cannot
  use promises an authority they lack.

So the screen is a *view*, not a table: it holds no approvals of its own, introduces no state, and
would keep working unchanged if a module changed what approving means.

**What it answers is the question neither module could.** KYC lives in one workspace and activation
in another, so "what is waiting on *me*" required opening both and knowing to. Something waiting in
the workspace nobody opened today waited another day. It sits second on the dashboard, under
channel health — everything else there is work the team is doing; this is work the team is waiting
*for*.

**Oldest first**, because the thing that has waited longest is the thing most worth deciding.

**Identity-merge recommendations are deliberately absent.** They have an approve endpoint and no
list endpoint, so aggregating them would mean writing backend to fill a screen — the wrong order to
build in. Named here so their absence reads as a decision rather than an oversight.

Approval Workflow 20% → **70%**. The remaining thirty points are the escalation system and generic
framework the original decision refused on merit; nothing in tonight's instruction says those became
a good idea, and building them would still be building a second authority.

Canonical average 85.4% → **87.0%**.

PASS: frontend **1,001 passed across 61 files**, ESLint, TypeScript and the production build clean;
backend unchanged at 1,735 passed, 0 skipped against live MySQL 8.

## SIM-01 — the fulfilment queues the scope document said would not be built (2026-09-17)

**Owner decision, recorded.** `MODULE_STATUS` carried, for SIM Orders, *"No standalone heavy UI is
planned; future exceptional operations require an explicit owner instruction"*, and for Activation
the same sentence about an Activation Queue. The owner has now given that instruction. This is that
work, and the scope reversal is recorded here rather than left to be inferred from a diff.

Frontend 983 → **993** across **60 files**; no backend change, no migration, contract unchanged.

**The APIs have been complete since CORE-02.** Lifecycle, transitions, optimistic concurrency,
idempotency, RBAC, audit and events — all of it, for both domains, with nothing to call them. The
two nav links resolved to the reactivation pipeline filtered by stage, which shows *cases* at the
SIM stage: no serial, no delivery address, no service area, no dispatch state. "What is waiting on
us today" had no answer anywhere in the product, which is the one question a queue exists for.

**Both domains, one screen.** SIM delivery and activation are two halves of the same question, and
splitting them across two pages would make an operator check twice to answer it once. The `sim` and
`activation` sections both render it; each half is gated on its own permission, so a reader with
only `sim:read` sees only that queue.

Four decisions worth stating:

- **Boards by status, not flat lists.** The work moves left to right and a backlog should be
  visible without counting rows, so every column carries its count.
- **Settled work is folded away.** A queue that keeps showing delivered orders stops being a list
  of what to do and becomes a list of what happened. One button brings it back.
- **The row version travels from the row the operator looked at.** Two people working one queue is
  the normal case, and the second must be *told* the order moved rather than silently overwrite the
  first. The server can only tell them if it is given the version they saw.
- **Only the moves that make sense are offered.** `SIM_NEXT` and `ACTIVATION_NEXT` never widen what
  the API allows — the server remains the authority — they only stop somebody being offered
  "requested" on an order already on a van.

Search is by **serial, address or area**. An operator holds a serial off a physical SIM or an
address off a phone call; nobody holds a UUID.

**Three existing tests failed and were corrected, not deleted.** They pinned the old decision —
that these links redirect, and that `Connected` is exactly `pipeline, kyc, documents, reports`.
Those assertions were true when written and are now false, which is what a good pin does when a
decision is reversed on purpose.

SIM Orders 35% → **75%**. Activation 35% → **75%**. Canonical average 82.8% → **85.4%**.

PASS: frontend **993 passed across 60 files**, ESLint, TypeScript and the production build clean;
backend unchanged at 1,735 passed, 0 skipped against live MySQL 8.

## SRCH-01 — the palette can find the records this platform is about (2026-09-17)

`Ctrl+K` searched contacts, campaigns, templates, numbers, users, tasks, media and conversations.
It could not find a **segment**, a **tag**, or a **reactivation case** — which for a reactivation
platform means it could not find the record the whole business turns on. Frontend 977 → **982**
across **59 files**; no backend change, no migration, contract unchanged.

Three sources added, each gated on the permission that owns it and asked for **before** the request
rather than filtered out of the answer:

- **Segments** (`segments:read`) — by name, described by its own description or its condition count.
- **Tags** (`contacts:read`) — with the contact count, because a tag nobody uses looks identical to
  one on half the roster without it.
- **Reactivation cases** (`reactivation:read`) — by the customer on them, through
  `/reactivation-pipeline`, the one Vi-domain list with a real `q` of its own.

**KYC cases, SIM orders and activation records are not indexed, and that is not an omission.** All
three are addressed per contact or per case — `/kyc-cases?contact_id=…`, `/sim-orders?case_id=…` —
so there is nothing to search globally without an endpoint that does not exist. Inventing one to
fill a palette would be building the feature in the wrong order, and the reactivation case already
carries the customer these records hang off.

**A staleness fix, found by writing the test.** The placeholder read *"Search contacts, campaigns,
templates, numbers, tasks…"* — five sources, when the palette reached eight even before this. A
promise printed on the control ages exactly the way a contract description does, which this
repository has now been caught by three times in one day. It names what it searches.

One thing checked and deliberately **not** changed: the input looked like it had no accessible name,
and it has one — an `sr-only` label reading "Search the workspace". The test was corrected instead
of the component. Working code does not move to suit a test.

Global Search 85% → **92%**.

PASS: frontend **982 passed across 59 files**, ESLint, TypeScript and the production build clean;
backend unchanged at 1,735 passed, 0 skipped. Four of the five new tests fail against the old
palette; the fifth — "asks for nothing the signed-in user may not read" — passes on both, because
code that never made the request satisfies it trivially.

## DL-01 — a scan export you can tell apart in the Download Center (2026-09-17)

`MODULE_STATUS` asked the Download Center to "add compliant Scan-result sources". It already has
them: a scan export **is** a contacts export carrying a reachability rule (SCAN-03), so it lands in
the history, under `contacts:export`, with the signed link and expiry every other artifact gets.
Third time this week that reading the code answered a tracker item.

What was genuinely wrong was the **name**. Every contacts export was titled "Contacts export", so
an operator who exported the unreachable list and then the full roster saw two identical rows and
had to open both to tell them apart — on a screen whose entire job is telling artifacts apart.

The title is now read back off the filter: a single `scan`/`reachability`/`eq` rule names the row
after the list it came from, in the Scan screen's own words. **Only the single-rule case.** A
filter combining reachability with three other conditions is not "the unreachable list", and
naming it one would be a more confident claim than the filter supports — worse than the generic
title it replaces. A test pins that.

Backend 1,733 → **1,735**. No migration, no contract change (the name is derived, not stored).

Download Center 88% → **90%**.

PASS: backend **1,735 passed, 0 skipped** against live MySQL 8 (544.2s); Ruff, strict mypy (331
files) clean. Both new tests were run against the code they describe first; one failed and one
passed, the passing one being the "mixed filter keeps the plain name" case that the old code
satisfied by having only one name.

## SEG-02 — the team's own audiences, offered where somebody would look for them (2026-09-17)

The discoverability gap SEG-01 named, closed. Frontend 971 → **977** across **58 files**; no
backend change, no migration, contract unchanged.

Every segment is already visible to the whole organization — there is no private/shared
distinction on the model — and any of them could always be copied from the list's Duplicate action.
What was missing was smaller and more human than the feature I had wrongly told the owner was
absent: somebody building their first audience **never saw them**. The quick-start gallery offered
ten built-in recipes and nothing the team itself had written, so a colleague's work was
discoverable only if you already knew to scroll to the list and press Duplicate.

The gallery now shows **Start from your team's audiences** beneath the built-in row, carrying the
same `duplicateOf` state the Duplicate action uses. An entry point, not a second copy path.

Four small decisions, each with a reason:

- **The four most recent, not all of them.** Fifty audiences would bury the built-in recipes under
  a wall of the team's own history, and the rest are one link away in the list this page already
  renders.
- **Nothing at all when the team has built none.** A heading over an empty row reads as something
  broken rather than something unused.
- **The condition count when a segment has no description.** "3 conditions" is a weaker label than
  a sentence somebody wrote, and a better one than blank space.
- **Read from the cache, not a second request.** `useSegments` is already resolved for the list on
  this same page.

Two of the six new tests pass against the old gallery, which is correct and worth saying: they are
the negative cases — no audiences, and no permission — and the old code satisfied both by having no
feature at all. The other four fail without it.

Segments 78% → **82%**. Canonical average 82.4% → **82.5%**.

PASS: frontend **977 passed across 58 files**, ESLint, TypeScript and the production build clean;
backend unchanged at **1,733 passed, 0 skipped** against live MySQL 8 (this milestone touches no
backend file).

## SEG-01 — the reachability audiences, and a recommendation of mine that was wrong (2026-09-17)

Two quick-start audiences built on SCAN-02's rule, and a correction to advice I gave the owner an
hour earlier. Frontend 969 → **971**; no backend change, no migration, contract unchanged.

### The correction, first

Asked what "shared saved filters" meant for Segments, I offered the owner two readings and, when
they asked which was right, told them **neither** — and that the real gap was that *"Segments is the
one workspace left out; your team cannot make an eleventh recipe."*

**That was wrong, and I had not checked it before saying so.** Reading the code afterwards:

- `Segment` has **no visibility column**. It is scoped by `organization_id` with a unique name per
  org, so **every segment is already visible to the whole team**. There is no private/shared
  distinction to add, because nothing is private.
- **Duplicate already exists.** `SegmentActions` opens the editor prefilled from any existing
  segment, and has all along.

So the team *can* make an eleventh recipe: build a segment, name it, and anyone can start from it.
The library of shared recipes is the segment list. What I described as a missing feature was a
feature that shipped before I arrived.

This is the second time today that checking beat building — SCAN-03 found the export already
worked. The pattern is worth naming: a gap named in a tracker is a claim about the past, and it
ages. Both times, the honest move was to read the code before writing any.

### What was actually worth doing

`whatsapp_active` seeds from `contact.is_active_on_wa`, which is set **only when a customer writes
to us**. That misses every customer Meta delivered to who simply did not reply — which, for a
reactivation list, is most of them. It is the narrowest possible reading of "on WhatsApp".

Two audiences now sit beside it, seeded from the scan rule:

- **Reachable on WhatsApp** — Meta delivered a campaign message to them. A wider and more useful
  set than "they replied".
- **Not on WhatsApp** — Meta refused the number (131026). Excluding it stops paying for the same
  refusal every campaign, which is the money case SCAN-02 opened and this makes one click.

`whatsapp_active` stays, with its description corrected to say what it actually means rather than
"currently marked active", which explained nothing.

A test pinned the gallery at ten links and failed, correctly. It now counts `AUDIENCE_PRESETS`
instead of a literal: the assertion worth making is that every preset is reachable, not how many
there happen to be this month.

**Still genuinely missing, and not built here:** the quick-start gallery shows the built-in
audiences only. A team that has built its own segments does not see them there, and has to know to
find them in the list and press Duplicate. That is a discoverability gap worth closing, and it is
much smaller than what I told the owner it was.

No module percentage moves.

PASS: frontend **971 passed across 57 files**, ESLint, TypeScript and the production build clean;
backend unchanged at **1,733 passed, 0 skipped** against live MySQL 8 (this milestone touches no
backend file).

## SCAN-03 — the export was already built, and now it is reachable from the screen (2026-09-17)

Scope §13's last applicable item, delivered by **not** building it. Backend 1,732 → **1,733**,
frontend 967 → **969**; no migration, contract unchanged at 247 paths.

SCAN-02 made reachability a segment rule. The contacts export addresses people **by segment rule**,
not by id. So `POST /contacts/export` with a `scan`/`reachability` rule already produced exactly the
right file — and this was checked rather than assumed: the test runs the export to completion and
reads the artifact, which contains the refused customer and neither the reachable one nor the one
nobody has tried.

Building a `scan_reachability` entity beside it would have duplicated the artifact writer, the
storage key, the signed link, the expiry and the Download Center registration, to produce the same
CSV. The export service says why in its own words — *"A report **is** an export: same `exports`
row, same queue, same worker discipline, same signed-download flow… so no second export pipeline
exists."* That reasoning applies here unchanged.

**What was genuinely missing was the way in.** An operator looking at the reachability list had to
leave it, build a segment, and start an export from a third screen to get the file for the list
already in front of them. There is now an **Export this list** button on the panel, which sends the
verdict currently selected. It stays disabled until one is chosen, because "everything" is what the
Contacts page already exports and this button means *this* list.

### WhatsApp Scan is now complete under the owner's chosen method

| Item | State |
|---|---|
| Active-status, Invalid-number, Scan analytics | done (SCAN-01) |
| Create segment | done (SCAN-02) |
| **Export** | **done here** |
| Upload list, Batch management, Duplicate detection, Scan queue, Retry failed scans | not applicable — machinery for *running* scans, and this method runs none |
| Business-account result | out of reach — Meta's Cloud API does not expose it, and the only route is the provider the owner declined |

Ten of eleven items are settled and the eleventh is settled *as impossible by decision*, which is a
different and more honest statement than the "ten of eleven covered" this ledger carried before
SCAN-02 corrected it.

WhatsApp Scan 75% → **90%**. The remaining ten points are the authenticated representative-data
visual review every module owes, not a feature. Canonical average 81.9% → **82.4%**.

PASS: backend **1,733 passed, 0 skipped** against live MySQL 8 (520.3s); frontend **969 passed
across 57 files**; OpenAPI unchanged at 247 paths; Ruff, strict mypy (331 files), ESLint,
TypeScript and the production build clean.

## SCAN-02 — the owner chose the compliant method, so reachability became actionable (2026-09-17)

**Owner decision, recorded:** asked whether WhatsApp Scan should stay on delivery evidence or add a
paid third-party provider for direct number lookups, the owner chose **delivery evidence** — the
free, compliant method that sends nothing and calls nobody. That closes one of the four open
questions, and it changes what "finished" means for this module.

Under that decision the remaining work was not a provider. It was that an operator could *read* the
reachability list and not *act* on it. Backend 1,727 → **1,732**, frontend 964 → **967**; one
migration, `0065_segment_scan_source`; contract unchanged at 247 paths.

**A segment can now ask what WhatsApp said.** `field_source: "scan"`, `field_key: "reachability"`,
matched against `reachable` / `unreachable` / `unknown`. The money case is the first one: every
campaign send costs, so a roster that keeps including numbers Meta has already refused pays for the
same refusal every month. `unknown` is the mirror of it — a contact nobody has ever tried is a
campaign waiting to happen, which calls for the opposite action to "not reachable", and the
grammar keeps the two apart rather than folding them into one "not reachable".

**One predicate, two screens.** The rule compiles through `verdict_condition`, which is the Scan
screen's own clause. A second implementation would drift, and that drift presents in the worst
possible way: a campaign quietly targeting a different population from the list the operator read
before building it. A test asserts the screen and the segment return the same people.

A misspelled verdict is a `422` naming it, not an empty segment. An empty segment reads as "nobody
qualifies", which is a different claim from "you typed it wrong" — the same reasoning FIX-01
applied to the webhook status filters.

### Corrected: "ten of the eleven section 13 items" was overstated

The previous entry claimed SCAN-01 covered ten of scope §13's eleven items. Counted honestly
against the owner's chosen method:

| Item | State |
|---|---|
| Active-status result | done (SCAN-01) |
| Invalid-number result | done (SCAN-01, error 131026) |
| Scan analytics | done (SCAN-01 counts) |
| **Create segment** | **done here** |
| Upload number list, Batch management, Duplicate detection, Scan queue, Retry failed scans | **not applicable** — all five are machinery for *running* scans, and this method runs none; the evidence already exists |
| Export | **outstanding**, and doable |
| Business-account result | **out of reach** — Meta's Cloud API does not expose it, and the only way to get it is the provider the owner declined |

So: four done, five that the chosen method makes moot, one genuinely left, one that the decision
puts permanently out of scope. "Ten of eleven" counted the five not-applicable items as covered,
which flatters the number by treating "we never need to" as "we did".

WhatsApp Scan 55% → 75%. Segments 75% → 78%. Canonical average 81.1% → **81.9%** (2538/31 = 81.87).

PASS: backend **1,732 passed, 0 skipped** against live MySQL 8 (529.7s); frontend **967 passed
across 57 files**; migration applied, downgraded and re-applied against live MySQL 8; OpenAPI
unchanged at 247 paths (a segment rule's `field_source` is a free string on the wire); Ruff, strict
mypy (331 files), ESLint, TypeScript and the production build clean. The five backend tests were
run against the code they describe first, to see them fail.

## VAL-05 — the journey nothing tested, and a sweep for the last milestone's bug class (2026-09-17)

Two pieces of verification, no product change. Backend 1,726 → **1,727**.

### The test that would have caught all four campaign bugs

Every fix this session had its own test, and each one passed while the campaign as a whole was
still broken — because nothing exercised the pieces *together*. A real Vi reactivation offer is not
"a template with a button" or "a template with an image". It is one message carrying an offer
picture, the customer's name, and a link only they can use, and until today it could not be sent at
all.

`test_campaign_journey.py` drives exactly that, once: preview the template with sample values,
upload the offer image, map two body variables and the button link to contact fields, dispatch,
assert all three components reach Meta in a single message with the right parameters, then have the
customer write back and read the reply off the campaign.

Its claim was checked rather than asserted. Restoring this morning's `campaign_service`,
`campaign_dispatch_service`, `message_service` and `campaign` schema, the test fails at
`recipient.status == RECIPIENT_SENT` — the campaign is **accepted**, then every recipient dies,
which is the exact pattern the four fixes were about.

### The sweep: was `replied_count` the only one?

CAM-REPLY-01 found a column that was declared, returned by the API and printed on screen, and that
nothing ever wrote. That find was luck. So every mapped column in the schema was checked for a
writer outside the model layer, and each candidate read by hand.

**No second instance.** The codebase is disciplined about this, and the contrast is the useful
part:

- `actual_cost` is never written, **and says so**: *"``actual_cost`` must be the
  provider-authoritative charge, and pricing it from our own card would produce a second estimate
  wearing the word 'actual'."* `pricing_model`, `is_billable` and `messages.cost_*` are refused on
  the same grounds, and `prev_hash` is marked a later hardening.
- The analytics rollup counters and `value_string` **are** written, through a string-keyed
  increments dict and a type map that a naive search cannot see.
- `campaigns.send_rate_mps` is genuinely unused, but it is in no schema and on no screen, so it
  claims nothing. Dead schema, not a false statement.

Which is exactly what separated `replied_count`: it was not an unwritten field, it was an unwritten
field **being displayed as a measurement**. `actual_cost` is a gap somebody documented; "Replies: 0
(0% of delivered)" was an answer.

No module percentage moves.

PASS: backend **1,727 passed, 0 skipped** against live MySQL 8; frontend **964 passed across 57
files**; OpenAPI unchanged at 247 paths; Ruff, strict mypy (331 files), ESLint, TypeScript and the
production build clean.

## CAM-REPLY-01 — the number every campaign screen printed and nothing measured (2026-09-17)

`campaigns.replied_count` has been on the model, in the API response and printed on every campaign
screen as **"Replies: N (X% of delivered)"** since the schema was written. Nothing ever wrote it.
Every campaign has reported **zero replies for its whole life** — a confident, specific number,
never measured, on the one metric a *reactivation* campaign exists to produce. Backend 1,723 →
**1,726**; one migration, `0064_recipient_replied_at`; contract unchanged at 247 paths.

Worse than a blank. A blank invites a question; "0 (0% of delivered)" answers one. An operator
comparing two templates by reply rate saw 0% for both and could only conclude that neither worked.

**Nothing could have recomputed it, either.** `refresh_progress` derives every other counter from
the roster — deliberately, because "an increment that replays or races produces a counter nobody
can reconcile" — and the roster had no reply to derive from. So the fact is recorded where the rest
of a recipient's history already lives, and the counter joins its siblings in being derived.

**The attribution rule invents nothing.** A reply is counted against the campaign whose message
that contact most recently *received* — not one they were merely rostered into — because the send
already stamped `sent_at` on exactly that row. And only the first reply counts: a customer sending
five messages is one customer who replied, and a counter that moved on each would be measuring
their typing rather than the campaign's reach.

**Recorded on the way in, not counted on the way out.** The alternative is a self-join across the
message ledger on every progress refresh, and that refresh runs after every send — at 200,000
recipients that is the same mistake PERF-01 and PERF-02 were about. One indexed lookup per
*inbound* message is the cheaper side by a wide margin: inbound volume is a fraction of outbound,
and `ix_crecip_contact` already exists from PERF-02.

**A counter must never cost an inbound message.** The hook is wrapped: a reply is in the ledger
whatever happens, and losing a customer's message because a statistic could not be updated would
be exactly the wrong way round. A failure logs and the message lands.

The column is nullable and unindexed on purpose. Counting is always scoped to one campaign, which
`uq_crecip_campaign_contact` already leads with, so a second index would be paid for on every
insert into a 200,000-row ledger to serve a query that is already selective. The table is
range-partitioned, so a *unique* key would have had to include `created_at` — nothing here needs
one.

Migration applied, downgraded and re-applied against the live MySQL 8 carrying 200,000 recipient
rows; the rows survived the round trip. `tests/test_migrations.py` pins the head revision and was
updated with it — the same tripwire that caught PERF-02.

Campaigns 97% → 98%, Analytics 82% → 83%. The canonical 31-module average moves 81.0% → **81.1%**.

PASS: backend **1,726 passed, 0 skipped** against live MySQL 8 (557.1s); frontend **964 passed
across 57 files** (no frontend change — the number it already printed is simply true now); OpenAPI
unchanged at 247 paths; Ruff, strict mypy (331 files), ESLint, TypeScript and the production build
clean. All three new tests were run against the code they describe first; two failed, and the third
— "a stranger's message counts nothing" — passed before the fix, which is correct, because nothing
counted anything.

## CAM-DRIFT-01 — the template moved after the campaign was built (2026-09-17)

The same total-campaign failure as the last two milestones, arriving through a third door: not
missing code, but **time**. A campaign mapped against a two-variable template can be dispatched
against a three-variable one, because `_apply_definition` rewrites `components_json`,
`variable_count` and `has_media_header` — and the Meta template sync calls it. The stored map is
then short, and every recipient fails separately for a count mismatch. Backend 1,721 → **1,723**;
no contract change.

The existing code already accepted the premise. Dispatch re-checks the template's *status*, with a
comment saying why: *"Meta may have paused the template since."* Exactly so — and it may have
rewritten it since, which was not checked.

**One refusal instead of one per recipient.** A campaign whose map no longer fits is now refused at
dispatch with a message naming what changed — `body now needs 4, the campaign maps 3` — and the
roster is left untouched at `pending`, so remapping and dispatching again is the whole remedy.
Unchecked, the campaign burned through its roster producing thousands of identical errors and the
operator read the reason after the sending window was spent.

**The comparison has one implementation, used at both moments.** `variable_map_gaps` and
`header_media_gap` live in `template_validation`, and create-time validation now calls the same
function dispatch does. Two copies would eventually disagree, and the way that failure presents is
the worst possible one: a campaign the create path calls complete and the dispatch path calls
short, with the operator told it is fine right up until it is refused.

The media-header check deliberately stops short of comparing the file's *kind* here, because that
needs the asset and therefore a database round trip. Create time compares it, where the file is
actually being chosen.

With this, the four ways a campaign reaches Meta — direct dispatch, scheduled, retried, and the
single-message send — were each traced to confirm they share the fixed path. Scheduling fires
`dispatch_campaign`, retry re-enters `send_recipient`, and only two places in the codebase build a
template spec at all. The seam is closed, not sampled.

No module percentage moves: this is a failure mode closed, not a capability added.

PASS: backend **1,723 passed, 0 skipped** against live MySQL 8 (568.2s); frontend **964 passed
across 57 files**; OpenAPI unchanged at 247 paths; Ruff, strict mypy (331 files), ESLint,
TypeScript and the production build clean. Both new tests were run against the code they describe
first, to see them fail.

## CAM-MEDIA-01 — a campaign could not attach the image its template asks for (2026-09-17)

The same shape as CAM-BTN-01, one field over, found by looking for it deliberately. A template
whose header carries an image — an offer picture over a reactivation message, about as ordinary as
a campaign gets — could not be sent by one. `SendService` has always required `header_media` for
such a template and the campaign path supplied none, so the campaign was accepted, the roster was
built, and **every recipient was rejected** with *"has a media header and needs header_media"*.
Backend 1,718 → **1,721**, frontend 961 → **964**; contract stays at 247 paths, `VariableMap` gains
`header_media`.

Refusing it would have been the cheap fix and the wrong one: an image-header offer is a campaign
the owner should be able to run. So the campaign carries the file.

**It rides the variable map, not a new column.** The map already answers "where does each part of
this message get its content"; a media header is that question for the header. No migration, and
the shape mirrors the send spec it feeds. One asset for the whole campaign rather than one per
contact: it is the offer's picture, not a field of anybody's record, and copying the same id onto
200,000 roster rows would be 200,000 copies of one fact.

**Three ways it can be wrong, all answered at create time.** No file for a media-header template;
a file for a template whose header is text; a video where the template declared an image. Each was
previously a rejection from Meta, per recipient, after the sending window had opened. Each is now a
422 naming the field, because the template already says which kind it is and create time already
knows.

**`kind` is read from the template, not from the asset.** The template is what declares the header
an image, and the campaign was refused unless the file matched; reading it back off the asset would
let a file replaced afterwards quietly change what the template says it is.

The wizard offers only files of the declared kind, and says plainly when the library has none of
them rather than presenting an empty picker.

Two things surfaced while testing and are worth recording. The send is **two** calls to Meta — the
file is uploaded for an id, then the message references it — which the campaign mock did not
answer, and a green test here would have proved only that the mock was agreeable. And the media
upload is multipart, so the assertion reads the JSON message calls only; decoding the upload would
have failed for a reason unrelated to the header.

Campaigns 96% → 97%. The canonical 31-module average stays at **81.0%**.

PASS: backend **1,721 passed, 0 skipped** against live MySQL 8 (562.1s); frontend **964 passed
across 57 files**; regenerated OpenAPI (247 paths) and TypeScript with no drift; Ruff, strict mypy
(331 files), ESLint, TypeScript and the production build clean. The six new tests were run against
the code they describe first, to see them fail.

## CAM-BTN-01 — a campaign could never fill in a button's link (2026-09-17)

A WhatsApp template whose button carries a per-customer link — the ordinary shape of a Vi
reactivation offer, "Recharge now" pointing at `https://vi.co/pay/{{1}}` — could not be sent by a
campaign. Not "sent wrong": Meta counts button parameters and rejects a message that is short one,
so **every recipient failed**, one rejection at a time, after the window the campaign was scheduled
for had opened. Nothing on any screen said it would. Backend 1,716 → **1,718**, frontend 958 →
**961**; contract stays at 247 paths, `VariableMap` gains `buttons`.

Found while checking whether TMPL-02's new preview had anywhere to lead. It did not.

**Six layers, and every one of them dropped it.**

1. `VariableMap` declared `header` and `body` only, so Pydantic **silently discarded** a `buttons`
   mapping. No caller could supply one, and none was told why.
2. `_validate_map` iterated `("header", "body")`, so a campaign on a template that *requires* a
   button value was accepted with none — the one moment a 422 would have cost one operator one
   message.
3. `_variables_for` resolved `("header", "body")`, so nothing was stored on the roster.
4. `campaign_dispatch_service` passed a hardcoded `"buttons": []`.
5. `campaign_service.preview` never passed buttons to `render()`, so the sample renders showed
   `https://vi.co/pay/{{1}}` — the template, not the message.
6. The wizard's `templateShape` counted header and body placeholders only, so no control was ever
   drawn to ask.

Either end of that chain was already complete: `TemplateContent.buttons`, `TemplateButtonValue`
with its index, and the Meta adapter's `sub_type`/`index`/`parameters` emission have been there all
along, and `POST /messages/send` accepts button values today. Only the campaign path between them
was missing, so the feature looked present from both directions and worked from neither.

**The value is paired back to its button, not assumed to line up.** Meta addresses a button
parameter by its index *within the template*, and the roster stores values in mapping order, so
`_button_values` walks the template's buttons and pairs them. A template whose second button is a
fixed phone number and whose third carries the link would otherwise send the link as parameter two
and reach nobody.

**The send path now checks the count, and only the direction that is proven.** Too few button
values is a rejection from Meta — that is the failure this milestone is about, and it is now a 422
at accept. Too many is a different question: a quick reply takes a tap payload with no placeholder
to count, and this repository's own send tests have always supplied a value for a fixed URL button.
Whether Meta accepts that is not something this container can ask it, so the check is a minimum
rather than an equality. Tightening it on a guess would break sends that work today. **Worth an
owner's decision if the answer is ever known.**

Templates 91% → 92%, Campaigns 95% → 96%. The canonical 31-module average stays at **81.0%**: two points spread over thirty-one modules does not move it, and rounding it up would be the kind of small overstatement these ledgers exist to prevent.

PASS: backend **1,718 passed, 0 skipped** against live MySQL 8 (549.3s); frontend **961 passed
across 57 files**; regenerated OpenAPI (247 paths) and TypeScript with no drift; Ruff, strict mypy
(331 files), ESLint, TypeScript and the production build clean. The five new tests were run against
the code they describe first, to see them fail; the dispatch one asserts on the Graph payload
rather than the recipient row, because the mock accepts anything and only the wire tells the truth.

## TMPL-02 — a preview that shows what the customer will actually get (2026-09-17)

The template preview rendered every variable as `{{1}}` and never showed a button's destination, so
the one question it exists to answer — *what will Priya receive?* — could not be asked on any
screen. Backend 1,712 → 1,716 tests, frontend 951 → 958. Contract stays at 247 paths;
`/templates/{id}/preview` gains three declared parameters and two response fields.

**The sample-value feature existed and nothing could reach it.** The endpoint read `?body=Priya`
off the raw request, which works but puts nothing in the published contract — and Doc 14 §2 says
the frontend's API types come from that contract and are never hand-written. So the generated
client had no way to send a value, the screen sent none, and every preview since the feature
shipped showed the template rather than a message. The template list already showed that. The
parameters are now declared, which is what makes them usable.

**A link button's destination appeared on no screen at all.** A URL button carries its variable
*inside the link* — `https://vi.co/pay/{{1}}` — and the send path has always supported that
(`TemplateButtonValue`, index and all). The preview rendered header, body and footer and stopped.
The detail page's Buttons table showed the raw URL with the placeholder still in it, which is the
template, not the message. So a variable mapped to the wrong column produced a broken link that
nothing before the send would reveal, and a campaign sends the same link to everybody at once.
`render()` now renders buttons too, and the bubble prints each destination under its label.

WhatsApp itself does not print the link under the button. That is the right call for WhatsApp and
the wrong one here: a label is readable from the template list, a link is readable nowhere, and
looking more like the real thing would hide the only thing this screen is for.

**A fixed button between two variable ones does not shift the values.** Values are consumed only by
buttons whose destination actually carries a placeholder, so the operator's second value belongs to
the second *link*, not to the second button. A phone button sitting between them takes nothing. A
test pins it, because the off-by-one version would look right on every template with one button.

**Blank boxes are not sent.** An empty value would substitute an empty string and render a
plausible URL pointing somewhere wrong. Left out, the placeholder stays visible — "a preview must
not invent a value", which was already the renderer's rule and is now also the screen's.

**How many boxes to draw comes from the server.** The response carries `expects`: header, body and
button variable counts. Counting `{{n}}` in the browser would be a second implementation of Meta's
per-component numbering rules, and the copy that drifted would be the one never compared against a
send. `expected_button_variables` is a new function rather than a wider `expected_variables`,
because that function's two-tuple is what every send is validated against and it is correct as it
stands.

`TemplateBubble` now takes one button shape and both callers reduce to it — the editor from the
draft being typed, the detail page from the server's render — rather than the component learning
two.

Templates 88% → 91%. The module's remaining gap is the explicit AI placeholder.

PASS: backend **1,716 passed, 0 skipped** against live MySQL 8 (531.1s); frontend **958 passed
across 57 files**; regenerated OpenAPI (247 paths) and TypeScript with no drift; Ruff, strict mypy
(331 files), ESLint, TypeScript and the production build clean. Each of the nine new tests was
run against the code it describes first, to see it fail.

## FIX-01 — reading last night's own diff back, adversarially (2026-09-17)

Nine defects in code shipped earlier the same night, found by re-reading the diff rather than by
running the suite again — the suite passed on every one of them. Backend **1,694 → 1,712
tests**, with each of the eighteen new ones run against the code it describes first, to see it fail,
before it was allowed to pass. No contract paths added; six contract *descriptions* corrected.

**A Google Sheet import could not report that it was not configured.** `GoogleSheetImportService`
built its client one line above the `try` that handles the client's own errors, so
`GoogleSheetsNotConfigured` — the exception carrying "set `GOOGLE_SERVICE_ACCOUNT_JSON`, then share
the sheet with that address" — was raised past its own handler and arrived as a **500**. This is
the first thing every new installation hits, including this one, which is still waiting on a key:
the one path guaranteed to be taken was the one path that answered with a stack trace instead of
the instructions.

**A tab called `Prepaid/Postpaid` asked Google the wrong question.** The URL was built with
`httpx.URL(path=tab).path`, which returns the *decoded* path, so a slash in a tab name survived
into the URL as a path separator and addressed a different Sheets endpoint. Google answered 400 and
the operator was told to check that the tab name matched exactly — which it did. A tab containing
`?` or `#` was worse: `httpx.InvalidURL` is not a `GoogleSheetsError`, so it escaped the module's
error mapping entirely as another 500. Both are now one percent-encoded path segment, with the
cases parameterised in a test. A reply that is not JSON at all — a proxy or captive portal
answering in place of Google — now names the proxy instead of raising a decoder error.

**A refused broker lost a dead-lettered event permanently.** Replay marked the entry `replayed`,
committed, and *then* queued the task, which is the order every other dispatch in this repository
uses and is wrong in this one place. The mark is what makes replay idempotent, so a broker that
refused the task after the commit left the entry reading "replayed" with nothing queued — and the
second press, the one that would have fixed it, returned that same row unchanged. The event was
lost in the one store whose entire purpose is that nothing is lost. Queueing first makes both
failures recoverable: a refused dispatch changes nothing and says so, and a failed commit costs one
redundant pass through a processor that already settles by event id (FR-WA-07).

**`/templates/usage` was dividing every template's success by somebody's unfinished work.** A
campaign materialises its whole roster the moment it is created, while it is still a draft, so a
5,000-person draft puts 5,000 never-attempted `pending` rows in the ledger under that template. All
five thousand were being counted as recipients. A template that delivered to 900 of 900 people read
as **15%**, the draft was invisible on the screen, and the obvious response to 15% is to retire a
template that is working perfectly. The same draft also counted as a campaign and set
`last_used_at` to today, so a template nobody had ever sent could read as "used this morning". The
denominator is now recipients a send was actually attempted for (`RECIPIENT_ATTEMPTED`, named
beside the statuses it groups), campaigns are ones that were actually dispatched, and `last_used_at`
comes from `campaigns.started_at`. The code now matches what its own docstring always claimed:
"delivered as a share of **attempted**".

The fixtures had been quietly describing an impossible campaign — never dispatched, yet with
delivered recipients — so `_campaign` now says whether it was sent, and defaults to yes.

**Two contract descriptions described behaviour the code does not have.** `POST
/webhooks/dead-letter/{id}/replay` told integrators it "refuses" an event past its 90-day
retention; it answers `404`, deliberately, because the entry is invisible by then — a client coded
against the published contract would have been waiting for a 409 that never comes. `GET
/scan/reachability` still said "counts are returned beside the page" after PERF-02 moved them to
their own endpoint; the schema beside that sentence has only `data` and `page`. FastAPI publishes
docstrings as the contract, so these were not stale comments — they were a lie in the machine-
readable artefact the frontend types are generated from.

**A misspelled status filter answered `200` with an empty list.** `/webhooks/events?status=faild`
matched nothing and returned success. On this screen an empty list reads as "no failures", which is
the single conclusion the screen exists to stop an operator reaching by accident. Every other
status filter in this API is constrained; these two were free text. They now answer `422` naming
the accepted values. `spreadsheet_id` is constrained the same way, so a half-pasted URL is a named
field error rather than Google's "no sheet with that id".

**The reachability search did not find what the Contacts search finds.** Same-looking box over the
same people, written without the `strip` and the `lower` `ContactRepository` has always had. A name
pasted with a trailing space — the ordinary result of copying a cell — found the customer on one
screen and an empty list on the other, with nothing on either saying why. The shorter field list
stays: Contacts also matches `email`, this screen shows none and promises none.

### Corrected: the 300ms claim was true at 20,000 rows and is not true at 200,000

VAL-04 timed 72 reads against 20,000 campaign recipients and recorded **nothing over the 300ms
budget**. That measurement stands *at that volume*. PERF-02 then seeded 200,000 recipients and
optimised the unfiltered page, but never re-timed the **verdict-filtered** one. Re-timed now,
warm, at 200,000:

| read | ms |
|---|---|
| `/scan/reachability` (no filter) | **8** |
| `/scan/reachability?q=…` | 32 |
| `/scan/reachability?verdict=reachable` | **300** |
| `/scan/reachability?verdict=unknown` | **347** |
| `/scan/reachability/counts` | 319 |
| `/templates/usage` | 267 |

Three of the six are at or over the 300ms budget. Every other read the sweep touches is under 32ms.

So clicking a verdict tile costs what the tallies cost, and the earlier "0 over budget" line did
not cover it. `EXPLAIN` says why, and says an index cannot help: the filter is on an aggregate, so
MySQL materialises all 221,369 recipient rows into a temporary table before it can apply it. The
one cheap idea — pruning rows that carry no receipt before the `GROUP BY`, which is semantically
free because such a row cannot change any verdict — measured **304.9ms → 298.3ms**, inside the
noise, and was dropped. That is the second time on this screen that an obvious optimisation
measured as nothing, which is the argument for measuring rather than reasoning about it. A real fix
means materialising the verdict per contact: a new table, a refresh path off the delivery receipts,
and a new class of staleness bug. That is a data-model decision, not an overnight one, and it is
the owner's to make.

No module percentage moves. Nine fixes and one correction to a claim; nothing new was built.

PASS: backend **1,712 passed, 0 skipped** against live MySQL 8 (535.9s); frontend **951
passed across 56 files**; live read sweep **210 requests over 73 contract-declared GET
paths, 0 5xx**; regenerated OpenAPI (247 paths, unchanged) and TypeScript with no drift; Ruff,
strict mypy (331 files), ESLint, TypeScript and the production build clean.

## PERF-02 — the reachability page at real volume (2026-09-17)

Measured against a real MySQL 8 seeded to **200,000 campaign recipients** over 20,000 contacts, the
reachability list falls from **799ms to 70ms**. Contract 246 → 247 paths; one migration,
`0063_reachability_contact_index`.

PERF-01 fixed this screen at 20,000 rows. Ten times the data showed the fix was only half of one:
the page had stopped aggregating the whole ledger, but it still had to *find* fifty contacts inside
it, and every index on `campaign_recipients` leads with `campaign_id` because every query before
SCAN-01 started from a campaign. Reachability asks the opposite question — what happened to this
contact, across every campaign — and nothing answered it.

**The index that did nothing now does everything.** The same
`campaign_recipients(contact_id)` index was tried during PERF-01 and dropped because it changed
nothing: at that point the query still aggregated every row, and no index avoids reading rows you
have asked for. After PERF-01 made the read selective it is worth 41.6ms → 9.1ms. The index and the
query shape are worth something together and nothing apart, which is a good argument for measuring
twice rather than assuming a result carries forward.

**The tallies moved to their own endpoint.** `GET /scan/reachability/counts` exists because the two
questions cost differently and only one of them can be made cheap. A page reads fifty contacts.
"How many contacts are in each state" reads every recipient row the organization has, to decide one
contact's verdict — 425ms at this volume, and no index helps. Returned together, the fast answer
waited for the slow one and the screen took four fifths of a second. Split, the list appears at once
and the tiles fill in behind it. Nothing is approximated and both use the same predicates, so they
cannot describe different sets; a test asserts the search reaches both.

**Measured and left alone: `/templates/usage` at 327ms.** It aggregates the same ledger grouped by
template, so it grows the same way. It is reported rather than rewritten because the honest trigger
is volume, not today: the owner's live account runs 22 campaigns of roughly a thousand recipients,
so around 22,000 rows — about 35ms. It becomes a problem somewhere past 100,000. The cheaper source
is the denormalized `campaigns.delivered_count`/`read_count`/`failed_count`, recomputed from the
roster by `refresh_progress` rather than incremented, so it is authoritative. Switching to it is a
change of data source and deserves a test proving the two agree before it ships, not a 3am rewrite.

The suite caught the one thing this milestone could have broken quietly:
`tests/test_migrations.py` pins the expected head revision, so adding `0063` failed two assertions
until they were updated. That tripwire exists for the same reason the OpenAPI path count does — a
migration should not be able to appear without somebody noticing — and it did its job.

PASS: backend **1,694 passed, 0 skipped** (14 in the reachability file, three of them new);
frontend **951 passed across 56 files**; migration applied, downgraded and re-applied against live
MySQL 8; regenerated OpenAPI and TypeScript with no drift; Ruff, strict mypy, ESLint, TypeScript
and the production build clean.

## VAL-04 — the same mistake, looked for everywhere else (2026-09-17)

Every one of the 72 parameterless reads timed against a seeded account of 20,000 contacts and
20,000 campaign recipients. **Nothing is over the 300ms budget.** The slowest is
`/scan/reachability` at 126ms — the one PERF-01 already halved and whose remaining cost is recorded
— then `/templates/usage` at 37ms and the ordinary contact list at 28ms. Everything else is under
20ms.

PERF-01 was a query that cost what the account weighs rather than what the page weighs. That shape
is invisible on an empty database, which is exactly how it shipped, and there was no reason to
believe it was the only one. It was worth finding out rather than assuming.

`scripts/live_api_read_sweep.py` now times each request and records the ten slowest paths in its
evidence, so the check is repeatable rather than a thing done once at 2am. It is not a performance
test — one warm request on one container proves little about a production host under load — and the
script says so where the figures are written. What it does is make an endpoint whose cost grows
with the data sort itself to the top of a file somebody already reads.

No product code changed. No module percentage moves: this is a measurement.

PASS: 72 paths timed, **0 over budget**; sweep **209 requests, 0 returned 5xx**; Ruff and mypy
clean on the amended script.

## PERF-01 — a page should cost what a page costs (2026-09-17)

`GET /scan/reachability` fell from **228ms to 125ms** at 20,000 contacts, and the query behind its
page from **42ms to 15ms**. No behaviour changed: the same twelve tests pass and the tallies still
read 6,667 / 6,667 / 6,666 against a deliberately seeded one-in-three split.

SCAN-01 shipped last night measured only against an account with almost no data, where it looked
instant. It was not. The page joined a whole-ledger aggregate — every campaign recipient the
organization has ever had — to the fifty rows it was about to show, so the cost of rendering one
screen grew with the size of the account rather than the size of the page. On this account that was
already seven times the cost of the ordinary contact list; on the owner's real volume it would have
passed the 300ms budget and kept going.

**The first fix was wrong, and measuring is what caught it.** The obvious cause looked like a
missing index on `campaign_recipients(contact_id)`, since the aggregate groups by it. The index was
added by hand against the live MySQL 8 and re-measured: 42.6ms and 73.5ms, unchanged to within
noise. The scan is inherent — every row must be read to compute a per-contact maximum — and no
index avoids reading. The index was dropped rather than migrated, and an hour of writing a
migration for it was not spent.

The structural fix is to stop asking the question. The page now runs two queries in order: an
indexed read of fifty contacts, then an aggregate restricted to exactly those fifty contact ids.
Filtering by verdict keeps the join, because deciding which contacts qualify needs the evidence
before a page exists — that is a deliberate exception, and it is the path an operator reaches for
second.

**A known limit, stated rather than hidden.** The tallies still cost ~72ms and still scan
everything, because "how many contacts are in each state" is a question about the whole set. At ten
times this volume that is roughly 700ms. Making it cheaper means caching or narrowing what the
screen promises, and both are choices about what the product should say — not something to decide
at 2am without the owner.

Two smaller repairs in the same pass, both found by Bandit on the night's new code:

- An `assert` in the dead-letter replay path (CORE-23) is now an explicit guard. Asserts vanish
  under `python -O`, and dispatching a `None` event id would have queued a task that failed a long
  way from the mistake.
- The contact predicates shared by the page, the verdict filter and the tallies are written once.
  Three copies of "which contacts this screen is about" is how the tallies end up describing a
  different set from the rows.

PASS: backend **1,692 passed, 0 skipped**; Bandit **0 high, 0 medium** with one fewer low; Ruff and
strict mypy clean. Endpoint measured before and after against real MySQL 8 with a seeded 20,000-row
ledger.

## VAL-03 — the performance gate, finally on the database it will run (2026-09-17)

`scripts/performance_canary.py` against the live MySQL-backed API: **p95 4.8ms across 40 reads**,
budget 300ms. The read sweep alongside it: **209 requests across 72 contract-declared GET paths,
zero 5xx**.

The canary has existed since REL-CERT-01 but every recorded run was against a disposable Docker
stack, which no longer starts in this environment. Running it against the MySQL server VAL-01 stood
up puts a number on the one thing an operator notices before any feature: whether the product feels
instant. It does, by a factor of sixty, on an account with a working data set rather than an empty
one.

Both evidence files are committed under `output/evidence/`, beside the existing preview and report
artifacts.

This is a measurement, not a feature: no module percentage moves. The figure is honest about its
own limits — a single-node container with a warm cache and a modest row count is not a production
host, and it says nothing about concurrency. What it does rule out is the failure that would have
been embarrassing to find later: a query that is merely *correct* on MySQL while being unusably
slow on it.

PASS: canary p95 **4.8ms** / 300ms budget; read sweep **209/209** answered with no 5xx; backend
**1,692 passed, 0 skipped**; frontend **949 passed across 56 files**.

## CORE-23 — deciding what happens to a parked webhook (2026-09-17)

`POST /api/v1/webhooks/dead-letter/{id}/replay` and `.../discard` complete Doc 04 §23 for the
dead-letter queue. Contract 244 → 246 paths. No migration, no new permission — both take
`webhooks:manage`, as §23 specifies.

CORE-22 made the queue visible. Visible is not enough: the queue exists so that a human decides,
and a screen that shows an operator the error without a way to act on it leaves them exactly where
they started. Replay puts the event back through `process_webhook_event`; discard closes it
without processing. Both are audited.

**Replay is idempotent, as §23 requires.** Replaying an entry already marked replayed returns it
unchanged rather than queueing a second pass. An operator who clicks twice, or a request the
browser retried, must not double-apply an event whose entire purpose was to apply once. The two
terminal states refuse each other in both directions: a discarded entry cannot be replayed, and a
replayed one cannot be discarded — the event was applied, and recording it as discarded afterwards
would leave the queue claiming nothing happened when something did.

**A finding in this milestone's own first draft.** §23.1 keeps `webhook_events` 90 days against the
dead letter's 180 and says "only events still within retention are replayable", so the service was
written with an explicit retention check returning 409. The test for it failed with 404 — and the
404 was right. Ownership is read through the source event, so once that row ages out the entry
belongs to no organization: it leaves the listing and is unreachable by id. The retention branch
could never execute. It was removed rather than left as code that documents a case it never sees,
and a 409 would in any event have had to describe a row the operator was never shown. The test now
asserts the real behaviour and that the listing agrees with it.

The two client hooks are written out separately instead of sharing a path template. The generated
client types each path, and the one thing worth keeping is that these calls are checked against the
contract; a shared helper would have had to cast that away. Both buttons lock while either is in
flight — replay is idempotent on the server, but a second click that appears to work and does
nothing teaches an operator to distrust the button.

PASS: backend **1,692 passed, 0 skipped** with 9 new tests, covering the queued replay, the
idempotent second replay, both terminal-state refusals, an aged-out source, cross-tenant refusal
and the permission gate. Frontend **949 passed across 56 files** (was 946) with 3 new tests.
Regenerated OpenAPI and TypeScript with no drift; Ruff, strict mypy, ESLint, TypeScript and the
production build clean.

## TMPL-01 — how each template has actually performed (2026-09-17)

`GET /api/v1/templates/usage` reports, per template, how many campaigns used it, how many people it
reached, how many arrived, how many failed, and when it was last sent. Contract 243 → 244 paths.
No migration, no new permission.

Templates are chosen by name today, which means they are chosen by memory. Every one of these
numbers was already in `campaigns` and `campaign_recipients`; nothing read them per template, so
the question "which of these actually works" had no answer anywhere in the product.

**Correction to the ledger.** Templates' pending list named "category server sync" as a gap. It is
not: `POST /templates/sync` exists, `useSyncTemplates` is wired to a permission-gated *Sync from
Meta* button on the list, and the approval-status filter is there too. That is the third time this
audit has found the trackers behind the code (after CORE-09 and the GROW-03 segment predicates).
The row now describes what is actually missing.

Two decisions:

- **A template nobody has sent is listed, with no rate rather than zero.** Zero reads as
  "everything failed" when the truth is that nothing was tried, and those call for opposite actions
  — fix it, or try it. The API returns `null` and the column says "Never sent". Dropping unused
  templates entirely would have hidden the ones most worth noticing: an unused template is either
  new or quietly broken.
- **Aggregates only.** "Which template works" is a template question; answering it names no
  customer and no campaign, so the endpoint sits behind `templates:read` alone rather than also
  requiring campaign access. SCAN-01 needed both because its rows were per contact; these are not.

The history loads beside the list rather than inside it, so a slower aggregate never holds up the
screen an operator opens to write a template. While it loads the columns show a dash, not a zero.

Ordering puts the most recently used first and never-used last, with an explicit `CASE` rather than
a dialect's default null ordering — MySQL and SQLite disagree about that, and the list would have
been sorted differently in production than in the tests.

PASS: backend **1,683 passed, 0 skipped** with 8 new tests, including one that exists only to keep
`/templates/usage` declared before `/templates/{template_id}` — the other way round, "usage" parses
as an identifier and the screen 404s. Frontend **946 passed across 56 files** (was 943/55) with 3
new tests. Regenerated OpenAPI and TypeScript with no drift; Ruff, strict mypy, ESLint, TypeScript
and the production build clean.

## SCAN-01 — WhatsApp reachability, from evidence we already hold (2026-09-17)

`GET /api/v1/scan/reachability` reports, for every contact, whether WhatsApp has reached that
number, refused it, or never been asked. Contract 242 → 243 paths. No migration, no new permission,
nothing sent, no provider called.

Scope §13 asks for a WhatsApp Scan module and, in the same breath, excludes the only technique that
answers it directly: *"Only compliant and authorised methods are allowed. Unofficial WhatsApp Web
bulk enumeration is excluded."* Meta's Cloud API has no lookup either — the on-premise `/contacts`
check did not survive the move — so a direct scan of numbers nobody has messaged remains genuinely
blocked on an approved provider, and the workspace now says exactly that instead of implying the
whole module is unavailable.

What is **not** blocked is the question underneath it. Every campaign already produces delivery
receipts, and they are unusually good evidence: a delivery is proof the number is reachable, and
error `131026` — "undeliverable / not a WhatsApp user", already classified in
`app/channels/meta/errors.py` — is Meta stating the opposite in its own words. Neither is inferred
and neither costs an extra send. That covers ten of the eleven items §13 lists; only
"business-account result" needs something this evidence cannot supply.

Three decisions carry the feature:

- **Only `131026` counts.** A paused template, a closed 24-hour window, a throttle — these are facts
  about our configuration, not about the customer's number. Counting them would mark reachable
  people unreachable on the strength of our own mistakes, and they would then be excluded from the
  very campaigns meant to win them back. A test asserts four such codes all leave the verdict
  `unknown`.
- **The more recent fact wins.** "Ever delivered" would call a disconnected number reachable
  forever; "ever refused" would condemn one that has since come back. Both timestamps are stored,
  returned and shown, so the verdict is derived from recency and an operator surprised by a row can
  see the March delivery and the September refusal that produced it.
- **`unknown` is an answer.** A contact no campaign has included has not been tested, and folding
  those into either side would invent a result. "We have never asked" and "we know they are not
  there" call for opposite next actions — a campaign, or a cleanup.

`campaign_recipients` carries no `organization_id`; it is monthly-partitioned with no foreign keys,
so ownership is read through the campaign each row belongs to, the way CORE-22 reads a webhook's
owner through the route it arrived on. A test proves another tenant's send cannot decide our
verdict. Reads require `contacts:read` **and** `campaigns:read` together: the rows are contacts, but
every verdict is a campaign outcome, and a reader barred from campaign results should not receive a
summary of them one customer at a time.

The verdict's SQL form sits beside its Python form in the same class, because the filter and the
badge have to agree — computing one in each place is how a list ends up disagreeing with its own
rows. Counts come from the same predicates in a single scan.

PASS: backend **1,675 passed, 0 skipped**, including 12 new tests. Frontend **943 passed across 55
files** (was 934/54) with 9 new tests. Regenerated OpenAPI and TypeScript with no drift; Ruff,
strict mypy, ESLint, TypeScript and the production build clean.

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
