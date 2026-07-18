# Database Design
### Self-Hosted WhatsApp Business Platform

| | |
|---|---|
| **Document** | 3 of 8 — Database Design (authoritative DB specification) |
| **Version** | 1.1 — **FROZEN** (final additive pass: §21 Business Event Ledger & Enterprise Event Taxonomy) |
| **Date** | 2026-07-15 |
| **Status** | ✅ Approved & frozen — do not edit; record changes in `CHANGELOG.md` |
| **Engine** | MySQL 8.0+ (InnoDB), `utf8mb4` / `utf8mb4_0900_ai_ci` |
| **Preceded by** | Doc 1 — SRS (frozen), Doc 2 — Feature Matrix (frozen) |
| **Followed by** | Doc 4 — API Design |

> This document is the **single source of truth for the database**. Every table, column,
> type, key, constraint, index, partition, and retention rule is specified here. Later
> Alembic migrations implement exactly this. DDL shown is MySQL 8 and is specification, not
> application code. Scale targets: **1M+ contacts, 10M+ messages, 100M+ delivery logs**,
> multi-WABA / multi-number, and years of analytics — with **no schema redesign** to add the
> future modules named in the SRS.

---

## 1. Design conventions & standards

These apply to **every** table unless a table's notes state an exception.

### 1.1 Naming conventions
- **Tables:** `snake_case`, **plural** (`contacts`, `campaign_recipients`).
- **Columns:** `snake_case`, singular. Booleans prefixed `is_`/`has_` (`is_active`).
- **Primary key:** `id`. **Foreign keys:** `<referent_singular>_id` (`contact_id`).
- **Indexes:** `ix_<table>_<cols>`; **unique:** `uq_<table>_<cols>`; **FK:** `fk_<table>_<referent>`;
  **check:** `ck_<table>_<rule>`. **Junction tables:** `<a>_<b>` alphabetical (`role_permissions`).
- **Timestamps:** `*_at` (DATETIME). **Enums/status:** stored as short `VARCHAR` + `CHECK` (see 1.4).

### 1.2 Primary keys & identifiers (two-key strategy)
Every core entity carries **two** identifiers:

| Column | Type | Purpose |
|---|---|---|
| `id` | `BIGINT UNSIGNED AUTO_INCREMENT` | Internal PK / FK joins. Compact (8 bytes), range-friendly, ideal for 10M+ rows and partitioning. |
| `uuid` | `BINARY(16)` (UUIDv7) | Public/external identifier used in APIs & URLs. **UUIDv7 is time-ordered**, so it indexes well (unlike UUIDv4) and never exposes row counts or sequence. |

Rationale: sequential `BIGINT` keeps indexes small and joins fast; a **UUIDv7** public id avoids
enumeration attacks and keeps internal ids out of the API. UUIDs are stored as `BINARY(16)` (16 bytes
vs 36 for text) with app-side encode/decode.

### 1.3 Timestamp strategy
- All time columns are **UTC**, `DATETIME(6)` (microsecond precision).
- Standard audit timestamps on mutable entities:
  - `created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)`
  - `updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)`
- We store UTC only; timezone conversion is a presentation concern (per-user tz in `users`).

### 1.4 Enums / status columns
- Stored as `VARCHAR(32)` + a `CHECK` constraint listing allowed values, **not** MySQL `ENUM`.
  Reason: `ENUM` changes require an `ALTER TABLE` (locking on huge tables) and are brittle for
  future-proofing; `VARCHAR + CHECK` is extensible (a check can be relaxed cheaply) and readable.
- Large, evolving, or user-managed sets use a **lookup table** (e.g., `permissions`, `tags`).

### 1.5 Soft delete strategy
- Soft-deletable tables have `deleted_at DATETIME(6) NULL` (`NULL` = active). Repositories filter
  `deleted_at IS NULL` by default.
- **Uniqueness with soft delete:** MySQL unique indexes treat multiple `NULL`s as distinct, and a
  plain `UNIQUE(natural_key)` would block reuse of a deleted key. Our convention: the **soft-delete
  routine anonymizes conflicting natural-unique columns** (e.g., `email → email + '#deleted#' + id`),
  so a simple `UNIQUE(natural_key)` correctly enforces uniqueness among **active** rows while
  freeing the key for reuse. This is applied consistently and documented per affected table.
- **High-volume append-only tables are never soft-deleted** — they are time-partitioned and pruned
  by dropping whole partitions (see §Partitioning). They carry no `deleted_at`.

### 1.6 Audit fields
- Mutable business entities carry `created_by BIGINT UNSIGNED NULL` and `updated_by BIGINT UNSIGNED NULL`
  referencing `users.id` (`NULL` = system/automated). These are **indexed** where audit queries are expected.
- Independent, immutable `audit_logs` (§Ops) records every mutation regardless of these columns.

### 1.7 Versioning strategy
- **Optimistic concurrency:** mutable entities that can be edited concurrently carry
  `row_version INT UNSIGNED NOT NULL DEFAULT 0`; the app increments and checks it on update to
  prevent lost updates.
- **Domain versioning:** where history matters (message templates), an explicit
  `*_versions` table stores immutable prior versions (see `template_versions`).

### 1.8 Referential integrity & cascade rules
- **Non-partitioned tables** use real `FOREIGN KEY` constraints (InnoDB).
- **Cascade policy:**
  - `ON DELETE CASCADE` for **owned children** whose existence is meaningless without the parent
    (e.g., `role_permissions` → `roles`, `contact_tags` → `contacts`).
  - `ON DELETE RESTRICT` (default) for **references that must not orphan silently** (e.g., a template
    referenced by campaigns).
  - `ON DELETE SET NULL` for **optional links** (e.g., `messages.campaign_id` when a campaign is purged
    but message history is retained).
- **Partitioned tables cannot have FK constraints** (MySQL restriction). For those, referential
  integrity is enforced in the service layer, and FK columns are **indexed** exactly as if constrained.
  Each such table's notes flag this explicitly.

### 1.9 Common column set (illustrative)
Most core entities include: `id`, `uuid`, business columns, `created_at`, `updated_at`,
`created_by`, `updated_by`, `row_version`, and (if soft-deletable) `deleted_at`.

---

## 2. Storage strategy — what lives where

| Store | Holds | Never holds |
|---|---|---|
| **MySQL (InnoDB)** | All durable business data: identity, contacts, templates (metadata), campaigns, the **message ledger**, delivery/status history, conversations, audit/system logs, settings, job metadata. **The source of truth.** | Large binary blobs (media bytes); ephemeral cache; per-request rate-limit counters; transient queue payloads. |
| **Redis** | Celery broker/result backend; app cache (dashboards, rate-limit counters, sessions hints); real-time pub/sub for the inbox/dashboard; **transient** campaign send-queue payloads; distributed locks/idempotency short-TTL keys. | **Anything that must survive a restart as the source of truth.** Redis is treated as rebuildable (per `NFR-DR-06`). Durable campaign progress lives in MySQL (`campaign_recipients` + `campaign_batches`), not Redis. |
| **Object storage** (local volume by default, S3-compatible optional) | Media **bytes** (images/video/docs/audio), export files, backup archives. MySQL stores only **metadata + a storage reference/URL**. | Structured/queryable data. |

**Key rules**
- **Media bytes never go in MySQL** — only a `media_assets` metadata row + object-storage key
  (`FR-MED-06`). Blobs in InnoDB bloat the buffer pool and backups.
- **Rate-limit counters never go in MySQL** — they are high-churn and belong in Redis (with atomic
  INCR + TTL). MySQL stores only the rate-limit **policy/config** and IP allow/block **rules**.
- **Durable truth never lives only in Redis** — campaign checkpoints, message ledger, and status
  history are always in MySQL so a Redis flush loses nothing (`NFR-DR-06/07`).

---

## 3. Entity-Relationship overview (core)

High-level ERD of the core transactional entities (full column detail in §4+). Lookup, ops,
and AI tables are omitted here for readability and specified in their sections.

```mermaid
erDiagram
    ORGANIZATIONS ||--o{ USERS : has
    ORGANIZATIONS ||--o{ WHATSAPP_BUSINESS_ACCOUNTS : owns
    WHATSAPP_BUSINESS_ACCOUNTS ||--o{ PHONE_NUMBERS : contains
    WHATSAPP_BUSINESS_ACCOUNTS ||--o{ MESSAGE_TEMPLATES : owns

    USERS ||--o{ USER_ROLES : assigned
    ROLES ||--o{ USER_ROLES : grants
    ROLES ||--o{ ROLE_PERMISSIONS : has
    PERMISSIONS ||--o{ ROLE_PERMISSIONS : in
    USERS ||--o{ REFRESH_TOKENS : holds
    USERS ||--o{ USER_SESSIONS : opens
    USERS ||--o{ API_KEYS : issues

    ORGANIZATIONS ||--o{ CONTACTS : owns
    CONTACTS ||--o{ CONTACT_TAGS : labeled
    TAGS ||--o{ CONTACT_TAGS : applies
    CONTACTS ||--o{ CONTACT_ATTRIBUTE_VALUES : has
    CUSTOM_ATTRIBUTE_DEFINITIONS ||--o{ CONTACT_ATTRIBUTE_VALUES : defines
    SEGMENTS ||--o{ SEGMENT_RULES : composed_of

    CAMPAIGNS ||--o{ CAMPAIGN_RECIPIENTS : targets
    CAMPAIGNS ||--o| CAMPAIGN_SCHEDULES : scheduled_by
    CAMPAIGNS }o--|| MESSAGE_TEMPLATES : uses
    CAMPAIGNS }o--|| PHONE_NUMBERS : sends_from
    CAMPAIGN_RECIPIENTS }o--|| CONTACTS : to
    CAMPAIGN_RECIPIENTS }o--o| MESSAGES : produced

    PHONE_NUMBERS ||--o{ CONVERSATIONS : hosts
    CONTACTS ||--o{ CONVERSATIONS : with
    CONVERSATIONS ||--o{ MESSAGES : contains
    MESSAGES ||--o{ MESSAGE_STATUS_HISTORY : tracked_by
    CONVERSATIONS ||--o{ INTERNAL_NOTES : annotated
    PHONE_NUMBERS ||--o{ WEBHOOK_EVENTS : receives
```

> **Reading it:** an **Organization** owns users, WABAs, and contacts. Each **WABA** contains
> **phone numbers** and **templates**. **Campaigns** send a template from a number to a set of
> **recipients**; each recipient that is actually sent produces a **message**, whose delivery is
> tracked in **message_status_history**. Inbound and outbound messages roll up into **conversations**.

---

## 4. Domain: Identity & Access (Phase 1)

### 4.1 `organizations`
Single-tenant today, but every scoped table carries `organization_id` so multi-workspace or
business-unit separation is possible **without redesign** (future-proofing, SRS §2.1 / NFR-EXT).

```sql
CREATE TABLE organizations (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid          BINARY(16)      NOT NULL,
  name          VARCHAR(160)    NOT NULL,
  slug          VARCHAR(80)     NOT NULL,
  timezone      VARCHAR(64)     NOT NULL DEFAULT 'UTC',
  default_locale VARCHAR(10)    NOT NULL DEFAULT 'en',
  settings_json JSON            NULL,
  is_active     TINYINT(1)      NOT NULL DEFAULT 1,
  created_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  deleted_at    DATETIME(6)     NULL,
  row_version   INT UNSIGNED    NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uq_organizations_uuid (uuid),
  UNIQUE KEY uq_organizations_slug (slug)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```
*Rows:* tiny (1–few). *Growth:* negligible. *Indexes:* uuid, slug unique. *Retention:* permanent.

### 4.2 `users`
```sql
CREATE TABLE users (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid            BINARY(16)      NOT NULL,
  organization_id BIGINT UNSIGNED NOT NULL,
  email           VARCHAR(255)    NOT NULL,
  password_hash   VARCHAR(255)    NOT NULL,           -- Argon2id encoded string
  full_name       VARCHAR(160)    NOT NULL,
  phone           VARCHAR(32)     NULL,
  avatar_url      VARCHAR(512)    NULL,
  timezone        VARCHAR(64)     NOT NULL DEFAULT 'UTC',
  locale          VARCHAR(10)     NOT NULL DEFAULT 'en',
  is_active       TINYINT(1)      NOT NULL DEFAULT 1,
  is_superuser    TINYINT(1)      NOT NULL DEFAULT 0, -- Owner bypass (FR-AUTH-06)
  mfa_enabled     TINYINT(1)      NOT NULL DEFAULT 0,
  mfa_secret_enc  VARBINARY(255)  NULL,               -- encrypted TOTP secret (FR-AUTH-10)
  failed_logins   SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  locked_until    DATETIME(6)     NULL,               -- lockout (FR-AUTH-04)
  last_login_at   DATETIME(6)     NULL,
  password_changed_at DATETIME(6) NULL,
  created_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  created_by      BIGINT UNSIGNED NULL,
  updated_by      BIGINT UNSIGNED NULL,
  deleted_at      DATETIME(6)     NULL,
  row_version     INT UNSIGNED    NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_uuid (uuid),
  UNIQUE KEY uq_users_email (email),                  -- soft-delete anonymizes email (see §1.5)
  KEY ix_users_org (organization_id),
  KEY ix_users_active (organization_id, is_active),
  CONSTRAINT fk_users_org FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```
*Rows:* tens–hundreds. *Query patterns:* login by `email`; list active by org. *Indexes:* unique email/uuid; `(org, is_active)`. *Retention:* permanent (soft delete). *Security:* `password_hash` Argon2id; `mfa_secret_enc` encrypted at rest (NFR-SEC-08).

### 4.3 `roles`, `permissions`, `role_permissions`, `user_roles`
RBAC is **many-to-many** both ways: users↔roles and roles↔permissions (FR-AUTH-05).

```sql
CREATE TABLE roles (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid            BINARY(16)      NOT NULL,
  organization_id BIGINT UNSIGNED NOT NULL,
  name            VARCHAR(80)     NOT NULL,
  description     VARCHAR(255)    NULL,
  is_system       TINYINT(1)      NOT NULL DEFAULT 0,  -- preset roles cannot be deleted
  created_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  deleted_at      DATETIME(6)     NULL,
  row_version     INT UNSIGNED    NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uq_roles_uuid (uuid),
  UNIQUE KEY uq_roles_org_name (organization_id, name),
  CONSTRAINT fk_roles_org FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE permissions (
  id          INT UNSIGNED   NOT NULL AUTO_INCREMENT,
  code        VARCHAR(64)    NOT NULL,   -- 'contacts:read', 'campaigns:send'
  resource    VARCHAR(40)    NOT NULL,
  action      VARCHAR(24)    NOT NULL,
  description VARCHAR(255)   NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_permissions_code (code),
  KEY ix_permissions_resource (resource)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
-- Lookup/seed table: fixed catalog of granular permissions, seeded at deploy.

CREATE TABLE role_permissions (
  role_id       BIGINT UNSIGNED NOT NULL,
  permission_id INT UNSIGNED    NOT NULL,
  PRIMARY KEY (role_id, permission_id),               -- composite PK (junction)
  KEY ix_rp_permission (permission_id),
  CONSTRAINT fk_rp_role FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE,
  CONSTRAINT fk_rp_perm FOREIGN KEY (permission_id) REFERENCES permissions (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE user_roles (
  user_id    BIGINT UNSIGNED NOT NULL,
  role_id    BIGINT UNSIGNED NOT NULL,
  assigned_at DATETIME(6)    NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  assigned_by BIGINT UNSIGNED NULL,
  PRIMARY KEY (user_id, role_id),                     -- composite PK (junction)
  KEY ix_ur_role (role_id),
  CONSTRAINT fk_ur_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
  CONSTRAINT fk_ur_role FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```
*Rows:* roles ~tens; permissions ~hundreds (seeded); junctions small. *Query:* resolve a user's
effective permissions (join user→roles→permissions), cached in Redis per session. *Cascade:*
deleting a role removes its junction rows; permissions are RESTRICT-protected via seed.

### 4.4 `refresh_tokens`, `user_sessions`, `api_keys`, `password_reset_tokens`
```sql
CREATE TABLE refresh_tokens (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid         BINARY(16)      NOT NULL,
  user_id      BIGINT UNSIGNED NOT NULL,
  token_hash   CHAR(64)        NOT NULL,   -- SHA-256 of the token; raw token never stored
  jti          CHAR(36)        NOT NULL,   -- JWT id embedded in the access token family
  parent_id    BIGINT UNSIGNED NULL,       -- rotation lineage (detect reuse)
  user_agent   VARCHAR(255)    NULL,
  ip_address   VARBINARY(16)   NULL,       -- packed IPv4/IPv6
  expires_at   DATETIME(6)     NOT NULL,
  revoked_at   DATETIME(6)     NULL,       -- server-side revocation (FR-AUTH-03)
  created_at   DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_rt_uuid (uuid),
  UNIQUE KEY uq_rt_token_hash (token_hash),
  KEY ix_rt_user_active (user_id, revoked_at, expires_at),
  KEY ix_rt_jti (jti),
  CONSTRAINT fk_rt_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE user_sessions (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid         BINARY(16)      NOT NULL,
  user_id      BIGINT UNSIGNED NOT NULL,
  refresh_token_id BIGINT UNSIGNED NULL,
  ip_address   VARBINARY(16)   NULL,
  user_agent   VARCHAR(255)    NULL,
  last_seen_at DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  created_at   DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  revoked_at   DATETIME(6)     NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_sessions_uuid (uuid),
  KEY ix_sessions_user (user_id, revoked_at),
  CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
-- Supports "log out all sessions" and the per-user device list (NFR-SEC-06).

CREATE TABLE api_keys (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid         BINARY(16)      NOT NULL,
  organization_id BIGINT UNSIGNED NOT NULL,
  name         VARCHAR(120)    NOT NULL,
  key_prefix   CHAR(12)        NOT NULL,   -- shown in UI to identify the key
  key_hash     CHAR(64)        NOT NULL,   -- SHA-256 of the secret; secret shown once
  scopes_json  JSON            NULL,       -- permission scopes for this key
  created_by   BIGINT UNSIGNED NULL,
  last_used_at DATETIME(6)     NULL,
  expires_at   DATETIME(6)     NULL,
  revoked_at   DATETIME(6)     NULL,
  created_at   DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_apikeys_uuid (uuid),
  UNIQUE KEY uq_apikeys_hash (key_hash),
  KEY ix_apikeys_org (organization_id, revoked_at),
  CONSTRAINT fk_apikeys_org FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE password_reset_tokens (
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id    BIGINT UNSIGNED NOT NULL,
  token_hash CHAR(64)        NOT NULL,
  expires_at DATETIME(6)     NOT NULL,
  used_at    DATETIME(6)     NULL,
  created_at DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_prt_hash (token_hash),
  KEY ix_prt_user (user_id),
  CONSTRAINT fk_prt_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```
*Security notes:* raw tokens/keys/secrets are **never** stored — only SHA-256 hashes; the plaintext
is shown once. `ip_address` is packed `VARBINARY(16)` (holds IPv4 & IPv6). Expired rows are pruned by
a scheduled cleanup job (§Retention). Token **rotation reuse detection** uses `parent_id` lineage.

---

## 5. Domain: WhatsApp Infrastructure (Phase 4)

### 5.1 `whatsapp_business_accounts` (WABA)
```sql
CREATE TABLE whatsapp_business_accounts (
  id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid               BINARY(16)      NOT NULL,
  organization_id    BIGINT UNSIGNED NOT NULL,
  waba_id            VARCHAR(32)     NOT NULL,   -- Meta WABA id
  business_name      VARCHAR(160)    NOT NULL,
  meta_business_id   VARCHAR(32)     NULL,
  access_token_enc   VARBINARY(1024) NOT NULL,   -- encrypted system-user token (FR-WA-03)
  token_expires_at   DATETIME(6)     NULL,
  webhook_verify_token_enc VARBINARY(255) NULL,
  currency           CHAR(3)         NULL,       -- billing currency for cost engine
  timezone           VARCHAR(64)     NULL,
  status             VARCHAR(32)     NOT NULL DEFAULT 'active',
  created_at         DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at         DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  created_by         BIGINT UNSIGNED NULL,
  updated_by         BIGINT UNSIGNED NULL,
  deleted_at         DATETIME(6)     NULL,
  row_version        INT UNSIGNED    NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uq_waba_uuid (uuid),
  UNIQUE KEY uq_waba_metaid (waba_id),
  KEY ix_waba_org (organization_id),
  CONSTRAINT fk_waba_org FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE RESTRICT,
  CONSTRAINT ck_waba_status CHECK (status IN ('active','suspended','disabled'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```
*Rows:* few–dozens. *Security:* tokens stored **encrypted** (`VARBINARY`, app-side AES-GCM via KMS key). *Multi-WABA* is first-class (FR-WA-01).

### 5.2 `phone_numbers`
Carries a `channel_type` for **omnichannel readiness** (default `whatsapp`) — Instagram/Messenger
numbers can be added later without schema change (NFR-EXT-02).

```sql
CREATE TABLE phone_numbers (
  id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid               BINARY(16)      NOT NULL,
  organization_id    BIGINT UNSIGNED NOT NULL,
  waba_id            BIGINT UNSIGNED NOT NULL,      -- FK to whatsapp_business_accounts.id
  channel_type       VARCHAR(24)     NOT NULL DEFAULT 'whatsapp',
  phone_number_id    VARCHAR(32)     NOT NULL,      -- Meta phone_number_id
  display_number     VARCHAR(24)     NOT NULL,      -- E.164
  verified_name      VARCHAR(160)    NULL,
  quality_rating     VARCHAR(8)      NULL,          -- GREEN/YELLOW/RED (FR-WA-04)
  messaging_tier     VARCHAR(16)     NULL,          -- TIER_1K/10K/100K/UNLIMITED
  mps_limit          SMALLINT UNSIGNED NOT NULL DEFAULT 80, -- messages/sec throttle target
  status             VARCHAR(32)     NOT NULL DEFAULT 'connected',
  is_default         TINYINT(1)      NOT NULL DEFAULT 0,
  throughput_level   VARCHAR(16)     NULL,
  last_synced_at     DATETIME(6)     NULL,
  created_at         DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at         DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  created_by         BIGINT UNSIGNED NULL,
  updated_by         BIGINT UNSIGNED NULL,
  deleted_at         DATETIME(6)     NULL,
  row_version        INT UNSIGNED    NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uq_phone_uuid (uuid),
  UNIQUE KEY uq_phone_metaid (phone_number_id),
  KEY ix_phone_waba (waba_id),
  KEY ix_phone_org (organization_id, channel_type),
  CONSTRAINT fk_phone_waba FOREIGN KEY (waba_id) REFERENCES whatsapp_business_accounts (id) ON DELETE CASCADE,
  CONSTRAINT fk_phone_org FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE RESTRICT,
  CONSTRAINT ck_phone_quality CHECK (quality_rating IN ('GREEN','YELLOW','RED') OR quality_rating IS NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```
*Rows:* few–dozens. *Query:* by `phone_number_id` on inbound webhook routing; list by org/waba. *FR-WA-02/04/13*.

---

## 6. Domain: Contacts & Segmentation (Phase 3)

### 6.1 `contacts` — the first large table (1M+)
```sql
CREATE TABLE contacts (
  id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid               BINARY(16)      NOT NULL,
  organization_id    BIGINT UNSIGNED NOT NULL,
  wa_id              VARCHAR(24)     NOT NULL,      -- normalized E.164 (no '+'), the WhatsApp id
  phone_e164         VARCHAR(24)     NOT NULL,      -- '+' formatted for display
  country_code       CHAR(2)         NULL,
  full_name          VARCHAR(160)    NULL,
  first_name         VARCHAR(80)     NULL,
  last_name          VARCHAR(80)     NULL,
  email              VARCHAR(255)    NULL,
  locale             VARCHAR(10)     NULL,
  profile_name       VARCHAR(160)    NULL,          -- name from WhatsApp profile
  opt_in_status      VARCHAR(16)     NOT NULL DEFAULT 'unknown',
  opt_in_at          DATETIME(6)     NULL,
  opt_out_at         DATETIME(6)     NULL,
  is_active_on_wa    TINYINT(1)      NULL,          -- webhook-based active detection (FR-WA-09)
  last_inbound_at    DATETIME(6)     NULL,          -- drives 24h window + active detection
  last_outbound_at   DATETIME(6)     NULL,
  last_contacted_at  DATETIME(6)     NULL,
  source             VARCHAR(40)     NULL,          -- import/manual/webhook/api
  attributes_cache   JSON            NULL,          -- denormalized hot attributes (see §Normalization)
  created_at         DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at         DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  created_by         BIGINT UNSIGNED NULL,
  updated_by         BIGINT UNSIGNED NULL,
  deleted_at         DATETIME(6)     NULL,
  row_version        INT UNSIGNED    NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uq_contacts_uuid (uuid),
  UNIQUE KEY uq_contacts_org_waid (organization_id, wa_id),  -- dedup key (FR-CON-06)
  KEY ix_contacts_org_created (organization_id, created_at),
  KEY ix_contacts_org_optin (organization_id, opt_in_status),
  KEY ix_contacts_last_inbound (organization_id, last_inbound_at),
  KEY ix_contacts_email (email),
  KEY ix_contacts_name (organization_id, full_name),
  CONSTRAINT fk_contacts_org FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE RESTRICT,
  CONSTRAINT ck_contacts_optin CHECK (opt_in_status IN ('unknown','opted_in','opted_out'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```
*Rows:* **1M+**. *Growth:* thousands/week via imports & inbound. *Query patterns:* dedup by
`(org, wa_id)`; paginated lists ordered by `created_at`; segment filters on opt-in / attributes /
tags; search by name/phone/email. *Indexes:* composite `(org, created_at)` for keyset pagination,
`(org, opt_in_status)` and `(org, last_inbound_at)` for segmentation, name/email for search.
*Partitioning:* **not partitioned** (1M rows fit comfortably in one InnoDB table with good indexes;
partitioning contacts would complicate the many FKs pointing at it). *Retention:* permanent;
soft-deleted with email/wa_id anonymization on hard-erase (FR-DL-08). *Denormalization:*
`attributes_cache` JSON mirrors the hottest custom attributes for fast list rendering & simple
filters — the normalized source of truth remains `contact_attribute_values` (justified in §Normalization).

### 6.2 `tags` & `contact_tags` (M:N)
```sql
CREATE TABLE tags (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid            BINARY(16)      NOT NULL,
  organization_id BIGINT UNSIGNED NOT NULL,
  name            VARCHAR(60)     NOT NULL,
  color           CHAR(7)         NULL,             -- '#RRGGBB'
  description     VARCHAR(255)    NULL,
  usage_count     INT UNSIGNED    NOT NULL DEFAULT 0, -- denormalized counter (maintained by triggers/app)
  created_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  created_by      BIGINT UNSIGNED NULL,
  deleted_at      DATETIME(6)     NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_tags_uuid (uuid),
  UNIQUE KEY uq_tags_org_name (organization_id, name),
  CONSTRAINT fk_tags_org FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE contact_tags (
  contact_id  BIGINT UNSIGNED NOT NULL,
  tag_id      BIGINT UNSIGNED NOT NULL,
  tagged_at   DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  tagged_by   BIGINT UNSIGNED NULL,
  PRIMARY KEY (contact_id, tag_id),                 -- composite PK
  KEY ix_ct_tag (tag_id, contact_id),               -- reverse lookup: contacts with tag X
  CONSTRAINT fk_ct_contact FOREIGN KEY (contact_id) REFERENCES contacts (id) ON DELETE CASCADE,
  CONSTRAINT fk_ct_tag FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```
*Rows:* `contact_tags` can reach many millions (1M contacts × several tags). *Indexes:* the
**reverse index** `(tag_id, contact_id)` is essential to resolve "all contacts with tag X" for
segments/campaigns. *Unlimited tags* (FR-CON-09).

### 6.3 Custom attributes — `custom_attribute_definitions` + `contact_attribute_values` (EAV)
```sql
CREATE TABLE custom_attribute_definitions (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid            BINARY(16)      NOT NULL,
  organization_id BIGINT UNSIGNED NOT NULL,
  key_name        VARCHAR(60)     NOT NULL,         -- machine name
  label           VARCHAR(120)    NOT NULL,
  data_type       VARCHAR(16)     NOT NULL,         -- string/number/datetime/boolean/enum
  enum_values_json JSON           NULL,             -- for data_type='enum'
  is_indexed      TINYINT(1)      NOT NULL DEFAULT 0, -- promote to attributes_cache/hot index
  is_pii          TINYINT(1)      NOT NULL DEFAULT 0,
  created_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  deleted_at      DATETIME(6)     NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_cad_uuid (uuid),
  UNIQUE KEY uq_cad_org_key (organization_id, key_name),
  CONSTRAINT fk_cad_org FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
  CONSTRAINT ck_cad_type CHECK (data_type IN ('string','number','datetime','boolean','enum'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE contact_attribute_values (
  id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  contact_id     BIGINT UNSIGNED NOT NULL,
  attribute_id   BIGINT UNSIGNED NOT NULL,
  value_string   VARCHAR(1024)   NULL,
  value_number   DECIMAL(20,6)   NULL,
  value_datetime DATETIME(6)     NULL,
  value_boolean  TINYINT(1)      NULL,
  updated_at     DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_cav_contact_attr (contact_id, attribute_id),   -- one value per attr per contact
  KEY ix_cav_attr_string (attribute_id, value_string(191)),    -- indexed attribute filtering
  KEY ix_cav_attr_number (attribute_id, value_number),
  KEY ix_cav_attr_datetime (attribute_id, value_datetime),
  CONSTRAINT fk_cav_contact FOREIGN KEY (contact_id) REFERENCES contacts (id) ON DELETE CASCADE,
  CONSTRAINT fk_cav_attr FOREIGN KEY (attribute_id) REFERENCES custom_attribute_definitions (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```
*Design:* **EAV with typed value columns** gives unlimited, strongly-typed, **indexable** custom
attributes (FR-CON-11) — segment filters like "plan = gold AND ltv > 5000" hit `(attribute_id, value_*)`
indexes. Hot attributes (`is_indexed=1`) are additionally mirrored into `contacts.attributes_cache`
for fast list rendering. *Rows:* up to 1M contacts × N attributes (potentially tens of millions);
indexed by attribute for scalable filtering.

### 6.4 `segments` + `segment_rules`
A segment is a **saved, dynamic filter**. Rules are normalized into rows (a rule tree) so they are
inspectable and, where useful, index-assisted; a compiled JSON form is cached for fast evaluation.

```sql
CREATE TABLE segments (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid            BINARY(16)      NOT NULL,
  organization_id BIGINT UNSIGNED NOT NULL,
  name            VARCHAR(120)    NOT NULL,
  description     VARCHAR(255)    NULL,
  match_type      VARCHAR(8)      NOT NULL DEFAULT 'all',  -- all=AND, any=OR (top level)
  compiled_json   JSON            NULL,                    -- cached compiled rule tree
  is_dynamic      TINYINT(1)      NOT NULL DEFAULT 1,      -- dynamic vs static snapshot
  cached_count    INT UNSIGNED    NULL,                    -- last evaluated size (denormalized)
  last_evaluated_at DATETIME(6)   NULL,
  created_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  created_by      BIGINT UNSIGNED NULL,
  deleted_at      DATETIME(6)     NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_segments_uuid (uuid),
  UNIQUE KEY uq_segments_org_name (organization_id, name),
  CONSTRAINT fk_segments_org FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
  CONSTRAINT ck_segments_match CHECK (match_type IN ('all','any'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE segment_rules (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  segment_id   BIGINT UNSIGNED NOT NULL,
  group_index  SMALLINT UNSIGNED NOT NULL DEFAULT 0,   -- rule groups for nested AND/OR
  field_source VARCHAR(24)     NOT NULL,               -- 'contact'|'attribute'|'tag'|'engagement'
  field_key    VARCHAR(60)     NOT NULL,               -- column name or attribute key
  operator     VARCHAR(24)     NOT NULL,               -- eq/neq/gt/lt/contains/in/exists/between...
  value_json   JSON            NULL,
  created_at   DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY ix_segrules_segment (segment_id, group_index),
  CONSTRAINT fk_segrules_segment FOREIGN KEY (segment_id) REFERENCES segments (id) ON DELETE CASCADE,
  CONSTRAINT ck_segrules_source CHECK (field_source IN ('contact','attribute','tag','engagement'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```
*Query:* segment evaluation compiles rules → a parameterized SQL query over `contacts` (+ joins to
`contact_attribute_values` / `contact_tags`). `cached_count` and `compiled_json` are denormalized for
fast display and re-use (justified: avoids re-evaluating a 1M-row filter on every page view).

### 6.5 `contact_events` (activity timeline — partitioned)
```sql
CREATE TABLE contact_events (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  organization_id BIGINT UNSIGNED NOT NULL,
  contact_id    BIGINT UNSIGNED NOT NULL,             -- app-enforced FK (partitioned table)
  event_type    VARCHAR(40)     NOT NULL,             -- message_sent/received/campaign/tag_added/optin...
  ref_type      VARCHAR(24)     NULL,
  ref_id        BIGINT UNSIGNED NULL,
  payload_json  JSON            NULL,
  created_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id, created_at),                        -- partition key must be in PK
  KEY ix_cevents_contact (contact_id, created_at),
  KEY ix_cevents_org_type (organization_id, event_type, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
PARTITION BY RANGE COLUMNS (created_at) (
  PARTITION p2026_07 VALUES LESS THAN ('2026-08-01'),
  PARTITION p2026_08 VALUES LESS THAN ('2026-09-01'),
  PARTITION pmax     VALUES LESS THAN (MAXVALUE)
);
```
*Rows:* tens of millions. *No DB FK* (partitioned) — integrity enforced in the service layer.
*Retention:* rolling (e.g., 24 months) via partition drop. Feeds the contact timeline (FR-CON-14).

---

## 7. Domain: Templates & Media (Phase 5)

### 7.1 `message_templates` + `template_versions`
```sql
CREATE TABLE message_templates (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid            BINARY(16)      NOT NULL,
  organization_id BIGINT UNSIGNED NOT NULL,
  waba_id         BIGINT UNSIGNED NOT NULL,
  meta_template_id VARCHAR(40)    NULL,               -- Meta id once created
  name            VARCHAR(512)    NOT NULL,           -- template name
  language        VARCHAR(10)     NOT NULL,           -- e.g. en_US
  category        VARCHAR(16)     NOT NULL,           -- marketing/utility/authentication
  status          VARCHAR(16)     NOT NULL DEFAULT 'draft', -- draft/pending/approved/rejected/paused/disabled
  rejection_reason VARCHAR(255)   NULL,
  quality_score   VARCHAR(16)     NULL,               -- GREEN/YELLOW/RED (Meta quality)
  components_json JSON            NOT NULL,           -- header/body/footer/buttons + variables
  variable_count  SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  has_media_header TINYINT(1)     NOT NULL DEFAULT 0,
  last_synced_at  DATETIME(6)     NULL,
  created_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  created_by      BIGINT UNSIGNED NULL,
  updated_by      BIGINT UNSIGNED NULL,
  deleted_at      DATETIME(6)     NULL,
  row_version     INT UNSIGNED    NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uq_tpl_uuid (uuid),
  UNIQUE KEY uq_tpl_waba_name_lang (waba_id, name, language),  -- Meta uniqueness (name+language per WABA)
  KEY ix_tpl_org_status (organization_id, status),
  KEY ix_tpl_category (organization_id, category),
  CONSTRAINT fk_tpl_org FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
  CONSTRAINT fk_tpl_waba FOREIGN KEY (waba_id) REFERENCES whatsapp_business_accounts (id) ON DELETE CASCADE,
  CONSTRAINT ck_tpl_category CHECK (category IN ('marketing','utility','authentication')),
  CONSTRAINT ck_tpl_status CHECK (status IN ('draft','pending','approved','rejected','paused','disabled'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE template_versions (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  template_id   BIGINT UNSIGNED NOT NULL,
  version_no    INT UNSIGNED    NOT NULL,
  components_json JSON          NOT NULL,
  category      VARCHAR(16)     NOT NULL,
  status        VARCHAR(16)     NOT NULL,
  created_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  created_by    BIGINT UNSIGNED NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_tplver_template_ver (template_id, version_no),
  CONSTRAINT fk_tplver_template FOREIGN KEY (template_id) REFERENCES message_templates (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```
*Design:* template structure is stored as `components_json` (variable, matches Meta's shape) with a
few **promoted columns** (name/language/category/status) for indexing and filtering. Immutable prior
versions live in `template_versions` (FR-TPL versioning). *Rows:* hundreds. *Unique* on
`(waba, name, language)` mirrors Meta's own uniqueness rule.

### 7.2 `media_assets`
Metadata only; **bytes live in object storage** (§Storage). Dedup by SHA-256 (FR-MED-05).

```sql
CREATE TABLE media_assets (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid            BINARY(16)      NOT NULL,
  organization_id BIGINT UNSIGNED NOT NULL,
  media_type      VARCHAR(16)     NOT NULL,           -- image/video/document/audio/sticker
  mime_type       VARCHAR(100)    NOT NULL,
  file_name       VARCHAR(255)    NULL,
  byte_size       BIGINT UNSIGNED NOT NULL,
  sha256          CHAR(64)        NOT NULL,           -- content hash for dedup
  storage_backend VARCHAR(16)     NOT NULL DEFAULT 'local', -- local/s3
  storage_key     VARCHAR(512)    NOT NULL,           -- object-storage path/key
  width           INT UNSIGNED    NULL,
  height          INT UNSIGNED    NULL,
  duration_sec    INT UNSIGNED    NULL,
  meta_media_id   VARCHAR(64)     NULL,               -- cached Cloud API media id (FR-MED-07)
  meta_media_expires_at DATETIME(6) NULL,
  usage_count     INT UNSIGNED    NOT NULL DEFAULT 0,
  created_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  created_by      BIGINT UNSIGNED NULL,
  deleted_at      DATETIME(6)     NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_media_uuid (uuid),
  UNIQUE KEY uq_media_org_sha (organization_id, sha256),   -- dedup within org
  KEY ix_media_type (organization_id, media_type),
  CONSTRAINT fk_media_org FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
  CONSTRAINT ck_media_type CHECK (media_type IN ('image','video','document','audio','sticker'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

---

## 8. Domain: Campaigns (Phase 6)

### 8.1 `campaigns`
Aggregate counters are **denormalized** onto the campaign for O(1) dashboard reads (justified in
§Normalization); the authoritative per-recipient truth is `campaign_recipients`.

```sql
CREATE TABLE campaigns (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid            BINARY(16)      NOT NULL,
  organization_id BIGINT UNSIGNED NOT NULL,
  name            VARCHAR(160)    NOT NULL,
  phone_number_id BIGINT UNSIGNED NOT NULL,           -- sending number
  template_id     BIGINT UNSIGNED NOT NULL,
  status          VARCHAR(20)     NOT NULL DEFAULT 'draft',
  -- draft/scheduled/queued/running/paused/completed/cancelled/failed
  audience_type   VARCHAR(16)     NOT NULL,           -- segment/tag/list/upload
  audience_ref_json JSON          NULL,               -- segment ids / tag ids / upload ref
  variable_map_json JSON          NULL,               -- template var → contact field/attribute mapping
  total_recipients INT UNSIGNED   NOT NULL DEFAULT 0, -- denormalized counters ↓
  queued_count     INT UNSIGNED   NOT NULL DEFAULT 0,
  sent_count       INT UNSIGNED   NOT NULL DEFAULT 0,
  delivered_count  INT UNSIGNED   NOT NULL DEFAULT 0,
  read_count       INT UNSIGNED   NOT NULL DEFAULT 0,
  failed_count     INT UNSIGNED   NOT NULL DEFAULT 0,
  replied_count    INT UNSIGNED   NOT NULL DEFAULT 0,
  estimated_cost   DECIMAL(14,4)  NULL,               -- cost calculator (FR-CAM-11)
  actual_cost      DECIMAL(14,4)  NOT NULL DEFAULT 0,
  cost_currency    CHAR(3)        NULL,
  send_rate_mps    SMALLINT UNSIGNED NULL,            -- pacing override (FR-CAM-13)
  started_at       DATETIME(6)    NULL,
  completed_at     DATETIME(6)    NULL,
  created_at       DATETIME(6)    NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at       DATETIME(6)    NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  created_by       BIGINT UNSIGNED NULL,
  updated_by       BIGINT UNSIGNED NULL,
  deleted_at       DATETIME(6)    NULL,
  row_version      INT UNSIGNED   NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uq_campaigns_uuid (uuid),
  KEY ix_campaigns_org_status (organization_id, status, created_at),
  KEY ix_campaigns_template (template_id),
  KEY ix_campaigns_number (phone_number_id),
  CONSTRAINT fk_campaigns_org FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE RESTRICT,
  CONSTRAINT fk_campaigns_number FOREIGN KEY (phone_number_id) REFERENCES phone_numbers (id) ON DELETE RESTRICT,
  CONSTRAINT fk_campaigns_template FOREIGN KEY (template_id) REFERENCES message_templates (id) ON DELETE RESTRICT,
  CONSTRAINT ck_campaigns_status CHECK (status IN
    ('draft','scheduled','queued','running','paused','completed','cancelled','failed')),
  CONSTRAINT ck_campaigns_audience CHECK (audience_type IN ('segment','tag','list','upload'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

### 8.2 `campaign_schedules` (1:1-ish with recurring support)
```sql
CREATE TABLE campaign_schedules (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid          BINARY(16)      NOT NULL,
  campaign_id   BIGINT UNSIGNED NOT NULL,
  schedule_type VARCHAR(16)     NOT NULL,             -- one_time/recurring
  run_at        DATETIME(6)     NULL,                 -- one_time (UTC)
  timezone      VARCHAR(64)     NOT NULL DEFAULT 'UTC',
  cron_expr     VARCHAR(120)    NULL,                 -- recurring (FR-CAM-04)
  starts_on     DATE            NULL,
  ends_on       DATE            NULL,
  next_run_at   DATETIME(6)     NULL,                 -- computed next fire (indexed)
  last_run_at   DATETIME(6)     NULL,
  is_active     TINYINT(1)      NOT NULL DEFAULT 1,
  created_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_csched_uuid (uuid),
  KEY ix_csched_next (is_active, next_run_at),        -- beat scans due schedules
  KEY ix_csched_campaign (campaign_id),
  CONSTRAINT fk_csched_campaign FOREIGN KEY (campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE,
  CONSTRAINT ck_csched_type CHECK (schedule_type IN ('one_time','recurring'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

### 8.3 `campaign_recipients` — the delivery log (partitioned, 100M+)
This is the durable **campaign delivery** truth and the checkpoint for resume-interrupted (FR-CAM-09).

```sql
CREATE TABLE campaign_recipients (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  campaign_id     BIGINT UNSIGNED NOT NULL,           -- app-enforced FK (partitioned)
  contact_id      BIGINT UNSIGNED NOT NULL,           -- app-enforced FK
  message_id      BIGINT UNSIGNED NULL,               -- links to messages once sent (nullable)
  wamid           VARCHAR(128)    NULL,               -- WhatsApp message id from Cloud API
  status          VARCHAR(16)     NOT NULL DEFAULT 'pending',
  -- pending/queued/sent/delivered/read/failed/skipped/cancelled
  variables_json  JSON            NULL,               -- resolved per-recipient variables
  error_code      VARCHAR(24)     NULL,               -- Meta error code (failure analysis)
  error_detail    VARCHAR(512)    NULL,
  retry_count     TINYINT UNSIGNED NOT NULL DEFAULT 0,
  cost_amount     DECIMAL(12,6)   NULL,
  batch_id        BIGINT UNSIGNED NULL,               -- checkpoint batch (resume)
  queued_at       DATETIME(6)     NULL,
  sent_at         DATETIME(6)     NULL,
  delivered_at    DATETIME(6)     NULL,
  read_at         DATETIME(6)     NULL,
  failed_at       DATETIME(6)     NULL,
  created_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id, created_at),                        -- partition key in PK
  UNIQUE KEY uq_crecip_campaign_contact (campaign_id, contact_id, created_at), -- 1 send per contact/campaign
  KEY ix_crecip_campaign_status (campaign_id, status),
  KEY ix_crecip_status_created (status, created_at),
  KEY ix_crecip_wamid (wamid),
  KEY ix_crecip_batch (batch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
PARTITION BY RANGE COLUMNS (created_at) (
  PARTITION p2026_07 VALUES LESS THAN ('2026-08-01'),
  PARTITION p2026_08 VALUES LESS THAN ('2026-09-01'),
  PARTITION pmax     VALUES LESS THAN (MAXVALUE)
);
```
*Rows:* **100M+** over time. *No DB FK* (partitioned). *Idempotency:* the unique
`(campaign_id, contact_id, …)` plus `wamid` prevents duplicate sends on retry/resume (FR-CAM-06/08).
*Resume:* `batch_id` + `status` let a restarted worker skip already-sent rows (FR-CAM-09).
*Partitioning:* monthly RANGE on `created_at`; old months archived/dropped (§Retention).

### 8.4 `campaign_batches` (checkpoint) & `campaign_retry_queue`
```sql
CREATE TABLE campaign_batches (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  campaign_id   BIGINT UNSIGNED NOT NULL,
  batch_index   INT UNSIGNED    NOT NULL,
  size          INT UNSIGNED    NOT NULL,
  status        VARCHAR(16)     NOT NULL DEFAULT 'pending', -- pending/in_progress/done/failed
  dispatched_at DATETIME(6)     NULL,
  completed_at  DATETIME(6)     NULL,
  created_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_cbatch_campaign_idx (campaign_id, batch_index),
  KEY ix_cbatch_status (campaign_id, status),
  CONSTRAINT fk_cbatch_campaign FOREIGN KEY (campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE campaign_retry_queue (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  campaign_id     BIGINT UNSIGNED NOT NULL,
  recipient_id    BIGINT UNSIGNED NOT NULL,           -- campaign_recipients.id (app-enforced)
  attempt         TINYINT UNSIGNED NOT NULL DEFAULT 1,
  error_code      VARCHAR(24)     NULL,
  next_attempt_at DATETIME(6)     NOT NULL,           -- backoff schedule (indexed)
  status          VARCHAR(16)     NOT NULL DEFAULT 'pending', -- pending/retrying/exhausted/succeeded
  created_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY ix_cretry_due (status, next_attempt_at),        -- smart-retry scanner
  KEY ix_cretry_campaign (campaign_id),
  CONSTRAINT fk_cretry_campaign FOREIGN KEY (campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```
*Smart retry (FR-CAM-08):* only **retryable** Meta error codes enter this queue; `next_attempt_at`
implements exponential backoff; `attempt` caps retries; exhausted rows mark the recipient failed.
*Note:* the **live send queue** itself is Celery/Redis; these MySQL tables are the **durable**
checkpoint/retry state so nothing is lost on a Redis flush (NFR-DR-06).

### 8.5 `rate_cards` — the pricing authority for estimation (FR-CAM-11)
> **Amendment 2026-07-17 (v1.2).** Added to unblock Phase 6 Step 5. Scope is **pre-send estimation
> only**; see §8.5.5 for what remains deliberately undefined.

FR-CAM-11 and Doc 4 §17/§31 compute from "the rate card" as an existing authority, but no entity
owned it. This is that entity, and nothing more: it answers **one** question — *what does one
message to country X in category Y cost?* — for the estimator to multiply by a count.

#### 8.5.1 Storage model
- **Global, not per-tenant.** Doc 4 §17 states the estimate is Meta's real rate card with **"no
  reseller markup"**, so the same card applies to every organization. The table carries **no
  `organization_id`**: a per-org card would imply markup the API contract forbids, and would let two
  tenants see different "exact" costs for the same send. Per-tenant pricing is **not** in scope.
- **Operator-managed data, not code and not seed.** The platform ships with the table **empty**. No
  default, sample, or bundled rates exist — Doc 12 §53 places Meta's pricing **outside** the frozen
  set, so the codebase must not restate it. An unpopulated card is a normal state that the API
  reports explicitly (§8.5.4), never a condition the engine guesses around.
- **Versioned by effective dating, never mutated in place.** A rate change is a **new row** that
  supersedes the old one; historical rows are retained. Editing a rate in place would silently
  rewrite what past estimates meant.

#### 8.5.2 Schema
```sql
CREATE TABLE rate_cards (
  id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid           BINARY(16)      NOT NULL,
  country_code   CHAR(2)         NOT NULL,            -- ISO-3166-1 alpha-2; matches contacts.country_code
  category       VARCHAR(16)     NOT NULL,            -- marketing/utility/authentication (template categories only)
  unit_price     DECIMAL(12,6)   NOT NULL,            -- per-message price; scale matches messages.cost_amount
  currency       CHAR(3)         NOT NULL,            -- ISO-4217; single-currency invariant (§8.5.3)
  effective_from DATETIME(6)     NOT NULL,            -- UTC; the row applies from this instant
  effective_to   DATETIME(6)     NULL,                -- UTC; NULL = currently in force (open-ended)
  created_at     DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at     DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  created_by     BIGINT UNSIGNED NULL,                -- operator who authored the rate (audit trail)
  PRIMARY KEY (id),
  UNIQUE KEY uq_ratecard_uuid (uuid),
  UNIQUE KEY uq_ratecard_slot (country_code, category, effective_from),  -- one rate per pair per instant
  KEY ix_ratecard_lookup (country_code, category, effective_from, effective_to), -- the estimator's scan
  CONSTRAINT fk_ratecard_author FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL,
  CONSTRAINT ck_ratecard_category CHECK (category IN ('marketing','utility','authentication')),
  CONSTRAINT ck_ratecard_price CHECK (unit_price >= 0),
  CONSTRAINT ck_ratecard_window CHECK (effective_to IS NULL OR effective_to > effective_from)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```
*Rows:* small (hundreds). *Access:* read-mostly, cacheable. *Repository:* a rate-card repository
resolves `(country_code, category, at)` → at most one row, and lists the card for administration.

**`ck_ratecard_category` admits only the three template categories.** `messages.category` also
permits `service` (§9.2), but a campaign always sends a **template**, and `ck_tpl_category` (§7.1)
permits only these three — so `service` is unreachable from an estimate by construction. Pricing for
`service` belongs to the conversation/billing semantics that remain out of scope (§8.5.5).

#### 8.5.3 Resolution & money rules
- **Rate lookup.** For `(country_code, category)` at instant `T`, the applicable row is the one where
  `effective_from <= T` and (`effective_to IS NULL` or `effective_to > T`). `uq_ratecard_slot`
  guarantees at most one.
- **Estimation instant.** An estimate resolves rates at **estimate time** (`now`). It is a
  point-in-time quote, not a promise about send time; a card amended between quote and send changes
  the cost, and reconciling that is out of scope (§8.5.5).
- **Single-currency invariant.** Every row in force at a given instant **MUST** share one `currency`.
  The card is authored in exactly one currency (Meta publishes USD), so an estimate never mixes
  currencies and **no FX conversion exists**. Multi-currency cards and FX are out of scope. This
  resolves the ambiguity between Doc 4 §17's "no reseller markup" (one global card) and the
  per-row `cost_currency` columns: `cost_currency` **records** the card's currency, it does not
  select one.
- **Precision.** `unit_price` is `DECIMAL(12,6)`, matching `messages.cost_amount` and
  `campaign_recipients.cost_amount`. `campaigns.estimated_cost` is `DECIMAL(14,4)`.
- **Rounding policy.** `unit_price × count` is **exact** in decimal (an integer count times a 6-dp
  decimal), so group subtotals are computed and summed at **full precision with no intermediate
  rounding**. The sum is rounded **once**, at the storage boundary, to 4 dp using **ROUND_HALF_UP**,
  to fit `campaigns.estimated_cost`. Rounding per recipient or per group would drift by cents across
  a 250k-recipient send — on the number FR-CAM-11 calls exact.

#### 8.5.4 Country resolution (including `NULL`)
The country dimension is **`contacts.country_code CHAR(2) NULL`** — it is nullable, so a recipient
may have no country.

- A recipient with a non-NULL `country_code` is **resolved** and priced from the card.
- A recipient with `country_code IS NULL` is **unresolved**: it is **not** priced, **not** included
  in `estimated_total`, and reported as an explicit count the caller can see (Doc 4 §17).
- **No derivation from `wa_id`.** Deriving country from the E.164 prefix is **not** specified and
  **MUST NOT** be implemented: prefixes are not 1:1 with countries (`+1` spans the NANP), so it needs
  a prefix→country dataset that no frozen document defines. Deferred.
- **Unresolved recipients are surfaced, never silently dropped.** Excluding them from the total
  while hiding the count would understate the headline number.

#### 8.5.5 Deferred — explicitly out of scope
This amendment covers **pre-send estimation only**. The following remain **undefined and MUST NOT be
implemented or inferred** until a specification defines them:

| Deferred | Status |
|---|---|
| `messages.pricing_model` (PMP/CBP) | Column frozen; **determination rule undefined**. Do not populate. |
| `messages.is_billable` | Column frozen (`DEFAULT 0`); **rule undefined** (free tier, free entry points, service conversations). Do not populate. |
| `messages.cost_amount` / `cost_currency` | Do not populate. |
| `campaign_recipients.cost_amount` | Do not populate. |
| **`campaigns.actual_cost` population** | Do not populate; leave at its `DEFAULT 0`. See rationale below. |
| Meta pricing **webhook payload** | Not specified in Doc 7; **do not parse**. |
| Billing reconciliation (estimated vs actual) | Undefined. |
| Finance reporting / cost analytics | Doc 6 §41 / FR-AN-03 — a later phase. |
| Free tier, per-tenant pricing, reseller markup, FX | Undefined. |

**Rationale — why `actual_cost` stays unset:** `campaigns.actual_cost` must represent the
provider-authoritative charge. Computing it from the local rate card would produce another estimate
rather than the provider's billed amount. Estimated and actual values may legitimately diverge due
to provider pricing rules, discounts, credits, or future pricing changes. Therefore
`campaigns.actual_cost` remains unset until an authoritative provider pricing source and contract
are defined.

---

## 9. Domain: Messaging & Inbox (Phase 4 & 7)

### 9.1 `conversations`
One open thread per (phone_number, contact). Tracks the **24-hour window** (FR-WA-12/INB-06).

```sql
CREATE TABLE conversations (
  id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid               BINARY(16)      NOT NULL,
  organization_id    BIGINT UNSIGNED NOT NULL,
  phone_number_id    BIGINT UNSIGNED NOT NULL,
  contact_id         BIGINT UNSIGNED NOT NULL,
  channel_type       VARCHAR(24)     NOT NULL DEFAULT 'whatsapp', -- omnichannel-ready
  status             VARCHAR(16)     NOT NULL DEFAULT 'open',      -- open/pending/resolved/snoozed
  assigned_user_id   BIGINT UNSIGNED NULL,
  last_message_at    DATETIME(6)     NULL,
  last_inbound_at    DATETIME(6)     NULL,           -- window start
  window_expires_at  DATETIME(6)     NULL,           -- last_inbound_at + 24h (denormalized)
  unread_count       INT UNSIGNED    NOT NULL DEFAULT 0,
  last_message_preview VARCHAR(255)  NULL,           -- denormalized for inbox list
  is_window_open     TINYINT(1)      NOT NULL DEFAULT 0,
  created_at         DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at         DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  deleted_at         DATETIME(6)     NULL,
  row_version        INT UNSIGNED    NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uq_conv_uuid (uuid),
  UNIQUE KEY uq_conv_number_contact (phone_number_id, contact_id),
  KEY ix_conv_org_status (organization_id, status, last_message_at),
  KEY ix_conv_assignee (assigned_user_id, status),
  KEY ix_conv_window (is_window_open, window_expires_at),
  CONSTRAINT fk_conv_org FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE RESTRICT,
  CONSTRAINT fk_conv_number FOREIGN KEY (phone_number_id) REFERENCES phone_numbers (id) ON DELETE CASCADE,
  CONSTRAINT fk_conv_contact FOREIGN KEY (contact_id) REFERENCES contacts (id) ON DELETE CASCADE,
  CONSTRAINT fk_conv_assignee FOREIGN KEY (assigned_user_id) REFERENCES users (id) ON DELETE SET NULL,
  CONSTRAINT ck_conv_status CHECK (status IN ('open','pending','resolved','snoozed'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

### 9.2 `messages` — the Message Ledger (partitioned, 10M+)
**Design decision:** the SRS lists "Messages" and "Message Ledger" separately; we **unify them into
one authoritative `messages` table** (the ledger). A campaign send *is* a message — a second table
would duplicate `wamid`, status, direction, and cost. This is a deliberate anti-duplication choice
(see §Normalization). Cost/pricing fields live here, making `messages` the billing ledger too.

```sql
CREATE TABLE messages (
  id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid             BINARY(16)      NOT NULL,
  organization_id  BIGINT UNSIGNED NOT NULL,
  conversation_id  BIGINT UNSIGNED NOT NULL,          -- app-enforced FK (partitioned)
  phone_number_id  BIGINT UNSIGNED NOT NULL,
  contact_id       BIGINT UNSIGNED NOT NULL,
  campaign_id      BIGINT UNSIGNED NULL,              -- set for campaign sends
  direction        VARCHAR(8)      NOT NULL,          -- inbound/outbound
  wamid            VARCHAR(128)    NULL,              -- WhatsApp message id (unique per partition)
  message_type     VARCHAR(20)     NOT NULL,          -- text/image/video/document/audio/template/interactive/location/contacts/reaction/sticker
  category         VARCHAR(16)     NULL,              -- marketing/utility/authentication/service (billing)
  template_id      BIGINT UNSIGNED NULL,
  content_json     JSON            NULL,              -- body/media ref/interactive payload
  media_asset_id   BIGINT UNSIGNED NULL,
  status           VARCHAR(16)     NOT NULL DEFAULT 'accepted',
  -- accepted/sent/delivered/read/failed (current status; history in message_status_history)
  error_code       VARCHAR(24)     NULL,
  pricing_model    VARCHAR(16)     NULL,              -- PMP/CBP (per-message vs legacy)
  is_billable      TINYINT(1)      NOT NULL DEFAULT 0,
  cost_amount      DECIMAL(12,6)   NULL,
  cost_currency    CHAR(3)         NULL,
  sent_at          DATETIME(6)     NULL,
  delivered_at     DATETIME(6)     NULL,
  read_at          DATETIME(6)     NULL,
  created_at       DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id, created_at),                        -- partition key in PK
  KEY ix_msg_conversation (conversation_id, created_at),
  KEY ix_msg_wamid (wamid),                            -- webhook status lookup by wamid
  KEY ix_msg_org_created (organization_id, created_at),
  KEY ix_msg_campaign (campaign_id),
  KEY ix_msg_contact (contact_id, created_at),
  KEY ix_msg_status (status, created_at),
  CONSTRAINT ck_msg_direction CHECK (direction IN ('inbound','outbound'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
PARTITION BY RANGE COLUMNS (created_at) (
  PARTITION p2026_07 VALUES LESS THAN ('2026-08-01'),
  PARTITION p2026_08 VALUES LESS THAN ('2026-09-01'),
  PARTITION pmax     VALUES LESS THAN (MAXVALUE)
);
```
*Rows:* **10M+**. *No DB FK* (partitioned). *Query patterns:* thread view by `(conversation_id, created_at)`;
webhook status update by `wamid`; analytics by `(org, created_at)` and `campaign_id`. *Cost engine:*
`category`, `is_billable`, `cost_amount` power exact cost analytics (FR-AN-03).

#### 9.2a Reaction payload (Amendment 2026-07-18, v1.4)
> **Append-only confirmation — no schema change.** `message_type` **already** enumerates `reaction`
> (§9.2) and `content_json` already holds per-type payloads, so a reaction needs **no new column and
> no migration** beyond the ledger row itself.

- **`message_type = 'reaction'`** — confirmed in the §9.2 `message_type` list; used for both inbound
  (customer→us, via webhook) and outbound (us→customer, Doc 04 §18.2) reactions.
- **`content_json` reaction format:** `{ "reaction": { "message_id": "<target wamid>", "emoji": "<emoji or empty string>" } }`.
  An empty `emoji` is a **removal**. This mirrors the Meta reaction shape, canonicalised behind the
  adapter (Doc 07 §5.3).
- **Target message reference:** a reaction references its target by the target message's **`wamid`**
  (carried in `content_json.reaction.message_id`) — **not** a new FK or column, consistent with §9.2
  storing message context in `content_json`. The reaction row's own `wamid` is the channel's id for
  the reaction message. The API accepts the target by its public `uuid` and resolves it to the stored
  `wamid` (Doc 04 §18.2 reaction contract).

### 9.3 `message_status_history` — delivery logs (partitioned, 100M+)
Append-only status transitions. Each outbound message yields several rows (sent→delivered→read).

```sql
CREATE TABLE message_status_history (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  message_id    BIGINT UNSIGNED NOT NULL,             -- app-enforced FK (partitioned)
  wamid         VARCHAR(128)    NULL,
  status        VARCHAR(16)     NOT NULL,             -- sent/delivered/read/failed
  error_code    VARCHAR(24)     NULL,
  error_title   VARCHAR(160)    NULL,
  error_detail  VARCHAR(512)    NULL,
  recipient_id  VARCHAR(24)     NULL,
  raw_json      JSON            NULL,
  occurred_at   DATETIME(6)     NOT NULL,             -- Meta timestamp
  created_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id, created_at),
  KEY ix_msh_message (message_id, created_at),
  KEY ix_msh_wamid (wamid),
  KEY ix_msh_status (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
PARTITION BY RANGE COLUMNS (created_at) (
  PARTITION p2026_07 VALUES LESS THAN ('2026-08-01'),
  PARTITION p2026_08 VALUES LESS THAN ('2026-09-01'),
  PARTITION pmax     VALUES LESS THAN (MAXVALUE)
);
```
*Rows:* **100M+**. *Why separate from `messages`:* status is append-only and highest-volume; keeping
it out of `messages` keeps the ledger row small and hot-path updates cheap. Current status is
denormalized onto `messages.status`; full history lives here.

### 9.4 `webhook_events` (partitioned) & `webhook_dead_letter`
Raw inbound webhooks are persisted **first** (durability), acked with `200`, then processed async
and idempotently (FR-WA-05/07).

```sql
CREATE TABLE webhook_events (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  event_id      VARCHAR(128)    NULL,                 -- dedup key when Meta provides one
  phone_number_id BIGINT UNSIGNED NULL,
  object_type   VARCHAR(40)     NULL,                 -- messages/statuses/...
  signature_ok  TINYINT(1)      NOT NULL DEFAULT 0,
  payload_json  JSON            NOT NULL,
  status        VARCHAR(16)     NOT NULL DEFAULT 'received', -- received/processed/failed/duplicate
  processed_at  DATETIME(6)     NULL,
  attempts      TINYINT UNSIGNED NOT NULL DEFAULT 0,
  created_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id, created_at),
  KEY ix_whe_status (status, created_at),
  KEY ix_whe_event (event_id),
  KEY ix_whe_number (phone_number_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
PARTITION BY RANGE COLUMNS (created_at) (
  PARTITION p2026_07 VALUES LESS THAN ('2026-08-01'),
  PARTITION p2026_08 VALUES LESS THAN ('2026-09-01'),
  PARTITION pmax     VALUES LESS THAN (MAXVALUE)
);

CREATE TABLE webhook_dead_letter (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid          BINARY(16)      NOT NULL,
  source_event_id BIGINT UNSIGNED NULL,
  payload_json  JSON            NOT NULL,
  error_detail  VARCHAR(1024)   NULL,
  attempts      TINYINT UNSIGNED NOT NULL DEFAULT 0,
  status        VARCHAR(16)     NOT NULL DEFAULT 'pending', -- pending/replayed/discarded
  created_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  replayed_at   DATETIME(6)     NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_whdl_uuid (uuid),
  KEY ix_whdl_status (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```
*Dead-letter + replay* (FR-WA-08) captures events that fail processing after retries, for manual/
automated replay — no webhook is silently lost.

### 9.5 `quick_replies` & `internal_notes`
```sql
CREATE TABLE quick_replies (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid            BINARY(16)      NOT NULL,
  organization_id BIGINT UNSIGNED NOT NULL,
  owner_user_id   BIGINT UNSIGNED NULL,               -- NULL = shared, else personal (FR-INB-04)
  shortcut        VARCHAR(60)     NOT NULL,           -- '/greeting'
  title           VARCHAR(120)    NOT NULL,
  body            TEXT            NOT NULL,
  usage_count     INT UNSIGNED    NOT NULL DEFAULT 0,
  created_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  created_by      BIGINT UNSIGNED NULL,
  deleted_at      DATETIME(6)     NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_qr_uuid (uuid),
  KEY ix_qr_org_owner (organization_id, owner_user_id),
  CONSTRAINT fk_qr_org FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE internal_notes (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid            BINARY(16)      NOT NULL,
  conversation_id BIGINT UNSIGNED NOT NULL,
  author_user_id  BIGINT UNSIGNED NOT NULL,
  body            TEXT            NOT NULL,
  created_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  deleted_at      DATETIME(6)     NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_note_uuid (uuid),
  KEY ix_note_conversation (conversation_id, created_at),
  CONSTRAINT fk_note_conversation FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE,
  CONSTRAINT fk_note_author FOREIGN KEY (author_user_id) REFERENCES users (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

### 9.6 Click tracking — `short_links` & `link_clicks` (partitioned) (Phase 8)
```sql
CREATE TABLE short_links (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid            BINARY(16)      NOT NULL,
  organization_id BIGINT UNSIGNED NOT NULL,
  code            VARCHAR(16)     NOT NULL,           -- short slug in the public URL
  target_url      VARCHAR(2048)   NOT NULL,
  campaign_id     BIGINT UNSIGNED NULL,
  click_count     INT UNSIGNED    NOT NULL DEFAULT 0, -- denormalized counter
  created_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  expires_at      DATETIME(6)     NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_slink_uuid (uuid),
  UNIQUE KEY uq_slink_code (code),
  KEY ix_slink_campaign (campaign_id),
  CONSTRAINT fk_slink_org FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE link_clicks (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  short_link_id BIGINT UNSIGNED NOT NULL,             -- app-enforced FK (partitioned)
  contact_id    BIGINT UNSIGNED NULL,
  campaign_id   BIGINT UNSIGNED NULL,
  ip_hash       CHAR(64)        NULL,                 -- hashed IP (privacy)
  user_agent    VARCHAR(255)    NULL,
  referrer      VARCHAR(512)    NULL,
  created_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id, created_at),
  KEY ix_clicks_link (short_link_id, created_at),
  KEY ix_clicks_campaign (campaign_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
PARTITION BY RANGE COLUMNS (created_at) (
  PARTITION p2026_07 VALUES LESS THAN ('2026-08-01'),
  PARTITION p2026_08 VALUES LESS THAN ('2026-09-01'),
  PARTITION pmax     VALUES LESS THAN (MAXVALUE)
);
```
*Click/URL tracking (FR-AN-04):* first-party shortener; per-click rows (high volume, partitioned)
with a denormalized `click_count` on `short_links` for instant display.

### 9.7 `conversation_tags` (M:N) (Phase 7)
> **Amendment 2026-07-18 (v1.3).** Adds conversation-level classification for **FR-INB-07**. This is a
> new **junction only**: it **reuses the existing `tags` taxonomy** (§6.2) — no new tag entity, and
> **no change** to `tags` or `contact_tags`. Conversation tags are deliberately distinct from contact
> tags: they classify *this thread* (agent triage — e.g. `refund`, `escalated`), not the person.

```sql
CREATE TABLE conversation_tags (
  conversation_id BIGINT UNSIGNED NOT NULL,
  tag_id          BIGINT UNSIGNED NOT NULL,
  tagged_at       DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  tagged_by       BIGINT UNSIGNED NULL,               -- user who applied it (attribution; no FK, nullable)
  PRIMARY KEY (conversation_id, tag_id),              -- composite PK: a tag applies at most once per thread
  KEY ix_convtag_tag (tag_id, conversation_id),       -- reverse lookup: conversations with tag X (inbox filter)
  CONSTRAINT fk_convtag_conversation FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE,
  CONSTRAINT fk_convtag_tag FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```
*Model:* an exact mirror of `contact_tags` (§6.2) — the proven M:N join pattern — but associating the
shared `tags` taxonomy with **conversations** rather than contacts.
*Keys / indexes:* composite PK `(conversation_id, tag_id)` gives idempotent membership and covers
"tags of conversation X"; the reverse index `(tag_id, conversation_id)` resolves "conversations with
tag X" — the inbox **by-tag** filter — mirroring `ix_ct_tag`.
*Constraints:* both FKs are `ON DELETE CASCADE` — deleting a conversation drops its tag links, and
deleting a tag (§14.2) detaches it from conversations as well as contacts.
*Soft delete:* **none.** Like `contact_tags`, membership is a hard association; removing a tag
hard-deletes the join row. `tagged_at` / `tagged_by` give lightweight attribution (no independent
audit record).
*Ownership & org scoping:* the junction carries **no `organization_id`** (as `contact_tags` carries
none); scope is enforced through **both parents** — the `conversation` and the `tag` are each
org-scoped, and the service **must** verify they belong to the **same** organization before
associating (a cross-org tag is rejected — §18.1). The association is a **shared team**
classification: any `inbox:write` member may add or remove tags on any conversation in the org (no
per-user ownership).

---

## 10. Domain: AI & Knowledge Base (Phase 9)

```sql
CREATE TABLE ai_knowledge_base (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid            BINARY(16)      NOT NULL,
  organization_id BIGINT UNSIGNED NOT NULL,
  title           VARCHAR(255)    NOT NULL,
  source_type     VARCHAR(16)     NOT NULL DEFAULT 'manual', -- manual/file/url
  content         MEDIUMTEXT      NULL,
  status          VARCHAR(16)     NOT NULL DEFAULT 'active',
  created_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  created_by      BIGINT UNSIGNED NULL,
  deleted_at      DATETIME(6)     NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_kb_uuid (uuid),
  KEY ix_kb_org (organization_id, status),
  FULLTEXT KEY ftx_kb_content (title, content),        -- keyword search fallback
  CONSTRAINT fk_kb_org FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE ai_knowledge_chunks (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  kb_id         BIGINT UNSIGNED NOT NULL,
  chunk_index   INT UNSIGNED    NOT NULL,
  content       TEXT            NOT NULL,
  embedding     JSON            NULL,                  -- vector (JSON now; pluggable vector store later)
  token_count   INT UNSIGNED    NULL,
  created_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_kbchunk (kb_id, chunk_index),
  CONSTRAINT fk_kbchunk_kb FOREIGN KEY (kb_id) REFERENCES ai_knowledge_base (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
-- Embeddings stored as JSON now; §Scalability describes swapping to a dedicated vector store.

CREATE TABLE ai_conversations (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid            BINARY(16)      NOT NULL,
  organization_id BIGINT UNSIGNED NOT NULL,
  user_id         BIGINT UNSIGNED NULL,               -- staff user using the assistant
  conversation_id BIGINT UNSIGNED NULL,               -- linked customer conversation (optional)
  purpose         VARCHAR(24)     NOT NULL,           -- suggest_reply/summarize/generate_campaign/translate...
  model           VARCHAR(64)     NULL,
  created_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_aiconv_uuid (uuid),
  KEY ix_aiconv_org (organization_id, created_at),
  CONSTRAINT fk_aiconv_org FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE ai_conversation_messages (
  id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  ai_conversation_id BIGINT UNSIGNED NOT NULL,
  role               VARCHAR(12)     NOT NULL,        -- system/user/assistant/tool
  content            MEDIUMTEXT      NOT NULL,
  tokens_prompt      INT UNSIGNED    NULL,
  tokens_completion  INT UNSIGNED    NULL,
  approved_by        BIGINT UNSIGNED NULL,            -- human approval before send (FR-AI-10)
  approved_at        DATETIME(6)     NULL,
  created_at         DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY ix_aimsg_conv (ai_conversation_id, created_at),
  CONSTRAINT fk_aimsg_conv FOREIGN KEY (ai_conversation_id) REFERENCES ai_conversations (id) ON DELETE CASCADE,
  CONSTRAINT ck_aimsg_role CHECK (role IN ('system','user','assistant','tool'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```
*AI provider abstraction (NFR-EXT-04):* `model` is stored per interaction; provider is config-driven.
*Human-in-the-loop (FR-AI-10):* `approved_by/approved_at` gate any AI content before it becomes a
customer message; drafts without approval never leave the system.

---

## 11. Domain: Administration & Operations (Phase 10)

### 11.1 `notifications`
```sql
CREATE TABLE notifications (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid            BINARY(16)      NOT NULL,
  organization_id BIGINT UNSIGNED NOT NULL,
  user_id         BIGINT UNSIGNED NULL,               -- NULL = org-wide broadcast
  type            VARCHAR(40)     NOT NULL,           -- campaign_done/quality_drop/import_done/...
  severity        VARCHAR(12)     NOT NULL DEFAULT 'info', -- info/warning/critical
  title           VARCHAR(160)    NOT NULL,
  body            VARCHAR(1024)   NULL,
  ref_type        VARCHAR(24)     NULL,
  ref_id          BIGINT UNSIGNED NULL,
  is_read         TINYINT(1)      NOT NULL DEFAULT 0,
  read_at         DATETIME(6)     NULL,
  created_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_notif_uuid (uuid),
  KEY ix_notif_user_unread (user_id, is_read, created_at),
  KEY ix_notif_org (organization_id, created_at),
  CONSTRAINT fk_notif_org FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
  CONSTRAINT ck_notif_sev CHECK (severity IN ('info','warning','critical'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

### 11.2 `audit_logs` (immutable, partitioned)
Tamper-evident record of **every mutation** (FR-ADM-02, NFR-SEC-07). No `updated_at`, no soft delete —
append-only. Optional hash-chain (`prev_hash`/`row_hash`) makes tampering detectable.

```sql
CREATE TABLE audit_logs (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  organization_id BIGINT UNSIGNED NULL,
  actor_user_id BIGINT UNSIGNED NULL,                 -- NULL = system
  actor_type    VARCHAR(12)     NOT NULL DEFAULT 'user', -- user/system/api_key
  action        VARCHAR(60)     NOT NULL,             -- contact.update / campaign.send / user.login
  entity_type   VARCHAR(40)     NULL,
  entity_id     BIGINT UNSIGNED NULL,
  ip_address    VARBINARY(16)   NULL,
  before_json   JSON            NULL,                 -- prior state (diff source)
  after_json    JSON            NULL,                 -- new state
  metadata_json JSON            NULL,
  prev_hash     CHAR(64)        NULL,                 -- hash chain (tamper evidence)
  row_hash      CHAR(64)        NULL,
  created_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id, created_at),
  KEY ix_audit_actor (actor_user_id, created_at),
  KEY ix_audit_entity (entity_type, entity_id, created_at),
  KEY ix_audit_action (action, created_at),
  KEY ix_audit_org (organization_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
PARTITION BY RANGE COLUMNS (created_at) (
  PARTITION p2026_07 VALUES LESS THAN ('2026-08-01'),
  PARTITION p2026_08 VALUES LESS THAN ('2026-09-01'),
  PARTITION pmax     VALUES LESS THAN (MAXVALUE)
);
```
*Rows:* tens of millions. *Retention:* long (e.g., 24–84 months, compliance-driven) via partitioning.

### 11.3 `system_logs` (partitioned) & `error_logs` (partitioned)
`system_logs` = structured operational logs (queryable in-app). `error_logs` = captured exceptions
with stack/context for debugging (kept distinct so error triage isn't diluted by routine logs).

```sql
CREATE TABLE system_logs (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  level         VARCHAR(10)     NOT NULL,             -- debug/info/warning/error/critical
  logger        VARCHAR(120)    NULL,
  event         VARCHAR(120)    NULL,
  message       VARCHAR(2048)   NULL,
  context_json  JSON            NULL,
  request_id    CHAR(36)        NULL,                 -- correlation id
  user_id       BIGINT UNSIGNED NULL,
  created_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id, created_at),
  KEY ix_syslog_level (level, created_at),
  KEY ix_syslog_request (request_id),
  KEY ix_syslog_event (event, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
PARTITION BY RANGE COLUMNS (created_at) (
  PARTITION p2026_07 VALUES LESS THAN ('2026-08-01'),
  PARTITION p2026_08 VALUES LESS THAN ('2026-09-01'),
  PARTITION pmax     VALUES LESS THAN (MAXVALUE)
);

CREATE TABLE error_logs (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  fingerprint   CHAR(40)        NULL,                 -- group identical errors
  exception_type VARCHAR(160)   NULL,
  message       VARCHAR(2048)   NULL,
  stack_trace   MEDIUMTEXT      NULL,
  request_id    CHAR(36)        NULL,
  route         VARCHAR(255)    NULL,
  user_id       BIGINT UNSIGNED NULL,
  context_json  JSON            NULL,
  occurrence_count INT UNSIGNED NOT NULL DEFAULT 1,   -- rolled up by fingerprint
  first_seen_at DATETIME(6)     NULL,
  created_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id, created_at),
  KEY ix_errlog_fingerprint (fingerprint, created_at),
  KEY ix_errlog_type (exception_type, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
PARTITION BY RANGE COLUMNS (created_at) (
  PARTITION p2026_07 VALUES LESS THAN ('2026-08-01'),
  PARTITION p2026_08 VALUES LESS THAN ('2026-09-01'),
  PARTITION pmax     VALUES LESS THAN (MAXVALUE)
);
```

### 11.4 `activity_logs` (user-facing activity feed)
Distinct from `audit_logs` (security/compliance) and `system_logs` (technical): this is the
human-readable "who did what" feed shown in the UI.

```sql
CREATE TABLE activity_logs (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  organization_id BIGINT UNSIGNED NOT NULL,
  user_id       BIGINT UNSIGNED NULL,
  verb          VARCHAR(40)     NOT NULL,             -- created/updated/sent/imported...
  object_type   VARCHAR(40)     NOT NULL,
  object_id     BIGINT UNSIGNED NULL,
  summary       VARCHAR(512)    NULL,
  created_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id, created_at),
  KEY ix_activity_org (organization_id, created_at),
  KEY ix_activity_user (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
PARTITION BY RANGE COLUMNS (created_at) (
  PARTITION p2026_07 VALUES LESS THAN ('2026-08-01'),
  PARTITION p2026_08 VALUES LESS THAN ('2026-09-01'),
  PARTITION pmax     VALUES LESS THAN (MAXVALUE)
);
```

### 11.5 `settings` (typed key/value, scoped)
```sql
CREATE TABLE settings (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  organization_id BIGINT UNSIGNED NULL,               -- NULL = global/system setting
  scope           VARCHAR(24)     NOT NULL DEFAULT 'organization', -- system/organization/user
  scope_id        BIGINT UNSIGNED NULL,               -- e.g. user id for user scope
  key_name        VARCHAR(120)    NOT NULL,
  value_json      JSON            NULL,
  value_type      VARCHAR(16)     NOT NULL DEFAULT 'json',
  is_secret       TINYINT(1)      NOT NULL DEFAULT 0, -- secret values stored encrypted
  updated_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  updated_by      BIGINT UNSIGNED NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_settings_scope_key (scope, scope_id, key_name),
  KEY ix_settings_org (organization_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

### 11.6 `backups`, `exports`, `imports`
```sql
CREATE TABLE backups (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid          BINARY(16)      NOT NULL,
  backup_type   VARCHAR(16)     NOT NULL,             -- full/incremental
  status        VARCHAR(16)     NOT NULL DEFAULT 'running', -- running/success/failed/verified
  storage_key   VARCHAR(512)    NULL,                 -- object-storage location
  byte_size     BIGINT UNSIGNED NULL,
  checksum      CHAR(64)        NULL,
  verified_at   DATETIME(6)     NULL,                 -- test-restore verification (NFR-DR-04)
  started_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  completed_at  DATETIME(6)     NULL,
  error_detail  VARCHAR(1024)   NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_backups_uuid (uuid),
  KEY ix_backups_status (status, started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE exports (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid            BINARY(16)      NOT NULL,
  organization_id BIGINT UNSIGNED NOT NULL,
  requested_by    BIGINT UNSIGNED NULL,
  entity          VARCHAR(40)     NOT NULL,           -- contacts/campaign/report...
  format          VARCHAR(8)      NOT NULL,           -- csv/xlsx/json
  filters_json    JSON            NULL,
  status          VARCHAR(16)     NOT NULL DEFAULT 'pending', -- pending/processing/ready/failed/expired
  row_count       BIGINT UNSIGNED NULL,
  storage_key     VARCHAR(512)    NULL,
  expires_at      DATETIME(6)     NULL,
  created_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  completed_at    DATETIME(6)     NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_exports_uuid (uuid),
  KEY ix_exports_org (organization_id, status, created_at),
  CONSTRAINT fk_exports_org FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE,
  CONSTRAINT ck_exports_format CHECK (format IN ('csv','xlsx','json'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE imports (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid            BINARY(16)      NOT NULL,
  organization_id BIGINT UNSIGNED NOT NULL,
  requested_by    BIGINT UNSIGNED NULL,
  entity          VARCHAR(40)     NOT NULL DEFAULT 'contacts',
  format          VARCHAR(8)      NOT NULL,           -- csv/xlsx
  source_key      VARCHAR(512)    NULL,               -- uploaded file location
  mapping_json    JSON            NULL,               -- column → field mapping
  dedup_strategy  VARCHAR(16)     NULL,               -- skip/merge/overwrite (FR-CON-06)
  status          VARCHAR(16)     NOT NULL DEFAULT 'pending', -- pending/processing/completed/failed
  total_rows      BIGINT UNSIGNED NULL,
  processed_rows  BIGINT UNSIGNED NOT NULL DEFAULT 0,
  success_rows    BIGINT UNSIGNED NOT NULL DEFAULT 0,
  error_rows      BIGINT UNSIGNED NOT NULL DEFAULT 0,
  error_report_key VARCHAR(512)   NULL,               -- downloadable error report
  created_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  completed_at    DATETIME(6)     NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_imports_uuid (uuid),
  KEY ix_imports_org (organization_id, status, created_at),
  CONSTRAINT fk_imports_org FOREIGN KEY (organization_id) REFERENCES organizations (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

### 11.7 `job_metadata` & `monitoring_metrics` (partitioned)
```sql
CREATE TABLE job_metadata (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid          BINARY(16)      NOT NULL,
  task_id       VARCHAR(64)     NOT NULL,             -- Celery task id
  task_name     VARCHAR(160)    NOT NULL,
  queue         VARCHAR(60)     NULL,
  status        VARCHAR(16)     NOT NULL DEFAULT 'queued', -- queued/started/success/failure/retry/revoked
  ref_type      VARCHAR(24)     NULL,                 -- campaign/import/export...
  ref_id        BIGINT UNSIGNED NULL,
  args_json     JSON            NULL,
  result_json   JSON            NULL,
  error_detail  VARCHAR(1024)   NULL,
  attempts      TINYINT UNSIGNED NOT NULL DEFAULT 0,
  started_at    DATETIME(6)     NULL,
  finished_at   DATETIME(6)     NULL,
  created_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_job_uuid (uuid),
  UNIQUE KEY uq_job_taskid (task_id),
  KEY ix_job_status (status, created_at),
  KEY ix_job_ref (ref_type, ref_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
-- Durable mirror of Celery job state (Redis is transient); powers queue/worker monitoring (FR-MON-01/02).

CREATE TABLE monitoring_metrics (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  metric_name   VARCHAR(80)     NOT NULL,             -- queue_depth/api_p95_ms/webhook_lag_ms/...
  label_json    JSON            NULL,                 -- dimensions (queue, endpoint, number)
  value_double  DOUBLE          NOT NULL,
  created_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id, created_at),
  KEY ix_metrics_name (metric_name, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
PARTITION BY RANGE COLUMNS (created_at) (
  PARTITION p2026_07 VALUES LESS THAN ('2026-08-01'),
  PARTITION p2026_08 VALUES LESS THAN ('2026-09-01'),
  PARTITION pmax     VALUES LESS THAN (MAXVALUE)
);
```
*Note:* `monitoring_metrics` is a lightweight time-series for in-app charts; a dedicated TSDB
(Prometheus) can be layered later (Doc 7) — this table keeps history queryable without extra infra.

### 11.8 `rate_limit_policies`, `ip_access_rules`, `feature_flags`
Rate-limit **counters live in Redis**; MySQL stores only durable **policy/config** and IP rules.

```sql
CREATE TABLE rate_limit_policies (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  scope         VARCHAR(24)     NOT NULL,             -- ip/user/api_key/endpoint
  key_pattern   VARCHAR(160)    NOT NULL,             -- e.g. 'POST:/auth/login'
  max_requests  INT UNSIGNED    NOT NULL,
  window_seconds INT UNSIGNED   NOT NULL,
  burst         INT UNSIGNED    NULL,
  is_active     TINYINT(1)      NOT NULL DEFAULT 1,
  created_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_rlp_scope_key (scope, key_pattern)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE ip_access_rules (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  organization_id BIGINT UNSIGNED NULL,
  rule_type     VARCHAR(8)      NOT NULL,             -- allow/block
  cidr          VARCHAR(64)     NOT NULL,             -- IPv4/IPv6 CIDR
  applies_to    VARCHAR(24)     NOT NULL DEFAULT 'all', -- all/admin/webhook/api
  description   VARCHAR(255)    NULL,
  is_active     TINYINT(1)      NOT NULL DEFAULT 1,
  created_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  created_by    BIGINT UNSIGNED NULL,
  PRIMARY KEY (id),
  KEY ix_iprules_active (is_active, rule_type),
  CONSTRAINT ck_iprules_type CHECK (rule_type IN ('allow','block'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE feature_flags (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  key_name      VARCHAR(80)     NOT NULL,
  description   VARCHAR(255)    NULL,
  is_enabled    TINYINT(1)      NOT NULL DEFAULT 0,
  rollout_json  JSON            NULL,                 -- targeting rules / % rollout
  organization_id BIGINT UNSIGNED NULL,               -- NULL = global
  updated_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_ff_key_org (key_name, organization_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```
*Feature flags* let new modules ship dark and enable progressively (supports phased rollout & the
future modules in §Scalability).

---

## 12. Relationships — every relationship & why

### 12.1 One-to-one (1:1)
| Relationship | Why |
|---|---|
| `campaigns` — `campaign_schedules` | A campaign has at most one active schedule row; separated so unscheduled campaigns carry no scheduling columns and the beat scanner queries a small table. |
| `users` — `mfa_secret_enc` (column) | 1:1 secret kept on the user row (encrypted); no separate table needed. |

### 12.2 One-to-many (1:N)
| Parent → Children | Why it exists |
|---|---|
| `organizations` → `users`, `whatsapp_business_accounts`, `contacts`, … | Tenancy/ownership scoping; every scoped entity belongs to one org. |
| `whatsapp_business_accounts` → `phone_numbers`, `message_templates` | A WABA contains many numbers and owns many templates (Meta's model). |
| `phone_numbers` → `conversations`, `messages`, `webhook_events` | A number hosts many conversations and receives many events. |
| `contacts` → `contact_attribute_values`, `conversations`, `campaign_recipients` | A contact has many attribute values, threads, and campaign sends. |
| `campaigns` → `campaign_recipients`, `campaign_batches`, `campaign_retry_queue` | A campaign fans out to millions of recipients and their retry/checkpoint rows. |
| `conversations` → `messages`, `internal_notes` | A thread holds many messages and notes. |
| `messages` → `message_status_history` | Each message accrues multiple status transitions. |
| `message_templates` → `template_versions` | Version history per template. |
| `ai_knowledge_base` → `ai_knowledge_chunks` | A KB doc is split into many embeddable chunks. |
| `users` → `rate_cards` (`created_by`) | Which operator authored a rate; the card's only FK (§8.5.2). |

### 12.3 Many-to-many (M:N) — via junction tables
| Relationship | Junction | Why M:N |
|---|---|---|
| `users` ↔ `roles` | `user_roles` | A user can hold several roles; a role is shared by many users. |
| `roles` ↔ `permissions` | `role_permissions` | Fine-grained permissions composed into roles; permissions reused across roles. |
| `contacts` ↔ `tags` | `contact_tags` | A contact has many tags; a tag labels many contacts. |
| `conversations` ↔ `tags` | `conversation_tags` | A conversation carries many classification tags; a tag labels many conversations (§9.7, v1.3). |

Junction tables use a **composite primary key** of the two FK columns (natural uniqueness, no surrogate
id needed) plus a **reverse secondary index** to make lookups fast in both directions.

### 12.4a Value joins (no FK) — `rate_cards` (FR-CAM-11)
> **Amendment 2026-07-17 (v1.2).**

`rate_cards` is a **lookup dimension**, not a child of anything it prices. It is joined **by value**,
never by key, and holds **no FK** to campaigns, contacts or templates:

| Joined to | On | Why it is not an FK |
|---|---|---|
| `contacts` | `contacts.country_code` = `rate_cards.country_code` | The card is priced per **country**, not per contact; `contacts` is a 10M+ tenant table and the card is a small global one. `country_code` is **nullable** — the unresolved case is a documented outcome (§8.5.4), not a broken reference. |
| `message_templates` | `message_templates.category` = `rate_cards.category` | The card is priced per **category**, not per template. Both sides are `VARCHAR + CHECK` (§1.4), so the shared vocabulary is the contract. |
| `campaigns` | resolved via the campaign's roster + template | The estimate is **derived**, not stored as a link. Only the rounded result lands on `campaigns.estimated_cost`. |

An FK on either column would tie a global, effective-dated price list to tenant rows and forbid the
NULL country the schema already permits. **Tenancy:** `rate_cards` has no `organization_id` and is
therefore the one campaign-domain table outside tenant scoping — deliberate, per §8.5.1.

### 12.4 Soft references (no DB FK) — partitioned tables
`messages`, `message_status_history`, `campaign_recipients`, `contact_events`, `webhook_events`,
`link_clicks`, `audit_logs`, `system_logs`, `error_logs`, `activity_logs`, `monitoring_metrics`
reference parents by **indexed id columns without FK constraints** (MySQL forbids FKs on partitioned
tables). Integrity is enforced in the service layer; every such column is indexed as if constrained.

---

## 13. Index strategy

### 13.1 Principles
- **Clustered/primary:** InnoDB clusters rows on the PK. Non-partitioned core tables cluster on the
  compact `BIGINT id` (fast joins, small secondary indexes). Partitioned tables cluster on
  `(id, created_at)` so the partition key is present and time-range scans are local to a partition.
- **UUID lookups:** every external-facing table has `UNIQUE (uuid)` for API `GET /resource/{uuid}`.
- **Foreign-key columns are always indexed** (constrained or app-enforced) to avoid full scans on joins
  and cascade checks.
- **Composite indexes are ordered by selectivity & query shape** — leading column is the equality
  filter (usually `organization_id` or a parent id), trailing column supports range/sort (`created_at`).
- **Keyset pagination** (not OFFSET) over big lists uses `(organization_id, created_at, id)` ordering,
  supported by `(organization_id, created_at)` indexes — O(log n) at any page depth.

### 13.2 Notable indexes and their purpose
| Table | Index | Serves |
|---|---|---|
| `contacts` | `uq (org, wa_id)` | Dedup + inbound routing (FR-CON-06) |
| `contacts` | `(org, created_at)`, `(org, opt_in_status)`, `(org, last_inbound_at)` | List pagination + segmentation |
| `contact_attribute_values` | `(attribute_id, value_string(191))` / `_number` / `_datetime` | Indexed attribute filtering for segments |
| `contact_tags` | `(tag_id, contact_id)` | "All contacts with tag X" (campaign audiences) |
| `conversation_tags` | `(tag_id, conversation_id)` | "All conversations with tag X" (inbox by-tag filter, §9.7) |
| `messages` | `(conversation_id, created_at)` | Thread view |
| `messages` | `ix (wamid)` | Webhook status update by WhatsApp id |
| `messages` | `(org, created_at)`, `(campaign_id)` | Analytics & campaign rollups |
| `campaign_recipients` | `(campaign_id, status)` | Live progress + resume scanning |
| `campaign_recipients` | `uq (campaign_id, contact_id, created_at)` | Idempotent, one-send-per-contact |
| `campaign_schedules` | `(is_active, next_run_at)` | Beat scan for due campaigns |
| `campaign_retry_queue` | `(status, next_attempt_at)` | Smart-retry due scan |
| `rate_cards` | `(country_code, category, effective_from, effective_to)` | Cost-estimate rate lookup (FR-CAM-11) |
| `rate_cards` | `uq (country_code, category, effective_from)` | One rate per pair per instant |
| `conversations` | `(org, status, last_message_at)` | Inbox list ordering/filtering |
| `conversations` | `(is_window_open, window_expires_at)` | Window-expiry sweeps |
| `audit_logs` | `(entity_type, entity_id, created_at)` | Entity history |
| `ai_knowledge_base` | `FULLTEXT (title, content)` | KB keyword search fallback |

### 13.3 Search indexes
- **Contacts search** (name/phone/email): B-tree indexes on `(org, full_name)`, `email`, and the
  `wa_id`/`phone_e164` columns. For fuzzy/large-scale search, §Scalability describes an optional
  external search engine; the schema stays the source of truth.
- **Knowledge base:** MySQL `FULLTEXT` now; vector search via `ai_knowledge_chunks.embedding` later.

---

## 14. Partitioning strategy

### 14.1 What we partition and why
All **append-only, time-series, high-volume** tables use **`RANGE COLUMNS(created_at)` monthly**
partitions:

| Table | Est. scale | Why partition |
|---|---|---|
| `messages` (ledger) | 10M+ | Thread/analytics queries are time-bounded; old months pruned by dropping partitions. |
| `message_status_history` | 100M+ | Highest write volume; partition pruning keeps status writes/reads on small hot partitions. |
| `campaign_recipients` (deliveries) | 100M+ | Delivery logs age out; per-campaign queries are recent; archive by month. |
| `webhook_events` | 10M+ | Firehose of inbound events; only recent ones are re-processed; drop old cheaply. |
| `audit_logs` | 10M+ | Compliance retention windows map naturally to month partitions. |
| `system_logs`, `error_logs`, `activity_logs` | 10M+ | Operational logs are time-scoped; prune by dropping months. |
| `contact_events`, `link_clicks`, `monitoring_metrics` | 10M+ | Time-series; recent-window queries + cheap pruning. |

### 14.2 Mechanics
- **PK includes the partition key** (`(id, created_at)`) — a MySQL requirement; app-generated
  `BIGINT id` remains globally unique via AUTO_INCREMENT.
- **No FKs on partitioned tables** — enforced in the service layer (§12.4).
- **Partition maintenance is automated**: a scheduled job (Celery beat / MySQL event) **pre-creates**
  N future monthly partitions and **drops/archives** partitions past the retention window. The
  `pmax` catch-all partition guarantees inserts never fail if maintenance lags; the job splits `pmax`
  before it is used.
- **Query alignment:** every hot query includes a `created_at` range (or a parent id that co-locates
  by time), enabling **partition pruning** so scans touch only relevant months.

### 14.3 Why not partition `contacts`
`contacts` (1M rows) is **not** time-series, is referenced by many FKs, and must be uniquely keyed by
`(org, wa_id)` — partitioning would force the partition key into that unique key and complicate joins
for no benefit at this scale. Correct indexing is sufficient; if it ever grows past ~50–100M, hash
partitioning by `organization_id` or `id` is the escape hatch (no redesign needed).

---

## 15. Archiving & retention policy

| Data class | Tables | Default retention | Archive / purge |
|---|---|---|---|
| Message ledger | `messages` | 24 months hot, then archive | Move old partitions to cold storage; keep aggregates |
| Delivery logs | `message_status_history`, `campaign_recipients` | 12–24 months | Drop/archive old partitions; campaign KPIs preserved on `campaigns` |
| Webhook raw | `webhook_events` | 90 days | Drop old partitions (already processed) |
| Audit | `audit_logs` | 24–84 months (compliance) | Archive, never silently delete |
| System/error logs | `system_logs`, `error_logs` | 30–180 days | Drop old partitions |
| Activity/metrics | `activity_logs`, `monitoring_metrics`, `contact_events`, `link_clicks` | 12–24 months | Drop/roll-up |
| Exports/backups metadata | `exports`, `backups` | Exports 7–30 days; backups per policy | Files expire in object storage; rows pruned |
| Contacts/business data | `contacts`, `campaigns`, `templates` | Permanent (soft delete) | Hard-delete on privacy request (FR-DL-08) |

All retention windows are **configurable** (FR-DL-05) and enforced by an automated cleanup job with a
**dry-run mode** and audit trail (FR-DL-06). Aggregated analytics are computed and stored before raw
partitions are dropped, so historical dashboards survive purging.

---

## 16. Scalability & future-proofing (no schema redesign)

| Future module (SRS NFR-EXT) | Already accommodated by |
|---|---|
| **WhatsApp Flows** | `message_templates.components_json` + `messages.content_json` store Flow references/payloads; no new columns needed to reference a Flow. |
| **Commerce** (catalog/orders) | `messages.message_type` allows `interactive`/product types; new `catalogs`/`orders` tables attach via existing `contacts`/`conversations` FKs — additive, not a redesign. |
| **CRM integrations** | `contacts.source`, `custom_attribute_definitions` (unlimited fields), and `api_keys`/outbound webhooks provide the sync surface; add an `integrations` table additively. |
| **Omnichannel** (IG/Messenger) | `phone_numbers.channel_type`, `conversations.channel_type`, `messages.message_type` are already channel-generalized; a new channel is data, not schema change. |
| **AI modules** | `ai_conversations.model`/provider-agnostic design; `ai_knowledge_chunks.embedding` can move to a dedicated vector store without touching business tables. |
| **Automation engine** | `contact_events` + a future `automation_rules`/`automation_runs` pair plug into the existing event stream (event-driven, NFR-EXT-05); no change to core tables. |
| **Multi-workspace** | `organization_id` on every scoped table already enables tenant separation. |
| **Sharding/scale-out** | `BIGINT` keys + `organization_id` scoping + time partitioning make horizontal sharding (by org or by time) feasible later without app rewrites. |

---

## 17. Normalization & justified denormalization

The schema is **normalized to 3NF** by default (no repeating groups; every non-key attribute depends
on the key). We **denormalize only** where a measured read pattern justifies it, and each case is
listed here:

| Denormalization | Where | Justification |
|---|---|---|
| **Aggregate counters** (`total/sent/delivered/read/failed_count`, `actual_cost`) | `campaigns` | Dashboards and lists must show campaign KPIs in O(1); recomputing from 100M `campaign_recipients` rows per view is infeasible. Counters are updated transactionally/atomically as statuses change and periodically reconciled against the source of truth. |
| **`messages.status` (current status)** | `messages` | Avoids joining 100M-row `message_status_history` to show a message's latest state; history remains authoritative. |
| **`contacts.attributes_cache` (JSON)** | `contacts` | Renders contact lists and simple attribute filters without N joins to `contact_attribute_values`; the EAV table stays the source of truth for complex/indexed filters. |
| **`conversations.last_message_preview / unread_count / window_expires_at`** | `conversations` | The inbox list must render hundreds of threads instantly without scanning `messages`; derived fields updated on message insert. |
| **`segments.cached_count / compiled_json`** | `segments` | Avoids re-evaluating a 1M-row filter on every page load; refreshed on a schedule/opening the segment. |
| **`tags.usage_count`, `short_links.click_count`, `media_assets.usage_count`** | respective | Cheap counters vs. COUNT() over large child tables. |
| **Unify "Messages" + "Message Ledger" into one `messages` table** | messaging | Avoids duplicating `wamid`/status/cost across two tables; a campaign send *is* a message (see §9.2). |

Every counter has a **reconciliation job** so denormalized values cannot drift permanently from the
normalized truth.

---

## 18. Requested-table → implemented-table map

Confirms full coverage of the SRS/brief table list (consolidations noted, per the "avoid unnecessary
duplication" directive):

| Requested | Implemented as | Note |
|---|---|---|
| Users / Roles / Permissions | `users`, `roles`, `permissions` (+ `role_permissions`, `user_roles`) | — |
| Sessions / Refresh Tokens / API Keys | `user_sessions`, `refresh_tokens`, `api_keys` (+ `password_reset_tokens`) | — |
| Organizations | `organizations` | Tenancy scoping |
| WhatsApp Business Accounts / Phone Numbers | `whatsapp_business_accounts`, `phone_numbers` | — |
| Contacts / Tags / Segments / Custom Attributes / Segment Rules | `contacts`, `tags` (+`contact_tags`), `segments`, `custom_attribute_definitions` (+`contact_attribute_values`), `segment_rules` | — |
| Templates / Media | `message_templates` (+`template_versions`), `media_assets` | — |
| Campaigns / Campaign Recipients / Campaign Queue / Campaign Schedule / Campaign Retry Queue | `campaigns`, `campaign_recipients`, `campaign_batches` (+ Redis/Celery for the live queue), `campaign_schedules`, `campaign_retry_queue` | "Campaign Queue" = durable checkpoint (`campaign_batches`) + transient Redis queue |
| Rate Card | `rate_cards` | Global (no tenancy), operator-managed, effective-dated; **estimation only** (§8.5) |
| Message Ledger / Messages / Message Status History | `messages` (unified ledger) + `message_status_history` | Ledger & Messages unified (§9.2) |
| Conversations | `conversations` | — |
| Webhook Events / Dead Letter | `webhook_events`, `webhook_dead_letter` | — |
| Quick Replies / Internal Notes | `quick_replies`, `internal_notes` | — |
| AI Knowledge Base / AI Conversations | `ai_knowledge_base` (+`ai_knowledge_chunks`), `ai_conversations` (+`ai_conversation_messages`) | — |
| Notifications | `notifications` | — |
| Audit Logs / System Logs / Activity Logs / Error Logs | `audit_logs`, `system_logs`, `activity_logs`, `error_logs` | Kept distinct by purpose (§11) |
| Settings | `settings` | Scoped key/value |
| Backups / Exports / Imports | `backups`, `exports`, `imports` | — |
| Job Queue Metadata / Monitoring Metrics | `job_metadata`, `monitoring_metrics` | — |
| Rate Limits / Feature Flags | `rate_limit_policies` (+`ip_access_rules`; counters in Redis), `feature_flags` | Counters correctly in Redis (§2) |
| Click/URL tracking (from SRS FR-AN-04) | `short_links`, `link_clicks` | Added to satisfy analytics reqs |

**Total: ~50 tables.** Every requested table is present; three consolidations are explicitly justified.

---

## 19. Row-count & performance summary

| Table | Est. rows (year 1–3) | Partitioned | Hot query | Scale mechanism |
|---|---|---|---|---|
| `contacts` | 1M+ | No | List/segment/search | Composite indexes, keyset pagination |
| `contact_attribute_values` | 10M+ | No | Attribute filter | `(attribute_id, value_*)` indexes |
| `contact_tags` | 5M+ | No | Contacts-by-tag | Reverse index |
| `messages` | 10M+ | Monthly | Thread / analytics | Partition pruning + `wamid` index |
| `message_status_history` | 100M+ | Monthly | Status by message/wamid | Partitioning + narrow rows |
| `campaign_recipients` | 100M+ | Monthly | Progress / resume | `(campaign_id,status)` + partitions |
| `webhook_events` | 10M+ | Monthly | Reprocess recent | Partition drop at 90d |
| `audit_logs` | 10M+ | Monthly | Entity history | Partitioning + entity index |
| `conversations` | 100k–1M | No | Inbox list | `(org,status,last_message_at)` |
| `conversation_tags` | 100k–1M | No | Conversations-by-tag | Reverse index `(tag_id, conversation_id)` |

Targets from SRS §5.1 (dashboard <1.5s, search <500ms @1M, import ≥10k/min) are met by: denormalized
counters (dashboards), covering composite indexes (search/lists), partition pruning (analytics),
and batched async writes (imports/sends).

---

## 20. Self-review record

Reviewed as **Principal DB Architect, Senior Backend, Performance Engineer, DBA, Security, DevOps**;
issues found were fixed before presenting:

- **Normalization (DBA):** 3NF confirmed; every denormalization is enumerated with justification and a
  reconciliation job (§17). No unjustified duplication. ✔
- **Partitioning correctness (DBA):** every partitioned table has the partition key in its PK; FK
  restriction acknowledged and mitigated with app-level integrity + indexed FK columns; `pmax`
  catch-all prevents insert failures; automated partition maintenance specified. ✔
- **Indexes (Performance):** every FK and hot filter/sort has a supporting index; keyset pagination
  designed in; reverse indexes on junctions; no obvious missing index for the stated query patterns. ✔
- **Scale (Performance):** 1M contacts / 10M messages / 100M delivery logs mapped to concrete tables,
  partitioning, and index plans; contacts deliberately not partitioned with a documented escape hatch. ✔
- **Security (Security Eng):** passwords/tokens/keys stored only as hashes; WABA tokens & MFA secrets
  encrypted at rest; audit log immutable + hash-chain; IP rules & rate-limit policy tables; PII flagged
  on attributes; privacy erasure supported. ✔
- **Reliability (DevOps):** durable campaign checkpoints and job metadata in MySQL (not only Redis);
  webhook dead-letter + replay; backups table tracks verification. ✔
- **Storage boundaries (Architect):** media bytes → object storage; rate-limit counters → Redis;
  durable truth → MySQL; explicitly stated with "never" rules (§2). ✔
- **Future-proofing (Architect):** WhatsApp Flows, commerce, CRM, omnichannel, AI, automation, and
  multi-workspace all accommodated additively (§16); `organization_id` and `channel_type` present now. ✔
- **Conventions (all):** consistent naming, two-key identity (BIGINT + UUIDv7), UTC `DATETIME(6)`,
  `VARCHAR+CHECK` enums, optimistic `row_version`, soft-delete strategy with unique-key handling. ✔

---

## 21. Business Event Ledger & Enterprise Event Taxonomy

> **Additive (v1.1).** The authoritative, immutable source of truth for **business analytics** — a versioned,
> append-only ledger of *what happened in the business*. Distinct from `audit_logs` (§11.2 — *who changed what*,
> for security/compliance) and `contact_events` (§6.5 — the contact-scoped activity timeline). Every business
> KPI (Doc 6 §48) and the Executive Business Dashboard (Doc 5 Part G) derive from this ledger, which is
> distributed to consumers by the **Domain Event Bus** (Doc 6 §47). Captured from Day One so future analytics
> require no redesign and no backfill.

### 21.1 Design properties
| Requirement | How it is met |
|---|---|
| **Append-only** | Only `INSERT`s; no `UPDATE`/`DELETE`. Corrections are new **compensating events**, never edits. |
| **Versioned events** | `event_version` on every row; the taxonomy catalog (§21.2) versions each type; consumers tolerate additive payload changes. |
| **Immutable** | Enforced at the service layer + review policy; no ORM update path; retention removes whole partitions only. |
| **Partition strategy** | Monthly `RANGE COLUMNS(occurred_at)` (Doc 3 §14) — same pattern as the message ledger; cheap pruning. |
| **Retention** | Long (default 24–84 months, compliance-driven); analytics rollups (Doc 6 §35) are computed **before** old partitions are pruned so history survives. |
| **Analytics-ready** | Indexed by type/subject/campaign/channel/time; the single source the KPI catalog (Doc 6 §48) reads. |
| **Replay-ready** | Durable log → projections/rollups (contact timeline, KPIs) rebuilt by **idempotent replay** (Doc 6 §47). |
| **Audit-ready** | Correlated to `audit_logs` via `correlation_id`/`trace_id`; a complete, tamper-evident business record. |
| **Channel-aware** | `channel_type` + `connector_id` on every event (Doc 7) — Meta (Channel 1) and Support Connector (Channel 2) uniformly. |
| **AI-aware** | AI events (`ai.draft_generated`/`ai.approved`/`ai.rejected`) carry model/confidence refs (Doc 9 §3.3). |
| **Future-proof** | New event types register additively in the catalog (§21.2); no schema change to add an event. |

### 21.2 `business_event_types` — the canonical taxonomy catalog
Governed lookup of every business-event type and version (seeded at deploy; extended additively).

```sql
CREATE TABLE business_event_types (
  id            INT UNSIGNED    NOT NULL AUTO_INCREMENT,
  event_type    VARCHAR(80)     NOT NULL,   -- e.g. 'lead.qualified'
  event_version SMALLINT UNSIGNED NOT NULL DEFAULT 1,
  category      VARCHAR(32)     NOT NULL,   -- lead / kyc / payment / sim / campaign / ai / template / connector / user / audit
  subject_type  VARCHAR(32)     NOT NULL,   -- contact / lead / campaign / conversation / template / connector / user
  description   VARCHAR(255)    NULL,
  schema_ref    VARCHAR(160)    NULL,       -- reference to the payload schema for this type+version
  is_active     TINYINT(1)      NOT NULL DEFAULT 1,
  created_at    DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_bet_type_version (event_type, event_version),
  KEY ix_bet_category (category),
  CONSTRAINT ck_bet_category CHECK (category IN
    ('lead','kyc','payment','sim','campaign','ai','template','connector','user','audit'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

### 21.3 Canonical enterprise event taxonomy (seed set)
| Event type | Category | Subject | Notes |
|---|---|---|---|
| `lead.created` | lead | lead/contact | a reactivation lead enters the pipeline |
| `lead.assigned` | lead | lead | assigned to an agent (Doc 7 §21) |
| `lead.qualified` | lead | lead | qualification confirmed |
| `document.received` | kyc | lead | customer document submitted (Doc 7 §16/§24) |
| `kyc.completed` | kyc | lead | verification complete |
| `payment.received` | payment | lead | payment confirmed |
| `sim.issued` | sim | lead | SIM issued |
| `sim.activated` | sim | lead | SIM activated |
| `customer.reactivated` | lead | contact | **the north-star outcome event** |
| `campaign.created` | campaign | campaign | (Doc 6 §26 draft) |
| `campaign.started` | campaign | campaign | send begins (Doc 6 §4) |
| `campaign.delivered` | campaign | message | per-recipient delivery (from status webhook) |
| `campaign.read` | campaign | message | read receipt |
| `campaign.failed` | campaign | message | send/delivery failure + code |
| `campaign.converted` | campaign | contact | recipient took the desired action (attribution) |
| `ai.draft_generated` | ai | conversation/campaign | AI produced a draft (Doc 9) |
| `ai.approved` | ai | draft | human approved an AI output (Doc 9 §30) |
| `ai.rejected` | ai | draft | human rejected an AI output |
| `template.approved` | template | template | Meta approval (Doc 3 §7) |
| `template.rejected` | template | template | Meta rejection + reason |
| `connector.connected` | connector | connector | Support Connector session established (Doc 7 §7) |
| `connector.disconnected` | connector | connector | session lost/logged out |
| `user.login` | user | user | operator login (also audited) |
| `permission.changed` | user | user/role | RBAC change (also audited) |
| `audit.event` | audit | any | generic business-audit marker |

New events (e.g., future channels/commerce) are appended to §21.2 without schema change.

### 21.4 `business_events` — the immutable event ledger (partitioned, high-volume)
```sql
CREATE TABLE business_events (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  uuid            BINARY(16)      NOT NULL,        -- public/dedup id (UUIDv7)
  organization_id BIGINT UNSIGNED NOT NULL,
  event_type      VARCHAR(80)     NOT NULL,        -- FK-by-value to business_event_types.event_type (app-enforced)
  event_version   SMALLINT UNSIGNED NOT NULL DEFAULT 1,
  occurred_at     DATETIME(6)     NOT NULL,        -- business time (when it happened)
  recorded_at     DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),  -- ingest time
  actor_type      VARCHAR(12)     NOT NULL,        -- user / system / ai / connector
  actor_id        BIGINT UNSIGNED NULL,
  subject_type    VARCHAR(32)     NULL,            -- contact / lead / campaign / conversation / template / connector / user
  subject_id      BIGINT UNSIGNED NULL,
  channel_type    VARCHAR(24)     NULL,            -- whatsapp / support_connector / ... (Doc 7)
  connector_id    BIGINT UNSIGNED NULL,
  campaign_id     BIGINT UNSIGNED NULL,
  contact_id      BIGINT UNSIGNED NULL,
  correlation_id  CHAR(36)        NULL,            -- ties related events / request (Doc 6 §13)
  trace_id        CHAR(36)        NULL,
  source          VARCHAR(40)     NULL,            -- emitting module
  schema_ref      VARCHAR(160)    NULL,
  payload_json    JSON            NULL,            -- typed event data (amounts, ids, refs)
  PRIMARY KEY (id, occurred_at),                    -- partition key in PK
  UNIQUE KEY uq_be_uuid (uuid, occurred_at),        -- dedup / idempotent ingest
  KEY ix_be_type_time (event_type, occurred_at),    -- analytics by type over time
  KEY ix_be_subject (subject_type, subject_id, occurred_at),
  KEY ix_be_campaign (campaign_id, occurred_at),
  KEY ix_be_contact (contact_id, occurred_at),
  KEY ix_be_channel (channel_type, occurred_at),
  KEY ix_be_correlation (correlation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
PARTITION BY RANGE COLUMNS (occurred_at) (
  PARTITION p2026_07 VALUES LESS THAN ('2026-08-01'),
  PARTITION p2026_08 VALUES LESS THAN ('2026-09-01'),
  PARTITION pmax     VALUES LESS THAN (MAXVALUE)
);
```
*Rows:* very high (all business facts). *No DB FK* (partitioned) — integrity enforced in the service layer.
*Idempotency:* the emitting service supplies a stable `uuid` per logical event so re-emission/replay is a no-op.
*Two timestamps:* `occurred_at` (business time, used for analytics + partitioning) vs `recorded_at` (ingest time)
so late-arriving events are attributed to when they happened.

### 21.5 Immutability, retention, replay
- **Immutable / append-only:** no update or delete path; a mistaken/changed fact is expressed as a **new
  compensating event** (e.g., `payment.received` reversed by a later negative-amount event) — the ledger is a
  perfect historical record.
- **Retention:** long, compliance-driven; rollups (Doc 6 §35/§48) are computed and stored **before** old
  partitions are dropped, so KPI history survives pruning.
- **Replay:** because the ledger is the durable log, any projection (contact timeline, KPI rollups, a future
  module's read model) is rebuilt by **idempotently replaying** events (Doc 6 §47) — new analytics require no
  new capture.

### 21.6 Relationship to existing tables (no duplication)
- **`audit_logs` (§11.2)** — security/compliance *mutations* (who changed what, before/after, hash-chained).
  `business_events` — *business facts* for analytics. Distinct purposes; correlated by `correlation_id`.
- **`contact_events` (§6.5)** — the contact-scoped *UI timeline*; becomes a **projection** of `business_events`.
- **`lead_stage_transitions` (Doc 7 §23)** — lead-stage changes also emit `lead.*` events into the ledger.
- **`message_status_history` (§9.3)** — delivery status; `campaign.delivered/read/failed` events are derived
  from it, giving analytics one uniform source.

### 21.7 Design decisions & self-review
- **Decision:** a **separate immutable, versioned business-event ledger** is the single source of truth for
  analytics/KPIs, distinct from audit and from operational tables. *Why:* guarantees future BI/ROI without
  backfill; decouples analytics from operational schemas; enables replay. *Trade-off:* event duplication of
  some facts (justified — the ledger is the analytics contract; §17 anti-duplication is respected because these
  are *events*, not the operational rows). *Migration:* new event types are additive.
- **Self-review:** ✔ append-only/immutable/versioned; ✔ partitioned + retention + rollup-before-prune;
  ✔ analytics-/replay-/audit-ready; ✔ channel- and AI-aware; ✔ future-proof (additive taxonomy); ✔ no
  duplication (distinct from audit/contact_events, which become projections). Consumed via Doc 6 §47.

---

*End of Document 3 — Database Design (Version 1.1, FROZEN). §1–§20 = v1.0 baseline; §21 (Business Event Ledger &
Enterprise Event Taxonomy) added in the final additive pass. Distributed by the Domain Event Bus (Doc 6 §47);
KPIs derive from it (Doc 6 §48).*



