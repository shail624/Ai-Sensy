"""Audit-log read schemas (Doc 04 §22)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.api.pagination import Page
from app.core.security import unpack_ip
from app.models.audit import AuditLog


class AuditLogResponse(BaseModel):
    id: int
    action: str
    actor_type: str
    actor: str | None  # actor user public UUID (None = system)
    entity_type: str | None
    entity_id: int | None
    ip_address: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    metadata: dict[str, Any] | None
    created_at: datetime

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
            before=entry.before_json,
            after=entry.after_json,
            metadata=entry.metadata_json,
            created_at=entry.created_at,
        )


class AuditLogPage(BaseModel):
    data: list[AuditLogResponse]
    page: Page
