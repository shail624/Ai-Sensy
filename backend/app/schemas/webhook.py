"""Inbound webhook schemas (Doc 04 §23)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WebhookAckResponse(BaseModel):
    """The body behind a fast ``200``.

    Meta only reads the status code, so this exists for operators and tests: it states how many
    events the delivery was durably split into (Doc 06 §11.2).
    """

    status: str = Field(default="received", examples=["received"])
    events: int = Field(description="Events persisted from this delivery.", examples=[2])
