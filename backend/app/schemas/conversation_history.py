"""Typed filters and shared-view contracts for Chat History."""

from __future__ import annotations

import uuid as uuidlib
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from app.models.conversation_history_view import ConversationHistoryView
from app.schemas.inbox import ConversationStatusName

FilterToken = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]


class ConversationHistoryFilters(BaseModel):
    """Portable, non-pagination filters stored in a shared Chat History view."""

    status: ConversationStatusName | None = None
    assignee: FilterToken | None = None
    number: uuidlib.UUID | None = None
    tag: uuidlib.UUID | None = None
    q: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
        | None
    ) = None
    date_from: date | None = Field(default=None, alias="from")
    date_to: date | None = Field(default=None, alias="to")
    campaign: uuidlib.UUID | None = None
    has_media: bool = False
    has_audit: bool = False

    @field_validator("assignee")
    @classmethod
    def validate_assignee(cls, value: str | None) -> str | None:
        if value is None:
            return None
        token = value.lower()
        if token in {"unassigned", "none"}:
            return token
        try:
            return str(uuidlib.UUID(value))
        except ValueError as exc:
            raise ValueError("assignee must be a UUID or unassigned") from exc

    @model_validator(mode="after")
    def validate_range(self) -> ConversationHistoryFilters:
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("from must be on or before to")
        return self


class ConversationHistoryViewCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    filters: ConversationHistoryFilters


class ConversationHistoryViewResponse(BaseModel):
    id: str
    name: str
    filters: ConversationHistoryFilters
    created_at: datetime

    @classmethod
    def from_view(cls, row: ConversationHistoryView) -> ConversationHistoryViewResponse:
        return cls(
            id=row.public_id,
            name=row.name,
            filters=ConversationHistoryFilters.model_validate(row.filters_json),
            created_at=row.created_at,
        )


class ConversationHistoryViewsResponse(BaseModel):
    data: list[ConversationHistoryViewResponse]
