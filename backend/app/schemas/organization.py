"""Organization schemas (Doc 04 §13.1)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.organization import Organization


class OrganizationResponse(BaseModel):
    id: str
    type: str = "organization"
    name: str
    slug: str
    timezone: str
    default_locale: str
    settings: dict[str, Any] | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    row_version: int

    @classmethod
    def from_org(cls, org: Organization) -> OrganizationResponse:
        return cls(
            id=org.public_id,
            name=org.name,
            slug=org.slug,
            timezone=org.timezone,
            default_locale=org.default_locale,
            settings=org.settings_json,
            is_active=org.is_active,
            created_at=org.created_at,
            updated_at=org.updated_at,
            row_version=org.row_version,
        )


class OrganizationUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    default_locale: str | None = Field(default=None, min_length=1, max_length=10)
    settings: dict[str, Any] | None = None
    row_version: int | None = None
