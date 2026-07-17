"""Rate card — the pricing authority for cost estimation (Doc 03 §8.5) — FR-CAM-11.

One question, one answer: *what does one message to country X in category Y cost?* The estimator
multiplies that by a count; nothing here knows what a campaign is.

Three properties are load-bearing, and all three are Doc 03 §8.5.1's:

* **Global, not per-tenant.** No ``organization_id`` — Doc 04 §17 promises Meta's real card with "no
  reseller markup", so a per-org rate would be a markup by another name, and two tenants would get
  different "exact" costs for the same send. It is the one campaign-domain table outside tenant
  scoping, deliberately (Doc 03 §12.4a).
* **Ships empty.** No default, sample or bundled rate exists. Doc 12 §53 places Meta's pricing
  *outside* the frozen set, so the codebase must not restate it. An empty card is a normal state the
  API reports (``rate_card_not_configured``), never one the engine guesses around.
* **Versioned by effective dating.** A rate change is a **new row**; rows are never mutated in place.
  Editing a price would silently rewrite what every past estimate meant.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CHAR, CheckConstraint, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IntPKMixin, TimestampMixin, UUIDMixin
from app.db.types import MYSQL_TABLE_ARGS, big_id, datetime6

#: The only categories a rate may price (Doc 03 §8.5.2). Deliberately the *template* categories
#: (``ck_tpl_category``, Doc 03 §7.1) and not ``messages.category``: a campaign always sends a
#: template, so the ``service`` category that the message ledger also permits is unreachable from an
#: estimate by construction, and its free-tier semantics are undefined (Doc 03 §8.5.5).
RATE_CATEGORIES = ("marketing", "utility", "authentication")


class RateCard(IntPKMixin, UUIDMixin, TimestampMixin, Base):
    """One price, for one (country, category), over one window of time (Doc 03 §8.5.2)."""

    __tablename__ = "rate_cards"
    __table_args__ = (
        # One rate per pair per instant — what makes resolution single-valued (Doc 03 §8.5.3).
        Index("uq_ratecard_slot", "country_code", "category", "effective_from", unique=True),
        # The estimator's scan: equality on the pair, range over the window.
        Index("ix_ratecard_lookup", "country_code", "category", "effective_from", "effective_to"),
        CheckConstraint(
            "category IN ('marketing','utility','authentication')", name="ck_ratecard_category"
        ),
        CheckConstraint("unit_price >= 0", name="ck_ratecard_price"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from", name="ck_ratecard_window"
        ),
        MYSQL_TABLE_ARGS,
    )

    #: ISO-3166-1 alpha-2, matching ``contacts.country_code`` — joined by value, never by key
    #: (Doc 03 §12.4a).
    country_code: Mapped[str] = mapped_column(CHAR(2), nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    #: Per-message price. Scale matches ``messages.cost_amount`` so the chain never widens.
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    #: ISO-4217. Every row in force shares one currency (Doc 03 §8.5.3) — there is no FX.
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(datetime6(), nullable=False)
    #: ``None`` == currently in force. A supersede closes the open row rather than deleting it.
    effective_to: Mapped[datetime | None] = mapped_column(datetime6(), nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        big_id(),
        ForeignKey("users.id", name="fk_ratecard_author", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<RateCard {self.country_code}/{self.category} {self.unit_price} {self.currency}>"
