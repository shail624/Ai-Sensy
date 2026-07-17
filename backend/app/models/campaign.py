"""Campaign registry models (Doc 03 §8.1/§8.3) — FR-CAM-01/02/10.

A campaign is a **plan** until it is sent: which number, which template, and which contacts. This
step builds only that plan and the roster it resolves to.

``campaigns`` carries denormalized counters so a dashboard reads one row instead of aggregating a
100M+ table (Doc 03 §8.1); ``campaign_recipients`` remains the authoritative per-recipient truth.

``uq_crecip_campaign_contact`` is the load-bearing constraint (Doc 03 §8.3): one row per
(campaign, contact) is what will later make a resumed or retried send incapable of contacting the
same person twice. It exists now because the roster is materialized now.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CHAR, JSON, CheckConstraint, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import (
    AuditMixin,
    IntPKMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
    utcnow,
)
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, int_id, small_uint

# campaigns.status (Doc 03 §8.1)
CAMPAIGN_DRAFT = "draft"
CAMPAIGN_SCHEDULED = "scheduled"
CAMPAIGN_QUEUED = "queued"
CAMPAIGN_RUNNING = "running"
CAMPAIGN_PAUSED = "paused"
CAMPAIGN_COMPLETED = "completed"
CAMPAIGN_CANCELLED = "cancelled"
CAMPAIGN_FAILED = "failed"
CAMPAIGN_STATUSES = (
    CAMPAIGN_DRAFT,
    CAMPAIGN_SCHEDULED,
    CAMPAIGN_QUEUED,
    CAMPAIGN_RUNNING,
    CAMPAIGN_PAUSED,
    CAMPAIGN_COMPLETED,
    CAMPAIGN_CANCELLED,
    CAMPAIGN_FAILED,
)
#: States the operator still owns. Once a campaign has been handed to the send fabric, editing it
#: would change what is already in flight (Doc 04 §17 → 409).
CAMPAIGN_EDITABLE = (CAMPAIGN_DRAFT,)
#: A campaign may only be handed to the send fabric from a state where nothing is in flight.
CAMPAIGN_DISPATCHABLE = (CAMPAIGN_DRAFT, CAMPAIGN_SCHEDULED)
#: Recipient states that still owe a send — what a resumed dispatch picks up (FR-CAM-09).
RECIPIENT_UNSENT = ("pending",)

# campaigns.audience_type (Doc 03 §8.1)
AUDIENCE_SEGMENT = "segment"
AUDIENCE_TAG = "tag"
AUDIENCE_LIST = "list"
AUDIENCE_UPLOAD = "upload"
AUDIENCE_TYPES = (AUDIENCE_SEGMENT, AUDIENCE_TAG, AUDIENCE_LIST, AUDIENCE_UPLOAD)

# campaign_batches.status (Doc 03 §8.4)
BATCH_PENDING = "pending"
BATCH_IN_PROGRESS = "in_progress"
BATCH_DONE = "done"
BATCH_FAILED = "failed"
BATCH_STATUSES = (BATCH_PENDING, BATCH_IN_PROGRESS, BATCH_DONE, BATCH_FAILED)

# campaign_recipients.status (Doc 03 §8.3)
RECIPIENT_PENDING = "pending"
RECIPIENT_QUEUED = "queued"
RECIPIENT_SENT = "sent"
RECIPIENT_DELIVERED = "delivered"
RECIPIENT_READ = "read"
RECIPIENT_FAILED = "failed"
RECIPIENT_SKIPPED = "skipped"
RECIPIENT_CANCELLED = "cancelled"
RECIPIENT_STATUSES = (
    RECIPIENT_PENDING,
    RECIPIENT_QUEUED,
    RECIPIENT_SENT,
    RECIPIENT_DELIVERED,
    RECIPIENT_READ,
    RECIPIENT_FAILED,
    RECIPIENT_SKIPPED,
    RECIPIENT_CANCELLED,
)


class Campaign(
    IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, AuditMixin, VersionMixin, Base
):
    """A broadcast: one template, from one number, to a resolved audience (Doc 03 §8.1)."""

    __tablename__ = "campaigns"
    __table_args__ = (
        Index("ix_campaigns_org_status", "organization_id", "status", "created_at"),
        Index("ix_campaigns_template", "template_id"),
        Index("ix_campaigns_number", "phone_number_id"),
        CheckConstraint(
            "status IN ('draft','scheduled','queued','running','paused','completed',"
            "'cancelled','failed')",
            name="ck_campaigns_status",
        ),
        CheckConstraint(
            "audience_type IN ('segment','tag','list','upload')", name="ck_campaigns_audience"
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_campaigns_org", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone_number_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("phone_numbers.id", name="fk_campaigns_number", ondelete="RESTRICT"),
        nullable=False,
    )
    template_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("message_templates.id", name="fk_campaigns_template", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=CAMPAIGN_DRAFT)
    audience_type: Mapped[str] = mapped_column(String(16), nullable=False)
    #: Which segment/tag/list the audience came from — the question, not the answer.
    audience_ref_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    #: Template variable → contact field/attribute (FR-CAM-01's variable mapping).
    variable_map_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    #: Denormalized counters (Doc 03 §8.1) — O(1) dashboard reads over a 100M+ roster.
    total_recipients: Mapped[int] = mapped_column(int_id(), nullable=False, default=0)
    queued_count: Mapped[int] = mapped_column(int_id(), nullable=False, default=0)
    sent_count: Mapped[int] = mapped_column(int_id(), nullable=False, default=0)
    delivered_count: Mapped[int] = mapped_column(int_id(), nullable=False, default=0)
    read_count: Mapped[int] = mapped_column(int_id(), nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(int_id(), nullable=False, default=0)
    replied_count: Mapped[int] = mapped_column(int_id(), nullable=False, default=0)
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=0)
    cost_currency: Mapped[str | None] = mapped_column(CHAR(3), nullable=True)
    send_rate_mps: Mapped[int | None] = mapped_column(small_uint(), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)

    @property
    def is_editable(self) -> bool:
        return self.status in CAMPAIGN_EDITABLE

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Campaign {self.name!r} {self.status}>"


class CampaignRecipient(IntPKMixin, Base):
    """One contact's place in a campaign (Doc 03 §8.3).

    Partitioned monthly on MySQL, so it takes the composite ``(id, created_at)`` primary key that
    requires and holds no foreign keys — ``campaign_id``/``contact_id`` are app-enforced.
    """

    __tablename__ = "campaign_recipients"
    __table_args__ = (
        # One send per contact per campaign. The constraint is what makes a resumed or retried
        # dispatch incapable of messaging someone twice (Doc 03 §8.3; FR-CAM-06/08).
        Index("uq_crecip_campaign_contact", "campaign_id", "contact_id", unique=True),
        Index("ix_crecip_campaign_status", "campaign_id", "status"),
        Index("ix_crecip_status_created", "status", "created_at"),
        Index("ix_crecip_wamid", "wamid"),
        Index("ix_crecip_batch", "batch_id"),
        MYSQL_TABLE_ARGS,
    )

    campaign_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    contact_id: Mapped[int] = mapped_column(big_id(), nullable=False)
    #: Set when the send produces a ledger row; the link between plan and outcome.
    message_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    wamid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=RECIPIENT_PENDING)
    #: The variables this contact's message will carry, resolved when the roster is materialized.
    variables_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(24), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(String(512), nullable=True)
    retry_count: Mapped[int] = mapped_column(small_uint(), nullable=False, default=0)
    cost_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    batch_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    queued_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<CampaignRecipient campaign={self.campaign_id} {self.status}>"


class CampaignBatch(IntPKMixin, Base):
    """A checkpoint over a slice of the roster (Doc 03 §8.4; FR-CAM-09).

    Batches exist so a crash costs a batch, not a campaign: ``batch_index`` + ``status`` tell a
    restarted worker exactly which slices still owe work, and the recipients inside carry the same
    ``batch_id`` so an already-sent row is skipped rather than sent twice.

    The live queue is Celery/Redis; this table is the **durable** checkpoint, so a Redis flush
    loses throughput rather than state (Doc 03 §8.4, NFR-DR-06).
    """

    __tablename__ = "campaign_batches"
    __table_args__ = (
        Index("uq_cbatch_campaign_idx", "campaign_id", "batch_index", unique=True),
        Index("ix_cbatch_status", "campaign_id", "status"),
        MYSQL_TABLE_ARGS,
    )

    campaign_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("campaigns.id", name="fk_cbatch_campaign", ondelete="CASCADE"),
        nullable=False,
    )
    batch_index: Mapped[int] = mapped_column(int_id(), nullable=False)
    size: Mapped[int] = mapped_column(int_id(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=BATCH_PENDING)
    dispatched_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<CampaignBatch campaign={self.campaign_id} #{self.batch_index} {self.status}>"
