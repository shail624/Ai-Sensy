"""Segment schemas (Doc 04 §14.3)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.api.pagination import Page
from app.models.segment import MATCH_ALL, MATCH_TYPES, Segment, SegmentRule
from app.schemas.contact import ContactResponse


def _validate_match(value: str) -> str:
    if value not in MATCH_TYPES:
        raise ValueError(f"match_type must be one of {MATCH_TYPES}")
    return value


class SegmentRuleModel(BaseModel):
    group_index: int = Field(default=0, ge=0)
    field_source: str = Field(max_length=24)
    field_key: str = Field(max_length=60)
    operator: str = Field(max_length=24)
    value: Any | None = None

    @classmethod
    def from_rule(cls, rule: SegmentRule) -> SegmentRuleModel:
        return cls(
            group_index=rule.group_index,
            field_source=rule.field_source,
            field_key=rule.field_key,
            operator=rule.operator,
            value=rule.value_json,
        )


class SegmentResponse(BaseModel):
    id: str
    type: str = "segment"
    name: str
    description: str | None
    match_type: str
    rules: list[SegmentRuleModel]
    is_dynamic: bool
    cached_count: int | None
    last_evaluated_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_segment(cls, segment: Segment) -> SegmentResponse:
        return cls(
            id=segment.public_id,
            name=segment.name,
            description=segment.description,
            match_type=segment.match_type,
            rules=[SegmentRuleModel.from_rule(r) for r in segment.rules],
            is_dynamic=segment.is_dynamic,
            cached_count=segment.cached_count,
            last_evaluated_at=segment.last_evaluated_at,
            created_at=segment.created_at,
            updated_at=segment.updated_at,
        )


class SegmentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    match_type: str = MATCH_ALL
    rules: list[SegmentRuleModel] = Field(default_factory=list)

    @field_validator("match_type")
    @classmethod
    def _match(cls, value: str) -> str:
        return _validate_match(value)


class SegmentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    match_type: str | None = None
    rules: list[SegmentRuleModel] | None = None

    @field_validator("match_type")
    @classmethod
    def _match(cls, value: str | None) -> str | None:
        return _validate_match(value) if value is not None else None


class SegmentContactsPage(BaseModel):
    data: list[ContactResponse]
    page: Page
