"""API key schemas (Doc 04 §4.1, Doc 12 §58)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.api_key import ApiKey


class ApiKeyResponse(BaseModel):
    id: str
    type: str = "api_key"
    name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime

    @classmethod
    def from_api_key(cls, api_key: ApiKey) -> ApiKeyResponse:
        return cls(
            id=api_key.public_id,
            name=api_key.name,
            key_prefix=api_key.key_prefix,
            scopes=list(api_key.scopes_json or []),
            is_active=api_key.is_active,
            last_used_at=api_key.last_used_at,
            expires_at=api_key.expires_at,
            revoked_at=api_key.revoked_at,
            created_at=api_key.created_at,
        )


class ApiKeyCreateResponse(ApiKeyResponse):
    """Returned once on creation — includes the plaintext secret (never shown again)."""

    secret: str


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
