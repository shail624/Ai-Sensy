"""Refresh-token and session models (Doc 03 §4.4).

Raw tokens are **never** stored — only their SHA-256 hash (``token_hash``). ``jti`` is the
token *family* id embedded in the access token (Doc 03 §4.4); ``parent_id`` records the
rotation lineage so a reused (already-rotated) token can be detected and the whole family
revoked (Doc 04 §11 — rotation with reuse detection). ``user_sessions`` backs the device
list and "log out everywhere" (Doc 01 NFR-SEC-06).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CHAR, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IntPKMixin, UUIDMixin, utcnow
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, packed_ip


class RefreshToken(IntPKMixin, UUIDMixin, Base):
    """A server-side, rotatable, revocable refresh token (Doc 03 §4.4)."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_rt_user_active", "user_id", "revoked_at", "expires_at"),
        Index("ix_rt_jti", "jti"),
        MYSQL_TABLE_ARGS,
    )

    user_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("users.id", name="fk_rt_user", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False, unique=True)
    jti: Mapped[str] = mapped_column(CHAR(36), nullable=False)
    # Rotation lineage — references refresh_tokens.id but intentionally unconstrained
    # (Doc 03 §4.4 declares no FK, so a pruned parent never blocks a child insert).
    parent_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[bytes | None] = mapped_column(packed_ip(), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<RefreshToken id={self.id} user_id={self.user_id} jti={self.jti}>"


class UserSession(IntPKMixin, UUIDMixin, Base):
    """A user device/session record (Doc 03 §4.4)."""

    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_sessions_user", "user_id", "revoked_at"),
        MYSQL_TABLE_ARGS,
    )

    user_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("users.id", name="fk_sessions_user", ondelete="CASCADE"),
        nullable=False,
    )
    # Links to the active refresh token for this session; unconstrained per Doc 03 §4.4.
    refresh_token_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    ip_address: Mapped[bytes | None] = mapped_column(packed_ip(), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<UserSession id={self.id} user_id={self.user_id}>"
