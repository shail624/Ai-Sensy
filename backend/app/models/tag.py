"""Tag models (Doc 03 §6.2) — unlimited contact tags (FR-CON-09).

``tags`` are organization-scoped labels; ``contact_tags`` is the M:N junction. The reverse
index ``(tag_id, contact_id)`` is essential for "all contacts with tag X" (segments/campaigns).
``usage_count`` is a denormalized counter maintained by the application.
"""

from __future__ import annotations

from sqlalchemy import CHAR, Column, ForeignKey, Index, String, Table
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IntPKMixin, SoftDeleteMixin, TimestampMixin, UUIDMixin, utcnow
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, int_id

# --- contacts ↔ tags junction (Doc 03 §6.2) ---------------------------------
contact_tags = Table(
    "contact_tags",
    Base.metadata,
    Column(
        "contact_id",
        big_id(),
        ForeignKey("contacts.id", name="fk_ct_contact", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "tag_id",
        big_id(),
        ForeignKey("tags.id", name="fk_ct_tag", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column("tagged_at", datetime6(), nullable=False, default=utcnow),
    Column("tagged_by", big_id(), nullable=True),
    Index("ix_ct_tag", "tag_id", "contact_id"),
    **MYSQL_TABLE_ARGS,
)


class Tag(IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """An organization-scoped contact tag (Doc 03 §6.2)."""

    __tablename__ = "tags"
    __table_args__ = (
        Index("uq_tags_org_name", "organization_id", "name", unique=True),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_tags_org", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    color: Mapped[str | None] = mapped_column(CHAR(7), nullable=True)  # '#RRGGBB'
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    usage_count: Mapped[int] = mapped_column(int_id(), nullable=False, default=0)
    created_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Tag id={self.id} name={self.name!r}>"
