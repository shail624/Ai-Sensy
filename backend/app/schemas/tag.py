"""Tag schemas (Doc 04 §14.2)."""

from __future__ import annotations

import re
import uuid as uuidlib
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.tag import Tag

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _validate_color(value: str | None) -> str | None:
    if value is None:
        return None
    if not _HEX_COLOR.match(value):
        raise ValueError("color must be '#RRGGBB'")
    return value


class TagSummary(BaseModel):
    """Compact tag shape embedded in a contact (Doc 04 §14 contact schema)."""

    id: str
    name: str
    color: str | None

    @classmethod
    def from_tag(cls, tag: Tag) -> TagSummary:
        return cls(id=tag.public_id, name=tag.name, color=tag.color)


class TagResponse(BaseModel):
    id: str
    type: str = "tag"
    name: str
    color: str | None
    description: str | None
    usage_count: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_tag(cls, tag: Tag) -> TagResponse:
        return cls(
            id=tag.public_id,
            name=tag.name,
            color=tag.color,
            description=tag.description,
            usage_count=tag.usage_count,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
        )


class TagCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str | None = None
    description: str | None = Field(default=None, max_length=255)

    @field_validator("color")
    @classmethod
    def _color(cls, value: str | None) -> str | None:
        return _validate_color(value)


class TagUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    color: str | None = None
    description: str | None = Field(default=None, max_length=255)

    @field_validator("color")
    @classmethod
    def _color(cls, value: str | None) -> str | None:
        return _validate_color(value)


class ContactTagsRequest(BaseModel):
    """Attach one or more existing tags to a contact (Doc 04 §14.1)."""

    tags: list[uuidlib.UUID] = Field(min_length=1)
