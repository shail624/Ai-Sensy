"""Application configuration.

Single, typed, environment-driven settings object (Pydantic Settings v2), per the
configuration hierarchy in Doc 08 §45 and the security rules in Doc 01 §5.4 / Doc 09
§34 (no secrets in code; everything comes from the environment). Import ``settings``
from here; never read ``os.environ`` directly elsewhere.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["development", "staging", "production", "test"]


class Settings(BaseSettings):
    """Typed application settings loaded from the environment / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application -------------------------------------------------------
    app_name: str = "WhatsApp Business Platform"
    app_version: str = "1.0.0-rc1"
    environment: Environment = "development"
    debug: bool = False
    # API is served under /api/v1 (Doc 04 §2). Health probes live at the root.
    api_v1_prefix: str = "/api/v1"

    # ---- Security / JWT (Doc 04 §4) --------------------------------------
    # SECRET_KEY MUST be overridden in every non-development environment.
    secret_key: str = "change-me-in-production-a-long-random-value"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    # ---- Password policy (Doc 01 FR-AUTH-04) ------------------------------
    password_min_length: int = 12
    max_failed_logins: int = 5
    lockout_minutes: int = 15

    # ---- Argon2id hashing (Doc 01 §5.4 / NFR-SEC-08) — OWASP-aligned defaults.
    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536  # KiB (64 MiB)
    argon2_parallelism: int = 4

    # ---- Database (Doc 03; Doc 08 §10) -----------------------------------
    # Either provide DATABASE_URL directly, or the discrete DB_* parts below
    # which are assembled into an async MySQL URL.
    database_url: str | None = None
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "wa_app"
    db_password: str = "wa_app"
    db_name: str = "wa_platform"
    db_pool_size: int = 10
    db_max_overflow: int = 10
    db_pool_pre_ping: bool = True
    db_echo: bool = False

    # ---- Redis (Doc 06 §12; Doc 08 §11) ----------------------------------
    redis_url: str = "redis://localhost:6379/0"

    # ---- Queue engine (Doc 06) -------------------------------------------
    celery_result_expires_seconds: int = 86400  # 24h; job_metadata is the durable record
    #: Worker heartbeat TTL — a worker missing this long is considered dead (Doc 06 §3.4).
    worker_heartbeat_ttl_seconds: int = 60
    worker_heartbeat_interval_seconds: int = 15

    # ---- Scheduler (Doc 06 §10) ------------------------------------------
    #: How late a **one-time** campaign may fire after downtime before it is skipped instead
    #: (Doc 06 §10.5, D15). A day-late marketing blast is worse than no blast, so this is
    #: deliberately short — and explicit, never accidental.
    scheduler_one_time_grace_seconds: int = 3600
    #: Ceiling on what a single tick claims, so a backlog cannot flood the control lane at once.
    scheduler_tick_scan_limit: int = 500

    # ---- Storage (Doc 08 §14; FR-MED-06/09) ------------------------------
    #: Pluggable backend: 'local' volume by default, S3-compatible optional (FR-MED-06).
    storage_backend: str = "local"
    storage_local_path: str = "./var/media"
    #: Signed, expiring access only — never a public bucket (Doc 08 §14, FR-MED-09).
    storage_signed_url_ttl_seconds: int = 300
    storage_public_base_url: str = ""
    #: How long a generated export stays downloadable (Doc 03 §11.6 exports.expires_at).
    storage_export_ttl_days: int = 7

    # ---- Meta Cloud API — Channel 1 (Doc 07 §5; Doc 01 CMP-01) -----------
    # Credentials are environment-only (Doc 01 §5.4: no secrets in code). Per-WABA tokens are
    # stored on `whatsapp_business_accounts` when that module is built; these are the process
    # defaults an adapter falls back to.
    meta_api_base_url: str = "https://graph.facebook.com"
    meta_api_version: str = "v21.0"
    meta_access_token: str = ""
    meta_phone_number_id: str = ""
    meta_waba_id: str = ""
    #: Meta **app** secret — the key `X-Hub-Signature-256` is HMAC'd with (Doc 04 §23). App-level,
    #: not per-WABA: one app receives every WABA's webhooks. Required to accept inbound webhooks.
    meta_app_secret: str = ""
    #: Shared secret echoed in Meta's subscription handshake (`hub.verify_token`, Doc 04 §23).
    #: Set to the same value in the Meta App dashboard's webhook configuration.
    meta_webhook_verify_token: str = ""
    #: Per-request timeout. Matches the send queues' 15s soft timeout (Doc 06 §2.3) so a hung
    #: Meta call fails inside the task rather than pinning a worker to its hard timeout.
    meta_timeout_seconds: float = 15.0
    #: 32-byte base64url key encrypting channel tokens at rest (Doc 03 §5.1 `access_token_enc`,
    #: FR-WA-03). Required in production; derived from SECRET_KEY elsewhere (see app.core.crypto).
    token_encryption_key: str = ""

    # ---- CORS (Doc 04 §25) ------------------------------------------------
    #: ``NoDecode`` is load-bearing. Without it pydantic-settings treats a ``list[str]`` field as
    #: "complex" and runs ``json.loads`` on the raw environment value *inside the settings source* —
    #: before any validator runs. That made the validator below unreachable and left a JSON array
    #: as the only accepted form, so every documented value (``CORS_ORIGINS=`` for same-origin, or
    #: a comma-separated list) raised SettingsError at import time and took down every process that
    #: imports this module: api, all three worker pools, beat and migrate alike.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    # ---- Logging (Doc 08 §19) --------------------------------------------
    log_level: str = "INFO"
    log_json: bool = True

    # ---- Idempotency (Doc 04 §8; Doc 06 §12.2) ---------------------------
    #: How long an `Idempotency-Key` replays its original response. 24h per Doc 04 §8.
    idempotency_ttl_seconds: int = 86400

    # ---- Tier-aware sending / rate gate (Doc 06 §5; FR-WA-13) ------------
    #: The gate every send passes before Meta is called. Off only for tests that are not about it.
    rate_gate_enabled: bool = True
    #: D11 fallback share of a number's MPS when Redis is unreachable. Each worker paces
    #: independently there, so the fraction is what keeps the fleet's sum under the ceiling.
    rate_gate_fallback_fraction: float = 0.25

    # ---- Rate limiting (Doc 04 §9) ---------------------------------------
    rate_limit_enabled: bool = True
    # 'auth' bucket: brute-force protection for login/refresh (Doc 04 §9 — 10 / 5 min / IP).
    rate_limit_auth_max: int = 10
    rate_limit_auth_window_seconds: int = 300

    # ---- Bootstrap (Doc 03 §4.1) — the single-tenant organization defaults.
    # The owner user is created by `python -m app.cli create-owner`; its password comes
    # from the environment (OWNER_PASSWORD) and is never stored in code or settings.
    bootstrap_org_name: str = "Vi Reactivation Team"
    bootstrap_org_slug: str = "vi-reactivation"

    # ---- WAHA QR provider (ADR-0021 Class B; QR-01 adapter foundation) -------------------
    # Unconfigured and disabled by default. The application boots normally with none of these
    # set — the adapter is registered statically but performs no network call until something
    # explicitly asks it to, and every organization-facing QR feature flag is off by default
    # (`app.channels.flags.OmnichannelFeatureFlag`).
    #
    # There is deliberately **no default API key**. An empty key is a configuration error raised
    # at call time (`ChannelConfigError`), never a silent fallback that might reach a real server.
    #: Administrative base URL of the self-hosted WAHA server. Must stay on an internal network —
    #: WAHA's own documentation warns against exposing it publicly.
    waha_base_url: str = ""
    #: Server API key. Secret: never logged, never echoed, redacted from adapter diagnostics.
    waha_api_key: str = ""
    waha_timeout_seconds: float = 10.0
    #: Certification baseline (`docs/evidence/provider-evaluations/waha-class-b-selection-record.md`).
    #: A server reporting a different version is reported as drift; a different engine fails closed.
    waha_certified_version: str = "2026.7.2"
    #: Only NOWEB is owner-approved. Changing this requires a new owner decision and re-certification.
    waha_approved_engine: str = "NOWEB"
    #: Shared secret the WAHA server signs each webhook body with (raw-body sha512 HMAC). Secret:
    #: never logged. Empty by default and an empty secret **rejects** every delivery, so an
    #: unconfigured deployment cannot silently accept unsigned provider traffic.
    waha_webhook_hmac_secret: str = ""
    #: Session this deployment sends through — the endpoint scope for sends, acknowledgement
    #: correlation and reconcile lookups. Empty by default; a send without one fails closed.
    waha_session_name: str = ""
    #: The single organization permitted to view or operate the WAHA QR connection surface
    #: (QR-07). ADR-0021 §"Deployment scope": WAHA is internal, self-hosted, **single
    #: organization** — not multi-tenant SaaS — so this is a scope, not a per-tenant secret
    #: store. ``None`` (the default) means every organization sees the QR surface as
    #: unconfigured, which is the safe default for a deployment that has not assigned it.
    waha_organization_id: int | None = None

    # ---- Development-only preview fixtures (`python -m app.cli seed-dev-fixtures`) -------
    # Explicit opt-in on top of the environment gate itself: `development`/`test` alone is not
    # enough, since a shared dev/staging box could still have ENVIRONMENT=development set by
    # mistake. Defaults to False everywhere, including local development, so fixture data is
    # never created as a side effect of anything else. Never true in production — enforced in
    # code (`app.dev_fixtures.ensure_dev_fixtures_allowed`), not just by convention.
    allow_dev_fixtures: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Parse CORS_ORIGINS from the environment.

        Accepts the documented comma-separated form (``a.example,b.example``), the empty string
        (meaning "no cross-origin callers" — the same-origin deployment behind the edge proxy),
        and a JSON array, which was the only form that worked before ``NoDecode`` was applied and
        so may exist in a deployed environment file already.
        """
        if not isinstance(value, str):
            return value
        text = value.strip()
        if not text:
            return []
        if text.startswith("["):
            return json.loads(text)
        return [origin.strip() for origin in text.split(",") if origin.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_database_uri(self) -> str:
        """The async SQLAlchemy connection URL.

        Uses ``DATABASE_URL`` verbatim when provided (tests set an in-memory
        SQLite URL); otherwise assembles an async MySQL URL from the DB_* parts.
        """
        if self.database_url:
            return self.database_url
        return (
            f"mysql+aiomysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton (cached)."""
    return Settings()


settings = get_settings()
