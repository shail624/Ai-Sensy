# Changelog

## UI-AIS-21 — Polish: the real font, smooth transitions, dialog and page animation (2026-09-24)

Owner feedback: still not as polished and smooth as AiSensy.

- Root cause of the "unfinished" look: the app asked for the Inter font but never shipped it, so
  Windows fell back to Segoe UI everywhere (`document.fonts` showed nothing loaded). The reference
  uses Roboto (Material) with Inter headings. Both are now bundled locally via `@fontsource/roboto`
  (300/400/500/700) and `@fontsource/inter` (400/500/600) — no external font requests, CSP
  unchanged — and Roboto is the interface font with the reference body tracking (0.00938em),
  Inter for h1/h2. Verified live: Roboto 400/500/700 and Inter 400/600 loaded.
- Smoothness: every button, link, tab, menu item and field eases colour/border/shadow changes
  (160ms, Material curve); buttons give a slight press (scale 0.97); each page fades up into place
  (220ms, keyed by path so query changes do not replay it); dialogs fade their backdrop and grow
  into place with the Material dialog shadow and a larger plain title. All motion is disabled
  under `prefers-reduced-motion`.
- PASS: frontend 1,092 tests, TypeScript, build (fonts emitted as hashed woff2 assets); live font
  check. No backend change.

## UI-AIS-20 — AiSensy audit pass 2: placeholder AI panels removed, Customer page, Developer header (2026-09-24)

- The "AI copilot / Provider not connected" placeholder (with governed-AI wording) is removed from
  Segments, Live Chat's Chat Profile ("AI Assist"), the campaign wizard ("AI planning assistant"),
  Analytics and Reactivation reports. It never worked (no AI provider is connected); the reference
  shows nothing there. The component stays for when a real provider is connected.
- Customer page: "Single customer identity / Persisted since" → "Customer since …" and "Details
  last updated …"; "Engagement facts … no synthetic score" → "Activity" with "Last message from /
  to customer"; the internal WhatsApp identity and record-version rows removed. Basic information
  now shows Opt-in in words (Yes / No / Not asked yet), **Sale status** (coloured pill) and
  **Release date**.
- Developer Hub: no self-referencing "Back to Developer" link; page titles no longer show a focus
  outline when the page opens.
- PASS: frontend 1,092 tests, TypeScript, ESLint, build; live check of Customer and Segments pages.
  No backend change.

## UI-AIS-19 — Full AiSensy audit, pass 1: shared header, History, Flows, Dashboard, plain copy (2026-09-24)

Owner request: the UI is close to AiSensy but still differs; audit everything and fill the gaps.
Reference pages were viewed read-only in the app browser (nothing changed there).

- Shared page layout (44 pages at once): `PageHeader` is now the reference white top bar (plain
  20px title, short grey line, actions on the right); `PageContainer` uses the reference light-grey
  canvas at full width; breadcrumb trails are gone — a top-level page shows none and a nested page
  shows one "← Back to …" link, as the reference does.
- History: reference three-pane look — search pill + filter/audit icons over an avatar list; the
  empty centre shows the WhatsApp wallpaper with "Select a chat to continue!"; an open chat has the
  teal Live Chat header with the customer's photo and the wallpaper behind messages. Full-height,
  own header. All filters, saved views, export and "Open in Live Chat" unchanged.
- Flows: page renamed "Flow Builder" with a Quick Guide and an Active Flows ring (published / all);
  the "Versioned authoring / Human approval / approval proposals" jargon replaced by one plain
  sentence (flows never message customers on their own).
- Dashboard: "Remaining Quota" (from `/campaigns/messaging-quota`, falls back to the limit) instead
  of "Messaging Limit"; the business profile photo now shows — the CSP `img-src` allows
  `https://pps.whatsapp.net`, WhatsApp's profile-image host (nginx reloaded, `nginx -t` passed).
- Plain language: 20+ remaining technical strings rewritten (governed, immutable, ledger, tenant,
  contract, projection …) across Analytics, Customer 360, Documents, KYC, Reactivation, Scan and
  Operations.
- Not built (AiSensy commercial features with no counterpart here): AI Agent, Ads Manager, WA
  Payments, Integrations marketplace, flow-template gallery, credits/plan/referral cards.
- PASS: frontend 1,092 tests, TypeScript, ESLint, build; live check of History, Flow Builder and
  Dashboard. No backend change.

## CORE-WH-01 — Retry-safe inbound webhook handoff (2026-09-24)

- Meta messages and QR phone echoes are settled only after their inbound task is accepted by the broker. A failed publish stays retryable instead of silently skipping the customer message.
- Broker operational errors use the existing transient retry policy. Signed inbound messages delayed more than 30 seconds before ingress emit a privacy-safe structured warning.
- No schema, API contract or frontend change. This hardens messages that reach our webhook; it cannot recover a message Meta never delivered to it.

## UI-AIS-18 — Messaging tier read from Meta's portfolio-level limit (2026-09-24)

Follow-up to UI-AIS-17: the Campaigns strip showed "Not reported yet" for the tier.

- Root cause (read-only Graph check): Meta no longer returns `messaging_limit_tier` on the phone
  number; the limit moved to the business portfolio and is reported as
  `whatsapp_business_manager_messaging_limit` (here `TIER_10K`, on both the number and the WABA).
- The Meta adapter now requests that field for number health and number sync and uses it when the
  old one is empty (`_messaging_tier`). The connected number was refreshed through the normal
  `PhoneNumberService.refresh` path: GREEN, TIER_10K. The rate gate's tier cap now uses the real
  10K instead of the 1K fallback.
- Live: Campaigns shows Quality High, "Tier 2 (10K/24 Hours)", Remaining Quota 9,999.
- PASS: `test_channels.py` + `test_api_waba.py` 70 (new field test), ruff, mypy. No API shape
  change, no migration.

## UI-AIS-17 — Campaigns list header: quality, tier, remaining quota, reports (2026-09-24)

Owner feedback (screenshot of the reference list): add the quota strip, search bar, tabs, report
buttons and rows-per-page.

- Quota strip above the list (reference layout): Quality Rating pill (High/Medium/Low), Template
  Messaging Tier ("Tier 2 (10K/24 Hours)" etc., or "Not reported yet"), Remaining Quota, and the
  Launch button. New `GET /campaigns/messaging-quota` (`campaigns:read`, declared before
  `/campaigns/{campaign_id}`): per number, tier limit from the rate gate's tier caps, customers sent
  a template from that number in the last 24h, and the remainder — an estimate labelled as such
  (Meta does not report it; sends outside this app are not seen). 256 OpenAPI paths.
- Big "Search by campaign name" bar, Refresh, underline tabs (All · Scheduled · Running ·
  Completed · Drafts), report buttons: Report downloads, **User Report** (pick a campaign → the
  existing per-customer results export), **Overview Report** (campaign totals per day as CSV via
  the analytics report export, delivered to Downloads).
- Table gains the reference 📊 analytics link per row; pagination shows "Rows per page 10/25/50"
  and "1-10 of N".
- Live: Quality shows High (GREEN from Meta); the tier is still empty from Meta for this number,
  so the tier reads "Not reported yet" and quota "—" rather than an invented number.
- PASS: backend 1,835 (full suite), ruff, OpenAPI `--check`; frontend 1,091 tests, TypeScript,
  ESLint, build; live page check. No migration.

## UI-AIS-16 — "Select Campaign Type" on Launch, with CSV Broadcast (2026-09-24)

Owner feedback (screenshot of the reference): Launch should first ask for the campaign type.

- Launch now opens "Select Campaign Type" (reference layout): **Broadcast Campaign** → the
  campaign wizard; **API Campaign** → the Developer page (API key, send endpoint); **CSV
  Broadcast** (NEW) → upload a CSV; **Meta Ads** shown as SOON and disabled (not built — no fake
  flow).
- CSV Broadcast: the file is read in the browser (phone column found by header or by content,
  optional "name" column, header row detected), up to 5,000 numbers. New
  `POST /contacts/resolve-numbers` (`contacts:write`, audited) finds or creates one contact per
  number (10 digits = +91, duplicates collapsed, unreadable rows reported, existing names never
  overwritten, new contacts `source=csv_broadcast`) and returns their ids; the wizard then opens
  with a "Selected contacts" audience, so templates, opt-out protection, approval and scheduling
  all apply as for any campaign. 255 OpenAPI paths.
- PASS: backend 1,833 (full suite), ruff, OpenAPI `--check`; frontend 1,091 tests (CSV parser,
  dialog), TypeScript, ESLint, build; live check of the dialog. No migration.

## UI-AIS-15 — Campaign launch wizard matched to AiSensy (2026-09-24)

Owner request: make the campaign creation page like AiSensy's.

- Reference (viewed read-only, nothing submitted): "Create Campaign" with a Quality Rating /
  Messaging Tier / Remaining Quota strip, three stages Campaign Details · Create Message ·
  Test & Preview, and Campaign Name + Select Audience on the first stage.
- `/campaigns/new` now uses the Manage header ("Create Campaign", Back to campaigns), a sending
  number strip (number, Quality Rating High/Medium/Low, Template Messaging Tier), and a three-stage
  tab bar mapped onto the existing steps (Audience → Campaign Details; Template + Preview → Create
  Message; Schedule + Approval + Confirmation → Test & Preview). The detailed step rail, approval
  gate and "nothing sends before confirmation" behaviour are unchanged.
- Campaign Name moved to the first stage with the audience (validated there); buttons use the
  reference teal styles. Remaining quota is not shown: the platform does not track Meta's live
  24-hour quota, so no number is invented.
- PASS: frontend 1,088 tests (new stage mapping test), TypeScript, ESLint, build; live page check.
  No backend change.

## UI-AIS-14 — Campaigns page matched to AiSensy (2026-09-24)

Owner request: Campaigns / Broadcast page like AiSensy.

- Reference (viewed read-only): header, Quick Guide, "Launch" button, tabs All · Broadcast · API ·
  Scheduled · QRScan, Refresh / Download Report, table Campaign · Type · Created At · Status ·
  Audience, 10 rows per page.
- `/campaigns` now uses the Manage header and a Quick Guide; pill tabs All · Scheduled · Running ·
  Completed · Drafts (server status filter, kept in the URL); Refresh, Report downloads and a teal
  "Launch" button (accessible name "Launch campaign", → the existing create wizard).
- Table restyled to the reference: Campaign · Type (BROADCAST + audience kind) · Created At ·
  Status · Audience (recipients) · Progress · Actions. The wizard, scheduling, detail page and
  saved views are unchanged. QR broadcasts are intentionally not offered (bulk sending over the QR
  number stays prohibited).
- PASS: frontend 1,086 tests, TypeScript, ESLint, build; live page check (no campaigns exist yet,
  so the table itself was verified by tests). No backend change.

## UI-AIS-13 — Contacts page matched to AiSensy, with sale status and release date (2026-09-24)

Owner request: Contacts like AiSensy (list, filter, import) showing sale status and release date.

- Reference (viewed read-only): header, Quick Guide, Filter · Broadcast · Add Contact · Import ·
  Actions, and a wide table (Name, Mobile Number, Tags, Source, Lead Stage, Status, Last Active,
  Created At, Opted In …) with "25 per page".
- Contacts page now uses the Manage header and Quick Guide; buttons Broadcast (→ /broadcasts),
  Add Contact, Import, Actions; sale status tabs (All + 7 statuses) kept in the URL (`?sale=`).
- Table: Name · Mobile Number · Tags · Source · Sale Status (coloured pill) · Release Date ·
  Opted In (Yes/No/Unknown) · Last Active · Created At (reference timestamp format); phone cards
  show the sale pill too. Pagination reads "25 per page · N contacts".
- Backend: `ContactResponse` carries `sale_status` and `release_date`; the contact search/segment
  compiler accepts `sale_status` (text operators) and `release_date` (date operators) rules, so
  segments and campaign audiences can use them too.
- Live check: the Follow-up tab narrows the list to the one customer marked Follow-up
  (release date 25 Sept 2026).
- PASS: backend 1,831 (full suite), ruff, mypy on changed modules, OpenAPI `--check`; frontend
  contacts 76 + buildRules 8 tests, full suite, TypeScript, ESLint, build. No migration.

## UI-AIS-12 — Voice notes and videos play in Live Chat (2026-09-24)

Owner report: a voice note arrived but would not play.

- Root cause: the production Content-Security-Policy allowed `blob:` for images only; `<audio>`
  and `<video>` fell back to `default-src 'self'`, so the browser refused the file
  (MEDIA_ERR_SRC_NOT_SUPPORTED) although the download and the OGG/Opus file were fine.
  `deploy/nginx/nginx.conf` now adds `media-src 'self' blob:` (nginx reloaded, config test passed).
- Hardening: each message file keeps one object URL for the page's lifetime instead of being
  revoked on re-render, so a player never points at a released URL.
- Live check: the inbound 13 KB voice note now loads (duration 5.8 s, no media error).
- PASS: frontend inbox 76 tests, TypeScript, ESLint, build; `nginx -t`. No backend change.

## UI-AIS-11 — Customer photo on official-API chats (2026-09-24)

Owner report: the customer's DP showed on QR chats but not on API chats.

- Meta's Cloud API exposes no profile photos. `WhatsAppQrService.contact_photo` now looks the
  photo up through the QR-connected WhatsApp by the customer's number for every conversation, not
  only QR-owned ones (same privacy as any WhatsApp user who has the number; nothing stored).
  `CustomerAvatar` requests it for all chats. Without a connected QR phone the initial/icon stays.
- Live check: both official-API chats in the list now show the customer's photo.
- PASS: `tests/test_waha_start_chat.py` 14 (new API-chat case), ruff; frontend inbox 76 tests,
  TypeScript, ESLint. No API shape change, no migration. No module percentage change.

## UI-AIS-10 — Remaining Manage pages matched to AiSensy; quieter API/QR badge; stuck template explained (2026-09-24)

Owner request: build Canned Message, Team, Tags, Analytics and Notification Preferences like the
AiSensy reference (viewed read-only), make the API/QR badge less loud, investigate message #2.

- New Manage routes with the reference header and a Quick Guide strip: `/canned-messages`, `/team`,
  `/tags`, `/chat-analytics`, `/notification-preferences`; the Manage menu points to them (the old
  `/settings/*` and `/admin/users` screens still work).
- Canned Messages: search pill, scope filter, Create; table Name (/shortcut) · Type · Text ·
  Visible to · Action (round icons) · Favourite (star, per browser, favourites first).
- Tags: same toolbar and table style (Tag Name · First Message · Customers · Last updated · Action).
- Team Members: summary strip and one card per member (initial, username, Online / last seen /
  never signed in / cannot sign in, role); add, edit and stop/restore sign-in (never yourself or
  the owner).
- Analytics: new `GET /analytics/chat-activity?days=&timezone=` (`analytics:read`, 1-31 days):
  user, business and chatbot messages per day from the ledger (automatic replies identified by
  their system-actor audit), plus chats closed and intervened from the audit trail. Page shows
  totals and bar charts for 7/14/30 days. 254 OpenAPI paths.
- Notification Preferences: sound switch with "Test sound", desktop push switch for this device
  (asks browser permission, explains when blocked), then the existing bell categories.
- Live Chat: API/QR badge made small and quiet (9px tinted label); file previews read
  "📷 Photo / 🎬 Video / 🎧 Audio / 📄 Document" instead of "[image]" (3 stored previews updated).
- Message #2 (template to 9891000010, stuck at `accepted`): sent 01:00:45 with a real wamid, but
  the first Meta webhook reached the platform only at 06:28 (Meta's dashboard test) — the webhook
  subscription did not exist yet, so its sent/delivered/read callbacks were never delivered and
  Meta offers no API to fetch them later. Left unchanged (honest "accepted"); later sends update
  normally. The dead-letter list still holds 14 entries from the pre-setup period.
- PASS: backend 1,829 (full suite), ruff, OpenAPI `--check`; frontend 1,085 tests, TypeScript,
  ESLint, build; live check of all five pages. No migration. No module percentage change.

## UI-AIS-09 — Messages sent from the QR phone shown in Live Chat (2026-09-24)

Owner request (deferred earlier): show messages typed directly on the QR-connected phone.

- WAHA `fromMe` echoes on a QR endpoint are now routed to the message lane instead of being
  settled unread. `MessageService._apply_phone_echo` stores them as **outbound** messages (status
  `sent`, `content.sent_from_phone = true`) in the customer's chat, updating the preview and the
  contact's last-outbound time — no unread count, no 24-hour window, no tags, automations or
  auto-replies, and the business's own push name is never written onto the customer.
- Duplicates: our own sends are echoed too; they are matched by provider id and skipped. A send
  still waiting for its provider id is given up to ~6 s (re-checked in fresh transactions) before
  an echo is treated as phone-sent. Redeliveries (`message` + `message.any`) add nothing.
- Groups, status posts and junk/short addresses are ignored (`ignored_echo`), never turned into
  contacts or dead letters. Phone-sent media goes through the UI-AIS-08 media lane.
- Live Chat labels these bubbles "📱 Sent from phone".
- Replayed today's stored echoes after a DB backup: all 3 were our own sends (duplicates), 1 junk
  test address ignored — nothing duplicated.
- PASS: backend 1,828 (full suite), ruff, OpenAPI `--check`; frontend 1,083 tests, TypeScript,
  ESLint, build. No migration. No module percentage change.

## UI-AIS-09 — Faster Live Chat refresh (2026-09-24)

- Active conversation list, chat details and messages now refresh every 2 seconds instead of 10 seconds. Other inbox consumers and counts retain their prior polling interval; no realtime transport or backend contract changed.
- Locally built and tested; a real Meta API inbound message appeared in the inbox. Provider delivery time is outside this refresh interval.

## UI-AIS-08 — Photos, videos, audio and documents shown inside Live Chat (2026-09-24)

Owner request: attachments showed only as a file name; show them inside the chat like WhatsApp.

- `GET /messages/{id}/media` (`inbox:read`, tenant-scoped through the message): streams the stored
  file with its MIME type, `Cache-Control: private`, `nosniff`; 404 while an inbound file is still
  being fetched. 253 OpenAPI paths.
- QR inbound media: the WAHA webhook now turns `hasMedia` + `media.url` into a media message
  (kind from MIME; only the `/api/files/` path is kept, never the reported host). The existing
  media lane downloads it through the WAHA adapter (`MEDIA_DOWNLOAD` declared,
  `download_attachment` bounded to 100 MB and to WAHA's file store) and links the asset.
  MIME parameters (e.g. `audio/ogg; codecs=opus`) are stripped before validation.
- Chat bubbles: photos inline (tap to enlarge, download), stickers without a bubble, videos and
  voice notes with players, documents as a card with a download button, locations with an
  "Open in Google Maps" link. Photos/videos sit in a thin 3px frame (owner feedback: the thick
  border looked bad). Files load once and are cached; inbound files are retried for a minute.
- Live check: the owner's sent Excel file shows as a download card; photos sent and received on a
  QR chat show inline.
- PASS: backend 1,826 (full suite), ruff, OpenAPI `--check`; frontend 73 files / 1,082 tests,
  TypeScript, ESLint, build. No migration. No module percentage change.

## UI-AIS-07 — Attachments, emoji and location in Live Chat (API and QR) (2026-09-24)

Owner request: both chats had no way to send attachments; add what WhatsApp Web offers —
documents, emoji, music, videos, maps.

- Composer: 😊 emoji picker (built-in set, inserts at the cursor) and 📎 menu — Photos & videos,
  Document, Audio / music, Location. A chosen file shows a preview (thumbnail for photos, name and
  size otherwise); the typed text becomes its caption. Files WhatsApp would refuse (type or size)
  are explained before any upload.
- Files are uploaded to the media library, then sent by `media_asset_id`: the official API uploads
  them to Meta as before; QR chats now send the file inline — WAHA adapter declares `MEDIA`
  (photo → sendImage, MP4 → sendVideo, OGG → sendVoice, everything else → sendFile).
  `accept_endpoint` accepts stored-file media only; templates/interactive stay refused on QR.
  WAHA server tier checked: CORE accepts media sends.
- Location: new `location` send type (`latitude`, `longitude`, optional `name`/`address`) for both
  providers (Meta Graph `location`; WAHA `sendLocation`), `Capability.LOCATION` declared by both.
  The dialog takes "Use my current location", a pasted Google Maps link or coordinates. Previews
  show "📍 <place>".
- Note: uploading needs `media:write` in addition to `messages:send`.
- PASS: backend 1,822 (full suite), ruff, mypy on changed modules, OpenAPI `--check` (252 paths);
  frontend 72 files / 1,078 tests, TypeScript, ESLint, build. Live UI check of the new menu. No
  real file or location sent yet (awaiting owner permission). No migration. No module % change.

## UI-AIS-06 — Sale status, number release date, chat reminders, API/QR badge, easier notes (2026-09-24)

Owner request: mark each customer's sale status from the chat, record the number release date and
be reminded on it, set reminders for a specific date, filter chats by status, see clearly which chat
is API or QR, and reach notes easily.

- Migration `0072_contact_sale_status` (additive): `contacts.sale_status` (Follow-up, Sale reminder,
  Sale in field, Sale confirmed, Sale done, Activated from other, Not interested; check constraint +
  index), `contacts.release_date`, `contacts.release_task_id`. New head 0072. DB backed up first.
- `PATCH /conversations/{id}/sale-details` (`inbox:write`, audited): only sent fields change. A
  release date creates one high-priority reminder task at 10:00 IST, moves it when the date changes
  and cancels it when cleared. Conversation contact now carries `sale_status` and `release_date`.
- `GET /conversations?sale_status=<value|none>` filter (400 on unknown values).
- Due notifications now also cover chat reminders (reminder tasks with a conversation and no case
  reference), titled "Reminder: <customer>" / "Release date today: <customer>".
- Live Chat: a row above each chat with a coloured status dropdown, Release date, Reminder (date,
  time, note → task) and Notes buttons; status tabs under the API/QR filter; status pill on rows;
  bold "API"/"QR" badges on rows and the chat header; profile shows status and release date.
- Notes open by default in the profile, plain wording, yellow note cards, Ctrl+Enter to save.
- Reminder alerts: the app chimes (and shows a desktop notice when allowed) when a reminder falls due.
- PASS: backend 1,813 (full suite), ruff, mypy on changed files, OpenAPI `--check` (252 paths);
  frontend 71 files / 1,072 tests, TypeScript, ESLint, build. Live check: status, release date and
  its task created, moved and cancelled; test data reverted. No module percentage change.

## UI-AIS-05 — WhatsApp QR fixes, new chat, customer photo and name, message alerts, API/QR filter (2026-09-24)

Owner testing of the QR-connected WhatsApp found missing configuration, dead-lettered echoes and
receipts, wrong times, and no way to message a new number, see who a customer is or hear new messages.

- QR setup: WAHA settings added to the production env (secrets generated, never displayed) and the
  omnichannel flags enabled. Live test passed both ways with the approved number.
- Webhooks: own-phone echoes (`fromMe`) are a new `echoes` event type that settles as processed;
  receipts for messages sent from the phone settle as `unmatched_receipt` after 3 tries instead of
  dead-lettering; duplicate-key races are retried as transient.
- Customer name now read from NOWEB `_data.pushName`; list, header, profile and alerts show
  "Name +number" (number enlarged to 13px in the list).
- New chat: `POST /channels/whatsapp-qr/chats` checks the number is on WhatsApp first (10 digits get
  +91), requires `messages:send`. Customer photo: `GET /channels/whatsapp-qr/conversations/{id}/photo`
  (whatsapp.net https only, images only, 2 MB cap, 204 when none) shown via `CustomerAvatar`.
- Times: API naive-UTC timestamps are marked UTC in the client (fixed a 5.5h display shift).
- Message alerts: chime (default on) and optional desktop notification with the customer's name and
  number, on every screen, skipping the chat already open; toggled from a speaker button.
- Live Chat filter "All chats / WhatsApp API / WhatsApp QR" (`channel=official|qr` on
  `GET /conversations`, 400 on other values), kept in the URL and across view tabs.
- Data: an empty test chat (+919100000000) created during testing was soft-deleted.
- PASS: backend 1,809, ruff, OpenAPI `--check` (251 paths); frontend 70 files / 1,066 tests,
  TypeScript, ESLint, production build. No migration. No module percentage change.

## UI-AIS-04 — User Attributes page, plain-language copy, API status on every screen (2026-09-24)

Owner feedback: the app is not user friendly compared with AiSensy — too many technical words — and
the WhatsApp Business API status had disappeared from some screens.

- Manage → User Attributes on its own page (`/user-attributes`, `contacts:read`) in the reference
  layout: search pill, type filter, Add attribute, and a table with a per-row Status switch (activate
  / retire straight from the list) and round edit/delete icons. All typed-attribute capabilities
  (type, choices, required, PII, indexed) are kept.
- Plain language: rewrote the Dashboard's operations copy (~36 strings), eleven page descriptions,
  approval, chat-history and Live Chat hints, and the Scan page badges, replacing phrases such as
  "governed", "authorized tenant", "derived", "SLA" and "authority" with short everyday wording.
  `PageHeader` no longer shows the category eyebrow labels ("Engagement orchestration" etc.).
  Claims were checked against behaviour before rewording (e.g. dashboard numbers do not all
  auto-refresh, so the copy says to press Refresh).
- API status restored everywhere: one shared `ApiStatus` (status + refresh) now sits in the app
  header, every Manage page header and the Live Chat top bar, and shows on narrow screens too
  (compact "API :" form). It had gone missing when those screens dropped the app header, and it
  only showed above 1280px.
- PASS: frontend 67 files / 1,051 tests, TypeScript, ESLint, production build. Backend unchanged
  since UI-AIS-03 (1,792 passed).
- No module percentage change.

## UI-AIS-03 — Manage → Live Chat Settings matched to the AiSensy reference, plus typing indicators and timezone (2026-09-24)

Third Manage page of the reference match. The reference page was only viewed.

- Live Chat Settings has its own page (`/live-chat-settings`, `settings:read`) in the reference
  order: Auto Resolve Chats, read behaviour, Welcome / Off Hours messages side by side with
  Configure dialogs and bubble previews, and day-wise Working Hours. Toggles save immediately (as
  the reference does); times and hours save on a button. The project's extra controls (clear unread
  on open, assignment rule, auto-resolve hours) are kept in the same design. The old
  `/settings/application#inbox-policy` view still works.
- Opt-in Management and Live Chat Settings now share one set of primitives
  (`managePrimitives.tsx`: switch, Configure dialog, bubble preview, button/field styles).
- New: Show Typing Indicators. Policy flag `show_typing_indicators` (default off, no migration — it
  lives in the validated policy JSON); `POST /api/v1/conversations/{id}/typing` (`inbox:write`)
  sends Meta's read-status-with-typing against the newest inbound message. It is best effort and
  never errors for provider reasons, and it only fires while read receipts are also on, because
  Meta pairs it with a read tick. The composer signals at most once per 20s on Meta threads.
- New: the workspace timezone is editable from this page through the existing audited organization
  update, from the browser's IANA zone list.
- Fixed before it shipped: the Opt-in page and the combined settings form resend the whole policy
  and would have silently reset the new typing flag; both now carry it through (caught by types).
- PASS: backend Ruff, strict mypy (332 files), full suite 1,792 passed, 0 failed; OpenAPI 249 paths,
  no drift; frontend 67 files / 1,050 tests, TypeScript, ESLint, production build.
- PENDING – live check of "typing…" on a customer's phone, once Meta WhatsApp is reconnected.
- No module percentage change.

## UI-AIS-02 — Manage → Opt-in Management matched to the AiSensy reference (2026-09-24)

Second Manage page of the screen-by-screen reference match (UI-AIS-01). The reference was only
viewed; its Configure dialog was opened and cancelled.

- Opt-in Management now has its own page (`/opt-in`, `settings:read`) with the reference layout:
  60px `ManagePageHeader`, a consent switch card, then Opt-out and Opt-in cards with one 200x42
  field per keyword, Add more, Save Settings, and a Configure (pencil) dialog at 959px whose saved
  text shows in a WhatsApp-bubble preview. The old `/settings/application#consent` view still works.
- Same data and endpoint as before (the inbox operations policy); a save sends every non-consent
  field back unchanged, verified by test. Validation is identical to the combined form's.
- Fixed: this project's `rounded-lg` is 12px while the reference uses 8px; the new Dashboard, Live
  Chat and Opt-in surfaces now use 8px.
- Not built (no backend capability, so not faked): API Campaign Opt-out toggle, template-based
  responses, and the Opt-in/out report download. The reference's guide and promo cards are its own
  content.
- PASS: frontend 65 files / 1,040 tests, TypeScript, ESLint, production build. Backend unchanged
  since UI-AIS-01 (1,786 passed).
- No module percentage change.

## UI-AIS-01 — Dashboard, Live Chat and the Manage column matched to the AiSensy reference (2026-09-24)

The owner asked for the app to match the logged-in AiSensy reference screen by screen. Each screen
was measured in a real browser at 1440px (computed sizes, colours, fonts, radii, shadows, transitions)
against the equivalent screen here, then rebuilt and re-measured. The reference was only viewed: its
dialogs were opened and cancelled, one Live Chat conversation was opened with the owner's explicit
permission, nothing was sent, saved or intervened.

- Shell: 70px `#0A474C` rail with 54px items, 20px icons, 10px captions and a 30px white active
  disc; Developer pinned to the rail's bottom block; 60px white header with the business name and a
  live WhatsApp Business API status plus a spinning refresh; canvas `#F7F7F7`; `shadow-card` token.
- Dashboard: API-status / quality / messaging-limit card with (i) tooltips, setup checklist as
  accordions (NEXT open by default) driven by real WABA/template/contact/campaign facts, WABA
  profile card with category, copy-link, inline View Profile and a pencil Edit Business Profile dialog;
  quick actions; the existing operations desk kept below as "Today's work".
- New backend capability: `GET`/`POST /api/v1/phone-numbers/{id}/business-profile` reads and writes
  Meta's WhatsApp Business profile live (never stored, so no migration); validation mirrors Meta's
  limits and rejects before calling Meta; writes need `waba:manage` and are audited as
  `phone_number.profile_updated`. OpenAPI 247 -> 248 paths, TypeScript types regenerated.
- Live Chat: app header hidden on desktop; 380 / 650 / 340 panes; grey search pill and 860px Filters
  dialog (Discard restores the pre-dialog filters); 50px tabs with a sliding 3px indicator, landing on
  Active; quick switcher of waiting chats; 60px rows; beige chat wallpaper; teal thread header with
  back arrow; reference bubbles, receipts and day chips; Chat Profile always beside the thread on wide
  screens with a facts card and Tags/Notes/AI accordions.
- Manage (first slice): the rail's Manage opens the first Manage destination, as the reference does,
  and the Manage column now matches it (261px, 20px title, 40px items with 5px radius, mint active
  state); Notification Preferences moved into the Manage list in the reference's order. Template
  Message is the first Manage page matched: its own 60px `ManagePageHeader` with Create Template,
  a 300x40 search pill, Sync Status, and All / Draft / Pending / Approved / Action Required tabs
  (Action Required groups rejected, paused and disabled). The reference's template gallery, quick
  guide and AI launch cards are its own content and were not reproduced. The other Manage pages
  are still to be matched one by one.
- Fixed along the way: a `waba:write` permission that does not exist (Connect/Edit never showed),
  Tailwind arbitrary `var()` shadows silently compiling to nothing, modal width overrides losing to
  `max-w-lg`, collapsed accordion links staying in the tab order, and a dev proxy that resolved
  `localhost` to a WSL relay instead of Docker.
- Not built (no backend source, so not faked): billing/plan/credits cards, Refer/Affiliate, Ads,
  Payments, the reference's MAU/opt-in/lead-stage/customer-journey profile rows and Block Incoming.
- PENDING – visual check of an open Live Chat conversation against real data (the local database has
  none until Meta WhatsApp is reconnected); covered by component tests meanwhile.
- PASS: frontend 64 files / 1,035 tests, TypeScript, ESLint, production build; backend Ruff, strict
  mypy (332 files), full suite 1,786 passed, 0 failed in 6:50; OpenAPI drift check clean at 248 paths.
- No module percentage change: presentation and one read/write profile capability, recorded here
  for the owner to judge rather than self-scored.

## REVIEW-02 — integrating the 16-commit `codex/rel-02-local-certification` branch (2026-09-23)

Reviewed and integrated the 16 commits left unmerged after REVIEW-01 (CORE-10, CORE-12–15,
UI-REF-11–18, ACCEPT-01, ACCEPT-02, REL-02A): read every changed line, reproduced anything
suspicious against real infrastructure, ran every gate. Resolved a genuine migration collision
(rel-02's own `0070_tag_first_message_rules` renamed to `0071`, re-chained onto WABA-01's
`0070_phone_quality_unknown`, applied cleanly to real MySQL). Found and fixed one bug: CORE-15's
claimed "Download Center advances 90% → 92%" was never applied to `MODULE_STATUS.md`'s own
percentage table. Kept ACCEPT-01's real finding (a `head→base→head` MySQL migration-reversibility
defect across ~20 already-applied migrations, independently re-reproduced here) but did not merge
its fix, which rewrote those applied migration files directly — forbidden outright by
`REPOSITORY_RULES.md`. Everything else checked out: PASS Ruff, strict mypy (332 files), TypeScript,
ESLint, full frontend (63 files / 1,024 tests), production build; full backend suite **1,782
passed, 0 failed** in 10:54, OpenAPI drift check clean at 247 paths.

## WABA-01 — a real WABA hit a bug the test suite had no way to catch (2026-09-23)

The owner connected a real Meta WhatsApp Business Account (`Vi Reactivation Team`,
`1061162763007187`) and reported it directly: full sync got stuck the moment a second number
(`8527928506`, still `PENDING` in Meta) was in the batch, reporting the trigger as its `UNKNOWN`
quality rating. Investigated the same way this session investigates everything — read the code path
first, then reproduce the exact failure against real MySQL before writing a line of fix — rather than
guessing from the symptom.

### The bug

`ck_phone_quality` permitted exactly `GREEN`, `YELLOW`, `RED`, or `NULL`. Meta's WhatsApp Cloud API
reports a fourth value, `UNKNOWN`, for a number that has not sent enough messages yet for a quality
score to exist — the normal state for a number just added to a WABA, which is precisely when an
operator is most likely to sync. `WabaService.run_sync` applies every number Meta reports in memory,
then flushes the **whole batch in one write** (Doc 06 idempotent-sync pattern). So the one number
Meta had not rated yet did not just fail on its own — it took the *other*, already-healthy number's
update down with it in the same flush, which is exactly "full sync stuck" as reported: nothing in
that sync round committed, GREEN update included.

Reproduced against live MySQL before any fix existed, through the real ORM path (not raw SQL) with
the owner's own two numbers standing in: `(3819, "Check constraint 'ck_phone_numbers_ck_phone_quality'
is violated.")`. No existing test exercised `quality_rating="UNKNOWN"` anywhere in the suite — this
is the same shape as this session's other runtime-only defects: the suite passed throughout, and
only a real account exposed it.

### The fix

Migration `0070` widens the constraint to include `UNKNOWN`; downgrade nulls the value on affected
rows rather than deleting the phone-number record itself — the row is real, only the rating value
the newer migration allowed is not. Verified up → down → up against live MySQL: downgrade preserved
the row (`id` and `phone_number_id` intact) and nulled only `quality_rating`; re-upgrade restored the
wider constraint. Two more sites carried the same stale three-value list and were widened to match:
`QUALITY_RATINGS` in `app/models/waba.py` (unused by any validator today, but the same "what values
can this hold" fact stated twice and left to drift, the same class of gap DEPLOY-01 and REVIEW-01
already found and fixed elsewhere in this codebase) and, functionally this time, the frontend's own
`QUALITY_RATINGS` in `features/channels/types.ts` — which drives a real `<select>` filter and a URL
query-param validator (`NumberList.tsx`), so before this fix an operator could never filter their
number list to `UNKNOWN` numbers even after the backend accepted them. `QUALITY_EXPLANATIONS` and
`WhatsAppOverview`'s `qualityLabel` gained a fourth case ("Scoring", distinct from "Not rated" —
Meta actively withholding a score is a different fact than the platform never having heard one) so
the new value reads as "still counting," never presented beside `RED`'s "something is wrong."
`isNumberHealthy`/the backend's own `healthy` computation already treat anything but `RED` as ready,
so `UNKNOWN` was correctly healthy the moment it could be stored — neither needed changing.

## REVIEW-01 — auditing the work merged directly to `main` (2026-09-23)

The owner reported substantial development had happened through a different tool while this
session was between turns. `git fetch` confirmed it: `origin/main` had moved six commits past this
branch's last commit (GSHEET-02, UI-REF-06 through UI-REF-10), authored on the owner's own machine,
and 22 more `codex/*` branches existed remotely, one of them (`codex/rel-02-local-certification`)
16 commits further still — CORE-12 through CORE-15, UI-REF-11 through UI-REF-18, ACCEPT-01/02 and
REL-02A — none of it merged.

This branch was a clean ancestor of `origin/main` (`git merge-base --is-ancestor` confirmed it, zero
divergent commits), so it was fast-forwarded rather than merged, keeping one linear history.

### What six commits' worth of work actually did

GSHEET-02 added Google Sheets as a real export destination: a new migration (`0069`), a
retry-safe write path (a resumed job clears and rewrites its own tab rather than appending, so a
retry after a shrinking result set cannot leave stale trailing rows — verified by reading, not
assumed, against `ensure_export_tab`'s `:clear` call), and `RAW` value semantics so a contact name
cannot become a spreadsheet formula. UI-REF-06 through UI-REF-10 closed the five differences this
session's own UI-REF-05 had recorded as outstanding (filter icon, list collapse, filled search
button, empty-state artwork, conversation-pane texture) plus navigation, contacts-actions and
campaign-list parity against the supplied capture archive.

The work was reviewed the same way this session reviews its own: read every changed line rather
than trusting the commit message, reproduce anything suspicious before calling it a defect, and run
every gate. Backend **1,773 passed, 0 failed, 0 skipped** (was 1,761 at GSHEET-02's own commit — no
regression); frontend **1,018 passed, 0 failed** before this milestone's own fix; ruff, strict mypy
(332 files) and ESLint all clean. The governance ledgers' own claims were checked against the
repository rather than trusted: 247 OpenAPI paths and migration head `0069` are both exactly what
GSHEET-02's entry says.

### Two defects found, both fixed here

**The Filters button's active-filter count was inert — invisible and inaudible.** UI-REF-06 moved
the "Filters" text to an icon plus a static `aria-label="Filters"`, and wrapped the previously
visible count in a `sr-only` span. `aria-label`, when present, is the *entire* accessible name a
browser computes for an element — nothing in its content contributes anything once it is set,
sr-only or not. So the count regressed for both audiences at once: nothing to see, nothing to hear.
Proved with a hermetic probe before touching anything: `getByRole("button", { name: "Filters" })`
resolved regardless of an active filter, and the rendered accessible name never contained the digit
that was plainly sitting in the DOM beside it. UI-REF-06's own new test never caught it because it
only exercised zero active filters, the one case where the missing span renders nothing at all.

Fixed by making the label itself carry the count (`"Filters, 1 active"`) and adding a small visible
badge — the same `absolute`/`ring-2 ring-surface` pattern TopNav's unread-notification dot already
uses, reused rather than re-invented, marked `aria-hidden` so it is decoration, not a duplicate
announcement. A regression test asserts the count-aware name directly; stashing the fix and
re-running it first confirmed the test fails against the pre-fix file with exactly this button
unfindable by that name, before confirming it passes with the fix restored.

**A stale comment claimed a scope the code no longer had.** `google_sheets_scope`'s doc comment
still read "Read-only by intent... narrower scope is the one to request" directly above a value
GSHEET-02 had already widened from `spreadsheets.readonly` to full `spreadsheets` — a change that is
not optional decoration but a hard requirement: `ensure_export_tab`'s `batchUpdate` and
`write_rows`'s `PUT` both 403 under the readonly scope, so export could not have worked without it.
`.env.example` was updated correctly in the same commit (Viewer → Editor); only the settings comment
was left telling a reader the opposite of what ships. Rewritten to state the current, correct
requirement and point at the two calls that need it, so a future reader auditing OAuth scope width
(the kind of review this owner's own standing instruction asks for) finds the right answer in the
one place they would look.

### Checked, not a live bug, recorded so it is not re-discovered as a surprise

`BulkActionDialog`'s `ready` boolean falls through to `selectedTags.length > 0` for every mode
except `set_attributes`, including `export` — reachable in principle if `selectedTags` were ever
non-empty while `mode === "export"`. It is not reachable today: the tag-selection checkboxes that
populate `selectedTags` render only under `mode === "add_tags" || "remove_tags"`, the dialog is a
real `aria-modal="true"` `Modal` with a focus trap, and every caller changes `mode` by setting it to
`null` first (an unmount, since the dialog only renders when `mode` is truthy) before setting a new
mode, so `useState`'s initial `[]` always applies on the next open. Confirmed by reading
`BulkActionsBar.tsx` and `ContactsActions.tsx`, not assumed. Worth a follow-up cleanup to an
exhaustive per-mode match rather than an OR-chain with an implicit default, but not urgent, and nothing
here writes to it changed to remove that shape.

The campaign list's new `role="tablist"`/`role="tab"` pair (UI-REF-09) does not implement the full
ARIA APG Tabs keyboard idiom (arrow-key roving focus) — click and Tab-key activation both work, and
the new test exercises exactly that, so this is a completeness gap against the pattern's full
specification, not a defect axe-core or the existing test would catch.

REL-02A (unmerged, in `codex/rel-02-local-certification`) adds `apk upgrade --no-cache` to both
Dockerfiles after their digest-pinned `FROM`, trading some of digest-pinning's own reproducibility
for currently-patched packages — a real tension, resolved and honestly documented in
`docs/adr/0022-patch-pinned-runtime-images-at-build.md` rather than silently traded away: the SBOM
and final image digest become the release's reproducibility anchor instead of the base digest alone.
Noted here for visibility; it is unmerged and this session made no changes to it.

### What is still outstanding

`codex/rel-02-local-certification` (16 commits: CORE-12 through CORE-15, UI-REF-11 through
UI-REF-18, ACCEPT-01/02, REL-02A) has not been reviewed at the same depth this entry gives the six
merged commits — it was surveyed at the commit-message and file-stat level only. Reviewing or
merging it is the owner's call, made explicitly, not something this session did on its own
initiative.
## REL-02A — Local release certification (2026-09-21)

Closed the local production-security blocker by applying current Alpine security updates in both
digest-pinned runtime images. Added a disposable-gate-only auth allowance for the hard-navigation
accessibility crawler while preserving the production default. PASS: full deployed profile,
1,782 backend tests, 1,022 frontend tests, source/dependency/image scans, SBOMs, production image
contracts, five browser journeys, Redis degradation, log correlation and 6.1 ms p95 canary.

## ACCEPT-02 — Authenticated local browser matrix (2026-09-21)

Validated the application with repository-owned representative fixtures on the disposable local
MySQL/Redis stack. Dashboard, Live Chat, Chat History, Contacts, Campaigns, Analytics, Download
Center, Automation, Tags and Developer Hub loaded under a real Owner session. Desktop and 390×844
mobile checks passed with no document-level horizontal overflow; conversation list/detail drill-in
worked at both breakpoints. No product code change was required.

## ACCEPT-01 — MySQL migration reversibility, finding kept and fix not merged (2026-09-21, revised 2026-09-23)

Validated the complete migration chain on disposable MySQL 8 and found a real defect: ~20
already-applied migrations drop a foreign-key-backing index before the table that needs it during
`downgrade()`, which MySQL enforces and SQLite never did. The proposed fix rewrote those applied
migration files directly — forbidden outright by `REPOSITORY_RULES.md`'s additive-migration
invariant. REVIEW-02 reverted the twenty file edits and the regression test built on top of them
(it would fail again against the restored files), and recorded the gap in PROJECT_STATE.md instead
of merging a rule violation. No code from this milestone ships; the diagnosis is preserved.

## UI-REF-18 — Developer API Keys focus (2026-09-21)

Compared the authenticated Developer Hub and made the direct credential entry a focused Developer
Hub with Project API keys context and a Create API key action. Existing one-time secret, scopes,
expiry, state, rotation/revocation and audit behavior remains intact. API campaigns, outbound
project webhooks and a competing documentation contract were not faked. PASS: focused 103 and full
frontend 1,022 tests, TypeScript, ESLint and production build.

## UI-REF-17 — Notification Preferences focus (2026-09-21)

Compared the authenticated Notification Preferences screen and promoted the existing real per-user
notification-category controls into a dedicated personal settings workspace. The advanced
server-synced preference store remains available below the primary controls. Unsupported sound,
push and device enrolment were not faked. PASS: focused 139 and full frontend 1,022 tests,
TypeScript, ESLint and production build.

## UI-REF-16 — Tags first-message column (2026-09-21)

Compared the authenticated Tags workspace and separated Tag name and First message into clear table
columns. Each row now exposes its real first-message rule state and exact-match count while existing
usage, editing, deletion and permission behavior remains intact. Unsupported categories/groups and
excluded launch or billing surfaces were not faked. PASS: focused 130 and full frontend 1,022 tests,
TypeScript, ESLint and production build.

## UI-REF-15 — Team Management focus (2026-09-21)

Compared the authenticated Team Members workflow and aligned the existing governed user workspace
around a direct Team Members heading, task description and Add team member creation action. Custom
roles, permission gates, enable/disable safeguards and account concurrency remain intact. Paid seat
quota, billing, launch cards, invitations and SSO were not faked. PASS: focused 72 and full frontend
1,022 tests, TypeScript, ESLint and production build.

## UI-REF-14 — Canned Message preview (2026-09-21)

Compared the authenticated New Canned Message workflow and added a truthful live preview of the
message body. Existing shortcut, title and personal/shared scope remain intact, and the empty state
clarifies that selecting a saved reply inserts text without sending. Unsupported media types and
gated variable substitution were not faked. PASS: focused 130 and full frontend 1,021 tests,
TypeScript, ESLint and production build.

## UI-REF-13 — User Attributes focus (2026-09-21)

Compared the authenticated User Attributes screen and aligned the existing typed contact-field
workspace around a compact search, type-filter and Add attribute toolbar. Creation language and
table headings now follow the observed task hierarchy while richer validation, lifecycle and
security facts remain intact. The Meta Lead Form-specific tab was not faked. PASS: focused 130 and
full frontend 1,021 tests, TypeScript, ESLint and production build.

## UI-REF-12 — Live Chat Settings focus (2026-09-21)

Compared the authenticated reference and made the existing Live Chat policy a dedicated Manage
workspace. Read-state controls, welcome/off-hours replies, working hours and auto-resolution remain
one real server-owned policy, while unrelated routing, consent and generic advanced controls are
hidden at this deep link. Unsupported typing indicators and excluded launch shortcuts were not
faked. PASS: focused 130 and full frontend 1,021 tests, TypeScript, ESLint and production build.

## UI-REF-11 — Opt-in Management focus (2026-09-21)

Compared the authenticated AiSensy Opt-in Management workflow and made the existing consent controls
a dedicated Manage workspace. Opt-in/out keywords, independent acknowledgement toggles, editable
customer previews and the single governed save action now carry the same clear hierarchy without
copying excluded ads, premium reports or unsupported API-campaign controls. PASS: focused 129 and
full frontend 1,020 tests, TypeScript, ESLint and production build. No backend or contract delta.

## CORE-10 — Chat History reference acceptance (2026-09-20)

Reconciled the complete existing Chat History workflow against the authenticated reference. Added
the missing compact contact-avatar hierarchy and stronger selected-row emphasis without inventing
a message-count fact the API does not provide. PASS: focused Chat History 41, full frontend 1,020,
focused backend history/transcript/fixture regression 48, static analysis and production build. No
backend, API, migration or permission delta.

## CORE-15 — Download Center retention authorization (2026-09-20)

Reconciled the previously delivered unified Download Center instead of rebuilding it. Signed export
links are now capped by durable artifact retention, and the public signature-authenticated download
target rechecks retention so an already-issued link cannot outlive the artifact. No API, migration
or frontend change was required. PASS: focused backend 63, full backend 1,769 with 6 MySQL-only
skips, and full frontend 1,020 plus static checks/build. The same 6 Redis-dependent campaign tests
remain host-environment failures.

## CORE-14 — governed provider read receipts (2026-09-20)

Added an independent organization policy for provider read receipts, a capability-gated Meta Cloud
implementation, and retry-safe inbox orchestration that never reports local success after provider
failure. Existing business-hours, automatic-reply and shared unread behavior remains intact.
OpenAPI remains 247 paths and no migration is required. PASS: focused backend 59, focused frontend
108, full frontend 1,020, static analysis and production build. Full backend passed 1,767 with 6
MySQL-only skips; 6 pre-existing Redis-dependent campaign tests remain host-environment failures.

## CORE-13 — first-message tag rules (2026-09-20)

Added exact-match first-message rules to organization tags. Matching the first accepted inbound
text now attaches configured contact tags through the canonical tag authority, maintains usage,
timeline and audit records, and records a deterministic effect on the existing business-event
ledger. Migration head is `0071_tag_first_message_rules`; OpenAPI remains 247 paths. PASS: focused
backend 52, focused frontend 191, full frontend 1,020, static analysis and production build. The
full backend run passed 1,763 with 6 MySQL-only skips; its one milestone-owned deployment-head
assertion was corrected and passed on rerun, while 6 pre-existing Redis-dependent campaign tests
remain host-environment failures.

## CORE-12 — consent keyword acknowledgements (2026-09-20)

Added independently configurable opt-in and opt-out acknowledgement messages to the existing
inbound consent-keyword evaluator. Consent is recorded before provider delivery, duplicate webhook
processing recovers the same durable reply, and the opt-out bypass is restricted to the withdrawal
acknowledgement itself. OpenAPI remains 247 paths. PASS: focused backend 43, focused frontend 105,
full frontend 1,019, Ruff, strict mypy, TypeScript, ESLint and production build. The full backend
run passed 1,762 with 6 MySQL-only skips; 6 pre-existing Redis-dependent campaign tests failed
because Redis was unavailable on this host.

## UI-REF-10 — Template creation focus (2026-09-20)

Kept the existing template editor and live preview visually primary by moving the Vi AI template
helper into an accessible, closed-by-default optional disclosure. No template capability was
removed and TTL/billing surfaces were not invented. PASS: 1,018 frontend tests, TypeScript,
ESLint and production build.

## UI-REF-09 — Campaign list controls (2026-09-20)

Aligned the Campaign list's supported interactions with the authenticated reference: truthful
All/Scheduled status shortcuts, explicit refresh, permission-aware campaign report-download
history, and a single Launch campaign action. Existing search/status/sort, saved views and
execution behavior are unchanged; unsupported Broadcast/API/QR tabs were not fabricated. PASS:
1,017 frontend tests, TypeScript, ESLint and production build.

## UI-REF-08 — Contacts actions and export discovery (2026-09-20)

Added a permission-aware Contacts Actions menu matching the observed workflow: operators can
export the complete current filtered view without first selecting rows and open the existing
Download Center as export history. Selection-only edits remain in the bulk bar; no fake Lists,
ads or import-history surface was added. PASS: 1,016 frontend tests, TypeScript, ESLint and build.

## UI-REF-07 — daily navigation parity (2026-09-20)

Compared the authenticated reference navigation and moved two existing, permitted capabilities
into the daily rail: Segments beside Contacts and a permission-gated Developer entry to the real
API credential surface. Added reduced-motion-safe rail width animation and clearer Manage-panel
separation. No fake AI/List tab or excluded commercial surface was introduced. PASS: 1,013
frontend tests, TypeScript, ESLint and production build.

## GSHEET-02 — queued contact export to a new Sheet tab (2026-09-20)

Added Google Sheets as a governed destination in the existing contact export workflow. Each queued
job creates a new dated, job-owned tab and streams the filtered contact set in bounded batches;
retries reuse only that tab and never overwrite an operator tab. Migration head is 0069; OpenAPI
remains 247 paths. PASS: 1,761 applicable backend tests and 1,013 frontend tests. Live Google,
Redis and MySQL host evidence remains pending.

## UI-REF-06 — Live Chat controls and empty states (2026-09-20)

Closed the five empty-screen differences recorded by UI-REF-05 with original implementation:
compact accessible filtering, a filled search action, desktop list collapse/restore, an original
empty-list graphic and an original token-driven conversation ground. Existing Inbox behavior and
all excluded-surface boundaries are unchanged. PASS: 1,012 frontend tests, TypeScript, ESLint and
production build. Authenticated populated visual acceptance remains pending.

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

All notable changes to **frozen** design documents and (later) released modules are recorded
here. Frozen documents are not edited silently; any change to a frozen document must be
logged as an entry below, with date, document, rationale, and the nature of the change.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project
will adopt semantic-ish versioning per document (e.g., `SRS v1.1`) once changes occur.

---

## [Unreleased]

### UI-REF-02 — Live Chat shell (2026-09-13)

- Reference-order Active / Requesting / Intervened strip with search above the workspace;
  empty desktop view separates conversation list, thread area and profile placeholder.
- Existing filter/search/assignment/save/bulk/message authorities preserved; no invented counts.
- Frontend 883/883, types/build, lint and desktop/mobile preview pass. Full populated Live Chat
  parity and production validation remain pending. Design Document 73 records exact boundaries.
- No backend/API/migration change, commit, push or deployment; no module percentage increase.

### UI-REF-01 — Screenshot-aligned navigation (2026-09-13)

- Labelled 84px rail and reference-order daily tabs; persistent adjacent Manage replaces overlay.
- Direct, permission-aware template/consent/chat-policy/attribute/reply/team/tag/analytics entries.
  Vi tools remain reachable. Settings uses its active heading without duplicate desktop tabs.
- Policy links focus existing controls; backend saves/permissions are unchanged. Owner screenshot
  direction and outstanding differences recorded in Design Document 72 and scope/rules.
- Frontend 882/882, types/lint/build and bounded desktop/mobile preview pass. Two optional-array
  typing errors in unfinished segment tests corrected without weakening assertions.
- Local only: full screen parity, cumulative backend/release revalidation and production
  acceptance remain pending. No commit, push or deployment; no module percentage increase.

### 2026-09-13 — PAR-VIEW-05: Governed Report Saved Views

Extends the shared workspace-view authority to Reports without adding a parallel store. One exact
period preset or complete custom range, day/week granularity and optional previous-period comparison
can be saved privately or permission-published to the tenant. Report tab, export format, schedule/
progress state and other transient state are excluded. Applying a definition uses the existing
Analytics URL contract, preserving the backend report-query authority.

Adds `analytics:views_manage`, `report_view.created/deleted`, typed list/create/delete APIs,
private/team chips and a responsive `Save / manage` sheet with plain-language visibility,
permission truth, grouped management, API errors and deliberate deletion. Existing Analytics
queries, export jobs, report schedules, Download Center and Notification authorities remain
unchanged.

Migration `0061_reports_workspace_views` advances one linear head to **62 revisions**. OpenAPI
advances **233 → 235 paths** with synchronized generated TypeScript. Focused backend contracts pass
**12/12**, focused Analytics UI passes **41/41**, full frontend passes **47 files / 875 tests**, and
full backend passes **1579 with 6 MySQL-only skips and zero failures in 413.35s**. Static **6/6**, strict mypy
across **322 source files**, OpenAPI drift and Vite **8.2.2** build pass. An authenticated isolated
local desktop and 390-pixel mobile preview verified the team view and responsive sheet with factual
empty report metrics. Executive Reports advances **75% → 80%**, Saved Views **85% → 95%**, and full
scope **76.5% → 77.0%** with median **86% → 88%**. Remaining `GROW-03` work is the Segment predicate/
saved-filter slice; representative-data WCAG/scale, revenue/ROI/attribution, Docker/security and
target-host release gates remain pending. No send/provider/customer/commit/push/release/deployment
action occurred.

### 2026-08-26 — PAR-VIEW-04: Governed KYC Saved Views

Extends the shared workspace-view authority to KYC without adding a parallel store. Trimmed customer
search and one validated lifecycle status can be saved privately or permission-published to the
tenant; fetch bounds, selected case, checklist, documents, appointments, SLA/detail and decision
state are excluded. KYC search/status are now URL-backed so reloads and shared links reproduce the
same server-evaluated queue while clearing only transient case selection.

Adds `kyc:views_manage`, `kyc_view.created/deleted`, typed list/create/delete APIs, lock/team chips
and a responsive `Save / manage` sheet with plain-language visibility, permission truth, grouped
management, API errors and confirmed deletion. Existing case mutation, protected-document, Task,
reviewer/manager decision, Audit and Reactivation handoff authorities remain unchanged.

Migration `0060_kyc_workspace_views` advances one linear head to **61 revisions**. OpenAPI advances
**231 → 233 paths** with synchronized generated TypeScript. Focused API/migration/OpenAPI contracts
pass **12/12**, focused KYC UI passes **2 files / 8 tests**, and full frontend passes **46 files /
870 tests**. Full backend passes **1574 with 6 MySQL-only skips and zero failures in
450.05s**. Static **6/6**, strict mypy across **321 source files**, OpenAPI drift
and Vite **8.2.2** build pass. KYC advances **85% → 90%**, Saved Views **75% → 85%**, API **98% →
99%**, and full scope **76.0% → 76.5%** with median **86%**. Reports views, remaining segment
predicates, protected-media/scale/browser commissioning and target-host release gates remain
pending; no send/provider/customer/commit/push/release/deployment action occurred.

### 2026-08-26 — PAR-VIEW-03: Governed Campaign Saved Views

Extends the shared workspace-view authority to Campaigns without adding a parallel store. Trimmed
search, validated lifecycle status and list sort can be saved privately or permission-published to
the tenant; local page number is excluded. Workspace-aware lookups, counts, names, indexes and
uniqueness isolate Campaign definitions from Contacts and Reactivation. The existing per-scope caps,
organization lock, private-user/tenant boundaries and immutable Audit evidence remain shared.

Adds `campaigns:views_manage`, `campaign_view.created/deleted`, typed list/create/delete APIs,
lock/team chips and a responsive `Save / manage` sheet with plain-language visibility, permission
truth, grouped management, API errors and confirmed deletion. Applying a definition returns to page
one through the existing URL contract; recipient paging, dispatch, lifecycle and result-export
authorities remain unchanged.

Migration `0059_campaign_workspace_views` advances one linear head to **60 revisions**. OpenAPI
advances **229 → 231 paths** with synchronized generated TypeScript. Focused saved-view backend
passes **16/16**, migration **5/5**, focused Campaign UI **54/54**, and full frontend **45 files /
866 tests**. Full backend passes **1569 with 6 MySQL-only skips and zero failures in 395.87s**.
Static **6/6**, strict mypy across **320 source files**, OpenAPI drift and Vite **8.2.2** build pass.
Campaigns advances **94% → 95%**, Saved Views **65% → 75%**, API **97% → 98%**, and
full scope **75.6% → 76.0%** with median **86%**. Authenticated browser/WCAG/device validation,
KYC/Reports views, remaining segment predicates, attribution/revenue/ROI and target-host
commissioning remain pending; no send/provider/customer/release action occurred.

### 2026-08-24 — PAR-VIEW-02: Governed Contacts Saved Views

Extends the Reactivation saved-view store into one governed workspace-view authority and integrates
Contacts without creating a second persistence model. Search, tag UUID and enum custom-attribute
selections can be private or permission-published to the tenant; cursor position is excluded.
Workspace-aware lookups, counts, names, indexes and uniqueness isolate Contacts from Reactivation.
The existing per-scope caps, organization lock, private-user/tenant boundaries and immutable Audit
evidence remain shared.

Adds `contacts:views_manage`, `contact_view.created/deleted`, typed list/create/delete APIs, lock/team
chips and a responsive `Save / manage` sheet with plain-language visibility, permission truth,
grouped management, API errors and confirmed deletion. Applying a definition intentionally drops
stale paging while the existing server search, bulk actions and export rule audience remain the
authorities.

Migration `0058_contacts_workspace_views` advances one linear head to **59 revisions** and preserves
existing rows as workspace `reactivation`. OpenAPI advances **227 → 229 paths** with synchronized
generated TypeScript. Focused backend passes **16/16**, focused UI **19/19**, full backend **1564
passed / 6 MySQL-only skipped / 0 failed in 506.04s**, and full frontend **44 files / 863 tests**.
Static **6/6**, strict mypy across **319 source files**, OpenAPI drift and Vite **8.2.2** build pass.
Contacts advances **95% → 98%**, Saved Views **55% → 65%**, API **96% → 97%**, and full scope
**75.2% → 75.6%** with median **86%**. In-app local visual access was denied, so authenticated
browser/WCAG/device validation and target-host commissioning remain pending; no provider/customer/
release action occurred.

### 2026-08-24 — PAR-VIEW-01: Governed Reactivation Saved Views

Adds tenant-scoped personal and team-shared views over the existing Reactivation filter contract.
Every Reactivation reader may save/delete private definitions; `reactivation:views_manage` governs
team publishing and deletion. Readers receive every shared view plus only their own private views;
foreign tenants and another user's private UUIDs remain hidden. Names are case-insensitively unique
inside their scope, private/shared caps are enforced under an organization lock, invalid filters fail
validation, database checks constrain display/visibility, and create/delete mutations are audited.

The existing work-view/filter/URL/board/list/pagination behavior is preserved. Saved chips identify
private versus team definitions, and an accessible `Save / manage` sheet provides plain-language
visibility, permission truth, grouped management, errors and deliberate deletion confirmation.
Applying a view restores portable filters and board/list mode without stale page position.

Migration `0057_reactivation_saved_views` advances one linear head to **58 revisions**. Three API
operations advance OpenAPI to **227 paths** with synchronized generated TypeScript. Focused backend
passes **13/13**, Reactivation UI **12/12**, full backend **1559 passed / 6 MySQL-only skipped / 0
failed in 459.36s**, and full frontend **43 files / 860 tests**. Strict mypy across **317 source
files**, changed-file Ruff, OpenAPI drift, frontend lint/types and Vite **8.2.2** build pass.
Reactivation advances **94% → 96%**, Saved Views **42% → 55%**, API **95% → 96%**, and full scope
**74.7% → 75.2%** with median **86%**. Other module views, campaign attribution/revenue/ROI and
host commissioning remain pending; no provider/customer/release action occurred.

### 2026-08-24 — PAR-CAM-01: Campaign Recipient Failure Operations

Replaces Campaign Detail's first-page-only recipient filter with an operational view over the
complete persisted roster. The existing recipient endpoint now declares exact `status`, bounded
`limit` and `cursor` parameters, emits a total-aware page envelope and keeps top-level `has_more`
for v1 compatibility. The generated client can navigate stable `(created_at,id)` keyset pages and
filter on the server rather than discarding unmatched rows from only the first 50.

Recipient rows now carry tenant-safe current contact name/WhatsApp identity, status, safe error
code, retry count and lifecycle timestamps. A corrupt foreign contact reference renders blank
identity; provider/internal message identifiers and internal error detail remain absent. Campaign
Detail adds complete forward/previous navigation, factual totals and shared loading/empty/error/
busy states. Failed-recipient retry now requires an explicit confirmation that states the count and
successful-recipient exclusion while preserving the existing permission, lifecycle, rate, smart-
retry, queue, idempotency and Audit authorities.

Migration `0056_campaign_recipient_operations` adds the two composite indexes matching unfiltered
and status-filtered ledger scans and advances one linear head to **57 revisions**. OpenAPI remains
**225 paths** with synchronized generated TypeScript. Campaign/migration regression passes
**107/107**, focused Campaign UI **51/51**, complete frontend **43 files / 857 tests**, static
**6/6**, strict mypy **314 files** and Vite **8.2.2** production build PASS; Campaigns is
**109.34/28.02 kB gzip**. Complete backend passes **1553 with 6 MySQL-only skips and zero failures
in 476.67s**.
Campaigns advance **90% → 94%** and full scope **74.5% → 74.7%**. The current-table median is
**86%**; this corrects the prior 85% summary and is not counted as additional feature progress.
Conversion/ROI source facts and host commissioning remain pending; no send/provider action occurred.

### 2026-08-24 — PAR-DL-03: Governed Campaign Results Exports

Adds `campaigns:export`-governed full-ledger or recipient-status-filtered result generation for one
tenant-scoped campaign. The worker streams the persisted recipient authority oldest-first in
500-row keyset batches; the browser never mistakes its currently visible roster page for complete
campaign evidence. PDF, CSV, XLSX and JSON artifacts include campaign/current-contact identity,
delivery state, safe error code, retry/cost and lifecycle timestamps while excluding provider and
message IDs, variable payloads, internal error detail and storage/provider references.

No parallel artifact system is introduced: campaign results reuse the existing export row, queue,
retry discipline, hardened/formula-safe writers, storage provider, expiry, signed links and audit
events. Campaign Detail gains an original responsive format/status/progress/download sheet. The
personal Download Center adds a permission-filtered Campaign results family, and navigation/route
entitlement recognizes the new permission.

Migration `0055_campaign_results_exports` adds only the permission and preserves one linear
**56-revision** head. Start/progress bring OpenAPI to **225 paths**; generated TypeScript and the
**32-task** source image contract are synchronized. Campaign/export backend passes **106/106**,
provider/OpenAPI/smoke/image regression **32/32**, migration **5/5**, and focused Campaign/Download/
navigation UI **63/63**. Complete backend passes **1552 with 6 MySQL-only skips and zero failures
in 475.58s**; complete frontend passes
**42 files / 854 tests**; static **6/6**, strict mypy **314 files** and Vite **8.2.2** production
build pass. Campaigns advance **85% → 90%**, Download Center **80% → 88%**, API **94% → 95%**,
and full scope **74.1% → 74.5%** with an unchanged **85%** median. Conversion/ROI, retry UX,
remaining artifact sources and target-host acceptance remain pending.

### 2026-08-24 — PAR-HIST-01: Advanced Chat History Filters and Shared Views

Adds server-authoritative Chat History filters for effective activity date, campaign membership,
media presence and audited activity. Campaign identifiers are tenant-resolved, date ranges use
inclusive start/exclusive end boundaries, and ledger predicates are evaluated with correlated
existence checks instead of treating the browser's loaded messages as complete history. Audit
filtering remains protected by `audit:read`.

Managers gain `inbox:views_manage` and can create or delete up to 25 organization-scoped team
views with case-insensitive unique names and validated portable filters. Mutations are audited,
tenant isolation is preserved, and audit-scoped views are hidden from users who lose audit access.
The existing personal Live Chat saved-view system is unchanged. Chat History adds an original
responsive advanced-filter sheet, active-filter count, URL persistence and horizontally scrollable
team-view chips.

Migration `0054_chat_history_filters_views` establishes one linear **55-revision** head. The
expanded conversation contract and three shared-view lifecycle resources bring OpenAPI to **223
paths** with synchronized generated TypeScript. Focused API/filter/view tests pass **10/10**,
existing Inbox/conversation/QR regression **77/77**, migration **5/5**, and Chat History UI
**41/41**. Complete backend passes **1547 with 6 MySQL-only skips and zero failures in 458.04s**;
complete frontend passes **41 files /
850 tests**; static **6/6**, strict mypy **314 files**, OpenAPI drift and Vite **8.2.2** production
build pass. Chat History advances **70% → 88%**, Saved Views **35% → 42%**, API **93% → 94%**,
and full scope **73.3% → 74.1%** with an unchanged **85%** median. Authenticated target-host
commissioning and the remaining cross-product roadmap are still pending.

### 2026-08-24 — PAR-DL-02: Governed Chat History Transcript Exports

Adds `inbox:export`-governed complete or date-bounded transcript generation for one selected
persisted conversation. Messages stream oldest-first from the indexed ledger in 500-row keyset
batches; the browser never mistakes its currently loaded pages for complete history. PDF, CSV, XLSX
and JSON artifacts carry factual timestamp/direction/participant/type/content/status/public-ID rows
while excluding provider message/media IDs, private media URLs and internal storage references.
Formula-leading spreadsheet content remains neutralized by the shared export writer.

No parallel artifact system is introduced: transcript jobs reuse the existing export row, `exports`
queue, retry policy, storage provider, expiry, signed links and audit events. Chat History gains an
original responsive export sheet with optional whole-day range, live progress, direct download and
Download Center link. The Center adds a personal `chat_history` category and navigation recognizes
the new entitlement.

Migration `0053_conversation_transcript_exports` adds the permission without a table and preserves
one linear **54-revision** head. Start/progress bring OpenAPI to **221 paths**; generated TypeScript
and the **31-task** source image contract are synchronized. Focused backend passes **35/35** and
focused Chat History/Download/navigation UI **50/50**. Complete backend passes **1537 with 6
MySQL-only skips and zero failures in 445.40s**; complete frontend passes **41 files / 845 tests**;
static **6/6**, strict mypy **310 files** and Vite **8.2.2** production build pass. Chat History
advances **55% → 70%**, Download Center **74% → 80%**, API **92% → 93%**, and full scope
**72.5% → 73.3%** with an unchanged **85%** median. Advanced list filters/saved views, remaining
artifact families, Docker/security rerun and target-host acceptance remain pending.

### 2026-08-24 — PAR-REP-04: Team Productivity and Current Workload

Adds a truthful split between historical productivity flows and current pending-work stock.
Conversation/task event rollups now present teammate throughput together, while a separate bounded
team snapshot counts unresolved/unread conversations and open/overdue/due-today tasks directly from
their operational authorities. Unassigned conversations and inactive owners retaining work are
visible attention cohorts; snapshot values are never added across time.

The governed report catalogue grows from ten to eleven with Team Productivity, reusing
CSV/XLSX/JSON/PDF, schedules, notifications, expiry, signed downloads and Download Center history.
Migration `0052_team_productivity_reports` preserves one linear **53-revision** head. Two named
resources bring OpenAPI to **219 paths** with synchronized generated TypeScript. Focused backend
passes **79 with 6 MySQL-only skips**, focused Analytics UI **36/36**, complete backend **1534
passed / 6 MySQL-only skipped / 0 failed in 367.01s**, complete frontend **41 files / 843 tests**,
static **6/6**, strict mypy **310 files** and production build pass. Revenue/ROI and
campaign attribution remain blocked on approved source facts; capacity utilization is not inferred
without per-person limits. Analytics advances **75% → 82%**, Executive Reports **65% → 75%**,
Download Center **73% → 74%**, Team Management **82% → 86%**, API **91% → 92%**, and full
scope **71.8% → 72.5%** with a recalculated **85%** median.

### 2026-08-24 — PAR-REP-03: Domain Outcome Analytics

Adds a rebuildable domain-outcome rollup derived from immutable Vi business events. Reactivation
creation, stage, terminal turnaround and source; eligibility decisions; KYC decisions/turnaround;
SIM and Activation terminal outcomes; and SLA starts/breaches/resolutions now flow through the
existing timezone, comparison, freshness and tenant-isolation analytics pipeline. Counts and sums
remain additive; rates and averages are calculated only after range aggregation and return unknown
without a denominator.

Analytics gains a responsive Business outcomes tab, lead-source table and formula-backed KPI cards.
The governed report catalogue grows from seven to ten with Reactivation, KYC and Service Levels;
CSV/XLSX/JSON/PDF, personal schedules, ready notifications, expiry, signed downloads and Download
Center history are reused unchanged.

Migration `0051_domain_outcome_analytics` preserves one linear **52-revision** head and OpenAPI grows
to **217 paths** with synchronized generated TypeScript. Focused backend passes **144/144**, focused
Analytics UI **35/35**, complete backend **1532 passed / 6 MySQL-only skipped / 0 failed in
426.19s**, complete frontend **41 files / 842 tests**, static **6/6**, strict mypy **309 files** and
production build pass. Analytics advances **55% → 75%**, Executive Reports **50% →
65%**, Download Center **72% → 73%**, API **90% → 91%**, and full scope **70.6% → 71.8%**.
Revenue/ROI/conversion attribution, workload/capacity, remaining artifact families, Docker/security
release rerun and target-host acceptance remain pending.

### 2026-08-24 — PAR-REP-02: Scheduled Analytics Reports

Adds personal daily, weekly and monthly schedules for the seven existing Analytics report families.
Authorized executives can create, edit, pause, resume and safely delete PDF/Excel/CSV schedules in
an IANA timezone. Due rows are claimed with row locks, permission-rechecked and advanced before the
existing report-export queue creates the artifact; inactive/deleted/revoked owners are disabled.
Completed jobs emit one idempotent `report_ready` Notification Center item that opens the personal
Analytics Download Center filter.

Migration `0050_scheduled_analytics_reports` adds the schedule table and notification constraint,
preserving a single linear **51-revision** head. OpenAPI grows to **214 paths** with synchronized
generated TypeScript and the image contract carries **30** application tasks. Scheduled lifecycle
tests pass **5/5**, combined backend **71/71**, focused Analytics UI **34/34**, complete backend
**1530 passed / 6 MySQL-only skipped / 0 failed in 425.43s**, complete frontend **41 files / 841
tests**, static **6/6**, strict mypy **309 files** and the Vite production build pass. Executive
Reports advance **35% → 50%**, Download Center **70% → 72%**, Notifications **85% → 86%**, API
**89% → 90%**, and full scope **70.0% → 70.6%**. New domain report projections, other artifact
families, optional external delivery and target-host acceptance remain pending.

### 2026-08-24 — PAR-REP-01: Analytics PDF Reports

Adds PDF as a governed fourth format for all seven existing asynchronous analytics report families.
The worker reuses the current rollup query, export job, queue, storage, expiry, signed-artifact and
Download Center authorities; contacts remain intentionally limited to CSV/XLSX/JSON. Paginated
landscape-A4 output has report titles, repeated headers/page numbers, stable table fitting, explicit
empty states and honest micro-unit cost labels.

Migration `0049_report_pdf_exports` widens the existing export-format constraint and preserves a
single linear **50-revision** head. OpenAPI remains **212 paths** with synchronized generated
TypeScript. Focused backend passes **139/139**, focused Analytics/Download UI **36/36**, complete
backend **1525 passed / 6 MySQL-only skipped / 0 failed in 434.13s**, complete frontend **41 files /
839 tests**, static **6/6**, strict mypy **306 files**, current Python dependency audit with no known
vulnerabilities and the Vite production build pass. A
three-page sample passes Poppler page-by-page visual review plus `pdfinfo`/`pypdf` structural and
content checks. Executive Reports advance **25% → 35%**, Download Center **65% → 70%**, and full
scope **69.5% → 70.0%**. Report schedules, new executive/domain metrics and other artifact families
remain pending.

### 2026-08-24 — PAR-DL-01: Unified Download Center

Adds one entitled `/downloads` Tools tab and `GET /api/v1/downloads` projection over the existing
contact/analytics export pipeline. Results are restricted by organization, requesting user and the
operator's current `contacts:export` / `analytics:export` family permissions. Ready artifacts receive
fresh signed links; retained rows whose artifact has expired are normalized to `expired` and never
expose a stale link.

The page provides URL-backed type/status filters, newest-first keyset pagination, row counts,
creation/expiry timestamps, manual refresh, three-second polling while visible work is active, and
complete loading/error/empty/status/action states. No duplicate export table, queue, storage path or
retry authority is introduced.

Download API tests pass **5/5**, corrected path-count/API regression **7/7**, and focused Download/
navigation UI **14/14**. Complete source validation passes **1523 backend / 6 MySQL-only skips /
zero failures in 326.78s**, **41 frontend files / 838 tests**, static **6/6**, strict mypy **306
files**, synchronized **212-path** OpenAPI and Vite production build; `DownloadsPage` is
**7.03/2.50 kB gzip**. No migration, new permission code, queue, storage provider or customer send
is added. PDF, scheduled/executive reports, transcripts, campaign/scan and generated-document
artifacts remain pending, so Download Center advances **30% → 65%** and full scope **68.4% → 69.5%**.

### 2026-08-23 — PAR-AUTO-23: Shared Delay Before Follow-Up

Adds one optional durable Delay immediately before the terminal `After both` action of the exact
bounded Yes/No graph. The selected body checkpoints first, both outcomes converge on one running
Delay attempt, and due resume executes the shared effect exactly once. Early/duplicate delivery
cannot repeat the selected action, Delay attempt or shared domain work; alternate-only nodes remain
durable skipped evidence.

The builder enables `Add shared delay before follow-up` only after a shared action exists, labels
the node `Shared delay`, safely reconnects both outcomes when it is removed and removes the
dependent Delay with its follow-up. Branch-specific Delay/Wait, multiple timers, arbitrary merges,
nested Conditions and external/customer actions remain fail-closed.

Focused live/safe runtime passes **54/54**, Automation/API/trigger/Schedule/migration regression
**77/77**, and focused UI **23/23**. Complete local source validation passes **1524 backend tests in
475.70s**, **40 frontend files / 833 tests**, static **6/6** and production build; `AutomationPage`
is **52.47/13.23 kB gzip**. The Docker/security-backed release profile could not be rerun because
its required approval service exhausted its usage allowance; PAR-AUTO-22's last complete **23/23
in 685.9s** evidence remains preserved and is not attributed to this changed tree. No migration,
route, permission, queue, provider call or customer send is added; Automation remains **99%**.

### 2026-08-23 — PAR-AUTO-22: Bounded Shared Follow-Up

Adds one optional terminal shared follow-up after the exact bounded Yes/No split. Both branch
terminals may converge on one trigger-safe internal effect under the unchanged four-effect ceiling.
The selected branch executes first and the shared node executes once; unselected-only nodes remain
durably skipped, while the shared node is never misclassified as unselected.

The builder exposes an `After` lane with `+ Both`, labels the converged node `After both`, supports
inserting a second branch step before it and preserves the merge when a branch terminal is removed.
Arbitrary/multiple merges, nested/multiple Conditions, longer bodies, branch Delay/Wait, loops and
external/customer actions remain fail-closed.

Focused live/safe runtime passes **51/51**, combined Automation/API/migration regression **78/78**,
and focused UI **22/22**. The exact current tree passes the complete release profile **23/23 in
685.9s**: **1521 backend tests with zero skips**, **40 frontend files / 832 tests**, build, SAST/
dependency/source/image scans, certified WAHA runtime, image contracts and CycloneDX SBOMs.
`AutomationPage` is **50.52/12.77 kB gzip**. No migration, route, permission, queue, provider call
or customer send is added; Automation remains **99%**.

### 2026-08-23 — PAR-AUTO-21: Bounded Multi-Step Branch Bodies

Extends the deterministic live Yes/No split from one terminal effect per side to one or two ordered
distinct internal effects per side, while preserving the existing four-effect ceiling. The selected
branch resumes from durable node checkpoints and every unselected branch node is recorded as
skipped. Same-kind effects remain valid across alternate branches but are rejected within one
selected body.

Safe test mode mirrors the multi-step decision without business effects. The builder exposes a
dedicated Yes/No effect palette while a branch is active, labels second steps, blocks unsafe
reordering and lets an operator remove only the terminal addition or return the graph to a linear
gate. Longer bodies, nested Conditions, branch Delay/Wait, merging, arbitrary fan-out and external/
customer actions remain fail-closed.

Focused live/safe runtime passes **48/48**, combined Automation/API/migration regression **75/75**,
and focused UI **21/21**. The exact current tree passes the complete release profile **23/23 in
609.3s**: **1518 backend tests with zero skips**, **40 frontend files / 831 tests**, build, SAST/
dependency/source/image scans, certified WAHA runtime, image contracts and CycloneDX SBOMs.
`AutomationPage` is **48.38/12.24 kB gzip**. No migration, route, permission, queue, provider call
or customer send is added; Automation remains **99%**.

### 2026-08-23 — PAR-AUTO-20: Bounded Live Yes/No Branch

Adds one deterministic terminal decision split to event-backed live Automation without opening a
general flow engine. An exact Trigger → Condition graph may have one `yes` edge and one `no` edge,
each ending at one already-approved trigger-safe internal effect. The Condition is evaluated once
against immutable privacy-safe input; only the chosen action executes, while the other action is
durably recorded as skipped with the selected branch. Same-kind effects are safe because only one
branch can execute and existing node/domain idempotency protects replay.

Safe test mode follows the same branch without business effects. The builder enables branching only
after exactly Trigger, Condition, Yes action and No action exist, labels both outcomes, locks unsafe
reordering and can return to a linear gate. Multiple/nested branches, branch sequences, Delay/Wait
inside branches, merging and arbitrary fan-out remain fail-closed.

Focused live/safe runtime passes **45/45**, combined Automation/API/migration regression **60/60**,
and focused UI **20/20**. The exact current tree passes the complete release profile **23/23 in
417.8s**: **1515 backend tests with zero skips**, **40 frontend files / 830 tests**, build, SAST/
dependency/source/image scans, certified WAHA runtime, image contracts and CycloneDX SBOMs.
`AutomationPage` is **44.79/11.20 kB gzip**. No migration, route, permission, queue, provider call
or customer send is added; Automation remains **99%**.

### 2026-08-23 — PAR-AUTO-19: Live Lead-Stage Changed Automation

Promotes Lead stage changed from an editor-only trigger/Wait choice to a bounded live Automation
event without creating a second CRM transition authority. The existing immutable
`reactivation.stage.transitioned` fact remains authoritative for stage history, Audit, Timeline and
owner Notification; Automation consumes it as the `lead.stage_changed` alias and receives only
`from_stage`, `to_stage` and the tenant-checked public Contact ID. Private transition reasons and
internal Reactivation identifiers never enter Automation input or effects.

A published path may evaluate Previous/New lead-stage conditions, use the existing Delay or Wait,
and create a Contact-linked Task, apply/remove a tag, or notify the publisher. Task creation does
not fabricate a Conversation. Handoff, Assignment, branches, repeated effects and external or
customer actions remain fail-closed. A same-organization/Contact future stage transition can also
resume the existing durable Wait exactly once; replay, wrong-contact and private-data boundaries
are covered.

Focused live runtime passes **35/35**, combined Automation/Reactivation/migration regression
**56/56**, and focused Automation UI **19/19**. The exact current tree passes the complete release
profile **23/23 in 389.1s**: **1512 backend tests with zero skips**, **40 frontend files / 829
tests**, production build, SAST/dependency/source/image scans, certified WAHA runtime, image
contracts and CycloneDX SBOMs. `AutomationPage` is **42.56/10.49 kB gzip**. Migration head remains
`0048` (**49 revisions**), OpenAPI remains **211 paths**, and no route, permission, queue, provider
operation or customer send is added. Automation remains **99%**.

### 2026-08-23 — REL-CERT-01: Consolidated Production Closure Certification

Closed the release-gate defects found only when the complete current worktree was exercised as one
production candidate. The QR-08 webhook test now owns its dispatched-task fixture instead of
leaking into a developer Redis instance; the live-MySQL migration assertions follow Alembic's
canonical head instead of a stale hard-coded revision; and blank optional WAHA organization IDs
normalize to the intended unconfigured state during production startup. The deployed-stack gate
now supplies every required synthetic secret, rejects those values if they appear in logs, and its
browser journey asserts the current Reactivation and bounded live-Automation contracts.

Upgraded the frontend build/router/test dependency line and resolved every npm advisory. The
blocking frontend audit now covers development/build dependencies as well as runtime dependencies.
The backend production-image contract derives its OpenAPI count from the checked canonical export
and compares the exact set of 29 registered application Celery tasks, so future contract drift
fails with actionable missing/unexpected evidence instead of a stale count.

The final cumulative `deployed` quality profile passes **25/25** in **597.4 seconds** on the exact
tree: Ruff, strict mypy over **305 files**, OpenAPI drift, frontend/browser types, **1510 backend
tests with zero skips**, **40 frontend files / 828 tests**, production build, Bandit, Python/npm
dependency audits (**0 frontend and E2E vulnerabilities**), source vulnerability/secret/IaC scan,
Compose and certified WAHA runtime gates, ten-service release contract, rebuilt backend/frontend
image contracts, image vulnerability scans and CycloneDX SBOMs. A fresh disposable ten-service
stack then passed the real owner browser workflow, dependency-degraded readiness (`503` while Redis
was stopped), correlated structured-log/no-secret checks, and 30 authenticated reads at **5.764 ms
p95** against the **300 ms** budget.

**Boundary:** this is repository and disposable-local-deployment certification for `1.0.0-rc1`.
It does not manufacture target-host TLS/secrets/monitoring/backup-restore/UAT evidence and does not
claim 100% AiSensy-inspired feature parity. The simple unweighted average of the 31 canonical
module estimates is **68.4%** (median **85%**); remaining product and commissioning work stays
explicit in `MODULE_STATUS.md` and `ROADMAP.md`. No commit, push, or live deployment was performed.

### 2026-08-23 — PAR-AUTO-18: Durable Task-Completed Wait

Promotes the existing Task completed Wait choice from safe-test-only simulation to a governed live
same-customer event. Single and bulk Task completion now append one deterministic, privacy-safe
`task.completed` Business Event inside the existing Task/history/Timeline/Audit transaction. The
event is scoped to the owning organization and Contact; retries converge by Task completion
revision, while a genuinely reopened and re-completed Task produces a distinct immutable cycle.

The PAR-AUTO-17 matcher now accepts Message received or Task completed. Wrong-Contact completion,
private Task title/note leakage, duplicate event/worker delivery and unsupported Wait types remain
protected; Lead stage changed stays test-only. No migration, route, permission, queue, provider
operation or customer send is added. Focused contract **4/4**, Task/Wait **53/53**, combined
Automation/Task/API/Notification/KYC **130/130**, focused UI **18/18**, complete frontend **40 files
/ 828 tests**, static gate **6/6**, strict mypy **305 files**, OpenAPI **211 paths** and production
build pass; AutomationPage is **42.56/10.78 kB gzip**. Applicable backend is **1501 passed / 6
MySQL skips / 1 known Redis deselection** in **377.10s**. Automation remains **99%**.

### 2026-08-23 — PAR-AUTO-17: Durable Wait for Event

Promotes the existing Wait for event node from safe-test-only simulation to one bounded live
checkpoint on event-backed Automation paths. The runtime persists one tenant/contact-scoped
subscription for the same customer's future `message.received` Business Event, pauses the original
receipt without a processing lease, and resumes the same pinned run from durable step checkpoints.
A required 60-second-to-30-day timeout is resolved by the existing minute receipt heartbeat; both
matched and timed-out paths continue to a later approved internal effect exactly once.

Migration `0048_automation_wait_subscriptions` adds indexed match/timeout evidence with one row per
run/node. Wrong-tenant/contact, unavailable event types, missing timeouts, terminal or multiple
Waits, Schedule waits, branches and unsupported effects fail closed. No route, permission, queue,
provider configuration or customer send is added. Wait checks pass **3/3**, combined Automation
regression **55/55**, wider Inbox/message/Task regression **112/112**, focused UI **17/17**, and
complete frontend **40 files / 827 tests**. Static profile **6/6**, strict mypy **305 files**,
OpenAPI **211 paths** and production build pass; AutomationPage is **42.50/10.77 kB gzip**.
Applicable backend is **1499 passed / 6 MySQL skips / 1 Redis deselection** in **400.25s**;
the final late-event temporal edge passes **3/3**. Automation remains **99%**.

### 2026-08-23 — PAR-AUTO-16: Durable Live Schedule

Promotes the existing five-field cron Schedule trigger to a fourth bounded live Automation event.
Published flows persist an indexed UTC `next_run_at` calculated in the organization IANA timezone;
disable clears it and enable/republish recompute it. A minute scheduler heartbeat row-locks a
bounded due set, writes one deterministic immutable `schedule` Business Event and exact receipt,
advances past missed slots and relies on existing receipt recovery if enqueueing fails.

The live path is intentionally `Trigger → optional Delay → Notification`: one workspace-only
Notification reaches the active eligible publisher without Contact linkage or customer send.
Conditions and every contact/conversation/external effect fail closed. Migration
`0047_automation_schedule_due` adds only the nullable projection and due index; OpenAPI remains
**211 paths** with regenerated TypeScript. Schedule checks pass **4/4**, Automation combined
**42/42**, wider regression **222/222**, focused UI **16/16**, complete frontend **40 files / 826
tests**, static gate **6/6**, and production build PASS (`AutomationPage` **41.90/10.62 kB gzip**).
Applicable backend is **1496 passed / 6 MySQL skips / 1 Redis deselection** in **376.13s**.
Automation remains **99%**.

### 2026-08-23 — PAR-AUTO-15: Conversation Auto-Resolved Live Follow-up

Promotes the existing immutable `conversation.auto_resolved` Business Event to a third bounded live
Automation trigger. A published flow may create one internal follow-up Task, apply/remove an
existing CRM tag and deliver an internal Notification, optionally behind the approved previous-
status/inactivity-threshold Condition and one durable Delay. Tenant-checked public Contact and
Conversation references are resolved from the event lineage for execution without mutating the
stored event evidence.

Human handoff and Assignment remain rejected before any effect because an auto-resolved
Conversation must not be silently reopened or re-owned. A genuine later inbound message retains the
existing Inbox authority to reopen the thread. The PAR-AUTO-14 receipt scanner and worker perform
dispatch/recovery; no migration, new queue, route, permission, provider operation or customer send
is added. OpenAPI remains **211 paths** with its Trigger enum synchronized to generated TypeScript.

Live runtime passes **29/29**, combined Automation/auto-resolve/trigger/API/scheduler checks pass
**50/50**, and the wider Automation/Inbox/Tasks/Tags/Notifications regression passes **180/180**.
Focused Automation UI passes **15/15**, the complete frontend passes **40 files / 825 tests**, and
static quality passes **6/6** with strict mypy over **305 files**. The production build passes with
`AutomationPage` at **41.33 kB / 10.48 kB gzip**. The clean applicable backend is **1492 passed / 6
MySQL skips / 1 known Redis deselection** in **212.83s**; the unchanged Redis-only environmental
case remains separately recorded. Automation remains **99%** while adding a third live event.

### 2026-08-23 — PAR-AUTO-14: Contact Created Live Consumer and Receipt Recovery

Promotes the existing durable `contact.created` receipt from evidence-only storage to a bounded
live Automation path. A published Contact Created trigger may now execute Apply tag, Remove tag and
internal Notification, optionally behind the approved source/opt-in Condition and one durable
Delay. Conversation-dependent Handoff, Create task and Assignment effects fail closed before any
effect because a newly created Contact does not yet own a Conversation.

A minute scheduler on the existing `scheduler.tick` queue now row-locks received receipts and
genuinely stale processing receipts, then hands them to the existing idempotent Automation worker.
New receipts receive a processing lease before dispatch; stale rows retain their old lease so the
consumer can distinguish recovery from concurrent work. A Delay-paused receipt has no processing
lease and remains owned by its already-scheduled resume task, so the scanner does not flood it.
No migration, route, permission, queue, provider operation or customer send is added.

Live runtime passes **26/26**, focused trigger/scheduler/runtime checks pass **35/35**, and the wider
Automation/Tasks/Tags/Notifications regression passes **175/175**. Focused Automation UI passes
**14/14**, the complete frontend passes **40 files / 824 tests**, and static quality passes **6/6**
with strict mypy over **305 files** and OpenAPI at **211 paths**. The production build passes with
`AutomationPage` at **40.93 kB / 10.39 kB gzip**. Canonical execution preserves **1489 passes / 6
MySQL skips / 1 known unavailable-Redis failure**; the clean applicable suite is **1489 passed / 6
MySQL skips / 1 Redis deselection** in **217.62s**. Automation remains **99%** while expanding its
live event evidence.

### 2026-08-23 — PAR-AUTO-13: Durable Live Delay

Activates the existing Delay builder node for bounded live inbound execution. One published Delay
of 60 seconds to 30 days may appear within an otherwise supported linear sequence of up to four
distinct internal effects. The runtime stores one running Delay attempt with its resume time,
schedules the same receipt task on the existing Automation queue, and cannot execute downstream
effects before the deadline. Early or duplicate deliveries converge on that same checkpoint;
completed upstream effects are not repeated when the run resumes.

A false approved Condition skips the Delay and every effect without scheduling continuation.
Multiple delays, branches, Wait-for-event nodes, repeated effect kinds, larger sequences and
external/customer-facing actions still fail closed. No migration, API path, permission, queue,
provider operation, customer send or parallel timer authority is added.

Live runtime and scheduling pass **22/22**, wider Automation/Tasks/Tags/Notifications regression
passes **166/166**, focused Automation UI passes **13/13**, and the complete frontend passes **40
files / 823 tests**. Static quality passes **6/6** with strict mypy over **305 files**; OpenAPI
remains **211 paths**, migration head remains `0046` (**47 revisions**), and the production build
passes with `AutomationPage` at **40.53 kB / 10.33 kB gzip**. Canonical backend is **1485 passed /
6 MySQL skips / 1 known unavailable-Redis failure**; applicable backend is **1485 passed / 6 MySQL
skips / 1 Redis deselection**. Automation advances **98% → 99%**.

### 2026-08-22 — PAR-AUTO-12: Bounded Sequential Effect Runtime

Adds ordered multi-effect execution without turning the bounded inbound consumer into a general
workflow engine. An exact `message.received` Trigger may now run one to four distinct Human
handoff, Create task, Apply tag, Remove tag, Assignment or internal Notification effects in the
published edge order, optionally behind the existing privacy-safe Condition.

Completed node attempts are durable checkpoints. A worker interruption resumes at the first
incomplete effect, while each existing domain idempotency contract prevents duplicate handoffs,
Tasks, tag evidence, assignments or notifications. A false Condition records every effect as
skipped. Branches, repeated effect kinds, more than four effects, delays/waits, external actions and
unsupported nodes fail closed before any effect begins. No migration, API path, permission, queue,
provider action, customer send or parallel effect authority is added.

Live runtime passes **19/19**, combined Automation/Tasks/Tags/Notifications/migration regression
passes **88/88**, focused Automation UI passes **12/12**, and the full frontend passes **40 files /
822 tests**. Static quality passes **6/6** with strict mypy over **305 files**; OpenAPI remains **211
paths**, migration head remains `0046` (**47 revisions**), and the production build passes with
`AutomationPage` at **40.17 kB / 10.23 kB gzip**. Canonical backend is **1482 passed / 6 MySQL
skips / 1 known unavailable-Redis failure**; applicable backend is **1482 passed / 6 MySQL skips /
1 Redis deselection**. Automation advances **96% → 98%**.

### 2026-08-22 — PAR-AUTO-11: Live Internal Notification Executor

Implements governed live internal notification delivery for exact `Trigger → Notification` and
`Trigger → Condition → Notification` graphs. The published message is delivered once to the active
automation publisher through the existing Contact-linked Notification Center. Publisher activity,
same-tenant ownership and effective `tasks:read` access are revalidated at execution. No email,
browser push, WhatsApp/customer message, provider action, route, permission or parallel delivery
store is added.

Migration `0046_automation_notifications` extends the existing Notification type constraint with
`automation_attention` and is reversible. Receipt/node deduplication makes crash replay an
`already_delivered` no-op; a conflicting key fails closed. A false privacy-safe Condition writes no
delivery. Runtime is **15/15**, combined Notification/migration regression **23/23**, static quality
**6/6**, strict mypy **305 files**, OpenAPI **211 paths**, and canonical backend **1478 passed / 6
MySQL skips / 1 known unavailable-Redis failure**. Applicable backend is **1478 passed / 6 MySQL
skips / 1 Redis deselection**.

Frontend ESLint and TypeScript pass, focused Automation/Notification checks pass **14/14**, and the
full frontend passes **40 files / 821 tests**. The production build passes with `AutomationPage` at
**40.08 kB / 10.20 kB gzip**. Automation advances **94% → 96%**.

### 2026-08-21 — PAR-AUTO-10: Live Remove Tag Executor

Adds governed live CRM tag removal to the automatic inbound runtime. Exact
`Trigger → Remove tag` and `Trigger → Condition → Remove tag` graphs now detach the immutable
published tag from the inbound Contact through the existing tenant-scoped Tag service,
`contact_tags`, usage counter, Contact Timeline and Audit authorities. No parallel tag store,
route, permission, queue, provider action, customer send or migration is added.

The Contact and Tag rows are locked before the association decision. A new removal commits one
`tag_removed` Timeline event and one `contact.untagged` system Audit entry. An already-absent tag is
a successful no-op. Crash replay therefore cannot duplicate the association change, counter
decrement, Timeline event or Audit record. A false privacy-safe Condition records Remove tag as
skipped and leaves the existing association untouched.

Live runtime passes **13/13** and combined runtime/Tag regression passes **45/45**. Full frontend
passes **40 files / 821 tests**, focused Automation **11/11**, static quality **6/6** with strict
mypy over **305 files**, and the production build passes (`AutomationPage` **39.68 kB / 10.12 kB
gzip**). OpenAPI remains **211 paths** and migration head remains `0045` (**46 revisions**).
Canonical backend is **1476 passed / 6 MySQL skips / 1 known unavailable-Redis failure**;
applicable backend is **1476 passed / 6 MySQL skips / 1 Redis deselection**. Automation advances
**92% → 94%**.

Multiple effects/general branching, waits/delays, notification/campaign/webhook/customer-message
executors, other event consumers and complete retry/DLQ/reconciliation operations remain future
PAR-AUTO scope.

### 2026-08-21 — PAR-AUTO-09: Live Assignment Executor

Adds governed live Conversation assignment to the automatic inbound runtime. Exact
`Trigger → Assignment` and `Trigger → Condition → Assignment` graphs now support a published
specific user or deterministic per-flow round-robin selection. Execution reuses the existing
Conversation owner, active organization User, effective `inbox:read` eligibility and Audit
authorities. No assignment table, route, permission, queue, provider action, customer send or
migration is added.

The Conversation is tenant-resolved and row-locked before mutation. A specific user must remain an
active eligible Inbox member; round robin uses durable flow-receipt order over a stable eligible-user
order. Any existing manual or automatic owner wins, so Automation never steals the conversation. A
new assignment and one system `conversation.assigned` Audit record commit together. Crash replay
settles as `already_assigned` without a second mutation, row-version bump or Audit entry. An
unmatched privacy-safe Condition records the action as skipped with no ownership effect.

Live runtime passes **11/11** and combined Automation/Inbox regression passes **45/45**. Full
frontend passes **40 files / 820 tests**, focused Automation **10/10**, static quality **6/6** with
strict mypy over **305 files**, and the production build passes (`AutomationPage` **38.91 kB / 10.05
kB gzip**). OpenAPI remains **211 paths** and migration head remains `0045` (**46 revisions**).
Canonical backend is **1474 passed / 6 MySQL skips / 1 known unavailable-Redis failure**;
applicable backend is **1474 passed / 6 MySQL skips / 1 Redis deselection**. Automation advances
**88% → 92%**.

Multiple effects/general branching, waits/delays, Remove tag, notification/campaign/webhook/
customer-message executors, other event consumers, team presence/capacity/skill routing and
complete retry/DLQ/reconciliation operations remain future PAR-AUTO scope.

### 2026-08-21 — PAR-AUTO-08: Live Apply Tag Executor

Adds the second internal live effect to the automatic inbound runtime. Exact
`Trigger → Apply tag` and `Trigger → Condition → Apply tag` graphs now attach the immutable
published CRM tag to the inbound Contact through the existing tenant-scoped Tag service,
`contact_tags`, usage counter, Contact Timeline and Audit authorities. Automated writes carry
system Audit attribution and no user impersonation. No parallel tag store, route, permission,
queue, provider action, customer send or migration is added.

Contact and Tag rows are locked during attachment, and multi-tag writes lock tags in stable order.
Concurrent receipts and crash replay converge on one association, counter increment, Timeline
event and Audit entry. An already-present tag completes successfully as a truthful no-op; an
unmatched privacy-safe Condition records the step as skipped and writes no CRM effect. Missing,
deleted, malformed or foreign references fail closed inside the receipt tenant.

Live runtime passes **9/9** and runtime plus Tag/bulk-tag regression passes **32/32**. Full frontend
passes **40 files / 819 tests**, focused Automation **9/9**, static quality **6/6** with strict mypy
over **305 files**, and the production build passes (`AutomationPage` **37.93 kB / 9.84 kB gzip**).
OpenAPI remains **211 paths** and migration head remains `0045` (**46 revisions**). Canonical backend
is **1472 passed / 6 MySQL skips / 1 known unavailable-Redis failure**; applicable backend is **1472
passed / 6 MySQL skips / 1 Redis deselection**. Automation advances **84% → 88%**.

Remove tag, multiple effects/general branching, waits/delays, assignment/notification/campaign/
webhook/customer-message executors, other event consumers and complete retry/DLQ/reconciliation
operations remain future PAR-AUTO scope.

### 2026-08-21 — PAR-AUTO-07: Live Create Task Executor

Adds the first internal work effect to the automatic inbound runtime. Exact
`Trigger → Create task` and `Trigger → Condition → Create task` graphs now create a real,
tenant-scoped Task linked to the inbound Contact and Conversation through the existing Task,
history, Contact Timeline and Audit authorities. The active automation publisher is the assignee;
title, existing Task type, priority and a 5-minute-to-365-day due delay are immutable published
inputs. No parallel task store, route, permission, queue, provider action or customer send is added.

Receipt UUID is the Task idempotency key and a canonical command hash binds the pinned version,
node, linked records, due time and assignee. A crash after Task commit but before attempt completion
recovers the same Task; a changed replay fails closed. The existing privacy-safe Condition can skip
the action with truthful no-effect evidence. The builder exposes the four supported Task fields and
explains publisher assignment; safe test mode remains side-effect-free.

Live runtime passes **7/7**, existing Task API regression **45/45**, full frontend **40 files / 818
tests**, focused Automation **8/8**, static quality **6/6** with strict mypy over **305 files**, and
the production build passes (`AutomationPage` **37.59 kB / 9.76 kB gzip**). OpenAPI remains **211
paths** and migration head remains `0045` (**46 revisions**). Canonical backend is **1470 passed / 6
MySQL skips / 1 known unavailable-Redis failure**; applicable backend is **1470 passed / 6 MySQL
skips / 1 Redis deselection**. Automation advances **80% → 84%**.

General branching, waits/delays, tag/notification/customer-message executors, other event consumers
and complete retry/DLQ/reconciliation operations remain future PAR-AUTO scope.

### 2026-08-21 — PAR-AUTO-06: Privacy-Safe Live Conditions

Extends the automatic inbound handoff runtime with one optional governed decision. Exact
`Trigger → Condition → Human handoff` graphs may evaluate only `event_type`, `source`,
`payload.direction` or `payload.message_type` using `eq`, `ne`, `contains` or `exists`. A match
continues through the existing idempotent handoff; a non-match completes without changing the
Conversation and records the handoff as `skipped`. Private identifiers, arbitrary fields,
numeric comparisons and every unsupported graph still fail closed before an effect.

Migration `0045_automation_live_conditions` expands durable attempt evidence with the truthful
`skipped` terminal state (46 revisions). The builder suggests live-safe metadata, preserves broader
test-only authoring and explains the boundary. Run evidence distinguishes a no-effect decision from
a completed handoff. No API path, permission, queue, provider action, customer send or second Inbox
state machine is added; OpenAPI remains **211 paths**.

Conditional runtime and migration checks pass **10/10**; full frontend passes **40 files / 818
tests**, focused Automation **8/8**, static quality **6/6** with strict mypy over **305 files**, and
the production build passes (`AutomationPage` **35.98 kB / 9.43 kB gzip**). Canonical backend is
**1468 passed / 6 MySQL skips / 1 known unavailable-Redis failure**; applicable backend is **1468
passed / 6 MySQL skips / 1 Redis deselection**. Automation advances **76% → 80%**.

General branching, multiple conditions, waits/delays, task/tag/notification/customer-message
executors, other live event consumers and complete retry/DLQ/reconciliation operations remain
future PAR-AUTO scope.

### 2026-08-21 — PAR-AUTO-05: Automatic Inbound Handoff Runtime

Closes the evidence-only gap for the first supported live path. Every newly accepted inbound
message now records a privacy-safe `message.received` Business Event and matching receipts inside
the Message/Conversation transaction. Post-commit dispatch uses each receipt's UUID, and duplicate
webhook delivery recovers only received or genuinely stale processing work.

Migration `0044_automation_live_handoff_runtime` expands AutomationRun mode to `test|live`, gives
receipts a one-run link and `received → processing → processed|failed` evidence, and adds a bounded
processing lease. The consumer pins the immutable version and executes only exact
`Trigger → Human handoff` graphs. It records trigger and handoff attempts, reuses the existing
idempotent handoff/Live Chat authority, and fails every unsupported graph closed without applying a
business effect. Message body, provider message ID, phone/name and credentials never enter the
Business Event or run input.

Automation's original workspace now presents one live/test Run history, step evidence and actual
receipt state with bounded polling. Safe test runs remain simulated. OpenAPI stays at **211 paths**
with regenerated TypeScript; migration head is `0044` (**45 revisions**). Focused Automation/Inbox
regression is **40/40**, full frontend is **40 files / 817 tests**, static quality is **6/6 PASS**
with strict mypy over **305 files**, and the production build passes (`AutomationPage` **35.10 kB /
9.16 kB gzip**). The canonical backend records **1465 passes / 6 MySQL skips / 1 known unavailable-
Redis failure**; the applicable rerun is **1465 passed / 6 MySQL skips / 1 Redis deselection**.

No API path, permission code, provider action, customer send or second Inbox state machine is
added. Conditions/branching, waits/delays, other live event types and executors, customer-message
actions, and full retry/DLQ/reconciliation operations remain future PAR-AUTO scope.

### 2026-08-21 — PAR-AUTO-04: Governed Automation Human Handoff

Adds the first bounded live automation effect without converting the deterministic test runtime
into a general production flow engine. Automation definitions gain a typed `Human handoff` node
with an immutable 1–160-character reason. The original builder exposes the node as a `Live
contract`; authoring and publication remain versioned, while every safe test run continues to
simulate the step without changing a business record or sending a customer message.

`POST /automations/{automation_id}/handoffs` requires `automations:publish`, a UUID
`Idempotency-Key`, a conversation and a handoff node from the clean active immutable version. The
body cannot override the published reason. The service performs a same-tenant row-locked decision:
unassigned open/resolved/snoozed conversations move to existing `pending`; an already requested or
human-owned chat is preserved; historical resolved ownership is cleared before requeue. The normal
Intervene/owner-only Resolve lifecycle remains the sole agent ownership authority.

A deterministic `conversation.handoff_requested` Business Event plus tamper-evident
`automation.handoff_requested` Audit entry commit atomically with any status/assignment change.
First execution returns `201`; replay returns `200` with the same event identity. An old replay
after an agent intervenes cannot requeue or unassign the chat, and a recorded replay remains
readable after later automation edit/disable while new executions fail closed. No customer message,
phone/name, credential or provider value enters the event payload.

OpenAPI advances **210 → 211 paths** with regenerated TypeScript. Automation/Inbox focused backend
coverage passes **76 tests**; focused authoring plus handoff coverage is **14/14**. The complete
frontend passes **40 files / 817 tests**, static quality is **6/6 PASS** with strict mypy over **304
files**, and production build passes (`AutomationPage` **34.64 kB / 9.04 kB gzip**). The applicable
backend suite passes **1462 tests / 6 MySQL skips / 1 known Redis-dependent deselection**.

No migration, new permission code, queue, provider action, customer send or second Inbox state
machine is added. Automatic trigger-receipt consumption, general live flow execution/checkpoints,
retry/DLQ operations, waits and all other action executors remain future PAR-AUTO scope.

### 2026-08-21 — AiSensy-style navigation and Live Chat intervention follow-up

Makes the daily product structure immediately visible without copying competitor branding or
assets. New workspaces now open with an expanded named sidebar; Dashboard, Live Chat, Chat History,
Campaigns, Contacts, Automation and Analytics remain visible, while Templates, audiences,
channels, Vi operations and administration are organized under a permission-aware `Manage`
section. The compact rail remains an explicit user preference.

Live Chat now presents the familiar `Requested`, `Active` and `Intervened` views over existing real
server facts: `pending`, `open`, and `open` assigned to the current user. The workflow is now
executable: `Intervene` row-locks and claims one request for the current agent, an attempted second
claim fails without stealing ownership, winning retries are idempotent, and only that owner may
`Resolve`. The owner rule also protects the legacy generic status route, so it cannot bypass the
dedicated action. Existing status, assignment and Audit records remain authoritative.

The two permission-scoped action routes take OpenAPI from **208 to 210 paths**; canonical JSON and
generated TypeScript are synchronized. No migration, permission code, new lifecycle state, queue,
provider or dispatch authority is added. Intervention backend checks pass **24/24**, combined path/
runtime regression **26/26**, focused intervention/thread frontend checks **37/37**, and the complete
frontend passes **40 files / 816 tests** with ESLint, TypeScript and production build. The applicable
backend suite passes **1457 tests / 6 MySQL skips / 1 known Redis-dependent deselection**; Ruff,
strict mypy (302 files), OpenAPI drift and static quality remain green.

Automatic trigger consumption/general chatbot execution, SLA badges, authenticated representative-
data browser/accessibility comparison and target-host concurrency remain pending.
The local and AiSensy reference sessions still stop at sign-in, so no authenticated visual-match
claim is made.

### 2026-08-21 — CORE-11C: Inactivity Auto-Resolve

Extends the validated Inbox Operations policy with an opt-in inactivity timer bounded from 1 to
720 hours. The existing minute scheduler scans at most 100 candidates per organization and reuses
Conversation state/activity, open Task links, Audit, Business Event and the P0 `scheduler.tick`
queue. No migration, new API path, permission, queue or parallel workflow authority is added.

Only read, inactive open/pending conversations qualify. Resolved, snoozed, unread, recent and open-
Task conversations are protected. Every candidate is row-locked and rechecked; successful changes
advance the Conversation version, append system Audit evidence and emit one deterministic
`conversation.auto_resolved` fact. Repeated or overlapping ticks converge. A genuinely new current
inbound reopens the thread in the same transaction, while a broker duplicate or older replay does
not.

Settings → Application adds an original responsive timer control with explicit protection and
reopen guidance. OpenAPI remains **208 paths** with regenerated TypeScript. Focused backend coverage
is **48 passed**; static quality is **6/6 PASS** with strict mypy over 302 files. The applicable
backend suite is **1453 passed / 6 MySQL skips / 1 Redis-dependent test deselected**; the canonical
unfiltered run preserves the known Redis-only failure and the same 1453 passes. Frontend validation
is **39 files / 811 tests**, ESLint, TypeScript and production build PASS.

**Status boundary:** CORE-11C is repository-implemented; CORE-11 remains `PARTIAL`. Campaign
preferences, pipeline/SLA, notification/security/audit settings, team presence/workload/login/
permission audit and required/active attribute controls remain. Authenticated visual, target-host
concurrency and production commissioning are pending. No provider, physical-phone, QR or Module 13
validation claim is made.

### 2026-08-21 — CORE-11B: Working Hours and Guarded Automatic Replies

Extends the validated Inbox Operations policy with organization-timezone working hours plus
optional welcome and off-hours text replies. The seven-day schedule supports disabled days and
overnight intervals. Every new capability defaults off; off-hours replies require enabled working
hours, and both message bodies are validated and bounded before persistence.

Fresh inbound processing now makes the reply decision inside its existing transaction. Outside-
hours messaging takes precedence over welcome, welcome is limited to a newly opened 24-hour
customer window, off-hours is rate-limited to once per conversation per 24 hours, exact opt-out
keywords suppress immediately, and stale/future webhook replay fails closed. The accepted outbound
Message, system Audit evidence and deterministic source→reply Business Event commit atomically;
post-commit delivery reuses the existing provider adapters and serializes duplicate attempts on the
durable Message row. No migration, route, permission, scheduler or parallel message authority was
added; OpenAPI remains **208 paths**.

Settings → Application now includes an original responsive schedule/message editor over the
generated contract and existing organization timezone. Full frontend validation is **39 files /
810 tests**, ESLint, TypeScript and production build PASS. Focused backend Settings/inbound tests
are **40 passed**, delivery/Inbox regression is **73 passed / 1 known Redis case deselected**, Ruff
and strict mypy (302 files) PASS, OpenAPI drift PASS, and the six-step static gate PASS. The final
applicable backend suite is **1450 passed / 6 MySQL skips / 1 Redis-dependent test deselected**.
Authenticated representative-data browser review and target-host/provider delivery remain pending
and are recorded without an acceptance claim.

**Status boundary:** CORE-11B is repository-implemented; CORE-11 remains `PARTIAL`. Auto-resolve,
pipeline/SLA, notification/security/audit settings, team presence/workload/login/permission audit,
and required/active attribute controls remain. No provider, physical-phone, QR, production-host or
Module 13 validation claim is made.

### 2026-08-20 — CORE-11A: Validated Inbox Operations Policy

Starts the remaining CORE-11 administrative work with one bounded, fully consumed policy instead
of adding inert settings. Settings → Application now controls new-thread routing (`manual` or
least-open eligible teammate), automatic versus deliberate read-state clearing, and exact inbound
opt-in/opt-out keywords. Safe defaults preserve existing behavior; consent recognition is disabled
until an authorized manager explicitly enables it.

The existing organization settings table remains authoritative through reserved key
`inbox.operations.v1`; no migration or permission-code change is required. New GET/PUT operations
on one path expose a validated generated contract, while the generic key/value write refuses this
reserved key so validation cannot be bypassed. Policy changes, automatic assignments and consent
transitions are audited; consent also writes Customer Timeline evidence in the same inbound
transaction.

The responsive UI uses original components and repository tokens. Approved Manage/reference
captures informed only category hierarchy, explicit state, compact forms and mobile stacking;
billing, seat purchase, Ads/AI promotions, proprietary branding, text, assets and layout were
rejected. Full frontend validation is **39 files / 809 tests**, lint and production build PASS;
focused backend/settings/inbound validation is **33 passed**, corrected path-count regressions are
**2/2 PASS**, and the complete static quality gate passes. The applicable backend run is **1443
passed / 6 MySQL skipped / 1 Redis-dependent test deselected**; the unfiltered environmental failure
and authenticated representative-data visual/host boundary are recorded precisely in
`VALIDATION_RESULTS.md`.

**Status boundary:** CORE-11A is repository-implemented; it does not complete CORE-11. Working
hours/messages, auto-resolve, pipeline/SLA, notification/security/audit settings, team
presence/login/permission audit and required/active attributes remain pending. No provider,
physical-phone, QR, live-message, production-host or Module 13 validation claim is made.

### 2026-08-09 — QR-09L: WAHA ACK Routing and LID Recipient Identity Remediation

Remediates **QR-09-D13 (application defect)** without changing WAHA acknowledgement mapping or
ranking. A persisted endpoint-owned `message.ack` no longer inherits the background worker's Meta
default: status processing resolves `channel_endpoint_id → ChannelEndpoint → ChannelConnection →
connector_type` from the durable webhook row. Phone-number-owned events remain on the existing Meta
path, and provider-message correlation remains scoped to the owning endpoint.

WAHA routing identity is now distinct from canonical Contact telephone identity. Existing
`contact_identities` is the durable authority: exact `@lid`, `@c.us`, and `@s.whatsapp.net`
addresses are stored as provider-scoped aliases, while `whatsapp_phone` is linked only when the
provider supplies a factual phone JID. LID digits are never interpreted as E.164. Outbound Inbox
replies select the latest provider-observed address for the owned endpoint and fail closed when no
route exists; they never manufacture `@c.us` from `Contact.wa_id`. Meta Contact and outbound
behavior are unchanged. No migration was required because the approved identity model already
holds namespace/scope/value plus connection and endpoint references.

Regression coverage proves signed WAHA ACK parsing through the default worker service,
DEVICE→delivered, late SERVER no-regression, READ→read, duplicate idempotency, unknown-code refusal,
cross-endpoint isolation, all three certified address forms, LID/phone separation, exact outbound
routing, historical duplicate replay without message duplication, Meta status behavior, HMAC,
message/message.any dedupe and QR-09-D12 timestamp normalization. The complete backend suite is
**1444 passed, 0 skipped**; frontend remains **806 passed**.

Canonical premerge is **14/14 PASS in 433.6s**: Ruff, strict mypy (301 files), OpenAPI drift,
frontend/browser types, backend/frontend tests, production build, Bandit, dependency audits and
tracked-source vulnerability/secret/IaC scan. Applicable release/runtime validation is **8/8 PASS
in 70.7s**: Compose, isolated exact-digest QR negotiation, provider-generated signed webhook/ACK
delivery, production release/build contracts, image contracts, vulnerability scans and SBOM. The
restart-bearing health validator was not run against the protected linked service; QR-09I's
approved isolated exact-digest health/restart evidence remains current and no deployment health
code changed.

The preserved genuine DEVICE ACK was replayed once through the normal default status processor. It
was parsed by WAHA and reached endpoint-scoped correlation, which truthfully returned unmatched;
its provider id belongs to neither historical outbound row, so no status was attributed. The
protected certified container remains healthy and WORKING/active/paired with the same persistent
volume and restart count zero. No QR, restart, logout, re-pair, resend, provider upgrade, secret,
frontend, route, OpenAPI, migration, RBAC, capability or approval state changed.

**Status boundary:** QR-09L is `REPOSITORY/RUNTIME VALIDATED`; QR-09-D13 is application-level
`REMEDIATED`, while correlated physical ACK certification remains pending until the newly governed
QR09-L-ACK message is sent and genuinely acknowledged. QR-09 remains `PARTIAL (BLOCKED)`. Meta
token rotation is **PENDING — OWNER DEFERRED**. `Host Validated`, `Provider Validated`, `Production
Ready`: NO.

### 2026-08-09 — QR-09J: WAHA Inbound Timestamp Normalization Remediation

Records and remediates **QR-09-D12 (Blocker)**. The second physical test text was a genuine
external inbound (`fromMe=false`). WAHA delivered both configured event variants, `message` and
`message.any`; each passed raw-body SHA-512 HMAC verification and resolved to the owned channel
endpoint. Both then failed before creating an Inbox row with `TypeError: can't compare offset-naive
and offset-aware datetimes`, and were dead-lettered. This left zero matching messages despite
truthful provider delivery.

The mismatch was at the provider boundary. WAHA's epoch was translated with an aware UTC timezone,
while the repository deliberately uses naive UTC for MySQL DATETIME and `utcnow()`. Conversation
window evaluation consequently compared incompatible values. The adapter now converts the epoch to
UTC and removes timezone metadata before handing it to the shared Contact/Conversation/Message
authorities. No global datetime rule, window behavior, ordering, dedupe or ACK ranking was changed.

One explicit regression asserts the certified timestamp's exact naive-UTC value. The existing
`message`/`message.any` integration now carries that real provider timestamp and proves one stored
message, one conversation, unread count one and naive `last_inbound_at`. Focused webhook/Inbox/
delivery/conversation coverage is **174 passed**.

After loading only the backend/worker fix, the two preserved source events were enqueued through the
normal idempotent webhook processor. Both became processed on their second attempt; actual Inbox
detail/history APIs returned the safe test token exactly once as an accepted WAHA inbound, with
unread count one and matching preview. The original D12 dead-letter rows remain preserved as
historical evidence. No live database row was edited directly.

Canonical premerge **14/14 passed in 684.7 seconds**: backend **1437 passed**, frontend **806
passed**, lint/types/OpenAPI/build/SAST/audits/source scans. Applicable release/runtime gates **8/8
passed in 87.9 seconds**: Compose, exact-digest QR, provider-generated signed webhook, production
contracts/builds, image contracts, vulnerability scans and SBOM. The unchanged canonical health
script was not rerun because it explicitly restarts the protected linked service; QR-09I's isolated
exact-digest health evidence remains current.

The exact live WAHA container, start time, volume and loopback-only exposure are unchanged; restart
count remains zero and the application remains WORKING/active/paired/connected with no QR. No
frontend source, migration, route, schema, RBAC, provider capability/configuration, secret, session
storage, screenshot, QR, rescan, logout or unmasked identity changed or entered evidence.

**Status boundary:** QR-09-D12 is `REMEDIATED`; QR-09J is `REPOSITORY/RUNTIME VALIDATED`; earlier
QR-09 remediations remain preserved. QR-09 stays `PARTIAL (BLOCKED)` pending outbound Inbox reply,
SERVER/DEVICE/READ and out-of-order ACK evidence, linked-session restart/reconnect,
logout/re-authentication and supported-browser/target-host validation. Meta token rotation is
**PENDING — OWNER DEFERRED**. `Host Validated`, `Provider Validated`, `Production Ready`: NO.

### 2026-08-09 — QR-09I: Pairing Window Renewal and Post-Scan Convergence Remediation

Records and remediates **QR-09-D11 (Blocker)**. The pairing TTL governs the ephemeral QR/availability
representation, not the lifetime of provider-established credentials. In the real linked runtime,
that representation expired after the physical scan while the exact configured WAHA session had
already reached identity-bearing `WORKING`. An explicit request for a new pairing window was an
equal-state no-op, while the general transition API correctly rejected all transitions after
expiry; the application therefore remained trapped in `pairing_available` despite the successful
provider link.

Two narrow, provider-neutral manager operations repair the boundary. An explicit pairing request
renews only the availability expiry under the current runtime lease, fencing token and expected row
version; pairing state, revision and original change timestamp stay stable. Read-only polling never
renews the window. Provider-confirmed completion is available only for an expired
`PAIRING_AVAILABLE` row and requires a fresh `WORKING` observation with an identity for the exact
configured session. It transitions to `PAIRED`, clears expiry, preserves the pairing revision and
audits only a boolean identity-presence fact. The ordinary expired-transition rejection is
unchanged, and missing identity, wrong session, provider outage and reached-provider conflict all
fail closed.

The real application, MySQL, Redis and untouched certified WAHA 2026.7.2 / NOWEB / CORE container
then converged to active/paired/connected with no QR available. Provider session, durable connection
and durable session counts stayed exactly one; container restart count stayed zero and linked
message count stayed zero. No provider restart, logout, delete, create, new QR, rescan, message,
manual database mutation or identity disclosure occurred.

Canonical premerge **14/14 passed** in 369.6 seconds: backend **1436 passed**, frontend **806
passed**, lint/types/OpenAPI/build/SAST/audits/scans. Nine release/runtime gates also passed. The
canonical health validator was not run against the owner-linked container because it explicitly
restarts WAHA; a unique internal-only container and volume at the exact certified digest instead
proved health success/failure and healthy restart survival, then was removed. This is a documented
preservation substitution, not a claim that the monolithic release runner executed unchanged.

No frontend source, migration, route, schema, RBAC, provider capability, digest, storage or approval
state changed. Local screenshot automation could not initialize, so no screenshot or browser-matrix
evidence is claimed.

**Status boundary:** QR-09-D11 is `REMEDIATED`; QR-09I is `REPOSITORY/RUNTIME VALIDATED`. QR-09D,
QR-09E, QR-09F, QR-09G and QR-09H remain preserved and validated. QR-09 remains `PARTIAL (BLOCKED)`
pending inbound/outbound/ACK, linked-session restart/reconnect, logout/re-authentication and
supported-browser/target-host evidence. Meta verification-token rotation is **PENDING — OWNER
DEFERRED**. `Host Validated`, `Provider Validated`, `Production Ready`: NO.

### 2026-08-09 — QR-09H: Expired QR Existing-Session Recovery Remediation

Records and remediates **QR-09-D10 (Blocker)**. An unscanned QR lapses — the ordinary outcome of
walking away from the screen — and the certified provider marks the session `FAILED` while the
session object itself survives. `begin_pairing()` only ever creates, so every retry of the governed
"Get a new QR code" action hit the provider's `422 "Session '<name>' already exists"`, and the
service mapped every `ChannelError` to `ServiceUnavailableError`. The operator was told WhatsApp
could not be reached when it had answered, `reconnect` refused because nothing was paired, and
`connect` was an idempotent no-op. After the first QR expired the channel could never issue another
without direct provider intervention.

Provider behavior was measured on the exact certified digest rather than assumed. `start` on a
`FAILED` session answers `201` and changes nothing — starting alone can never recover the expired-QR
state. `stop` moves `FAILED → STOPPED`, and `start` then reaches `STARTING → SCAN_QR_CODE` within
seconds, holding the session count at one, `me` at `None` and the stored `noweb` configuration
byte-identical. Recovery is therefore that existing non-destructive pair, never a delete, recreate
or logout.

A new `WahaChannelAdapter.prepare_pairing()` carries it. `begin_pairing()` is deliberately left
untouched, so QR-03's "no guessing on conflict" principle and its regression still stand: the new
method tries the create first — leaving the ordinary first-pairing path byte-identical — and only on
a reached-provider refusal reads live state and decides. A session already showing a QR is returned
untouched, an already-stopped session skips a redundant stop, and a session the provider reports as
having a linked account is refused outright. The durable half of that guard refuses a `PAIRED`
connection before any provider call, so credential-bearing state stays in the reconnect/logout
domain. Every provider mutation runs under the governed runtime lease.

Error classification is corrected alongside it: `ChannelTransportError` remains
`ServiceUnavailableError`, a reached-provider `ChannelApiError` becomes a truthful `ConflictError`,
and configuration/authentication failures keep their existing semantics. The provider's own wording
is never echoed to operators.

Thirteen focused regressions cover the create path, the certified stop/start recovery and its exact
call order, repeatability, the skip-redundant-stop and reuse-existing-QR branches, both halves of
the paired guard, outage versus conflict classification, message sanitization, lease enforcement,
stale-fencing refusal and that polling never mutates provider state. With the fix reverted nine
fail; the four that pass assert deliberately unchanged behaviour.

Runtime evidence used a genuinely expired QR: the previous code's own QR lapsed naturally to
`FAILED`, and activating "Get a new QR code" in the actual application performed, under a single
request and lease, a refused create, a live read, a stop and a start, after which the UI advanced to
the scan state. Two consecutive application QR requests returned `200 image/png` with
`Cache-Control: no-store, private, max-age=0` and `Pragma: no-cache`; the bytes were measured for
length only and never printed, saved, logged, audited or screenshotted. A second recovery from an
already-stopped session issued a start with no redundant stop. Provider sessions, durable
connections and durable sessions each remained exactly one throughout, with no database
intervention. **Repeatability at runtime was proven once from a natural expiry; a controlled `stop`
was deliberately *not* counted as a second expiry** because it produces `STOPPED → PAUSED` rather
than natural expiry's `FAILED → DEGRADED`, a materially different durable state. Deterministic
repeatability is covered by test instead.

All **23 release gates pass** in 508.9 seconds: backend **1431 passed**, frontend **806 passed**
(unchanged — this milestone touches no frontend source), Ruff, strict mypy (300 files), OpenAPI
drift, ESLint, TypeScript, browser-test types, production build, Bandit, dependency/browser audits,
tracked-source vulnerability/secret/IaC scan, certified WAHA health/QR/webhook runtime gates,
production release and image contracts, image vulnerability scan and SBOM. Migration remains `0043`
(44 revisions), OpenAPI remains 207 paths, and no route, schema, RBAC, capability, digest, storage
or provider-approval change was made.

**Status boundary:** QR-09-D10 is `REMEDIATED` and QR-09H is `REPOSITORY/RUNTIME VALIDATED`.
QR-09D, QR-09E, QR-09F and QR-09G remain `REPOSITORY/RUNTIME VALIDATED`. QR-09 remains `PARTIAL
(BLOCKED)` until physical-phone validation completes. Meta verification-token rotation is **PENDING
— OWNER DEFERRED**. `Host Validated: NO`, `Provider Validated: NO`, `Production Ready: NO`; no
phone, scan, target-host or certification-approval evidence is claimed.

### 2026-08-09 — QR-09D: Pairing Action State Remediation

Closes **QR-09-D6 (Major)** on top of the committed QR-09G backend. The operator selected Connect
WhatsApp, one durable application session was created, WAHA still held no provider session, and
status polling returned `provider_session_missing`. The frontend projected that back to
`ready-to-connect`, so the screen re-offered Connect WhatsApp — an idempotent call that provably
cannot create provider state — and `POST /session/pair` became operationally unreachable. Every
poll re-asserted the dead end.

The durable application session is now the boundary between the two honest operator actions: with
no durable session `connect()` is genuinely what creates one, and with one present the only action
that can move a never-paired connection forward is pairing. A provider-neutral `ready-to-pair` view
state carries that, rendering "Begin pairing" wired to `POST /session/pair`. Because this branch is
only reached on a live session-missing observation — which the backend emits exclusively of a
transport outage — the QR-09F outage check above it still wins, and the QR-09-D2 previously-paired
case is still resolved earlier as `reauth-required` via `requires_reauthentication`. State
precedence is unchanged otherwise: not-configured, connected, reauth-required, provider-unavailable,
ready-to-pair, ready-to-connect, qr-available, the QR-02/QR-06 STARTING ambiguity, and reconnect.

Frontend regressions were reconciled by hand against the QR-09F suite rather than by applying the
historical patch, whose test file genuinely conflicted; every QR-09F outage regression is preserved
and the D6 coverage added alongside it. New tests prove the durable-session boundary in both
directions, that Begin pairing is the only offered action, that it calls pair exactly once and
connect zero times, that three real status refetches never regress the action, that polling and
re-render fire no mutation of their own, that a failed pairing reports truthfully without falling
back to Connect, that the action stays named and busy in flight, that an outage outranks
ready-to-pair and mounts no QR, that recovery restores the pairing action with no QR fetch, and
that a read-only actor sees the state without an operable control.

Validated against the real stack — MySQL, Redis, the actual backend and frontend, and the exact
certified WAHA digest at `2026.7.2 / NOWEB / CORE`. `ready-to-pair` rendered from a genuine
provider-reachable, session-absent, never-paired state and survived eight consecutive live
three-second polls with Connect WhatsApp absent throughout. Activating Begin pairing in the actual
browser issued exactly one `/session/pair` and zero `/session/connect`, leaving exactly one provider
session and one durable connection and session. Two consecutive application QR requests returned
`200 image/png` with `Cache-Control: no-store, private, max-age=0` and `Pragma: no-cache`; the bytes
were consumed in memory and never printed, saved, logged, audited, displayed or scanned. A genuine
outage produced zero new QR requests and no pairing, connect, scan or connecting affordance, and the
same container, volume, provider session and durable session recovered without duplication. The
QR-09G paused never-paired recovery was re-proven through the same UI: a paused, never-paired
session with the provider session absent now renders ready-to-pair and recovers to
`waiting_for_pairing` with one provider session and no database intervention.

Actual running-application screenshots were captured at 1920×1080 and 390×844 in the ready-to-pair
state, plus the provider-unavailable state, with no QR visible and no PII. Neither viewport shows
horizontal overflow, keyboard focus reaches Begin pairing with a visible ring, and the mobile
control measures 118×40. These are local runtime captures, not target-host or browser-matrix
acceptance.

All **23 release gates pass** in 635.1 seconds on the combined tree: backend **1418 passed**,
frontend **806 passed**, Ruff, strict mypy (300 files), OpenAPI drift, ESLint, TypeScript,
browser-test types, production build, Bandit, dependency/browser audits, tracked-source
vulnerability/secret/IaC scan, certified WAHA health/QR/webhook runtime gates, production release
and image contracts, image vulnerability scan and SBOM. Migration remains `0043` (44 revisions),
OpenAPI remains 207 paths, and no route, schema, RBAC, capability, digest, storage or
provider-approval change was made.

**Status boundary:** QR-09-D6 is `REMEDIATED`; QR-09D, QR-09E, QR-09F and QR-09G are all
`REPOSITORY/RUNTIME VALIDATED`. QR-09 remains `PARTIAL (BLOCKED)` pending physical-phone validation.
Meta verification-token rotation is **PENDING — OWNER DEFERRED**. `Host Validated: NO`,
`Provider Validated: NO`, `Production Ready: NO`; no phone, scan, target-host or
certification-approval evidence is claimed.

### 2026-08-09 — QR-09G: Paused Never-Paired Session Recovery Remediation

Records and remediates **QR-09-D9 (Blocker)** without absorbing the separately preserved QR-09D
frontend work. `STOPPED` is an ordinary WAHA status (a restart, or a provider-side session
removal); `map_session_status` turns it into durable `PAUSED`, and `SessionManager.acquire_lock`
refuses to lease a `PAUSED` row. For a session that had **never** been paired this closed every
exit: `GET` status silently swallowed the lease `ConflictError` and fell back to stale durable
metadata, reporting an outage that was not happening; `POST /session/pair` returned `409 "The
session is paused and cannot acquire a runtime lease"`; `POST /session/reconnect` returned `409`
telling the operator to pair; and `POST /session/connect` was an idempotent no-op. Reconnect said
pair, pair could not run, and the WhatsApp QR channel was unrecoverable without direct database
intervention. The documented `PAUSED → INITIALIZING` escape existed only behind `can_reconnect`,
which requires durable `PAIRED`.

The `SessionManager` invariant is deliberately unchanged — nothing now leases a paused row.
`begin_pairing()` instead reuses the exact control-plane pattern `reconnect()` already
established: an explicitly requested pairing on a `PAUSED` session whose pairing state is not
`PAIRED` performs the legal, lease-free governed `PAUSED → INITIALIZING` transition first, then
acquires the ordinary runtime lease and drives the existing adapter path. The recovery is narrow by
proof: `PAIRED` is the only state meaning credentials were ever established, it is terminal in
`LEGAL_PAIRING_TRANSITIONS`, and a paused paired session is the reconnect/re-authentication domain
`can_reconnect` already covers — it keeps the pre-existing refusal rather than being restarted as a
first-time pairing. Separately, a row that cannot be leased at all is now still *read*: reading the
provider is not a mutation, so a missing session and an unreachable provider are reported
truthfully, while a successful observation is downgraded to "not observed" because applying it
needs the lease that could not be taken. Nothing creates, starts or mutates provider or durable
state from a `GET`.

Ten focused regressions prove recovery, transition-before-lease ordering, the retained `PAUSED`
lease prohibition, single provider creation, honest provider-failure reporting, row-version/fencing
progression and stale-version refusal, no duplicate durable session, the corrected projection, and
that QR-09F outage truth and QR-09-D2 session-missing semantics both survive the unleasable path.
With the fix reverted, eight of them fail; the two that pass are exactly the ones asserting
unchanged behaviour. A real MySQL/Redis/application run against the exact certified WAHA digest
replayed the preserved live D9 reproduction: status stopped claiming a false outage without
mutating the row (`row_version` unchanged), the pairing request returned `200` instead of `409`,
the audit trail shows `transitioned → initializing` *before* `lock_acquired` (fencing 867 → 868),
exactly one provider session reached `SCAN_QR_CODE`, exactly one durable connection and session
remained, and no database intervention was required. No QR was displayed, persisted or scanned.

All **23 release gates pass** in 506.1 seconds: backend **1418 passed**, frontend **798 passed**,
Ruff, strict mypy (300 files), OpenAPI drift, ESLint, TypeScript, browser-test types, production
build, Bandit, dependency/browser audits, tracked-source vulnerability/secret/IaC scan, certified
WAHA health/QR/webhook runtime gates, production release and image contracts, image vulnerability
scan and SBOM. Migration remains `0043` (44 revisions), OpenAPI remains 207 paths, and no route,
schema, RBAC, capability, digest, storage or provider-approval change was made.

**Status boundary:** QR-09G is `REPOSITORY/RUNTIME VALIDATED`. QR-09D remains externally preserved
and `PARTIAL`; QR-09 remains `PARTIAL (BLOCKED)`. Meta verification-token rotation is **PENDING —
OWNER DEFERRED**. `Host Validated: NO`, `Provider Validated: NO`, `Production Ready: NO`; no phone,
scan, target-host or certification-approval evidence is claimed.

### 2026-08-09 — QR-09F: Provider-Outage QR Availability Projection Remediation

Records and remediates **QR-09-D8 (Major)** without combining or reapplying the separately
preserved QR-09D frontend work. During a genuine provider outage, a durable
`pairing_available` row was projected as `qr_available: true` with stale
`provider_status: SCAN_QR_CODE`. The frontend evaluated that stale action state before the outage
signal and mounted the QR workflow, causing repeated provider QR requests while WAHA was down.

The backend now distinguishes a current provider observation, a missing provider session and a
transport outage. Only a current `SCAN_QR_CODE` observation may advertise QR availability. An
outage projects `provider_status: null`, `qr_available: false`, `connected: false`,
`healthy: false`, `can_reconnect: false` and `reconnect_blocked_reason: provider_unavailable`
without mutating durable pairing/reauthentication truth. The session-missing projection remains
separate. The frontend gives this stable outage reason priority over stale creating, connecting,
reconnect and QR action states, so it renders the existing unavailable/retry surface without
mounting QR retrieval.

Focused regressions prove the fail-closed projection, absence of create/start/delete/QR side
effects, durable-state preservation and recovery. A real MySQL/Redis/application run with the exact
certified WAHA digest reproduced D8, then held a genuine outage across more than three polling
intervals with zero QR-handler requests; the same container, volume, provider session and durable
application session recovered without recreation. A legitimate post-recovery application QR
request returned `200 image/png` with private/no-store controls; its bytes were held only in memory
and never printed, displayed, persisted or scanned.

Actual local-browser evidence at 1920×1080 and 390×844 shows the truthful unavailable state, no QR
image/action, no horizontal overflow and keyboard-accessible retry. These are local runtime
screenshots, not target-host or supported-browser-matrix acceptance. All **23 release gates pass**
in 474.4 seconds: backend **1408 passed**, frontend **798 passed**, lint/types/OpenAPI/build/SAST,
dependency and source secret/IaC scans, certified WAHA health/QR/webhook gates, production
contracts, image scans and SBOMs. Migration remains `0043` (44 revisions), OpenAPI remains 207
paths, and routes/schemas/RBAC/capabilities/digest/storage/provider approval are unchanged.

**Status boundary:** QR-09F is `REPOSITORY/RUNTIME VALIDATED`. QR-09D remains externally preserved,
unapplied and `PARTIAL`; QR-09 remains `PARTIAL (BLOCKED)`. Meta verification-token rotation is
**PENDING — OWNER DEFERRED**. `Host Validated: NO`, `Provider Validated: NO`, and
`Production Ready: NO`; no phone, scan, target-host or certification-approval evidence is claimed.

### 2026-08-09 — QR-09E: WAHA QR Content Negotiation Remediation

Records and remediates **QR-09-D7 (Major)** without combining the separately preserved QR-09D
frontend work. The WAHA client's binary QR request inherited the JSON API default
`Accept: application/json`. The exact certified WAHA 2026.7.2 runtime honors that header and
returned `200 application/json` from the QR route even with `?format=image`; the adapter correctly
rejected that non-image response, leaving the operator endpoint unable to serve the QR image.

The client now supports request-specific response negotiation. JSON GET/POST behavior remains
`application/json`; only QR byte retrieval sends `Accept: image/png`. Existing API-key handling,
bounded timeouts, provider/transport error mapping, strict image content-type validation, transient
challenge object and application `no-store`/private response controls remain unchanged. Tests cover
the header split, exact bytes, non-image fail-closed behavior without body leakage, authentication,
provider status preservation, timeouts and transport errors.

`scripts/validate_waha_qr.py` starts a uniquely named, loopback-only container from the exact
certified digest, verifies `2026.7.2` / `NOWEB` / `CORE`, creates one disposable unpaired session,
reproduces the JSON-negotiation baseline, and exercises the repository's real client to obtain and
validate a PNG signature in memory. The gate mounts no session volume and removes only its labelled
temporary container. It verifies exactly one provider session and never prints, logs, writes,
displays or scans QR content. The cumulative release runner now executes this regression alongside
the existing certified health and signed-webhook gates.

Two consecutive live application QR fetches returned `200 image/png` with
`Cache-Control: no-store, private, max-age=0` and `Pragma: no-cache`, while one provider session,
one durable connection and one durable session remained. Bodies were consumed only in memory and
discarded; no screenshot or physical scan was produced.

All **23 release gates pass** in 800.3 seconds: backend **1407 passed**, frontend **796 passed**,
lint/types/OpenAPI/build/SAST/dependency audits/source secret-IaC scan, certified WAHA health/QR/
webhook runtime checks, production release/image contracts, image vulnerability scans and SBOMs.
Migration remains `0043` (44 revisions), OpenAPI remains 207 paths, and frontend source, routes,
schemas, RBAC, capabilities, certified digest, persistent storage and provider approval are
unchanged. The production frontend audit retains two moderate React Router advisories below the
repository's high/critical failure threshold; QR-09E changes no dependency.

**Status boundary:** QR-09E is `REPOSITORY/RUNTIME VALIDATED`. QR-09D's external three-file patch
was not reapplied or committed and QR-09D remains `PARTIAL`; QR-09 remains `PARTIAL (BLOCKED)`.
Meta rotation is **PENDING — OWNER DEFERRED**. `Host Validated: NO`, `Provider Validated: NO`, and
`Production Ready: NO`; no phone, screenshot, target-host or certification-approval evidence is
claimed.

### 2026-08-09 — QR-09C: WAHA Webhook Delivery Wiring and Credential Hygiene

Records and remediates **QR-09-D5 (Major)** without rewriting QR-09, QR-09A or QR-09B history. The
backend already exposed `POST /api/v1/webhooks/waha` and rejected unsigned or forged deliveries with
raw-body SHA-512 HMAC verification, but neither Compose definition configured WAHA to call it. A
paired provider therefore had no delivery route into `WebhookService`, `MessageService` or the
Unified Inbox.

Both Compose definitions now configure one global provider webhook. Production uses the private
`http://api:8000/api/v1/webhooks/waha` route; local development uses the Docker-internal
`host.docker.internal` route while preserving WAHA's loopback-only host publication. Subscriptions
are restricted to `message`, `message.any` and `message.ack`. A dedicated
`WAHA_WEBHOOK_HMAC_SECRET` is required by the production WAHA profile and is injected into both the
provider sender and existing backend verifier. It is explicitly separate from every Meta credential,
the provider API key and session material. Per-session webhooks remain absent: the pinned provider
combines global and per-session configuration, which would duplicate delivery, and per-session HMAC
configuration would persist the signing key with session state.

The certified sender's observed retry contract is pinned explicitly at 15 attempts, constant
two-second delay. Its requests have no configured timeout in WAHA 2026.7.2; that provider limitation
is documented rather than hidden. Global settings remain in container environment, survive restart,
and are reapplied as restored sessions start; `waha-sessions:/app/.sessions`, digest, engine,
capabilities, restart policy and production network exposure are unchanged.

`scripts/validate_waha_webhook.py` renders both Compose profiles with synthetic, distinct
credentials and runs the exact certified image on an isolated private Docker network. WAHA's shipped
`WebhookSender` — not repository HMAC code — produced a valid SHA-512 signature to the internal
`api:8000` callback. A controlled `503` caused one byte-identical retry with the same request id;
after provider restart, a separately signed ACK delivery succeeded with a new request id. The gate
confirmed `2026.7.2` / `NOWEB` / `CORE` and zero provider sessions before and after restart. It
created no session, requested/displayed no QR and performed no phone interaction. Existing focused
receiver tests prove forged/missing signatures fail closed and provider retries plus
`message`/`message.any` converge to one stored message through the governed dedupe authorities.

All **22 release gates pass** in 525.3 seconds: backend **1399 passed, 0 skipped**, frontend
**796 passed**, lint/types/OpenAPI/build/SAST/dependency audits/source secret-IaC scan, both certified
WAHA runtime regressions, Compose/release/image contracts, application-image vulnerability scans and
SBOMs. Migration head remains `0043_conversation_channel_endpoints` (44 revisions), OpenAPI remains
207 paths, and application source, UI, RBAC, migrations and provider capabilities are unchanged.

**META WEBHOOK_VERIFY_TOKEN ROTATION:**
**PENDING — OWNER DEFERRED**

**Status boundary:** QR-09C is `PARTIAL — D5 REMEDIATED, META TOKEN ROTATION PENDING`; QR-09 remains
`PARTIAL (BLOCKED)`. `Host Validated: NO`, `Provider Validated: NO`, and `Production Ready: NO`.
Provider certification/approval is unchanged. No physical-phone or target-host evidence is claimed.

### 2026-08-09 — QR-09B: WAHA Runtime Healthcheck Remediation

Records and repairs **QR-09-D4 (Major)** without rewriting QR-09 or QR-09A history: both Compose
files invoked `wget` from the certified WAHA image, but that executable is absent, so Docker could
never leave its `starting` health state even while the provider API was responsive. The exact pinned
image contains `curl 7.88.1`; its API-key-protected `/health` endpoint returns `401` without a
credential, while the provider-owned unauthenticated `/ping` liveness endpoint returns `200`.

Both development and production definitions now use an exec-form, five-second bounded
`curl --fail` probe against `http://127.0.0.1:3000/ping`. The command contains no secret and tests
provider process/API responsiveness only — never WhatsApp pairing state. A new runtime regression
starts the exact certified digest, proves Docker becomes `healthy`, executes the committed command
successfully, proves the same probe fails against an unavailable loopback endpoint, restarts WAHA,
proves it becomes healthy again, and verifies the same named session volume remains mounted with no
pre-existing file removed. It also enforces loopback-only development exposure, no production WAHA
port, unchanged restart policy, and no new `service_healthy` startup coupling.

The release gate now runs that real-container regression. Its build-only Compose environment gained
only a conspicuous WAHA API-key sentinel because Compose interpolates required profile values before
profile selection; no real credential is read or printed. The backend image contract was synchronized
from its stale historical 193-path assertion to the repository's existing **207-path** OpenAPI
contract (25 registered application tasks unchanged).

All **21 release gates pass**: backend **1397 passed**, frontend **796 passed**, lint/types/OpenAPI
drift/build/SAST/dependency audits/source secret-IaC scan/Compose/release and image contracts/app-image
vulnerability scans and SBOMs all pass. The exact WAHA image also passes the repository's pinned
Trivy image gate. Migration head remains `0043_conversation_channel_endpoints` (44 revisions),
OpenAPI remains 207 paths, capabilities/RBAC/application behavior are unchanged, production WAHA
remains internal-only, and no QR was displayed or scanned.

**Status boundary:** QR-09B is `REPOSITORY VALIDATED`; QR-09 remains `PARTIAL (BLOCKED)` pending its
real physical-phone and target-host/browser evidence. QR-09A remains preserved as historical
repository validation with this factual superseding D4 note. Provider certification approval,
`Host Validated`, `Provider Validated`, and `Production Ready` are not advanced.

### 2026-08-08 — QR-09A: Production Validation Remediation

Repairs exactly the blockers QR-09 recorded, and nothing else. **QR-09 itself remains
`PARTIAL (BLOCKED)`** — its failure evidence is preserved verbatim, because a remediation milestone
fixes causes, it does not retroactively pass the validation that found them. Migration head stays
`0043_conversation_channel_endpoints` (44 revisions) and OpenAPI stays **207 paths**: no revision,
route, RBAC entry or capability was added.

**QR-09-D1 (Major) — `0043` is now reversible on real MySQL.** `downgrade()` dropped
`uq_conv_endpoint_contact` before `fk_conv_channel_endpoint`, but InnoDB elects that index (leading
column `channel_endpoint_id`) to satisfy the foreign key's mandatory supporting index, so MySQL
refused with error 1553 — and because MySQL DDL is not transactional, the failed attempt left
`messages`/`webhook_events` already stripped while `alembic_version` still read `0043`, a schema
matching neither revision. All conversation-side drops now happen in one batch in dependency order
(check → foreign key → index → column). **No new revision was created**: the fix is to a broken
`downgrade()` body, and the upgrade path, revision id and resulting schema are byte-for-byte
unchanged, so nothing already applied is rewritten. Regression added to
`tests/test_migrations_mysql.py` (12 live-MySQL tests, was 11): clean database → `0042` → seed a
representative Meta thread → `0043` → assert every seeded row survives byte-for-byte and gains no
invented endpoint ownership → downgrade → assert the version is truthful, that no `0043` column,
index or constraint remains, and that the seeded data is still valid → upgrade again. SQLite never
reproduced this (batch mode rebuilds the whole table), which is exactly why the regression is
asserted against a real server.

**QR-09-D2 (Major) — a reachable provider holding no session is now a recoverable state, not a
500.** The provider's `404 Session not found` became a generic `ChannelApiError`, which
`_reconcile()` only caught as `ChannelTransportError` and `get_status()` only suppressed as
`ConflictError`; neither matched, so it surfaced as an unhandled 500 on the one screen an operator
needs in order to recover. `WahaSessionNotFound` now narrows that 404 at the client boundary, and
the service treats it as an observation rather than a fault: durable pairing truth is left
**untouched**, and the status projection reports the divergence instead. The distinction that
matters to an operator is preserved — a connection that had reached `PAIRED` reports
`requires_reauthentication` (its credentials really are gone and a fresh scan is required), while
anything else is the ordinary connect-and-scan path. Reconnect refuses explicitly (`409`) rather
than restarting a session that does not exist. Nothing recreates a session, starts pairing or
fetches a QR on a status read — asserted by a test that fails if a read issues any write. An
outage is still an outage: `ChannelTransportError` remains `provider_unavailable` and never reports
a missing session, so QR-06's semantics are untouched. The frontend gained the matching correction:
`deriveViewState` returned `"creating-session"` for this state, rendering *"Starting the session…"*
— false progress an operator would wait on indefinitely — and now resolves to the truthful
`ready-to-connect`, carrying the server's own explanation. One additive response field
(`provider_session_missing`); no route added.

**QR-09-D3 (Minor) — an oversized delivery is answered `413`, not `500`.** The 1 MiB bound is
QR-04's and is unchanged; the body is still refused *before* it is hashed. `WahaBodyTooLarge` simply
had no HTTP mapping. New `PayloadTooLargeError` maps it to a client error, which is operationally
load-bearing rather than cosmetic: WAHA delivery is at-least-once and retries a `5xx`, so the old
answer turned one oversized delivery into an endless redelivery loop. The refusal states the bound
and never echoes the body.

**QR-09-G1 (required gate) — the OpenAPI drift gate is green.** `frontend/openapi.json` was
regenerated through the canonical exporter (`scripts/export_openapi.py`) and the client types
through `npm run gen:api`; neither file was hand-edited. `scripts/quality_gate.py static` now passes
all six steps. The committed artifact had been written with `ensure_ascii=True` while the exporter
emits `ensure_ascii=False` — QR-09 proved generation is deterministic and key order identical, so
the previously recorded "key-order mismatch under an unpinned FastAPI/Pydantic resolver"
explanation was wrong. That historical text is **annotated, not rewritten**, in `PROJECT_STATE.md`
and `VALIDATION_RESULTS.md`. No FastAPI or Pydantic version was pinned or changed. Path count is
unchanged at 207; the only schema delta is D2's one additive property.

**QR-09-I1 (infrastructure) — WAHA now has a governed deployment definition.** A `waha` service was
added to both compose files, pinned by **digest**
(`devlikeapro/waha@sha256:33ecd1b782b2708db2ff1d366f51608889a036e76332dceae3fbbe3f10f2d75e`) rather
than by tag, because the certification evidence is for one immutable build and a floating tag can be
repointed upstream. It sits behind a `waha` compose profile, so an operator who has not adopted the
QR channel runs the exact stack they ran before, and the backend's WAHA settings default to empty
(the adapter then reports `configured=false` and registers no runtime). Production publishes **no
port at all** — only the backend reaches it over the compose network; development binds
`127.0.0.1` only. Session state persists on a `waha-sessions` volume at `/app/.sessions`, the path
verified empirically against this digest (`noweb/waha.sqlite3` plus `noweb/<session>/`).
`deploy/DEPLOYMENT.md` gains §15 covering topology, why the volume is not optional, operator
procedures for each failure mode, backup, and disable/rollback.

**QR-09-S1 (security) — `cryptography` advisory resolved.** `PYSEC-2026-3552` affected `49.0.0`
and is fixed in `50.0.0`. The declared floor was `>=43` and this repository ships **no lock file**,
so the floor is the only thing that can stop a constrained or offline resolve from selecting a
vulnerable build; it is raised to `>=50`. `pip-audit` now reports **no known vulnerabilities**, and
94 crypto/auth/credential tests pass against the upgraded library. No unrelated dependency was
touched.

**Validated against real infrastructure**, not SQLite: MySQL `8.0.46`, Redis `7.4.9`, and the real
pinned WAHA container. The D2 condition was reproduced end to end — provider up (`/api/server/version`
`200`), its session deleted, provider answering `404 Session not found` — and the status endpoint
returned **`200`** with `provider_session_missing: true` and
`reconnect_blocked_reason: "provider_session_missing"`, where QR-09 recorded `500` on 30/30 calls.
A real `docker compose restart waha` with the new volume preserved the session. Oversized delivery
returned `413`; valid HMAC `200` and invalid HMAC `403` are unchanged. Backend **1397 passed, 0
skipped** (was 1385; +12), frontend **796** (was 793; +3), 371 QR-01..08 regression tests pass
together, Ruff/strict mypy/ESLint/TypeScript/production build all pass, Bandit unchanged at 0
High / 0 Medium / 28 Low.

**Not claimed.** WAHA capabilities are unchanged (`HEALTH`, `QR_AUTH`, `SESSION_STREAM`, `TEXT`,
`SESSION_RECONNECT`, `SESSION_LOGOUT`; `BULK`/`CAMPAIGNS`/`TEMPLATE` still permanently prohibited).
Credential survival across a restart *after a real QR scan* cannot be proven without a physical
handset and is **not** claimed — only pre-pairing session persistence was demonstrated. The
provider certification record is untouched. `Host Validated`, `Provider Validated` and
`Production Ready` all remain **NO**.

### 2026-08-08 — QR-09: Production Validation — PARTIAL (BLOCKED, evidence-only)

**No product code, migration, OpenAPI, dependency, or capability change.** This entry records a
validation attempt only. Migration head remains `0043_conversation_channel_endpoints` (44
revisions); OpenAPI remains 207 paths; WAHA capabilities remain unchanged
(`HEALTH`/`QR_AUTH`/`SESSION_STREAM`/`TEXT`/`SESSION_RECONNECT`/`SESSION_LOGOUT`;
`BULK`/`CAMPAIGNS`/`TEMPLATE` still permanently prohibited).

**Environment.** Real MySQL `8.0.46` and Redis `7.4.9` (this repository's own
`docker compose up -d`), and the real pinned WAHA container
(`devlikeapro/waha@sha256:33ecd1b782b2708db2ff1d366f51608889a036e76332dceae3fbbe3f10f2d75e`,
2026.7.2 / NOWEB / CORE — the exact certified digest). No physical handset was available, so QR
scan-to-`WORKING`, real external inbound/outbound, ACK-chain reconciliation, reconnect-without-a-
new-QR, and logout/re-auth were **not** exercised.

**Closed a QR-08 preview limitation.** QR-08's own preview evidence was blocked by the absence of
Redis in that throwaway environment (`503 idempotency_unavailable`). Against real Redis, the full
contract holds: a normal send succeeds; a duplicate `Idempotency-Key` replays the original response
and writes no second row; 6 concurrent requests sharing one key produce exactly one message; a
Redis outage fails closed (`503`); a Redis restart recovers.

**Decisive dual-provider proof on real MySQL.** Delivering one underlying provider message as
`message` **and** `message.any`, each retried once (4 deliveries total), produced 4
`webhook_events` rows (event-layer persistence is intentionally at-least-once) but **exactly one**
stored `messages` row (`apply_inbound` outcomes: `applied`, then three `duplicate`) — proving
QR-08's endpoint-scoped stored-message dedupe end to end against real MySQL, not just SQLite.

**Two Major defects found, reproduced, and left unfixed (per validation defect policy — this
milestone stops on discovery, it does not silently remediate).**

- **QR-09-D1.** `0043_conversation_channel_endpoints`'s `downgrade()` fails on real MySQL 8:
  `(1553, "Cannot drop index 'uq_conv_endpoint_contact': needed in a foreign key constraint")`.
  `uq_conv_endpoint_contact` (leading column `channel_endpoint_id`) backs
  `fk_conv_channel_endpoint`; the downgrade drops the index before the foreign key. Because MySQL
  DDL is non-transactional, the failed attempt left `messages`/`webhook_events` columns already
  dropped while `alembic_version` still read `0043` — a schema matching neither revision. Same
  defect class as the already-tracked `0036`/`0040` real-MySQL downgrade defect. The upgrade path
  (`0042` → `0043`) is unaffected: verified to preserve seeded Meta rows byte-for-byte and to
  correctly enforce the exactly-one-owner `CHECK` at the database level.
- **QR-09-D2.** `GET /channels/whatsapp-qr/session` returns `HTTP 500` whenever the real provider
  is reachable but the named session no longer exists there (reproduced deterministically after a
  WAHA container restart with no persistent session volume — 30/30 calls during the performance
  run). Root cause: the provider's `404 Session not found` becomes `ChannelApiError`, which
  `WhatsAppQrService._reconcile()` only catches as `ChannelTransportError` and
  `get_status()` only suppresses as `ConflictError` — neither matches, so it propagates. A genuine
  provider outage (container stopped) is handled correctly today
  (`reconnect_blocked_reason: "provider_unavailable"`, `requires_reauthentication: false`); this
  specific state — provider up, session gone — is not.
- **QR-09-D3 (Minor).** An oversized WAHA webhook body is correctly refused before hashing
  (`WahaBodyTooLarge`, the 1 MiB bound holds) but surfaces as `HTTP 500` rather than a 4xx, because
  the exception has no HTTP mapping — inviting the provider's at-least-once retry rather than
  stopping it.

**A required repository gate genuinely fails.** `scripts/quality_gate.py`'s OpenAPI drift check
(`scripts/export_openapi.py --check`) reports `openapi.json` stale. Investigated rather than
dismissed: generation is deterministic (identical SHA-256 across processes); the committed file and
a fresh generation parse to **exactly equal** objects with **207 paths both**; re-encoding the
committed file with `ensure_ascii=False` (the exporter's own setting) produces a **byte-exact**
match to the fresh generation. Key order and content are identical — the only difference is JSON
ASCII-escaping (the committed artifact was written with `ensure_ascii=True` at some point in its
history). This **corrects** the explanation recorded elsewhere in this repository attributing
OpenAPI generation non-determinism to "a pre-existing JSON key-order mismatch under the unpinned
FastAPI/Pydantic resolver" — that explanation does not hold for this artifact; the true cause is a
one-time ASCII-escaping setting difference, not resolver non-determinism. The gate is real and
required, and it is red; QR-09 cannot close while it is.

**Real-infrastructure gate results.** Backend full suite **1385 passed, 0 skipped** (was 1380 passed
+ 5 skipped without MySQL) — the 5 previously-always-skipped live-MySQL tests now genuinely ran.
11/11 live-MySQL tests pass. Frontend 38 files / 793 tests, ESLint, TypeScript, and production build
all pass. Ruff and strict mypy (300 files) pass. Bandit: 0 High, 0 Medium, 28 Low (the documented
pre-existing `assert`-usage class, none new). `pip-audit`: one production advisory,
`cryptography 49.0.0` → `PYSEC-2026-3552`, fixed in `50.0.0` — **not upgraded** in this milestone.
`npm audit --omit=dev`: 2 moderate (a `react-router` SSR-hydration advisory; this is a
client-rendered SPA, not SSR). Latency measured against this repository's own documented budgets
(Doc 01 §5.1 `NFR-PERF-01` p95 < 300 ms reads; Doc 06 webhook ack < 200 ms) on a single developer
workstation: mixed-Inbox list p95 12.8 ms, thread load p95 5.2 ms, WAHA thread load p95 4.7 ms,
webhook ingest ACK p95 10.4 ms — all within budget, but **not** target-host, concurrency, soak, or
1M-contact-scale evidence.

**Infrastructure gap found.** No WAHA service, image pin, or persistent session volume is defined
in `docker-compose.yml`, `docker-compose.production.yml`, or `deploy/DEPLOYMENT.md` — the absence
that made QR-09-D2 reachable outside a lab environment is a genuine deployment gap, not only a
validation-harness artifact.

**Preserved, unchanged by this milestone.** QR-01 through QR-08 remain exactly as delivered; QR-08
remains `COMPLETE`. The WAHA selection record
(`docs/evidence/provider-evaluations/waha-class-b-selection-record.md`) and its
`CONDITIONALLY CERTIFIED — HOST/PHONE EVIDENCE REQUIRED` status are untouched. No capability was
added, expanded, or removed. No migration, route, RBAC entry, or dependency was changed.

**Classification.** `Repository Validated: NO` (a required gate is red and two Major defects are
open) · `Host Validated: NO` · `Provider Validated: NO` · `Production Ready: NO`. Recommended next
milestone (not started): `QR-09A — Production Validation Remediation` — fix D1 (reorder the FK-then
-index drop in `downgrade()`, add a real-MySQL down/up regression test), fix D2 (translate a
provider-up/session-absent `ChannelApiError`/404 into a truthful recoverable status, add a
regression), fix D3 (map `WahaBodyTooLarge` to a 4xx), regenerate `openapi.json` with consistent
ASCII-escaping and correct the stale explanation elsewhere in governance, add a WAHA service
definition with persistent session storage to compose/deployment/runbook, triage the `cryptography`
advisory, rerun QR-09, then pursue physical-phone/host-browser evidence.

### 2026-08-08 — QR-08: Unified Inbox integration

**Added**
- `backend/alembic/versions/0043_conversation_channel_endpoints.py` — additive expand-stage
  migration: `conversations` gains a nullable, real-FK `channel_endpoint_id` and its
  `phone_number_id` widens to nullable, guarded by a new `ck_conv_endpoint_owner` check (exactly
  one of the two set); `messages`/`webhook_events` (both partitioned on MySQL) gain the same
  nullable, app-enforced `channel_endpoint_id` alongside their existing `phone_number_id`. No
  column dropped, renamed, or narrowed; every existing row's `phone_number_id` is untouched.
- `POST /webhooks/waha` — the WAHA analogue of the existing `/webhooks/whatsapp` route. QR-04
  (2026) built the HMAC verification and event parsing but never wired an HTTP route to it; this
  is that route, unchanged in shape from Meta's (public, signature-gated, persist-then-ack).
- `SendService.accept_for_conversation` / `.accept_endpoint` / `._deliver_endpoint` — the WAHA
  outbound path. Text-only; no window check (WAHA carries no Meta customer-service-window rule);
  refuses to send when the underlying session is not `ACTIVE`+`PAIRED`
  (`ChannelNotConnectedError`); a send whose outcome cannot be confirmed is marked
  `failed`/`error_code=indeterminate` and is never retried automatically.
- `MessageService._apply_inbound_endpoint` / `WebhookService` endpoint routing /
  `ConversationService.thread_for_endpoint` / `.open_for_inbound_endpoint` — the WAHA inbound
  path, mirroring the existing Meta path method-for-method rather than branching inside it
  (ADR-0020 "independent failure domains").
- `MessageRepository.get_by_provider_message_id_for_endpoint` /
  `ConversationRepository.get_for_endpoint_contact` /
  `WebhookEventRepository.resolve_endpoints` — the endpoint-scoped analogues of the existing
  phone-number-scoped lookups (ADR-0020, QR-00's provider-message-identity scoping), keyword-only
  and required, with no unscoped variant.
- `MessageSendRequest.conversation_id` (optional) — a reply to an existing thread. The provider is
  resolved entirely server-side from the conversation's own durable ownership; the request carries
  no provider/endpoint field for a caller to set. `phone_number_id`+`to` remain for the original
  "send to any number" contract, unchanged.
- `ConversationResponse.connector_type` — which provider owns the thread (`meta_cloud`/`waha`),
  display-only, server-derived.
- `frontend/src/features/inbox/` — mixed-provider channel badge (conversation list + thread
  header) and a provider-aware composer: no 24h-window check for a WAHA thread, and a truthful
  disabled/refuse state (reusing QR-07's own live session-status read, `useWhatsAppQrStatus`) when
  the WAHA session is not currently connected.
- `backend/tests/test_qr08_inbox_integration.py` — 13 new hermetic backend tests. `frontend`
  gains 4 new Inbox tests.

**Behaviour**
- **Stored-message dedupe is not event dedupe.** `message`/`message.any` share one `envelope.id`
  and represent the same underlying WAHA message; QR-04's event-level dedupe (scoped by session +
  event type) correctly treats them as two distinct, both-valid events — but
  `MessageService._apply_inbound_endpoint` additionally dedupes by
  `(channel_endpoint_id, canonical_provider_message_id)` before ever inserting a row, so the two
  events collapse to one stored message. Proven for a same-event redelivery too, and proven *not*
  to collapse across two different endpoints holding the same provider message id.
- **Contact identity is unified across providers without a second normalization rule.** A WAHA
  sender arrives as `<digits>@c.us`/`@lid`/`@s.whatsapp.net`; the existing `wa_id_from_e164`
  (digit-stripping) already reduces it to the same key Meta's `wa_id` uses, so the same phone
  number resolves to the same `Contact` regardless of which provider it messaged through
  (ADR-0020 "One Contact authority") — no new identity code was needed.
- **No cross-provider failover, enforced structurally, not by convention.** `conversations`'
  `ck_conv_endpoint_owner` check makes "owned by both" or "owned by neither" a schema violation,
  not just a code discipline; `accept_for_conversation` has no provider parameter to override.
- **Reused, not duplicated, QR-07's own `channel_endpoints`.** `WhatsAppQrService.connect()` (QR-07
  code) now also idempotently creates the connection's one `ChannelEndpoint`
  (`provider_endpoint_id` = the WAHA session name — stable across a logout/re-pair cycle, unlike
  the phone number behind it) — the durable, addressable identity a conversation is anchored to.
  QR-07 never created one because nothing needed it yet.

**Defects found and fixed (both pre-existing in already-shipped QR-06/QR-07 code, surfaced only
once QR-08 exercised paths nothing had exercised before)**
- QR-07's `_REAUTH_PAIRING` constant included `PairingState.UNPAIRED`, diverging from the
  canonical definition QR-06 already established (`app.channels.waha.recovery`, which correctly
  excludes it). Harmless in QR-07 alone; became load-bearing once QR-08 needed `connect()` +
  `_ensure_endpoint()` to always succeed for a fresh connection. Fixed to match QR-06's definition.
- QR-04's `parse_events` classified `message.ack` as `UNKNOWN` even though QR-05 had already built
  `to_status_update` specifically to translate it — the wiring between the two was simply never
  completed. Now routed as `InboundEventType.STATUSES`, reaching the existing monotonic
  `messages.status` machinery QR-05 targeted from the start.

**Permanently absent for WAHA (unchanged from QR-01..07, enforced again here at the send-routing
layer)**
- MEDIA, INTERACTIVE, REACTION, LOCATION, CONTACT, TEMPLATE, CAMPAIGNS, BULK — a non-text reply
  against a WAHA conversation is refused with `ChannelCapabilityNotSupportedError`, not silently
  downgraded or routed to Meta.
- WAHA history retrieval and media-byte transfer remain unimplemented; unrelated to this milestone
  and not silently added. Unsupported media in an inbound WAHA message continues to render
  truthfully (`message_type: "unsupported"`, per QR-04), never as blank text.

**Known limitation**
- Analytics' existing "throughput by number × agent" rollup (`AnalyticsRollupService`) is a
  Meta-number-specific dimension; a WAHA conversation (no `phone_number_id`) is excluded from it
  rather than counted under a fabricated dimension. QR-08 introduces no WAHA analytics.

### 2026-08-08 — QR-07: WhatsApp Scan/Connect interface

**Added**
- `backend/app/services/whatsapp_qr_service.py` — bridges the live WAHA adapter (QR-01..06) to the
  existing M13-03/04/05 durable connection/session/pairing control plane
  (`ChannelConnectionService`, `SessionManager`, `PairingManager`). Single-organization scope per
  ADR-0021 (`WAHA_ORGANIZATION_ID`); creates no new table.
- `backend/app/api/v1/endpoints/whatsapp_qr.py` — 6 routes under `/channels/whatsapp-qr`: session
  status, connect, pair, QR image (binary, `Cache-Control: no-store, private`), reconnect, logout
  (requires `{"confirm": true}`). Gated on the existing `channels:read`/`channels:authenticate`
  permissions; no RBAC catalog change.
- `backend/app/schemas/whatsapp_qr.py` — provider-neutral response contract. No WAHA credential,
  session secret or QR byte ever appears in a JSON field.
- WAHA runtime registration is now wired into `get_channel_foundation()` — the QR-06 opt-in entry
  point — gated on `WAHA_BASE_URL`/`WAHA_API_KEY`/`WAHA_SESSION_NAME` all being set. An
  unconfigured deployment still registers nothing (asserted by test).
- `frontend/src/features/whatsapp-qr/` — the operator-facing Scan/Connect screen: live status
  polling (adaptive rate), QR image as an in-memory object URL (never cached, never persisted),
  connect/pair/reconnect actions, and an explicit two-step logout confirmation. New route
  `/channels/whatsapp-qr` (own `channels:read` gate, distinct from the Meta `waba:read` shell),
  linked from the existing Channels page header.
- 30 new hermetic backend tests (`tests/test_whatsapp_qr.py`) and 23 new frontend tests
  (`whatsapp-qr.test.tsx`).

**Behaviour**
- **STARTING stays ambiguous through the UI, not just the backend.** The frontend's own view-state
  derivation refuses to call a `STARTING` provider status "connecting" unless durable
  `pairing_state` is already `paired` — otherwise it reads as "creating session", mirroring
  QR-02/QR-06 exactly rather than re-deriving the rule loosely in presentation code.
- **Pairing transitions are ordered around a real M13-05 constraint discovered while building
  this**: `PairingManager` only accepts a pairing transition while the session is still
  `INITIALIZING`/`WAITING_FOR_PAIRING`. Reaching `ACTIVE` must therefore happen *after* the pairing
  step lands, not before — the service now orders session/pairing transitions conditionally rather
  than in a fixed sequence.
- **`PairingState.PAIRED` is terminal**, by existing M13-05 design (the same rule that requires a
  new session revision to re-authenticate an `EXPIRED` one). Logout does not try to reverse a paired
  revision in place — it terminates it and registers a fresh `UNPAIRED` revision on the same
  connection, changing the session identity the caller sees. This is the correct signal, not an
  artefact.
- **`SessionManager.acquire_lock` refuses to lease a `PAUSED` session** (an existing invariant).
  Reconnect therefore moves `PAUSED → INITIALIZING` through the lease-free write path
  (`channels:manage`) before acquiring a lease and driving the actual reconnect.
- **The QR image is never persisted.** Fetched fresh per request from the adapter, served with
  `Cache-Control: no-store, private`, held client-side only as a revoked-on-replace object URL.
- **Every mutating action holds the real M13-05 database lease**, not a bespoke lock — a second
  request racing a mutation gets the existing "lease held by another active runtime" conflict.
- **No QR-08 leakage.** No Unified Inbox integration, no history/media sync, no
  interactive/reaction/location/contact. `BULK`/`CAMPAIGNS`/`TEMPLATE` remain permanently
  prohibited.

**Known limitation**
- Retrying an **expired, never-scanned** QR reuses the pairing-request path, which the certified
  provider correctly refuses once its own session object already exists (`ChannelApiError`,
  observed and asserted in QR-03's own suite). The UI surfaces that real error rather than hiding
  it; a dedicated provider-side session restart is not implemented in this milestone. Recorded here
  rather than silently left for someone to rediscover.

**Unchanged**
- Migration head `0042_scope_provider_message_identity` (43 revisions — QR-07 reuses the *existing*
  `channel_connections`/`channel_sessions` tables from M13-03/04, no new migration). RBAC catalog
  (`channels:read`/`channels:manage`/`channels:authenticate`/`channels:diagnose` already existed
  from M13-05). Meta behaviour and `BULK`/`CAMPAIGNS`/`TEMPLATE` prohibition.

**OpenAPI**
- **200 → 206 paths.** The six new routes are QR-07's first public surface over the pairing
  control plane; two pre-existing invariant tests that asserted an exact path count of 200 were
  updated to 206 with an explanatory comment, since QR-07 explicitly authorizes this — the
  assertion that no *secret*-shaped field (`qr_payload`, `pairing_secret`, `pairing_reason_code`)
  ever appears is preserved unchanged.

### 2026-08-08 — QR-06: WAHA session recovery, health and teardown

**Added**
- `app/channels/waha/recovery.py` — `ReconnectDecision`, `plan_reconnect()`, `backoff_delay()`,
  `RuntimeLease`/`assert_lease_current()`/`StaleRuntimeLease`, `project_health()`, and the
  opt-in `waha_channel_metadata()`/`waha_runtime_metadata()`/`register_waha_runtime()`.
- `WahaClient.start_session()`, `stop_session()`, `logout_session()`.
- `WahaChannelAdapter.session_health()`, `plan_session_recovery()`, `reconnect_session()`,
  `stop_session()`, `logout_session()`.
- **`SESSION_RECONNECT` and `SESSION_LOGOUT` declared** — earned by implementing them.
- 62 tests in `tests/test_channel_waha_recovery.py`.

**Behaviour**
- **Reconnect never guesses from an ambiguous provider status.** QR-02 proved `STARTING` means
  either a fresh session heading to `SCAN_QR_CODE` *or* a paired one resuming to `WORKING`.
  `plan_reconnect()` is therefore driven by the platform's **durable** pairing record and consults
  it before the provider status; `STARTING` yields `WAIT`, never `RECONNECT` and never
  `REQUIRES_REAUTH`. A session whose durable state is not `PAIRED` is never auto-restarted.
- **Provider unavailability never destroys durable truth.** An unreachable provider yields
  `PROVIDER_UNAVAILABLE` — explicitly not `REQUIRES_REAUTH` — so a brief outage cannot unpair a
  customer. `session_health()` reports it as unknown-and-unhealthy rather than optimistically fine.
- **Reconnect is bounded.** Attempts stop at `DEFAULT_MAX_RECONNECT_ATTEMPTS`, and `backoff_delay()`
  grows exponentially to a 60s ceiling as a pure function of the attempt number — identical in every
  worker, no shared coordination, no reconnect storm. A `WORKING` session is never reported
  exhausted regardless of prior attempts.
- **STOP and LOGOUT stay semantically distinct.** STOP halts the session and leaves credentials
  (`pairing_state` stays indeterminate — it does not claim the session became unpaired). LOGOUT
  invalidates them, producing the certified `SCAN_QR_CODE` / `me=null` / re-auth-required outcome,
  which is the *intended* result and is never auto-repaired. Collapsing them would let a routine
  restart silently unpair an account. `DELETE` is deliberately not exposed at all.
- **Ownership reuses the existing lease.** `RuntimeLease` describes a lease the existing session
  authority already issued; `assert_lease_current()` requires **both** holder identity and fencing
  token to match, so a re-claimed session cannot accept a stale writer that happens to hold the same
  token number. Every lifecycle mutation refuses outright without a lease and makes **no** provider
  call in that case. No new ownership system was invented.
- **Health is session-scoped.** Only `WORKING` is healthy; a reachable server with no working
  session is not. A session awaiting a scan reports re-authentication required, which outranks
  generic provider health.
- **No auto-pairing.** Recovery never fetches a QR and never creates a session — `reconnect_session`
  issues `POST /sessions/{name}/start`, never `POST /sessions`.
- **Runtime registration is opt-in.** `register_waha_runtime()` is explicit and idempotent; merely
  importing the package still registers no runtime, preserving the invariant every milestone through
  QR-05 asserted. Runtime capabilities are asserted never to exceed the adapter's.

**Changed**
- Twelve milestone-boundary guards were re-pointed as `SESSION_RECONNECT`/`SESSION_LOGOUT` moved
  from withheld to declared and stop/logout legitimately began to exist. They now guard what remains
  unimplemented — permanent deletion, history and media transfer.

**Unchanged**
- Migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200 paths, zero QR
  routes, RBAC, generated types, **frontend untouched**, Meta behaviour, and the default
  `ProviderRuntimeRegistry` (still empty). `BULK`/`CAMPAIGNS`/`TEMPLATE` remain permanently
  prohibited. No history/media sync, interactive, reaction, location, contact or UI.

### 2026-08-08 — Fix: WAHA webhook event identity collision

**Fixed**
- `event_identity()` in `app/channels/waha/webhook.py` built its dedupe key by concatenating
  `session`, `event_type` and `envelope_id` and slicing the result to 128 characters, on the belief
  that placing `envelope_id` last made it "survive truncation". That was backwards: Python's
  `s[:128]` keeps the **left** prefix and discards the right tail — placing `envelope_id` last made
  it the first thing cut. Once `session`/`event_type` alone reached 128 characters, every
  `envelope_id` was discarded and two genuinely different events collapsed onto one stored
  `webhook_events.event_id`, defeating the very dedupe scoping QR-04 introduced. A second,
  length-independent collision existed in the same concatenation: plain `":"` delimiters let one
  component's content be mistaken for another's boundary. Both are reproduced as regression tests
  that assert the removed algorithm collided and the replacement does not.
- Replaced with `"waha:" + sha256(canonical).hexdigest()` — a fixed 69 characters, always within
  the 128-character column regardless of any component's length. `canonical` is a netstring-style
  length-prefixed encoding (`f"{len(part)}:{part}|"` per component) that is unambiguous by
  construction, so no adversarial component content can forge a false boundary. Uses
  `hashlib.sha256`, not Python's per-process-randomized `hash()`.
- Corrected the inaccurate "envelope id survives truncation" claim everywhere it appeared:
  `webhook.py`'s docstrings, `VALIDATION_RESULTS.md`, and the QR-05 tracker entry that had reported
  the (wrong) prior review as clean.

**Unchanged**
- Migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200 paths, zero QR
  routes, capabilities (`health`, `qr_auth`, `session_stream`, `text`), RBAC, generated types,
  frontend, Meta behaviour, and QR-05 send/delivery-state code. The fix is confined to
  `event_identity()`/`_canonicalize()`.

**Tests**
- 12 new tests in `tests/test_channel_waha_webhook.py`: the old algorithm reconstructed and shown
  to collide on the same long-input and delimiter-injection cases the new algorithm resolves,
  fixed-length-regardless-of-input-length assertions, five adversarial delimiter cases, a
  50-call determinism check, and a source assertion that `hash()` is not used.
- Full QR-04 suite: 64 passed (52 before). All five WAHA suites: 253 passed together. Full backend
  suite: **1289 passed** (1277 before; +12).

### 2026-08-08 — QR-05: WAHA send path and delivery-state reconciliation

**Added**
- `app/channels/waha/delivery.py` — `WahaAck`, `ACK_TO_STATUS`, `map_ack()`, `to_status_update()`,
  `extract_sent_id()` and `WahaSendIndeterminate`.
- `WahaClient.send_text()` (`POST /api/sendText`) and `message_exists()` — the endpoint-scoped
  reconcile-before-resend lookup.
- `WahaChannelAdapter._dispatch()`, `to_status_update()` and `reconcile_send()`.
- `WahaCredentials.session` / `require_session()` and `WAHA_SESSION_NAME`, mirroring Meta's
  `require_phone_number()`. **This is the endpoint scope.**
- **`TEXT` declared** — text send is implemented and was proven cross-account by certification.
- 46 tests in `tests/test_channel_waha_delivery.py`.

**Behaviour**
- **Monotonicity is inherited, not reinvented.** `messages` already ranks
  `accepted < sent < delivered < read` and `advances()` refuses anything that does not move forward
  (Doc 06 §11.3 / D16). QR-05 only *maps* provider acknowledgements onto that vocabulary — no second
  ordering, no last-write-wins path, no parallel status column. Certification's out-of-order
  `DEVICE(2) → SERVER(1) → READ(3)` becomes `delivered → sent → read`, the late `sent` is ignored,
  and the message ends `read`. Proven for **every permutation** of an interleaved ack sequence.
- **Duplicate acks are idempotent** — QR-04 delivery is at-least-once, so a repeated ack simply does
  not advance. `failed` is terminal and is never overwritten.
- **Unknown acks fail closed.** An uncertified code maps to `None` (no state change) and
  `to_status_update()` raises rather than guessing. A guess could invent progress or, at a low rank,
  look like a regression.
- **Ambiguous sends are never blindly retried.** A transport failure raises `WahaSendIndeterminate`,
  which is deliberately **not** a `ChannelTransportError` so generic retry handling cannot sweep it
  up. A caller must reconcile first and may resend only if the message is proven *absent*; if the
  reconcile lookup itself fails, the error propagates and the outcome stays indeterminate rather
  than being downgraded to "safe to resend". No `resend`/`retry_send` path exists anywhere.
- **Endpoint scoping is structural.** Sends and reconcile lookups both run through
  `require_session()`, and the lookup queries that session's own chat — so one endpoint can never
  confirm or advance another's message, and there is no global provider-message search.
- **Correlation is on the canonical trailing provider id.** The send response is `@s.whatsapp.net`,
  the ack arrives `@lid`, history is `@c.us`; only the trailing component is stable, and that is
  what is matched. Reconciliation matches across all three forms.
- **Text only.** A media, interactive or template send is refused, never degraded into a text send.
- A send that returns no provider id reports `accepted=False`: nothing could correlate an ack or be
  reconciled later, so it is not a success.

**Changed**
- Eight milestone-boundary tests were re-pointed as `TEXT` moved from withheld to declared. Two that
  asserted "QR-05 is not pulled forward" were re-aimed at what genuinely remains unimplemented
  (interactive/media), and the webhook-seam guard now protects Meta's `OFFICIAL_WEBHOOKS`
  handshake, which this provider must never declare.

**Unchanged**
- Migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200 paths, zero QR
  routes, RBAC, generated types, **frontend untouched**, Meta behaviour, and the absence of any WAHA
  entry in `ProviderRuntimeRegistry`. `BULK`/`CAMPAIGNS`/`TEMPLATE` remain permanently prohibited
  and disjoint. No teardown, reconnect, media, history, interactive, reaction, location or contact.

### 2026-08-08 — QR-04: WAHA webhook ingestion

**Added**
- `app/channels/waha/webhook.py` — raw-body sha512 HMAC verification, provider event
  normalization, `event_identity()` and `canonical_message_id()`.
- `WahaChannelAdapter.verify_webhook_signature()` / `parse_webhook()` / `to_inbound_message()`,
  implementing the **existing** generic `ChannelAdapter` seam. No parallel ingest path.
- Configuration `WAHA_WEBHOOK_HMAC_SECRET`, empty by default.
- **`SESSION_STREAM` declared** — earned by implementing ingestion.
- 52 tests in `tests/test_channel_waha_webhook.py`.

**Behaviour**
- **Reuses the existing ingest authority.** Events flow into `WebhookService` → `webhook_events`,
  which already owns persist-first durability, dedupe and dead-lettering. No new table, no new
  route, no second dedupe store, no migration.
- **`envelope.id` alone is not the dedupe key.** Certification proved delivery is at-least-once,
  that a retry repeats both `envelope.id` and `X-Webhook-Request-Id`, and that one provider message
  arrives as both `message` and `message.any` **sharing one `envelope.id`**. `event_identity()`
  scopes the key by session **and** event type, so a retry collapses while two distinct event types
  over one message both survive. Session scoping also prevents cross-tenant collision on a
  provider-chosen id. Determinism is proven by test — including a 64-way concurrent duplicate —
  because `messages` is partitioned and MySQL cannot enforce that uniqueness (error 1503).
- **Signature is verified before parsing**, over the raw bytes the provider signed, with
  `hmac.compare_digest`. An absent, malformed or wrong-algorithm signature is a rejection.
  A body over 1 MiB is refused **before** hashing.
- **An unset secret rejects every delivery** — an unconfigured deployment cannot silently accept
  unsigned provider traffic. There is no default secret.
- **Unknown shapes fail closed but are never dropped.** Unrecognised event types and malformed
  envelopes become `UNKNOWN` so Doc 06 §11.6 can dead-letter them for inspection. A malformed
  envelope carries **no** `event_id`, so two different malformed deliveries can never collapse.
- **Outbound echoes and acknowledgements are recorded, not applied.** `fromMe: true` and
  `message.ack` become `UNKNOWN`; delivery-state persistence is QR-05.
- **Identity evidence is preserved, not normalised away.** `@c.us`/`@lid`/`@s.whatsapp.net` survive
  into the stored payload; the canonical trailing provider message id is exposed alongside. No
  global provider-message lookup is performed.
- **Media inbound is not faked as empty text** — it is reported as `unsupported` with a
  `provider_has_media` flag rather than being rendered as a blank message.

**Changed**
- Five milestone-boundary tests were re-pointed as `SESSION_STREAM` moved from withheld to declared.
  `test_adapter_declares_no_webhook_ingestion` now guards `to_status_update` (QR-05) instead of the
  webhook methods QR-04 was always scoped to implement.

**Unchanged**
- Migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200 paths, zero QR
  routes, RBAC, generated types, frontend, Meta behaviour, and the absence of any WAHA entry in
  `ProviderRuntimeRegistry`. `BULK`/`CAMPAIGNS`/`TEMPLATE` remain permanently prohibited. No send
  path, no delivery-state persistence, no teardown, no history/media execution, no UI.

### 2026-08-08 — QR-03: WAHA QR pairing

**Added**
- `app/channels/waha/pairing.py` — `CERTIFIED_NOWEB_STORE`/`build_session_config()` (the session
  configuration certification proved is required) and `WahaQrChallenge`, a transient QR value that
  redacts its own bytes.
- `WahaClient.create_session(name)` — `POST /api/sessions`, the first provider **write**.
- `WahaClient.qr_challenge(name)` — `GET /api/{session}/auth/qr`, returning raw image bytes.
- `WahaChannelAdapter.begin_pairing()` / `pairing_challenge()` / `pairing_state()`.
- **`QR_AUTH` is now declared** — the first capability added since QR-01, earned by implementing
  pairing and proven end-to-end by physical-phone certification.
- 30 tests in `tests/test_channel_waha_pairing.py`, fully hermetic via `httpx.MockTransport`.

**Behaviour**
- **Up, but never down.** QR-03 can create and start a session; it deliberately has no stop,
  restart, logout or delete. Teardown is QR-06, so nothing shipped so far can destroy a working
  pairing. Asserted by test on both adapter and client.
- **`fullSync` is camelCase, in exactly one place.** Certification proved the provider accepts
  `full_sync` with HTTP 201 and then silently stores `fullSync: false`, leaving a session that looks
  healthy with no history. The payload is built centrally and asserted by test so the trap cannot be
  reintroduced per call site.
- **The QR challenge is treated as a secret.** It is never persisted, never logged, excluded from
  the dataclass `repr`, and `repr`/`str` render `data=***withheld***`. This preserves M13-05's
  boundary that QR images and challenge bytes are never stored.
- **Pairing safety.** `pairing_state()` returns `None` for `STARTING`/`STOPPED`/`FAILED` and callers
  must leave durable pairing truth untouched — certification proved `STARTING` occurs both for a
  fresh session and for an already-paired session restarting, so inferring "unpaired" would discard
  a real pairing on a transient restart.
- **No guessing on conflict.** If the provider reports a session of that name already exists, the
  error surfaces rather than the session being silently reused or recreated.
- **Fails closed** on a non-image QR response (an HTML login page or JSON error is never handed back
  as a QR), on an unapproved engine, and on an invalid session name before any URL is built.
- **Capability-gated before I/O**: without `QR_AUTH` all three pairing methods raise
  `ChannelNotSupported` and open no connection.

**Changed**
- Two milestone-boundary tests were re-pointed rather than deleted, because the boundary legitimately
  moved: bringing a session **up** is now allowed, tearing one **down** still is not. `QR_AUTH` was
  removed from the withheld-capability list and the capability assertion now expects
  `{HEALTH, QR_AUTH}`. `send_text` was dropped from one forbidden-name list — it is an inherited
  generic `ChannelAdapter` method present on every adapter, so its presence proved nothing; the send
  path is now asserted **behaviourally** to still raise `ChannelNotSupported`.

**Unchanged**
- Migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200 paths, RBAC,
  generated types, frontend, Meta behaviour, and the absence of any WAHA entry in
  `ProviderRuntimeRegistry`. `BULK`/`CAMPAIGNS`/`TEMPLATE` remain permanently prohibited and
  disjoint from the declared set. No webhook ingestion, send path, media, history, runtime or UI.

### 2026-08-08 — QR-02: WAHA session lifecycle read and provider-neutral mapping

**Added**
- `app/channels/waha/lifecycle.py` — `WahaSessionStatus` (the five statuses observed during
  physical-phone certification), a pure `map_session_status()` translating each to the platform's
  own `SessionState`/`PairingState`, `WahaSessionSnapshot`, and strict session-name validation.
- `WahaClient.session_status(name)` — one authenticated read, `GET /api/sessions/{name}`.
- `WahaChannelAdapter.session_snapshot(name)` / `session_status(name)` — provider-neutral lifecycle
  for a session the caller names.
- 54 tests in `tests/test_channel_waha_lifecycle.py`, fully hermetic via `httpx.MockTransport`.

**Behaviour**
- **Read-only.** QR-02 adds exactly one authenticated read. No session is created, started,
  stopped, restarted, paired or logged out; adapter and client are asserted to expose no such
  method. Driving a lifecycle is QR-03 (pairing) and QR-06 (reconnect/health).
- **No capability added.** Capabilities remain exactly `HEALTH`. Observing a lifecycle is not being
  able to drive one, and `PROHIBITED_CAPABILITIES` is untouched.
- **Ambiguous statuses refuse to guess a pairing state.** `STARTING`, `STOPPED` and `FAILED` return
  no pairing state. Certification observed `STARTING` both on a fresh session (`→ SCAN_QR_CODE`) and
  on a controlled restart of a paired one (`→ WORKING` with no new QR), so the status alone cannot
  distinguish "never paired" from "paired and reconnecting". The caller keeps its durable state
  rather than having it overwritten by an inference.
- **`FAILED` maps to `degraded`, not a terminal state**, because certification recovered a `FAILED`
  session with a controlled restart.
- **Order-independence by construction.** Certification observed acknowledgements arriving out of
  order (`DEVICE(2) → SERVER(1) → READ(3)`). QR-02 introduces no delivery-state persistence at all,
  and the mapping is a pure function of status, so no arrival order can regress state.
- **Fails closed on an uncertified status**, without echoing the raw provider value.
- **Session names are validated, not escaped**, before reaching a request path; a traversal attempt
  opens no connection.
- **Both `@c.us` and `@lid` are retained** — certification proved one account is addressed both
  ways — so provider-neutral identity boundaries are preserved rather than normalised away here.
- **Server health is still not session health.** `authenticate()`/`status()` remain
  `connected=False`; only `session_status(name)` may report a live session, and only for `WORKING`.

**Fixed**
- `authenticate()` detail said QR pairing arrives in "QR-02+". QR-02 exists and does not implement
  pairing, so the reference was corrected to `QR-03`. Documentation-only string; no behaviour change.

**Unchanged**
- Migration head `0042_scope_provider_message_identity` (43 revisions), OpenAPI 200 paths, RBAC,
  generated types, frontend, Meta behaviour, and the absence of any WAHA entry in
  `ProviderRuntimeRegistry`. No QR API, QR UI, webhook ingestion, send path, media or history.

### 2026-08-07 — QR-01: WAHA provider adapter foundation

**Added**
- `app/channels/waha/` — the `waha` provider adapter behind the existing `ChannelAdapter` seam
  (ADR-0021 Class B). Connector identity `connector_type="waha"` on channel family
  `channel_type="whatsapp"`: a second *implementation* of the same channel, never a second channel
  and never a parallel hierarchy.
- `app/channels/waha/client.py` — a minimal typed async client implementing exactly the two
  authenticated reads QR-01 needs: the server version/engine banner and `/health`.
- Configuration `WAHA_BASE_URL`, `WAHA_API_KEY`, `WAHA_TIMEOUT_SECONDS`,
  `WAHA_CERTIFIED_VERSION` (`2026.7.2`), `WAHA_APPROVED_ENGINE` (`NOWEB`). Unconfigured by
  default with **no default API key**; the application boots normally with none of them set.
- 63 tests in `tests/test_channel_waha_adapter.py`, fully hermetic via `httpx.MockTransport`.

**Behaviour**
- **Capabilities are deliberately minimal: only `HEALTH`.** The QR-00 spike proved the *provider*
  supports QR pairing, sessions, media and history, but a provider endpoint existing is not the
  same as this adapter being able to use it, and neither is the same as a paired WhatsApp account
  working. `QR_AUTH`, `SESSION_STREAM`, `SESSION_RECONNECT`, `SESSION_LOGOUT`, `HISTORY_SYNC`,
  `TEXT`, `MEDIA`, `MEDIA_UPLOAD`, `MEDIA_DOWNLOAD`, `INTERACTIVE`, `REACTION`, `LOCATION` and
  `CONTACT` are all withheld until the milestone that implements them.
- **`BULK`, `CAMPAIGNS` and `TEMPLATE` are permanently prohibited** for this provider (ADR-0020
  section 5, ADR-0021, owner Class B approval) — recorded in `PROHIBITED_CAPABILITIES` and enforced
  by tests that no future milestone may quietly relax.
- **Server health is not session health.** `authenticate()`/`status()` return `connected=False`
  with an explicit "No WhatsApp session" detail, and `health_signal()` labels itself
  server-health-only. A healthy WAHA server with zero paired sessions cannot message.
- **Deterministic error mapping**, each shape observed against the real certified build: timeout and
  unavailable to `ChannelTransportError` (distinct messages); 401/403 to `ChannelAuthError`; 5xx and
  other reached errors to `ChannelApiError` carrying the status; malformed JSON, unexpected content
  type (the real server answers `text/html` on its root path) and non-object JSON to
  `ChannelApiError`; unconfigured to `ChannelConfigError` before any socket opens.
- **Version/engine safety.** Certified baseline `2026.7.2`, `NOWEB` only. An unexpected engine fails
  closed because payload shapes differ between engines. Version drift is reported, never
  auto-corrected; nothing upgrades a provider on its own.
- **Registration is inert.** Static registration opens no socket, requires no API key and starts no
  runtime, so the provider is *resolvable* but *disabled*. `ProviderRuntimeRegistry` deliberately
  gains no WAHA runtime.

**Security**
- API key sent only as `X-Api-Key`; never logged, never echoed into an exception message, masked in
  `repr`. Provider error bodies are never quoted (they are attacker-influencable); the warning log
  records status and path only. No QR material exists to persist. Meta webhook security and the
  QR-00 endpoint-scoped provider-message identity are unchanged.

**Verified**
- An isolated `devlikeapro/waha:noweb-2026.7.2` (digest `sha256:33ecd1b7...`) was run locally on
  `127.0.0.1` and the committed adapter driven against it: 11/11 checks covering authenticated
  version/engine, authenticated health, wrong-key and missing-config rejection, unavailable, timeout,
  non-JSON handling and the engine guard. **No session was created, no QR requested, no phone
  paired, nothing sent or received.** Torn down afterwards with all credentials and artefacts
  removed; the committed `docker-compose.yml` was not edited.
- Ruff, strict mypy (292 files), **1099 backend tests (0 skipped)**, `export_openapi.py --check`
  (200 paths, unchanged) and `quality_gate.py static` all pass.

**Preserved**
- No migration (head remains `0042_scope_provider_message_identity`, 43 revisions), no OpenAPI
  change, no RBAC change, no generated-type change, no frontend change. Meta Cloud behaviour is
  untouched.
- **QR login does not work and is not claimed to.** No WhatsApp session, QR generation, pairing,
  webhook ingestion, send path, media or history transfer, session worker or UI exists. QR-02
  through QR-09 and physical-phone certification all remain pending; no Production Ready, Host
  Validated, provider-certified or M13-07 claim is made.


### 2026-08-07 — QR-00: WAHA Class B provider selection and provider-message identity foundation

**Added**
- `docs/evidence/provider-evaluations/waha-class-b-selection-record.md` — the Design Document 33
  §6.4 provider-selection record. WAHA 2026.7.2 (tier CORE, engine NOWEB, Apache-2.0) is selected as
  the ADR-0021 **Class B** owner-approved internal self-hosted candidate. Owner Approval,
  Architecture Approval, Security Approval and explicit acceptance of WhatsApp restriction/ban risk
  are recorded verbatim. Certification remains **CONDITIONALLY CERTIFIED — HOST/PHONE EVIDENCE
  REQUIRED**; production certification is not granted. Succeeds, without rewriting, the earlier
  `waha-class-b-evaluation.md`.
- `app/channels/attention.py` — provider-neutral `SessionAttentionState` projection supplying the
  four Design Document 33 §6.1 operator signals (Healthy / Warning / Critical / Re-auth Required)
  by **deriving** re-authentication from the existing `SessionState` + `PairingState` rather than
  adding a fourth persisted health value. Re-auth outranks observed health; a `TERMINATED` session
  never reports re-auth.
- `alembic/versions/0042_scope_provider_message_identity.py` — additive, index-only migration adding
  `ix_msg_endpoint_wamid (phone_number_id, wamid)`. No column added, no backfill, no data change.
- 21 tests in `tests/test_provider_message_identity.py` covering endpoint/tenant isolation and the
  full re-authentication projection.

**Fixed**
- **Provider message identity was globally resolvable.** `MessageRepository.get_by_wamid(wamid)`
  looked a provider message id up with no organization, connection or endpoint filter. Safe only
  while Meta — whose `wamid` is globally unique — was the sole provider; a QR/multi-device provider's
  ids are session-scoped and may legitimately repeat across endpoints, which would have let one
  endpoint resolve, or a delivery receipt advance, another endpoint's or another tenant's message.
  This contradicted ADR-0020 ("provider message identity is scoped by connection/endpoint").
  Replaced by `get_by_provider_message_id(provider_message_id, *, phone_number_id)`, whose scope is
  keyword-only and required so an unscoped lookup cannot be written; no global variant remains.
  `apply_status` now receives the endpoint the callback arrived on.

**Verified**
- No backfill was required: `messages.organization_id`/`phone_number_id` have been `NOT NULL` since
  `0016_conversations_messages`, so ownership is already explicit rather than derived. Live database
  check: 191 messages, 0 null owners, 0 orphaned endpoints, 0 organization mismatches, 0 duplicate
  `(phone_number_id, wamid)` pairs.
- A UNIQUE constraint is impossible and is recorded as such: MySQL error **1503** rejects a unique
  index that omits the partitioning columns, and `messages` is `PARTITION BY RANGE
  COLUMNS(created_at)`. Reproduced on MySQL 8.0.46. Uniqueness remains enforced by the scoped read
  plus the persist-first ingestion path, as it already was for Meta.
- Real MySQL 8: fresh base → `0042` and `0041` → `0042` with pre-existing data preserved.
- Ruff, strict mypy (289 files), **1036 backend tests (0 skipped)**, `export_openapi.py --check`
  (200 paths, unchanged) and `quality_gate.py static` all pass.

**Preserved**
- Meta Cloud behaviour is unchanged — webhook ingestion, inbound deduplication, delivery/read
  reconciliation and Inbox suites pass unmodified. No API route, schema, RBAC entry, generated
  frontend type or frontend file changed.
- **QR login is not implemented and is not claimed.** QR-00 adds no WAHA client, adapter, Docker
  service, provider runtime registration, QR API, QR image endpoint, QR persistence, QR frontend,
  webhook endpoint, inbound ingestion, outbound send, history sync, media sync, session worker or
  reconnect runtime. Only `meta_cloud` is a registered adapter. QR-01 through QR-09 and
  physical-phone certification all remain pending; no Production Ready, Host Validated or M13-07
  claim is made.


### 2026-08-07 — Alembic version-table MySQL fix: support long revision ids

**Fixed**
- `alembic upgrade head` failed on a real MySQL 8 database while transitioning
  `0035_notification_center → 0036_customer_identity_resolution` with
  `DataError: Data too long for column 'version_num'`. Root cause: Alembic's own bookkeeping
  column, `alembic_version.version_num`, defaults to `VARCHAR(32)`; this repository's descriptive
  revision-id convention produces identifiers up to 43 characters, and
  `0036_customer_identity_resolution` (33 characters) was the first to exceed it. No real MySQL
  deployment had ever advanced past `0035_notification_center` — this blocked schema creation,
  `create-owner`, authentication, and every real UI preview on MySQL.
- Repaired with a new migration, `0035a_widen_version_table`, inserted between
  `0035_notification_center` and `0036_customer_identity_resolution`, widening
  `alembic_version.version_num` to `VARCHAR(255)` on MySQL only (dialect-guarded; SQLite enforces
  no such length and PostgreSQL is not part of this stack). `0036_customer_identity_resolution`'s
  `down_revision` was retargeted to the new revision — its own revision id, schema body and
  behaviour are unchanged. No revision was renamed, renumbered, squashed, reordered, or stamped
  past a failure; the migration head remains `0041_channel_sync_control_plane` and the chain stays
  linear with a single head.

**Added**
- Three hermetic regression tests in `test_migrations.py`: single migration head, linear revision
  chain (no merges), and every revision id fits the widened column (with an early-warning margin).
- A new `test_migrations_mysql.py`: three tests against a real, throwaway-per-test MySQL 8
  database — fresh base→head, upgrade from `0035_notification_center` to head (the exact
  historical failure), and `create-owner` immediately after. Skipped cleanly (never failed) when
  no MySQL server is reachable, so the hermetic default suite gains no new external dependency.

**Verified**
- Real MySQL 8, both automated (throwaway databases) and manual (the documented CLI workflow
  against a fresh `docker compose` instance): fresh base→head succeeds; `0035`→head succeeds;
  `python -m app.cli create-owner` succeeds and is idempotent on re-run.

**Preserved**
- No application endpoint, model, schema, RBAC definition, ADR, provider/Meta/WAHA code, or
  frontend file changed. `scripts/export_openapi.py --check` and the full static quality gate both
  pass unchanged.
- Does not unblock the separate Chat History UI-preview gap: a real, populated `/chat-history`
  screenshot still requires either live Meta WhatsApp Business API credentials or an approved
  development fixture mechanism for conversation/message data, neither of which exists. This fix
  repairs the schema/auth path only. No Host Validated or Production Ready claim is made.

### 2026-08-07 — Chat History pagination/polling/accessibility hardening (audit findings D1–D8)

**Fixed**
- Removed the Chat History conversation list's Previous control, which could never activate — the
  backend never returns `prev_cursor`. Replaced it with a forward-only `Next` plus a `Back to
  newest` reset, shown only once a later page has been loaded, that returns to the same bounded
  25-row first page rather than any backend cursor contract change.
- `useConversation`/`useMessages` (`features/inbox/api.ts`) gained an optional trailing
  `refetchInterval` parameter, defaulting to the existing 10s poll every current caller relies on;
  Chat History passes `false` for the selected conversation's detail and messages, since a
  read-only archive view has no live-triage need for it. Live Chat and Customer 360 are
  unaffected — neither passes the new argument.
- Selecting a conversation below the route's own `lg` list/detail breakpoint now moves focus into
  the detail pane (the "Back to conversation history" button); returning to the list restores
  focus to the row that was open. Neither happens at or above `lg`, where both panes stay visible.
  Reuses the existing `useMediaQuery` utility rather than a new breakpoint mechanism.
- The `contact` deep-link filter now participates in active-filter detection, so a contact filter
  matching nothing shows the same "No conversations match" / Clear filters state every other
  filter does, instead of the global "no history at all" empty state.
- The conversation list's status badge now colors `open` as success and every other status as
  neutral, matching Live Chat's own `ConversationList.tsx` convention exactly (previously every
  non-resolved status, including pending and snoozed, read as success).
- The message list gained `aria-label="Message history"`; the page title is now a real `<h1>` and
  the selected thread's contact name a real `<h2>` (matching `ConversationThread.tsx`'s own
  heading level for the identical field) — the route previously contributed no heading at all.

**Added**
- Twelve new tests in `chat-history.test.tsx` covering all of the above, plus a direct regression
  proving no conversation-detail or message request is made before a conversation is selected.

**Preserved**
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path, RBAC
  definition or generated type changed; no new permission was introduced.
- `MODULE_STATUS.md`'s Chat History pending-work wording was corrected to keep naming media-only
  and audit-scoped filtering alongside the existing date-range/campaign-generated/export/Download
  Center gaps; completion remains `55%`, unchanged by this hardening pass.
- Audit findings D9–D12 (the `<time>` `dateTime` attribute, the `/phone-numbers` duplicate cache
  key, general test observations, button-vs-anchor deep links) were left untouched, as instructed.

### 2026-08-07 — Dedicated Chat History read workspace over the existing conversation and message contract

**Added**
- Added a `/chat-history` route and `inbox:read`-gated navigation entry: a read-only list/detail
  workspace over the same `GET /conversations`, `GET /conversations/{id}` and
  `GET /conversations/{id}/messages` endpoints Live Chat and Customer 360 already read. Reuses
  `useConversations`, `useConversation`, `useMessages` and `useAssignableUsers` from
  `features/inbox/api.ts` verbatim — no second conversation/message query authority was opened.
- Search, status, assignee and tag filters map onto the identical query params Live Chat's own
  filters already send. A new `number` (channel) filter is additive on the shared
  `InboxFilters`/`toListQuery` types both surfaces read from one definition — the backend already
  accepted `number`; only the frontend type was missing it.
- Cursor pagination for the conversation list and the existing infinite-query "Load older
  messages" control are both reused as-is, so neither list nor message history ever fetches an
  unbounded page.
- A deep link opens the selected conversation in Live Chat (`/inbox?conversation={id}`, the exact
  shape Live Chat's own route already parses); a second deep link to the audit trail is shown only
  to `audit:read` holders and hidden otherwise, following the same pattern Customer 360 already
  uses.
- The route exposes no assignment, status, tag, note or send control — those remain Live Chat's
  job. Date-range and campaign-generated filtering, and transcript export, are named in the page
  header as not yet available rather than offered as disabled controls, since none is backed by
  the current contract.
- Twenty-two focused tests, plus updates to `inbox.test.tsx`'s `toListQuery` fixtures and
  `phase1-foundations.test.ts`'s exact-order navigation assertion for the additive `number` field
  and new nav entry.

**Preserved**
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path, RBAC
  definition or generated type changed. No new permission was introduced.
- Closes the frontend half of `ROADMAP.md`'s `CORE-10 — Dedicated Chat History`; its backend
  "Conversation query extensions" (a date-range query param, `MessageResponse.campaign_id`) and
  export capability are not implemented and remain recorded, open follow-up — not claimed here,
  not M13-07, and `ROADMAP.md` itself is unmodified.

### 2026-08-06 — User Attributes management interface over the existing Custom Attribute contract

**Added**
- Added a Settings → User Attributes panel over the existing `GET/POST/PATCH/DELETE
  /api/v1/custom-attributes` endpoints. The contract was already complete — typed definitions
  (`string`/`number`/`datetime`/`boolean`/`enum`), org-scoped key uniqueness, `is_indexed`/`is_pii`
  flags — but the frontend only ever issued the list read consumed by the Contacts filter bar,
  campaign audience rules and segment predicates, so no organization could define a typed field
  from the product itself.
- Create, edit and delete for `contacts:write` holders. `key_name` and `data_type` are immutable
  after creation — the update contract carries no field for either — so the edit dialog presents
  both as read-only facts (via the same `DefinitionRow`/`<dl>` pattern used for Canned Messages'
  read-only scope) rather than disabled controls that would silently do nothing.
- Search across key name and label; a data-type filter; `Indexed`/`PII` shown as informational
  badges. The delete confirmation states plainly that removing a definition also removes every
  contact's stored value for it, matching the endpoint's real behaviour.
- Twenty-three focused tests, including three pure-function tests for the comma-separated
  enum-choice parser and its validation, and a cache-refresh regression against the real
  `useCustomAttributeDefinitions` hook the Contacts page already imports from
  `customer-profile/api.ts`, under one shared `QueryClient`.

**Preserved**
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path or generated
  type changed; migration head remains `0041_channel_sync_control_plane` and the contract remains
  drift-free.
- Only contract fields are shown; no status, category, required/active flag or other unsupported
  field was invented. `is_pii` is described honestly as not yet enforced elsewhere, since nothing
  else in the codebase reads it.

### 2026-08-06 — Canned message scope accessibility fix

**Fixed**
- The Canned Messages edit dialog showed its read-only Scope information through a `Field
  htmlFor="canned-message-scope"` label pointing at a plain `<div>`, which is not a labelable
  element and created no real accessible association. Replaced with the `DefinitionRow`/`<dl>`
  pattern already used for read-only information elsewhere in Settings (`OrganizationPanel`,
  `ApplicationPanel`) — no fake form control, no behaviour change.

### 2026-08-06 — Canned Messages management interface over the existing Quick Reply contract

**Added**
- Added a Settings → Canned Messages panel over the existing `GET/POST/PATCH/DELETE
  /api/v1/quick-replies` endpoints. The contract was already complete — personal and shared canned
  replies, scope-aware shortcut uniqueness, soft delete — but the frontend only ever issued the list
  read from the Message Composer's `/shortcut` picker, so on an organization with no canned messages
  yet the picker stayed permanently empty with no way to populate it from the product.
- Create, edit and delete are offered to `inbox:write` holders; `shared` (Personal/Shared) is
  selectable only at creation, matching the immutable-after-creation contract — the edit dialog shows
  scope as read-only information rather than a control that would silently do nothing.
- Search across shortcut, title and body; a scope filter (All/Personal/Shared); a one-line body
  preview in the table. `usage_count` is read but not shown — no send path increments it yet, so
  presenting it as live usage would be dishonest.
- A minimal, permission-correct addition to the Message Composer's empty quick-reply state: an
  `inbox:write` agent gets a link to Settings → Canned Messages; a read-only agent sees the same
  empty message with no link, never a misleading action they cannot use.
- Eighteen focused Settings tests and two focused Inbox tests, including a regression that renders
  the panel beside the real `useQuickReplies` hook `MessageComposer.tsx` imports from `inbox/api`,
  under the identical `["quick-replies"]` cache key, and proves a create through Settings refreshes
  the composer's own picker without a manual reload.

**Preserved**
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path or generated
  type changed; migration head remains `0041_channel_sync_control_plane` and the contract remains
  drift-free.
- Only contract fields are shown; no status, category, favourite, pinning, created-by display, AI
  generation or unsupported ownership field was invented.

### 2026-08-06 — Focused Tag Management audit follow-up: regression coverage and accessibility/error-state hardening

**Fixed**
- Reset stale `create`/`update`/`delete` mutation state when a Tags panel dialog opens, so a
  previous failure can no longer resurface as a false error the moment a different tag's dialog is
  opened.
- Moved the failed-delete error into the confirmation modal itself; it previously rendered behind
  the still-open modal's backdrop and was not genuinely visible at the moment of failure.

**Added**
- Six regression tests: cross-feature cache-invalidation (proved against the real `useTags` hooks
  in `customer-profile/api.ts` and `campaigns/api.ts` under one shared `QueryClient`, no new
  cache-key system), a duplicate-name 409 conflict, a failed delete with retry, an explicit loading
  state, per-tag accessible row-action names (e.g. `Edit Prepaid`), and a dedicated proof that a
  failed attempt's error does not resurface when a dialog is later opened for a different tag.

**Preserved**
- Frontend only: no backend file, migration, endpoint, permission code, OpenAPI path or generated
  type changed. Not a roadmap milestone, not M13-07; Settings/Tags/Attributes completion claims are
  unchanged.

### 2026-08-06 — Tag management interface (verified UI remediation)

**Added**
- Added a Settings → Tags panel so the organization's tag vocabulary can be created, renamed,
  recoloured, described and deleted from the product. The existing `GET/POST/PATCH/DELETE
  /api/v1/tags` contract was already complete, but the frontend only ever issued the list read, so
  no tag could be created anywhere in the UI.
- The panel reuses the shared enterprise primitives (`Section`, `FilterBar`, `Input`, `Select`,
  `Button`, `Badge`, `Modal`, `Pagination`, `EmptyState`, `ErrorState`, `TagChip`) and the generated
  API client; search, a usage filter, client-side paging, a live tag preview, inline validation and a
  delete confirmation that states how many contacts would be detached.
- Added ten focused tests covering listing, the persistent create action on an empty organization,
  create/edit/delete requests, search and usage filtering, colour validation, the read-only
  experience without `contacts:write`, and the error retry.

**Preserved**
- Frontend only. No backend file, migration, endpoint, permission definition, OpenAPI path or
  generated contract type changed; migration head remains `0041_channel_sync_control_plane` and the
  contract remains drift-free.
- Tags carry no status column in the contract, so the second filter is usage, derived from the
  `usage_count` the existing read already returns. No backend field was invented, and the reference
  product's `First Message` tag concept was deliberately not reproduced.
- Reads stay on `contacts:read` and writes on `contacts:write`, exactly as the endpoints enforce;
  users without write permission see no create, edit or delete control at all.

### 2026-08-05 — Provider-neutral History & Media Control Plane (M13-06B)

**Added**
- Added the repository-owned lifecycle service over the existing M13-06A history checkpoints and
  media references: create/reopen, bounded transitions, monotonic progress, factual media observations,
  optimistic concurrency, tenant/object authorization, feature flags, dedicated RBAC and Audit evidence.
- Added the frozen `channels:history_sync` permission through additive migration
  `0041_channel_sync_control_plane`; no table, provider dependency or public API was introduced.
- Added focused regressions for lifecycle legality, resume/fresh-run semantics, permission and flag
  failure, tenant isolation, capability gating, secret rejection, idempotency and API absence.

**Preserved**
- No provider is certified. No adapter, QR payload/login, provider cursor, event ingestion, history
  retrieval, media-byte transfer, queue execution, messaging, webhook, frontend or generated contract
  exists in M13-06B.
- ADR-0020, ADR-0021 and Design Document 33 remain frozen and authoritative.

**Validated**
- Workflow `31038662241` passes Ruff, strict mypy, OpenAPI/client drift, 985 backend tests,
  36 frontend files / 671 tests, production build, E2E types, SAST, dependency audits and tracked-source
  vulnerability/secret/IaC scanning.
- Migration upgrade/downgrade/re-upgrade passes at `0041_channel_sync_control_plane`; OpenAPI remains
  200 paths and the main application bundle remains `199.78/54.87 kB gzip`.
- M13-06B reaches `Repository Validated`; live provider-dependent history/media behavior remains
  blocked by certification and Host Machine Validation.

### 2026-08-05 — Owner review, release candidate audit and merge readiness (UI-TASTE-05)

**Fixed**
- Removed the verified campaign create/edit lazy-chunk execution cycle by importing the existing
  `CampaignWizard`, form helpers and types from their direct modules instead of the campaigns barrel.
- Preserved the existing campaign workflow, API, permissions, route boundaries and feature behavior.

**Reviewed**
- Audited Dashboard, Reactivation, Contacts, Customer 360, Inbox, Campaigns, Templates, Analytics,
  Notifications, Settings, Authentication, RBAC, Customer Identity, shared components and the
  provider-neutral Module 13 foundations as one release candidate.
- No second authority, architecture drift, governance expansion, provider work or roadmap resequencing
  was introduced.

**Validated**
- Release-candidate workflow `30982637585` passes repository lint, strict typing, OpenAPI/client drift,
  980 backend tests, 36 frontend files / 671 tests, clean production build, E2E types, SAST, dependency
  audits and tracked-source vulnerability/secret/IaC scanning.
- Main application JavaScript remains `199.78/54.87 kB gzip`; the campaign chunk-order warning is absent.
- Authenticated representative-data browser/device/screen-reader and production-scale evidence remains
  `PENDING – Host Machine Validation`.

### 2026-08-05 — Responsive, accessibility and performance regression (UI-TASTE-04)

**Changed**
- Added the existing `kyc:read` route guard to the Reactivation KYC deep link without changing the
  permission catalog or backend authorization.
- Debounced permission-aware workspace record search and kept loading feedback truthful while
  preserving the existing bounded APIs.
- Lazy-split authenticated page and administrative panel routes behind the existing shell and route
  guards; no route, workflow or API contract changed.
- Made shared pagination wrap safely on narrow layouts and made shared modals lock background
  scrolling while retaining focus entry, trapping, Escape handling and focus restoration.

**Fixed**
- Prevented empty search-result collections from producing an invalid negative keyboard selection.
- Replaced the keyboard-shortcut overlay with the shared modal authority.
- Removed the verified unused `ComingSoonPage` and its obsolete test.

**Preserved**
- No new feature, API, migration, dependency, governance, architecture, provider, QR, runtime,
  messaging, history, media or production-credential work was introduced.
- Reactivation remains 94%; Module 13 remains 44%; all provider-dependent behavior remains blocked.

**Validated**
- Repository pre-merge quality gate passed in workflow `30980229127`: Ruff, strict mypy, OpenAPI drift,
  980 backend tests, ESLint, TypeScript, 36 frontend files / 671 tests, production build, E2E types,
  Bandit, dependency audits and tracked-source vulnerability/secret/IaC scan.
- Main application JavaScript reduced from 733.97/178.29 kB gzip to
  199.78/54.87 kB gzip through authenticated route splitting.
- Authenticated representative-data browser/device/screen-reader and production-scale performance
  evidence remains `PENDING – Host Machine Validation`.

### 2026-08-05 — Reactivation operational hierarchy (UI-TASTE-03B)

**Added**
- Added bounded offset pagination to the existing tenant-scoped Reactivation pipeline query and
  shared previous/next controls at 25 cases per page.
- Added URL-backed search, status, label, owner, reminder, date, display, page, and factual work-view
  state without claiming server-shared saved views.
- Added Design Document 34 and focused backend/frontend regressions for hierarchy, permission truth,
  redirects, pagination, terminal movement, and existing case workflows.

**Changed**
- Made the real Reactivation CRM the default Reactivation destination and limited primary
  sub-navigation to connected, permission-available CRM, KYC, Document, and Report surfaces.
- Redirected historical SIM, Activation, Completed, Interested, and bulk-eligibility routes to the
  existing filtered CRM or Contact import authorities.
- Reused shared filter, form, toolbar, pagination, loading, empty, error, and modal components;
  strengthened visible due/SLA/owner/document/next-task hierarchy.

**Fixed**
- Removed foundation-only executable-looking placeholder navigation and outdated KYC gating copy.
- Hid KYC, Document, and Report tabs when the existing route permission is absent.
- Stopped terminal cases from advertising drag behavior, fixed malformed result-summary encoding,
  and removed the 200-card unpaginated render path.
- Corrected governance stop wording so provider certification blocks Module 13 live/provider UI,
  not unrelated provider-neutral product milestones.

**Preserved**
- No provider evaluation, certification, WAHA, Evolution API, QR runtime, live session, ingestion,
  history synchronization, media transfer, provider dependency, migration, permission, audit, or
  tenant-authority change.
- Module 13 remains 44% and all provider-dependent work remains blocked.

**Validated**
- Ruff, strict mypy, OpenAPI/client drift, 4 focused backend tests, all
  980 backend tests, ESLint, TypeScript, 35 frontend files /
  668 tests, production build, E2E TypeScript, dependency audits, Bandit, and tracked
  source vulnerability/secret/IaC scan passed in workflow `30953600784`.
- Migration head remains `0040_channel_sync_media_foundation`; OpenAPI remains 200 paths.
- Authenticated representative-data visual/WCAG/device/performance acceptance remains
  `PENDING – Host Machine Validation`.

### 2026-08-05 — Provider-neutral Sync & Media Persistence Foundation (M13-06A)

**Added**
- Added the frozen-contract `channel_sync_checkpoints` and `media_channel_references` records with
  organization, connection/endpoint, checkpoint/progress, expiry, transfer-state, Audit and optimistic-
  concurrency facts.
- Added tenant-scoped repositories and provider-neutral sync/media state vocabulary, including the
  existing capability seam's `history_sync` value.
- Added migration `0040_channel_sync_media_foundation` and focused repository, tenant, secret-redaction,
  uniqueness, constraint and migration regressions.

**Preserved**
- No provider is certified. WAHA remains `Requires Additional Evidence`.
- No provider adapter, dependency, live QR pairing, live event ingestion, history job, media transfer,
  queue task, API route, generated contract, frontend behavior or production runtime was added.
- Existing Contact, Conversation, Message, MediaAsset, ChannelAdapter, ChannelConnection,
  ChannelSession, queue, RBAC, tenant, feature-flag and Audit authorities remain unchanged.

**Validated**
- Ruff and strict mypy pass; 18 focused tests and all 979 backend tests pass in workflow
  `30946554198`.
- Migration upgrade/downgrade/re-upgrade passes at `0040_channel_sync_media_foundation`.
- OpenAPI remains semantically unchanged at 200 paths; generated TypeScript and unchanged frontend
  lint, types, tests and production build pass.
- M13-06A reaches `Repository Validated`; all live provider-dependent M13-06 behavior remains blocked
  by certification and host evidence.


### 2026-08-04 — QR Pairing & Provider Runtime Foundation (M13-05)

**Added**
- Added provider-neutral runtime metadata/lifecycle/event/health contracts and a runtime registry over the existing `ChannelAdapter` seam.
- Added tenant-scoped runtime registration/discovery/ownership, capability publication, health/lifecycle reporting, heartbeat, restart/recovery metadata and durable session integration.
- Added a no-store pairing lifecycle with governed request/available/expired/cancelled/paired/active transitions, dedicated feature flags/RBAC/Audit and migration `0039_qr_pairing_provider_runtime_foundation`.

**Security**
- Runtime reports require valid lease fencing, pairing TTL and expiry are enforced, expiry sweeps are bounded, reason codes are constrained, and no QR payload, token, protocol credential or provider secret is stored or audited.

**Preserved**
- M13-01 through M13-04 channel, identity, persistence and session authorities remain intact; no duplicate provider/runtime/connection/message authority was introduced.
- No QR image generation/scanning, WhatsApp login/protocol, provider adapter, message/history synchronization, incoming/outgoing messaging, webhook, routing, Inbox/Customer 360/Analytics, API or frontend work is included.

**Validated**
- Ruff, strict mypy, 20 focused tests and all 976 backend tests pass in workflow `30933007710`.
- Migration round-trip, generated-client invariance, Bandit, dependency audits and tracked-source security scan pass; OpenAPI remains semantically unchanged at 200 paths.
- Unchanged frontend passes ESLint, TypeScript, 34 Vitest files / 661 tests and production build with no bundle change. M13-05 reaches `Repository Validated`; host/provider/runtime commissioning remains pending.

### 2026-08-04 — QR Session Manager Foundation (M13-04)

**Added**
- Added provider-neutral session lifecycle/state contracts and durable `ChannelSession` records linked to existing organization-owned channel connections.
- Added tenant-scoped registration/discovery/ownership, factual health, heartbeat/expiration, recovery metadata, restart policy, capability references, database leases, fencing tokens, optimistic concurrency and Audit evidence.
- Added disabled-by-default session flags, channel session RBAC permissions and additive migration `0038_qr_session_manager_foundation`.

**Security**
- Session metadata rejects secret-shaped material and stores only optional references to existing encrypted credentials; provider secrets are never returned through APIs, OpenAPI, generated clients, logs or Audit payloads.

**Preserved**
- M13-01 through M13-03 channel, identity and persistence authorities remain intact; no duplicate connection, endpoint, credential, message or history storage was introduced.
- No QR code generation/scanning, WhatsApp login, provider adapter/runtime, message/history synchronization, sending, incoming webhook runtime, routing, Inbox/Customer 360 change or M13-05 work is included.

**Validated**
- Ruff and strict mypy across 279 source files pass; 7 focused session/migration tests and all 970 backend tests pass.
- Migration upgrade/downgrade/upgrade, OpenAPI/client regeneration, Bandit high-severity and dependency audits pass; OpenAPI remains 200 paths.
- Unchanged frontend passes ESLint, TypeScript, 34 Vitest files / 661 tests and production build with no bundle change. M13-04 reaches `Repository Validated`; target-host multi-node/runtime/MySQL/KMS/rollout commissioning remains pending.

### 2026-08-04 — Persistent Channel Connections & Endpoint Records (M13-03)

**Added**
- Added provider-neutral, organization-owned persistent Channel Connection, Channel Endpoint and encrypted Channel Secret records with immutable provider identifiers, lifecycle/health/configuration/metadata facts, Audit references, soft delete and optimistic locking.
- Added tenant-scoped repositories and a disabled-by-default feature-gated persistence service, including logical cascade deletion and credential rotation/version/revocation/expiry/access evidence.
- Added an AES-GCM secret-cipher abstraction and migration `0037_persistent_channel_connections`; plaintext credentials are rejected from metadata and never exposed through APIs, OpenAPI, generated clients, logs or Audit payloads.

**Preserved**
- M13-01 channel foundations, M13-02 identity resolution, existing `ChannelAdapter`, Contact/Inbox/Customer 360/Timeline/Notification/Analytics authorities and the 200-path public API remain unchanged.
- No provider adapter/runtime, QR login/pairing/session, history or message synchronization, live messaging, webhook, routing engine, Inbox/Customer 360 UI or M13-04 work is included.

**Validated**
- Ruff and strict mypy across 275 source files pass; 4 focused persistence tests and all 965 backend tests pass.
- Migration upgrade/downgrade/upgrade, OpenAPI/client regeneration, Bandit high-severity and dependency audits pass; OpenAPI remains 200 paths.
- Unchanged frontend passes ESLint, TypeScript, 34 Vitest files / 661 tests and production build with no bundle change. M13-03 reaches `Repository Validated`; target-host MySQL/KMS/rollout commissioning remains pending.

### 2026-08-04 — Customer Identity Resolution (M13-02)

**Added**
- Added exact tenant-scoped provider and endpoint identities linked to the canonical Contact, with immutable ownership, factual confidence, ambiguous/conflict detection and a restricted manual-review queue.
- Added non-destructive merge recommendations with explicit approve/reject decisions, RBAC, feature flags, Audit and Customer Timeline evidence.
- Added migration `0036_customer_identity_resolution`, seven additive API paths, generated OpenAPI/client authority and focused identity regressions.

**Preserved**
- M13-01 channel foundations, canonical Contact ownership and existing CRM, Inbox, Customer 360, Timeline and Audit authorities remain unchanged; approval never merges Contacts or moves identities.
- No M13-03 session/connection control-plane, provider runtime, QR pairing, messaging, UI route or provider selection work is included.

**Validated**
- Ruff, strict mypy across 271 source files, 22 focused tests and all 961 backend tests pass.
- Frontend production audit, ESLint, TypeScript, Vitest and production build pass; OpenAPI has 200 paths and the generated client is current.
- Migration upgrade/downgrade/upgrade passes. M13-02 reaches `Repository Validated`; host/runtime commissioning remains pending.

### 2026-08-04 — Generic Channel Foundation (M13-01)

**Added**
- Added provider-independent Communication Intent, Communication Policy, Channel Metadata,
  Provider Health and Provider Lifecycle contracts with shared enums and validation.
- Added provider metadata and capability registries that delegate adapter creation to the
  existing `ChannelAdapter` registry rather than creating a parallel provider system.
- Added two disabled-by-default generic connection flags over the existing organization-scoped
  `FeatureFlag` table and typed dependency-injection composition.
- Added seven focused tests for registry parity/conflict handling, policy decisions, factual
  health/lifecycle validation, feature-flag precedence and DI stability.

**Preserved**
- No provider implementation, QR pairing, session/runtime, history, live messaging, database
  migration, API route, OpenAPI/client, dependency, frontend or shared CRM-authority change.
- Contact, Customer 360, Timeline, Inbox, Notification Center, Analytics and the existing
  `ChannelAdapter` remain authoritative and unchanged.

**Validated**
- Ruff and strict mypy pass across 263 source files; 46 focused and 955 full backend tests pass.
- The unchanged frontend passes production audit high threshold, ESLint, TypeScript, 661 tests
  and build with no bundle change.
- M13-01 reaches `Repository Validated`; persistent channel records/Meta backfill remain a
  Required unimplemented contract gap, and M13-02 is not authorized.

### 2026-08-04 — Module 13 implementation contract (M13-00)

**Added**
- Added accepted ADR-0020 and frozen Design Document 33 for the Enterprise Omnichannel Channel
  Manager, preserving the existing capability-based channel seam and shared CRM authorities.
- Added the provider capability matrix, objective QR provider evaluation gate, threat model, security
  architecture, session lifecycle, exact customer identity contract, additive API/database plan,
  rollback, feature flags, staged rollout, disaster recovery, observability, performance objectives,
  testing strategy, acceptance criteria, risk register and external dependencies.
- Added a classified gap analysis with Required, Recommended and Future Enhancement findings.

**Clarified**
- Confirmed that Module 13 extends the existing `ChannelAdapter` rather than introducing a parallel
  adapter hierarchy or duplicate Contact, Inbox, message, media, notification, analytics or audit authority.
- Recorded ADR-0020 as the later owner decision permitting Instagram only as a future separately
  approved adapter possibility despite the older Doc 07 exclusion; no future-provider implementation
  is authorized by M13-00.
- Kept QR provider selection honest: no vendor is claimed until every Required criterion passes.

**Preserved**
- No QR login, session runtime, Channel Manager, backend, frontend, migration, API, generated contract,
  dependency, route, queue or deployment implementation was added.
- Repository remains `1.0.0-rc1`, migration `0035_notification_center`, OpenAPI 193 paths and Module 13
  implementation completion `0%`.

**Validated**
- M13-00 reaches `Repository Validated` through documentation structure, consistency, changed-file,
  gap-classification and governance checks. Host/runtime/provider/production evidence is intentionally
  not claimed, and M13-01 remains unstarted pending its explicit gates and owner instruction.

### 2026-08-04 — Operator-first operational Dashboard (UI-TASTE-03A)

**Added**
- Added a permission-aware operational desk that prioritizes blocked Reactivation customers, KYC
  reviews, SIM/Activation SLA risk, Campaign failures, waiting conversations, blocked Templates,
  agent workload and today KPI changes using existing source authorities.
- Added truthful loading, empty, partial-source error and permission states, governed source actions,
  signed-in task snapshot, responsive table/card transformations and four focused selector tests.

**Changed**
- Replaced the messaging-led Dashboard with decision-first operational intelligence while preserving
  Live Chat/New Campaign primary links and all source workflows.
- Added optional `enabled` controls to existing Reactivation, KYC, Template and Analytics query hooks
  so unauthorized Dashboard sources issue no request.
- Lazy-split the operational workspace behind an accessible skeleton. The main chunk improves from
  747.91 kB to 733.62 kB; the Dashboard workspace is 31.96 kB / 8.61 kB gzip.

**Fixed**
- Fixed strict TypeScript widening of KPI sentiment literals.
- Fixed a regression where primary Dashboard navigation actions had become buttons instead of real
  links; the established accessibility/navigation contract is restored.

**Validated**
- Production dependency audit, ESLint, TypeScript, 34 Vitest files / 661 tests and production build
  pass. Migration `0035`, 193-path OpenAPI, generated client, backend and dependencies are unchanged.
- Authenticated representative-data visual/reference review remains `PENDING – Host Machine
  Validation`; bounded source reads are not claimed as exact enterprise totals.

### 2026-08-04 — Shared enterprise design-system modernization (UI-TASTE-02)

**Added**
- Added original shared `Input`, `Select`, `Textarea`, `Field`, `Toolbar`, `FilterBar`, and cursor
  `Pagination` primitives with semantic focus, disabled, invalid, busy, label, help, error, icon,
  action, summary, and mobile touch-target behavior.
- Added named `control`, `surface`, and `overlay` radius tiers so enterprise density can converge
  without silently changing legacy sidebar or navigation utilities.
- Added three focused shared-primitive tests covering semantic labels, invalid state, pagination
  callbacks/disabled state, and loading-button accessibility.

**Changed**
- Refined shared Button, Card/CardHeader, PageHeader, and PageContainer hierarchy, spacing, elevation,
  responsive action alignment, and restrained interaction treatment.
- Replaced duplicated Contacts search/filter/mobile-sheet/pagination styling, Inbox search/advanced-
  filter/saved-view/bulk-select/pagination styling, and Notification Center filter/action styling
  with governed shared components. Existing URL state, shortcuts, bulk behavior, polling, read
  state, permissions, and source deep links are unchanged.

**Preserved**
- Sidebar, navigation, routes, backend, migrations, OpenAPI, generated contracts, dependencies,
  permissions, real workflows, keyboard/focus handling, reduced motion, responsive navigation, and
  source-domain ownership are unchanged. No heavy animation library, copied reference implementation,
  proprietary asset, fake metric, or parallel component system was introduced.

**Validated**
- ESLint and TypeScript pass; all 33 Vitest files and 657 tests pass; the production build passes
  after transforming 2,599 modules. The main application chunk is 747.91 kB minified / 181.62 kB
  gzip and retains the known >500 kB warning.
- The production dependency audit has no high/critical finding and reports two moderate React Router
  advisories. The combined development-tool inventory reports 11 transitive findings and remains a
  separately governed dependency-modernization task.
- Authenticated representative-data desktop/tablet/mobile and approved-reference visual comparison
  remains `PENDING – Host Machine Validation`; Priority 2 is blocked pending owner approval.

### 2026-08-02 — Customer 360 domain convergence (CORE-07)

**Added**
- Converged the existing Contact profile into one persisted, permission-aware workspace for identity
  and attributes, exact-contact WhatsApp conversations/messages, Reactivation status/labels,
  reminders, assignment, notes, SLA, Documents, Tasks, KYC/SIM/Activation facts, Campaign
  participation, Audit, and Customer Timeline.
- Added accessible Overview, Vi operations, Conversations, Timeline, Tasks, Documents, Campaigns,
  and Audit tabs, source-workflow deep links, loading/empty/error/denied/read-only states, and
  responsive desktop/tablet/mobile composition using the existing design system.
- Added optional exact Contact filters to the existing Inbox conversation query and Reactivation
  pipeline query; regenerated OpenAPI/TypeScript contracts at the unchanged 189-path boundary; added
  ADR-0018, Design Document 31, and focused backend/frontend regressions.

**Reused and preserved**
- Reused Contact, Conversation/Message, Inbox, Reactivation, Task/reminder, Document Center, KYC,
  SIM, Activation, Campaign, Audit, Customer Timeline, RBAC, tenant, and shared UI authorities.
  Customer 360 remains a read composition with no parallel model, repository, service, route family,
  synthetic metric, migration, fake data, or duplicated completed module.
- Reviewed the approved `0001`, `0008`, `0010`, and `0048` paired reference captures for contextual
  hierarchy, tabs, density, and activity patterns. Original code, wording, icons, colors, tokens,
  spacing, and breakpoints are retained; reference files remain ignored and uncommitted.

**Fixed**
- Fixed the workflow-blocking Contact conversation placeholder. Root cause: the existing Inbox list
  query could not request one exact public Contact. The query now resolves that id tenant-scoped and
  reuses the existing message authority; malformed, unknown, and foreign identifiers are covered by
  API regression tests.
- Fixed Contact tag mutation controls being exposed to read-only users. Root cause: the section did
  not apply the existing `contacts:write` permission to its action controls. It now renders an
  explicit read-only state with focused regression coverage.
- Removed attribute-derived Vi implications and the AI context placeholder from Customer 360;
  persisted source facts and honest empty states now define the workspace.
- Fixed the production owner journey asserting the superseded KYC, SIM, and AI placeholder tabs.
  Root cause: the release proof had not advanced with the converged information architecture. It now
  requires Vi operations, Conversations, Tasks, Documents and Audit and asserts the placeholder is
  absent; the rebuilt deployed journey passes.

**Validated**
- Focused backend API tests pass 21/21 and the focused Customer 360 frontend regression passes 5/5.
  Canonical suites pass 945/945 pytest and 651/651 Vitest with Ruff, strict mypy across 253 files,
  OpenAPI drift, TypeScript/ESLint, build, security scans, SBOMs, image contracts and MySQL/Redis/
  Celery health. The corrected production owner journey passes 1/1 in 11.1 seconds; desktop/tablet/
  mobile review found no overflow or console error, and the 30-read canary records p95 10.4 ms.

### 2026-08-02 — Lightweight Reactivation CRM correction (CORE-05)

**Added**
- Replaced the planned heavyweight SIM fulfilment direction with the owner-approved single-case CRM:
  exactly one of nine primary statuses, six multi-select labels, Follow-up/Release date controls,
  assignment, notes, premium chips, due counters, and status/label/assignee/date filters.
- Added Task-backed Follow-up and Name Change reminders with Upcoming, Due Today and Overdue
  projection, shared Complete/Reschedule/Snooze actions, assigned-user due evidence, optimistic
  concurrency, RBAC, tenant isolation, Audit and Customer Timeline.
- Added additive migration `0034_reactivation_crm`, the Task Snooze path, OpenAPI 3.1.0 at 189
  paths, generated TypeScript contracts, ADR-0017, Design Document 30, and focused regression tests.

**Reused and preserved**
- Extended the existing Reactivation model/repository/service/API/workspace, Task lifecycle and work
  queue, Contact/User authorities, Celery, Audit, Customer Timeline, RBAC, and shared UI primitives.
  CORE-02/04 KYC, SIM, Activation, document, SLA and approval foundations remain intact.
- Added no parallel reminder/notification store, fake count/card, local-only workflow, copied
  reference content, standalone SIM/Activation workspace, or duplicate completed module.

**Fixed**
- Fixed stale Follow-up/Release dates being submitted after their labels were removed; root cause
  was unconditional drawer serialization. Dates now serialize only with their governing label and
  focused UI/contract tests protect the rule.
- Fixed shared Complete and Reschedule UI actions omitting `row_version`; root cause was an optional
  client parameter left unused. All reminder mutation actions now send the current version.
- Fixed Not Required being closable without a server-enforced disposition reason; the service now
  fails closed, matching the accessible confirmation UI.
- Fixed timezone-aware workflow dates reaching persistence without normalization; the request
  boundary now converts them to naive UTC before transactional Task composition.
- Fixed owner-only case updates leaving open reminders assigned to the previous staff member; the
  root cause was reminder synchronization being conditional on a labels payload. Owner/date/label
  changes now all reconcile through TaskService, with a focused assignment regression test.
- Fixed `0034` downgrade failing when real post-upgrade stage events used the corrected status
  vocabulary; the rollback now translates both current cases and event rows before restoring legacy
  constraints, and the migration roundtrip test inserts representative new-vocabulary evidence.

**Validated**
- Focused backend Reactivation/API/KYC regression tests pass 11/11; focused Reactivation/Tasks/KYC
  frontend tests pass 25/25. The canonical 22-step deployed profile passes 943/943 pytest and
  646/646 Vitest, Ruff, strict mypy across 253 files, OpenAPI drift, TypeScript/ESLint, production
  build, Python compile, Bandit, dependency/source/image scans, SBOMs, Compose/image contracts,
  MySQL migration `0034`, healthy Redis/Celery, and Playwright 1/1 in 11.338 seconds.
- Four paired approved reference workflows were reviewed for filter density, label chips, staff
  selection, form/modal hierarchy, and responsive collapse. Original components, tokens, icons,
  wording and breakpoints are retained; `.reference/aisensy/` remains ignored and uncommitted. The
  deployed 30-read canary records p50 10.168 ms and p95 17.761 ms (<300 ms).

### 2026-08-02 — Governed KYC operations (CORE-04)

**Added**
- Added the real tenant-scoped KYC operations projection and responsive queue/detail workspace over
  the existing CORE-02 KYC authority, with holder, Delhi-presence and active-number verification,
  factual progress/SLA, and truthful loading, empty, error, permission and read-only states.
- Added verified Aadhaar/PAN checklist references to existing protected Document Center records;
  the KYC schema, API, UI, audit evidence and migration store no identity numbers.
- Added idempotent Task-backed appointment creation and reused existing Task commands for
  reschedule, completion and cancellation with immutable Task/Customer Timeline evidence.
- Added structured rejection reasons, enforced requester/reviewer/manager separation, immutable
  decisions, optimistic concurrency, manager-approved Reactivation handoff, Customer 360
  projection, ADR-0016, Design Document 29, and focused backend/frontend tests.
- Added migration `0033_kyc_operations`; regenerated OpenAPI 3.1.0 at 188 paths and generated
  TypeScript contracts.

**Reused and preserved**
- Extended existing KYC, Reactivation, Contact, User, Document Center, Task, Customer 360, Audit,
  Customer Timeline, RBAC, SLA, shared form/table/drawer/status/state, and generated-client
  implementations in place. No completed module or parallel authority was rebuilt.
- Added no mock operational data, plaintext Aadhaar/PAN number, independent document store,
  appointment table, approval engine, timeline, SIM fulfilment, copied reference material, or
  tracked `.reference/aisensy/` content.

**Validated**
- The canonical 22-step deployed profile passed: 940 pytest tests, 646 Vitest tests, Ruff, strict
  mypy across 252 files, OpenAPI drift, TypeScript/ESLint, production build, Python compile,
  Bandit, dependency/source/image scans, SBOMs, Compose/image contracts, MySQL migration `0033`,
  healthy Redis/Celery services, and Playwright 1/1 in 8.635 seconds.
- Four paired approved full/viewport references were reviewed for queue density, filters,
  form/action hierarchy and responsive drawer behavior. Component tests pass accessibility and
  responsive transformations; authenticated representative-data live review remains target-host
  validation. The deployed 30-read performance canary recorded p95 12.551 ms (<300 ms).

### 2026-08-02 — Governed Reactivation pipeline (CORE-03)

**Added**
- Added a real tenant-scoped pipeline projection with factual fifteen-stage counts, joined contact
  and owner identity, eligibility/rejection evidence, task/document aggregates, reservation and
  family-plan facts, conversion indicators, SLA status, and server-published permitted moves.
- Added two permission-scoped API paths for the pipeline projection and immutable internal case
  notes; regenerated OpenAPI 3.1.0 at 184 paths and the TypeScript contract.
- Added pointer drag/drop, keyboard stage movement, responsive board/list views, assignment and
  number editing, immutable history/notes, Tasks/Documents reuse, Customer 360 links, truthful
  loading/empty/error/permission states, ADR-0015, Design Document 28, and focused tests.

**Reused and preserved**
- Extended the existing Reactivation route, CORE-02 Vi repository/service/API authority, Contact and
  User records, governed Documents, Tasks/reminders, Customer 360, RBAC, Audit, Customer Timeline,
  SLA, shared Modal, and premium responsive shell; no completed module or parallel authority was
  rebuilt.
- Added no migration, mock lead card, fake count, local-only workflow state, KYC operations UI,
  copied reference code/asset/branding, or tracked `.reference/aisensy/` content.

**Validated**
- Canonical release and isolated deployed profiles passed all 22 applicable steps: 938 pytest tests,
  641 Vitest tests, Ruff, strict mypy across 252 files, OpenAPI drift, TypeScript/ESLint, production
  build, security/dependency/source/image scans, SBOMs, Compose/image contracts, MySQL/Redis/Celery,
  and Playwright 1/1.
- Authenticated reference review passed at 1280×720, 768×1024, and 390×844 without page-level
  horizontal overflow; the deployed 30-read performance canary recorded p95 8.547 ms (<300 ms).

### 2026-08-02 — Vi domain foundation (CORE-02)

**Added**
- Added the ten approved tenant-scoped Reactivation, eligibility, KYC, SIM, Activation, and SLA
  records with immutable decision/event evidence, strong constraints, transition prerequisites,
  optimistic concurrency, UUID idempotency, and explicit approval boundaries.
- Added repository/service/schema layers and 29 permission-scoped lifecycle API paths; regenerated
  OpenAPI 3.1.0 at 182 paths and the TypeScript contract.
- Added fifteen additive RBAC permissions, seven durable business-event types, audit and Customer
  Timeline projections, ADR-0014, Design Document 27, and focused domain/API/migration tests.
- Added migration `0032_vi_domain_foundation` from the unchanged `0031` head.

**Preserved**
- Reused contacts, configurable lead pipelines, governed documents, tasks, audit, Customer
  Timeline, durable business events, automation receipts, and runtime RBAC as existing authorities.
- Added no Reactivation Kanban, KYC workspace, SIM fulfilment UI, Activation Queue, fake operational
  data, placeholder workflow, duplicate module, parallel event bus, or migration downgrade.

**Validated**
- Canonical pre-merge and release profiles passed: 936 pytest tests, 636 Vitest tests, Ruff, strict
  mypy across 252 source files, OpenAPI drift, ESLint, frontend/browser TypeScript, production build,
  Bandit, dependency audits, Trivy source/image scans, SBOMs, Compose and image contracts.
- SQLite migration upgrade/downgrade/re-upgrade passed. The isolated ten-service MySQL/Redis/Celery
  deployment applied `0032`, passed Playwright, and recorded p95 16.5 ms across 30 reads.

### 2026-08-02 — Governed premium product shell (CORE-01)

**Added**
- Accepted ADR-0013 and Design Document 26 for the canonical permission-aware navigation catalogue,
  reference comparison, originality boundary, responsive behavior, and accessibility evidence.
- Added a permanent runtime/test guard against excluded Ads, Payments, Billing, marketplace,
  SaaS/multi-project, public-signup/reseller, and commerce navigation concepts.
- Added honest `Foundation` and `Future` maturity labels and one shared permission-scoped quick-create
  catalogue for the top bar and command palette.

**Changed**
- Finalized the original Vi Reactivation dark-green desktop rail, grouped More surface, mobile task
  bar/drawer, active states, shared command palette, and dismissible create/account menus.
- Added dialog focus trapping/restoration, Escape behavior, live search-result announcements,
  explicit ARIA state, 44px mobile targets, and mobile More state for overflow destinations.
- Removed two incidental Billing references from user-facing administrative copy without changing
  API-key or role behavior.

**Preserved**
- The existing six-item primary order, all completed routes/modules, backend architecture, product
  scope, module percentages, permissions, OpenAPI 3.1.0 at 153 paths, and migration head `0031`.
- `.reference/aisensy/` remains ignored and untracked; no proprietary code, asset, branding, exact
  icon, exact color, wording, typography, screenshot, or pixel value was copied or shipped.

**Validated**
- Passed canonical static checks, Ruff, strict mypy, OpenAPI drift, frontend/Playwright TypeScript,
  ESLint, Python compile, migration head, generated-contract drift, 932 pytest tests, 636 Vitest
  tests, production build, Bandit, and dependency audits.
- Passed 30 focused navigation/foundation tests and authenticated 1280×720 browser comparison for
  the compact rail, More, command palette, factual error states, and horizontal-overflow boundary.
- Docker-backed Trivy/release/deployed reruns remain `PENDING – Host Machine Validation` because the
  Docker Desktop daemon was unavailable; prior successful deployed evidence remains preserved.

### 2026-08-02 — Premium AiSensy-parity product goal lock (GOV-02)

**Added**
- Accepted ADR-0012, permanently setting an original private enterprise-grade WhatsApp Business
  Platform for the Vi Reactivation Team as the product target, with functionality and premium
  presentation as equal acceptance requirements.
- Added Design Document 25 with experience principles, the fourteen-step approved-reference review,
  shared enterprise component catalogue, truthful state rules, responsive/accessibility acceptance,
  and the twenty-point premium screen Definition of Done.
- Recorded the permanent priority order, no-placeholder rule, original-implementation boundary, and
  bounded continuous-quality policy across the scope and governance ledgers.

**Changed**
- Synchronized the scope, rules, README, project state, implementation tracker, gap analysis, module
  status, roadmap, validation ledger, and changelog for the owner-approved GOV-02 documentation
  milestone.
- Clarified that GitHub remains the only implementation source of truth while the owner-approved
  AiSensy archive is a Git-ignored, local-only workflow and visual-quality benchmark that must never
  be staged, committed, bundled, imported, or copied.

**Preserved**
- Product feature scope, roadmap sequence and estimates, module completion percentages, architecture,
  requirements, migrations, OpenAPI, permissions, tests, and runtime behavior are unchanged.
- Ads Manager, Meta Ads, WhatsApp Payments, payment processing, billing/subscriptions/trials/upgrades,
  public signup, reseller/multi-project, marketplace, catalog, cart, checkout, orders, refunds, and
  commerce remain excluded. AI and Automation references remain milestone-gated.

**Validated**
- Passed GOV-02 Markdown structure/link, required-file/content, governance-consistency, changed-file,
  reference-ignore, exclusion, migration-invariance, and OpenAPI-invariance checks.
- Application tests were not rerun for this documentation-only milestone; their last successful
  evidence remains preserved in `VALIDATION_RESULTS.md` and `IMPLEMENTATION_TRACKER.md`.

### 2026-08-02 — Governance repository state synchronization

**Changed**
- Recorded owner approval of the completed GOV-01 governance baseline and retained CORE-01 as the
  next milestone requiring a separate owner instruction.
- Recorded migration head `0031`, OpenAPI 3.1.0 with 153 paths, 932 backend tests, 628 frontend
  tests, and the successfully completed repository validation pipeline.
- Removed local ZIP/archive exceptions from the active governance rules and roadmap. GitHub at the
  latest approved HEAD is the only implementation source of truth.

**Preserved**
- No backend, frontend, API, migration, test, architecture, or product behavior changed.
- `CURRENT_PROJECT_GAP_ANALYSIS.md` and `VI_REACTIVATION_FINAL_PRODUCT_SCOPE.md` remain unchanged.

### 2026-08-02 — Permanent repository governance baseline (GOV-01)

**Added**
- Added root `PROJECT_STATE.md`, `VALIDATION_RESULTS.md`, `MODULE_STATUS.md`,
  `REPOSITORY_RULES.md`, and the canonical final-scope `ROADMAP.md` without overwriting the existing
  historical roadmap.
- Added a synchronized milestone closeout model covering Git state, migration/OpenAPI/test evidence,
  module completion, validation truth, one-milestone-per-commit discipline, and owner approval.
- Registered the explicitly supplied 73-state AiSensy capture set as permitted UI/workflow reference
  material while keeping ads, payments, billing, marketplaces, SaaS, and other scope exclusions out
  of the product roadmap.

**Preserved**
- `VI_REACTIVATION_FINAL_PRODUCT_SCOPE.md` and `CURRENT_PROJECT_GAP_ANALYSIS.md` remain unchanged and
  retain product-intent and remaining-work authority.
- No backend, frontend, migration, API, queue, provider, permission, or runtime behavior changed.

**Validated**
- Verified branch `feature/module6-queue-engine` at `a8479e7`, migration head `0031`, OpenAPI 3.1.0
  with 153 paths and no export drift, 932 collected backend tests, and 628 enumerated frontend tests.
- Passed the repository static quality profile: Ruff, strict mypy across 247 files, OpenAPI drift,
  ESLint, frontend TypeScript, and Playwright TypeScript; the governance updater also compiles and
  passes focused Ruff validation.
- The last completed engineering milestone remains PAR-AUTO-03 with its recorded full release and
  deployed validation evidence. GOV-01 is documentation/governance only and was subsequently
  approved on 2026-08-02.

### 2026-07-30 — Durable automation trigger receipts (MD5 Phase 2C)

**Added**
- Added the governed `contact.created` event type, append-only business-event ledger, and migration
  `0031` with MySQL time partitioning and a reversible SQLite test path.
- Added atomic event publication from the existing API/import and system conversation contact paths.
  Only enabled, clean published flows with the matching immutable trigger receive a tenant-scoped,
  replay-safe receipt.
- Added the permission-scoped receipt history route, generated TypeScript contract, and a compact
  builder panel that labels real matches as evidence and explicitly states no action executed.

**Preserved**
- No receipt starts a run or applies a task, tag, assignment, notification, webhook, campaign,
  provider, approval, handoff, send, AI, Forms or commerce effect. Existing contact validation,
  permissions, audit, import queueing and transaction ownership remain unchanged.

**Validated**
- Passed 932 backend tests, Ruff, strict mypy across 247 files, OpenAPI drift validation, 628
  frontend tests, TypeScript, ESLint and production builds. Rebuilt production images expose 153
  paths and register the unchanged 24 Celery tasks. The complete deployed profile passed SAST,
  dependency/source/image scans, SBOM generation, MySQL migration, API/worker/queue health, real
  queued-import trigger receipt evidence, readiness/observability checks and a 19.002 ms p95 canary.

### 2026-07-30 — Deterministic automation test runtime (MD5 Phase 2B)

**Added**
- Added tenant-scoped immutable-version test runs, step-attempt evidence, durable UUID idempotency,
  deterministic DAG execution, checkpoint/resume, and migration `0030`.
- Added the `automation.run` Jobs-pool route and tracked Celery task using the existing job,
  retry and DLQ authorities; no new queue framework was introduced.
- Added three permission-scoped OpenAPI routes, generated frontend contracts, safe test submission,
  polling, recent run history and ordered attempt evidence in the existing automation builder.

**Fixed**
- Replaced the test-run UI's secure-origin-only `crypto.randomUUID()` assumption with UUID v4
  generation backed by `crypto.getRandomValues()`. The isolated HTTP production gate now submits
  and completes the real queued test run; a focused regression test covers the portable key path.

**Preserved**
- Test mode simulates every action. No live event or schedule, delay/wait, CRM/task/tag/assignment
  mutation, provider/webhook/campaign call, approval/handoff, send, AI, Forms or commerce behavior
  was introduced. Existing API, schema, permission and business behavior is otherwise unchanged.

**Validated**
- Passed 928 backend tests, Ruff, strict mypy across 242 files, OpenAPI drift validation, 627
  frontend tests, TypeScript, ESLint and production builds. The rebuilt backend exposes 152 paths
  and registers 24 tasks. The complete release and deployed profiles passed image contracts,
  SAST/dependency/source/image scans, SBOM generation, migration, API/worker/queue health, a real
  browser safe test run, readiness degradation, observability checks and an 18.423 ms p95 canary.

### 2026-07-30 — Versioned automation definitions (MD5 Phase 2A)

**Added**
- Added tenant-scoped automation drafts, bounded typed graphs, fail-closed semantic validation,
  immutable content-addressed published versions, restore/enable/disable controls, optimistic
  concurrency, audit events and migration `0029`.
- Added least-privilege `automations:read`, `automations:write` and `automations:publish` permissions,
  eight OpenAPI paths, regenerated TypeScript contracts, and a searchable versioned authoring
  workspace. Execution remains visibly unavailable until the governed runtime milestone.

**Fixed**
- Prevented the compact sidebar's advanced-navigation panel from opening over active advanced
  routes and intercepting workspace clicks.
- Kept the successful draft-save confirmation visible when refreshed server state synchronizes
  back into the builder.

**Preserved**
- No automation task, trigger, schedule, provider call, outbound webhook, CRM mutation, campaign
  dispatch or customer message was introduced. Existing API behavior, send authority, queue routing,
  Meta adapter, tenant isolation and business rules remain unchanged.

**Validated**
- Passed 921 backend tests, Ruff, strict mypy across 237 files, OpenAPI drift validation, 625
  frontend tests, TypeScript, ESLint and production builds. The production backend retains 23
  registered tasks and now exposes 149 paths. Rebuilt and contract-checked production images; the
  isolated ten-service deployment passed migration, API/worker/queue health, real browser
  create/save/publish, readiness degradation, log redaction and a 25.9 ms p95 read canary.

### 2026-07-30 — Campaign follow-up and chat-link acquisition

**Added**
- Added a clear `Create follow-up` action for completed campaigns. It composes the source definition
  into a fresh, distinctly named draft and preserves the existing audience, editing, scheduling,
  approval and dispatch authorities.
- Added a phone-number-level WhatsApp chat-link utility with an optional prefilled message, local QR
  generation, copy/test actions and a downloadable PNG. The QR encoder is loaded only when the
  dialog opens; no phone number, message or link is sent to a QR service.

**Preserved**
- No backend API, schema, permission, tenant-isolation, campaign dispatch, queue or Meta adapter
  behavior changed. Links are not shortened or tracked, and carousel support remains hidden because
  its end-to-end template/send contract does not exist.

**Validated**
- Passed all 621 frontend tests, ESLint, TypeScript and the production build. The production-only
  dependency audit remains at the two known moderate React Router advisories with no high/critical
  finding. Rebuilt the production frontend image, passed its nginx contract, recreated the container
  healthy, and returned HTTP 200 for the number-detail route with the current bundle. MD5 Phase 1
  repository implementation is release ready; task-time baselines remain target UAT evidence.

### 2026-07-30 — Audience and retargeting presets

**Added**
- Added four marketer-friendly audience templates—recently engaged, needs reactivation, new
  contacts and WhatsApp active—using only the existing segment rule grammar.
- Added one-click quick audiences in the campaign audience step when matching saved segments
  actually exist. Presets still open the normal segment editor for review and use the existing
  create endpoint, live campaign resolution, consent filtering and approval journey.

**Preserved**
- No API, schema, permission, tenant-isolation, campaign dispatch or queue behavior changed.
- Campaign-specific read/click/failed retargeting is not inferred from the recipient UI's partial
  page; it remains unavailable until a complete audience contract is separately approved.

**Validated**
- Passed all 617 frontend tests, ESLint, TypeScript and the production build. Rebuilt the production
  frontend image, passed its nginx image contract, recreated the frontend container healthy, and
  returned HTTP 200 for `/segments` with the current bundle.

### 2026-07-30 — Payment and commerce scope removal

**Changed**
- Recorded the owner's explicit decision that payments, transaction processing, product catalogs,
  carts, checkout, orders, refunds and commerce journeys are not product roadmap deliverables.
- Replaced the five-phase plan's former payment/commerce phase with advanced analytics, reporting
  and team operations.
- Removed the non-functional Payments placeholder from Customer 360, leaving 12 contract-relevant
  sections. No backend API, schema, permission or business behavior changed.

**Validated**
- Passed the focused Customer 360 regression, all 612 frontend tests, ESLint, TypeScript and the
  production build. Rebuilt the frontend image, passed its nginx image contract, recreated the
  frontend container healthy, and returned HTTP 200 for the Customer 360 route with the new bundle.

### 2026-07-30 — Five-phase parity execution plan

**Added**
- Added Design Document 21, a five-phase path from the verified repository baseline to an
  AiSensy-comparable but original product: simplicity/retargeting, automation/forms, ads,
  analytics/team operations, and governed AI/integrations.
- Defined the required data, API, permission, audit, failure-recovery and quality gates for every
  phase so genuine gaps cannot be presented as implemented UI.

### 2026-07-30 — Live Chat simplicity

**Changed**
- Replaced the crowded inbox folder strip with three task-first views: Requests (open and
  unassigned), Active (all open), and My chats (assigned to the current user). These use the
  existing status and assignment contracts and do not simulate chatbot or handoff state.
- Moved status, assignee, label and saved-view management behind one advanced Filters control while
  keeping search and saved inboxes immediately available.
- Simplified conversation rows around customer identity, message preview, unread urgency and aged
  waits; preserved status, service-window, labels, pinning and bulk selection.
- Reduced permanent thread chrome to status and assignment. Customer context, editable labels,
  notes, governed AI assistance, pinning and Customer 360 now open through the Details panel.
  APIs, permissions, schemas, tenant rules and message behavior are unchanged.

**Validated**
- Passed 612 frontend tests, ESLint, TypeScript and the production build. Rebuilt the production
  frontend image, passed its nginx image contract, recreated the frontend container healthy, and
  returned HTTP 200 for `/inbox` with the new production bundle.

### 2026-07-30 — Guided campaign journey

**Changed**
- Replaced the horizontally scrolling campaign step tabs with a compact progress rail that fits the
  full Audience → Template → Preview → Schedule → Approval → Confirmation journey and preserves
  completed-step navigation.
- Added consistent step context, larger accessible controls, audience and delivery choice cards,
  customer-facing message previews, a compact final review, and clearer sticky actions across create,
  duplicate, and edit flows.
- Kept the existing AI planning foundation available as an optional collapsed section so the default
  campaign journey stays focused. Campaign APIs, permissions, schedules, approval checkpoint,
  validation, dispatch authority, and business behavior are unchanged.

**Validated**
- Passed 610 frontend tests, ESLint, TypeScript, the production build, the frontend image contract,
  container health, and a direct production-route smoke check for `/campaigns/new`.

### 2026-07-30 — Simplified customer workspace

**Added**
- Added the active AiSensy-inspired parity roadmap, separating verified product coverage from
  genuine automation, forms, ads, AI-agent and integration contract work while explicitly
  excluding payments and commerce.

**Changed**
- Made the six-destination desktop task rail compact by default, with one permission-aware `More`
  flyout for every entitled advanced route. Users can still expand the rail and the preference is
  retained without changing routes or permissions.
- Replaced the generic purple accent with an original teal engagement palette. No competitor
  branding, assets, code, or unsupported capability claims were introduced.
- Reduced the default sidebar from the full module catalog to six task-first destinations; all
  entitled advanced, operational, and administrative areas remain available through one expanded
  `More` section and workspace search.
- Renamed the existing inbox destination to `Live Chat` in navigation, removed duplicate favorite
  links, moved theme and shortcut help into the account menu, and aligned desktop/mobile order.
- Replaced the chart-heavy executive home with a compact task-first dashboard: four operational
  indicators, two primary actions, the existing personal work queue, and setup steps. Redundant
  quick-access and recent-route cards were removed; empty task buckets use the compact state so
  mobile users do not scroll through oversized blanks.
- Added a setup-first WhatsApp overview derived only from the existing WABA and phone-number
  contracts: connection readiness, quality, send capacity, default identity, and three governed
  setup steps. Unsupported subscription, credit, quota, mobile-app, and advertising claims are
  deliberately absent.

**Fixed**
- Replaced the dashboard's dead `/settings/whatsapp` onboarding destination with the existing
  permission-governed account and number routes. APIs, permissions, schemas, and channel behavior
  are unchanged.

**Validated**
- Passed 608 frontend tests, ESLint, TypeScript, and the production build. Rebuilt the production
  frontend image and passed its nginx runtime contract. The isolated ten-service gate verified an
  authenticated browser journey, API/workers/queues/dependency health, cleanup, and a 22.7 ms p95
  across 30 reads (<300 ms). The live shell audit at 1440 × 900 and 390 × 844 found no horizontal
  overflow; the compact rail, expandable preference, mobile navigation, and advanced `More` panel
  remain usable against the production container.

### 2026-07-30 — Phase 4A governed customer documents

**Added**
- Added tenant-scoped customer document records with immutable media-backed versions, human
  verification/rejection, explicit expiry, archive, signed previews, audit history, customer
  timeline projection, optimistic concurrency, and migration `0028`.
- Added least-privilege `documents:read`, `documents:write`, and `documents:verify` permissions and
  one shared premium document workspace for Customer 360 and Reactivation.
- Added generated 141-path OpenAPI/TypeScript contracts, 10 backend API regressions, and 5 frontend
  workflow regressions.

**Fixed**
- Updated the production backend image contract from the stale 133-path assertion to the verified
  141-path contract. The failure was limited to release evidence; application APIs and behavior
  were already correct and remain unchanged. Regression coverage now pins the image assertion.

**Validated**
- Passed 912 backend and 600 frontend tests, Ruff, strict mypy, ESLint, TypeScript, OpenAPI drift,
  dependency/source/image security gates, production builds, image contracts/SBOMs, and the
  isolated API/worker/queue/browser smoke gate (30-read p95 19.4 ms, budget <300 ms).

### 2026-07-25 — Phase 3 reactivation platform and automation foundations

**Added**
- Added the complete Reactivation workspace navigation: eligible numbers, bulk eligibility,
  interested customers, customer pipeline, KYC, Document Center, SIM orders, Activation Queue,
  completed cases, and reports.
- Added an honest reactivation pipeline blueprint over the existing pipeline/stage authority,
  a real media-backed Document Center, real analytics-backed reports, and the complete 13-tab
  Customer 360 information architecture.
- Added a separate Scan Studio adapter/queue boundary and an accessible visual automation
  blueprint builder with trigger, condition, internal-action, delay, tag, assignment, wait,
  webhook, campaign, notification, and mandatory human-approval nodes.
- Added focused Phase 3 boundary tests and extended the isolated production browser journey
  through Reactivation, Automation, Scan Studio, and a 390 × 844 responsive check.

**Changed**
- Reactivation, Automation, and Scan Studio are route-split production chunks; the main bundle
  decreased from the Phase 2 baseline despite the new UI surfaces.
- Backend APIs, OpenAPI, database schema, permissions, tenant isolation, Celery/task behavior,
  provider behavior, and business rules remain unchanged. Missing document/KYC/SIM/scan/
  automation-runtime contracts are shown as disabled, explicit boundaries rather than simulated data.

### 2026-07-25 — Phase 2 customer engagement platform

**Added**
- Added server-synchronized custom inboxes and pins, quick folders, teammate mention insertion,
  customer/notes/AI context, expanded bulk actions, and explicit contract-gated merge/timed-snooze states.
- Added a dedicated Broadcast Center over the existing campaign engine, template favorites, segment
  recents, factual engagement funnel, analytics dashboard navigation/export center, and Phase 2 AI seams.
- Added the Phase 2 realization record, updated research feature matrix, and focused architecture-
  boundary regression coverage.

**Changed**
- Extended the campaign journey through Confirmation and the post-launch Analytics destination, and
  upgraded Customer 360, Template Center, Segments, and Analytics entry points.
- Extended the isolated production browser journey through Broadcast Center, Analytics, the factual
  engagement funnel, and a 390 × 844 no-horizontal-overflow check.
- Backend APIs, OpenAPI, database schema, permissions, tenant isolation, queue behavior, provider
  behavior, and business rules remain unchanged.

### 2026-07-25 — Phase 1 enterprise product transformation

**Added**
- Added a business-first premium shell with responsive navigation, command palette, cross-module
  search, favorites, recents, quick-create actions, keyboard shortcuts, and live attention signals.
- Added customer-360 context, inbox saved views/pins/bulk actions and unread-wait SLA signals, an
  approval-ready campaign journey, Operations control center, permission catalog, and honest
  Automation/Reactivation foundations.
- Added Phase 1 architecture-boundary regression coverage and the verified transformation record in
  `docs/design/16-PHASE-1-ENTERPRISE-PRODUCT-TRANSFORMATION.md`.

**Changed**
- Reorganized navigation around business workflows and upgraded dashboard, sign-in, contacts,
  customer profile, inbox, campaigns, Operations, Administration, Tasks, and Analytics presentation.
- Backend APIs, OpenAPI, database schema, permissions, tenant isolation, queue behavior, Celery task
  registration, provider behavior, and business rules are unchanged.

### 2026-07-25 — Module 11 defensive observability contracts

**Added**
- Added canonical structured `http_request` events with request-id, method, path, status, and
  duration fields. Safe bounded client correlation ids are preserved across nginx and the API;
  unsafe values are replaced.
- Added formatter-boundary redaction for sensitive fields and recognizable credentials, email
  addresses, and international phone numbers in both JSON and text logs. ADR-0007 records the
  repository-versus-environment observability boundary.
- Extended the isolated deployed gate to prove edge and API runtime logs share correlation ids,
  contain none of its synthetic secret/PII values, and report Redis down with a 503 from `/ready`
  after that dependency is stopped.

**Changed**
- Disabled the duplicate uncorrelated Uvicorn access record; application middleware is now the
  canonical API access logger. The release contract also syntax-checks the actual mounted edge
  configuration with the digest-pinned production nginx image.
- API routes, response contracts, permissions, tenant scope, business behavior, and schema are
  unchanged.

### 2026-07-25 — Module 11 deployed-stack E2E and performance canary

**Added**
- Added the cumulative `deployed` quality profile. It starts the unchanged ten-service production
  topology under a unique Compose project with synthetic secrets and disposable volumes, bootstraps
  an Owner through the existing CLI, captures evidence, and guarantees project-scoped cleanup.
- Added a digest-pinned Playwright 1.61.1 Chromium runner and one focused real-UI journey: login →
  Contacts → CSV upload/mapping → queued import → persisted contact search/profile. This exercises
  nginx, the SPA, API, MySQL, Redis broker, and jobs worker without a provider or customer send.
- Added a 30-sample authenticated standard-read canary using nearest-rank p95 and the frozen <300 ms
  target; the first isolated run passed at 7.9 ms. ADR-0006 records the boundary from full load tests.

**Changed**
- Pinned the production MySQL 8.0 image by immutable manifest digest. The release contract now
  rejects unpinned third-party service images as well as unpinned application Dockerfile stages.
- Corrected the deployment smoke runbook to use the existing Contacts import UI instead of referring
  to a nonexistent direct-create control; APIs, permissions, routing, and product behavior are unchanged.

### 2026-07-25 — Module 11 security and release-gate automation

**Added**
- Added cumulative, provider-neutral `static`, `pre-merge`, and `release` quality profiles covering
  Ruff, strict mypy, OpenAPI drift, frontend lint/types, both full test suites, production build,
  Bandit SAST, dependency audits, tracked-source vulnerability/secret/IaC scanning, Compose/image
  contracts, production image scans, smoke checks, and CycloneDX SBOM evidence.
- Added deterministic tests for fail-fast orchestration, tracked-only scanner snapshots, Compose
  invariants, synthetic secret handling, and non-root/health image metadata. ADR-0005 records the
  gate boundaries and scanner pin.

**Security**
- The first blocking audit found `asyncmy` 0.2.11 affected by critical unpatched SQL injection
  (`GHSA-qhqw-rrw9-25rm`). Replaced only the SQLAlchemy driver boundary with pinned `aiomysql`
  0.3.2 / PyMySQL 1.2.0; application layering, SQLAlchemy repositories, schema, routes, permissions,
  queue behavior, and the 133-path contract are unchanged.
- Production application image tags now fail closed when `IMAGE_TAG` is absent, and the deployment
  template demonstrates the immutable release tag `1.0.0-rc1` instead of `latest`.
- Backend and frontend build/runtime bases, plus the production Redis and edge-nginx images, are
  pinned by immutable manifest digest. The application runtimes use current Alpine layers; both
  rebuilt application images pass the blocking HIGH/CRITICAL scan and emit CycloneDX SBOMs.
- The tracked source snapshot is clean at HIGH/CRITICAL across vulnerability, secret, and IaC
  scanning; backend SAST and production dependency audit are clean. Moderate React Router
  advisories remain visible and require an explicit later v7 migration.

### 2026-07-25 — Module 11 strict typing completion

**Added**
- Added precise SQLAlchemy result/expression types, analytics fact-model unions, callback/iterator
  contracts, JSON container types, and focused invariant tests across repository and service seams.
- Missing linked templates, WABAs, or campaign sending numbers now take explicit existing domain
  outcomes instead of surfacing as attribute errors; malformed internal priority cursors are rejected.

**Changed**
- Eliminated the remaining 120 strict-mypy findings across 45 files. Raw `mypy app` now passes for
  all 227 backend source files under the unchanged strict configuration and pinned mypy 2.3.0.
- Retired the temporary baseline, wrapper, and wrapper tests exactly as ADR-0004 required once the
  direct strict gate became clean. ADR-0004 is retained as a superseded transition record.
- Runtime APIs, routes, permissions, tenant scoping, SQL queries, queue behavior, database schema,
  migrations, and the 133-path OpenAPI contract remain unchanged.

### 2026-07-25 — Module 11 strict-mypy ratchet

**Added**
- Added a deterministic strict-mypy ratchet (`backend/scripts/check_mypy.py`) with a versioned
  baseline and focused tests. New or increased path/error-code allowances fail; reductions mark the
  baseline stale until it is explicitly lowered, and same-version writes cannot raise allowances.
- Added ADR-0004 to record the transitional baseline policy, exact checker-version requirement,
  and removal condition once raw strict mypy is clean.

**Changed**
- Pinned the development checker to mypy 2.3.0 while leaving the repository's strict mypy settings
  unchanged. The backend README now documents both the enforced ratchet and the raw-debt audit.
- Reduced strict findings from 251 across 67 files to 120 across 45 files by typing the existing
  Celery/async task boundary and SQLAlchemy model metadata/JSON containers. Runtime behavior,
  queues, retries, database schema, API routes, permissions, and contracts are unchanged.
- Remaining repository/service findings are retained as explicit Module 11 debt behind the ratchet,
  not suppressed or globally disabled. Count granularity avoids line churn; review remains the
  backstop for a same-code replacement within one file.

### 2026-07-25 — Excel import inspection (FR-CON-04)

**Added**
- Added the permission-gated `POST /api/v1/contacts/import/inspect` contract for workbook headers,
  one sample row, worksheet name, estimated data-row count, and non-mutating header validation.
- The inspection path reuses the importer's existing openpyxl parser and cell rendering, runs its
  synchronous workbook work outside the async request loop, and applies a 25 MB inspection ceiling.
- The contact import wizard now accepts `.xlsx`, uploads it for inspection before mapping, and keeps
  the existing browser parser for CSV. No SheetJS or second workbook parser was introduced.

**Changed**
- ADR-0002 moved from proposed to accepted. Docs 4 §14.1 and 5 B3.3 record the additive inspection
  API; the existing async import endpoint and its request contract are unchanged.
- Recovered the canonical project state from Git and executable gates: synchronized the README,
  implementation tracker, roadmap statuses, and deployment guide with the post-RC1 repository.
- Excluded generated `.pytest-run*` directories from Git and the backend Docker build context; an
  unreadable local pytest directory can no longer block production image packaging.

### 2026-07-23 — Docker deployment validation (first execution of the containerised stack)

The production stack was built and run for the first time. Four defects were reproduced in the
running deployment and fixed; none were visible to static review or to the test suite, because
each only manifests in a worker process or at the edge proxy.

**Fixed**
- **All async background work failed after the first task in each worker process.** Every task
  runs under its own `asyncio.run(...)`, which creates and then closes an event loop, while the
  SQLAlchemy engine and Redis client were cached in module globals. The second task in a process
  inherited a connection pool bound to a closed loop and raised
  `got Future attached to a different loop`. `scheduler_tick` was failing every minute; campaign
  dispatch, webhooks, imports, exports, media and analytics rollups were all dead. The engine and
  the Redis client are now rebuilt when the running loop changes
  (`app/db/session.py`, `app/core/redis.py`).
- **Storage backend unavailable in workers.** `app.storage.local` registers itself on import, and
  the only import lived in `app.main` — which a worker never loads. Every worker-side write failed
  with `storage backend 'local' is not available; registered: ()`. Registration moved into
  `app/storage/__init__.py` so it holds for every process.
- **nginx served 502 after any container recreation.** A statically named `upstream` server is
  resolved once at config load and cached for the process lifetime, so `docker compose up -d` —
  the documented upgrade step — left the edge proxying to the previous container's address.
  Reproduced (nginx held `172.19.0.7` while the API had moved to `172.19.0.6`) and fixed with a
  `resolver` plus request-time resolution; verified by moving the API to a new address and
  observing recovery with no reload. Costs the upstream keepalive pool, which open-source nginx
  cannot combine with re-resolution.
- **Duplicate security headers on `/health` and `/ready`.** The probe locations lacked the
  `proxy_hide_header` set that `/api/` already had, so each probe returned two copies of every
  security header and leaked the API's HSTS over plain HTTP.

**Correction (2026-07-24)** — this entry originally closed with a "Known, not fixed" note about
`ExportService.download_url` signing `export-<uuid>` onto a UUID-typed media route and returning 422.
That defect **was** fixed later the same day, in `c86d11c`, which added
`/api/v1/artifacts/{artifact_id}/download` and made `LocalStorageProvider.signed_url` route by id
shape; the note was simply never removed. Verified on 2026-07-24 against the running stack (the
artifacts route answers 400 for a missing signature rather than 404) and by
`tests/test_api_export.py::test_export_download_url_serves_the_csv`, which downloads a real export
with no `Authorization` header and asserts its bytes. Recorded as `docs/adr/0001`.

---

## [1.0.0-rc1] — 2026-07-23

First release candidate. Everything recorded below this heading is included in the tag
`v1.0.0-rc1`; entries above it are post-RC1 work.

### Added
- **Task & Activity Engine** (Doc 14) — models, migration `0026_tasks`, RBAC scopes, 15 endpoints.
- **Analytics & Reporting** (Doc 15) — migration `0027_analytics`, rollup pipeline, query service,
  report exports, 16 endpoints.
- **Frontend application** — authentication, dashboard, contacts, inbox, campaigns, templates,
  media, WhatsApp accounts, segments, pipelines, tasks, analytics, operations, admin, settings.
- **Production deployment** — multi-stage backend and frontend images, `docker-compose.production.yml`
  (10 services), edge and SPA nginx configuration, `deploy/DEPLOYMENT.md`, `.env.production.example`.
- `LICENSE` (proprietary, matching the terms already declared in `backend/pyproject.toml`).

### Fixed
- **Startup blocker** — `CORS_ORIGINS` was JSON-decoded by pydantic-settings before validators ran,
  so the empty and comma-separated forms both raised `SettingsError` at import. Every backend
  process (api, three worker pools, beat, migrate) failed to start. Now `Annotated[..., NoDecode]`.
- **Celery task registration** — workers imported no task modules, so every pool started with an
  empty registry and rejected all work. `include=TASK_MODULES` now registers all 23 tasks.
- **JSON logging** — the parent `uvicorn` logger held a plain stderr handler with `propagate=False`,
  so request lines never reached the JSON handler despite `LOG_JSON=true`.
- **`list` shadowing in `TaskService`** — a method named `list` shadowed the builtin for annotations
  later in the class body, so those signatures resolved to the method. Harmless at run time under
  deferred annotations, but it broke type resolution and `typing.get_type_hints()`.
- **`_fail` return type** in the segment compiler — annotated `NoReturn`, so the existing
  `if spec is None: _fail(...)` guard narrows as the code already reads.
- **`.gitignore`** — `.env.production.example` was matched by the broad `.env.*` rule and excluded
  from the repository, although `deploy/DEPLOYMENT.md` §2 begins by copying it.

### Changed
- Version aligned to `1.0.0-rc1` across `pyproject.toml` (PEP 440 `1.0.0rc1`), `app/__init__.py`,
  `Settings.app_version`, and `package.json`. `frontend/openapi.json` regenerated — the only
  semantic change is `info.version`.
- Frontend production build emits `sourcemap: "hidden"` and splits framework vendor chunks.

### Known limitations
- **The containerised deployment has never been executed.** No image has been built and no
  container started in any environment available to date. See §Remaining Blockers in the RC1
  report and `deploy/DEPLOYMENT.md`, which is written as a commissioning procedure.
- `tests/test_analytics_rollup.py` hard-codes `NOW = 2026-07-23 14:30`; two tests fail when real
  UTC falls inside the derived `[08:00, 14:00)` window on that date. Fixture defect, not a product
  defect.

---

### 2026-07-18 — Amendment: Message Reactions (Doc 7 → v1.1, Doc 4 v1.3 → v1.4, Doc 3 v1.3 → v1.4) — **FROZEN**
**Reason:** Phase 7 Step 9 (Message Reactions) was **blocked by a frozen-doc conflict.** Doc 4 §18.2
defines `POST /messages/{uuid}/reaction` (send a reaction), but Doc 7 §5.2's Meta capability column
declared `text/media/interactive/template/bulk` only — reaction was **deliberately undeclared** (the
Meta adapter surfaces `ChannelNotSupported`), so no channel could fulfil the endpoint. The canonical
seam (`MessageType`) and SendService likewise had no reaction path.

**Decision (owner):** amend additively so reaction is **adapter-capability-driven**; the Meta adapter
declares it (Meta Cloud API supports outbound reactions). Invent no behaviour beyond the frozen contract.

**Changed — Doc 7 (Integrations & Channel Architecture) → v1.1**
- **New §5.2a** — the Meta adapter additionally declares `send_reaction` (capability-flagged); the §5.2
  baseline matrix is unedited. Decision **CD20** (reaction is adapter-declared, not assumed).

**Changed — Doc 4 (API Design) v1.3 → v1.4**
- **§18.2** — appended the full `POST /messages/{uuid}/reaction` contract: `{emoji}` payload (empty =
  remove), single-emoji validation (`invalid_emoji`), `Idempotency-Key` required, `messages:send`, the
  24-hour free-form window rule (`window_closed`), `not_reactable`/`opt_out`, the `202` accept→deliver
  flow through SendService→Meta adapter, and failure handling. §18.2 table row unedited.

**Changed — Doc 3 (Database Design) v1.3 → v1.4**
- **New §9.2a** — confirms reaction storage: `message_type='reaction'` (already enumerated) + the
  `content_json` reaction format `{reaction:{message_id:<target wamid>, emoji}}`, target referenced by
  the target's `wamid`. **No new column, no migration.** §9.2 schema unedited.

**Decision records added:** Doc 7 **CD20**.
**Compatibility:** additive only — no schema/migration, no code (implementation follows on approval).
Docs 1, 2, 5, 6, 8–12 unedited.

### 2026-07-18 — Amendment (backfill log): Conversation Tags (FR-INB-07) — Doc 3 v1.2 → v1.3, Doc 4 v1.1 → v1.3 — **FROZEN**
**Backfilled.** The conversation-tags amendment shipped in commit `4ec1c34` with in-document `v1.3`
markers but was not logged here at the time; governance (top of file) requires every frozen-doc change
be recorded, so it is logged now.
**Changed — Doc 3:** new **§9.7 `conversation_tags`** (M:N junction reusing the `tags` taxonomy) + §12.3
M:N row, §13.2 reverse-index row, §19 sizing row. **Changed — Doc 4:** **§18.1** conversation-tag
endpoints (`POST`/`DELETE /conversations/{uuid}/tags`), the additive `tags[]` array on list/detail
reads, and the single-valued `tag` filter.
**Compatibility:** additive; realized by migration `0025_conversation_tags` (Phase 7 Step 5, HEAD
`16c65e2`). The Doc 4 marker used `v1.3` in lockstep with Doc 3 (Doc 4 `v1.2` is unused).

### 2026-07-17 — Amendment: FR-CAM-11 rate card & cost estimation (Doc 3 → v1.2, Doc 4 → v1.1) — **FROZEN**
**Reason:** Phase 6 Step 5 (Cost Engine) was **blocked**. The frozen set defined the cost engine's
*consumers* (`campaigns.estimated_cost`, `messages.cost_*`, `pricing_model`, `is_billable`) but never
its *source*: no rate-card entity or schema existed in Doc 3, Doc 7 contained no pricing content, and
Doc 12 §53 places Meta's pricing under "External … not restated here". Doc 4 §17 specified
`estimate-cost` by sample response only, with a bare `422` and no machine code. Gap analysis:
`docs/design/FR-CAM-11-GAP-ANALYSIS.md`.

**Decision (owner):** amend with the **minimum** required to unblock **pre-send estimation only**.
Invent no pricing data and no billing semantics.

**Changed — Doc 3 (Database Design) v1.1 → v1.2**
- **New §8.5 `rate_cards`** — entity, storage model, schema, resolution & money rules, country
  resolution, and an explicit deferred list. Global (no `organization_id`, per Doc 4 §17's "no
  reseller markup"), operator-managed, **ships empty**, versioned by effective dating (supersede,
  never mutate).
- **New §12.4a** — `rate_cards` value joins (no FK to contacts/templates/campaigns) + tenancy note.
- **§12.2** — `users` → `rate_cards` (`created_by`), the card's only FK.
- **§13.2** — rate-card lookup + uniqueness indexes.
- **§16 entity map** — Rate Card row added.

**Changed — Doc 4 (API Design) v1.0 → v1.1**
- **§17** — `POST /campaigns/{uuid}/estimate-cost` upgraded from sample to full contract: request,
  `200` shape with the `recipients == Σ breakdown[].count + unresolved.count` invariant, money
  serialization, the `campaigns.estimated_cost` side effect, and errors.
- **§17 wire format** — monetary fields (`unit`, `subtotal`, `estimated_total`) are **fixed-scale
  JSON strings**, not numbers: a JSON number carries no scale and most clients parse it into a
  binary float, the one representation money must not pass through. The v1.0 sample illustrated them
  as numbers; v1.1 makes the string format normative.
- **§17 route table** — bare `422` → `422(rate_card_not_configured)`, `404`.
- **New §17.1** — rate-card administration (the operator update mechanism). Requires **elevated
  administrative authority** (platform-level, never tenant-level, since the card is global); the
  concrete RBAC mapping is **left to the authorization model**, not frozen here. **Specified for
  future administration — not implemented in Phase 6 Step 5**, which delivers the read path only.
- **§31** — bulk `/estimate` cross-reference pinned to §17 as the single rate-card contract.

**Money rules fixed:** single-currency card (no FX); `unit_price DECIMAL(12,6)`; subtotals exact
(no intermediate rounding); total rounded **once** to 4 dp **ROUND_HALF_UP** at the storage boundary.

**Country resolution fixed:** `contacts.country_code IS NULL` ⇒ recipient is *unresolved* — counted
and reported, excluded from the total, **never** silently dropped and **never** derived from the
`wa_id` E.164 prefix (no prefix→country dataset is specified).

**Contradictions resolved:**
1. `messages.category` permits `service` while `ck_tpl_category` permits only three categories — a
   campaign always sends a template, so `service` is unreachable from an estimate. Doc 4 §17's sample
   note referencing free-tier **service** conversations was incorrect and is **corrected**.
2. Rate card treated as internal authority but declared external (Doc 12 §53) — resolved by making it
   operator-managed data that ships empty, with the platform restating no Meta pricing.
3. "No reseller markup" (global card) vs per-row `cost_currency` (per-tenant currency) — resolved by
   the single-currency invariant: `cost_currency` *records* the card's currency, it does not select one.
4. Precision mismatch (`DECIMAL(12,6)` per message vs `DECIMAL(14,4)` per campaign) — resolved by the
   round-once-at-the-boundary rule.

**Explicitly DEFERRED / OUT OF SCOPE** (unchanged, still undefined — Doc 3 §8.5.5):
`messages.pricing_model`, `messages.is_billable`, `messages.cost_*`, `campaign_recipients.cost_amount`,
**`campaigns.actual_cost` population**, the Meta pricing **webhook payload**, billing reconciliation,
and finance reporting.

> **Rationale — `campaigns.actual_cost` remains unset:** `campaigns.actual_cost` must represent the
> provider-authoritative charge. Computing it from the local rate card would produce another estimate
> rather than the provider's billed amount. Estimated and actual values may legitimately diverge due
> to provider pricing rules, discounts, credits, or future pricing changes. Therefore
> `campaigns.actual_cost` remains unset until an authoritative provider pricing source and contract
> are defined.

**Impact:** documentation only — no code, schema migration, or pricing data in this change. Docs 1, 2,
5–12 unedited. Implementation of Phase 6 Step 5 resumes from this amended specification on approval.

### Design documents — status
- **Doc 12 — Enterprise Governance** — `v1.1` (`12-ENTERPRISE-GOVERNANCE.md`; §1–§55 = v1.0 baseline, §56–§66 added in the governance-handbook enhancement pass; 66 sections, 22 diagrams). Master governance / single entry point referencing Docs 1–11 without duplication.
- **Doc 11 — Operations Runbook** — delivered, awaiting owner approval (`11-OPERATIONS-RUNBOOK.md`; 85 sections, 15 diagrams, OD1–OD40). Operational-only; references Docs 1–10 without redefining them.
- **Doc 9 — AI & Automation Architecture** — delivered, awaiting owner approval (`09-AI-AUTOMATION-ARCHITECTURE.md`; 52 sections, AD1–AD43). Additive; no frozen doc edited.
- **Doc 10 — Testing & QA Architecture** — `v1.1` **FROZEN** on 2026-07-15 (`10-TESTING-QA-ARCHITECTURE.md`; §1–§60 = v1.0 baseline, §61–§72 added in pass; 72 sections, 18 diagrams, TD1–TD65). Additive; references Docs 1–9 without duplication.
- **Doc 1 — SRS** — `v1.0` **FROZEN** on 2026-07-15 (authoritative specification).
- **Doc 2 — Expanded Feature Matrix** — `v1.0` **FROZEN** on 2026-07-15.
- **Doc 3 — Database Design** — `v1.4` **FROZEN** (v1.0 baseline; **§21 Business Event Ledger** → v1.1; **§8.5 `rate_cards`** + §12.4a/§12.2/§13.2/§16 → v1.2 on 2026-07-17; **§9.7 `conversation_tags`** + §12.3/§13.2/§19 → v1.3 on 2026-07-18; **§9.2a reaction payload** → v1.4 on 2026-07-18).
- **Doc 4 — API Design Specification** — `v1.4` **FROZEN** (v1.0 on 2026-07-15 incl. enhancement pass §29–§36 + §23.1/§24.1/§27.1/§27.2; **§17 estimate-cost** + **§17.1 rate-card admin** → v1.1 on 2026-07-17; **§18.1 conversation tags** → v1.3 on 2026-07-18; **§18.2 reaction contract** → v1.4 on 2026-07-18).
- **Doc 5 — UI/UX Design Specification** — `v1.1` **FROZEN** (v1.0 = Parts A–F incl. F1–F15; **Part G Executive Business Dashboard** added in the final additive pass).
- **Doc 6 — Queue & Scheduler Design** — `v1.2` **FROZEN** (pass 1 §21–§34 at v1.0; pass 2 §35–§46 → v1.1; final additive pass **§47 Enterprise Domain Event Bus** + **§48 Business KPI Metric Catalog** → v1.2).
- **Doc 7 — Integrations & Channel Architecture** — `v1.1` (delivered v1.0, awaiting owner approval; **§5.2a Meta `send_reaction` capability** amendment + decision **CD20** added on 2026-07-18 → v1.1). Realizes the dual-channel / Support Connector spec that frozen Doc 6 forward-references as "Doc 6.5" (content in `07-INTEGRATIONS-CHANNEL-ARCHITECTURE.md`; Doc 6 unedited). Defines new **additive** entities (connector registry/session/health, lead pipelines/stages, conversation tags, assignment rules) and additive columns (`connector_id`, lead references) to be applied via migration when built — no frozen doc edited.
- **Doc 8 — Deployment & DevOps Architecture** — `v1.2` **FROZEN** (`08-DEPLOYMENT-DEVOPS.md`; §1–§41 = v1.0 baseline, §42–§55 added in the enhancement pass; **§56 Platform Portability Appendix** added in the final additive pass; DD1–DD41).

### 2026-07-15 — Major requirement: dual-channel (Support Connector) architecture
**Reason:** Owner requires two channels — Channel 1 (Official Meta WhatsApp Cloud API) and Channel 2 (vendor-neutral **Support Connector** abstraction) — unified in one CRM, with the whole platform depending only on a Channel Abstraction Layer, never a specific connector implementation.
**Decision (owner Option 3):** Keep Docs 1–6 **frozen**; centralize all dual-channel design in a **dedicated Doc 6.5**. Docs 7+ reference Doc 6.5 rather than modifying frozen docs.
**Compliance advisory (logged):** The current QR-based connector is treated strictly as a swappable implementation detail; the architecture is designed around the abstraction only, not any specific unofficial implementation. Concrete adapters must comply with their channel's terms of service; official adapters are recommended where available. This advisory is retained so Doc 1 CMP-01 ("official API only") is read together with the dual-channel decision.
**Impact:** No edits to frozen Docs 1–6; new concepts (connector registry/session/health, lead management, connector dashboard, connector endpoints) live in Doc 6.5 and are referenced by later docs.
- **Doc 7 — Deployment Architecture** — not yet started.
- **Doc 8 — Development Roadmap** — not yet started.

### 2026-07-15 — Document order adjusted
**Reason:** Owner chose to design the UI/UX before the Queue & Scheduler internals.
**Changed:** Doc 5 = UI/UX Design; Doc 6 = Queue & Scheduler Design (was Doc 5); Docs 7–8 unchanged.
**Impact:** No change to frozen Docs 1–4.

### Notes
- No changes to frozen documents yet. When a major business requirement changes a frozen
  document, add a dated entry here (e.g., `### 2026-08-01 — SRS v1.0 → v1.1`) describing
  what changed and why, then bump that document's version header.

---

## Module releases

### 2026-07-17 — **Module 2 — CRM COMPLETE** FROZEN (`v0.5.4-module2-foundation`)
Closes the module opened by `v0.2.0-crm-foundation`, whose async half was deferred by dependency to
the Queue Engine + Storage. **Every mandatory SRS contact requirement is now built:** FR-CON-01/02
(CRUD, keyset pagination at 1M+), **03/04** (CSV **and Excel** import with column mapping + per-row
validation), **05** (async import: progress + downloadable error report), **06** (duplicate detection
with `skip`/`merge`/`overwrite` on import, plus a standalone dedup scan/merge), **07/08** (bulk edit
and bulk soft-delete over a selection or filter), **09** (tags), **10** (segments), **11** (typed
custom attributes), **12** (advanced AND/OR search), **14** (activity timeline), **15** (export to
**CSV / Excel / JSON**).

**Steps:** 1–4 = `v0.2.0-crm-foundation` (sync surface) · 5A `v0.5.0-module2-import` · 5B
`v0.5.1-module2-export` · 5C `v0.5.2-module2-bulk` · 5D `v0.5.3-module2-formats`.
**Migrations:** 0005–0008 (contacts, tags/events/leads, segments, custom attributes), 0011 (imports),
0012 (exports), 0013 (bulk_jobs).
**State at freeze:** 249 backend tests passing, ruff clean, migrations 0001–0013 reversible, zero
model↔migration drift, OpenAPI 3.1.0 valid (62 paths / 87 operations). RBAC uses only seeded catalog
permissions (`contacts:*`, `segments:*`).

**Architectural note.** The async CRM is deliberately thin: every bulk path (import, export,
bulk-update/delete, merge) resolves its audience through the **same rule compiler** as segments and
search, walks it in **keyset batches**, and applies each item **through the CRM's own services** — so
a row created by an import and a row edited in bulk obey exactly the same validation, timeline and
audit rules as one touched through the single-contact API. Format is only a rendering choice
(`app/crm/formats.py`); the audience and columns are shared.

**Still deferred (unchanged, by dependency — NOT missing):**
| Deferred | Reason | Lands with |
|---|---|---|
| Auto opt-out on "STOP" (FR-CON-13, the requirement's second half; status field itself is built) | Needs inbound message handling | Messaging (M4) |
| Internal notes, contact assignment, `conversation_lead`/`lead_stage_transitions` | Frozen docs scope these to `conversations` | Inbox (M7) |
| `Idempotency-Key` (Doc 04 §8), `bulk`/`read`/`write` rate classes (Doc 04 §9) | **Cross-cutting** — belong to every side-effectful POST, not to contacts alone; import/export/bulk all shipped without them | Own hardening step |
| Doc 04 §30's wider bulk family (`/contacts/bulk` create, `bulk-tag`, `bulk-attributes`, `/campaigns/bulk-action`, `/templates/bulk`) | Out of §14.1's contact scope | Their own modules |

### 2026-07-17 — **Module 2 — Step 5D: Excel import, Excel & JSON export** (`v0.5.3-module2-formats`)
**Scope delivered (no migration, no new endpoint):** **`.xlsx` import** (FR-CON-04) and **Excel/JSON
export** (FR-CON-15) — the last two mandatory CRM requirements, and ones the schema already promised:
`exports.format`'s `ck_exports_format` constraint (Doc 03 §11.6) and Doc 06 §2.3 (`exports` =
"CSV/Excel/JSON") declared all three formats while the services accepted only CSV.

**Reuse over reimplementation:** `read_xlsx` returns the **same header-keyed rows** as `read_csv`, so
the import pipeline's mapping, validation and error report are format-agnostic and untouched; the
export gains a per-format **writer** while the audience, `EXPORT_COLUMNS` and keyset streaming loop
stay shared. CSV output is byte-for-byte unchanged (asserted by test). Excel quirks handled at the
reader: a phone typed as a number renders as `14155550001`, never `1.4155550001e+10`; blank trailing
rows are dropped. Adds `openpyxl` (read-only / write-only modes, so neither direction builds a full
cell graph). **State:** 249 tests passing (+11), ruff clean.

### 2026-07-17 — **Module 2 — Step 5C: bulk operations & duplicate merge** (`v0.5.2-module2-bulk`, migration 0013)
**Scope delivered:** the last CRM items deferred to the Queue Engine (CHANGELOG 2026-07-16 deferral
table) — **bulk update** (FR-CON-07: `add_tags` / `remove_tags` / `set_attributes`), **bulk delete**
(FR-CON-08, soft), and **duplicate scan / merge** (FR-CON-06, `report` or `merge`). All three are
async-only per Doc 04 §14.1: `POST /contacts/bulk-update`, `POST /contacts/bulk-delete`,
`POST /contacts/deduplicate` return **`202` + job** and run on the Queue Engine; progress and the
**§29 partial-success envelope** are polled at `GET /contacts/bulk/{uuid}`. RBAC `contacts:write`
(already seeded — no catalog change); every operation audited (`bulk.started`, `bulk.completed`,
`contact.merged`).

**Design decisions (each traceable to a frozen doc):**
- **Addressing** follows Doc 04 §30's two mutually-exclusive modes — explicit `ids` or a `filter` —
  with the optional **`expected_count` safety guard** (resolved count differs → **409**, act on
  nothing). Filters reuse the **same rule compiler** segments/search/export use, so one audience
  definition serves all four.
- **Per-item commit** (Doc 04 §29): a rejected contact lands in `errors[]` (capped at 100) plus a
  signed, downloadable `error_report_url`, and never rolls back the rest.
- **Idempotent by construction** (Doc 06 §8): attaching a present tag, deleting a deleted contact and
  merging an already-merged group are all no-ops, so at-least-once redelivery converges without
  snapshotting a million-row selection. Every action is applied **through the CRM's own services**, so
  a bulk edit obeys the same validation/timeline/audit rules as the single-contact endpoints.
- **Merge semantics** (FR-CON-06): the **oldest** contact of a group survives; blanks are filled from
  duplicates (a set primary field is never overwritten), tags and attribute values move across, the
  duplicate is soft-deleted, and the merge is recorded on the survivor's timeline (`contact_merged`).
  `wa_id`/`phone_e164` are never merged — they are the survivor's identity.
- **Memory-bounded**: the audience is walked in keyset batches and the dedup scan pages over *groups*,
  so a 1M-row table never materialises.

**State:** 237 backend tests passing (+16), ruff clean, migrations 0001–0013 reversible, zero
model↔migration drift, OpenAPI 3.1.0 valid (62 paths / 87 operations).

**Deferred (unchanged by this step):** `Idempotency-Key` (Doc 04 §8) and the `bulk`/`read`/`write`
rate classes (Doc 04 §9) are **cross-cutting** and remain unbuilt — import/export shipped without
them too. They should be retrofitted across every side-effectful POST in one step, not bolted onto
contacts alone. Doc 04 §30's wider bulk family (`/contacts/bulk` create, `/contacts/bulk-tag`,
`/contacts/bulk-attributes`, `/campaigns/bulk-action`, `/templates/bulk`) belongs to its own module;
this step delivers only the three endpoints Doc 04 §14.1 scopes to contacts.

### 2026-07-16 — **Module 2 — Step 5B: contact export (async)** (`v0.5.1-module2-export`, migration 0012)
*(Backfilled 2026-07-17: the tag shipped without its changelog entry, which the governance policy
above requires.)*
**Scope delivered:** `exports` (Doc 03 §11.6) + `POST /contacts/export` → **`202` + job** and
`GET /contacts/export/{uuid}` → progress + **signed, expiring download URL** (FR-CON-15, CSV at this
step; Excel/JSON landed in 5D). Runs on the Doc 06 §2.3 `exports` queue. The filter resolves through
the **same compiler** segments/search use, so an export returns exactly what its preview showed, and
the result is walked in **keyset batches** rendered incrementally — a 1M-row export never
materialises 1M ORM objects. The artifact is written through the **Storage** abstraction and bounded
by `expires_at` (an expired export stops serving a URL). Re-running regenerates rather than
duplicating (Doc 06 §8). RBAC `contacts:export`; audited (`export.started` / `export.completed`).
**State at the time:** 213 tests passing, ruff clean, zero drift.

### 2026-07-16 — **Module 2 — Step 5A: contact import (async)** (`v0.5.0-module2-import`, migration 0011)
*(Backfilled 2026-07-17: the tag shipped without its changelog entry, which the governance policy
above requires.)*
**Scope delivered:** `imports` (Doc 03 §11.6) + `POST /contacts/import` → **`202` + job** and
`GET /contacts/import/{uuid}` → progress + **downloadable error report** (FR-CON-03/05/06). The
request path never parses a byte: the file is uploaded first via Media (§16) and referenced by
`upload_id`; the work runs on the Doc 06 §2.3 `imports` queue. Rows stream through the CRM's own
`ContactService`, so an imported contact is validated, deduped, timelined and audited by exactly the
same rules as one created through the API — no duplicated business logic. A bad row is collected
into the error report and **never aborts the import**; progress is committed as it goes and
already-imported rows are no-ops under `skip`/`merge`, so a retried task converges (Doc 06 §8).
Dedup `skip`/`merge`/`overwrite` on normalized `wa_id` (FR-CON-06). RBAC `contacts:import`; audited
(`import.started` / `import.completed`).
**State at the time:** 203 → 213 tests passing, ruff clean, zero drift.

### 2026-07-16 — **Storage Foundation** FROZEN (`v0.4.0-storage-foundation`)
**Scope delivered (migration 0010):** storage abstraction + provider registry (Doc 8 §14,
FR-MED-06, DD16) with a **local volume provider** (default) and an **S3-compatible provider
contract** that registers without touching callers — selecting an unregistered backend fails
loudly rather than degrading; **signed URL framework** (FR-MED-09: HMAC binds media id to
expiry, constant-time verify, expired→410 distinct from invalid→403); **media validation**
(FR-MED-01..04: per-type MIME allow-lists + Cloud API size ceilings → 413/415/422 *before* any
bytes are stored); **virus scan interface** (Doc 8 §26 — contract + hook only, no scanner ships,
fail-closed if a configured scanner errors); **upload/download services** (validate → scan →
hash → dedup → store → record; SHA-256 dedup per org, FR-MED-05). `media_assets` (Doc 3 §7.2)
holds metadata + a reference — **never blobs**. APIs: `POST /media/upload`, `GET /media`,
`GET /media/{id}`, `GET /media/{id}/content` (signed URL), `GET /media/{id}/download`
(signature-authenticated), `DELETE /media/{id}`. RBAC `media:read`/`media:write`; audited.

**Security fix (found by test):** the local provider stripped `..` textually, which could yield
an absolute path that re-rooted the join and escaped the storage root. Keys are now resolved and
required to stay under the root.

**State at freeze:** 203 backend tests passing, ruff clean, migrations 0001–0010 reversible,
zero drift.

**Not built (their own modules):** media processing (thumbnails/transcode), Meta media-id
refresh/caching (FR-MED-07), retention sweeps (FR-MED-08), a concrete S3 provider, a concrete
virus scanner.

### 2026-07-16 — **Module 6 — Queue Engine Foundation** FROZEN (`v0.3.0-queue-foundation`)
**Scope delivered (branch `feature/module6-queue-engine`, migration 0009):** Celery application
(Redis broker/backend; `task_acks_late` + `task_reject_on_worker_lost` + `prefetch_multiplier=1`
= at-least-once with no hoarding, Doc 6 §3.4/D7); **queue registry** encoding the Doc 6 §2.3
master specification as data (18 queues with purpose/priority/pool/retry/timeouts/failure
destination) — routing, worker pools and the Queue Monitor all read this one source; **smart
retry framework** (Doc 6 §6: failure classes, per-class attempt caps, exponential backoff with
full jitter, pluggable per-channel error maps); **worker framework** (`TrackedTask`: durable
`job_metadata` state, structured logging, smart retry, terminal DLQ park); **DLQ foundation**
(Doc 6 §7: durable parked-task store, fingerprint grouping, replay through the same idempotent
processor, discard — all audited); **Redis worker registry + TTL heartbeat** (§3.4); **queue
health** from live broker depth + fleet (§13.2). APIs: `GET /jobs`, `GET /jobs/{id}`,
`POST /jobs/{id}/cancel`, `GET /queues` (`system:read`/`system:manage`).

**State at freeze:** 180 backend tests passing, ruff clean, migrations 0001–0009 reversible,
zero drift, OpenAPI 49 paths. Celery added to the environment (was declared, not installed).

**Deliberately not built (they bind to this fabric in their own modules):** domain tasks for
sends, webhooks, imports, exports, media, AI and the Support Connector; Celery Beat schedules;
rate gate / circuit breaker (Doc 6 §5/§6.4 — belong with the send pipeline);
`monitoring_metrics` time-series (Doc 3 §11.7 — Monitoring module).

### 2026-07-16 — **Module 2 — CRM Foundation** FROZEN (`v0.2.0-crm-foundation`)
**Scope delivered (branch `feature/module2-contacts-crm`, migrations 0005–0008):**
- **Step 1** (`v0.2.0-module2-step1`) — `contacts` (Doc 3 §6.1): CRUD, dedup by `(org, wa_id)`, E.164
  validation, opt-in transitions, optimistic concurrency, soft delete, keyset pagination, search,
  filters, whitelisted sorting.
- **Step 2** (`v0.2.0-module2-step2`) — `tags` + `contact_tags` (Doc 3 §6.2, FR-CON-09),
  `contact_events` timeline (Doc 3 §6.5, FR-CON-14), `lead_pipelines` + `lead_stages`
  configuration with the default pipeline (Doc 7 §19.2, §23.2).
- **Step 3** (`v0.2.0-module2-step3`) — `segments` + `segment_rules` (Doc 3 §6.4, FR-CON-10):
  saved dynamic filters, rule tree, preview, cached counts.
- **Step 4** (`v0.2.0-module2-step4`) — `custom_attribute_definitions` + `contact_attribute_values`
  (Doc 3 §6.3, FR-CON-11) and `POST /contacts/search` (FR-CON-12).

**State at freeze:** 153 backend tests passing, ruff clean, migrations 0001–0008 reversible, zero
model↔migration drift. RBAC uses only seeded catalog permissions (`contacts:*`, `segments:*`).

**Deferred by dependency (owner-approved; NOT missing — scheduled to their prerequisite module):**
| Deferred | Reason | Lands with |
|---|---|---|
| Contact Import / Export | Doc 4 §14.1 mandates async `202 + job`; FR-CON-05 requires async progress + error report | Queue Engine + Storage |
| Bulk update / delete, Duplicate merge | Doc 4 §14.1 `202 + job` (bulk class) | Queue Engine |
| Internal Notes, Contact Assignment, `conversation_lead`/`lead_stage_transitions` | Frozen docs scope these to `conversations` (Doc 3 §9.5 `internal_notes.conversation_id NOT NULL`; SRS FR-INB-03/05) | Inbox / Messaging |
| Auto opt-out on "STOP" (FR-CON-13) | Requires inbound message handling | Messaging |

### 2026-07-16 — **Module 1 — Foundation** FROZEN (`v0.1.0-foundation`)
Auth, RBAC, users, organization, settings/feature-flags, API keys, audit read API, preferences.
110 tests, 91% coverage, migrations 0001–0004 reversible, OpenAPI 3.1.0 valid. Deferred to their
designated modules: password reset (email), MFA (Doc 12 §56 "Future"), user activity feed
(`activity_logs`), inbound API-key authentication (future public API).

---

## Change log entries

### 2026-07-17 — Implementation order: frontend (M2) deferred — backend-first until the APIs are complete
**Reason:** Owner ruling. The frontend is deliberately deferred until the backend API surface is
complete, so the SPA is built once against a settled contract rather than chased across modules.
**Deviation from:** Doc 12 §15 / §42, which order delivery **M1 → M2 (Frontend Shell + Auth UI) →
M3 (Contacts) → M4 …**. Implementation has instead run M1 → M3 (Contacts) → Queue Engine → Storage
→ M3 async completion, leaving **M2 unbuilt** (`frontend/` holds only the scaffold committed with
M1: shell, theme, React Query, two routes — no login, no protected routing).
**Why this is safe:** Doc 12 §14's dependency graph is **not** violated — M2 depends on M1 (built),
and nothing built so far depends on M2. Only the *order* changed, not the dependency rule. The
Queue Engine and Storage Foundation were likewise built ahead of their manifest position because
M3's import/export/bulk items depend on them (Doc 04 §14.1 mandates `202 + job`).
**Impact:** No frozen document edited. §15/§42 remain the canonical order; this entry records the
approved departure. M2 re-enters the sequence once the backend APIs are complete.
**Naming note (no code impact):** commit/tag labels do not match the Doc 12 §56 manifest — "Module 2"
in git history is manifest **M3 (Contacts)**, and "Module 6 — Queue Engine" is the async fabric, not
manifest **M6 (Campaigns)**, which is not started. The manifest remains authoritative.

### 2026-07-17 — Module 2 Step 5C — additive deviations required to deliver bulk operations
**Reason:** Delivering Doc 04 §14.1's `bulk-update` / `bulk-delete` / `deduplicate` surfaced two gaps
in the frozen set. Recorded here per the §27 change-management rule; **no frozen document edited**.
1. **New table `bulk_jobs`** (migration 0013), additive, reversible, sitting beside `imports`/`exports`
   in the Doc 03 §11.6 job-record family. *Why:* Doc 04 §30 says async bulk ops report
   `processed/total/succeeded/failed`, but Doc 03 §11.7's `job_metadata` has **no progress columns
   and no `organization_id`**, and `imports` cannot be reused (`format` is `NOT NULL`, and its
   `source_key`/`mapping_json` are file-import specific). Doc 12 §56 lists no bulk table for M3
   because §30 assumed `job_metadata` would carry this; it cannot.
2. **Poll endpoint `GET /contacts/bulk/{uuid}`** (`contacts:write`) instead of Doc 04 §30's
   "poll `GET /jobs/{uuid}`". *Why:* §22 gates `/jobs/{uuid}` behind **`system:read`** and
   `job_metadata` is organization-blind, so that route can serve neither a `contacts:write` operator
   nor tenant scoping — §30 and §22 contradict each other. The chosen shape is the one §14.1 already
   defines for the import/export progress endpoints.
3. **Queue placement:** bulk work runs on the existing **`imports`** queue — Doc 06 §2.3 scopes it to
   long-running CRM "parse, validate, dedup, upsert" work (P3, Jobs pool, 300s/600s,
   `job=failed + error report`), and Doc 12 §56 grants M3 no other write queue. **No queue was added**
   to the frozen §2.3 taxonomy; the three operations stay independently traceable via distinct task
   names.
**Impact:** Additive only. Docs 3/4/6/12 unedited; if the owner wants the frozen text reconciled to
match, that is a separate documentation pass.

### 2026-07-16 — FINAL architecture additive pass (A–E) — architecture PERMANENTLY FROZEN
**Reason:** Owner-approved final enterprise additions (A–E). Purely additive; existing content, numbering,
and section IDs preserved. After this pass **the architecture is permanently frozen** and implementation
(Module 1) resumes.
**Changed (append-only, before each doc's end marker; headers version-bumped):**
- **A — Business Event Ledger → Doc 3 (v1.0 → v1.1).** Appended **§21 Business Event Ledger & Enterprise
  Event Taxonomy**: `business_event_types` catalog + immutable, time-partitioned `business_events` ledger (DDL),
  a 25-event canonical taxonomy (`lead.created` … `customer.reactivated`, `ai.approved/rejected`, `data.exported`,
  …), append-only/versioned/replay-ready properties, and its relationship to `audit_logs` / `contact_events`.
- **B — Domain Event Bus → Doc 6 (→ v1.2).** Appended **§47 Enterprise Domain Event Bus & Extension Points**:
  durable-first bus over the ledger, event envelope, topics, publish/subscribe, per-subject ordering, idempotency,
  retry/DLQ, replay, fan-out (mermaid), decisions D35–D37.
- **C — Business KPI Metric Catalog → Doc 6 (→ v1.2).** Appended **§48 Business KPI Metric Catalog**: 15 KPIs
  (Reactivation Rate, Revenue Recovery, Cost per Reactivation, Campaign ROI, Lead Funnel/Velocity, AI Acceptance,
  Agent Productivity, Forecast Metrics, …) with Purpose / Formula / Source events / Refresh / Owner / Future
  columns; decision D38. Single source of truth for all business KPIs.
- **D — Executive Business Dashboard → Doc 5 (v1.0 → v1.1).** Appended **Part G — Executive Business Dashboard**:
  executive KPI cards, business trend charts, conversion funnel, revenue recovery, campaign ROI, lead-pipeline
  overview, agent performance, forecast widgets, business-health score; filters (date/campaign/agent/region/
  channel = Meta / Support Connector); export (PDF/Excel/scheduled reports); reads **only** the KPI Catalog
  (Doc 6 §48) from pre-aggregated rollups — **no operational-widget duplication** (those remain in B2).
- **E — Platform Portability Appendix → Doc 8 (v1.1 → v1.2).** Appended **§56 Platform Portability Appendix**:
  Full Data Export Guarantee, Data Ownership, Vendor Independence, Exit Strategy, open Export Formats,
  Validation/Audit/Integrity Verification, Backup Compatibility, Future Migration Readiness — an architecture
  guarantee built on existing backups (§9), storage (§10) and export APIs (Doc 4 §20).
**New governance items (additive to the Doc 4 §4.3 permission catalog; seeded when the corresponding module is
built, not now):**
- Permission **`analytics:executive`** — gates the Executive Business Dashboard (roles: Executive, Owner, Admin).
  Finance-sensitive figures (ROI/revenue/cost) additionally gated by existing **`finance:read`** (Doc 6 §37).
**Explicitly NOT created (per the owner's final ruling):** Plugin SDK / marketplace / general plugin framework,
legacy migration/ETL engine, data warehouse, MDM, or any additional standalone governance document.
**Impact:** Additive only — no existing section edited, renumbered, or deleted. Docs 3, 5, 6, 8 version headers
and end markers updated. **Architecture is now permanently frozen; Module 1 implementation resumes.**


### 2026-07-15 — Doc 12 (Enterprise Governance) v1.0 → v1.1
**Reason:** Owner-requested governance-handbook enhancement pass.
**Changed:** Appended **§56–§66** with no edits to §1–§55: §56 Enterprise Module Manifest, §57 Feature-to-Module Mapping, §58 Enterprise Permission Matrix, §59 Configuration Inventory, §60 Naming Standards, §61 Technology Dependency Inventory, §62 Software Lifecycle, §63 Documentation Ownership Matrix, §64 Readiness Scorecard, §65 Product Version Roadmap, §66 Enhancement Review. Added 2 diagrams (lifecycle, version roadmap).
**Impact:** Additive only; no frozen document edited. Makes Doc 12 the definitive governance handbook.


### 2026-07-15 — Doc 10 (Testing & QA) v1.0 → v1.1
**Reason:** Owner-requested first post-freeze additive enhancement pass.
**Changed:** Appended **§61–§72** with no edits to §1–§60: §61 Test Case Management, §62 Defect & Bug Management, §63 Release Certification Framework, §64 UAT, §65 Exploratory Testing, §66 Production Verification, §67 Certification Matrix, §68 Test Data Governance, §69 Cross-Document Traceability, §70 Testing Maturity Model, §71 Decision Appendix (TD52–TD65), §72 Final 15-perspective Review. Added 5 diagrams and 14 decision records; extended glossary + cross-references.
**Impact:** Additive only; no frozen document edited.


### 2026-07-15 — Doc 9 (AI & Automation Architecture) started
**Reason:** Owner requested the AI architecture document (`09-AI-AUTOMATION-ARCHITECTURE.md`, v1.0).
**Changed:** New document; architecture-only; plugs into frozen Docs 1–8 without modifying them. Any new data fields (AI interaction record: confidence/reasoning/sources/cost/latency/model_version) are **additive** extensions to Doc 3's AI tables, applied via migration when built.
**Impact:** No frozen document edited.


### 2026-07-15 — Doc 6 (Queue & Scheduler) v1.0 → v1.1
**Reason:** Owner-requested second additive enhancement pass (post-freeze), per the changelog-versioning policy.
**Changed:** Appended **§35–§46** with no edits to §1–§34: §35 Queue Analytics Engine, §36 Predictive Capacity Planning, §37 Cost Analytics Engine, §38 Queue Simulation Engine, §39 Queue Versioning Strategy, §40 Maintenance Mode, §41 Disaster Replay Architecture, §42 Enterprise SLA Matrix, §43 Queue Governance, §44 Queue Audit Architecture, §45 Architectural Decision Appendix (RabbitMQ/Kafka/Redis Streams/SQS/Pub-Sub/Service Bus/Temporal/BullMQ/NATS), §46 self-review. Added decisions D24–D34.
**Impact:** Additive only. Two new permissions flagged for the Doc 4 catalog (`finance:read` for cost data, `ops:emergency` + `ops:dlq_delete` for break-glass ops) — to be seeded when Module 1 RBAC is built; no edits to frozen Docs 1–5.

### 2026-07-15 — Doc 8 (Deployment & DevOps) v1.0 → v1.1
**Reason:** Owner-requested additive enhancement pass.
**Changed:** Appended **§42–§55** with no edits to §1–§41: §42 Environment Strategy (full lifecycle), §43 CI/CD Architecture, §44 Infrastructure Inventory, §45 Configuration Management, §46 Release Management, §47 Business Continuity Planning, §48 Compliance Architecture (GDPR/DPDP), §49 Dependency Governance, §50 Cost Optimization, §51 Production Readiness Checklist, §52 Operational KPIs, §53 Orchestrator Decision Appendix, §54 Cross-Document Traceability, §55 Final Self-Review. Added decisions DD33–DD41.
**Impact:** Additive only; no frozen doc edited.

### (older entries below)

<!-- Add newest entries at the top, using this template:

### YYYY-MM-DD — <Document> <old-version> → <new-version>
**Reason:** <business/requirement driver>
**Changed:**
- <bullet describing the change>
**Impact:** <downstream documents/modules affected>

-->
