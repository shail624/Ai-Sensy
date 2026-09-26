"""Organization-shared filter presets for the read-only Chat History workspace."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IntPKMixin, TimestampMixin, UUIDMixin
from app.db.types import MYSQL_TABLE_ARGS, big_id


class ConversationHistoryView(IntPKMixin, UUIDMixin, TimestampMixin, Base):
    """A validated filter definition visible to every inbox reader in one organization."""

    __tablename__ = "conversation_history_views"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_conversation_history_views_org_name"),
        Index(
            "ix_conversation_history_views_org_created",
            "organization_id",
            "created_at",
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    created_by_user_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    filters_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
