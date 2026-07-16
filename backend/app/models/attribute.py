"""Custom attribute models (Doc 03 §6.3) — FR-CON-11.

Typed EAV: ``custom_attribute_definitions`` declares the schema; ``contact_attribute_values``
stores one value per (contact, attribute) in a **typed column** so filters hit the
``(attribute_id, value_*)`` indexes. Hot attributes (``is_indexed``) are additionally mirrored
into ``contacts.attributes_cache`` for fast list rendering.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import IntPKMixin, SoftDeleteMixin, TimestampMixin, UUIDMixin, utcnow
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6


class CustomAttributeDefinition(
    IntPKMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, Base
):
    """Declaration of a typed custom attribute (Doc 03 §6.3)."""

    __tablename__ = "custom_attribute_definitions"
    __table_args__ = (
        Index("uq_cad_org_key", "organization_id", "key_name", unique=True),
        CheckConstraint(
            "data_type IN ('string','number','datetime','boolean','enum')", name="ck_cad_type"
        ),
        MYSQL_TABLE_ARGS,
    )

    organization_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("organizations.id", name="fk_cad_org", ondelete="CASCADE"),
        nullable=False,
    )
    key_name: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    data_type: Mapped[str] = mapped_column(String(16), nullable=False)
    enum_values_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_indexed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_pii: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<CustomAttributeDefinition {self.key_name!r}:{self.data_type}>"


class ContactAttributeValue(IntPKMixin, Base):
    """One typed attribute value for a contact (Doc 03 §6.3)."""

    __tablename__ = "contact_attribute_values"
    __table_args__ = (
        Index("uq_cav_contact_attr", "contact_id", "attribute_id", unique=True),
        # Prefix index on MySQL (VARCHAR(1024) cannot be fully indexed); plain on SQLite.
        Index("ix_cav_attr_string", "attribute_id", "value_string", mysql_length={"value_string": 191}),
        Index("ix_cav_attr_number", "attribute_id", "value_number"),
        Index("ix_cav_attr_datetime", "attribute_id", "value_datetime"),
        MYSQL_TABLE_ARGS,
    )

    contact_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey("contacts.id", name="fk_cav_contact", ondelete="CASCADE"),
        nullable=False,
    )
    attribute_id: Mapped[int] = mapped_column(
        big_id(),
        ForeignKey(
            "custom_attribute_definitions.id", name="fk_cav_attr", ondelete="CASCADE"
        ),
        nullable=False,
    )
    value_string: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    value_number: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    value_datetime: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    value_boolean: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        datetime6(), nullable=False, default=utcnow, onupdate=utcnow, server_default=func.now()
    )

    #: Eager so a loaded value always knows its key/type (used to build the attributes map).
    definition: Mapped[CustomAttributeDefinition] = relationship(
        CustomAttributeDefinition, lazy="selectin"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<ContactAttributeValue contact={self.contact_id} attr={self.attribute_id}>"
