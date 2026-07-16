"""Reusable model mixins.

Implements the common column set from Doc 03 §1: the two-key identity (BIGINT PK +
UUIDv7 public id), UTC microsecond timestamps, soft-delete, audit fields, and the
optimistic-concurrency version counter. Concrete models compose these in later steps.

Note: :func:`uuid7` provides a time-ordered UUIDv7 (Doc 03 §1.2). Python's stdlib
``uuid`` gains native ``uuid7`` in newer versions; this implementation is used when
that is unavailable so behaviour is deterministic across interpreters.
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.types import big_id, datetime6, int_id, uuid_binary


def uuid7() -> uuid.UUID:
    """Return a time-ordered UUIDv7 (Doc 03 §1.2 — index-friendly public ids)."""
    native = getattr(uuid, "uuid7", None)
    if native is not None:  # Python 3.14+
        return native()  # type: ignore[no-any-return]
    unix_ms = int(time.time() * 1000)
    rand = os.urandom(10)
    value = bytearray(16)
    value[0:6] = unix_ms.to_bytes(6, "big")
    value[6:16] = rand
    value[6] = (value[6] & 0x0F) | 0x70  # version 7
    value[8] = (value[8] & 0x3F) | 0x80  # RFC 4122 variant
    return uuid.UUID(bytes=bytes(value))


def utcnow() -> datetime:
    """Current UTC timestamp as a naive datetime (Doc 03 §1.3 — all stored times are UTC).

    Returned naive because both MySQL ``DATETIME`` and SQLite read datetimes back as naive;
    keeping a single naive-UTC convention avoids offset-aware/naive comparison errors when
    values loaded from the database are compared against "now".
    """
    return datetime.now(UTC).replace(tzinfo=None)


class IntPKMixin:
    """Internal BIGINT UNSIGNED auto-increment primary key (Doc 03 §1.2)."""

    id: Mapped[int] = mapped_column(big_id(), primary_key=True, autoincrement=True)


class UUIDMixin:
    """Public UUIDv7 identifier used by the API, stored as BINARY(16) (Doc 03 §1.2)."""

    uuid: Mapped[bytes] = mapped_column(
        uuid_binary(), unique=True, nullable=False, default=lambda: uuid7().bytes
    )

    @property
    def public_id(self) -> str:
        """The canonical string form of the public identifier."""
        return str(uuid.UUID(bytes=self.uuid))


class TimestampMixin:
    """``created_at`` / ``updated_at`` in UTC with microsecond precision (Doc 03 §1.3).

    Values are populated by Python callables (``utcnow``) as well as DB-side defaults. The
    client-side value matters: a SQL ``onupdate`` expression would leave the attribute
    *expired* after an UPDATE, forcing a lazy refresh that fails under the async engine when
    the object is later serialized outside a greenlet. The ``server_default`` remains so
    non-ORM writes still get correct timestamps.
    """

    created_at: Mapped[datetime] = mapped_column(
        datetime6(), nullable=False, default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        datetime6(),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
    )


class SoftDeleteMixin:
    """``deleted_at`` NULL == active (Doc 03 §1.5)."""

    deleted_at: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class AuditMixin:
    """``created_by`` / ``updated_by`` referencing ``users.id`` (Doc 03 §1.6)."""

    created_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)
    updated_by: Mapped[int | None] = mapped_column(big_id(), nullable=True)


class VersionMixin:
    """Optimistic-concurrency counter (Doc 03 §1.7)."""

    row_version: Mapped[int] = mapped_column(int_id(), nullable=False, default=0)
