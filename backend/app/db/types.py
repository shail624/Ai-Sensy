"""Cross-dialect column types.

The frozen schema (Doc 03) targets **MySQL 8** with specific physical types —
``BINARY(16)`` UUIDs, ``VARBINARY(16)`` packed IPs, ``BIGINT UNSIGNED`` identities,
``DATETIME(6)`` microsecond timestamps. The hermetic test suite runs on **SQLite**
(Doc 10 §8). These helpers use SQLAlchemy ``with_variant`` so a single model/migration
renders the Doc-03-exact type on MySQL and a portable equivalent on SQLite — the schema
never forks between environments.

Usage: ``mapped_column(uuid_binary(), ...)`` etc. Each call returns a fresh ``TypeEngine``
instance (SQLAlchemy requires per-column type instances, not shared singletons).
"""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from sqlalchemy import BigInteger, DateTime, Integer, LargeBinary
from sqlalchemy.dialects import mysql
from sqlalchemy.types import TypeEngine


def uuid_binary() -> TypeEngine[bytes]:
    """UUIDv7 public identifier — ``BINARY(16)`` on MySQL, ``BLOB`` on SQLite (Doc 03 §1.2)."""
    return LargeBinary(16).with_variant(mysql.BINARY(16), "mysql")


def varbinary(length: int) -> TypeEngine[bytes]:
    """Variable-length binary — ``VARBINARY(n)`` on MySQL, ``BLOB`` on SQLite."""
    return LargeBinary(length).with_variant(mysql.VARBINARY(length), "mysql")


def packed_ip() -> TypeEngine[bytes]:
    """Packed IPv4/IPv6 address — ``VARBINARY(16)`` on MySQL, ``BLOB`` on SQLite (Doc 03 §4.4)."""
    return varbinary(16)


def big_id() -> TypeEngine[int]:
    """BIGINT identity/foreign-key — ``BIGINT UNSIGNED`` on MySQL (Doc 03 §1.2).

    Renders as ``INTEGER`` on SQLite so an autoincrement primary key aliases ``rowid``
    (a ``BIGINT`` PK does not autoincrement on SQLite); ``INTEGER`` affinity keeps joins
    and foreign keys correct for the hermetic test suite.
    """
    return (
        BigInteger()
        .with_variant(mysql.BIGINT(unsigned=True), "mysql")
        .with_variant(Integer(), "sqlite")
    )


def int_id() -> TypeEngine[int]:
    """INT identity/foreign-key — ``INT UNSIGNED`` on MySQL (used by ``permissions.id``, Doc 03 §4.3)."""
    return Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")


def small_uint() -> TypeEngine[int]:
    """Small unsigned counter — ``SMALLINT UNSIGNED`` on MySQL (e.g. ``users.failed_logins``)."""
    return Integer().with_variant(mysql.SMALLINT(unsigned=True), "mysql")


def datetime6() -> TypeEngine[datetime]:
    """UTC microsecond timestamp — ``DATETIME(6)`` on MySQL, ``DATETIME`` on SQLite (Doc 03 §1.3).

    ``timezone=True`` keeps values timezone-aware in Python; storage is UTC-naive on the
    wire per Doc 03 §1.3 ("we store UTC only").
    """
    return DateTime(timezone=True).with_variant(mysql.DATETIME(fsp=6), "mysql")


class _MySQLTableArgs(TypedDict):
    """The MySQL-specific keyword arguments accepted by ``Table``."""

    mysql_engine: str
    mysql_charset: str
    mysql_collate: str


# InnoDB + utf8mb4 table options (Doc 03 §1.1); ignored by SQLite.
MYSQL_TABLE_ARGS: _MySQLTableArgs = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}
