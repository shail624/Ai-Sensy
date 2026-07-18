# API Design Specification
### Self-Hosted WhatsApp Business Platform

| | |
|---|---|
| **Document** | 4 of 8 — API Design Specification (authoritative API contract) |
| **Version** | 1.0 — **FROZEN** (after owner-requested enhancement pass) |
| **Date** | 2026-07-15 |
| **Status** | ✅ Frozen — do not edit; record changes in `CHANGELOG.md`. §29–§36 added in the enhancement pass. |
| **Base URL** | `/api/v1` |
| **Media type** | `application/json` (errors: `application/problem+json`) |
| **Preceded by** | Docs 1–3 (frozen) |
| **Followed by** | Doc 5 — Queue & Scheduler Design |

> This is the **authoritative API contract**. It is a design document — **no application code,
> routers, or models**. It defines the URL surface, request/response schemas, auth, permissions,
> errors, pagination, filtering, idempotency, rate limits, async events, and versioning so that the
> React frontend, a future mobile app, a future public API, internal automation, AI modules, and
> future omnichannel all build against one stable contract. Resource identifiers exposed by the API
> are always the **UUIDv7 `uuid`** from Doc 3 (never the internal `BIGINT id`). Timestamps are
> **ISO-8601 UTC** (`2026-07-15T09:30:00Z`). Every schema here maps to a Doc 3 table and a Doc 1
> requirement, and is expressible in **OpenAPI 3.1**.

---

## 1. Design goals & principles

| Principle | Applied as |
|---|---|
| **Resource-oriented REST** | Nouns as resources, HTTP verbs for actions, sub-resources for relationships. |
| **Predictable & uniform** | One error format, one pagination format, one filter grammar — everywhere. |
| **Stable for 10+ years** | `/api/v1` prefix; additive evolution; deprecation policy (§17); no breaking changes within a major version. |
| **Frontend- & SDK-friendly** | Consistent envelopes, cursor pagination, `Idempotency-Key`, fully OpenAPI-3.1-describable (§18). |
| **Secure by default** | Every route authenticated + permission-checked unless explicitly public (login, webhook, short-link redirect). |
| **Async-aware** | Long operations (imports, campaigns, exports) return `202 Accepted` + a job resource; real-time via SSE/WebSocket (§16). |
| **Meta-compliant** | Send endpoints enforce opt-in, 24-hour window, and messaging-limit rules server-side (Doc 1 §7). |

---

## 2. URL & resource conventions

- **Base:** every endpoint is under `/api/v1`. Collections are plural nouns: `/contacts`, `/campaigns`.
- **Item:** `/{resource}/{uuid}` (e.g., `GET /api/v1/contacts/018f...` ). UUIDv7 only.
- **Sub-resources:** `/campaigns/{uuid}/recipients`, `/conversations/{uuid}/messages`.
- **Actions that aren't pure CRUD** use a sub-path verb with `POST`:
  `POST /campaigns/{uuid}/pause`, `POST /campaigns/{uuid}/resume`, `POST /auth/logout`.
  Rationale: pause/resume/retry/cancel are state transitions, not resources; a `POST` action sub-path
  is clearer and safer than overloading `PATCH`.
- **Casing:** paths `kebab-or-plural-noun`; JSON fields `snake_case` (matches DB & Pydantic).
- **No trailing slashes.** Unknown routes → `404` problem.

---

## 3. Standard response envelopes

**Single resource** — returned directly (no wrapper), so it round-trips on `PUT`/`PATCH`:
```json
{
  "id": "018f7c3e-6a1b-7e2c-9d4a-1f2e3c4b5a6d",
  "type": "contact",
  "created_at": "2026-07-15T09:30:00Z",
  "updated_at": "2026-07-15T09:30:00Z",
  "...": "resource fields"
}
```

**Collection** — data array + a `page` object (cursor pagination, §6):
```json
{
  "data": [ { "id": "018f...", "...": "..." } ],
  "page": {
    "limit": 50,
    "has_more": true,
    "next_cursor": "eyJjcmVhdGVkX2F0IjoiMjAyNi0wNy0xNVQwOTozMDowMFoiLCJpZCI6MTIzfQ",
    "prev_cursor": null,
    "total_estimate": 10423
  }
}
```
> `total_estimate` is an **approximate** count (from table stats or a cached counter) — exact counts
> over 100M-row tables are intentionally avoided (performance). Endpoints where an exact count is cheap
> return `total` instead.

**Accepted (async)** — `202` for long jobs:
```json
{ "job": { "id": "018f...", "type": "import", "status": "queued", "poll_url": "/api/v1/jobs/018f..." } }
```

**No content** — `204` for successful deletes/logouts with no body.

---

## 4. Authentication & authorization

### 4.1 Mechanisms
| Mechanism | Header | Used by | Notes |
|---|---|---|---|
| **JWT access token** | `Authorization: Bearer <jwt>` | Frontend, mobile | Short-lived (30 min default), HS256, carries `sub`(user uuid), `jti`, `type=access`, permissions hash. |
| **Refresh token** | Sent to `/auth/refresh` in body (or httpOnly cookie option) | Frontend | Long-lived (14 d), rotated on use, server-side revocable (Doc 3 `refresh_tokens`). |
| **API key** | `Authorization: Bearer sk_live_...` or `X-API-Key` | Future public API, automation | Hashed at rest; scoped permissions; per-key rate limits. |

Bearer JWT is **not** cookie-based, so it is not CSRF-exploitable (Doc 1 NFR-SEC-01). If a cookie mode
is enabled for the browser app, it uses `SameSite=Strict` + a CSRF token header.

### 4.2 Authorization (RBAC)
- Every protected endpoint declares a **required permission** as `resource:action`
  (e.g., `contacts:read`, `campaigns:send`). These map to Doc 3 `permissions.code`.
- The Owner (`is_superuser`) bypasses checks. Missing permission → `403` (§5).
- Endpoints list their permission in each table below. Read actions use `:read`, mutations `:write`,
  privileged operations get dedicated permissions (`campaigns:send`, `users:manage`, `settings:manage`).

### 4.3 Permission catalog (seeded — excerpt)
`auth:*` (self), `users:read|write|manage`, `roles:read|write`, `contacts:read|write|import|export`,
`segments:read|write`, `templates:read|write|sync`, `media:read|write`, `campaigns:read|write|send|manage`,
`inbox:read|write|assign`, `messages:send`, `ai:use|manage`, `analytics:read`, `waba:read|manage`,
`webhooks:manage`, `settings:read|manage`, `audit:read`, `system:read|manage`, `apikeys:manage`.

---

## 5. Error model — RFC 7807 Problem Details

All errors use `application/problem+json` (Doc 1 API rules). Shape:

```json
{
  "type": "https://api.internal/errors/validation",
  "title": "Validation failed",
  "status": 422,
  "detail": "One or more fields are invalid.",
  "instance": "/api/v1/contacts",
  "code": "validation_error",
  "request_id": "018f7c3e-6a1b-7e2c-9d4a-1f2e3c4b5a6d",
  "errors": [
    { "field": "phone_e164", "code": "invalid_format", "message": "Must be E.164, e.g. +14155552671" }
  ]
}
```

### 5.1 Standard status codes & problem types
| Status | `type` slug | When |
|---|---|---|
| `400 Bad Request` | `/errors/bad-request` | Malformed JSON, bad cursor, unsupported filter. |
| `401 Unauthorized` | `/errors/unauthorized` | Missing/invalid/expired token. |
| `403 Forbidden` | `/errors/forbidden` | Authenticated but lacks permission; or IP-blocked. |
| `404 Not Found` | `/errors/not-found` | Resource absent or not visible to the caller. |
| `409 Conflict` | `/errors/conflict` | Duplicate (e.g., contact `wa_id`), version conflict (optimistic lock), state conflict (resume a completed campaign). |
| `410 Gone` | `/errors/gone` | Deprecated endpoint removed / expired export link. |
| `422 Unprocessable Entity` | `/errors/validation` | Field validation errors (with `errors[]`). |
| `429 Too Many Requests` | `/errors/rate-limit` | Rate limit exceeded (with `Retry-After`). |
| `500 Internal Server Error` | `/errors/server-error` | Unhandled error (correlate via `request_id`). |
| `503 Service Unavailable` | `/errors/unavailable` | Dependency down / graceful degradation (Doc 1 NFR-DR-08). |

Every endpoint can return `401` (if auth fails), `403` (permission/IP), `429` (rate limit), and `500`.
Those four are **implicit on all endpoints** and not repeated per-endpoint below; endpoint tables list
only the **notable** additional errors (e.g., `409` duplicate, `422` validation, `404`).

### 5.2 Optimistic concurrency
Mutating endpoints accept an optional `If-Match: "<row_version>"` header (or `row_version` in body).
A stale version → `409 Conflict` (`code: "version_conflict"`), preventing lost updates (Doc 3 §1.7).

---

## 6. Pagination — cursor-based (keyset)

Offset pagination is **not used** for large datasets (it degrades at depth and drifts under writes).
All collections use **opaque cursor** (keyset) pagination:

**Request:** `GET /contacts?limit=50&cursor=<opaque>&sort=-created_at`
- `limit` — 1–200 (default 50). `cursor` — opaque token from a prior `next_cursor`/`prev_cursor`.
- The cursor encodes the last row's sort keys `(created_at, id)` (base64url JSON), so paging is O(log n)
  at any depth and stable under concurrent inserts.

**Response:** the `page` object (§3) with `next_cursor`, `prev_cursor`, `has_more`, `total_estimate`.

Small, bounded collections (roles, permissions, a user's sessions, tags) may return the **full list**
without pagination; those are marked "unpaginated" in their tables.

---

## 7. Filtering, sorting, search

### 7.1 Filtering grammar
Filters are query params of the form `filter[field][op]=value` (repeatable, ANDed). Supported operators:

| Op | Meaning | Example |
|---|---|---|
| `eq` / `ne` | equals / not equals | `filter[status][eq]=open` |
| `contains` | substring | `filter[full_name][contains]=raj` |
| `starts` / `ends` | prefix / suffix | `filter[phone_e164][starts]=+1` |
| `gt` `gte` `lt` `lte` | comparisons | `filter[created_at][gte]=2026-07-01T00:00:00Z` |
| `between` | range (CSV) | `filter[created_at][between]=2026-07-01T00:00:00Z,2026-07-31T23:59:59Z` |
| `in` / `nin` | set membership (CSV) | `filter[opt_in_status][in]=opted_in,unknown` |
| `exists` | non-null | `filter[email][exists]=true` |
| `has_tag` | tag membership | `filter[tags][has_tag]=vip` |
| `attr` | custom attribute | `filter[attr.plan][eq]=gold` |
| `bool` | boolean | `filter[is_active][bool]=true` |

Complex AND/OR groups (contacts/segments) accept a JSON body on a dedicated
`POST /{resource}/search` endpoint (below) so deeply nested logic isn't crammed into query strings.

### 7.2 Sorting
`?sort=field` (asc) or `?sort=-field` (desc); multiple comma-separated (`?sort=-created_at,full_name`).
Only whitelisted, indexed fields are sortable per resource (prevents un-indexed scans).

### 7.3 Search
- **Per-resource quick search:** `?q=<text>` does a resource-appropriate search (e.g., contacts by
  name/phone/email). Backed by indexes (Doc 3 §13.3).
- **Global search:** `GET /search?q=...&types=contacts,messages,campaigns,templates,users` returns a
  unified, grouped result set (§21).

---

## 8. Idempotency

- **`Idempotency-Key: <uuid>`** header is **required** on side-effectful, non-idempotent `POST`
  operations that create or send: `campaigns:send`, `messages:send`, contact `import`, `export`,
  bulk operations. The server stores `key → (response, status)` for **24 hours**; a repeat with the same
  key returns the original response instead of acting twice (Doc 1 reliability; Doc 3 idempotency keys).
- `PUT` and `DELETE` are idempotent by definition. `PATCH` is made idempotent via `If-Match` version.
- Meta send idempotency is additionally enforced at the data layer (Doc 3 `campaign_recipients` unique
  key + `wamid`), so retries never double-send even across restarts.

---

## 9. Rate limiting

Limits are enforced per identity (user/API-key) and per IP; counters live in Redis (Doc 3 §2).
Every response carries: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`; `429` adds
`Retry-After`. Endpoints are tagged with a **rate class**:

| Class | Default limit | Applies to |
|---|---|---|
| `auth` | 10 / 5 min / IP | login, refresh, forgot/reset password (brute-force protection) |
| `read` | 600 / min / user | GET endpoints |
| `write` | 120 / min / user | POST/PUT/PATCH/DELETE mutations |
| `bulk` | 10 / min / user | imports, bulk update/delete, exports |
| `send` | bounded by number's messaging tier & MPS | campaign send, message send (Meta-limit-aware, not a fixed number) |
| `ai` | 60 / min / org | AI endpoints (also cost-guarded) |
| `webhook` | unlimited (public, signature-gated) | inbound Meta webhook |

Policies are configurable (Doc 3 `rate_limit_policies`). Each endpoint table names its class.

---

## 10. Common headers

| Header | Direction | Purpose |
|---|---|---|
| `Authorization` | req | Bearer JWT or API key |
| `Idempotency-Key` | req | Idempotent create/send (§8) |
| `If-Match` | req | Optimistic concurrency (§5.2) |
| `X-Request-Id` | req/resp | Client-supplied or server-generated correlation id (appears in logs & problems) |
| `X-RateLimit-*` / `Retry-After` | resp | Rate-limit signaling (§9) |
| `X-Hub-Signature-256` | req | Meta webhook signature (verified, §15) |
| `ETag` / `Last-Modified` | resp | Cacheable GETs where useful |

---

## 11. Authentication & session endpoints

**Route rationale:** all auth lives under `/auth` (not `/users`) because these are *session/credential*
operations, not user-resource CRUD. Self-service endpoints require only the caller's own identity.

| Method | Path | Purpose | Auth | Permission | Rate class | Idempotent | Notable errors |
|---|---|---|---|---|---|---|---|
| POST | `/auth/login` | Exchange email+password for tokens | Public | — | `auth` | no | 401, 422, 423(locked) |
| POST | `/auth/refresh` | Rotate refresh → new access+refresh | Refresh token | — | `auth` | no | 401 (revoked/reused) |
| POST | `/auth/logout` | Revoke current refresh token/session | Bearer | `auth:self` | `write` | yes | 401 |
| POST | `/auth/logout-all` | Revoke **all** sessions/tokens for the user | Bearer | `auth:self` | `write` | yes | 401 |
| POST | `/auth/forgot-password` | Email a reset token | Public | — | `auth` | yes | 202 always (no user enumeration) |
| POST | `/auth/reset-password` | Set new password via reset token | Public | — | `auth` | no | 400(expired), 422 |
| POST | `/auth/change-password` | Change own password (old→new) | Bearer | `auth:self` | `write` | no | 401, 422 |
| GET | `/auth/me` | Current user + effective permissions | Bearer | `auth:self` | `read` | — | 401 |
| GET | `/auth/sessions` | List own active sessions/devices | Bearer | `auth:self` | `read` | — | 401 |
| DELETE | `/auth/sessions/{uuid}` | Revoke one session | Bearer | `auth:self` | `write` | yes | 404 |
| POST | `/auth/mfa/setup` | Begin TOTP enrollment (returns secret/QR) | Bearer | `auth:self` | `write` | no | 409(already on) |
| POST | `/auth/mfa/verify` | Confirm TOTP code, enable MFA | Bearer | `auth:self` | `write` | no | 422 |
| POST | `/auth/mfa/disable` | Disable MFA (requires password/code) | Bearer | `auth:self` | `write` | no | 422 |

**`POST /auth/login` — sample**
```http
POST /api/v1/auth/login
Content-Type: application/json

{ "email": "owner@company.com", "password": "••••••••", "mfa_code": "123456" }
```
```json
200 OK
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 1800,
  "refresh_token": "eyJhbGciOi...",
  "user": { "id": "018f...", "full_name": "Owner", "email": "owner@company.com", "is_superuser": true }
}
```
- **Validation:** `email` RFC-5322 + normalized; `password` present; `mfa_code` required only if MFA on.
- **Security:** Argon2id verify; increments `failed_logins`, locks after threshold → `423 Locked`;
  never reveals whether email exists; login writes an `audit_logs` row.
- **`/auth/refresh`** implements **rotation with reuse detection** — presenting a already-rotated
  refresh token revokes the whole token family (Doc 3 `refresh_tokens.parent_id`) and returns `401`.

**`GET /auth/me` — sample response**
```json
{
  "id": "018f...", "email": "owner@company.com", "full_name": "Owner",
  "is_superuser": true, "roles": ["owner"],
  "permissions": ["contacts:read","contacts:write","campaigns:send", "..."],
  "timezone": "Asia/Kolkata", "locale": "en", "mfa_enabled": true
}
```
The frontend caches `permissions` to drive UI gating; the server still enforces on every call.

---

## 12. User, Role & Permission management

**Route rationale:** `/users`, `/roles`, `/permissions` are administrative resources under RBAC; user
*preferences* and *activity* are sub-resources of a user.

### 12.1 Users
| Method | Path | Purpose | Permission | Rate class | Notable errors |
|---|---|---|---|---|---|
| GET | `/users` | List users (paginated, filter/sort/search `q`) | `users:read` | `read` | — |
| POST | `/users` | Create user (assign roles) | `users:manage` | `write` | 409(email), 422 |
| GET | `/users/{uuid}` | Get one user | `users:read` | `read` | 404 |
| PATCH | `/users/{uuid}` | Update user (name/roles/active) | `users:manage` | `write` | 404, 409(version) |
| DELETE | `/users/{uuid}` | Soft-delete (deactivate) user | `users:manage` | `write` | 404, 409(self) |
| POST | `/users/{uuid}/activate` | Reactivate | `users:manage` | `write` | 404 |
| POST | `/users/{uuid}/deactivate` | Deactivate (revokes sessions) | `users:manage` | `write` | 404 |
| POST | `/users/{uuid}/reset-password` | Admin-trigger password reset email | `users:manage` | `write` | 404 |
| GET | `/users/{uuid}/activity` | User activity feed (from `activity_logs`) | `users:read` | `read` | 404 |
| GET | `/users/me/preferences` | Get own preferences | `auth:self` | `read` | — |
| PUT | `/users/me/preferences` | Update own preferences (theme, shortcuts, tz) | `auth:self` | `write` | 422 |

**Filtering:** `filter[is_active][bool]`, `filter[role][eq]=agent`, `q` over name/email.
**Sort:** `created_at`, `full_name`, `last_login_at`.

### 12.2 Roles & permissions
| Method | Path | Purpose | Permission | Rate class | Notes |
|---|---|---|---|---|---|
| GET | `/roles` | List roles (unpaginated) | `roles:read` | `read` | includes permission codes |
| POST | `/roles` | Create custom role | `roles:write` | `write` | 409(name) |
| GET | `/roles/{uuid}` | Get role + permissions | `roles:read` | `read` | 404 |
| PATCH | `/roles/{uuid}` | Rename / edit role | `roles:write` | `write` | 403(system role), 404 |
| PUT | `/roles/{uuid}/permissions` | Replace role's permission set | `roles:write` | `write` | 422(unknown code) |
| DELETE | `/roles/{uuid}` | Delete role (if unused/non-system) | `roles:write` | `write` | 409(in use), 403 |
| GET | `/permissions` | List the permission catalog (unpaginated) | `roles:read` | `read` | grouped by resource |

**Design notes:** roles are fully custom (Doc 1 FR-AUTH-05/08); `is_system` roles cannot be deleted or
have their code changed. Assigning a permission validates it against the seeded catalog → `422` if
unknown, so the permission surface stays consistent and OpenAPI-enumerable. Changing a user's roles
invalidates their cached permission set (a new token/refresh reflects it).

---

## 13. WABA, Phone Numbers & Meta account health

**Route rationale:** WhatsApp infrastructure is nested to mirror Meta's model — an **organization**
owns **WABAs**, a WABA owns **phone numbers**. Number *health* (quality/limits) is a sub-resource read.

### 13.1 Organizations
| Method | Path | Purpose | Permission | Rate class | Notes |
|---|---|---|---|---|---|
| GET | `/organization` | Get the current org profile | `settings:read` | `read` | single-tenant: the caller's org |
| PATCH | `/organization` | Update org (name, tz, locale, settings) | `settings:manage` | `write` | 422 |

### 13.2 WhatsApp Business Accounts
| Method | Path | Purpose | Permission | Rate class | Notable errors |
|---|---|---|---|---|---|
| GET | `/waba` | List connected WABAs | `waba:read` | `read` | — |
| POST | `/waba` | Connect a WABA (id + system-user token) | `waba:manage` | `write` | 409(dup), 422, 502(meta) |
| GET | `/waba/{uuid}` | Get WABA (status, currency, tz) | `waba:read` | `read` | 404 |
| PATCH | `/waba/{uuid}` | Update WABA (rotate token, name) | `waba:manage` | `write` | 404 |
| DELETE | `/waba/{uuid}` | Disconnect WABA | `waba:manage` | `write` | 409(has numbers) |
| POST | `/waba/{uuid}/sync` | Pull numbers+templates from Meta | `waba:manage` | `bulk` | 202(job), 502 |

**Security:** the system-user **token is write-only** — it is accepted on create/update, stored
encrypted (Doc 3 `access_token_enc`), and **never returned** in any response (a `token_set: true`
boolean is returned instead). This is called out because it's the single most sensitive field.

### 13.3 Phone Numbers & health
| Method | Path | Purpose | Permission | Rate class | Notable errors |
|---|---|---|---|---|---|
| GET | `/phone-numbers` | List numbers (all WABAs) | `waba:read` | `read` | filter by `waba`, `status`, `quality_rating` |
| GET | `/phone-numbers/{uuid}` | Get number detail | `waba:read` | `read` | 404 |
| PATCH | `/phone-numbers/{uuid}` | Update (default flag, mps_limit, name) | `waba:manage` | `write` | 404 |
| GET | `/phone-numbers/{uuid}/health` | Quality rating, messaging tier/limit, status | `waba:read` | `read` | 404 |
| POST | `/phone-numbers/{uuid}/refresh` | Re-pull health/limits from Meta | `waba:manage` | `write` | 502 |
| GET | `/waba/{uuid}/webhook` | Webhook config + verification status | `webhooks:manage` | `read` | 404 |
| POST | `/waba/{uuid}/webhook/verify` | Trigger/confirm webhook verification | `webhooks:manage` | `write` | 422, 502 |

**`GET /phone-numbers/{uuid}/health` — sample**
```json
{
  "id":"018f...","display_number":"+14155552671","verified_name":"Company",
  "quality_rating":"GREEN","messaging_tier":"TIER_100K","mps_limit":80,
  "status":"connected","last_synced_at":"2026-07-15T08:00:00Z",
  "limits":{"unique_customers_24h_cap":100000,"used_24h":42310}
}
```
- **Why it exists:** the campaign engine reads `messaging_tier`/`mps_limit` to auto-throttle sends
  (Doc 1 FR-WA-13/CMP-06); the UI shows quality health so operators can react to a `RED` drop.
- **Performance:** health is **cached** (Redis) and refreshed on webhook signals + periodic sync, so the
  UI never blocks on a Meta round-trip.
- **Extensibility:** `phone_numbers.channel_type` means this surface generalizes to other channels
  later without new routes.

---

## 14. Contact management

### 14.1 Contacts CRUD
| Method | Path | Purpose | Permission | Rate class | Notable errors |
|---|---|---|---|---|---|
| GET | `/contacts` | List/paginate/filter/sort/search contacts | `contacts:read` | `read` | — |
| POST | `/contacts` | Create a contact | `contacts:write` | `write` | 409(dup wa_id), 422 |
| GET | `/contacts/{uuid}` | Get contact (with tags + attributes) | `contacts:read` | `read` | 404 |
| PATCH | `/contacts/{uuid}` | Update contact | `contacts:write` | `write` | 404, 409(version) |
| DELETE | `/contacts/{uuid}` | Soft-delete contact | `contacts:write` | `write` | 404 |
| GET | `/contacts/{uuid}/timeline` | Activity timeline (`contact_events`) | `contacts:read` | `read` | 404 |
| POST | `/contacts/{uuid}/tags` | Add tags to contact | `contacts:write` | `write` | 404, 422 |
| DELETE | `/contacts/{uuid}/tags/{tag_uuid}` | Remove a tag | `contacts:write` | `write` | 404 |
| PUT | `/contacts/{uuid}/attributes` | Set custom attribute values | `contacts:write` | `write` | 422(type) |
| POST | `/contacts/search` | Advanced AND/OR search (JSON body) | `contacts:read` | `read` | 422(bad rule) |
| POST | `/contacts/import` | Start CSV/Excel import (async) | `contacts:import` | `bulk` | 202(job), 422 |
| GET | `/contacts/import/{job_uuid}` | Import progress + error report link | `contacts:import` | `read` | 404 |
| POST | `/contacts/export` | Start export (CSV/Excel/JSON, async) | `contacts:export` | `bulk` | 202(job) |
| POST | `/contacts/bulk-update` | Bulk edit (tags/attrs) over selection/filter | `contacts:write` | `bulk` | 202(job), 422 |
| POST | `/contacts/bulk-delete` | Bulk soft-delete over selection/filter | `contacts:write` | `bulk` | 202(job) |
| POST | `/contacts/deduplicate` | Run dedup scan (report or merge) | `contacts:write` | `bulk` | 202(job) |

**Contact resource — schema**
```json
{
  "id":"018f...","type":"contact",
  "wa_id":"14155552671","phone_e164":"+14155552671","country_code":"US",
  "full_name":"Priya R","email":"priya@x.com","locale":"en",
  "opt_in_status":"opted_in","opt_in_at":"2026-06-01T10:00:00Z","opt_out_at":null,
  "is_active_on_wa":true,"last_inbound_at":"2026-07-14T18:20:00Z",
  "tags":[{"id":"018f...","name":"vip","color":"#22c55e"}],
  "attributes":{"plan":"gold","ltv":5400.0},
  "source":"import","created_at":"...","updated_at":"...","row_version":3
}
```

**`POST /contacts/import` — sample (async)**
```http
POST /api/v1/contacts/import
Idempotency-Key: 018f7c3e-...
Content-Type: application/json

{ "upload_id":"018f...", "format":"csv",
  "mapping": { "Phone":"phone_e164", "Name":"full_name", "Plan":"attr.plan" },
  "dedup_strategy":"merge", "default_tags":["import-jul"] }
```
```json
202 Accepted
{ "job": { "id":"018f...", "type":"import", "status":"queued", "poll_url":"/api/v1/contacts/import/018f..." } }
```
- **Why async:** imports of up to millions of rows must not block a request; throughput target ≥10k/min
  (Doc 1 NFR-PERF-08). The file is uploaded first (see Media §16), then referenced by `upload_id`.
- **Validation:** per-row validation produces a downloadable error report; valid rows commit in batches.
- **Dedup:** `skip|merge|overwrite` on normalized `wa_id` (Doc 1 FR-CON-06).

**`POST /contacts/search` — advanced filter body**
```json
{ "match":"all",
  "rules":[
    { "field":"opt_in_status","op":"eq","value":"opted_in" },
    { "any":[
      { "field":"attr.plan","op":"in","value":["gold","platinum"] },
      { "field":"tags","op":"has_tag","value":"vip" }
    ]}
  ],
  "sort":"-created_at","limit":50 }
```
Returns the standard paginated collection. This mirrors the segment rule model (Doc 3 `segment_rules`)
so a saved search becomes a segment with one call.

### 14.2 Tags
| Method | Path | Purpose | Permission | Rate class |
|---|---|---|---|---|
| GET | `/tags` | List tags (with usage counts) | `contacts:read` | `read` |
| POST | `/tags` | Create tag | `contacts:write` | `write` |
| PATCH | `/tags/{uuid}` | Rename/recolor | `contacts:write` | `write` |
| DELETE | `/tags/{uuid}` | Delete tag (detaches from contacts) | `contacts:write` | `write` |

### 14.3 Segments
| Method | Path | Purpose | Permission | Rate class | Notes |
|---|---|---|---|---|---|
| GET | `/segments` | List segments (+cached counts) | `segments:read` | `read` | — |
| POST | `/segments` | Create segment (rules) | `segments:write` | `write` | 422(rule) |
| GET | `/segments/{uuid}` | Get segment + rules | `segments:read` | `read` | 404 |
| PATCH | `/segments/{uuid}` | Update rules/name | `segments:write` | `write` | 404 |
| DELETE | `/segments/{uuid}` | Delete segment | `segments:write` | `write` | 404 |
| GET | `/segments/{uuid}/contacts` | Preview matching contacts (paginated) | `segments:read` | `read` | 404 |
| POST | `/segments/{uuid}/refresh` | Recompute cached count | `segments:read` | `write` | 404 |

### 14.4 Custom attribute definitions
| Method | Path | Purpose | Permission | Rate class |
|---|---|---|---|---|
| GET | `/custom-attributes` | List attribute definitions | `contacts:read` | `read` |
| POST | `/custom-attributes` | Define attribute (typed) | `contacts:write` | `write` |
| PATCH | `/custom-attributes/{uuid}` | Update label / indexing / enum values | `contacts:write` | `write` |
| DELETE | `/custom-attributes/{uuid}` | Remove definition (and values) | `contacts:write` | `write` |

**Design rationale (contacts domain):** the split of *quick* (`?q`, `filter[...]`) vs *advanced*
(`POST /search` with nested AND/OR) keeps simple lists cacheable and URL-shareable while allowing
arbitrarily complex audience logic in a body. All list/preview endpoints are cursor-paginated over
indexed columns (Doc 3 §13) to hold <500ms at 1M contacts (NFR-PERF-10). Bulk ops and imports/exports
are async jobs (202 + poll) so the UI stays responsive and the work is retriable.

---

## 15. Template management

**Route rationale:** templates belong to a WABA (Meta's rule); the API keeps them as a top-level
`/templates` resource filterable by `waba`, with Meta sync as an action.

| Method | Path | Purpose | Permission | Rate class | Notable errors |
|---|---|---|---|---|---|
| GET | `/templates` | List templates (filter waba/status/category/language, `q`) | `templates:read` | `read` | — |
| POST | `/templates` | Create + submit template to Meta | `templates:write` | `write` | 202/201, 422, 502 |
| GET | `/templates/{uuid}` | Get template (components, status) | `templates:read` | `read` | 404 |
| PATCH | `/templates/{uuid}` | Edit draft (re-submit if needed) | `templates:write` | `write` | 409(approved), 422 |
| DELETE | `/templates/{uuid}` | Delete template (local + Meta) | `templates:write` | `write` | 404, 502 |
| POST | `/templates/sync` | Sync all templates + statuses from Meta | `templates:sync` | `bulk` | 202(job) |
| GET | `/templates/{uuid}/preview` | Render with sample variables | `templates:read` | `read` | 404 |
| GET | `/templates/{uuid}/versions` | Version history | `templates:read` | `read` | 404 |

**Template resource — schema (excerpt)**
```json
{
  "id":"018f...","name":"order_update","language":"en_US","category":"utility",
  "status":"approved","quality_score":"GREEN","waba_id":"018f...",
  "components":[
    {"type":"header","format":"text","text":"Order {{1}}"},
    {"type":"body","text":"Hi {{1}}, your order {{2}} is {{3}}."},
    {"type":"buttons","buttons":[{"type":"url","text":"Track","url":"https://..."}]}
  ],
  "variable_count":3,"has_media_header":false,"rejection_reason":null,
  "created_at":"...","updated_at":"..."
}
```
- **Approval status** (`draft/pending/approved/rejected/paused/disabled`) and `rejection_reason` are
  surfaced so operators know exactly why a template can't be used (Doc 1 FR-TPL-03).
- **Validation:** category correctness, variable placeholders, button limits, and media-header rules are
  validated **before** submission to Meta to cut rejection loops.
- **Performance:** listing filters on indexed `(org,status)`/`(org,category)` (Doc 3 §7.1).

---

## 16. Media

**Route rationale:** media is a first-class resource because assets are reused across templates,
campaigns, and inbox messages. Bytes go to object storage; the API deals in metadata + signed URLs.

| Method | Path | Purpose | Permission | Rate class | Notable errors |
|---|---|---|---|---|---|
| POST | `/media/upload` | Upload a file (multipart) → asset metadata | `media:write` | `write` | 413(too large), 415(type), 422 |
| GET | `/media` | List media library (filter type, `q`) | `media:read` | `read` | — |
| GET | `/media/{uuid}` | Get asset metadata | `media:read` | `read` | 404 |
| GET | `/media/{uuid}/content` | Signed, expiring download/preview URL | `media:read` | `read` | 404, 410(expired) |
| DELETE | `/media/{uuid}` | Delete asset (if unused) | `media:write` | `write` | 409(in use) |
| POST | `/media/{uuid}/refresh-meta-id` | Re-upload to Meta, refresh cached media id | `media:write` | `write` | 502 |

**`POST /media/upload` — response**
```json
201 Created
{
  "id":"018f...","media_type":"image","mime_type":"image/jpeg",
  "byte_size":184320,"sha256":"…","width":1280,"height":720,
  "storage_backend":"s3","usage_count":0,
  "content_url":"/api/v1/media/018f.../content",
  "meta_media_id":null,"created_at":"..."
}
```
- **Dedup:** on upload the server computes SHA-256; an identical asset in the org returns the **existing**
  record (Doc 1 FR-MED-05) — no duplicate storage.
- **Security:** `content_url` issues a **signed, expiring** URL; raw object-storage keys are never
  exposed; type/size validated against Cloud API limits (FR-MED-01..04, FR-MED-09).
- **Meta cache:** `meta_media_id` is cached and transparently refreshed on expiry (FR-MED-07) so sends
  don't re-upload every time.
- **Extensibility:** `storage_backend` lets local↔S3 switch without API change (FR-MED-06).

---

## 17. Campaign management

**Route rationale:** a campaign is a resource; its lifecycle transitions (schedule/pause/resume/cancel/
retry) are `POST` action sub-paths (not `PATCH`) because they trigger side effects on the queue and must
be idempotent and permission-gated (`campaigns:send`/`campaigns:manage`). Analytics & recipients are
read sub-resources.

| Method | Path | Purpose | Permission | Rate class | Idem. | Notable errors |
|---|---|---|---|---|---|---|
| GET | `/campaigns` | List campaigns (filter status, `q`) | `campaigns:read` | `read` | — | — |
| POST | `/campaigns` | Create draft campaign | `campaigns:write` | `write` | key | 422 |
| GET | `/campaigns/{uuid}` | Get campaign (+ counters) | `campaigns:read` | `read` | — | 404 |
| PATCH | `/campaigns/{uuid}` | Edit draft (audience/template/vars) | `campaigns:write` | `write` | — | 409(not draft), 422 |
| DELETE | `/campaigns/{uuid}` | Delete draft / soft-delete | `campaigns:write` | `write` | — | 409(running) |
| POST | `/campaigns/{uuid}/preview` | Resolve audience size + sample renders | `campaigns:read` | `read` | — | 422 |
| POST | `/campaigns/{uuid}/estimate-cost` | Cost estimate from rate card | `campaigns:read` | `read` | — | 422(`rate_card_not_configured`), 404 |
| POST | `/campaigns/{uuid}/schedule` | Schedule (one-time/recurring) | `campaigns:send` | `write` | key | 422(cron/time) |
| POST | `/campaigns/{uuid}/send` | Send now (enqueue) | `campaigns:send` | `send` | **key req** | 409(state), 422(opt-in/limit) |
| POST | `/campaigns/{uuid}/pause` | Pause a running campaign | `campaigns:manage` | `write` | key | 409(not running) |
| POST | `/campaigns/{uuid}/resume` | Resume a paused campaign | `campaigns:manage` | `write` | key | 409(not paused) |
| POST | `/campaigns/{uuid}/cancel` | Cancel (stop pending sends) | `campaigns:manage` | `write` | key | 409(completed) |
| POST | `/campaigns/{uuid}/retry` | Retry failed recipients (smart retry) | `campaigns:send` | `write` | key | 409, 422 |
| POST | `/campaigns/{uuid}/duplicate` | Clone as a new draft | `campaigns:write` | `write` | — | 404 |
| GET | `/campaigns/{uuid}/recipients` | Per-recipient status (paginated, filter status) | `campaigns:read` | `read` | — | 404 |
| GET | `/campaigns/{uuid}/analytics` | Campaign analytics (rates, timeline, cost) | `analytics:read` | `read` | — | 404 |

**Campaign resource — schema (excerpt)**
```json
{
  "id":"018f...","name":"July Promo","status":"running",
  "phone_number":{"id":"018f...","display_number":"+14155552671"},
  "template":{"id":"018f...","name":"july_promo","language":"en_US","category":"marketing"},
  "audience":{"type":"segment","refs":["018f...seg"]},
  "variable_map":{"1":"contact.first_name","2":"attr.coupon"},
  "counters":{"total":250000,"queued":120000,"sent":128000,"delivered":119400,
              "read":54300,"failed":2600,"replied":8100},
  "cost":{"estimated":2350.00,"actual":1204.55,"currency":"USD"},
  "send_rate_mps":40,"started_at":"...","completed_at":null,
  "created_at":"...","updated_at":"..."
}
```

**`POST /campaigns/{uuid}/estimate-cost` — contract**
> **Amendment 2026-07-17 (v1.1).** Added to unblock Phase 6 Step 5. Previously specified by sample
> response only. Scope is **pre-send estimation**; actual cost and billing remain out of scope.

**Request:** no body. The estimate is derived from the campaign's **materialized roster** (Doc 3
§8.3) and its template — never from a fresh audience query, so the quote prices what would actually
be sent. `campaigns:read`, rate class `read`, no `Idempotency-Key` (naturally idempotent).

**`200` — sample response**
```json
{
  "recipients": 250000,
  "breakdown": [
    { "country":"IN","category":"marketing","count":180000,"unit":"0.009400","subtotal":"1692.000000" },
    { "country":"US","category":"marketing","count":69997,"unit":"0.025000","subtotal":"1749.925000" }
  ],
  "unresolved": { "count": 3, "reason":"country_unknown" },
  "estimated_total": "3441.9250", "currency":"USD",
  "notes":["3 recipients have no country and are excluded from the total."]
}
```
> Monetary fields are **JSON strings at fixed scale**, not numbers. A JSON number cannot carry scale
> (`0.009400` and `0.0094` are the same token) and most clients parse it into a binary float, which
> is the one representation money must never pass through. Strings are lossless in every parser.
> *(v1.0 illustrated these as numbers; the v1.1 amendment makes the wire format explicit.)*

| Field | Meaning |
|---|---|
| `recipients` | The whole roster. **Invariant:** `recipients == Σ breakdown[].count + unresolved.count`. |
| `breakdown[]` | One row per `(country, category)` actually priced. `unit` is the rate in force **at estimate time**; `subtotal = unit × count`, exact (Doc 3 §8.5.3). |
| `unresolved` | Recipients whose `contacts.country_code` is `NULL` (Doc 3 §8.5.4). **Counted, priced at nothing, excluded from `estimated_total`.** Present with `count: 0` when all resolve. |
| `estimated_total` | Σ of subtotals, rounded **once** to 4 dp, ROUND_HALF_UP. Covers **resolved recipients only**. |
| `currency` | The rate card's single currency (Doc 3 §8.5.3). No FX; never mixed. |
| `notes[]` | **Advisory, human-readable, non-contractual.** Clients **MUST NOT** parse them; machine outcomes are `unresolved` and the error codes below. |

Money is decimal server-side and serialized as **fixed-scale JSON strings** (`unit`/`subtotal` 6 dp,
matching `rate_cards.unit_price`; `estimated_total` 4 dp, matching `campaigns.estimated_cost`).
Clients must parse them as decimal, never as float.

**Side effect:** on success the endpoint persists `campaigns.estimated_cost` and
`campaigns.cost_currency` — a derived cache of the campaign's own data, which is why it stays on
`campaigns:read` rather than becoming a write-permission action. It populates **nothing else**:
`campaigns.actual_cost` and every `messages.cost_*` / `pricing_model` / `is_billable` field are out
of scope (Doc 3 §8.5.5).

**Errors**

| Code | HTTP | When |
|---|---|---|
| `rate_card_not_configured` | `422` | **No rate in force** for one or more required `(country, category)` pairs at estimate time — including a wholly empty card, which is the platform's shipped state (Doc 3 §8.5.1). The response `detail` names the missing pairs. **No partial estimate is returned:** a total missing India's 180k would understate the headline number while looking authoritative. |
| — | `404` | Campaign not found / not in this organization. |

An **unresolved country is not an error** — the card is fine, the contact data is incomplete, and the
count is reported. A **missing rate** is a misconfiguration the operator must fix before any total
can be trusted.

- **Why it exists:** exact pre-send cost is our headline differentiator (Doc 1 FR-CAM-11) — computed from
  Meta's real rate card by contact country + template category. No reseller markup.
- **Rate card:** global, operator-managed, effective-dated, **ships empty** (Doc 3 §8.5). The platform
  bundles no rates: Doc 12 §53 places Meta's pricing outside the frozen set, so the codebase must not
  restate it. Until an operator populates the card, this endpoint answers `rate_card_not_configured`.
- **Category domain:** a campaign always sends a **template**, so the category is one of
  `marketing/utility/authentication` (`ck_tpl_category`, Doc 3 §7.1). The `service` category that
  `messages.category` also permits is **unreachable** from an estimate, and free-tier/service-conversation
  semantics are undefined and out of scope (Doc 3 §8.5.5) — an earlier sample note here implied
  otherwise and has been corrected.
- **`send` guardrails:** the endpoint re-validates **opt-in** of every recipient, **template approval**,
  and the number's **messaging limit** before enqueuing; violations → `422` with a machine `code`
  (`recipients_not_opted_in`, `template_not_approved`, `messaging_limit_exceeded`). Requires an
  `Idempotency-Key` so a double-click never double-sends.
- **Pause/Resume/Cancel/Retry** operate on the durable `campaign_recipients` ledger + `campaign_batches`
  checkpoints (Doc 3 §8.3), so they are crash-safe and never duplicate sends (FR-CAM-06/08/09).
- **Performance:** counters come from the denormalized `campaigns` row (O(1)); `/recipients` is
  cursor-paginated over a partitioned table filtered by `(campaign_id,status)`.

### 17.1 Rate-card administration — the update mechanism (FR-CAM-11)
> **Amendment 2026-07-17 (v1.1).** The write path required by "operator-managed" (Doc 3 §8.5.1).
> Estimation reads this card; without a write path the card could never leave its shipped-empty
> state. Scope is confined to authoring rates — it is not billing, invoicing or finance reporting.
>
> **Specified for future administration; NOT implemented in Phase 6 Step 5.** Step 5 delivers the
> read path only (`estimate-cost`). These routes define the contract the administration surface will
> honour when it is built; until then the card is populated out-of-band.

| Method | Path | Purpose | Permission | Rate class | Idem. | Notable errors |
|---|---|---|---|---|---|---|
| GET | `/rate-cards` | List rates (filter `country`, `category`, `at`) | Elevated administrative authority | `read` | — | — |
| POST | `/rate-cards` | Author a rate (supersedes the row in force) | Elevated administrative authority | `write` | key | 422, 409 |

**Platform-scoped, not tenant-scoped.** `rate_cards` is **global** (no `organization_id`, Doc 3
§8.5.1) while ordinary roles are org-scoped — so a tenant-level settings permission alone **MUST NOT**
authorize a write, or one tenant's operator would silently reprice every other tenant. These routes
therefore **require elevated administrative authority**. Reads are likewise platform-scoped: the card
is not tenant data.

The **concrete RBAC mapping is deliberately left to the authorization model** and is not frozen here.
This section fixes the *requirement* (platform-level authority, never tenant-level); which permission,
role or principal satisfies it is the authorization model's decision.

**Supersede, never mutate (versioning).** `POST /rate-cards` **appends** an effective-dated row; it
never edits a rate in place, and there is no `PATCH`/`DELETE`. Authoring a rate for
`(country, category)` with an `effective_from` closes the currently-open row by setting its
`effective_to` to the new `effective_from`. Past estimates stay explainable because the rate they
used still exists.

- **Request:** `{ "country_code":"IN", "category":"marketing", "unit_price":"0.0094",
  "currency":"USD", "effective_from":"2026-08-01T00:00:00Z" }`
- `422` — unknown category (outside `marketing/utility/authentication`), negative `unit_price`,
  malformed `country_code`, or a `currency` that disagrees with the card's existing single currency
  (`rate_card_currency_conflict`, Doc 3 §8.5.3).
- `409` — a row already exists for that exact `(country_code, category, effective_from)`
  (`uq_ratecard_slot`).
- **Backdating** an `effective_from` earlier than an existing row is rejected `422`: it would rewrite
  what a past estimate meant.

**Out of scope for this surface:** bulk import, rate approval workflow, per-tenant overrides, markup,
FX, and any billing/finance reporting (Doc 3 §8.5.5).

---

## 18. Messaging & Inbox

**Route rationale:** the **inbox** is organized around `/conversations` (the thread), with `/messages`
as a sub-resource. A separate `/messages/send` composes outbound sends. This mirrors how agents work
(open a conversation → read history → reply) and how the send pipeline works (compose → enqueue).

### 18.1 Conversations (inbox)
| Method | Path | Purpose | Permission | Rate class | Notes |
|---|---|---|---|---|---|
| GET | `/conversations` | Inbox list (filter status/assignee/number, `q`) | `inbox:read` | `read` | cursor-paginated by `last_message_at` |
| GET | `/conversations/{uuid}` | Conversation detail (+ window state) | `inbox:read` | `read` | 404 |
| GET | `/conversations/{uuid}/messages` | Message history (paginated) | `inbox:read` | `read` | 404 |
| POST | `/conversations/{uuid}/assign` | Assign/reassign to a user | `inbox:assign` | `write` | 404, 422 |
| POST | `/conversations/{uuid}/status` | Set open/pending/resolved/snoozed | `inbox:write` | `write` | 404 |
| POST | `/conversations/{uuid}/read` | Mark read (reset unread) | `inbox:write` | `write` | 404 |
| GET | `/conversations/{uuid}/notes` | List internal notes | `inbox:read` | `read` | 404 |
| POST | `/conversations/{uuid}/notes` | Add internal note (staff-only) | `inbox:write` | `write` | 404 |
| DELETE | `/conversations/{uuid}/notes/{note_uuid}` | Delete note | `inbox:write` | `write` | 404 |
| POST | `/conversations/{uuid}/tags` | Add existing tag(s) to a conversation | `inbox:write` | `write` | 404, 422 |
| DELETE | `/conversations/{uuid}/tags/{tag_uuid}` | Remove a tag from a conversation | `inbox:write` | `write` | 404 |

**Conversation tags (Phase 7 — FR-INB-07 · Doc 03 §9.7).**
> **Amendment 2026-07-18 (v1.3).** Conversation-level classification, reusing the org `tags` taxonomy
> (§14.2). Distinct from contact tags (§14.1): this path never reads or mutates `contact_tags`, and it
> does not create tags.

- **Add** — `POST /conversations/{uuid}/tags`, `inbox:write`. Body `{ "tag_ids": ["<tag-uuid>", …] }`
  — 1–50 tag uuids that **already exist** in the caller's org (duplicates in the list are ignored).
  Applies each tag to the thread and is **idempotent**: a tag already present is a no-op, never a
  `409`. Returns **`200`** with the thread's full tag set — `{ "data": [ {"id","name","color"}, … ] }`.
  Errors: **`404`** (conversation not in the caller's org); **`422`** (empty or >50 list, malformed
  uuid, or any tag uuid that is unknown, soft-deleted, or belongs to another org — a cross-org tag is
  never applied). Creating new tags is **not** part of this path; tags are authored via `POST /tags`
  (§14.2, `contacts:write`).
- **Remove** — `DELETE /conversations/{uuid}/tags/{tag_uuid}`, `inbox:write`. Detaches the tag
  (hard-deletes the join row — no soft delete). **`204`** on success; **`404`** if the conversation or
  the specific association does not exist.
- **Attribution / audit** — the join records `tagged_by` / `tagged_at`; tag add/remove is **not**
  written to the audit log (low-stakes classification — audit only where a spec explicitly requires it).
- **In read responses** — both `GET /conversations` (every list row) and `GET /conversations/{uuid}`
  include a `tags` array `[ {"id","name","color"} ]` (empty `[]` when untagged). This is the frozen
  source for the list row's tag chips (Doc 05 B7) and backs the `tag` filter below. *(This extends the
  §18.1 read responses shipped in Phase 7 Step 2 with one additive field.)*

**`tag` filter on `GET /conversations`.** Adds a single filter to the frozen set
(status / assignee / number / `q`):
- **Param** — `tag=<tag-uuid>` — a single tag uuid (the "by-tag" folder, Doc 05 B7).
- **Matching** — a conversation matches iff it has an association to that tag in `conversation_tags`.
- **Multiple tags** — the filter is **single-valued**; supplying more than one `tag` value is a **`400`**.
  Multi-tag AND/OR filtering is **deferred** (not part of this amendment).
- **Empty / unknown** — a **malformed** uuid → **`400`** (as with the other filters); a **well-formed**
  uuid that is unknown, from another org, or simply matches nothing → a normal **empty page** (`200`,
  `data: []`), exactly as the assignee/number filters behave (§18.1, Step 2).

**Out of scope of this amendment (Conversation Tags only).** AI tagging & auto-tagging (`/ai/auto-tag`
stays suggestion-only — §19), rules engine, workflow automation, routing (FR-INB-09), SLA timers
(FR-INB-10), analytics/reports, bulk actions, and any change to the contact tag model (§6.2 / §14.1) or
the `tags` registry (§14.2).

### 18.2 Sending & message operations
| Method | Path | Purpose | Permission | Rate class | Idem. | Notable errors |
|---|---|---|---|---|---|---|
| POST | `/messages/send` | Send a message (template/text/media/interactive) | `messages:send` | `send` | **key req** | 422(window/opt-in), 409, 502 |
| GET | `/messages/{uuid}` | Get a message (+ current status) | `inbox:read` | `read` | — | 404 |
| GET | `/messages/{uuid}/status-history` | Delivery/read/failed timeline | `inbox:read` | `read` | — | 404 |
| POST | `/messages/{uuid}/reaction` | Send a reaction emoji | `messages:send` | `send` | key | 422 |
| GET | `/messages/search` | Search messages (`q`, filters) | `inbox:read` | `read` | — | — |
| GET | `/quick-replies` | List quick replies (personal+shared) | `inbox:read` | `read` | — | — |
| POST | `/quick-replies` | Create quick reply | `inbox:write` | `write` | — | 409(shortcut) |
| PATCH | `/quick-replies/{uuid}` | Edit quick reply | `inbox:write` | `write` | — | 404 |
| DELETE | `/quick-replies/{uuid}` | Delete quick reply | `inbox:write` | `write` | — | 404 |

**`POST /messages/send` — sample (template)**
```http
POST /api/v1/messages/send
Idempotency-Key: 018f...
Content-Type: application/json

{ "phone_number_id":"018f...","to":"+14155552671","type":"template",
  "template":{ "name":"order_update","language":"en_US",
    "variables":{"body":["Priya","#1234","shipped"]},
    "buttons":[{"index":0,"type":"url","url_suffix":"1234"}] } }
```
```json
202 Accepted
{ "id":"018f...","status":"accepted","wamid":null,"conversation_id":"018f...",
  "queued_at":"2026-07-15T09:31:00Z" }
```
- **Window enforcement (critical):** for `type:"text"`/free-form, the server checks the conversation's
  **24-hour window**; if closed → `422 code:"window_closed"` instructing use of a template (Doc 1
  FR-WA-12/INB-06). Template sends are always allowed (subject to approval + opt-in).
- **Idempotency:** required key + data-layer `wamid`/unique constraints prevent duplicates.
- **Status lifecycle:** the send returns `accepted`; real delivery/read updates arrive via **webhook**
  and are pushed to the UI over SSE/WebSocket (§20) and readable via `/status-history`.
- **Typing indicators:** Cloud API supports marking messages read / typing on inbound handling; where
  supported, `POST /conversations/{uuid}/read` also emits the read receipt. (Outbound typing is limited
  by Meta; the API exposes only what the platform officially supports — no unofficial signals.)
- **Performance:** `/conversations` list uses denormalized `last_message_preview`/`unread_count` (Doc 3
  §9.1) so the inbox renders instantly; message history is cursor-paginated over the partitioned ledger.

---

## 19. AI endpoints

**Route rationale:** AI is a set of *capabilities* applied to existing resources, grouped under `/ai`.
Every generative action returns a **draft for human review** — the API has **no endpoint that lets AI
send a customer message directly** (Doc 1 FR-AI-10). Sending always goes through `/messages/send` or
`/campaigns/send` after a human approves.

| Method | Path | Purpose | Permission | Rate class | Notes |
|---|---|---|---|---|---|
| GET | `/ai/knowledge-base` | List KB documents | `ai:use` | `read` | — |
| POST | `/ai/knowledge-base` | Add KB document (chunked+embedded async) | `ai:manage` | `bulk` | 202(job) |
| GET | `/ai/knowledge-base/{uuid}` | Get KB doc | `ai:use` | `read` | 404 |
| PATCH/DELETE | `/ai/knowledge-base/{uuid}` | Edit/remove KB doc | `ai:manage` | `write` | 404 |
| POST | `/ai/knowledge-base/search` | RAG search over KB (returns passages) | `ai:use` | `ai` | 422 |
| POST | `/ai/suggest-reply` | Draft reply for a conversation | `ai:use` | `ai` | returns draft only |
| POST | `/ai/summarize` | Summarize a conversation | `ai:use` | `ai` | — |
| POST | `/ai/generate-campaign` | Draft campaign copy/variables | `ai:use` | `ai` | draft only |
| POST | `/ai/generate-template` | Draft a compliant template | `ai:use` | `ai` | draft only |
| POST | `/ai/auto-tag` | Suggest tags for a contact/conversation | `ai:use` | `ai` | suggestions only |
| POST | `/ai/sentiment` | Sentiment score for text/conversation | `ai:use` | `ai` | — |
| POST | `/ai/translate` | Translate text/message | `ai:use` | `ai` | — |

**`POST /ai/suggest-reply` — sample**
```json
// request
{ "conversation_id":"018f...", "tone":"friendly", "use_knowledge_base":true }
// response
{ "draft":"Hi Priya! Your order #1234 shipped today and arrives Thu...",
  "sources":[{"kb_id":"018f...","title":"Shipping Policy"}],
  "requires_approval":true, "ai_conversation_id":"018f..." }
```
- **Human-in-the-loop:** `requires_approval:true` is always present; the frontend must route the draft
  through the normal send flow (with a human click). The `ai_conversation_id` links the interaction for
  audit (Doc 3 `ai_conversations`).
- **Cost/rate:** `ai` class + per-org token accounting; provider is config-driven (NFR-EXT-04, default
  latest Claude models).

---

## 20. Analytics & reporting

**Route rationale:** analytics are **read-only** aggregate resources under `/analytics`, each accepting a
common time-range + grouping contract, so the frontend charts share one query shape.

| Method | Path | Purpose | Permission | Rate class |
|---|---|---|---|---|
| GET | `/analytics/dashboard` | KPI tiles + trend series for the home dashboard | `analytics:read` | `read` |
| GET | `/analytics/campaigns` | Cross-campaign performance | `analytics:read` | `read` |
| GET | `/analytics/campaigns/{uuid}` | Single-campaign deep dive | `analytics:read` | `read` |
| GET | `/analytics/delivery` | Delivery/read/failure rates over time | `analytics:read` | `read` |
| GET | `/analytics/agents` | Agent performance (volume, response time) | `analytics:read` | `read` |
| GET | `/analytics/cost` | Cost analytics (by category/country/number/date) | `analytics:read` | `read` |
| GET | `/analytics/templates` | Template usage/quality/perf | `analytics:read` | `read` |
| GET | `/analytics/clicks` | Click/URL tracking analytics | `analytics:read` | `read` |
| POST | `/analytics/reports/export` | Export a report (CSV/Excel/JSON, async) | `analytics:read` | `bulk` |

**Common query contract:** `?from=2026-07-01&to=2026-07-31&granularity=day&number=018f...&timezone=Asia/Kolkata`.

**`GET /analytics/dashboard` — sample (excerpt)**
```json
{
  "range":{"from":"2026-07-01","to":"2026-07-15","granularity":"day"},
  "kpis":{"messages_sent":420310,"delivered_rate":0.972,"read_rate":0.611,
          "failed_rate":0.011,"active_campaigns":3,"spend":1204.55,"currency":"USD"},
  "series":{"sent":[{"t":"2026-07-01","v":21000}, "..."],
            "delivered":["..."],"read":["..."]}
}
```
- **Performance:** dashboards read **pre-aggregated** rollups (built by scheduled jobs, Doc 5) and
  denormalized counters, hitting the <1.5s target (NFR-PERF-06) without scanning 100M rows live.
- **Cost analytics** is computed from the `messages` ledger's `category/country/cost_amount` (Doc 3 §9.2)
  — exact spend, our differentiator (FR-AN-03).

---

## 21. Global search

| Method | Path | Purpose | Permission | Rate class |
|---|---|---|---|---|
| GET | `/search` | Unified search across resource types | (per-type read perms) | `read` |

`GET /search?q=priya&types=contacts,messages,campaigns,templates,users&limit=5`
```json
{
  "query":"priya",
  "groups":{
    "contacts":{"data":[{"id":"018f...","full_name":"Priya R","phone_e164":"+1..."}],"has_more":true},
    "messages":{"data":[{"id":"018f...","preview":"...priya...","conversation_id":"018f..."}],"has_more":false},
    "campaigns":{"data":[],"has_more":false},
    "templates":{"data":[],"has_more":false},
    "users":{"data":[],"has_more":false}
  }
}
```
- Results are **permission-filtered per type** (a user without `inbox:read` gets no message hits).
- Backed by indexed columns / FULLTEXT (Doc 3 §13.3); an external search engine can back it later
  without changing this contract (§18 extensibility).

---

## 22. Administration & operations

| Method | Path | Purpose | Permission | Rate class |
|---|---|---|---|---|
| GET/PUT | `/settings` | Read/update system & org settings | `settings:read` / `settings:manage` | `read`/`write` |
| GET | `/feature-flags` | List feature flags | `settings:read` | `read` |
| PATCH | `/feature-flags/{key}` | Toggle/target a flag | `settings:manage` | `write` |
| GET | `/audit-logs` | Query audit trail (filter actor/entity/action/date) | `audit:read` | `read` |
| GET | `/notifications` | List own notifications (unread filter) | `auth:self` | `read` |
| POST | `/notifications/{uuid}/read` | Mark notification read | `auth:self` | `write` |
| POST | `/notifications/read-all` | Mark all read | `auth:self` | `write` |
| GET | `/monitoring/metrics` | Subsystem metrics (queue/redis/mysql/api/webhook) | `system:read` | `read` |
| GET | `/jobs` | List background jobs (filter status/type) | `system:read` | `read` |
| GET | `/jobs/{uuid}` | Job detail/progress | `system:read` | `read` |
| POST | `/jobs/{uuid}/cancel` | Cancel a cancellable job | `system:manage` | `write` |
| GET | `/queues` | Queue depth/throughput per queue | `system:read` | `read` |
| GET | `/backups` | List backups + verification status | `system:manage` | `read` |
| POST | `/backups` | Trigger a backup | `system:manage` | `write` |
| POST | `/backups/{uuid}/restore` | Start a guided restore | `system:manage` | `write` |
| GET | `/health` | Liveness (public, no auth) | Public | — |
| GET | `/ready` | Readiness (deps: db/redis/meta) | Public/system | — |

**`GET /health` / `GET /ready`** — for orchestration (Doc 1 FR-MON-09). `/health` is a cheap liveness
`200 {"status":"ok"}`; `/ready` checks MySQL, Redis, and Meta reachability and returns `503` with a
per-dependency breakdown when degraded (drives graceful degradation, NFR-DR-08).

**Monitoring/queues** power the ops dashboard (FR-MON-01..10) reading `monitoring_metrics`, `job_metadata`,
and live Redis/Celery stats. Audit-log queries hit the partitioned `audit_logs` with entity/actor indexes.

---

## 23. Webhooks (inbound from Meta)

**Route rationale:** the inbound webhook is a **public**, signature-gated endpoint, deliberately separate
from the authenticated API. It does the absolute minimum synchronously (verify + persist + `200`) and
processes asynchronously (Doc 1 FR-WA-05/07).

| Method | Path | Purpose | Auth | Notes |
|---|---|---|---|---|
| GET | `/webhooks/whatsapp` | Meta verification handshake (`hub.challenge`) | Verify token | Returns challenge on match |
| POST | `/webhooks/whatsapp` | Receive messages + statuses | `X-Hub-Signature-256` | Persist raw → `200` fast → async process |
| GET | `/webhooks/events` | Admin: list received webhook events (filter status) | `webhooks:manage` | from `webhook_events` |
| POST | `/webhooks/events/{uuid}/replay` | Replay a processed/failed event | `webhooks:manage` | idempotent |
| GET | `/webhooks/dead-letter` | List dead-letter queue | `webhooks:manage` | from `webhook_dead_letter` |
| POST | `/webhooks/dead-letter/{uuid}/replay` | Replay a dead-lettered event | `webhooks:manage` | — |
| POST | `/webhooks/dead-letter/{uuid}/discard` | Discard a dead-lettered event | `webhooks:manage` | — |

- **Signature verification:** every `POST` verifies `X-Hub-Signature-256` (HMAC-SHA256 over the raw body
  with the app secret) **before** parsing; failure → `403` and the event is not trusted (Doc 1 security).
- **Fast ack + idempotency:** the raw payload is written to `webhook_events` and `200` is returned in
  <200ms; a Celery task processes it. Duplicate deliveries (Meta retries up to 7 days) are deduped by
  `event_id`/message id → status `duplicate`, never double-applied (FR-WA-07).
- **Dead-letter + replay:** events that fail processing after retries land in `webhook_dead_letter` for
  inspection and one-click replay (FR-WA-08) — nothing is lost.

### 23.1 Replay, retention & duplicate protection

Replay (of both `webhook_events` and dead-letter entries) is deliberately constrained so it is safe,
bounded, and auditable:

| Aspect | Policy |
|---|---|
| **Replay retention** | Raw `webhook_events` retained **90 days** (Doc 3 §15); dead-letter entries retained **180 days** or until explicitly discarded. Only events still within retention are replayable. |
| **Maximum replay age** | Events older than their retention window are not replayable via the API (→ `410 Gone`); recovery for those is via database backup only. |
| **Replay limits** | Manual replay is `webhooks:manage` + `write` rate class. Automated dead-letter retries use capped exponential backoff, **max 5 attempts**, after which the entry is parked as `pending` for human action (no infinite loops). |
| **Replay ordering** | Replays for a given conversation/number are applied in **`occurred_at` (Meta timestamp) order**, not receipt order, so a late `delivered` never clobbers a later `read`. Cross-conversation ordering is neither guaranteed nor required. |
| **Duplicate protection** | Replays run through the **same idempotent processor** as live events: dedupe by `event_id`/message id, and status transitions are **monotonic** (status never regresses). Re-applying an already-applied event is a no-op marked `duplicate`. |
| **Audit logging** | Every manual replay/discard writes an `audit_logs` row (actor, event id, outcome) — operator interventions are fully traceable (NFR-SEC-07). |
| **Bulk replay** | An optional batch replay accepts a filter and replays matching entries as an async job following the partial-success standard (§29). |

---

## 24. Asynchronous events (real-time to clients)

Delivery/read/inbound updates originate at Meta (webhooks) and must reach the UI live. Two channels:

- **Server-Sent Events (SSE):** `GET /api/v1/events/stream?topics=inbox,dashboard,campaigns`
  (Bearer auth). One-way server→client push for the inbox, dashboard counters, and campaign progress.
  Chosen as the default (simple, proxy-friendly, auto-reconnect).
- **WebSocket (optional):** `/api/v1/ws` for bidirectional needs (typing/presence) if required later.
- **Outbound webhooks (future/public API):** the platform can POST signed events to a company-registered
  URL (`webhooks:manage`), for CRM/automation integrations (NFR-EXT-05).

**Event catalog** (payload = `{ "event": <name>, "id": <uuid>, "occurred_at": <ts>, "data": {...} }`):

| Event | Trigger | Consumers |
|---|---|---|
| `campaign.started` | Campaign send begins | dashboard, campaign view, notifications |
| `campaign.progress` | Batch completes (throttled) | campaign view live counters |
| `campaign.finished` | Campaign completes/cancelled | dashboard, notifications |
| `message.accepted` | Outbound queued to Meta | conversation view |
| `message.delivered` | Status webhook `delivered` | conversation, delivery analytics |
| `message.read` | Status webhook `read` | conversation, read analytics |
| `message.failed` | Status webhook `failed` | conversation, failure analytics, notifications |
| `message.received` | Inbound message webhook | inbox (new/updated conversation), active-detection |
| `template.approved` / `template.rejected` | Template status webhook | templates view, notifications |
| `webhook.received` | Any inbound webhook persisted | ops/monitoring |
| `queue.failed` | Job/queue failure threshold | monitoring, notifications |
| `number.quality_changed` | Quality-rating webhook | waba/health view, notifications |

These events map 1:1 to internal domain events on the event bus (Doc 5), so SSE, notifications, and
future outbound webhooks all consume the same stream.

### 24.1 SSE connection specification

The SSE stream (`GET /api/v1/events/stream`) follows a strict operational contract so clients reconnect
cleanly and neither miss nor duplicate events:

| Parameter | Value / behavior |
|---|---|
| **Authentication** | `Authorization: Bearer <access token>` on connect. |
| **Auth renewal** | When the access token nears expiry the client refreshes via `/auth/refresh` and **reconnects** with the new token. A stream whose token expires receives an `auth_expired` event and is closed, signaling the client to renew — the server never serves data on an expired token. |
| **Heartbeat** | The server emits a comment heartbeat (`: ping`) every **15 s** to keep proxies from idling the connection. |
| **Connection timeout** | A client that misses **3 heartbeats (~45 s)** treats the connection as dead and reconnects. Servers may recycle a stream after **1 hour**; the client reconnects transparently. |
| **Reconnect strategy** | Native `EventSource` auto-reconnect augmented with **exponential backoff + jitter** (1s → 2s → 4s … cap 30s) to avoid thundering herds after a server blip. |
| **Retry interval hint** | The server sends the SSE `retry:` field (default **3000 ms**) to set the client's base reconnect delay. |
| **Event ids & ordering** | Each event carries a monotonic `id:` (per-stream sequence). On reconnect the client sends `Last-Event-ID`; the server **resumes from the last delivered id** while the short backlog buffer still holds it, otherwise sends a `resync` event telling the client to refetch affected resources. Ordering is **guaranteed per topic** (e.g., a conversation's message events); cross-topic ordering is not. |
| **Max concurrent connections** | Bounded **per user** (default 5) and **per organization** (configurable); excess connects get `429`. The frontend prefers **one shared multiplexed stream** over one-per-tab. |
| **Topics** | `?topics=inbox,dashboard,campaigns,notifications`; only events the user is permitted to see are delivered (per-topic RBAC). |
| **Fallback** | If SSE is blocked by an intermediary, the client falls back to short-interval polling of the relevant list endpoints — no functionality is lost, only immediacy. |

---

## 25. Security (consolidated)

| Control | How the API applies it |
|---|---|
| **JWT auth** | Bearer access token on every non-public route; short TTL; permissions embedded + server-verified. |
| **RBAC** | `resource:action` permission required per endpoint (tables above); Owner bypass; `403` on miss. |
| **API-key auth** | Hashed keys, scoped permissions, per-key rate limits (future public API). |
| **CSRF** | Header-bearer tokens (not cookies) → not CSRF-exploitable; cookie mode (if used) adds `SameSite=Strict` + CSRF token (NFR-SEC-01). |
| **Rate limiting** | Per-user/IP classes (§9); `429` + `Retry-After`; Redis counters. |
| **IP restrictions** | Allow/block CIDR rules (Doc 3 `ip_access_rules`), applied to admin/webhook/api surfaces (NFR-SEC-05). |
| **Input validation** | Every body/param validated (types, formats, enums, sizes) → `422` problem with field errors. |
| **Webhook signatures** | `X-Hub-Signature-256` verified before trust (§23). |
| **Idempotency** | `Idempotency-Key` on sends/creates + data-layer uniqueness (§8). |
| **Output safety** | Secrets/tokens never returned; media via signed URLs; error bodies carry no sensitive data. |
| **Auditing** | All mutations recorded in `audit_logs` with actor, before/after, `request_id`. |

---

## 26. Versioning & deprecation

- **URI versioning:** `/api/v1`. A breaking change means `/api/v2`; `v1` keeps running in parallel.
- **Additive within a version:** new endpoints, new **optional** fields, new enum values behind
  capability flags — never remove/rename/retype an existing field in `v1`. Clients must ignore unknown
  fields (documented contract), which lets us add data without a major bump.
- **Deprecation policy:** a deprecated endpoint returns a `Deprecation` header + `Sunset` date and is
  documented; removal only in the next major version after the sunset window. Removed → `410 Gone`.
- **10-year stability:** `v2`/`v3` can be introduced later without breaking `v1` clients (mobile/public
  API/integrations), satisfying the longevity goal.

---

## 27. OpenAPI 3.1 & SDK strategy

- The entire contract above is expressible in **OpenAPI 3.1**: each resource is a `schema` component,
  each error is the shared `Problem` component, pagination/filter params are reusable `parameter`
  components, and security schemes model Bearer JWT + API key.
- The spec will be **generated and served** so tooling works out of the box: **Swagger UI** and **Redoc**
  for interactive docs, and **client SDK generation** (TypeScript for the frontend/mobile; others as
  needed) from the same source of truth.
- Because fields are `snake_case` and consistent, generated TS types drop straight into the React app
  (React Query hooks), keeping frontend and backend in lockstep.

### 27.1 OpenAPI 3.1 document organization

The generated spec is organized for clarity, reuse, and stable codegen:

| Element | Organization |
|---|---|
| **Tags** | One tag per domain — `Auth`, `Users`, `Roles`, `WABA`, `Phone Numbers`, `Contacts`, `Tags`, `Segments`, `Templates`, `Media`, `Campaigns`, `Inbox`, `Messages`, `AI`, `Analytics`, `Search`, `Admin`, `Webhooks`, `Events` — driving grouped navigation in Swagger UI / Redoc. |
| **Reusable schemas** (`components/schemas`) | Every resource (`Contact`, `Campaign`, `Message`, `Template`, …) plus shared objects: `Page`, `Problem`, `Job`, `PartialSuccessResult`, and the status/category enums. |
| **Reusable parameters** (`components/parameters`) | `LimitParam`, `CursorParam`, `SortParam`, `SearchQParam`, `FilterParam`, `TimeRangeFrom/To`, `Granularity`, `IdempotencyKeyHeader`, `IfMatchHeader`. |
| **Reusable responses** (`components/responses`) | `Unauthorized401`, `Forbidden403`, `NotFound404`, `Conflict409`, `Validation422`, `RateLimited429`, `ServerError500`, `Accepted202`, `NoContent204` — referenced by every operation so error contracts stay DRY and consistent. |
| **Reusable security schemes** (`components/securitySchemes`) | `bearerAuth` (JWT) and `apiKeyAuth`; applied globally with per-operation overrides for public routes. |
| **Error components** | The single RFC 7807 `Problem` schema (with `code`, `request_id`, `errors[]` extensions) referenced by all error responses. |
| **Examples** | Named request/response examples per operation (the samples in this document become OpenAPI `examples`) so "Try it out" and generated docs are realistic. |
| **operationId** | Stable, predictable `verbResource` ids (`listContacts`, `sendMessage`, `sendMessageBatch`) → clean generated SDK method names. |

### 27.2 SDK generation & version compatibility

From the single OpenAPI source we generate typed client SDKs so integrators never hand-write HTTP:

| Language | Primary use |
|---|---|
| **TypeScript** | React frontend + future web/mobile (React Query hooks). |
| **Python** | Internal automation, data/AI scripts, server-to-server. |
| **Node.js** (JS) | Node integrations without TypeScript. |
| **PHP** | Common CRM / e-commerce (WordPress, Laravel) integrations. |
| **Go**, **Java**, **C#** | Enterprise back-office integrations. |

**Version compatibility rules:**
- SDKs are versioned to the **API major version** (`v1`); a `v1` SDK works against any additive `v1.x`
  server (unknown fields ignored, new optional params defaulted).
- SDKs are **regenerated on every additive release** and published with semver: **minor** for new
  endpoints/fields, **patch** for docs/fixes, **major** only for `/api/v2`.
- The `GET /api` capability handshake (§33) lets an SDK detect enabled modules/features at runtime and
  degrade gracefully against an older or feature-limited server.
- Backward compatibility is contractually guaranteed within a major version (§26), so upgrading the
  server never breaks an existing SDK client.

---

## 28. Self-review record

Reviewed as **Principal API Architect, Senior Backend, Senior Frontend, Security, DevOps, QA**; issues
found were fixed before presenting:

- **Completeness (Architect/QA):** every capability area in the brief has endpoints — auth, users/roles,
  WABA/numbers/health, contacts/import/export/bulk/segments/attributes/search, templates, media,
  campaigns (+schedule/pause/resume/cancel/retry/duplicate/preview/estimate/analytics/recipients),
  messaging/inbox/quick-replies/notes, AI (with human-approval), analytics, admin/monitoring/health/jobs/
  queues/backups, webhooks (+replay/DLQ), global search, and async events. ✔
- **Uniformity (Frontend):** one error format (RFC 7807), one pagination format (cursor), one filter
  grammar, one time-range contract for analytics — so the React client shares infrastructure. ✔
- **Security (Security Eng):** every route has explicit auth + permission; implicit `401/403/429/500`;
  webhook signature; idempotency on sends; tokens never returned; IP rules; input validation → `422`. ✔
- **Reliability (DevOps):** long operations are async `202` + job polling + SSE; sends are idempotent and
  crash-safe via the ledger; `/health` + `/ready` for orchestration. ✔
- **Meta-compliance (Backend):** send endpoints enforce opt-in, 24-hour window, template approval, and
  messaging limits server-side; no endpoint bypasses these; no unofficial-API surface. ✔
- **Performance (Backend):** cursor pagination everywhere large; dashboards/analytics read pre-aggregated
  rollups + denormalized counters; list endpoints sort only on indexed columns. ✔
- **Extensibility (Architect):** URI versioning + additive rules; `channel_type`-ready messaging routes;
  outbound-webhook/event bus for integrations; OpenAPI-3.1/SDK-ready — stable for 10+ years. ✔
- **Traceability:** endpoints cite Doc 1 requirement IDs and Doc 3 tables; schemas use the UUIDv7 public
  ids and `snake_case` fields consistent with the database. ✔

> **Enhancement pass:** sections **§29–§36** were added on 2026-07-15 (owner-requested). §36 is the
> enhancement self-review covering those additions.

---

## 29. Partial success standard

Bulk and batch operations (which act on many items in one request) use **one uniform result contract**
so every client handles them identically.

**Status code:** a bulk/batch request that is accepted and processed returns **`200 OK`** when run
synchronously with a per-item breakdown, or **`202 Accepted`** + a job when run asynchronously (large
sets). When some items succeed and some fail it is **still `200`/`202`** — the operation as a whole
succeeded; per-item outcomes are in the body. (We deliberately avoid `207 Multi-Status`, which is
WebDAV-oriented and awkward for JSON clients — see §35.) A request that fails *as a whole* (auth,
permission, malformed body) returns the usual `4xx` problem (§5).

**Result envelope — `PartialSuccessResult`:**
```json
{
  "summary": { "total": 1000, "succeeded": 995, "failed": 5, "skipped": 0 },
  "status": "partial_success",              // success | partial_success | failed
  "job_id": "018f...",                       // present when processed asynchronously
  "errors": [
    { "index": 42, "id": "+1415...", "code": "invalid_format", "message": "phone_e164 not valid E.164" },
    { "index": 88, "id": "+9199...", "code": "duplicate",      "message": "contact already exists" }
  ],
  "error_report_url": "/api/v1/.../errors.csv"   // full report for large sets
}
```

**Client handling:**
- Treat `status` as the source of truth: `success` (all applied), `partial_success` (show the counts +
  `errors[]`/`error_report_url`), `failed` (nothing applied — safe to retry wholesale).
- `errors[]` is **capped** (first 100) for readability; the complete list is at `error_report_url`.
- Items are committed **per-item, not per-request** (unless the caller sets `"atomic": true` for small
  sets), so a retry should target only the failed items — the required `Idempotency-Key` (§8) makes that safe.
- For async jobs, poll `job_id` (`GET /jobs/{uuid}`) until terminal, then read this same envelope.

---

## 30. Bulk operations

A standardized family of bulk endpoints applies one action to many resources efficiently. **All** bulk
endpoints share: the **`bulk` rate class**, a **required `Idempotency-Key`**, the **partial-success
result** (§29), and **async execution** (`202` + job) above a threshold (default > 1,000 items; smaller
sets may run synchronously and return `200`).

| Method | Path | Purpose | Permission |
|---|---|---|---|
| POST | `/contacts/bulk` | **Bulk create** contacts (with dedup strategy) | `contacts:write` |
| POST | `/contacts/bulk-update` | **Bulk update** fields over a selection or filter | `contacts:write` |
| POST | `/contacts/bulk-delete` | **Bulk delete** (soft) over a selection or filter | `contacts:write` |
| POST | `/contacts/bulk-tag` | **Bulk add/remove tags** | `contacts:write` |
| POST | `/contacts/bulk-attributes` | **Bulk custom-attribute update** | `contacts:write` |
| POST | `/campaigns/bulk-action` | **Bulk campaign actions** (pause/resume/cancel/archive) | `campaigns:manage` |
| POST | `/templates/bulk` | **Bulk template operations** (sync/submit/delete) | `templates:write` |

**Request format** — two mutually-exclusive addressing modes:
```json
// (a) explicit ids
{ "ids": ["018f...","018f..."], "action": "add_tags", "payload": { "tags": ["vip"] } }

// (b) filter — act on everything matching (server resolves the set)
{ "filter": { "match":"all", "rules":[{ "field":"opt_in_status","op":"eq","value":"opted_in" }] },
  "action": "add_tags", "payload": { "tags": ["vip"] },
  "expected_count": 12500 }   // optional safety guard
```

- **Validation:** body/`action`/`payload` validated up front (`422` on structural errors); per-item
  validation happens during processing and surfaces in `errors[]`.
- **Partial success:** per §29 — valid items commit, invalid items are reported; not all-or-nothing
  (unless the caller opts into `"atomic": true` for small sets).
- **Progress tracking:** async bulk ops return `job_id`; `GET /jobs/{uuid}` reports
  `processed/total/succeeded/failed` for a live progress bar.
- **Error reporting:** capped inline `errors[]` + downloadable `error_report_url` for large sets.
- **Idempotency:** the required `Idempotency-Key` prevents a retried bulk request from double-applying;
  filter-mode snapshots the resolved set so re-runs are stable.
- **Safety guard:** filter-mode supports `expected_count` — if the live count differs beyond a tolerance
  (data changed underneath), the server returns `409` rather than acting on a surprise set.

---

## 31. Batch messaging API

`POST /messages/send-batch` sends a message to a **hand-picked list of contacts without creating a
campaign** — for ad-hoc sends (e.g., "message these 40 leads") that don't warrant the full campaign
lifecycle. It complements, and reuses the pipeline of, §17/§18.

| Method | Path | Purpose | Permission | Rate class | Idem. |
|---|---|---|---|---|---|
| POST | `/messages/send-batch` | Send one template to many selected contacts | `messages:send` | `send` | **key req** |
| POST | `/messages/send-batch/estimate` | Cost estimate for a batch (no send) | `messages:send` | `read` | — |
| GET | `/messages/send-batch/{job_uuid}` | Batch progress + per-recipient outcomes | `inbox:read` | `read` | — |

**Request:**
```json
{ "phone_number_id":"018f...",
  "template":{ "name":"promo","language":"en_US" },
  "recipients":[ { "contact_id":"018f...","variables":{"1":"Priya"} },
                 { "to":"+14155550000","variables":{"1":"Sam"} } ],
  "throttle_mps": 20 }
```

- **Maximum recipients:** **10,000 per request**. Larger audiences must use a campaign (built for
  millions); over the cap → `422 code:"batch_too_large"`.
- **Async processing:** accepted (`202` + `job_id`) and enqueued; the endpoint never blocks on delivery.
- **Queue behavior:** batches share the **same send pipeline, throttling, and smart-retry** as campaigns
  (Doc 5), bounded by the number's messaging tier/MPS, but are tracked as a lightweight batch job rather
  than a campaign entity. Per-recipient rows are still written to the message ledger.
- **Validation:** enforces **opt-in**, **template approval**, and the **24-hour-window/template** rule
  per recipient exactly like campaigns; invalid recipients are reported via §29, valid ones still send.
- **Cost estimation:** `/estimate` returns the same rate-card breakdown as campaign estimation (§17) —
  the same global card (Doc 3 §8.5), the same money rules, the same `unresolved` handling, and the same
  `rate_card_not_configured` error. The rate card has exactly one contract; §17 is its definition.
  *(Bulk send is not Phase 6 Step 5; this cross-reference fixes the shared contract, it does not schedule the endpoint.)*
- **Idempotency & rate limiting:** required `Idempotency-Key`; `send` rate class (Meta-limit-aware);
  data-layer uniqueness prevents duplicate sends on retry.

---

## 32. API usage & quotas

Usage endpoints expose consumption for observability today and **billing readiness** tomorrow (should
usage ever be metered internally). Read-only, org-scoped.

| Method | Path | Purpose | Permission | Rate class |
|---|---|---|---|---|
| GET | `/api-usage` | Current-period usage snapshot + quota status | `analytics:read` | `read` |
| GET | `/api-usage/history` | Usage time-series over a range | `analytics:read` | `read` |

**Tracked dimensions:** API requests, messages sent (by category), campaigns run, **AI token usage**
(prompt/completion), storage used (media/exports), imports, exports, webhook counts
(received/processed/failed), and **rate-limit consumption** per class.

**`GET /api-usage` — sample:**
```json
{
  "period": { "from":"2026-07-01","to":"2026-07-15","reset_at":"2026-08-01T00:00:00Z" },
  "usage": {
    "api_requests": 128340,
    "messages_sent": { "marketing":210000,"utility":34000,"authentication":5000,"service":98000 },
    "campaigns_run": 12,
    "ai_tokens": { "prompt":1840000,"completion":420000 },
    "storage_bytes": 5321000000,
    "imports": 8, "exports": 22,
    "webhooks": { "received":512000,"processed":511800,"failed":200 },
    "rate_limits": { "read":{"limit":600,"peak_used":540}, "send":{"tier":"TIER_100K","peak_used":42310} }
  },
  "quotas": { "ai_tokens_month": {"limit":5000000,"used":2260000,"status":"ok"},
              "storage_bytes": {"limit":53687091200,"used":5321000000,"status":"ok"} }
}
```
- **Billing readiness:** usage counters are keyed by org/period/metric, so a future internal
  chargeback/billing view needs no new instrumentation — the numbers already exist. Quotas are **soft**
  by default (surfaced + alertable) and can be made enforcing per metric.
- **Performance:** served from pre-aggregated counters (Redis + periodic rollup to MySQL), never live scans.

---

## 33. API metadata & capability discovery

`GET /api` is a **public, unauthenticated** capability document letting clients (frontend, SDKs, mobile)
discover what the server supports before/independently of auth — enabling graceful feature degradation
and forward/backward compatibility (used by the SDK handshake in §27.2).

| Method | Path | Purpose | Auth | Rate class |
|---|---|---|---|---|
| GET | `/api` | API + build metadata and enabled capabilities | Public | `read` |

**Sample:**
```json
{
  "api_version": "v1",
  "build_version": "1.4.2",
  "release_date": "2026-07-15",
  "server_time": "2026-07-15T09:45:12Z",
  "openapi_version": "3.1.0",
  "supported_authentication": ["bearer_jwt","api_key"],
  "supported_ai_provider": { "name":"anthropic","default_model":"claude-opus-4-8" },
  "enabled_modules": ["auth","contacts","templates","campaigns","inbox","analytics","ai","webhooks"],
  "supported_features": {
    "batch_messaging": true, "recurring_campaigns": true, "flows": false,
    "commerce": false, "omnichannel": false, "sse": true, "websocket": false
  },
  "limits": { "batch_max_recipients": 10000, "max_upload_mb": 100, "max_page_limit": 200 }
}
```
- **Why public:** it exposes only capabilities (no sensitive data), so the login screen, health probes,
  and SDK handshakes can read it without credentials.
- **Forward-compat:** clients key features off `supported_features`/`enabled_modules` (which grow as
  future modules ship), so a newer client degrades cleanly against an older server and vice-versa.

---

## 34. Appendix A — Operational recommendations

Non-normative recommended defaults for a production deployment (tuned in Doc 7).

| Concern | Recommendation | Rationale |
|---|---|---|
| **DB connection pool** | API: **10–20** per worker process; Celery: **5–10** per worker; total ≤ MySQL `max_connections` with margin. | Async SQLAlchemy multiplexes; oversized pools waste MySQL memory and cause contention. |
| **Redis pool** | **20–50** per process; broker and cache logically separated. | Broker, cache, and pub/sub traffic differ; keep headroom. |
| **API request timeout** | Server hard timeout **30 s**; clients **15 s** reads, **60 s** bulk submits (which return `202` fast anyway). | Long work is async; sync requests must never hang. |
| **Upstream (Meta) timeout** | **10 s** connect/read + retries + circuit breaker. | Isolates the app from Meta latency; feeds graceful degradation. |
| **Max JSON payload** | **1 MB** default; bulk bodies up to **5 MB**. | Prevents memory abuse; large data goes via uploads/imports. |
| **Max upload size** | **100 MB** (media additionally validated to Cloud API per-type limits, which are smaller). | Object storage handles bytes; protects the API tier. |
| **Compression** | `gzip`/`br` response compression for payloads > 1 KB (at Nginx); accept gzipped request bodies for bulk imports. | Cuts bandwidth for large lists/analytics. |
| **Caching** | `Cache-Control` on static/rarely-changing reads (permission catalog, `GET /api`, template lists); private short TTLs for user data. | Reduces load without staleness risk. |
| **ETag / If-None-Match** | Strong `ETag` (representation hash) on cacheable single-resource GETs; clients send `If-None-Match` → **`304 Not Modified`** when unchanged. | Saves bandwidth for polling clients and detail views. |
| **If-Match** | Used for optimistic-concurrency writes (§5.2) — distinct from `If-None-Match` (caching). | Prevents lost updates. |
| **Keep-alive / HTTP/2** | Enabled at Nginx for the SPA and SSE. | Fewer connections, better multiplexing. |

---

## 35. Appendix B — API design decisions & trade-offs

For each major decision: what we chose, alternatives considered, why they were rejected, benefits,
limitations, and the future migration path.

### 35.1 REST vs GraphQL
- **Chosen:** REST (resource-oriented, `/api/v1`).
- **Alternatives:** GraphQL; gRPC.
- **Rejected because:** GraphQL complicates caching, rate limiting, auth per-field, and file uploads, and
  invites unbounded queries against 100M-row tables; gRPC is poor for browsers and public webhooks.
- **Benefits:** HTTP caching/ETags, simple per-route RBAC + rate limits, trivial webhooks, universal
  tooling, easy SDK gen.
- **Limitations:** occasional over-/under-fetching; multiple round-trips for composite views.
- **Migration path:** a GraphQL/BFF gateway can be layered **in front** of the REST API later for
  specific rich clients without changing the core — REST stays the system of record.

### 35.2 Cursor vs Offset pagination
- **Chosen:** opaque cursor (keyset).
- **Alternatives:** offset/limit; page numbers.
- **Rejected because:** offset degrades (`O(n)` skips) at depth and **drifts/duplicates** under concurrent
  writes — untenable for 1M–100M-row tables.
- **Benefits:** `O(log n)` at any depth; stable under inserts; index-aligned (Doc 3 §13).
- **Limitations:** no random "jump to page N"; total counts are estimates.
- **Migration path:** offset can be offered as an opt-in for small, bounded admin lists without changing
  the default contract.

### 35.3 RFC 7807 problem details
- **Chosen:** `application/problem+json` for all errors.
- **Alternatives:** ad-hoc `{error, message}`; bare HTTP status.
- **Rejected because:** ad-hoc shapes fragment client handling and lack a standard for field errors.
- **Benefits:** one parseable error shape, machine `code`, field-level `errors[]`, `request_id`
  correlation; standard, OpenAPI-friendly.
- **Limitations:** slightly more verbose than a bare message.
- **Migration path:** extension members can be added over time without breaking clients (they ignore
  unknown fields).

### 35.4 JWT vs session cookies
- **Chosen:** stateless JWT access + server-revocable refresh (Bearer header).
- **Alternatives:** server-side session cookies; opaque tokens in a store.
- **Rejected because:** pure server sessions don't fit a stateless, horizontally-scaled API + future
  mobile/public API as cleanly; cookies raise CSRF concerns for a cross-client API.
- **Benefits:** stateless verification (scales), header-based (not CSRF-exploitable), works for web +
  mobile + API keys uniformly; refresh rotation with reuse detection covers revocation.
- **Limitations:** access tokens can't be revoked before expiry (mitigated by short TTL + refresh
  revocation + a `jti` denylist for emergencies).
- **Migration path:** an optional `SameSite=Strict` cookie mode (with CSRF tokens) exists for the
  first-party web app if desired — no API change.

### 35.5 SSE vs WebSocket
- **Chosen:** SSE as the default real-time channel; WebSocket optional/reserved.
- **Alternatives:** WebSocket for everything; long-polling.
- **Rejected because:** our real-time needs are **server→client** (delivery/read/inbound/progress);
  WebSocket adds bidirectional complexity, custom framing, and heavier infra for little gain; long-polling
  is inefficient.
- **Benefits:** plain HTTP, auto-reconnect, proxy-friendly, resumable via `Last-Event-ID`, simple auth.
- **Limitations:** one-way; limited concurrent connections per browser (mitigated by multiplexing).
- **Migration path:** `/ws` is reserved for future bidirectional features (typing/presence) alongside SSE.

### 35.6 Async jobs vs long requests
- **Chosen:** `202 Accepted` + job resource + SSE/poll for imports/exports/campaigns/bulk.
- **Alternatives:** synchronous long-running requests.
- **Rejected because:** multi-minute requests exhaust connections, hit proxy timeouts, and can't survive a
  restart — fatal for million-row work.
- **Benefits:** responsive UI, retriable/resumable, observable progress, crash-safe (durable job state).
- **Limitations:** clients must handle a two-step (submit → poll/stream) flow.
- **Migration path:** small operations still run synchronously; the threshold is tunable.

### 35.7 Resource-based URLs (vs RPC)
- **Chosen:** resource nouns + HTTP verbs, with `POST /{resource}/{id}/{action}` for state transitions.
- **Alternatives:** RPC-style verbs everywhere.
- **Rejected because:** RPC sprawls, is inconsistent, and maps poorly to caching/permissions.
- **Benefits:** predictable, cacheable, uniform RBAC; transitions (pause/resume) are explicit and
  idempotent.
- **Limitations:** some actions aren't perfectly "RESTful" nouns (accepted trade-off, clearly scoped).
- **Migration path:** new resources/actions slot in additively.

### 35.8 Idempotency keys
- **Chosen:** client-supplied `Idempotency-Key` on sends/creates + data-layer uniqueness.
- **Alternatives:** rely on client retries; server-side natural-key dedup only.
- **Rejected because:** network retries and double-clicks otherwise double-send/charge; natural-key dedup
  alone can't express "same request."
- **Benefits:** exactly-once semantics for money/message-affecting calls; safe retries.
- **Limitations:** clients must generate/store keys; server stores key→response for 24 h.
- **Migration path:** the key window and scope are configurable.

### 35.9 Bulk API strategy
- **Chosen:** dedicated bulk endpoints + partial-success envelope + async above a threshold (§29–§30).
- **Alternatives:** loop single-item calls client-side; all-or-nothing bulk.
- **Rejected because:** N calls are slow and rate-limit-hostile; all-or-nothing fails a whole batch for
  one bad row.
- **Benefits:** one round-trip, per-item outcomes, progress, idempotent, scalable.
- **Limitations:** partial success requires richer client handling (standardized in §29).
- **Migration path:** new bulk actions follow the same contract; batch messaging (§31) reuses it.

### 35.10 Versioning strategy
- **Chosen:** URI versioning (`/api/v1`) + additive evolution + deprecation policy.
- **Alternatives:** header/media-type versioning; no versioning.
- **Rejected because:** header versioning is invisible in logs/proxies and harder for integrators; no
  versioning risks breaking long-lived clients.
- **Benefits:** obvious, cache-friendly, lets `v1`/`v2` run in parallel — 10-year client stability.
- **Limitations:** a major bump duplicates routes during the overlap window.
- **Migration path:** `/api/v2` introduced beside `v1`; clients migrate on their own schedule; `v1`
  sunset only after a published window.

---

## 36. Self-review record — enhancement pass (v1.0 freeze)

Re-reviewed the **entire** document (original + additions) as **Principal API Architect, Senior Backend,
Senior Frontend, Security, Performance, DevOps, QA**; issues found were fixed before freezing:

- **Additive integrity:** no existing section was removed, renumbered, or restructured; the four "expand"
  items are in-place subsections (§23.1, §24.1, §27.1, §27.2) and the seven new items are appended
  (§29–§35), so all original cross-references still resolve. ✔
- **Consistency (Frontend):** bulk/batch reuse the single partial-success envelope (§29); usage/metadata
  follow the standard read/response conventions; SSE spec aligns with the event catalog (§24). ✔
- **Security (Security Eng):** batch/bulk require `Idempotency-Key` and enforce opt-in/window/approval
  like campaigns; `GET /api` and `GET /health` are the only new public routes and expose no sensitive
  data; replay is audited; usage endpoints are permission-gated. ✔
- **Performance (Perf Eng):** batch cap (10k) protects the send pipeline; bulk/imports are async above a
  threshold; usage/metadata are served from pre-aggregated counters; ETag/`304` and compression added in
  Appendix A reduce load. ✔
- **Reliability (DevOps):** replay limits/ordering/duplicate-protection specified (§23.1); SSE reconnect/
  resume/heartbeat specified (§24.1); operational timeouts/pools recommended (§34). ✔
- **Completeness (QA):** every requested addition is present — bulk ops, batch messaging, usage/quotas,
  `GET /api`, partial-success standard, SSE spec, webhook replay, OpenAPI organization, SDK generation,
  operational appendix, and the design-decisions appendix. ✔
- **Rationale (Architect):** §35 documents the "why/alternatives/rejected/benefits/limits/migration" for
  all ten key decisions, so future maintainers understand the trade-offs. ✔

**Document 4 frozen as Version 1.0 — authoritative API contract for the project.**

---

*End of Document 4 — API Design Specification (Version 1.0, FROZEN). Awaiting owner approval before
generating Document 5 (Queue & Scheduler Design).*




