"""Template registry models (Doc 03 §7.1) — FR-TPL-01/02/03.

A template is **Meta's object, mirrored** — we do not own its approval state, only what we
submitted and what Meta last told us. That asymmetry drives the design: ``components_json`` holds
the whole definition (variable by nature), while name/language/category/status are **promoted
columns** so the registry can be filtered and indexed without opening the JSON (Doc 03 §7.1).

``uq_tpl_waba_name_lang`` mirrors Meta's own uniqueness rule — one template per (WABA, name,
language) — which is what makes sync an idempotent upsert rather than a diff.

``template_versions`` keeps prior definitions immutable: an edited template is a new version, so
what a message was sent against remains readable after the template moves on.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, CheckConstraint, ForeignKey, Index, String
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

# message_templates.category (Doc 03 §7.1)
CATEGORY_MARKETING = "marketing"
CATEGORY_UTILITY = "utility"
CATEGORY_AUTHENTICATION = "authentication"
CATEGORIES = (CATEGORY_MARKETING, CATEGORY_UTILITY, CATEGORY_AUTHENTICATION)

# message_templates.status (Doc 03 §7.1)
TPL_DRAFT = "draft"
TPL_PENDING = "pending"
TPL_APPROVED = "approved"
TPL_REJECTED = "rejected"
TPL_PAUSED = "paused"
TPL_DISABLED = "disabled"
TPL_STATUSES = (TPL_DRAFT, TPL_PENDING, TPL_APPROVED, TPL_REJECTED, TPL_PAUSED, TPL_DISABLED)

#: Only an approved template may be sent (FR-TPL-03; Doc 04 §18.2 "subject to approval").
TPL_SENDABLE = (TPL_APPROVED,)
#: States we own; anything else is Meta's to change, and an edit would be overwritten by sync.
TPL_EDITABLE = (TPL_DRAFT, TPL_REJECTED)


class MessageTemplate(
    IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, AuditMixin, VersionMixin, Base
):
    """A template on a WABA, mirrored from Meta (Doc 03 §7.1)."""

    __tablename__ = "message_templates"
    __table_args__ = (
        Index("uq_tpl_waba_name_lang", "waba_id", "name", "language", unique=True),
        Index("ix_tpl_org_status", "organization_id", "status"),
        Index("ix_tpl_category", "organization_id", "category"),
        CheckConstraint(
            "category IN ('marketing','utility','authentication')", name="ck_tpl_category"
        ),
        CheckConstraint(
            "status IN ('draft','pending','approved','rejected','paused','disabled')",
            name="ck_tpl_status",
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_tpl_org", ondelete="CASCADE"),
        nullable=False,
    )
    waba_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("whatsapp_business_accounts.id", name="fk_tpl_waba", ondelete="CASCADE"),
        nullable=False,
    )
    #: Meta's id, once it has one. NULL means a draft Meta has never seen.
    meta_template_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=TPL_DRAFT)
    #: Why Meta said no — surfaced verbatim so an operator can act on it (FR-TPL-03).
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quality_score: Mapped[str | None] = mapped_column(String(16), nullable=True)
    #: The whole definition: header/body/footer/buttons (Doc 04 §15's shape).
    components_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    #: Derived from the placeholders, so a send can be checked without re-parsing the definition.
    variable_count: Mapped[int] = mapped_column(small_uint(), nullable=False, default=0)
    has_media_header: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)

    @property
    def is_sendable(self) -> bool:
        return self.status in TPL_SENDABLE and self.deleted_at is None

    @property
    def is_editable(self) -> bool:
        return self.status in TPL_EDITABLE

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<MessageTemplate {self.name}/{self.language} {self.status}>"


class TemplateVersion(IntPKMixin, Base):
    """An immutable snapshot of a template's definition (Doc 03 §7.1)."""

    __tablename__ = "template_versions"
    __table_args__ = (
        Index("uq_tplver_template_ver", "template_id", "version_no", unique=True),
        MYSQL_TABLE_ARGS,
    )

    template_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("message_templates.id", name="fk_tplver_template", ondelete="CASCADE"),
        nullable=False,
    )
    version_no: Mapped[int] = mapped_column(int_id(), nullable=False)
    components_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(datetime6(), nullable=False, default=utcnow)
    created_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<TemplateVersion template_id={self.template_id} v{self.version_no}>"
