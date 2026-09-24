"""Campaigns header: quality, tier and estimated remaining 24h quota (UI-AIS-17)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.db.mixins import utcnow
from app.models.message import Message
from app.services.messaging_quota_service import MessagingQuotaService
from tests.test_sale_status import _thread


@pytest.mark.anyio
async def test_remaining_counts_unique_customers_sent_templates_in_24h(
    db_session, organization
) -> None:
    first = await _thread(db_session, organization.id, "919990070707", "Q1")
    number_id = first.phone_number_id
    from app.models.waba import PhoneNumber

    number = await db_session.get(PhoneNumber, number_id)
    number.messaging_tier = "TIER_1K"
    number.quality_rating = "GREEN"

    def template_to(contact_id: int, when) -> Message:
        return Message(
            organization_id=organization.id,
            conversation_id=first.id,
            phone_number_id=number_id,
            contact_id=contact_id,
            direction="outbound",
            message_type="template",
            template_id=1,
            content_json={},
            status="sent",
            created_at=when,
        )

    now = utcnow()
    db_session.add_all(
        [
            template_to(first.contact_id, now),
            template_to(first.contact_id, now),  # same customer twice counts once
            template_to(first.contact_id + 1000, now - timedelta(hours=30)),  # outside 24h
        ]
    )
    await db_session.commit()

    quotas = await MessagingQuotaService(db_session).for_organization(organization.id)
    quota = next(q for q in quotas if q.display_number == number.display_number)
    assert (quota.daily_limit, quota.used_last_24h, quota.remaining) == (1000, 1, 999)
    assert quota.quality_rating == "GREEN"


@pytest.mark.anyio
async def test_quota_route_is_not_swallowed_by_campaign_id(client, make_user) -> None:
    from tests.test_api_messages import _headers

    headers = await _headers(client, make_user, email="quota@vi.co", is_superuser=True)
    response = await client.get("/api/v1/campaigns/messaging-quota", headers=headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)
