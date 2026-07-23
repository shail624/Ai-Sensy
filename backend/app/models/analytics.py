"""Analytics rollup models (Doc 15 §9) — Phase 8 Analytics & Reporting.

Six **fact** tables plus one **control** table. Every fact row is a pre-aggregated bucket of
operational history at hourly (or, after consolidation, daily) grain, scoped to one organization.

Three properties define this module and are enforced by its shape:

* **Derived, never authoritative** (Doc 15 §4.1). A rollup is a pure function of source rows in a
  closed time bucket. The tables can be dropped and rebuilt from `messages`, `campaign_recipients`,
  `conversations`, `task_events` and `contacts` at any time. Nothing here is a second source of
  truth.
* **Additive measures only** (Doc 15 §6.2). Columns hold counts and sums — never ratios, never
  averages. The mean of hourly means is not the daily mean, so every rate is computed at *read*
  time from two stored counters (hence the paired ``*_sum`` / ``*_count`` columns). This is what
  makes arbitrary date ranges and granularities correct by construction.
* **One writer, regenerated in place** (Doc 15 §6.3). The rollup service deletes and re-inserts a
  bucket inside one transaction, so no row is ever concurrently edited.

Consequently these models carry **no** ``uuid`` (rollups are never addressed individually by a
client), **no** ``deleted_at`` (they are regenerated, not retired) and **no** ``row_version`` (no
optimistic concurrency to guard). They use ``IntPKMixin`` + ``TimestampMixin`` only.

Unlike the partitioned sources they aggregate, these tables are **not partitioned** (Doc 15 §21.2):
at hourly grain the row counts are small, so they keep real foreign keys to ``organizations``,
matching ``tasks`` and ``internal_notes``.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IntPKMixin, TimestampMixin
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, int_id

# --- Bucket grain (Doc 15 §21.4) ---------------------------------------------------------------
#: Hourly rows are the primary grain; the nightly job also writes daily consolidation rows so long
#: ranges stay cheap after hourly rows are pruned at 90 days.
GRAIN_HOUR = "hour"
GRAIN_DAY = "day"
GRAINS: tuple[str, ...] = (GRAIN_HOUR, GRAIN_DAY)

# --- Rollup kinds, as recorded on ``analytics_rollup_runs`` (Doc 15 §9.7) -----------------------
KIND_MESSAGES = "messages"
KIND_FAILURES = "failures"
KIND_CAMPAIGNS = "campaigns"
KIND_CONVERSATIONS = "conversations"
KIND_TASKS = "tasks"
KIND_CONTACTS = "contacts"
ROLLUP_KINDS: tuple[str, ...] = (
    KIND_MESSAGES,
    KIND_FAILURES,
    KIND_CAMPAIGNS,
    KIND_CONVERSATIONS,
    KIND_TASKS,
    KIND_CONTACTS,
)

# --- Run outcomes (Doc 15 §23.1) ---------------------------------------------------------------
RUN_OK = "ok"
RUN_FAILED = "failed"
RUN_SKIPPED = "skipped"
RUN_STATUSES: tuple[str, ...] = (RUN_OK, RUN_FAILED, RUN_SKIPPED)

#: Column widths (mirrored by the migration and the schemas).
GRAIN_LENGTH = 8
KIND_LENGTH = 32
STATUS_LENGTH = 16
DIRECTION_LENGTH = 16
MESSAGE_TYPE_LENGTH = 24
ERROR_CODE_LENGTH = 24


# --- Shared column factories -------------------------------------------------------------------
# Each fact table repeats the same scope/bucket/measure columns. These factories keep one
# definition of each without introducing an inheritance hierarchy the schema does not want
# (SQLAlchemy needs a fresh column object per model, so these are functions, not constants).


def _organization_id(constraint_name: str) -> Mapped[int]:
    """The org scope, with a real FK (these tables are not partitioned, Doc 15 §21.2)."""
    return mapped_column(
        big_id(),
        ForeignKey("organizations.id", name=constraint_name, ondelete="CASCADE"),
        nullable=False,
    )


def _bucket_start() -> Mapped[datetime]:
    """Start of the bucket in **UTC**; local days are folded at read time (Doc 15 §6.1)."""
    return mapped_column(datetime6(), nullable=False)


def _grain() -> Mapped[str]:
    return mapped_column(String(GRAIN_LENGTH), nullable=False, default=GRAIN_HOUR)


def _counter() -> Mapped[int]:
    """An additive count. Never a ratio (Doc 15 §6.2)."""
    return mapped_column(int_id(), nullable=False, default=0)


def _accumulator() -> Mapped[int]:
    """An additive sum wide enough for milliseconds/seconds/micros over a bucket."""
    return mapped_column(big_id(), nullable=False, default=0)


class AnalyticsMessageRollup(IntPKMixin, TimestampMixin, Base):
    """Delivery, read and failure volume over the message ledger (Doc 15 §9.1, FR-AN-01)."""

    __tablename__ = "analytics_message_rollups"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "grain",
            "bucket_start",
            "phone_number_id",
            "direction",
            "message_type",
            name="uq_amr_grain",
        ),
        Index("ix_amr_org_bucket", "organization_id", "grain", "bucket_start"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = _organization_id("fk_amr_organization_id")
    grain: Mapped[str] = _grain()
    bucket_start: Mapped[datetime] = _bucket_start()
    #: Dimension — the sending/receiving number (internal id; resolved at read time, Doc 15 §6.2).
    phone_number_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    direction: Mapped[str] = mapped_column(String(DIRECTION_LENGTH), nullable=False)
    message_type: Mapped[str] = mapped_column(String(MESSAGE_TYPE_LENGTH), nullable=False)

    accepted_count: Mapped[int] = _counter()
    sent_count: Mapped[int] = _counter()
    delivered_count: Mapped[int] = _counter()
    read_count: Mapped[int] = _counter()
    failed_count: Mapped[int] = _counter()
    #: Rate-card cost in micro-units of the organization's currency (Doc 15 §11.6).
    cost_micros: Mapped[int] = _accumulator()
    #: Σ (delivered_at − sent_at) and its denominator — averaged at read time, never stored.
    delivery_latency_ms_sum: Mapped[int] = _accumulator()
    delivery_latency_count: Mapped[int] = _counter()

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<AnalyticsMessageRollup org={self.organization_id} at={self.bucket_start}>"


class AnalyticsFailureRollup(IntPKMixin, TimestampMixin, Base):
    """Failures grouped by Meta error code (Doc 15 §9.2, FR-AN-07).

    Guidance for each code ships as reference data in code, not as a table (Doc 15 §9.2).
    """

    __tablename__ = "analytics_failure_rollups"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "grain",
            "bucket_start",
            "phone_number_id",
            "error_code",
            name="uq_afr_grain",
        ),
        Index("ix_afr_org_bucket_code", "organization_id", "grain", "bucket_start", "error_code"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = _organization_id("fk_afr_organization_id")
    grain: Mapped[str] = _grain()
    bucket_start: Mapped[datetime] = _bucket_start()
    phone_number_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    error_code: Mapped[str] = mapped_column(String(ERROR_CODE_LENGTH), nullable=False)

    failure_count: Mapped[int] = _counter()

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<AnalyticsFailureRollup code={self.error_code!r} n={self.failure_count}>"


class AnalyticsCampaignRollup(IntPKMixin, TimestampMixin, Base):
    """Per-campaign funnel and spend (Doc 15 §9.3, FR-AN-02/03)."""

    __tablename__ = "analytics_campaign_rollups"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "grain", "bucket_start", "campaign_id", name="uq_acr_grain"
        ),
        Index("ix_acr_org_campaign_bucket", "organization_id", "campaign_id", "bucket_start"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = _organization_id("fk_acr_organization_id")
    grain: Mapped[str] = _grain()
    bucket_start: Mapped[datetime] = _bucket_start()
    campaign_id: Mapped[int] = mapped_column(big_id(), nullable=False)

    targeted_count: Mapped[int] = _counter()
    sent_count: Mapped[int] = _counter()
    delivered_count: Mapped[int] = _counter()
    read_count: Mapped[int] = _counter()
    failed_count: Mapped[int] = _counter()
    skipped_count: Mapped[int] = _counter()
    #: Populated by Phase 8b click tracking (Doc 15 §13); zero until then.
    click_count: Mapped[int] = _counter()
    cost_micros: Mapped[int] = _accumulator()

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<AnalyticsCampaignRollup campaign={self.campaign_id} at={self.bucket_start}>"


class AnalyticsConversationRollup(IntPKMixin, TimestampMixin, Base):
    """Inbox throughput and responsiveness (Doc 15 §9.4, FR-AN-02/06).

    The agent is a **dimension here**, not a separate fact table: agent performance (Doc 15 §17) is
    this table grouped by ``assigned_user_id``, joined with the task rollup.
    """

    __tablename__ = "analytics_conversation_rollups"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "grain",
            "bucket_start",
            "phone_number_id",
            "assigned_user_id",
            name="uq_acvr_grain",
        ),
        Index(
            "ix_acvr_org_bucket_user",
            "organization_id",
            "grain",
            "bucket_start",
            "assigned_user_id",
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = _organization_id("fk_acvr_organization_id")
    grain: Mapped[str] = _grain()
    bucket_start: Mapped[datetime] = _bucket_start()
    phone_number_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    #: NULL = unassigned; the unassigned backlog is a first-class row, not an absence.
    assigned_user_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)

    opened_count: Mapped[int] = _counter()
    resolved_count: Mapped[int] = _counter()
    inbound_message_count: Mapped[int] = _counter()
    outbound_message_count: Mapped[int] = _counter()
    handled_count: Mapped[int] = _counter()
    first_response_seconds_sum: Mapped[int] = _accumulator()
    first_response_count: Mapped[int] = _counter()
    resolution_seconds_sum: Mapped[int] = _accumulator()
    resolution_count: Mapped[int] = _counter()

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<AnalyticsConversationRollup user={self.assigned_user_id} at={self.bucket_start}>"


class AnalyticsTaskRollup(IntPKMixin, TimestampMixin, Base):
    """Follow-up engine metrics (Doc 15 §9.5, FR-AN-09), redeeming the Doc 14 §12 reservation.

    Computed from ``task_events`` (immutable history) rather than ``tasks``, so a task edited after
    the fact cannot rewrite its own history — the auditability Doc 14 §12 promised.
    """

    __tablename__ = "analytics_task_rollups"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "grain",
            "bucket_start",
            "assigned_agent_id",
            "task_type",
            name="uq_atr_grain",
        ),
        Index(
            "ix_atr_org_bucket_agent",
            "organization_id",
            "grain",
            "bucket_start",
            "assigned_agent_id",
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = _organization_id("fk_atr_organization_id")
    grain: Mapped[str] = _grain()
    bucket_start: Mapped[datetime] = _bucket_start()
    assigned_agent_id: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    task_type: Mapped[str] = mapped_column(String(MESSAGE_TYPE_LENGTH), nullable=False)

    created_count: Mapped[int] = _counter()
    completed_count: Mapped[int] = _counter()
    #: ``completed_at <= due_at`` — the numerator of on-time completion % (Doc 15 §11.3).
    completed_on_time_count: Mapped[int] = _counter()
    skipped_count: Mapped[int] = _counter()
    cancelled_count: Mapped[int] = _counter()
    reopened_count: Mapped[int] = _counter()
    #: Open tasks whose ``due_at`` elapsed inside this bucket.
    overdue_entered_count: Mapped[int] = _counter()
    time_to_complete_seconds_sum: Mapped[int] = _accumulator()
    time_to_complete_count: Mapped[int] = _counter()

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<AnalyticsTaskRollup agent={self.assigned_agent_id} at={self.bucket_start}>"


class AnalyticsContactRollup(IntPKMixin, TimestampMixin, Base):
    """Customer growth and opt-in health (Doc 15 §9.6, FR-AN-08).

    Org-wide: segment breakdowns drill down against the live contact search rather than being
    pre-aggregated here (Doc 15 §16).
    """

    __tablename__ = "analytics_contact_rollups"
    __table_args__ = (
        UniqueConstraint("organization_id", "grain", "bucket_start", name="uq_actr_grain"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = _organization_id("fk_actr_organization_id")
    grain: Mapped[str] = _grain()
    bucket_start: Mapped[datetime] = _bucket_start()

    created_count: Mapped[int] = _counter()
    opted_in_count: Mapped[int] = _counter()
    opted_out_count: Mapped[int] = _counter()
    #: Inbound after >= 30 days of silence.
    reactivated_count: Mapped[int] = _counter()
    #: Distinct contacts active within the bucket. Additive across buckets only as
    #: "active customer-hours" — not a unique customer count (Doc 15 §11.4, Q3).
    active_count: Mapped[int] = _counter()

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<AnalyticsContactRollup org={self.organization_id} at={self.bucket_start}>"


class AnalyticsRollupRun(IntPKMixin, TimestampMixin, Base):
    """Per-organization, per-kind watermark and last outcome (Doc 15 §9.7, §23).

    The scheduler reads it to decide what to compute, ``GET /analytics/freshness`` reads it so a
    dashboard can state how stale it is, and recovery reads it to choose a replay window.
    """

    __tablename__ = "analytics_rollup_runs"
    __table_args__ = (
        UniqueConstraint("organization_id", "kind", name="uq_arr_org_kind"),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = _organization_id("fk_arr_organization_id")
    kind: Mapped[str] = mapped_column(String(KIND_LENGTH), nullable=False)
    #: Last bucket successfully computed; freshness is ``now - watermark_at``.
    watermark_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(STATUS_LENGTH), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(int_id(), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<AnalyticsRollupRun kind={self.kind!r} watermark={self.watermark_at}>"


__all__ = [
    "GRAINS",
    "GRAIN_DAY",
    "GRAIN_HOUR",
    "KIND_CAMPAIGNS",
    "KIND_CONTACTS",
    "KIND_CONVERSATIONS",
    "KIND_FAILURES",
    "KIND_MESSAGES",
    "KIND_TASKS",
    "ROLLUP_KINDS",
    "RUN_FAILED",
    "RUN_OK",
    "RUN_SKIPPED",
    "RUN_STATUSES",
    "AnalyticsCampaignRollup",
    "AnalyticsContactRollup",
    "AnalyticsConversationRollup",
    "AnalyticsFailureRollup",
    "AnalyticsMessageRollup",
    "AnalyticsRollupRun",
    "AnalyticsTaskRollup",
]
