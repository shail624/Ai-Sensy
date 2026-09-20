# Project State

## UI-REF-09 — Campaign list controls (2026-09-20)

Current milestone branch `codex/ui-ref-09-campaigns-parity`, based on approved main `06770cc`.
The Campaign list now provides supported reference-style category shortcuts and actions while
reusing real status, refresh and Download Center authorities. PASS: 1,017 frontend tests,
TypeScript, ESLint and production build. Campaigns remains 98% and overall completion remains
approximately 88.0%; this is interaction/discovery parity, not additional domain capability.

## UI-REF-08 — Contacts actions and export discovery (2026-09-20)

Current milestone branch `codex/ui-ref-08-contacts-parity`, based on approved main `97ac07b`.
Authenticated reference comparison added the missing Contacts Actions entry while reusing real
filtered export and Download Center behavior. PASS: 1,016 frontend tests, TypeScript, ESLint and
production build. Contacts remains 98% and overall completion remains approximately 88.0%; this
closes an interaction/discovery difference rather than adding domain scope.

## UI-REF-07 — daily navigation parity (2026-09-20)

Current milestone branch `codex/ui-ref-07-navigation-parity`, based on approved main `ff4a88d`.
The daily rail now exposes real Segments and Developer destinations observed in the authenticated
reference, while preserving RBAC, Vi extensions and excluded-surface rules. PASS: 1,013 frontend
tests, TypeScript, ESLint and production build. Overall completion remains approximately 88.0%;
this is navigation refinement, not new domain capability.

## GSHEET-02 — Google Sheets contact export (2026-09-20)

Current milestone branch `codex/gsheet-02-contact-export`, based on main `32fb4b2`. A filtered
contact export can now create a fresh dated tab in an operator-supplied Google Sheet through the
existing queue and progress contract. Migration head 0069; OpenAPI remains 247. PASS: 1,761
applicable backend and 1,013 frontend tests plus static/build gates. Google Sheets advances from
55% to 70%; canonical average advances from 87.5% to approximately 88.0%. Live provider and host
commissioning remain pending.

## UI-REF-06 — Live Chat controls and empty states (2026-09-20)

Latest local milestone branch: `codex/ui-ref-06`, based on GitHub `main` at `7639380`. The five
UI-REF-05 empty-screen differences are implemented with original UI: icon-only filtering, filled
search action, desktop list collapse, governed empty-state artwork and a token-driven conversation
ground. PASS: 1,012 frontend tests, lint, TypeScript and production build. No backend/API/migration
change and no completion-percentage increase. Authenticated populated preview and host acceptance
remain pending.

## UI-REF-05 — Live Chat tab strip, against the real capture (2026-09-19)

The owner supplied the capture archive directly: **130 unique states, 203 screenshots**. The two
archives extract to the Git-ignored `.reference/aisensy/` and nothing from them is staged, bundled
or imported — verified with `git status` after extraction. The `.json` files beside each image are a
manifest (label, source URL, capture time, and Windows paths to the originals); the MHTML and
rendered HTML those paths name are **not in the archives**, so the reference material here is
screenshots only. There is no reference markup on this machine to copy from even by accident.

`0001_live_chat_active_full.png` was compared against the running Live Chat screen, signed in
against the built bundle.

### Most of the screen already matched

Three columns, the three tab names in the same order, the dark strip they sit on, `Chat Profile`
anchored right, and the `Search name or mobile number` placeholder — all already in place from
UI-REF-02 and UI-REF-04. The differences are small and local, which is worth recording plainly: the
gap between this product and the reference on this screen was never structural.

### What changed

The count moved inside the tab label. The reference reads `ACTIVE (0)`; this read `ACTIVE` followed
by a separate pill. It now reads `ACTIVE (0)`.

The accessible name is deliberately untouched — `12 in Active` before and after. A pill and a
parenthesis are the same announcement to a screen reader, and `inbox-counts.test.tsx` asserts on
that name rather than on the decoration, so its three count assertions and its "omitted while the
read is in flight" case all still hold **without being edited**. A parity change that had required
rewriting those tests would have been the wrong change.

### Still different on this screen

| Reference | Here | Note |
|---|---|---|
| Filter is an icon alone | A `Filters` button with a text label | Straightforward |
| A `◀` control collapses the list column | Absent | Straightforward |
| Search carries a filled circular button | Leading icon only | Straightforward |
| Empty list shows an illustration | Text only | Needs an original illustration |
| Conversation pane carries a patterned ground | Plain | Needs an original pattern |

The last two are reference *assets*. They are not copied. Matching them means an original
illustration and an original pattern in the same position — the arrangement is the owner's
direction, the artwork cannot be.

### Scope

33 of the 130 captured states belong to Ads Manager, WA Payments, Integrations and Developer, which
`REPOSITORY_RULES.md` excludes and the UI-REF-01 direction confirms are not reinstated by navigation
parity. 97 states remain in scope.

## DEPLOY-03 — the first deploy, executed on a real machine (2026-09-18)

DEPLOY-01 and DEPLOY-02 were repaired here and proven by rendering the manifest, because this
environment has no registry access and cannot build an image. Both closed with `PENDING – Host
Machine Validation`. The owner ran the repaired procedure on their own Windows machine, and the
whole chain completed.

| Step | Result |
|---|---|
| §3 build | `wa-platform/backend:v1` and `wa-platform/frontend:v1` built, 28.8s |
| §4 migrate | `0001_identity_and_audit` → `0068_attribute_required_and_active` against containerised MySQL 8; `migrate-1 exited with code 0` |
| §5 owner | `Owner created: <redacted>` |
| §6 start | Ten services up; `api` and `frontend` report **Healthy** |
| §7 readiness | `/ready` returned **200 on the first poll** |

Host: Docker 29.7.2, Compose v5.3.1, Windows PowerShell 5.1.

**Both defects are now disproven in the field, not only on paper.**

DEPLOY-02: the generated `.env.production` contains **no `WAHA_*` variable at all**. Before the
guards were relocated, `${WAHA_API_KEY:?}` inside the profiled service would have aborted `build`
with `required variable WAHA_API_KEY is missing a value` — this exact configuration was the failure.
It built without comment.

DEPLOY-01: the bootstrap one-shot logged
`no such role; executing as a command: python -m app.cli create-owner`, then `Owner created`. That
line is the backend entrypoint's fall-through branch doing precisely what its comment claims, with
the owner variables reaching the container because the `bootstrap` service declares them. The
command the guide used to document exits 2 here.

### What this does not yet cover

Signing in through the SPA, the §8 smoke checks (CSV import, inbound webhook, reply, export,
formula-injection neutralisation, executive gating), TLS, the browser matrix, and OPS-02's worker
fleet showing in `GET /api/v1/queues` on this host. Those stay `PENDING – Host Machine Validation`.
`META_APP_SECRET` is a generated placeholder on this deployment, so Meta webhook verification fails
closed by design and WhatsApp sending is inert until the real secret is set.

## OPS-02 — the fleet view reported an empty fleet, always (2026-09-18)

The registry Compose could not be used to test was tested a different way: without container images,
but with the real application. A genuinely empty MySQL schema, `alembic upgrade head`, `app.cli
create-owner`, uvicorn in `ENVIRONMENT=production`, a Celery worker, and a signed-in owner — §4
through §8 of the deployment guide, run natively.

It worked. Then `GET /api/v1/queues` said there were **no workers**, with a worker running and
`ready`.

`app/queue/heartbeat.py` has always held a complete worker registry: a TTL'd Redis key per worker, a
reader, a schema, a `worker_heartbeat_ttl_seconds` setting, and `_worker_count()` in
`queue/health.py` to fold it into each queue's row. Nothing ever wrote to it. `beat()` had no
callers anywhere in `app/`, and the codebase contained **no Celery signal handlers at all** — no
`worker_ready`, no `worker_shutdown`, nothing. Redis confirmed it: zero `worker:heartbeat:*` keys
while a worker was live.

So the endpoint reported zero workers in every deployment that has ever run, whether the fleet was
healthy or entirely dead. `DEPLOYMENT.md` §12 calls that endpoint **"the primary saturation
signal"**, lists "queue depth and worker fleet ... backlog and dead workers" as what to watch, and
§14 tells an operator debugging "sends accepted then never delivered" to check it. A signal that
reads identically in both states carries no information; worse, it reads as the alarming state, so
the correct reaction to it was to learn to ignore it.

`test_heartbeat_registers_with_ttl_and_lists_workers` passed throughout — it calls `beat()` itself.
This is the same shape as the campaign-dispatch crash: the unit test exercises the function, and
nothing in production invokes it.

### The fix

The writer was the only missing piece, so only the writer was added. `app/queue/worker_heartbeat.py`
connects `worker_ready` and `worker_shutdown`, and refreshes on a daemon thread at a third of the
TTL. `celery_app` imports it, which is what registers the handlers.

It uses its own **synchronous** Redis client, and that is not an optimisation. `app.core.redis`
caches its async client in a module-level global keyed only by the *running loop*, so a second
thread calling `get_redis_client()` swaps out the client a running task is using — and the send
path's rate gate reaches for that client on every message. Reusing `run_async` here would have
traded a dead monitoring signal for intermittent send failures. `beat()` and `beat_sync()` share one
`_payload()`, so the two writers cannot drift.

The pool is derived from the queue registry rather than declared a second time, and an unrecognised
queue reports `unknown` rather than being filed under a real pool.

### Verified against a running fleet, not a fixture

| | |
|---|---|
| Worker starts | `workers: 1`, pool `send-bulk`, queues `sends.bulk, sends.retry` |
| 20s later | `last_seen_at` advanced — the refresh loop is alive |
| Clean `SIGTERM` | key deleted immediately; `workers: 0` |
| `SIGKILL` (a crash) | key survives, TTL 46s remaining — then reaped; `workers: 0` |
| Queues with no worker | 17 of 19 report `0` — the coverage gap an operator needs to see |

Six tests. The wiring test runs in a **subprocess** that imports only `celery_app`: asserting on
signal state in-process proves nothing, because the test module's own import of `worker_heartbeat`
connects the handlers by itself. That blind spot is exactly what let the defect through, and the
first draft of the test had it. With the import removed from `celery_app`, the subprocess fails with
`celery app does not import it`.

## DEPLOY-02 — an optional provider blocked every deployment that never used it (2026-09-18)

With a Docker daemon available, DEPLOY-01's remaining `PENDING` was attempted for real: §2, then
§3. §3 never reached a build step.

```
error while interpolating services.waha.environment.WAHA_API_KEY:
required variable WAHA_API_KEY is missing a value
```

The QR provider is **opt-in and off by default** — ADR-0021 Class B, `--profile waha`, and §15 opens
by saying a deployment that has not adopted it "runs exactly the stack it ran before". It did not.
`WAHA_API_KEY` and `WAHA_WEBHOOK_HMAC_SECRET` were written as `${VAR:?}` **inside the profiled
service**, and profiles do not gate interpolation. Both markers therefore aborted `build`, `up`,
`ps` and `down` for every deployment, adopted or not. `.env.production.example` ships both empty,
and `${VAR:?}` rejects empty as well as unset, so §2 followed verbatim guaranteed the failure.

This is the same defect DEPLOY-01 reasoned about and avoided one commit earlier. It was already in
the manifest at that point, and was not found by reading — the render that checked DEPLOY-01's own
work passed only because the test environment had both WAHA variables set, which is precisely the
condition a real first deploy does not have. Running it found it in seconds.

### The fix

The requirement is not dropped, it is relocated. A `waha-preflight` one-shot, in the `waha` profile,
refuses to start when either credential is unset or empty; `waha` waits on it with
`service_completed_successfully`. It reuses the backend image rather than adding another external
one to a digest-pinned topology, and defers `$$VAR` expansion to the container shell. Fail-closed
behaviour is preserved exactly; what changed is that it now fails closed for the people who enabled
the provider instead of for everyone.

`tests/test_deployment_contract.py` gains a general guard: any `${VAR:?}` reachable only from a
profiled service is a defect. It names both variables against the pre-fix manifest.

### A third defect, caused by the fix for the second

The first full suite run after the WAHA change reported **7 failed**. One was real and was mine:
`test_deployed_stack_environment_satisfies_every_required_compose_variable`.

`release_contract.required_variables()` finds required variables with a regex over the **raw**
manifest text. The comment explaining the WAHA change contained the marker syntax as prose, so the
release contract read a variable literally named `VAR`, which no environment can provide — failing
the deployed-stack gate and seeding a junk entry into `synthetic_environment()`.

That is the same false positive the new profile test hit an hour earlier, in a second place, and it
was latent before either change: any comment in this manifest mentioning the syntax would have done
it. Both ends are fixed — the prose no longer spells the marker, and `required_variables` strips
whole-line comments before scanning, with two tests covering it (a comment is ignored; the real
manifest still yields every declared secret plus `IMAGE_TAG`).

The other six failures were not the change. MySQL and Redis had stopped when the Docker daemon was
started, and the run was scored against a broken environment. They are recorded here because the
same misreading happened once before in this project and was nearly repeated: with both services
restarted and nothing else altered, the suite is **1,764 passed, 0 failed, 0 skipped** in 622s.

`PyYAML` is now declared in the backend `dev` extra. `tests/test_deployment_contract.py` imports it,
and it had been reaching the environment only as a transitive dependency of `bandit`.

The first draft of the new profile test was itself wrong — it scanned the raw file and flagged `${VAR:?}`
written inside a manifest comment. It now scans the parsed services, where comments do not exist.

## DEPLOY-01 — the first command of a first deploy could never have worked (2026-09-18)

`DEPLOYMENT.md` §5 tells an operator to create the first organization and owner like this:

```bash
docker compose ... run --rm api python -m app.cli create-owner
```

It exits **2**, with `owner email is required (--email or OWNER_EMAIL)`. It always has.

`app.cli` reads `OWNER_EMAIL`, `OWNER_FULL_NAME` and `OWNER_PASSWORD` from the environment **inside
the container**. Compose gives a container only the variables named in its own `environment:` block,
and `docker-compose.production.yml` names none of them anywhere — `--env-file` governs interpolation
of the manifest on the host, which is a different thing. Verified by rendering the manifest with all
three set: the `api` service receives 24 variables and not one of them is an owner variable.

So the platform built, migrated, started and passed health checks, and then the first human step
failed — no account, no way to sign in, nothing to do but read the CLI source.

**Why no gate caught it.** `scripts/deployed_stack_gate.py` creates an owner too, and it works,
because it passes `--env OWNER_EMAIL --env OWNER_PASSWORD` explicitly. The gate proved its own
invocation and never exercised the documented one. Automation that takes a different path from the
human it stands in for verifies the path, not the human's.

### The fix

A `bootstrap` one-shot with its own environment block, in its own profile:

```bash
docker compose ... --profile bootstrap run --rm bootstrap
```

It does not share `x-backend-env`, and that is the point. Adding `OWNER_PASSWORD` there would put a
plaintext credential into every api, worker and beat container for the life of the deployment, where
`docker inspect` and `/proc/<pid>/environ` both read it back. Here it exists only in the container
that consumes it, only while the command runs, and only when the profile is named.

The owner variables use `${VAR:-}` rather than `${VAR:?}`. Compose interpolates **every** service in
a manifest regardless of which profiles are active — confirmed with a two-service reproduction — so a
required-variable marker in a profiled service aborts `up -d` for the whole stack. §5 ends by telling
the operator to clear `OWNER_*`; with `:?` that instruction would have taken the platform down the
next time it restarted. The CLI already rejects an empty email or password with a clear message.

### Two more, found on the way

**`API_DOCS_ENABLED` was decoration.** SEC-01 added the setting yesterday and documented it in
`.env.production.example`; no service ever passed it, so an operator who set it changed nothing. It
now rides the shared backend environment.

Its default is `false`, not empty, and the distinction is not cosmetic: the field is `bool | None`,
and pydantic **rejects an empty string**. `${API_DOCS_ENABLED:-}` — the obvious spelling, and the one
used for every optional string beside it — would have raised `ValidationError` at import time in
every backend container and crash-looped the entire stack, in the default case of an operator never
setting it. Caught by trying it before writing it. `false` is also exactly what production already
did implicitly, so nobody's behaviour changes.

**§4 named a migration head 41 revisions behind.** It told operators to expect `alembic upgrade head`
to finish at `0027_analytics`; the head is `0068_attribute_required_and_active`. An operator checking
their upgrade against that line would have concluded a correct migration had failed.

### Evidence

`backend/tests/test_deployment_contract.py` — six tests over the manifest, all hermetic. Four fail
against the pre-fix files (owner variables absent, no profile gate, docs flag unreachable, stale
head). Two pass before and after by construction: they guard the fix itself — that `OWNER_PASSWORD`
stays out of the long-lived services, and that no owner variable is ever marked required. The head
test reads `alembic/versions` rather than a constant, so the guide cannot drift again silently.

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
| Full-scope completion | The 31 canonical rows sum to 2696: simple unweighted average **87.0%**, recalculated median **88%**. This is distinct from the green source-validation gate and is not a 100% AiSensy parity claim. |
| Migration head | `0063_reachability_contact_index` (**64 linear revisions**), added by PERF-02 to index the recipient ledger by contact. Applied, downgraded and re-applied against live MySQL 8. |
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
