"""WhatsApp reachability, derived from campaign delivery evidence (scope §13).

Section 13 permits only "compliant and authorised methods" and excludes unofficial WhatsApp Web
bulk enumeration. Meta's Cloud API has no endpoint that answers "is this number on WhatsApp" --
the on-premise ``/contacts`` check did not survive the move -- so the only compliant signal is what
Meta already told us about messages we actually sent.

That evidence is in ``campaign_recipients``, and it is unusually good: a delivery receipt is proof
the number is reachable, and error ``131026`` ("undeliverable / not a WhatsApp user") is Meta
stating the opposite in its own words. Neither is inferred and neither costs an extra send.

Two timestamps are read rather than one verdict. A delivery six months ago and a ``131026`` last
week are both facts, and which one is *current* is the whole question -- a number can be
deactivated after having been reachable. Returning both lets the verdict be derived from recency
and lets the screen show its own evidence, so an operator can disagree with it.

A failure for any other reason -- a paused template, a closed 24-hour window, a throttle -- says
nothing whatsoever about the number and is deliberately not counted. Treating those as "not on
WhatsApp" would quietly condemn reachable customers on the strength of our own configuration
mistakes.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Subquery

from app.models.campaign import RECIPIENT_FAILED, Campaign, CampaignRecipient
from app.models.contact import Contact

#: Meta's code for "undeliverable / not a WhatsApp user" (``app/channels/meta/errors.py``). The one
#: failure that is evidence about the *number* rather than about our own configuration.
NOT_A_WHATSAPP_USER = "131026"

REACHABLE = "reachable"
UNREACHABLE = "unreachable"
UNKNOWN = "unknown"
VERDICTS = (REACHABLE, UNREACHABLE, UNKNOWN)


@dataclass(slots=True)
class ReachabilityRow:
    contact: Contact
    last_delivered_at: datetime | None
    last_undeliverable_at: datetime | None

    @property
    def verdict(self) -> str:
        """The more recent fact wins; with no facts at all, say so rather than guess.

        "Unknown" is a real answer here, not a fallback: a contact nobody has messaged has not been
        tested, and reporting them as reachable would invent a delivery that never happened.
        """
        delivered, undeliverable = self.last_delivered_at, self.last_undeliverable_at
        if delivered is None and undeliverable is None:
            return UNKNOWN
        if undeliverable is None:
            return REACHABLE
        if delivered is None:
            return UNREACHABLE
        return REACHABLE if delivered >= undeliverable else UNREACHABLE


def _evidence(organization_id: int, *, contact_ids: Sequence[int] | None = None) -> Subquery:
    """Per-contact delivery evidence for one organization.

    ``campaign_recipients`` carries no ``organization_id`` -- it is monthly-partitioned with no
    foreign keys -- so ownership is read through the campaign the row belongs to, the same way
    CORE-22 reads it through the route a webhook arrived on.

    ``contact_ids`` narrows the aggregate to one page. Measured at 20,000 contacts against a real
    MySQL 8, aggregating the whole ledger to render fifty rows cost 42ms for the page and 74ms for
    the tallies; restricting the page's half to the fifty contacts it will actually show is the
    difference between a cost that grows with the account and one that does not. The tallies still
    need every row -- they are a question about the whole set -- so they pass ``None``.
    """
    delivered = case(
        (CampaignRecipient.read_at.is_not(None), CampaignRecipient.read_at),
        (CampaignRecipient.delivered_at.is_not(None), CampaignRecipient.delivered_at),
    )
    undeliverable = case(
        (
            and_(
                CampaignRecipient.status == RECIPIENT_FAILED,
                CampaignRecipient.error_code == NOT_A_WHATSAPP_USER,
            ),
            CampaignRecipient.failed_at,
        )
    )
    return (
        select(
            CampaignRecipient.contact_id.label("contact_id"),
            func.max(delivered).label("last_delivered_at"),
            func.max(undeliverable).label("last_undeliverable_at"),
        )
        .join(Campaign, Campaign.id == CampaignRecipient.campaign_id)
        .where(
            Campaign.organization_id == organization_id,
            *(
                [CampaignRecipient.contact_id.in_(tuple(contact_ids))]
                if contact_ids is not None
                else []
            ),
        )
        .group_by(CampaignRecipient.contact_id)
        .subquery()
    )


def verdict_condition(organization_id: int, verdict: str) -> ColumnElement[bool]:
    """A contact-level predicate for one verdict, for callers outside this repository.

    Exists so a *segment* of "not on WhatsApp" is the same set the Scan screen shows. Written
    separately it would drift, and the way that drift presents is the worst kind: a campaign
    excluding a different population from the one the operator read off the screen before building
    it.

    Phrased as ``EXISTS`` against the evidence rather than a join, because a segment's predicate is
    combined with others by ``compile_rules`` and has to be a condition, not a shape.
    """
    evidence = _evidence(organization_id)
    inner = (
        select(evidence.c.contact_id)
        .where(
            evidence.c.contact_id == Contact.id,
            ReachabilityRepository._verdict_clause(evidence, verdict),
        )
        .exists()
    )
    # ``unknown`` is the absence of evidence, so it is the one verdict expressed by *not* finding a
    # row rather than by finding one that says so.
    if verdict == UNKNOWN:
        return ~(
            select(evidence.c.contact_id)
            .where(evidence.c.contact_id == Contact.id)
            .exists()
        )
    return inner


class ReachabilityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _verdict_clause(evidence: Subquery, verdict: str) -> ColumnElement[bool]:
        """The SQL form of :attr:`ReachabilityRow.verdict`, kept beside it deliberately.

        The filter and the label an operator reads have to agree; computing one in Python and the
        other in SQL is how a list ends up disagreeing with the badge on its own rows.
        """
        delivered = evidence.c.last_delivered_at
        undeliverable = evidence.c.last_undeliverable_at
        if verdict == UNKNOWN:
            return and_(delivered.is_(None), undeliverable.is_(None))
        if verdict == REACHABLE:
            return and_(
                delivered.is_not(None),
                or_(undeliverable.is_(None), delivered >= undeliverable),
            )
        return and_(
            undeliverable.is_not(None),
            or_(delivered.is_(None), delivered < undeliverable),
        )

    @staticmethod
    def _contact_clauses(organization_id: int, q: str | None) -> list[ColumnElement[bool]]:
        """Which contacts the screen is about, shared by every query here.

        The page, the verdict filter and the tallies must describe the same population; written
        three times, the one that drifted would be the one nobody compared.
        """
        clauses: list[ColumnElement[bool]] = [
            Contact.organization_id == organization_id,
            Contact.deleted_at.is_(None),
        ]
        if q:
            # Normalised the way ``ContactRepository`` normalises it -- the same ``strip`` and
            # the same ``lower``. This box sits on a table of contacts and looks identical to the
            # one on the Contacts screen, so the same text typed into each has to find the same
            # people; a name pasted with a trailing space, the ordinary result of copying a cell,
            # found the customer on one screen and an empty list on the other, and nothing on
            # either screen said why.
            #
            # The field list is deliberately shorter: Contacts also matches ``email``, this screen
            # does not, because it shows neither email nor any promise of one -- its label is
            # "Search by name or number" and matching a hidden column would return rows whose
            # reason for matching is not on the page.
            text = q.strip()
            like = f"%{text.lower()}%"
            clauses.append(
                or_(
                    func.lower(Contact.full_name).like(like),
                    Contact.phone_e164.like(f"%{text}%"),
                    Contact.wa_id.like(f"%{text}%"),
                )
            )
        return clauses

    def _base(
        self, organization_id: int, *, verdict: str | None, q: str | None
    ) -> Select[tuple[Contact, datetime | None, datetime | None]]:
        evidence = _evidence(organization_id)
        stmt = select(
            Contact,
            evidence.c.last_delivered_at,
            evidence.c.last_undeliverable_at,
        ).outerjoin(evidence, evidence.c.contact_id == Contact.id)
        clauses = self._contact_clauses(organization_id, q)
        if verdict:
            clauses.append(self._verdict_clause(evidence, verdict))
        return stmt.where(*clauses)

    async def paginate(
        self,
        organization_id: int,
        *,
        limit: int,
        cursor: tuple[datetime, int] | None,
        verdict: str | None,
        q: str | None,
    ) -> tuple[list[ReachabilityRow], bool]:
        """One page of contacts with their evidence.

        Two queries rather than one join, and the order matters: page the contacts first -- an
        indexed read whose cost is the page size -- then aggregate the ledger for exactly those
        contacts. Joining a whole-ledger aggregate to fifty rows made the page cost grow with the
        account rather than with the page.

        Filtering by verdict is the exception and cannot be: deciding which contacts qualify needs
        the evidence before the page exists, so that path keeps the join. It is the deliberate
        choice, not an oversight -- the unfiltered list is what an operator opens.
        """
        if verdict:
            return await self._paginate_by_verdict(
                organization_id, limit=limit, cursor=cursor, verdict=verdict, q=q
            )

        page_stmt = select(Contact).where(*self._contact_clauses(organization_id, q))
        if cursor:
            created_at, row_id = cursor
            page_stmt = page_stmt.where(
                or_(
                    Contact.created_at < created_at,
                    and_(Contact.created_at == created_at, Contact.id < row_id),
                )
            )
        page_stmt = page_stmt.order_by(Contact.created_at.desc(), Contact.id.desc()).limit(limit + 1)
        contacts = list((await self.session.scalars(page_stmt)).all())
        return await self._with_evidence(organization_id, contacts, limit)

    async def _with_evidence(
        self, organization_id: int, contacts: list[Contact], limit: int
    ) -> tuple[list[ReachabilityRow], bool]:
        page = contacts[:limit]
        evidence: dict[int, tuple[datetime | None, datetime | None]] = {}
        if page:
            sub = _evidence(organization_id, contact_ids=[contact.id for contact in page])
            for contact_id, delivered, undeliverable in (
                await self.session.execute(
                    select(sub.c.contact_id, sub.c.last_delivered_at, sub.c.last_undeliverable_at)
                )
            ).all():
                evidence[contact_id] = (delivered, undeliverable)
        rows = [
            ReachabilityRow(
                contact=contact,
                last_delivered_at=evidence.get(contact.id, (None, None))[0],
                last_undeliverable_at=evidence.get(contact.id, (None, None))[1],
            )
            for contact in page
        ]
        return rows, len(contacts) > limit

    async def _paginate_by_verdict(
        self,
        organization_id: int,
        *,
        limit: int,
        cursor: tuple[datetime, int] | None,
        verdict: str,
        q: str | None,
    ) -> tuple[list[ReachabilityRow], bool]:
        stmt = self._base(organization_id, verdict=verdict, q=q)
        if cursor:
            created_at, row_id = cursor
            stmt = stmt.where(
                or_(
                    Contact.created_at < created_at,
                    and_(Contact.created_at == created_at, Contact.id < row_id),
                )
            )
        stmt = stmt.order_by(Contact.created_at.desc(), Contact.id.desc()).limit(limit + 1)
        rows = [
            ReachabilityRow(
                contact=contact, last_delivered_at=delivered, last_undeliverable_at=undeliverable
            )
            for contact, delivered, undeliverable in (await self.session.execute(stmt)).all()
        ]
        return rows[:limit], len(rows) > limit

    async def counts(self, organization_id: int, *, q: str | None) -> dict[str, int]:
        """How many contacts fall in each verdict, over the same population the list pages.

        Computed from one scan rather than three, and from the same predicates the list uses, so
        the tallies and the rows can never describe different sets.
        """
        evidence = _evidence(organization_id)
        clauses = self._contact_clauses(organization_id, q)
        totals = {
            verdict: func.sum(case((self._verdict_clause(evidence, verdict), 1), else_=0))
            for verdict in VERDICTS
        }
        stmt = (
            select(*(total.label(verdict) for verdict, total in totals.items()))
            .select_from(Contact)
            .outerjoin(evidence, evidence.c.contact_id == Contact.id)
            .where(*clauses)
        )
        row = (await self.session.execute(stmt)).one()
        return {verdict: int(getattr(row, verdict) or 0) for verdict in VERDICTS}
