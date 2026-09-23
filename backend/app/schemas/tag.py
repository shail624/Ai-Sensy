"""Tag schemas (Doc 04 §14.2)."""

from __future__ import annotations

import re
import uuid as uuidlib
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.tag import Tag

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _normalize_keywords(value: list[str]) -> list[str]:
    normalized: list[str] = []
    for keyword in value:
        candidate = " ".join(keyword.strip().upper().split())
        if candidate and candidate not in normalized:
            normalized.append(candidate)
    return normalized


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
    first_message_enabled: bool
    first_message_keywords: list[str]
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
            first_message_enabled=tag.first_message_enabled,
            first_message_keywords=tag.first_message_keywords_json,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
        )


class TagCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str | None = None
    description: str | None = Field(default=None, max_length=255)
    first_message_enabled: bool = False
    first_message_keywords: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("color")
    @classmethod
    def _color(cls, value: str | None) -> str | None:
        return _validate_color(value)

    @field_validator("first_message_keywords")
    @classmethod
    def _keywords(cls, value: list[str]) -> list[str]:
        return _normalize_keywords(value)

    @model_validator(mode="after")
    def _enabled_rule_has_keywords(self) -> TagCreateRequest:
        if self.first_message_enabled and not self.first_message_keywords:
            raise ValueError("enabled first-message tagging requires at least one keyword")
        return self


class TagUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    color: str | None = None
    description: str | None = Field(default=None, max_length=255)
    first_message_enabled: bool | None = None
    first_message_keywords: list[str] | None = Field(default=None, max_length=20)

    @field_validator("color")
    @classmethod
    def _color(cls, value: str | None) -> str | None:
        return _validate_color(value)

    @field_validator("first_message_keywords")
    @classmethod
    def _keywords(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else _normalize_keywords(value)


class ContactTagsRequest(BaseModel):
    """Attach one or more existing tags to a contact (Doc 04 §14.1)."""

    tags: list[uuidlib.UUID] = Field(min_length=1)
