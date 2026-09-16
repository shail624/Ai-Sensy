"""Inbound webhook repositories (Doc 03 §9.4)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.sql.elements import ColumnElement

from app.models.channel_connection import ChannelConnection, ChannelEndpoint
from app.models.waba import PhoneNumber
from app.models.webhook import WH_PROCESSED, WebhookDeadLetter, WebhookEvent
from app.repositories.base import BaseRepository


def _event_organization_clause(organization_id: int) -> ColumnElement[bool]:
    """Which inbound events belong to one tenant.

    ``webhook_events`` has no ``organization_id``: it is written on the ack path, before anything
    is interpreted, and the table is range-partitioned with no foreign keys. Ownership is a
    property of the route the delivery arrived on, and there are two of them -- a Meta delivery
    routes by ``phone_number_id``, a WAHA one by ``channel_endpoint_id`` (QR-08). Both are matched
    here, because an operator shown only half their traffic would read the quiet half as silence.
    """
    return or_(
        WebhookEvent.phone_number_id.in_(
            select(PhoneNumber.id).where(PhoneNumber.organization_id == organization_id)
        ),
        WebhookEvent.channel_endpoint_id.in_(
            select(ChannelEndpoint.id).where(ChannelEndpoint.organization_id == organization_id)
        ),
    )


def _organization_clause(organization_id: int) -> ColumnElement[bool]:
    """A dead letter belongs to whoever the event it came from belonged to."""
    return WebhookDeadLetter.source_event_id.in_(
        select(WebhookEvent.id).where(_event_organization_clause(organization_id))
    )


class WebhookEventRepository(BaseRepository[WebhookEvent]):
    model = WebhookEvent

    async def resolve_numbers(self, channel_number_ids: set[str]) -> dict[str, int]:
        """Map the channel's own number ids to ``phone_numbers.id`` in one round trip.

        The ack path resolves routing for a whole delivery here (Doc 03 §5.2 — "query by
        `phone_number_id` on inbound webhook routing"), so the processor never sees a channel id
        and the persisted row is useful the moment it lands.
        """
        if not channel_number_ids:
            return {}
        stmt = select(PhoneNumber.phone_number_id, PhoneNumber.id).where(
            PhoneNumber.phone_number_id.in_(channel_number_ids),
            PhoneNumber.deleted_at.is_(None),
        )
        return {row.phone_number_id: row.id for row in await self.session.execute(stmt)}

    async def resolve_endpoints(
        self, channel_number_ids: set[str], *, connector_type: str
    ) -> dict[str, int]:
        """Map a WAHA session name to ``channel_endpoints.id`` (QR-08).

        The provider-neutral analogue of :meth:`resolve_numbers`. Scoped by ``connector_type``
        (unlike Meta's globally-unique ``phone_number_id``, a session name is only guaranteed
        unique within one connection — the connector scope is what keeps two deployments' sessions
        from colliding here) since this runs before an organization is known at all.
        """
        if not channel_number_ids:
            return {}
        stmt = (
            select(ChannelEndpoint.provider_endpoint_id, ChannelEndpoint.id)
            .join(ChannelConnection, ChannelConnection.id == ChannelEndpoint.connection_id)
            .where(
                ChannelEndpoint.provider_endpoint_id.in_(channel_number_ids),
                ChannelEndpoint.deleted_at.is_(None),
                ChannelConnection.connector_type == connector_type,
            )
        )
        return {row.provider_endpoint_id: row.id for row in await self.session.execute(stmt)}

    async def has_processed_sibling(self, event_id: str, *, exclude_id: int) -> bool:
        """Has this same event already been applied? (FR-WA-07 / Doc 06 §11.4.)

        Dedup is against the *processed* history rather than mere existence: two rows for one
        event id are a redelivery, and exactly one of them is allowed to be applied.
        """
        stmt = select(WebhookEvent.id).where(
            WebhookEvent.event_id == event_id,
            WebhookEvent.id != exclude_id,
            WebhookEvent.status == WH_PROCESSED,
        )
        return (await self.session.scalars(stmt)).first() is not None


    async def paginate(
        self,
        organization_id: int,
        *,
        limit: int,
        cursor: tuple[datetime, int] | None,
        status: str | None,
    ) -> tuple[list[WebhookEvent], bool]:
        """One organization's inbound deliveries, newest first."""
        clauses = [_event_organization_clause(organization_id)]
        if status:
            clauses.append(WebhookEvent.status == status)
        if cursor:
            created_at, row_id = cursor
            clauses.append(
                or_(
                    WebhookEvent.created_at < created_at,
                    and_(WebhookEvent.created_at == created_at, WebhookEvent.id < row_id),
                )
            )
        stmt = (
            select(WebhookEvent)
            .where(*clauses)
            .order_by(WebhookEvent.created_at.desc(), WebhookEvent.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self.session.scalars(stmt)).all())
        return rows[:limit], len(rows) > limit

    async def count(self, organization_id: int, *, status: str | None) -> int:
        clauses = [_event_organization_clause(organization_id)]
        if status:
            clauses.append(WebhookEvent.status == status)
        stmt = select(func.count()).select_from(WebhookEvent).where(*clauses)
        return int(await self.session.scalar(stmt) or 0)


class WebhookDeadLetterRepository(BaseRepository[WebhookDeadLetter]):
    model = WebhookDeadLetter

    async def paginate(
        self,
        organization_id: int,
        *,
        limit: int,
        cursor: tuple[datetime, int] | None,
        status: str | None,
    ) -> tuple[list[WebhookDeadLetter], bool]:
        """Dead letters belonging to one organization, newest first.

        ``webhook_dead_letter`` carries no ``organization_id`` of its own either, so ownership is
        read through the source event exactly as :meth:`WebhookEventRepository.paginate` reads it.
        An entry whose source row has already aged out (90 days against the dead letter's 180,
        Doc 04 §23.1) can no longer be attributed to a tenant and is therefore not listed: showing
        it to every organization would be worse than showing it to none.
        """
        clauses = [_organization_clause(organization_id)]
        if status:
            clauses.append(WebhookDeadLetter.status == status)
        if cursor:
            created_at, row_id = cursor
            clauses.append(
                or_(
                    WebhookDeadLetter.created_at < created_at,
                    and_(
                        WebhookDeadLetter.created_at == created_at,
                        WebhookDeadLetter.id < row_id,
                    ),
                )
            )
        stmt = (
            select(WebhookDeadLetter)
            .where(*clauses)
            .order_by(WebhookDeadLetter.created_at.desc(), WebhookDeadLetter.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self.session.scalars(stmt)).all())
        return rows[:limit], len(rows) > limit

    async def count(self, organization_id: int, *, status: str | None) -> int:
        clauses = [_organization_clause(organization_id)]
        if status:
            clauses.append(WebhookDeadLetter.status == status)
        stmt = select(func.count()).select_from(WebhookDeadLetter).where(*clauses)
        return int(await self.session.scalar(stmt) or 0)
