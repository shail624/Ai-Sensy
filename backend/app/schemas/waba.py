"""WABA & phone-number schemas (Doc 04 §13.2/§13.3).

**The token is write-only** (Doc 04 §13.2): it is accepted on create/update, stored encrypted, and
never rendered. Responses expose ``token_set: true`` instead — the reason no response model here
has an ``access_token`` field at all, rather than relying on a caller to remember to strip it.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.waba import QUALITY_RATINGS, WABA_STATUSES, PhoneNumber, WhatsAppBusinessAccount


class WabaCreateRequest(BaseModel):
    """``POST /waba`` — connect a WABA with its system-user token."""

    waba_id: str = Field(min_length=1, max_length=32)
    business_name: str = Field(min_length=1, max_length=160)
    access_token: str = Field(min_length=1, repr=False)
    meta_business_id: str | None = Field(default=None, max_length=32)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    timezone: str | None = Field(default=None, max_length=64)
    token_expires_at: datetime | None = None


class WabaUpdateRequest(BaseModel):
    """``PATCH /waba/{uuid}`` — rotate the token or amend metadata."""

    business_name: str | None = Field(default=None, min_length=1, max_length=160)
    access_token: str | None = Field(default=None, min_length=1, repr=False)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    timezone: str | None = Field(default=None, max_length=64)
    status: str | None = None
    token_expires_at: datetime | None = None
    row_version: int | None = None

    @field_validator("status")
    @classmethod
    def _status(cls, value: str | None) -> str | None:
        if value is not None and value not in WABA_STATUSES:
            raise ValueError(f"status must be one of {list(WABA_STATUSES)}")
        return value


class WabaResponse(BaseModel):
    id: str
    type: str = "waba"
    waba_id: str
    business_name: str
    meta_business_id: str | None
    currency: str | None
    timezone: str | None
    status: str
    #: Whether a token is stored — the token itself is never returned (Doc 04 §13.2).
    token_set: bool
    token_expires_at: datetime | None
    phone_number_count: int
    created_at: datetime
    updated_at: datetime
    row_version: int

    @classmethod
    def from_waba(cls, waba: WhatsAppBusinessAccount, *, phone_number_count: int) -> WabaResponse:
        return cls(
            id=waba.public_id,
            waba_id=waba.waba_id,
            business_name=waba.business_name,
            meta_business_id=waba.meta_business_id,
            currency=waba.currency,
            timezone=waba.timezone,
            status=waba.status,
            token_set=bool(waba.access_token_enc),
            token_expires_at=waba.token_expires_at,
            phone_number_count=phone_number_count,
            created_at=waba.created_at,
            updated_at=waba.updated_at,
            row_version=waba.row_version,
        )


class WabaListResponse(BaseModel):
    data: list[WabaResponse]


class PhoneNumberUpdateRequest(BaseModel):
    """``PATCH /phone-numbers/{uuid}`` — operator-owned fields only (Doc 04 §13.3).

    Meta-owned facts (quality rating, tier, verified name) are not settable here: they arrive via
    sync/refresh, so letting an operator type them would create a lie the next sync silently undoes.
    """

    verified_name: str | None = Field(default=None, max_length=160)
    mps_limit: int | None = Field(default=None, ge=1, le=1000)
    is_default: bool | None = None
    row_version: int | None = None


class PhoneNumberResponse(BaseModel):
    id: str
    type: str = "phone_number"
    waba_id: str
    channel_type: str
    phone_number_id: str
    display_number: str
    verified_name: str | None
    quality_rating: str | None
    messaging_tier: str | None
    throughput_level: str | None
    mps_limit: int
    status: str
    is_default: bool
    last_synced_at: datetime | None
    created_at: datetime
    row_version: int

    @classmethod
    def from_number(cls, number: PhoneNumber, *, waba_public_id: str) -> PhoneNumberResponse:
        return cls(
            id=number.public_id,
            waba_id=waba_public_id,
            channel_type=number.channel_type,
            phone_number_id=number.phone_number_id,
            display_number=number.display_number,
            verified_name=number.verified_name,
            quality_rating=number.quality_rating,
            messaging_tier=number.messaging_tier,
            throughput_level=number.throughput_level,
            mps_limit=number.mps_limit,
            status=number.status,
            is_default=number.is_default,
            last_synced_at=number.last_synced_at,
            created_at=number.created_at,
            row_version=number.row_version,
        )


class PhoneNumbersListResponse(BaseModel):
    data: list[PhoneNumberResponse]


class PhoneNumberHealthResponse(BaseModel):
    """``GET /phone-numbers/{uuid}/health`` (Doc 04 §13.3 sample)."""

    id: str
    display_number: str
    verified_name: str | None
    quality_rating: str | None
    messaging_tier: str | None
    throughput_level: str | None
    mps_limit: int
    status: str
    healthy: bool
    last_synced_at: datetime | None

    @classmethod
    def from_number(cls, number: PhoneNumber) -> PhoneNumberHealthResponse:
        return cls(
            id=number.public_id,
            display_number=number.display_number,
            verified_name=number.verified_name,
            quality_rating=number.quality_rating,
            messaging_tier=number.messaging_tier,
            throughput_level=number.throughput_level,
            mps_limit=number.mps_limit,
            status=number.status,
            # Stored health only: this endpoint reads, `POST .../refresh` re-pulls (Doc 04 §13.3).
            healthy=number.quality_rating not in ("RED",) and number.status == "connected",
            last_synced_at=number.last_synced_at,
        )


__all__ = [
    "QUALITY_RATINGS",
    "PhoneNumberHealthResponse",
    "PhoneNumberResponse",
    "PhoneNumberUpdateRequest",
    "PhoneNumbersListResponse",
    "WabaCreateRequest",
    "WabaListResponse",
    "WabaResponse",
    "WabaUpdateRequest",
]
