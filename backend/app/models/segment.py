"""Segment models (Doc 03 §6.4) — FR-CON-10.

A segment is a **saved, dynamic filter** over contacts. Rules are normalized into rows (a
rule tree) so they stay inspectable and index-assisted; ``compiled_json`` caches the compiled
tree and ``cached_count``/``last_evaluated_at`` denormalize the last evaluated size.

Note: Doc 03 §6.4 defines no ``row_version`` for segments, so they carry no optimistic-
concurrency counter (unlike ``contacts``).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import IntPKMixin, SoftDeleteMixin, TimestampMixin, UUIDMixin, utcnow
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, int_id, small_uint

MATCH_ALL = "all"
MATCH_ANY = "any"
MATCH_TYPES = (MATCH_ALL, MATCH_ANY)

SOURCE_CONTACT = "contact"
SOURCE_ATTRIBUTE = "attribute"
SOURCE_TAG = "tag"
SOURCE_ENGAGEMENT = "engagement"
FIELD_SOURCES = (SOURCE_CONTACT, SOURCE_ATTRIBUTE, SOURCE_TAG, SOURCE_ENGAGEMENT)


class Segment(IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A saved, dynamic contact filter (Doc 03 §6.4)."""

    __tablename__ = "segments"
    __table_args__ = (
        Index("uq_segments_org_name", "organization_id", "name", unique=True),
        CheckConstraint("match_type IN ('all','any')", name="ck_segments_match"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_segments_org", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    match_type: Mapped[str] = mapped_column(String(8), nullable=False, default=MATCH_ALL)
    compiled_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_dynamic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cached_count: Mapped[int | None] = mapped_column(int_id(), nullable=True)
    last_evaluated_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    created_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)

    rules: Mapped[list[SegmentRule]] = relationship(
        "SegmentRule",
        lazy="selectin",
        order_by="SegmentRule.group_index, SegmentRule.id",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Segment id={self.id} name={self.name!r}>"


class SegmentRule(IntPKMixin, Base):
    """One normalized rule row within a segment's rule tree (Doc 03 §6.4)."""

    __tablename__ = "segment_rules"
    __table_args__ = (
        Index("ix_segrules_segment", "segment_id", "group_index"),
        CheckConstraint(
            "field_source IN ('contact','attribute','tag','engagement')",
            name="ck_segrules_source",
        ),
        MYSQL_TABLE_ARGS,
    )

    segment_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("segments.id", name="fk_segrules_segment", ondelete="CASCADE"),
        nullable=False,
    )
    group_index: Mapped[int] = mapped_column(small_uint(), nullable=False, default=0)
    field_source: Mapped[str] = mapped_column(String(24), nullable=False)
    field_key: Mapped[str] = mapped_column(String(60), nullable=False)
    operator: Mapped[str] = mapped_column(String(24), nullable=False)
    value_json: Mapped[object | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<SegmentRule {self.field_source}.{self.field_key} {self.operator}>"
