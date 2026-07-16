"""Audit-log model (Doc 03 §11.2).

Tamper-evident, append-only record of every security-relevant mutation (Doc 01 FR-ADM-02 /
NFR-SEC-07): no ``updated_at``, no soft delete. An optional hash chain
(``prev_hash``/``row_hash``) makes tampering detectable. On MySQL the physical table uses a
composite ``(id, created_at)`` primary key and monthly range partitioning (applied in the
migration, Doc 03 §11.2); the ORM maps the surrogate ``id`` as the identity key.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CHAR, JSON, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import utcnow
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, packed_ip

ACTOR_USER = "user"
ACTOR_SYSTEM = "system"
ACTOR_API_KEY = "api_key"


class AuditLog(Base):
    """One immutable audit entry (Doc 03 §11.2)."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_actor", "actor_user_id", "created_at"),
        Index("ix_audit_entity", "entity_type", "entity_id", "created_at"),
        Index("ix_audit_action", "action", "created_at"),
        Index("ix_audit_org", "organization_id", "created_at"),
        MYSQL_TABLE_ARGS,
    )

    id: Mapped[int] = mapped_column(big_id(), primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    actor_user_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(12), nullable=False, default=ACTOR_USER)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    ip_address: Mapped[bytes | None] = mapped_column(packed_ip(), nullable=True)
    before_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    prev_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    row_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<AuditLog id={self.id} action={self.action!r}>"
