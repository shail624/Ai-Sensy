"""Personal, tenant-scoped schedules for recurring Analytics report exports."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IntPKMixin, TimestampMixin, UUIDMixin, VersionMixin
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6, small_uint

REPORT_SCHEDULE_REPORTS = (
    "messages",
    "failures",
    "campaigns",
    "conversations",
    "tasks",
    "customers",
    "costs",
    "reactivation",
    "kyc",
    "service_levels",
    "team_productivity",
)
REPORT_SCHEDULE_FORMATS = ("pdf", "xlsx", "csv")
REPORT_SCHEDULE_PRESETS = (
    "yesterday",
    "last_7d",
    "last_30d",
    "this_month",
    "last_month",
    "this_quarter",
)
REPORT_SCHEDULE_GRANULARITIES = ("day", "week", "month")
REPORT_SCHEDULE_CADENCES = ("daily", "weekly", "monthly")
REPORT_SCHEDULE_WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def _in_clause(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class ReportSchedule(IntPKMixin, UUIDMixin, TimestampMixin, VersionMixin, Base):
    """A user's saved delivery instruction; due work becomes a normal export job."""

    __tablename__ = "report_schedules"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "owner_user_id", "name", name="uq_report_schedules_owner_name"
        ),
        Index("ix_report_schedules_due", "is_active", "next_run_at"),
        Index(
            "ix_report_schedules_owner_created",
            "organization_id",
            "owner_user_id",
            "created_at",
        ),
        CheckConstraint(_in_clause("report", REPORT_SCHEDULE_REPORTS), name="ck_rs_report"),
        CheckConstraint(_in_clause("format", REPORT_SCHEDULE_FORMATS), name="ck_rs_format"),
        CheckConstraint(_in_clause("preset", REPORT_SCHEDULE_PRESETS), name="ck_rs_preset"),
        CheckConstraint(
            _in_clause("granularity", REPORT_SCHEDULE_GRANULARITIES), name="ck_rs_granularity"
        ),
        CheckConstraint(_in_clause("cadence", REPORT_SCHEDULE_CADENCES), name="ck_rs_cadence"),
        CheckConstraint(
            "(cadence = 'daily' AND weekday IS NULL AND month_day IS NULL) OR "
            "(cadence = 'weekly' AND weekday IS NOT NULL AND month_day IS NULL) OR "
            "(cadence = 'monthly' AND weekday IS NULL AND month_day IS NOT NULL)",
            name="ck_rs_cadence_shape",
        ),
        CheckConstraint(
            "weekday IS NULL OR " + _in_clause("weekday", REPORT_SCHEDULE_WEEKDAYS),
            name="ck_rs_weekday",
        ),
        CheckConstraint(
            "month_day IS NULL OR (month_day >= 1 AND month_day <= 28)",
            name="ck_rs_month_day",
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    owner_user_id: Mapped[int] = mapped_column(
        big_id(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    report: Mapped[str] = mapped_column(String(32), nullable=False)
    format: Mapped[str] = mapped_column(String(8), nullable=False)
    preset: Mapped[str] = mapped_column(String(24), nullable=False)
    granularity: Mapped[str] = mapped_column(String(8), nullable=False)
    cadence: Mapped[str] = mapped_column(String(12), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    local_time: Mapped[str] = mapped_column(String(5), nullable=False)
    weekday: Mapped[str | None] = mapped_column(String(9), nullable=True)
    month_day: Mapped[int | None] = mapped_column(small_uint(), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    next_run_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
