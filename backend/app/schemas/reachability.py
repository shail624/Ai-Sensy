"""WhatsApp reachability contracts (scope §13 — Scan)."""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.api.pagination import Page
from app.repositories.reachability import ReachabilityRow

Verdict = Literal["reachable", "unreachable", "unknown"]


class ReachabilityResponse(BaseModel):
    """One contact, with the evidence behind its verdict rather than only the verdict.

    Both timestamps are returned because which is *current* is the whole question: a number can be
    deactivated after having been reachable, and an operator looking at a surprising row needs to
    see that the delivery was in March and the refusal was last week. A bare label would have to be
    taken on trust.
    """

    contact_id: uuidlib.UUID
    full_name: str | None
    phone_e164: str | None
    verdict: Verdict
    last_delivered_at: datetime | None = Field(
        description="When WhatsApp last confirmed a message reached this number."
    )
    last_undeliverable_at: datetime | None = Field(
        description="When WhatsApp last refused this number as not a WhatsApp user (error 131026)."
    )

    @classmethod
    def from_row(cls, row: ReachabilityRow) -> ReachabilityResponse:
        return cls(
            contact_id=uuidlib.UUID(row.contact.public_id),
            full_name=row.contact.full_name,
            phone_e164=row.contact.phone_e164,
            verdict=row.verdict,
            last_delivered_at=row.last_delivered_at,
            last_undeliverable_at=row.last_undeliverable_at,
        )


class ReachabilityCounts(BaseModel):
    reachable: int
    unreachable: int
    unknown: int


class ReachabilityPage(BaseModel):
    data: list[ReachabilityResponse]
    counts: ReachabilityCounts
    page: Page
