"""SQLAlchemy declarative base and shared metadata.

Establishes the single :class:`Base` all models inherit from, with the index /
constraint **naming convention** from Doc 03 §1.1 so migrations produce predictable,
consistent names. Concrete models are added in later steps (Doc 03 domains).
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Naming convention (Doc 03 §1.1): ix_ / uq_ / fk_ / ck_ / pk_.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "pk": "pk_%(table_name)s",
}

metadata_obj = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    metadata = metadata_obj
