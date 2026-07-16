"""API key model (Doc 03 §4.4).

The raw secret is never stored — only its SHA-256 ``key_hash`` and a short ``key_prefix``
for identification. Keys carry optional permission ``scopes`` and expiry, and are revocable.
Inbound API-key *authentication* is out of Module 1 scope (future public-API module); this
model + CRUD manage the keys' lifecycle only.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CHAR, JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IntPKMixin, UUIDMixin, utcnow
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6


class ApiKey(IntPKMixin, UUIDMixin, Base):
    """A hashed, scoped, revocable API key (Doc 03 §4.4)."""

    __tablename__ = "api_keys"
    __table_args__ = (
        Index("ix_apikeys_org", "organization_id", "revoked_at"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_apikeys_org", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    key_prefix: Mapped[str] = mapped_column(CHAR(12), nullable=False)
    key_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False, unique=True)
    scopes_json: Mapped[object | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<ApiKey id={self.id} prefix={self.key_prefix!r}>"
