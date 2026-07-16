"""Advanced contact search schemas (Doc 04 §14.1 ``POST /contacts/search``).

Reuses the segment rule shape so a saved filter and an ad-hoc search are interchangeable.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.models.segment import MATCH_ALL, MATCH_TYPES
from app.schemas.segment import SegmentRuleModel


class ContactSearchRequest(BaseModel):
    match_type: str = MATCH_ALL
    rules: list[SegmentRuleModel] = Field(default_factory=list)
    limit: int | None = Field(default=None, ge=1, le=200)
    cursor: str | None = None

    @field_validator("match_type")
    @classmethod
    def _match(cls, value: str) -> str:
        if value not in MATCH_TYPES:
            raise ValueError(f"match_type must be one of {MATCH_TYPES}")
        return value
