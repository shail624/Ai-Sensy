"""Audit-log read schemas (Doc 04 §22)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from app.api.pagination import Page
from app.core.security import unpack_ip
from app.models.audit import AuditLog
from app.services.audit_service import AuditService


class AuditLogResponse(BaseModel):
    id: int
    action: str
    actor_type: str
    actor: str | None  # actor user public UUID (None = system)
    entity_type: str | None
    entity_id: int | None
    ip_address: str | None
    user_agent: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    metadata: dict[str, Any] | None
    created_at: datetime
    #: Whether the row still reproduces its own stored digest: ``verified``, ``verified_legacy``
    #: (written before the timestamp was covered, so its content is intact but its time is not
    #: vouched for), ``mismatch`` (content changed after the write), or ``unhashed``. Carried on
    #: the row itself because the person reading an audit trail is exactly the person who needs to
    #: know whether it can be trusted, and a digest nothing ever recomputes protects nothing.
    #: Spelled out rather than left as `str` so the generated client gets the four verdicts,
    #: not a free-text field it has to guess at.
    integrity: Literal["verified", "verified_legacy", "mismatch", "unhashed"]

    @classmethod
    def from_entry(cls, entry: AuditLog, actor_uuid: str | None) -> AuditLogResponse:
        return cls(
            id=entry.id,
            action=entry.action,
            actor_type=entry.actor_type,
            actor=actor_uuid,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            ip_address=unpack_ip(entry.ip_address),
            user_agent=entry.user_agent,
            before=entry.before_json,
            after=entry.after_json,
            metadata=entry.metadata_json,
            created_at=entry.created_at,
            integrity=AuditService.verify(entry),
        )


class AuditLogPage(BaseModel):
    data: list[AuditLogResponse]
    page: Page
