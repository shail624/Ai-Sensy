"""Application configuration.

Single, typed, environment-driven settings object (Pydantic Settings v2), per the
configuration hierarchy in Doc 08 §45 and the security rules in Doc 01 §5.4 / Doc 09
§34 (no secrets in code; everything comes from the environment). Import ``settings``
from here; never read ``os.environ`` directly elsewhere.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    app_version: str = "0.1.0"
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
    #: Per-request timeout. Matches the send queues' 15s soft timeout (Doc 06 §2.3) so a hung
    #: Meta call fails inside the task rather than pinning a worker to its hard timeout.
    meta_timeout_seconds: float = 15.0

    # ---- CORS (Doc 04 §25) ------------------------------------------------
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # ---- Logging (Doc 08 §19) --------------------------------------------
    log_level: str = "INFO"
    log_json: bool = True

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

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Allow CORS_ORIGINS as a comma-separated string in the environment."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

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
            f"mysql+asyncmy://{self.db_user}:{self.db_password}"
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
