# Implementation Tracker (canonical)

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

> Canonical implementation tracker. GitHub at the latest approved HEAD remains the repository source
> of truth. Every new session must read this first.
> Update it after each verified milestone. Keep it short: state, not narrative.

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

> GitHub at the latest approved HEAD is the repository source of truth. Keep repository-verifiable
> engineering evidence separate from host/provider/runtime acceptance.

Latest UI checkpoint: **UI-REF-02**, reference-order Live Chat strip/search and empty desktop
columns. Frontend **883/883**, types/build/lint and desktop/mobile preview pass. Full populated
workflow parity is pending in Design Document 73. No backend/API/migration/delivery change.

_Previous update: 2026-09-13 · UI-REF-01 local UI slice: frontend 882/882,
types/lint/build and bounded desktop/mobile preview pass. Design Document 72 records remaining
screen parity. Separate unfinished GROW-03 segment work advances the migration head to 0062;
OpenAPI remains 235. Cumulative backend/release revalidation is pending. PAR-VIEW-05 is the
prior fully source-validated slice. PAR-AUTO-22 remains the last complete 23/23 Docker-backed release profile.
REL-CERT-01's prior 25/25 disposable-deployment
evidence remains preserved. CORE-11C remains the current bounded administrative product milestone.
QR-09D/G/H/I/J/L evidence remains preserved and QR-09 remains PARTIAL — BLOCKED._

## Current state

- **Branch:** `ui/taste-modernization`
- **Starting HEAD:** `1d109b984b165f166e8575e5fd4fa3648ce903dc` (`feat(channels): establish QR provider foundation`)
- **Release:** `1.0.0-rc1`
- **Repository/local-deployment certification:** `REL-CERT-01 — PASS`. Its pre-PAR-AUTO-19 tree
  passed **25/25** deployed gates in **597.4s**, including a fresh disposable ten-service browser/
  performance/failure exercise. On the prior PAR-AUTO-22 tree, the complete release profile
  passes **23/23 in 685.9s** with **1521 backend tests / zero skips**, **832 frontend tests**, clean
  lint/types/OpenAPI/build/SAST/dependency/source/image scans, exact image contracts and SBOMs, and
  certified WAHA runtime checks. The earlier PAR-VIEW-05 tree passed focused Reports
  saved-view/API/migration/OpenAPI **12/12**, complete backend **1579 passed / 6 MySQL-only skipped /
  0 failed in 413.35s**, **875 frontend tests**, static **6/6**, strict mypy **322 files**,
  synchronized **235-path** OpenAPI and production build. The Docker/security release rerun
  remains pending.
  The preserved deployed canary was **5.764ms p95 / 300ms budget**;
  Redis-down readiness was **503 degraded** with zero synthetic-secret/PII log leaks.
- **Completion boundary:** the prior release gate is preserved, not rerun for the cumulative tree; full approved product
  scope is not 100%. The 31 canonical rows sum to 2,388: the simple unweighted mean is **77.0%**
  and the recalculated median is **88%**. Target-host TLS/secrets/monitoring/restore/UAT and remaining module work are
  still pending; no commit, push, or live deployment was authorized.
- **Migration/OpenAPI:** `0062_segment_domain_predicates` (**63 revisions**, unfinished segment delta) · **235 paths**.
  PAR-VIEW-05 adds governed Reports list/create/delete contracts through the shared view authority; JSON/TypeScript remain
  synchronized.
- **Prior administrative milestone:** `CORE-11C — Inactivity Auto-Resolve — REPOSITORY
  IMPLEMENTED`; CORE-11 remains `PARTIAL`.
- **Prior feature change:** PAR-VIEW-05 persists one report period/custom range, day/week granularity and
  optional comparison as private or team views through the same service/repository/table as KYC,
  Campaigns, Contacts and Reactivation. Every Analytics reader may govern personal views;
  `analytics:views_manage` protects team publishing/deletion. Workspace-aware caps, names, indexes,
  isolation, validation and Audit fail closed. Private/team chips and the responsive management
  sheet reopen URL-backed report filters without storing tab, export, schedule or progress state.
  Focused contracts **12/12**, focused Analytics UI **41/41**, full frontend **47 files / 875
  tests**, static **6/6**, strict mypy **322 files** and production build pass. Authenticated local
  desktop/mobile previews pass for this bounded workflow. Prior PAR-AUTO-22 release evidence remains
  preserved; head is `0061` (**62 revisions**), Executive Reports advances **75% → 80%**, Saved
  Views **85% → 95%** and full scope **76.5% → 77.0%**; median advances **86% → 88%**.
- **Historical UI parity follow-up (shell superseded by UI-REF-01):** the expanded named sidebar exposes Dashboard, Live Chat, Chat
  History, Campaigns, Contacts, Automation and Analytics; `Manage` preserves every entitled
  template/audience/channel/additional/admin route. Live Chat now labels its persisted filters
  `Requested`, `Active` and `Intervened` without inventing chatbot state. `Intervene` performs an
  atomic, audited, retry-safe claim and only that owner can `Resolve`; a second agent cannot steal or
  close the chat through either action route or the legacy status route. Backend intervention
  **24/24**, combined contract regression **26/26**, focused frontend **37/37**, full frontend **40
  files / 816 tests**, lint and production build PASS. The applicable full backend is **1457 passed /
  6 MySQL skipped / 1 known Redis-dependent deselection**.
- **Latest CORE-11 change:** the existing organization policy now drives optional inactivity resolution.
  Only read, inactive open/pending conversations without an open Task qualify; snoozed/unread/recent
  rows are protected, each mutation is row-locked/audited/evented, and genuinely new inbound reopens
  a resolved thread while duplicate/stale delivery does not. Frontend **811 tests**, lint and build
  pass; focused backend **48 tests**, static quality and OpenAPI drift pass. The applicable backend
  suite is **1453 passed / 6 MySQL skipped / 1 Redis-dependent test deselected**; authenticated
  visual/host evidence and later CORE-11 controls remain pending.
- **CORE-11A/11B/11C boundary:** assignment/read/consent, working-hours/welcome/off-hours and
  protected inactivity auto-resolve controls are implemented. Pipeline/SLA, notification/security/
  audit settings, campaign preferences, team presence/
  workload/login/permission audit and required/active attributes are explicitly not claimed.
- **Superseded change:** QR-09J closes QR-09-D12 (Blocker): a real signed external inbound reached both
  certified WAHA event variants but dead-lettered because the adapter returned aware UTC into a
  repository whose MySQL DATETIME/`utcnow()` convention is naive UTC. Normalization now occurs at
  that provider boundary. Both preserved source events were redriven through the normal queue and
  converged to exactly one accepted Inbox message with unread count one; no database rewrite.
  Canonical premerge 14/14 (backend 1437, frontend 806) and applicable release/runtime 8/8 passed.
  Outbound/ACK/persistence/logout, Meta rotation and target-host/browser evidence remain pending.
- **Superseded change:** QR-09I closes QR-09-D11 (Blocker): the local QR representation could expire
  after the physical scan even though the same provider session had reached identity-bearing
  `WORKING`. An explicit pairing request now renews only that representation under the existing
  lease/fence/version controls; polling cannot extend it. A narrow completion path accepts only a
  fresh same-session `WORKING` observation with identity, preserves the pairing revision and emits
  redacted Audit evidence. The actual linked session converged to active/paired/connected with no
  new QR, rescan, restart, logout, message or database backdoor. Canonical premerge 14/14 plus nine
  release/runtime gates passed; backend 1436, frontend 806. Physical phone/ACK/persistence/logout,
  Meta rotation and target-host/browser evidence remain pending.
- **Superseded change:** QR-09H closes QR-09-D10 (Blocker): an unscanned QR lapses to `FAILED` while
  the provider session object survives, so every governed "Get a new QR code" retry hit the
  provider's `already exists` refusal, which the service reported as an outage; with `reconnect`
  refusing and `connect` a no-op, the channel could never issue another QR. Certified behavior was
  measured rather than assumed: `start` alone cannot recover `FAILED`, while `stop` then `start`
  reaches `SCAN_QR_CODE` with the session count at one, `me` still `None` and the stored config
  byte-identical. A new `prepare_pairing()` applies exactly that, leaving `begin_pairing()`
  create-only so QR-03's no-guessing-on-conflict principle is intact; it reuses an already
  QR-eligible session, skips a redundant stop, and refuses both a provider-reported linked account
  and a durably `PAIRED` connection. Error classification is corrected so a reached provider is a
  truthful conflict rather than a false outage, and provider wording never reaches operators. A
  genuinely expired QR recovered through the actual frontend under a single lease, with the
  application QR returning `200 image/png` and no-store/private/no-cache. Release gate 23/23;
  backend 1431, frontend 806 (unchanged — no frontend source touched).
- **Superseded change:** QR-09D closes QR-09-D6 (Major): with a durable application session present
  and the provider reachable but holding none, the screen projected `ready-to-connect` and
  re-offered an idempotent `connect()` that cannot create provider state, leaving
  `POST /session/pair` operationally unreachable. The durable session is now the boundary between
  the two honest actions: a provider-neutral `ready-to-pair` state offers "Begin pairing" wired to
  `POST /session/pair`, while no durable session still yields `ready-to-connect`. QR-09F outage
  truth still outranks it and a previously paired connection still resolves earlier as
  `reauth-required`. Frontend regressions were reconciled by hand against the QR-09F suite rather
  than by applying the conflicting historical patch. Real MySQL/Redis/application/WAHA evidence:
  `ready-to-pair` held across eight live three-second polls, the actual UI action issued exactly
  one `/session/pair` and zero `/session/connect`, two application QR requests returned
  `200 image/png` with no-store/private/no-cache, a genuine outage produced zero new QR requests
  and recovered cleanly, and the QR-09G paused recovery was re-proven through the same UI. Actual
  1920x1080 and 390x844 screenshots show ready-to-pair with no QR and no horizontal overflow.
  Release gate 23/23; backend 1418, frontend 806.
- **Superseded change:** QR-09G repairs QR-09-D9 (Blocker): an ordinary `STOPPED` provider observation
  pauses the durable session, and a `PAUSED` row cannot acquire a runtime lease — so for a
  never-paired connection, status reconciliation stopped permanently, `pair` returned 409,
  `reconnect` returned 409 telling the operator to pair, and `connect` was an idempotent no-op,
  leaving the channel unrecoverable without direct database intervention. `begin_pairing()` now
  reuses the exact pattern `reconnect()` established: the legal, lease-free
  `PAUSED → INITIALIZING` transition first, then the ordinary lease. The `SessionManager` PAUSED
  lease prohibition is unchanged, and recovery is narrow to non-`PAIRED` pairing states so durable
  credentials stay in the reconnect/re-authentication domain. A row that cannot be leased is now
  still read, so missing-session and outage facts are reported truthfully without creating or
  mutating any provider or durable state from a `GET`. Real MySQL/Redis/application/WAHA evidence
  replayed the preserved D9 reproduction: `pair` returned 200, the audit trail shows
  `transitioned → initializing` before `lock_acquired`, one provider session reached
  `SCAN_QR_CODE`, and one durable connection/session remained. Release gate 23/23; backend 1418,
  frontend 798. No frontend source changed, so no UI preview evidence is claimed.
- **Superseded change:** QR-09F repairs QR-09-D8: a genuine WAHA transport outage can no longer inherit
  actionable QR truth from a durable `pairing_available` row or stale `SCAN_QR_CODE` metadata.
  Backend observation is now typed; only a current live provider observation can advertise QR
  availability, while a transport outage projects no provider status/action and leaves durable
  pairing/reauthentication facts untouched. The frontend prioritizes the stable outage reason before
  QR, creating, connecting or reconnect states and therefore does not mount QR retrieval. Real
  MySQL/Redis/application/WAHA evidence held an outage across more than three poll intervals with
  zero QR-handler requests, then recovered the same container, volume, provider session and durable
  application session. Actual local desktop/mobile screenshots show the unavailable state without
  a QR or responsive overflow. Release gate **23/23 PASS** (backend 1408, frontend 798).
  Migration/OpenAPI/RBAC/capabilities/provider approval remain unchanged. QR-09D's external patch
  remains unapplied.
- **Previous change:** QR-09E repairs QR-09-D7: binary QR retrieval no longer inherits the WAHA
  client's JSON default and now requests `image/png` explicitly, while every JSON request retains
  `application/json`. Exact certified WAHA `2026.7.2` / `NOWEB` / `CORE` reproduces the JSON
  response under JSON negotiation and returns a valid PNG through the repository client. Repeated
  live application requests return `200 image/png` with no-store/private cache controls and create
  no duplicate provider or durable session. QR bytes remain in memory only and are neither shown,
  stored, logged nor scanned. The release gate is now **23/23 PASS** (backend 1407, frontend 796).
  Migration/OpenAPI/RBAC/UI/capabilities/provider approval remain unchanged. QR-09D's three-file
  frontend patch remains preserved externally and absent from QR-09E.
- **Previous change:** QR-09C repairs QR-09-D5 technically: both Compose models configure one global,
  private WAHA callback to the existing `/api/v1/webhooks/waha` receiver, subscribe only to
  `message`, `message.any`, and `message.ack`, and supply a dedicated HMAC key to the unchanged
  raw-body SHA-512 verifier. Production publishes no WAHA port; per-session webhooks remain absent
  to avoid duplicate delivery and persisted signing keys. The exact certified image's own sender
  proves private callback reachability, provider-generated HMAC, byte-identical retry after a
  controlled 503, and signed ACK delivery after restart with zero sessions/QR/phone interaction.
  Full release gate **22/22 PASS** (backend 1399/0 skipped; frontend 796). Migration `0043`/44
  revisions, OpenAPI 207, RBAC, UI and provider capabilities are unchanged.
  **META WEBHOOK_VERIFY_TOKEN ROTATION: PENDING — OWNER DEFERRED.** Consequently QR-09C is PARTIAL;
  `Host Validated`/`Provider Validated`/`Production Ready` remain NO.
- **Previous change:** QR-09B repairs QR-09-D4: the certified image lacks the committed `wget`
  executable. Both Compose models now use the image's verified `curl 7.88.1` against the
  unauthenticated provider-owned `/ping` endpoint with a five-second bound. A real-container
  regression proves positive health, deterministic failure against an unavailable endpoint,
  Docker `healthy` before and after restart, exact digest/provider identity, network boundaries,
  and session-volume preservation. All 21 release gates pass (backend 1397; frontend 796); no
  migration, route, RBAC, capability, application behavior, pairing, or certification-state change.
  `Host Validated`/`Provider Validated`/`Production Ready` remain NO.
- **Previous change:** QR-09A — Production Validation Remediation: repairs exactly the blockers QR-09
  recorded, and nothing else. **D1** — `0043`'s `downgrade()` released `uq_conv_endpoint_contact`
  before the foreign key InnoDB borrows it for; all conversation-side drops now run in one batch in
  dependency order, so the revision is reversible on real MySQL. No new revision was created (the
  upgrade path, revision id and schema are unchanged), and a live-MySQL up/down/up regression proves
  seeded Meta data survives and no partial schema is left behind. **D2** — the provider's
  `404 Session not found` is narrowed to `WahaSessionNotFound` and treated as an observation, not a
  fault: the status endpoint returns a truthful recoverable state instead of an HTTP 500, durable
  pairing truth is preserved, a previously paired connection is told it needs a fresh scan, reconnect
  refuses with `409`, and a status read is proven to issue no write and fetch no QR. Genuine outages
  still report `provider_unavailable`, so QR-06 is untouched. The frontend stopped rendering the
  state as "Starting the session…". **D3** — an oversized delivery is answered `413` instead of
  `500`, which stops the provider's at-least-once retry looping; the refuse-before-hashing bound is
  unchanged. **G1** — the OpenAPI artifact was regenerated through the canonical exporter and the
  required drift gate is green; 207 paths unchanged with one additive D2 property, and the
  inaccurate "key-order/resolver" explanation is annotated rather than rewritten. **I1** — a
  digest-pinned WAHA service was added to both compose files behind a `waha` profile, publishing no
  port in production, with a persistent `waha-sessions` volume at `/app/.sessions` and a full
  operator runbook. **S1** — `cryptography` floor raised to `>=50`; `pip-audit` reports no known
  vulnerabilities. Validated against real MySQL 8.0.46, Redis 7.4.9 and the real pinned WAHA
  container, including reproducing the D2 condition end to end (now `200`, was `500`) and proving a
  real `docker compose restart` preserves the session with the volume. **Capabilities, RBAC,
  migration head, path count and the provider certification record are all unchanged.** Physical-phone
  and host/browser evidence remain outstanding, so `Host Validated`/`Provider Validated`/
  `Production Ready` stay NO.
- **Previous change:** QR-09 — Production Validation (attempted, blocked): validated against **real**
  MySQL `8.0.46`, Redis `7.4.9`, and the real pinned WAHA container
  (`devlikeapro/waha@sha256:33ecd1b7…`, 2026.7.2/NOWEB/CORE) rather than QR-08's SQLite-only preview
  evidence. Closed the QR-08 preview's Redis-absent `503` limitation: normal send, duplicate-key
  replay, concurrent-duplicate collapse, fail-closed outage, and post-restart recovery all proven
  against real Redis. Proved the decisive QR-08 claim on real MySQL: one underlying provider message
  delivered as `message`×2 + `message.any`×2 produces 4 `webhook_events` rows but exactly **1**
  stored message. Found and left unfixed (defect policy: discover, record, stop — do not silently
  remediate inside a validation milestone) two Major defects — **QR-09-D1**: `0043`'s `downgrade()`
  fails on real MySQL because `uq_conv_endpoint_contact` is dropped before the foreign key that
  depends on it (same class as the tracked `0036`/`0040` downgrade defect); **QR-09-D2**: the QR
  operator status endpoint returns `HTTP 500` when the real provider is up but the named session is
  gone (a restarted WAHA container has no persistent session volume — none is defined anywhere in
  this repository's compose/deployment files), because `ChannelApiError`/404 is not translated into
  a truthful recoverable state — and one Minor (**QR-09-D3**: oversized webhook body correctly
  refused before hashing but surfaces as `500` rather than a 4xx). Also found, and **corrected**, a
  wrong governance explanation: the OpenAPI drift gate genuinely fails, but not for the reason
  previously recorded ("key-order mismatch under an unpinned resolver") — investigation proved
  generation is deterministic and the committed/generated JSON objects are exactly equal, 207 paths
  both; the only byte difference is ASCII-escaping. That required gate (`quality_gate.py:98`) stays
  red. Classification: `Repository Validated: NO` · `Host Validated: NO` · `Provider Validated: NO`
  · `Production Ready: NO`. No product code, migration, OpenAPI artifact, dependency, or capability
  was changed; recommended next milestone `QR-09A — Production Validation Remediation` is not
  started.
- **Previous change:** QR-08 — Unified Inbox integration: wires QR-04's inbound and QR-05's outbound/ack translation into the **same** existing `Conversation`/`Message`/`MessageService`/`ConversationService`/`InboxQueryService`/`SendService` authorities Meta already uses, rather than a second Inbox. Additive migration `0043` gives `conversations`/`messages`/`webhook_events` a nullable, app-enforced `channel_endpoint_id` alongside the existing `phone_number_id` (`conversations.phone_number_id` widened to nullable, `ck_conv_endpoint_owner` requires exactly one owner); reuses the M13-03 `channel_endpoints` table QR-07 never populated (`WhatsAppQrService.connect()` now creates one, idempotently). Inbound stored-message dedupe is endpoint-scoped + canonical-provider-id, independent of event-level dedupe (`message`/`message.any` collapse to one row). Outbound reply routing is entirely server-derived from the conversation's own durable ownership (`SendService.accept_for_conversation`) — `MessageSendRequest` gains an optional `conversation_id`; when present the request carries no provider field at all, so there is nothing to forge. A WAHA send that cannot be confirmed is marked `failed`/`indeterminate` and is never auto-retried (no blind resend). WAHA composer honestly refuses to send when the session is not connected (reused from QR-07's own live status read; no automatic reconnect). Inbox UI gains a channel badge (list + thread header) and a provider-aware composer; no new Inbox route. Two real defects found and fixed during this milestone: (1) QR-07's `_REAUTH_PAIRING` incorrectly included `UNPAIRED`, diverging from the canonical QR-06 definition — harmless until QR-08 needed `connect()` to always succeed; (2) `message.ack` events were classified `UNKNOWN` by QR-04's `parse_events` even though QR-05 had already built `to_status_update` to translate them — now routed as `STATUSES`. **Permanently absent for WAHA: MEDIA, INTERACTIVE, REACTION, LOCATION, CONTACT, TEMPLATE, CAMPAIGNS, BULK** (`ChannelCapabilityNotSupportedError` on a non-text reply attempt). No history/media sync, no QR-09 production validation.
- **Previous change:** QR-07 — WhatsApp Scan/Connect interface: the first real operator-facing surface over the WAHA adapter, bridging it to the existing M13-03/04/05 connection/session/pairing control plane. 6 new routes under `/channels/whatsapp-qr` (own `channels:read`/`channels:authenticate` gate; no RBAC catalog change), a live-polling frontend covering all 12 required states, and no-store QR delivery. **OpenAPI 200 → 206 paths (authorized, unlike every prior QR milestone)**; no migration (reuses existing tables); no QR-08 (Unified Inbox), history/media sync, campaign/bulk/template, or interactive/reaction/location/contact.
- **Previous change:** QR-06 — WAHA session recovery, health and teardown: start/stop/logout behind a runtime lease, bounded reconnect planning driven by durable pairing truth rather than the provider's ambiguous `STARTING`, and a session-scoped health projection. Declares `SESSION_RECONNECT` and `SESSION_LOGOUT`. Runtime registration is **opt-in** — importing the package still registers no runtime. **No history/media sync, no session deletion, no interactive/reaction/location/contact, no route, table or migration, and no UI.**
- **Previous change:** QR-05 — WAHA send path and delivery-state reconciliation: outbound text through the configured session, canonical provider-id capture, acknowledgement translation onto the platform's **existing** monotonic `messages.status` vocabulary, and an endpoint-scoped reconcile-before-resend primitive. Declares `TEXT`. **No blind retry, no teardown/reconnect, no media/history, no interactive/reaction/location/contact, no route, table or migration, and no UI.**
- **Previous change:** QR-04 — WAHA webhook ingestion: raw-body sha512 HMAC verification and provider event normalization onto the **existing** `ChannelAdapter` webhook seam and `webhook_events` ingest authority. Dedupe identity is scoped by session **and** event type because certification proved `envelope.id` alone is not unique. Declares `SESSION_STREAM`. **No new route, table or migration; no send path, no delivery-state persistence, no teardown, no history/media execution and no UI.**
- **Previous change:** QR-03 — WAHA QR pairing: create a session with the certified store configuration, fetch the transient QR challenge, and report provider-neutral pairing state. First declared capability since QR-01 (`QR_AUTH`). **QR-03 can bring a session up and cannot take one down — no stop/restart/logout/delete, no webhook ingestion, no send path, no media/history transfer, no session runtime, no public route and no UI.**
- **Completion:** Shared Enterprise Design System `94%` · Global Search `85%` · Reactivation `94%` · Module 13 `52%` (was 48%) · Chat History `55%` — Module 13 raised: QR-08 is the first milestone that makes WAHA operator-visible in a real workflow (the Inbox), not just an isolated control-plane/session surface.
- **Backend evidence:** Ruff PASS · strict mypy PASS (300 files) · 1380 full pytest tests PASS (1367 before QR-08; +13 QR-08 tests: mixed inbound/routing/dedupe/RBAC/indeterminate-send/not-connected coverage) · Bandit PASS (only pre-existing Low `assert`-usage findings in QR-07 code, none new)
- **Frontend evidence:** ESLint PASS · TypeScript PASS · 793 Vitest tests PASS (789 before QR-08; +4) · production build PASS (`InboxPage` chunk 37.28 kB / gzip 10.28 kB, up from carrying no channel-badge/WAHA-composer logic)
- **Provider selection:** WAHA 2026.7.2 (CORE, NOWEB, Apache-2.0), ADR-0021 Class B. Approvals recorded in `docs/evidence/provider-evaluations/waha-class-b-selection-record.md`. The physical-phone evidence that record required was produced on 2026-08-08 and PASSED; the record itself still reads **CONDITIONALLY CERTIFIED — HOST/PHONE EVIDENCE REQUIRED** and needs an **owner decision** to advance, which QR-08 does not make on its own authority.
- **Physical-phone certification:** **PASSED** (2026-08-08) against the pinned certified build. Real QR pairing to `WORKING`, controlled-restart reconnect with no new QR, external outbound with `SERVER`/`DEVICE`/`READ` acknowledgement, external inbound text, external inbound JPEG with verified download, HMAC-verified webhook delivery, history/fullSync correlation, and logout with re-auth required. This unblocked QR-02; it does not itself constitute Host Validated / Production Ready evidence for QR-08.
- **QR-09 real-infrastructure evidence (PARTIAL — BLOCKED):** real MySQL `8.0.46` + Redis `7.4.9` + the certified WAHA digest (`sha256:33ecd1b7…`). Backend full suite **1385 passed, 0 skipped** (11/11 live-MySQL tests genuinely ran, vs 5 always-skipped without MySQL). Frontend 38 files / 793 tests, ESLint, TypeScript, build all PASS. Ruff/mypy PASS. Bandit 0 High/0 Medium/28 Low. `pip-audit`: 1 production advisory (`cryptography 49.0.0`, not upgraded). `npm audit --omit=dev`: 2 moderate. Latency within this repository's own documented budgets (Doc 01 `NFR-PERF-01` p95 < 300 ms; Doc 06 webhook ack < 200 ms) on a single workstation. **Two Major defects open** (QR-09-D1 real-MySQL `0043` downgrade failure; QR-09-D2 QR status `500` when provider is up but session is absent), **one Minor** (QR-09-D3 oversized-webhook `500`), and **one required gate red** (OpenAPI drift — investigated and found to be a genuine ASCII-escaping artifact difference, not the previously-recorded "resolver key-order" cause). Full detail: `VALIDATION_RESULTS.md` "QR-09 — Production Validation".
- **QR-09A remediation evidence:** real MySQL `8.0.46` + Redis `7.4.9` + the certified WAHA digest. Backend **1397 passed, 0 skipped** (1385 before; +12) · live-MySQL **12 passed** (11 before) · QR-01..08 regression **371 passed** together · frontend **796 passed** (793 before; +3) · Ruff/strict mypy/ESLint/TypeScript/production build PASS · `scripts/quality_gate.py static` passes **all six steps**, including the previously red OpenAPI drift step · Bandit unchanged (0 High/0 Medium/28 Low) · `pip-audit` **no known vulnerabilities**. Full detail: `VALIDATION_RESULTS.md` "QR-09A — Production Validation Remediation".
- **QR-09B runtime evidence:** exact certified digest; WAHA `2026.7.2` / `NOWEB` / `CORE`; exec-form
  `curl --fail --silent --show-error --max-time 5 http://127.0.0.1:3000/ping`; Docker healthy before
  and after restart; negative unavailable-endpoint probe non-zero; development `127.0.0.1:3000`
  only; production no published WAHA port; `waha-sessions:/app/.sessions` preserved; no startup
  coupling. Full `scripts/quality_gate.py release`: **21/21 PASS**, backend 1397, frontend 796.
- **QR-09E runtime evidence:** exact certified digest; WAHA `2026.7.2` / `NOWEB` / `CORE`; JSON
  negotiation baseline `200 application/json`; repository client `200 image/png`; repeated live
  application fetches with no-store/private controls; exactly one provider/durable session; no QR
  output or persistence. Full `scripts/quality_gate.py release`: **23/23 PASS**, backend 1407,
  frontend 796.
- **Next milestone:** none authorized. Do not automatically reapply QR-09D or resume QR-09. Meta
  rotation, QR-09D revalidation, physical-phone E2E and supported-browser/target-host validation
  await explicit owner direction.
- **Last synchronized:** `2026-08-09T11:54:44+05:30`

## Delivered

### Alembic version-table MySQL fix — support long revision ids

- **Verified failure:** `alembic upgrade head` against a real MySQL 8 database (this repository's
  own `docker compose up -d` infrastructure) failed transitioning
  `0035_notification_center → 0036_customer_identity_resolution` with
  `DataError: Data too long for column 'version_num'`. Alembic's own `alembic_version.version_num`
  bookkeeping column defaults to `VARCHAR(32)`; this repository's descriptive revision-id
  convention produces identifiers up to 43 characters, and `0036_customer_identity_resolution`
  (33 characters) was the first to exceed it. No real MySQL deployment had ever advanced past
  `0035_notification_center` — this blocked all schema creation, `create-owner`, authentication,
  and any real UI preview on MySQL.
- **Repair:** a new revision, `0035a_widen_version_table`, inserted between
  `0035_notification_center` and `0036_customer_identity_resolution`, widens
  `alembic_version.version_num` to `VARCHAR(255)` on MySQL only (dialect-guarded; SQLite has no
  length enforcement and PostgreSQL is not part of this stack). `0036_customer_identity_resolution`'s
  `down_revision` was retargeted to the new revision; its own id, schema body and behaviour are
  byte-for-byte unchanged. No revision was renamed, renumbered, squashed, reordered, or stamped
  past a failure. Head remains `0041_channel_sync_control_plane`; the chain stays linear with a
  single head (42 revisions, was 41).
- Verified on real MySQL 8, both via automated tests (throwaway per-test databases) and by
  reproducing the documented CLI workflow manually against a fresh `docker compose` instance: a
  fresh database upgrades base→head; a database stamped at `0035_notification_center` (the exact
  historical failure point) upgrades to head; `python -m app.cli create-owner` succeeds
  immediately afterward, including its documented idempotent re-run behaviour. This is
  repository/local-host evidence (a local `docker compose` MySQL 8 container) — not genuine
  target-host validation, which remains pending.
- Regression coverage added: three hermetic checks in `test_migrations.py` (single head, linear
  chain, every revision id fits the widened column with an early-warning margin) plus a new
  `test_migrations_mysql.py` — three tests against real, throwaway MySQL databases, skipped
  (never failed) when no MySQL server is reachable, so the hermetic default suite gains no new
  external dependency.
- Frontend, application endpoints, models, schemas, RBAC, and OpenAPI are all unchanged;
  `scripts/export_openapi.py --check` and the full static quality gate both pass.
- **Does not unblock the separate Chat History UI-preview gap:** producing a real, populated
  `/chat-history` screenshot still requires either live Meta WhatsApp Business API credentials (to
  register a phone number and create genuine conversations/messages) or an approved development
  fixture mechanism, neither of which exists. This fix repairs the schema/auth path only.
- **Known open defect, pre-existing and unrelated to this fix:** downgrading past
  `0036_customer_identity_resolution` or `0040_channel_sync_media_foundation` fails on real MySQL 8
  with `DROP INDEX ... needed in a foreign key constraint`; reproduced identically against the
  pre-fix migration graph, confirming it is not caused by `0035a_widen_version_table`. Hermetic
  (SQLite) downgrade coverage for these revisions passes and remains valid for what it tests, but
  does not prove MySQL rollback safety. Remediation is out of scope for this fix.
- **Known gap, pre-existing:** no CI pipeline exists in this repository, and the local quality gate
  does not provision MySQL before running tests, so `test_migrations_mysql.py` has no automated
  execution path today — it runs only when a developer manually starts MySQL first.

### Defect fix — WAHA webhook event identity collision

- **Root cause:** `event_identity()` in `app/channels/waha/webhook.py` built
  `f"waha:{session}:{event_type}:{envelope_id}"[:128]`. The docstring claimed placing
  `envelope_id` last made it "survive truncation"; this was backwards — Python slicing `[:128]`
  keeps the **left** prefix and discards the right tail, so `envelope_id` (placed last) is exactly
  what gets cut. Once `session`/`event_type` alone pushed the fixed prefix past 128 characters,
  every `envelope_id` was discarded and two distinct events collapsed onto one stored
  `webhook_events.event_id`. A second, length-independent collision existed in the same
  concatenation: plain `":"` delimiters let one component's content be mistaken for another's
  boundary (`session="tenant", event_type="a:b"` collided with `session="tenant:a", event_type="b"`).
  Both reproduced as regression tests before the fix.
- **Fix:** `event_identity()` now returns `"waha:" + sha256(canonical).hexdigest()` — a fixed 69
  characters, always within the 128-character column regardless of component length. `canonical`
  is a netstring-style length-prefixed encoding of all three full components
  (`f"{len(part)}:{part}|"` per component), which is unambiguous by construction: a component's
  own exact character count pins its boundary, so no content — including the delimiter characters
  themselves — can forge a false boundary. `hashlib.sha256` is used, not Python's `hash()`, which
  is per-process randomized and would make the key non-reproducible.
- **Scope discipline:** the fix is confined to `event_identity()`/`_canonicalize()` in
  `webhook.py`. QR-05 send/delivery-state code, Meta behaviour, capabilities, routes, OpenAPI and
  migrations are all untouched.
- **Tests:** 12 new tests, including a reconstruction of the removed algorithm that proves it
  collided on the same inputs the new algorithm now discriminates, plus five delimiter-injection
  cases and a determinism/no-`hash()` assertion. Full QR-04 suite 64 passed (52 before); all five
  WAHA suites 253 passed together; full backend suite 1289 passed (1277 before).

### QR-07 — WhatsApp Scan/Connect interface

- **Delivered:** `app/services/whatsapp_qr_service.py` (bridges live WAHA I/O to
  `ChannelConnectionService`/`SessionManager`/`PairingManager`), `app/api/v1/endpoints/whatsapp_qr.py`
  (6 routes), `app/schemas/whatsapp_qr.py`, WAHA runtime registration wired into
  `get_channel_foundation()` (opt-in, gated on full configuration), and
  `frontend/src/features/whatsapp-qr/` (status polling, QR display, connect/pair/reconnect/logout,
  route `/channels/whatsapp-qr`).
- **Real defects found and fixed while integrating, not hidden:** (1) `PairingManager` requires
  `INITIALIZING`/`WAITING_FOR_PAIRING` for any pairing transition — reaching `ACTIVE` must happen
  strictly after pairing lands, not before, so `_apply_snapshot` orders the two conditionally.
  (2) `PairingState.PAIRED` is terminal in the existing state machine — logout terminates the
  paired revision and registers a fresh `UNPAIRED` one rather than attempting an illegal reverse
  transition. (3) `SessionManager.acquire_lock` refuses a `PAUSED` session — reconnect exits
  `PAUSED` via the lease-free write path before leasing.
- **Single-organization scope (ADR-0021):** `WAHA_ORGANIZATION_ID` names the one org the surface
  exists for; every other org — and an unconfigured deployment — sees the identical
  `configured=false`, so existence is never confirmed to a caller who does not own it.
- **QR still never persisted:** fetched fresh per request, `Cache-Control: no-store, private`, held
  client-side only as a revoked-on-replace object URL.
- **Known limitation, disclosed not hidden:** retrying an expired never-scanned QR surfaces the
  provider's real "session already exists" error (proven in QR-03's own suite) rather than a
  fabricated success — a dedicated provider restart path is not built in this milestone.
- **Tests:** 30 new hermetic backend tests + 23 new frontend tests. Backend suite 1364 passed
  (0 before this milestone's two path-count fixes); frontend suite 789 passed (766 before; +23).
- **OpenAPI:** 200 → 206 paths — the first authorized public surface over the pairing control
  plane. Two pre-existing exact-count invariant tests were updated with rationale; the
  no-secret-shaped-field assertions they also carry are unchanged and still pass.
- **Unchanged:** migration head `0042` (43 revisions, reuses existing tables), RBAC catalog
  (permissions pre-existed from M13-05), Meta behaviour, prohibited capabilities.

### QR-06 — WAHA session recovery, health and teardown

- **Delivered:** `app/channels/waha/recovery.py` (`plan_reconnect`, `backoff_delay`, `RuntimeLease`/
  `assert_lease_current`, `project_health`, opt-in runtime metadata + `register_waha_runtime`),
  client `start_session`/`stop_session`/`logout_session`, and adapter `session_health`/
  `plan_session_recovery`/`reconnect_session`/`stop_session`/`logout_session`. Declares
  `SESSION_RECONNECT` and `SESSION_LOGOUT`.
- **STARTING ambiguity enforced, not just documented:** reconnect planning consults the durable
  pairing record before the provider status, so `STARTING` yields `WAIT` and never `RECONNECT` or
  `REQUIRES_REAUTH`. An unpaired session is never auto-restarted.
- **Outage safety:** an unreachable provider yields `PROVIDER_UNAVAILABLE`, asserted distinct from
  `REQUIRES_REAUTH`, so durable pairing truth survives a provider being briefly down.
- **Bounded:** attempts capped and backoff exponential to a 60s ceiling, computed as a pure function
  of the attempt number so every worker agrees without coordination.
- **STOP vs LOGOUT preserved:** STOP keeps credentials and refuses to claim the session became
  unpaired; LOGOUT deliberately produces re-auth-required truth that nothing auto-repairs. `DELETE`
  is not exposed at all.
- **Lease reuse, not reinvention:** `RuntimeLease` carries identifiers only; ownership remains
  `SessionManager`/`ProviderRuntimeManager` against `channel_sessions`. Both holder identity and
  fencing token must match, and every mutation refuses — with no provider call — when unowned.
- **Runtime registration opt-in:** the default `ProviderRuntimeRegistry` is still empty, preserving
  the invariant every milestone through QR-05 asserted.
- **Tests:** 62 new hermetic tests (`tests/test_channel_waha_recovery.py`); 313 across all six WAHA
  suites. Full suite 1349 passed (1289 before QR-06).
- **Unchanged:** migration head, OpenAPI (200 paths, zero QR routes), RBAC, generated types,
  frontend, Meta behaviour, and prohibited capabilities.

### QR-05 — WAHA send path and delivery-state reconciliation

- **Delivered:** `app/channels/waha/delivery.py` (ack vocabulary, `map_ack()`, `to_status_update()`,
  `extract_sent_id()`, `WahaSendIndeterminate`), client `send_text()`/`message_exists()`, adapter
  `_dispatch()`/`to_status_update()`/`reconcile_send()`, and `WahaCredentials.session` +
  `WAHA_SESSION_NAME`. Declares `TEXT`.
- **Monotonicity carry-forward closed:** the QR-05 acknowledgement-ordering constraint is satisfied
  by *reusing* `STATUS_RANK`/`advances()` rather than adding a second ordering. The certified
  out-of-order `DEVICE(2) → SERVER(1) → READ(3)` is proven to end at `read`, and every permutation
  of an interleaved ack sequence converges. Duplicate acks are idempotent; `failed` is terminal.
- **Ambiguous-send safety:** a transport failure is `WahaSendIndeterminate` — explicitly not a
  `ChannelTransportError`, so generic retry cannot sweep it up. Reconcile first; resend only on
  proven absence; a failed lookup stays indeterminate. No resend path exists.
- **Endpoint scoping is structural:** sends and lookups both go through `require_session()`, and the
  reconcile query runs inside that session's own chat. No global provider-message lookup.
- **QR-04 review (superseded — see the defect fix below):** the 128-character `event_identity`
  truncation was re-inspected during QR-05 and reported clean at the time. That conclusion was
  **wrong**: Python's `s[:128]` keeps the left prefix and discards the right tail, so placing
  `envelope_id` last did not make it survive truncation — it made it the first thing cut. A
  follow-up fix replaced the truncated concatenation with a fixed-length digest; see "Defect fix —
  WAHA webhook event identity collision" below.
- **Tests:** 46 new hermetic tests (`tests/test_channel_waha_delivery.py`); 241 across all five WAHA
  suites. Full suite 1277 passed (1232 before QR-05).
- **Unchanged:** migration head, OpenAPI (200 paths, zero QR routes), RBAC, generated types,
  frontend, Meta behaviour, prohibited capabilities, and the absence of a WAHA runtime.

### QR-04 — WAHA webhook ingestion

- **Delivered:** `app/channels/waha/webhook.py` (raw-body sha512 HMAC verification,
  `event_identity()`, `canonical_message_id()`, event normalization) plus the adapter's
  implementation of the existing `verify_webhook_signature`/`parse_webhook`/`to_inbound_message`
  seam. Configuration `WAHA_WEBHOOK_HMAC_SECRET` (empty default). Declares `SESSION_STREAM`.
- **No parallel ingest path:** events flow into the existing `WebhookService` → `webhook_events`
  authority, which already owns persist-first durability, dedupe and dead-lettering. No new route,
  table or migration.
- **Dedupe identity resolved:** the QR-04 carry-forward is closed. `envelope.id` alone is unsafe —
  one provider message arrives as both `message` and `message.any` sharing it — so the key is
  scoped by session and event type. Determinism proven by a 64-way concurrent test, because
  `messages` is partitioned and MySQL cannot enforce that uniqueness (error 1503).
- **Security:** verify before parse, over raw bytes, constant-time, 1 MiB bound enforced before
  hashing, unset secret rejects everything, no default secret, unknown/malformed shapes fail closed
  to `UNKNOWN` with no `event_id`.
- **Not pulled forward:** acknowledgements and outbound echoes are recorded as `UNKNOWN`, never
  applied — delivery state is QR-05. No teardown, history or media execution.
- **Tests:** 52 new hermetic tests (`tests/test_channel_waha_webhook.py`); 196 across all four WAHA
  suites. Full suite 1232 passed (1181 before QR-04).
- **Unchanged:** migration head, OpenAPI (200 paths, zero QR routes), RBAC, generated types,
  frontend, Meta behaviour, prohibited capabilities, and the absence of a WAHA runtime.

### QR-03 — WAHA QR pairing

- **Delivered:** `app/channels/waha/pairing.py` (`CERTIFIED_NOWEB_STORE`, `build_session_config()`,
  transient `WahaQrChallenge`), two client calls (`create_session`, `qr_challenge`) and three
  adapter methods (`begin_pairing`, `pairing_challenge`, `pairing_state`). `QR_AUTH` is declared —
  the first capability added since QR-01.
- **Up, never down:** no stop, restart, logout or delete exists on adapter or client, asserted by
  test. Teardown is QR-06, so nothing shipped so far can destroy a working pairing.
- **Silent-failure trap closed:** `fullSync` is camelCase and built in one place. Certification
  proved `full_sync` returns HTTP 201 and then silently stores `fullSync: false`, leaving a session
  that looks healthy with no history.
- **QR is a secret:** never persisted, never logged, excluded from `repr`. M13-05's boundary that
  QR images and challenge bytes are never stored is preserved rather than widened.
- **Pairing safety:** `pairing_state()` returns `None` on `STARTING`/`STOPPED`/`FAILED`; durable
  pairing truth is never overwritten from an ambiguous provider status.
- **Boundary tests re-pointed, not removed:** two guards moved with the milestone (see the QR-03
  changelog entry). `send_text` was dropped from a forbidden-name list because it is an inherited
  generic `ChannelAdapter` method whose presence proves nothing; the send path is now asserted
  behaviourally to still raise `ChannelNotSupported`.
- **Tests:** 30 new hermetic tests (`tests/test_channel_waha_pairing.py`). Full suite 1181 passed
  (1153 before QR-03).
- **Unchanged:** migration head, OpenAPI (200 paths, zero QR routes), RBAC, generated types,
  frontend, Meta behaviour, prohibited capabilities, and the absence of a WAHA runtime.

### QR-02 — WAHA session lifecycle read and provider-neutral mapping

- **Delivered:** `app/channels/waha/lifecycle.py` — `WahaSessionStatus` (the five statuses observed
  during physical-phone certification: `STARTING`, `SCAN_QR_CODE`, `WORKING`, `FAILED`, `STOPPED`),
  a pure `map_session_status()` onto `SessionState`/`PairingState`, `WahaSessionSnapshot`, and
  strict session-name validation. One authenticated client read (`GET /api/sessions/{name}`) and two
  adapter methods (`session_snapshot`, `session_status`).
- **Read-only:** no session is created, started, stopped, restarted, paired or logged out. Adapter
  and client are asserted to expose no such method. Driving a lifecycle is QR-03/QR-06.
- **Capability-neutral:** capabilities remain exactly `HEALTH`; `PROHIBITED_CAPABILITIES` untouched.
- **Honest ambiguity:** `STARTING`/`STOPPED`/`FAILED` return no pairing state, because certification
  observed `STARTING` on both a fresh session and a controlled restart of a paired one. `FAILED`
  maps to `degraded`, not a terminal state, because certification recovered it with a restart.
- **Carry-forward respected:** QR-02 introduces no delivery-state persistence and no event dedupe,
  so the out-of-order acknowledgement finding (`DEVICE(2) → SERVER(1) → READ(3)`) and the shared
  `envelope.id` finding constrain QR-04/QR-05, not this milestone. The mapping is pure and
  order-independent by construction.
- **Tests:** 54 new hermetic tests (`tests/test_channel_waha_lifecycle.py`). Full suite 1153 passed
  (1099 before QR-02).
- **Unchanged:** migration head, OpenAPI (200 paths), RBAC, generated types, frontend, Meta
  behaviour, and the absence of a WAHA entry in `ProviderRuntimeRegistry`.

### QR-01 — WAHA provider adapter foundation

- **Delivered:** connector identity `waha` on channel family `whatsapp`; a minimal typed async
  client (`app/channels/waha/client.py`) implementing exactly two authenticated reads — the server
  version/engine banner and `/health`; the adapter (`app/channels/waha/adapter.py`) behind the
  existing `ChannelAdapter` seam; inert static registration; and disabled-by-default configuration.
- **Capabilities:** only `HEALTH`. Withheld deliberately: `QR_AUTH`, `SESSION_STREAM`,
  `SESSION_RECONNECT`, `SESSION_LOGOUT`, `HISTORY_SYNC`, `TEXT`, `MEDIA`, `MEDIA_UPLOAD`,
  `MEDIA_DOWNLOAD`, `INTERACTIVE`, `REACTION`, `LOCATION`, `CONTACT` — each either unimplemented
  here, unproven without a paired handset, or both. A provider endpoint existing is not evidence
  that this adapter can use it.
- **Permanently prohibited:** `BULK`, `CAMPAIGNS`, `TEMPLATE` (ADR-0020 section 5, ADR-0021, owner
  Class B approval). Recorded in `PROHIBITED_CAPABILITIES` and enforced by tests asserting they are
  never declared and that the capability gate refuses template/text sends.
- **Server health is not session health:** `authenticate()`/`status()` report `connected=False` with
  an explicit "No WhatsApp session" detail; `health_signal()` labels itself server-health-only.
- **Error mapping:** timeout and unavailable to `ChannelTransportError` (distinct messages);
  401/403 to `ChannelAuthError`; 5xx and other reached errors to `ChannelApiError` with status;
  malformed JSON, unexpected content type and non-object JSON to `ChannelApiError`; unconfigured to
  `ChannelConfigError` before any socket opens.
- **Version/engine safety:** baseline `2026.7.2`, `NOWEB` only. Unexpected engine fails closed;
  drift is reported and never auto-corrected; the spike pinned an immutable digest, not a floating
  tag.
- **Security:** API key sent only as `X-Api-Key`, never logged, never in an exception message,
  masked in `repr`; provider error bodies never echoed; error log carries status and path only.
- **Real validation:** isolated `devlikeapro/waha:noweb-2026.7.2` run locally on `127.0.0.1`; the
  committed adapter driven against it, 11/11 checks. No session created, no QR requested, no phone
  paired, nothing sent or received. Torn down and credentials removed; the committed
  `docker-compose.yml` was not edited.
- **Unchanged:** migration head, OpenAPI (200 paths), RBAC, generated types, frontend, Meta
  behaviour, and the QR-00 endpoint-scoped provider-message identity.

### QR-00 — WAHA Class B provider selection and provider-message identity foundation

- **Provider selection:** WAHA 2026.7.2 (tier CORE, engine NOWEB, Apache-2.0) recorded as the
  ADR-0021 Class B candidate in `docs/evidence/provider-evaluations/waha-class-b-selection-record.md`,
  the Design Document 33 §6.4 selection record. It succeeds — and does not rewrite — the earlier
  `waha-class-b-evaluation.md`, closing its E-005/E-006/E-010/E-011(partial)/E-015 items. Owner
  Approval, Architecture Approval, Security Approval and explicit acceptance of WhatsApp
  restriction/ban risk are recorded verbatim. Certification remains **CONDITIONALLY CERTIFIED —
  HOST/PHONE EVIDENCE REQUIRED**; production certification is **not** granted.
- **Message identity root cause:** `MessageRepository.get_by_wamid(wamid)` resolved a provider
  message id globally — no organization, connection or endpoint filter. Safe only while Meta (whose
  `wamid` is globally unique) was the sole provider; a QR provider's session-scoped ids may
  legitimately repeat across endpoints, which would let one endpoint resolve, or a delivery receipt
  advance, another endpoint's or another tenant's message. Contradicted ADR-0020.
- **Fix:** `get_by_provider_message_id(provider_message_id, *, phone_number_id)` — endpoint-scoped,
  with the scope keyword-only and required so an unscoped lookup cannot be written. No global
  variant exists. `phone_numbers.organization_id` is `NOT NULL`, so the endpoint transitively pins
  the tenant. All three call sites updated; `apply_status` now receives the endpoint the callback
  arrived on (already available and null-checked in `webhook_service`).
- **No backfill required and none performed.** `messages.organization_id`/`phone_number_id` have
  been `NOT NULL` since `0016_conversations_messages`; ownership is already explicit, not derived.
  Verified on the live database: 191 rows, 0 null owners, 0 orphaned endpoints, 0 org mismatches,
  0 duplicate `(phone_number_id, wamid)` pairs.
- **UNIQUE constraint proven impossible.** `messages` is `PARTITION BY RANGE COLUMNS(created_at)`;
  MySQL error 1503 requires unique keys on partitioned tables to contain the partition columns
  (reproduced on MySQL 8.0.46 against this schema). Adding `created_at` would permit the duplicate
  the rule exists to prevent. Uniqueness stays enforced by the scoped read plus persist-first
  ingestion, as it already is for Meta. Migration `0042_scope_provider_message_identity` adds only
  the supporting non-unique index `ix_msg_endpoint_wamid (phone_number_id, wamid)`.
- **Re-authentication health:** derived projection (`app/channels/attention.py`), not a new stored
  state — Option B. Projects `ProviderHealthState` + `SessionState` + `PairingState` into the four
  Doc 33 §6.1 signals (Healthy/Warning/Critical/Re-auth Required). Avoids duplicating state the
  session columns already carry and avoids widening `CHECK` constraints on three columns. Re-auth
  outranks observed health; `TERMINATED` never reports re-auth. No provider-specific value.
- **Tests:** 21 new in `tests/test_provider_message_identity.py` — same provider id on two
  endpoints resolves separately, endpoints cannot read each other's messages, organizations cannot
  read each other's messages, the scope cannot be omitted, plus total coverage of the projection
  across every state combination. Migration head pins updated in `test_migrations.py` and
  `test_migrations_mysql.py`.
- **Meta compatibility unchanged:** webhook ingestion, inbound dedupe, delivery/read reconciliation
  and Inbox suites pass unmodified. OpenAPI remains 200 paths; no route, schema, RBAC entry or
  generated type changed.
- **Explicitly not implemented by QR-00:** WAHA client/adapter/Docker service, provider runtime
  registration, QR API, QR image endpoint, QR persistence, QR frontend, webhook endpoint, inbound
  ingestion, outbound send, history sync, media sync, session worker, reconnect runtime, Unified
  Inbox QR integration, M13-07. QR login does not work and is not claimed to.

### MySQL migration evidence hardening (independent audit follow-up)

- **Governance correction:** the "Host evidence" row in `PROJECT_STATE.md` previously read
  "Target-host MySQL migration is now verified" — an overclaim, since the evidence was a local
  `docker compose` MySQL 8 container, not the project's target deployment host (the term
  "target-host" is used elsewhere in this repository specifically for that distinction). Reworded
  to state plainly that this is repository/local-host evidence and that genuine target-host
  evidence remains pending. No valid evidence was removed. `IMPLEMENTATION_TRACKER.md`'s own
  "Remaining work" list already correctly listed target-host evidence as pending — that
  inconsistency between the two files is now resolved.
- **Governance correction:** historical `VALIDATION_RESULTS.md` rows recording SQLite-hermetic
  downgrade passes for `0036_customer_identity_resolution` and `0040_channel_sync_media_foundation`
  are annotated to state plainly that they are hermetic/SQLite-only and do not prove MySQL rollback
  safety, cross-referencing the verified open real-MySQL downgrade defect recorded above. The
  historical PASS rows themselves, and the migration code they describe, are unchanged.
- **Test hardening:** `test_migrations_mysql.py`'s three live-MySQL tests now assert directly
  against `information_schema.COLUMNS` that `alembic_version.version_num` is genuinely
  `varchar(32)` before the repair and `varchar(255)` after it (both for a fresh base→head run and
  for the historical 0035→head transition) — real database inspection, not migration source text.
  `create-owner` is now exercised twice in one test: the first call creates the owner, the second
  is asserted idempotent (`owner_created`/`organization_created` both `False` on rerun), and a raw
  `SELECT COUNT(*) FROM users WHERE email = ...` confirms exactly one row exists after both calls —
  independent of what the returned dataclass claims.
- **Skip-logic hardening:** MySQL reachability is now classified into three states instead of two.
  A connection failure whose MySQL/pymysql error code indicates nobody answered (connection
  refused, timed out, unknown host) is `MySQLUnavailable` and skips cleanly, exactly as before —
  ordinary developers without Docker running still get a clean hermetic run. Any other failure
  (most commonly MySQL error 1045, "Access denied") means a real server answered and rejected the
  configured credentials; this is now `MySQLMisconfigured` and fails the live-MySQL tests loudly
  with a message naming the `DB_HOST`/`DB_PORT`/`MYSQL_ROOT_PASSWORD` environment variables to
  check — never the credential value itself, which pymysql's own error text already omits. Six new
  tests cover the classification logic hermetically (no network access), plus two new tests
  confirm the "reachable and correctly configured" and "reachable but rejects a wrong password"
  states against the real local MySQL 8 server when one is available.
- **Preserved, not modified:** `0035a_widen_version_table`, `0036_customer_identity_resolution`,
  and `0040_channel_sync_media_foundation` migration files are byte-for-byte unchanged; migration
  head remains `0041_channel_sync_control_plane`, revision count remains 42; no application
  endpoint, model, schema, RBAC definition, OpenAPI path, or frontend file changed;
  `scripts/export_openapi.py --check` and the full static quality gate both pass unchanged. No CI
  system was added — the real-MySQL downgrade defect at 0036/0040 and the absence of automated CI
  execution for `test_migrations_mysql.py` both remain open, explicitly recorded, and out of scope
  for this follow-up.

### PAR-VIEW-05 — Governed Report saved views

- Extends the shared saved-view discriminator with `reports`; Reports, KYC, Campaigns, Contacts and
  Reactivation share one governance service, persistence repository, tenant boundary and cap/name/
  lock policy. No second table or browser-only authority is introduced.
- Stores only one exact period preset or complete custom range, day/week granularity and optional
  previous-period comparison. Applying a view uses the existing Analytics URL contract; report tab,
  export format, schedule/progress and other transient state are excluded.
- Every Analytics reader governs private rows; `analytics:views_manage` protects organization-shared
  publishing/deletion. Lists contain tenant team rows plus only the actor's private rows, and
  workspace/tenant/private identifiers fail closed. Mutations commit with immutable Audit.
- Private/team chips and the responsive `Save / manage` sheet were verified in authenticated local
  desktop and 390-pixel mobile previews using an isolated database.
- `0061_reports_workspace_views` advances one linear head to **62 revisions**; list/create/delete
  operations advance OpenAPI to **235 paths** with synchronized generated TypeScript.
- Focused backend contracts **12/12**, focused Analytics UI **41/41**, full frontend **47 files /
  875 tests**, static **6/6**, strict mypy **322 files**, OpenAPI drift and production build PASS.
  Full backend: **1579 passed / 6 MySQL-only skipped / 0 failed in 413.35s**.
- Remaining `GROW-03` work is the Segment predicate/saved-filter slice. Representative-data WCAG/
  device, scale, Docker/security and target-host commissioning remain pending. No provider/customer/
  commit/push/release/deployment action occurred.

### PAR-VIEW-04 — Governed KYC saved views

- Extends the shared saved-view discriminator with `kyc`; KYC, Campaigns, Contacts and Reactivation
  continue to share one governance service, persistence repository, tenant boundary and
  cap/name/lock policy. No second table or browser-only view authority is introduced.
- Stores only trimmed customer search and one validated lifecycle status. KYC queue filters are
  URL-backed; applying a view clears transient selection, while fetch bounds, checklist/documents,
  appointments, SLA/detail and reviewer/manager decisions are deliberately excluded.
- Every KYC reader governs private rows; `kyc:views_manage` protects organization-shared
  publishing/deletion. Lists contain tenant team rows plus only the actor's private rows, and
  workspace/tenant/private identifiers fail closed. Mutations commit with immutable Audit.
- Lock/team chips and the responsive `Save / manage` sheet provide grouped management, permission
  truth, API errors and confirmed deletion without changing any KYC case.
- `0060_kyc_workspace_views` advances one linear head to **61 revisions**; list/create/delete
  operations advance OpenAPI to **233 paths** with synchronized generated TypeScript.
- Focused API/migration/OpenAPI contracts **12/12**, KYC UI **2 files / 8 tests**, full frontend
  **46 files / 870 tests**, static **6/6**, strict mypy **321 files**, OpenAPI drift and production
  build PASS. Full backend: **1574 passed / 6 MySQL-only skipped / 0 failed in
  450.05s**.
- Authenticated representative-data visual/WCAG/device review remains pending rather than PASS.
  Reports views, remaining segment predicates, protected-media/scale and host commissioning remain.
  No send/provider/customer/commit/push/release/deployment action occurred.

### PAR-VIEW-03 — Governed Campaign saved views

- Extends the shared saved-view discriminator with `campaigns`; Campaigns, Contacts and
  Reactivation continue to share one governance service, persistence repository, tenant boundary
  and cap/name/lock policy. No second table or browser-only view authority is introduced.
- Stores only trimmed search, validated lifecycle status and list sort. The URL-backed Campaign
  list remains authoritative; applying a view resets local page to one, while roster, recipient
  cursor, dispatch and lifecycle state are deliberately excluded.
- Every Campaign reader governs private rows; `campaigns:views_manage` protects organization-
  shared publishing/deletion. Lists contain tenant team rows plus only the actor's private rows,
  and workspace/tenant/private identifiers fail closed. Mutations commit with immutable Audit.
- Lock/team chips and the responsive `Save / manage` sheet provide grouped management, permission
  truth, API errors and confirmed deletion without changing any campaign.
- `0059_campaign_workspace_views` advances one linear head to **60 revisions**; list/create/delete
  operations advance OpenAPI to **231 paths** with synchronized generated TypeScript.
- Focused saved-view backend **16/16**, migration **5/5**, Campaign UI **54/54**, full frontend **45
  files / 866 tests**, static **6/6**, strict mypy **320 files**, OpenAPI drift and production build
  PASS. Full backend: **1569 passed / 6 MySQL-only skipped / 0 failed in 395.87s**.
- Authenticated representative-data visual/WCAG/device review remains pending rather than PASS.
  KYC/Reports views, remaining segment predicates, attribution/revenue/ROI and host commissioning
  remain. No send/provider/customer/release action occurred.

### PAR-VIEW-02 — Governed Contacts saved views

- Extends the existing saved-view store with a required workspace discriminator; Reactivation and
  Contacts share one governance service, persistence repository, tenant boundary and cap/name/lock
  policy. The original physical table name is retained for additive upgrade compatibility.
- Stores only trimmed search, tag UUID and validated enum-attribute filters. The existing Contacts
  search compiler, cursor paging, bulk actions and export rule audience remain authoritative;
  applying a view drops any stale cursor.
- Every Contacts reader governs private rows; `contacts:views_manage` protects organization-shared
  publishing/deletion. Lists contain tenant team rows plus only the actor's private rows, and
  workspace/tenant/private identifiers fail closed. Mutations commit with immutable Audit evidence.
- The existing responsive Contacts filter experience remains. Lock/team chips and the accessible
  `Save / manage` sheet provide grouped management, permission truth, API errors and confirmed
  deletion without changing contacts.
- `0058_contacts_workspace_views` advances one linear head to **59 revisions**; list/create/delete
  operations advance OpenAPI to **229 paths** with synchronized generated TypeScript.
- Focused backend **16/16**, focused UI **19/19**, full backend **1564 passed / 6 MySQL-only skipped
  / 0 failed in 506.04s**, full frontend **44 files / 863 tests**, static **6/6**, strict mypy **319
  files**, OpenAPI drift and production build PASS.
- In-app local-page access was denied, so authenticated representative-data visual/WCAG/device
  review remains pending rather than PASS. Campaigns/KYC/Reports views, attribution/revenue/ROI and
  host commissioning remain. No provider/customer/release action occurred.

### PAR-VIEW-01 — Governed Reactivation saved views

- Adds validated, tenant-scoped personal/team view definitions over existing Reactivation search,
  owner, status, label, reminder and date filters plus board/list mode; page position is excluded.
- Every Reactivation reader governs personal views; `reactivation:views_manage` protects team
  publishing/deletion. Another user's private UUID and foreign-tenant UUID fail as not found.
- Independent 25-view caps, case-insensitive scoped names, organization locking, database checks and
  atomic create/delete Audit evidence preserve concurrency and governance boundaries.
- Existing factual work views and URL state remain. Lock/team chips and an accessible responsive
  `Save / manage` sheet provide permission-truthful creation, grouped management, errors and
  deliberate deletion confirmation without changing any Reactivation case.
- `0057_reactivation_saved_views` advances one linear head to **58 revisions**; list/create/delete
  operations advance OpenAPI to **227 paths** with synchronized generated TypeScript.
- Focused backend **13/13**, focused UI **12/12**, full backend **1559 passed / 6 MySQL-only skipped /
  0 failed in 459.36s**, full frontend **43 files / 860 tests**, strict mypy **317 files**,
  changed-file Ruff, OpenAPI drift, frontend lint/types and production build PASS.
- Remaining: Contacts/Campaigns/KYC/Reports view integrations, attribution/revenue/ROI, target-scale
  and host commissioning. No provider/customer/release action occurred.

### PAR-CAM-01 — Campaign recipient failure operations

- Declares `status`, bounded `limit` and `cursor` on the existing recipient-ledger resource and adds
  a total-aware page envelope while keeping top-level `has_more` for v1 compatibility.
- Resolves current contact name/WhatsApp identity through an organization predicate, exposes safe
  status/error/retry/lifecycle facts, and leaves provider/message/internal error identities absent.
- Campaign Detail now filters the complete server roster and navigates forward/back through keyset
  cursor history. Failed-recipient retry requires an explicit count/boundary confirmation and keeps
  mutation errors in the decision dialog; the existing send permission, rate limiter, smart retry,
  idempotent roster, queue and Audit contracts remain authoritative.
- Additive `0056_campaign_recipient_operations` adds composite indexes for unfiltered and exact-
  status `(campaign_id, created_at, id)` scans. One linear head advances to **57 revisions**;
  OpenAPI remains **225 paths** and generated TypeScript is synchronized.
- Campaign/migration regression **107/107**, focused Campaign UI **51/51**, complete frontend **43
  files / 857 tests**, complete backend **1553 passed / 6 MySQL-only skipped / 0 failed in 476.67s**,
  static **6/6**, strict mypy **314 files** and Vite **8.2.2** build PASS.
- Still open: campaign-to-reactivation conversion and approved recovered-value/revenue/ROI sources,
  target-MySQL scale evidence, Docker/security rerun and host commissioning. No send/provider action.

### PAR-DL-03 — Governed Campaign results exports

- Adds a distinct `campaigns:export` entitlement and tenant/requester/campaign-scoped start/progress
  contracts. A job UUID cannot be substituted below another campaign and current permission still
  gates Download Center visibility.
- Streams the authoritative recipient ledger oldest-first in 500-row keyset batches, optionally by
  recipient status. The artifact includes current contact identity plus factual status/error-code/
  retry/cost/timestamps while excluding provider/message IDs, variables and internal error detail.
- PDF/CSV/XLSX/JSON reuse the existing export row, queue, hardened writers, storage, expiry, signed
  links and audit. Campaign Detail adds the responsive export/progress sheet; Download Center adds
  the Campaign results category and navigation entitlement.
- Additive `0055_campaign_results_exports` preserves one **56-revision** head. OpenAPI is **225
  paths**, generated TypeScript is synchronized and source image inventory is **32 tasks**.
- Campaign/export regression **106/106**, provider/OpenAPI/smoke/image **32/32**, migration **5/5**,
  focused UI **63/63**, complete backend **1552 passed / 6 MySQL-only skipped / 0 failed in
  475.58s**, complete frontend **42 files / 854
  tests**, static **6/6**, strict mypy **314 files** and production build PASS.
- Still open after PAR-CAM-01: campaign conversion/ROI, compliant Scan/generated-document artifacts and
  host commissioning. No send/provider action.

### PAR-HIST-01 — Advanced Chat History filters and shared views

- Extends the existing conversation list with declared inclusive-`from`/exclusive-`to`, campaign,
  media and audit parameters. Campaign/media use tenant-scoped ledger `EXISTS`; audit uses direct
  conversation audit evidence and requires `audit:read`. Existing keyset order and basic filters
  remain authoritative.
- Adds `conversation_history_views`: a 25-per-organization, case-insensitively named collection of
  validated portable filters. `inbox:read` lists/applies ordinary views; new
  `inbox:views_manage` creates/deletes them; audit-scoped views remain invisible without audit
  access. Create/delete are audited and tenant-isolated.
- Chat History adds compact team-view chips and an original responsive Advanced bottom-sheet/dialog
  with local calendar bounds, campaign/media/audit controls, validation and permission-truthful
  manager governance. Personal Live Chat preferences are unchanged.
- Additive `0054_chat_history_filters_views` preserves one **55-revision** head. OpenAPI is **223
  paths** and generated TypeScript is synchronized; no queue, provider, storage or customer-send
  contract changed.
- Focused backend **10/10**, existing Inbox/conversation/QR **77/77**, migration **5/5**, Chat
  History UI **41/41**, complete backend **1547 passed / 6 MySQL-only skipped / 0 failed in
  458.04s**, complete frontend **41 files / 850
  tests**, static **6/6**, strict mypy **314 files** and production build PASS.
- Remaining Chat History work is authenticated representative-data WCAG/device/browser review and
  production-scale target-host query commissioning. Docker/security and live-host acceptance remain
  separate.

### PAR-DL-02 — Governed Chat History transcript exports

- Adds one selected-conversation export contract and personal progress contract under the dedicated
  `inbox:export` permission. The UI only offers the action when both the Chat History route and this
  extraction entitlement are available; ordinary `inbox:read` users keep a read-only history view.
- The worker resolves the conversation inside the requester tenant and streams chronological ledger
  rows in 500-row keyset batches. Optional `from` (inclusive) / `to` (exclusive) instants support the
  UI's whole-day range; no browser-loaded page is mistaken for the complete thread.
- PDF/CSV/XLSX/JSON reuse the current export job, queue, format writer, storage, expiry, signed link,
  audit and Download Center. A new `chat_history` Center category is permission- and owner-filtered.
- Artifact content includes timestamp, direction, participant role, message type, human content,
  status and public message ID. Provider/storage/media identifiers and private links are excluded;
  spreadsheet formula triggers remain neutralized by the shared writer.
- Additive `0053_conversation_transcript_exports` seeds the permission only; no domain or artifact
  table is added. OpenAPI is **221 paths**, the source image inventory is **31 tasks**, and generated
  TypeScript is synchronized.
- Focused backend **35/35**, focused frontend **50/50**, complete backend **1537 passed / 6 MySQL-
  only skipped / 0 failed in 445.40s**, complete frontend **41 files / 845 tests**, static **6/6**,
  strict mypy **310 files** and production build PASS.
- Still open: list-level date/campaign/media/audit filtering, shared Chat History saved views,
  campaign/Scan/generated-document artifacts and target-host acceptance. No send/provider action.

### Dedicated Chat History read workspace over the existing conversation and message contract

- Added a `/chat-history` route and permission-aware `inbox:read` navigation entry — a read-only
  list/detail workspace over the same `GET /conversations`, `GET /conversations/{id}` and
  `GET /conversations/{id}/messages` endpoints Live Chat and Customer 360 already read, reusing
  `useConversations`/`useConversation`/`useMessages`/`useAssignableUsers` from
  `features/inbox/api.ts` verbatim — no second query authority.
- Supports every filter the current contract already backs: search (`q`), status, assignee, tag,
  and a new `number` (channel) filter — additive to `InboxFilters`/`toListQuery`, the same shared
  types Live Chat's own filters use, so the addition is available to both surfaces from one
  definition. Cursor pagination for the conversation list and the existing infinite-query
  "Load older messages" control are both reused as-is.
- Deliberately exposes no assignment, status, tag, note or send control — those remain Live Chat's
  job; this route only reads. A deep link opens the selected conversation in Live Chat; a second
  deep link to the audit trail is shown only to `audit:read` holders and hidden otherwise.
- At this historical foundation milestone, date-range filtering and transcript export were named as
  unavailable instead of being faked. PAR-DL-02 now supersedes the transcript half with a real
  selected-thread artifact contract; list-level date/campaign filters remain open.
- This historical slice was frontend-only. PAR-DL-02 later adds the export permission, worker and
  two API resources; the remaining backend conversation-query extensions stay open.
- **Follow-up hardening (same day):** removed the dead Previous-page control (the backend never
  returns `prev_cursor`) in favour of a bounded "Back to newest" reset; disabled the inherited 10s
  poll for the selected conversation's detail and messages via an optional, backward-compatible
  `refetchInterval` override on `useConversation`/`useMessages` (Live Chat and Customer 360 keep
  their existing default); moved focus into the detail pane on narrow viewports and restored it to
  the originating row on return; included the `contact` deep-link filter in active-filter
  detection; matched the status badge to Live Chat's open-only success convention; and added an
  accessible name to the message list plus a page/thread heading pair. Twelve new tests; no
  backend, contract, RBAC or percentage change.

### User Attributes management interface over the existing Custom Attribute contract

- Added a Settings → User Attributes panel over the existing `GET/POST/PATCH/DELETE
  /api/v1/custom-attributes` endpoints. The contract was already complete, but the frontend only
  ever issued the list read consumed by the Contacts filter bar, campaign audience rules and
  segment predicates, so no organization could define a typed field from the product itself.
- Create, edit and delete for `contacts:write` holders; `key_name` and `data_type` are immutable
  after creation, shown as read-only facts in the edit dialog via the same `DefinitionRow`
  pattern Canned Messages already established, rather than disabled controls.
- Search, a data-type filter, and `Indexed`/`PII` shown as informational badges; the delete
  confirmation accurately states that every contact's stored value for the definition is removed
  too.
- Writes invalidate the exact `["custom-attributes"]` cache key the Contacts page already reads,
  plus the campaign/segment picker's key prefix, so a new attribute is selectable in both existing
  pickers without a reload.
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path or generated
  type changed.

### Canned Messages management interface over the existing Quick Reply contract

- Added a Settings → Canned Messages panel over the existing `GET/POST/PATCH/DELETE
  /api/v1/quick-replies` endpoints. The contract was already complete, but the frontend only ever
  issued the list read from the Message Composer's `/shortcut` picker, so the canned-message
  vocabulary could not be populated from the product on a new organization.
- Create, edit and delete for `inbox:write` holders; `shared` (Personal/Shared) is selectable only
  at creation, matching the immutable-after-creation contract, and shown as read-only information in
  the edit dialog rather than offered as a control.
- Search across shortcut/title/body, a scope filter, and a body preview; `usage_count` is read but
  intentionally not shown, since no send path increments it yet.
- Writes invalidate the exact `["quick-replies"]` cache key `MessageComposer.tsx` already reads, so a
  new canned message is selectable from the composer without a reload. A permission-correct link was
  added to the composer's empty state for `inbox:write` agents only.
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path or generated
  type changed.

### Focused Tag Management audit follow-up: regression coverage and accessibility/error-state hardening

- Reset stale `create`/`update`/`delete` mutation state when a dialog opens, so a previous failure
  cannot resurface as a false error in a freshly opened dialog for a different tag.
- Moved the failed-delete error into the confirmation modal itself; it previously rendered behind
  the still-open modal's backdrop and was not genuinely visible at the moment of failure.
- Added regressions for cross-feature cache invalidation (against the real `useTags` hooks already
  used by contact/inbox and campaign/segment/automation pickers, under one shared `QueryClient`, no
  new cache-key system), a duplicate-name conflict, a failed delete with retry, an explicit loading
  state, per-tag accessible row-action names, and a dedicated proof that a failed attempt's error
  does not resurface when a dialog is later opened for a different tag.
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path or generated
  type changed. Settings/Tags/Attributes completion claims are unchanged from the prior remediation.

### Tag management interface (verified UI remediation)

- Added a Settings → Tags panel over the existing tag endpoints. The contract was already complete,
  but the frontend only issued the list read, and attaching a tag requires the id of one that already
  exists — so on a new organization the tag vocabulary could never be populated from the product and
  every shipped tagging surface stayed empty.
- Create, rename, recolour, describe and delete are now available to `contacts:write` holders, with
  search, a usage filter, client-side paging, inline validation, a live preview, and a delete
  confirmation that states how many contacts would be detached.
- Writes invalidate the shared `["tags"]` cache and the campaign picker cache, so a new tag is
  selectable in the existing contact and conversation attach flows without a reload.
- Frontend only: no backend file, migration, endpoint, permission definition, OpenAPI path or
  generated type changed. Module 13, its architecture and its provider boundary are untouched.

### M13-06B Provider-neutral History & Media Control Plane

- Added one provider-neutral service over the existing checkpoint/media-reference persistence; it
  owns no provider call, queue execution, API route, event ingestion, history retrieval or media bytes.
- History checkpoints are feature-gated, permissioned, tenant/object scoped, capability-gated and
  versioned; legal transitions, monotonic progress, cutover/watermark boundaries and restart semantics
  fail closed and emit immutable Audit evidence.
- Provider media identifiers reuse existing `MediaAsset` and `ChannelEndpoint` authorities; registration
  is idempotent, declared media capability is required and factual transfer observations reject secrets.
- Additive migration `0041_channel_sync_control_plane` seeds only `channels:history_sync`; OpenAPI and
  frontend remain unchanged.

### UI-TASTE-05 Owner Review, Release Candidate Audit and Merge Readiness

- Completed a full repository release-candidate audit across product routes, shared components,
  authentication/RBAC, tenant/object authorization evidence, API contracts, audits and Module 13
  provider-neutral boundaries.
- Fixed one verified Major defect: campaign create/edit lazy chunks no longer depend on a cyclic barrel
  re-export that Rollup warned could break execution order.
- Full repository validation passes in workflow `30982637585`; the main application bundle is `199.78/54.87 kB gzip`.
- No feature, architecture, governance, provider, QR, runtime, API, migration, dependency, permission
  catalog or roadmap-sequencing change was made.
- No verified Blocker or Major defect remains in repository-verifiable scope. The branch is ready for
  explicit Owner Approval and Merge, not Host Validated or Production Ready.

### UI-TASTE-04 Responsive, Accessibility and Performance Regression

- Reactivation KYC deep links now reuse the existing `kyc:read` route authority.
- Workspace record search waits 250 ms before issuing bounded permission-scoped requests; empty
  collections retain keyboard index zero and truthful loading feedback.
- Keyboard shortcuts use the shared modal authority; shared modals lock background scroll and shared
  pagination wraps without narrow-screen overflow.
- Authenticated pages and administrative panels load at their route boundaries; the main JavaScript
  bundle measures 199.78/54.87 kB gzip.
- Verified unused `ComingSoonPage` code is removed. No business workflow or route was added.

### UI-TASTE-03B Reactivation Operational Hierarchy

- Real Reactivation CRM is the default route; only connected and permission-available KYC,
  Document, and Report destinations remain in primary Reactivation navigation.
- Existing pipeline search/filters are URL-backed and use shared controls; factual All active,
  Due today, Overdue, and Completed work views preserve refresh/share context.
- Existing tenant-scoped stable ordering now supports additive non-negative offset pagination at
  25 cases per page without a new table, service, route, permission, or authority.
- Historical SIM/Activation/Completed/Interested/bulk links resolve to existing filtered CRM or
  Contact import workflows instead of placeholder operational shells.
- Design Document 34 records reuse, originality, responsive/accessibility, security, validation, and
  host-evidence boundaries.


### M13-06A Provider-neutral Sync & Media Persistence Foundation

- Added inert organization-scoped history checkpoints and endpoint-scoped provider media references from the frozen data model.
- Added bounded progress/count constraints, opaque non-secret cursor metadata, expiry/verification facts, optimistic concurrency and tenant-scoped repositories.
- Extended only the existing capability vocabulary with `history_sync`; no adapter implementation or provider branch exists.
- Additive migration `0040_channel_sync_media_foundation`; no API, generated-contract, queue, dependency or frontend source change.

### M13-05 QR Pairing & Provider Runtime Foundation

- Provider-neutral runtime metadata/lifecycle/event/health contracts and a runtime registry over the existing adapter seam.
- Tenant-scoped runtime registration, discovery and ownership; durable capability observations, health/lifecycle reports, heartbeat, restart policy and recovery metadata on the existing `ChannelSession` authority.
- No-store pairing lifecycle with constrained state/reason/timestamp facts only; no QR payload, image, token, protocol credential or login implementation.
- Lease/fencing and optimistic-concurrency enforcement for runtime reports; holder-specific observations reset safely when runtime ownership changes.
- Disabled-by-default runtime/pairing flags, dedicated permissions, Audit coverage and bounded pairing-expiry processing.
- Additive migration `0039_qr_pairing_provider_runtime_foundation`; no API, generated-contract or frontend source change.

### Preserved M13-01 through M13-04 authorities

- Existing `ChannelAdapter`, provider metadata/capability registries, canonical Contact identity, persistent connection/endpoint/encrypted-secret records and durable session lifecycle/lease/fencing remain authoritative.
- No provider implementation, duplicate persistence authority or shared CRM/message/UI authority was added.

## Validation

- Repository pre-merge quality gate PASS in workflow `31038662241`.
- Ruff and strict mypy PASS; OpenAPI/generated-client drift PASS at 200 paths.
- Full backend regression: 985 PASS; migration head is `0041_channel_sync_control_plane`.
- Frontend ESLint and TypeScript PASS; 36 Vitest files / 671 tests PASS; production build PASS.
- E2E TypeScript, Bandit, Python/frontend/browser dependency audits and tracked-source
  vulnerability/secret/IaC scan PASS.
- Main application bundle remains 199.78/54.87 kB gzip; no frontend or API execution path changed.
- Five focused M13-06B tests cover lifecycle, RBAC/flags, tenant isolation, capability boundaries,
  idempotency, audit, secret rejection and absence of public/provider execution.
- Host/provider certification evidence remains `PENDING – Host Machine Validation`.

## Explicitly absent

QR image generation/scanning, WhatsApp login/protocol, provider adapters, live event ingestion,
provider history retrieval, media-byte transfer/processing, sending, incoming webhooks, routing, Inbox/Customer
360/Analytics changes, public runtime/pairing/sync APIs and provider-specific tables are absent.

## Remaining work

- QR-04 webhook ingestion, QR-05 send path, QR-06 reconnect/health, QR-07 QR frontend, QR-08
  Unified Inbox integration, QR-09 production validation — none started. QR-01 delivered an adapter
  that can probe the WAHA *server*; QR-02 added a read-only session lifecycle mapping; QR-03 added
  QR pairing. Nothing can yet ingest events, send, tear a session down or supervise one, and there
  is still no QR route or UI (QR-07).
- **QR-05 carry-forward (acknowledgement ordering):** physical-phone certification observed
  acknowledgements arriving `DEVICE(2) → SERVER(1) → READ(3)`. Any delivery-state persistence must
  advance monotonically (take the highest state reached); last-write-wins would regress a delivered
  message back to "sent".
- **QR-04 carry-forward (event identity):** the same underlying provider message was delivered as
  both `message` and `message.any` sharing one `envelope.id`. Deduplication keyed on `envelope.id`
  alone would silently drop a genuine event; the key must include the event type. Webhook delivery
  is at-least-once and redelivery repeats both `envelope.id` and `X-Webhook-Request-Id`, so neither
  distinguishes a retry from a first delivery.
- **QR-04 carry-forward (concurrency):** `messages` is partitioned, so DB-level endpoint/provider
  message-id uniqueness cannot be enforced by constraint (MySQL error 1503). Concurrent
  duplicate-event safety must therefore be proven independently — by test, not by schema — before
  QR-04 turns on live webhook ingestion. Partitioning is deliberately not redesigned.
- Physical-phone WAHA certification evidence (paired session reaching `WORKING`, real inbound,
  outbound send, delivery/read acknowledgement, media, history) — the four Required criteria that
  remain PENDING in the selection record.
- Genuine target-host MySQL migration evidence (repository/local-host `docker compose` evidence
  exists for upgrade paths — see `0035a_widen_version_table` remediation — but target-host itself
  remains unvalidated).
- Real-MySQL rollback/downgrade fix at `0036_customer_identity_resolution` and
  `0040_channel_sync_media_foundation` — a verified open defect (`DROP INDEX ... needed in a
  foreign key constraint`), pre-existing and confirmed unrelated to the `0035a` remediation;
  remediation is not part of that fix or this follow-up.
- Automated CI execution of the live-MySQL migration tests (`test_migrations_mysql.py`) — no CI
  pipeline exists in this repository today.
- Real multi-node runtime/lease/fencing contention and stale-runtime recovery validation.
- Runtime supervisor, heartbeat, reconnect/re-authentication and alerting commissioning.
- Production KMS custody for referenced provider credentials.
- Representative tenant/RBAC/feature-flag rollout and operator acceptance.
- Provider certification host evidence and all live M13-06 inbound/history/media execution plus later messaging/operator milestones.

## Stop rule

This rule was written at M13-06B closeout. Its release conditions — "certification **and** a separate
owner instruction" — have both since been met, so it no longer blocks the QR sequence:

- **Certification:** physical-phone WAHA certification PASSED on 2026-08-08.
- **Owner instruction:** the owner authorized QR-01 through QR-04 individually, and QR-01, QR-02,
  QR-03 and QR-04 were delivered under that authorization.

Still gated, and each requiring its own owner instruction: QR-05 send, QR-06 reconnect/health/
teardown, QR-07 provider UI, QR-08 Unified Inbox, QR-09 production validation. Provider history
retrieval and media-byte transfer remain unimplemented. No Production Ready or Host Validated claim
is made, and the WAHA selection record's approval state is unchanged and remains an owner decision.
