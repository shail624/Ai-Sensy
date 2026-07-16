"""Lead pipeline & stage models (Doc 07 §19, §23.2) — additive to Doc 03.

Doc 07 defines these **logically** (no DDL) and requires they reuse Doc 03 conventions
(BIGINT + UUIDv7 ids, timestamps, soft-delete). A pipeline is an ordered set of stages; the
platform ships a default pipeline (Doc 07 §19.2) and supports unlimited custom stages
reordered by ``position``. Archiving a stage/pipeline = soft delete.

Pipelines/stages are **configuration only** here. Attaching a stage to a lead
(``conversation_lead``/``lead_stage_transitions``) is per-conversation and belongs to the
Inbox/Messaging module, where the ``conversations`` table lives.
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import IntPKMixin, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.db.types import MYSQL_TABLE_ARGS, big_id

# Default pipeline shipped with the platform (Doc 07 §19.2), in order.
# (stage name, is_terminal)
DEFAULT_PIPELINE_NAME = "Default"
DEFAULT_STAGES: tuple[tuple[str, bool], ...] = (
    ("New Lead", False),
    ("Interested", False),
    ("Documents Received", False),
    ("Documents Pending", False),
    ("Verification Pending", False),
    ("Lead Confirmed", False),
    ("Activation Pending", False),
    ("Completed", True),
    ("Closed", True),
    ("Lost", True),
)


class LeadPipeline(IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A customizable lead pipeline definition (Doc 07 §23.2)."""

    __tablename__ = "lead_pipelines"
    __table_args__ = (
        Index("uq_lead_pipelines_org_name", "organization_id", "name", unique=True),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_pipelines_org", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    stages: Mapped[list[LeadStage]] = relationship(
        "LeadStage",
        lazy="selectin",
        order_by="LeadStage.position",
        primaryjoin=(
            "and_(LeadPipeline.id == LeadStage.pipeline_id, LeadStage.deleted_at.is_(None))"
        ),
        viewonly=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<LeadPipeline id={self.id} name={self.name!r}>"


class LeadStage(IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """An ordered stage within a pipeline (Doc 07 §23.2)."""

    __tablename__ = "lead_stages"
    __table_args__ = (
        Index("uq_lead_stages_pipeline_name", "pipeline_id", "name", unique=True),
        Index("ix_lead_stages_pipeline_position", "pipeline_id", "position"),
        MYSQL_TABLE_ARGS,
    )

    pipeline_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("lead_pipelines.id", name="fk_stages_pipeline", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<LeadStage id={self.id} name={self.name!r} pos={self.position}>"
