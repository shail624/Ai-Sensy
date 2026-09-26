# Design 64 — PAR-HIST-01 Advanced Chat History Filters and Shared Views

**Status:** Repository implemented  
**Depends on:** Dedicated Chat History, shared conversation/message query authority, immutable audit
log, campaign registry, RBAC and PAR-DL-02 transcripts

## Product boundary

Chat History remains a read-only workspace over the existing conversation and message authorities.
This slice adds list discovery and reusable organization views; it does not create a second inbox,
copy messages, mutate conversations, search message text, send customer messages or broaden audit
access.

## Filter semantics

- `from` is inclusive and `to` is exclusive UTC at the API. The UI accepts local calendar days and
  turns **Through** into the exclusive start of the following day.
- Date bounds apply to the list's existing effective activity key:
  `COALESCE(last_message_at, created_at)`.
- `campaign` accepts a public campaign UUID and matches a conversation only when the tenant-scoped
  message ledger contains a row for that campaign.
- `has_media=true` matches a conversation only when the ledger contains a message with a persisted
  media-asset reference.
- `has_audit=true` matches direct conversation assignment/status audit evidence. It requires
  `audit:read`; callers without that permission receive `403` rather than an inferred result.
- Filters compose with existing contact, status, assignee, number, tag and customer search filters
  and retain the existing newest-first keyset pagination.
- Malformed identifiers and inverted ranges are bounded client errors. Unknown or foreign public
  identifiers return an empty page, preserving tenant non-disclosure.

The large message ledger and audit table are queried with correlated `EXISTS` predicates over their
existing conversation/campaign/entity indexes. Results never depend on how many rows the browser
has loaded.

## Organization-shared views

`conversation_history_views` stores one validated, portable filter JSON document with an
organization, creator, public UUID, name and timestamps. Names are case-insensitively unique per
organization and creation is serialized on the organization row. The bounded maximum is 25 shared
views per organization.

- Every `inbox:read` user can list and apply ordinary shared views.
- New `inbox:views_manage` governs creation/deletion and is included in the Manager preset.
- Audit-scoped views may be created and listed only with `audit:read`; they are omitted from an
  ordinary inbox reader's list.
- Create/delete are immutable-audit events. Delete and list are tenant-scoped; foreign UUIDs are
  indistinguishable from missing ones.
- Personal Live Chat preferences remain unchanged. Shared Chat History views are a separate server
  authority rather than a silent rewrite of existing browser/server preference data.

## API and UI

- `GET|POST /api/v1/conversation-history/views`
- `DELETE /api/v1/conversation-history/views/{view_id}`
- `GET /api/v1/conversations` adds declared `from`, `to`, `campaign`, `has_media` and `has_audit`
  query parameters.

The Chat History toolbar shows a compact Advanced control and horizontally scrollable team-view
chips. Advanced filters open as a bottom sheet on phones and a centered dialog on larger screens.
The surface includes date/campaign/media/audit controls, inverted-range validation, permission-
truthful fields, view creation/deletion states and a single Clear/Apply decision. Basic status,
agent, channel and tag controls remain immediately visible.

## Persistence and contract

Migration `0054_chat_history_filters_views` adds the view table and permission after
`0053_conversation_transcript_exports`; the graph remains one linear 55-revision head. OpenAPI is
223 paths and generated TypeScript is synchronized. No queue, provider, storage, export or customer-
send contract changes.

## Validation

- New backend filter/view/API coverage: **10/10**.
- Existing Inbox/conversation/QR integration regression: **77/77**.
- Migration upgrade/downgrade/re-upgrade and single-head checks: **5/5**.
- Chat History UI: **41/41**; complete frontend: **41 files / 850 tests**.
- Static gate: **6/6**, strict mypy **314 files**, OpenAPI drift and browser-test types pass.
- Vite **8.2.2** production build passes; Chat History chunk is **23.82 kB / 6.91 kB gzip**.
- Complete backend: **1547 passed / 6 MySQL-only skipped / 0 failed in 458.04s**.

## Remaining boundary

Chat History still needs authenticated representative-data review across the supported device/
browser/WCAG matrix and target-host query/performance commissioning. Docker/security release
rerun, target-host TLS/secrets/monitoring/restore/UAT and owner acceptance remain separate release
gates. This milestone performs no commit, push, provider call, customer send or deployment.
