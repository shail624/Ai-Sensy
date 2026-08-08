"""Inbound webhook repositories (Doc 03 §9.4)."""

from __future__ import annotations

from sqlalchemy import select

from app.models.channel_connection import ChannelConnection, ChannelEndpoint
from app.models.waba import PhoneNumber
from app.models.webhook import WH_PROCESSED, WebhookDeadLetter, WebhookEvent
from app.repositories.base import BaseRepository


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


class WebhookDeadLetterRepository(BaseRepository[WebhookDeadLetter]):
    model = WebhookDeadLetter
