"""Focused guards for service-layer references and internal cursor shapes."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, create_autospec

import pytest

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.campaign import CAMPAIGN_DRAFT, RECIPIENT_PENDING, Campaign, CampaignRecipient
from app.models.contact import Contact
from app.models.template import MessageTemplate
from app.models.user import User
from app.services.campaign_dispatch_service import CampaignDispatchService
from app.services.campaign_service import CampaignService
from app.services.send_service import SendService
from app.services.task_service import TaskService
from app.services.template_service import TemplateService


async def test_template_delete_reports_a_missing_linked_waba(db_session, monkeypatch) -> None:
    service = TemplateService(db_session)
    template = MessageTemplate(
        id=11,
        organization_id=7,
        waba_id=22,
        name="order_update",
        language="en_US",
        meta_template_id="remote-1",
    )
    actor = User(id=5, organization_id=7)
    monkeypatch.setattr(service, "get_template", AsyncMock(return_value=template))
    monkeypatch.setattr(service._wabas, "get_by_id", AsyncMock(return_value=None))

    with pytest.raises(NotFoundError, match="WABA not found"):
        await service.delete(
            organization_id=7,
            actor=actor,
            public_id=uuid.uuid4(),
        )


async def test_campaign_update_reports_a_missing_linked_template(db_session, monkeypatch) -> None:
    service = CampaignService(db_session)
    campaign = Campaign(
        id=31,
        organization_id=7,
        phone_number_id=41,
        template_id=51,
        status=CAMPAIGN_DRAFT,
        audience_type="list",
        row_version=3,
    )
    actor = User(id=5, organization_id=7)
    monkeypatch.setattr(service, "get_campaign", AsyncMock(return_value=campaign))
    monkeypatch.setattr(service._templates, "get_by_id", AsyncMock(return_value=None))

    with pytest.raises(NotFoundError, match="Template not found"):
        await service.update(
            organization_id=7,
            actor=actor,
            public_id=uuid.uuid4(),
            fields={},
            number_public_id=None,
            template_public_id=None,
            expected_version=3,
        )


async def test_campaign_accept_marks_a_missing_sending_number_as_a_missing_reference(
    db_session, monkeypatch
) -> None:
    service = CampaignDispatchService(db_session)
    campaign = Campaign(
        id=61,
        organization_id=7,
        phone_number_id=71,
        template_id=81,
        created_by=5,
    )
    recipient = CampaignRecipient(
        id=91,
        campaign_id=61,
        contact_id=101,
        status=RECIPIENT_PENDING,
    )
    contact = Contact(id=101, organization_id=7, phone_e164="+919876543210")
    template = MessageTemplate(id=81, organization_id=7, waba_id=22)
    sender = create_autospec(SendService, instance=True)
    skip = AsyncMock()
    monkeypatch.setattr(service._contacts, "get_by_id", AsyncMock(return_value=contact))
    monkeypatch.setattr(service._templates, "get_by_id", AsyncMock(return_value=template))
    monkeypatch.setattr(service._numbers, "get_by_id", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_skip", skip)

    assert await service._accept(sender, campaign, recipient) is None
    skip.assert_awaited_once_with(
        recipient,
        code="missing_ref",
        detail="contact, template, or sending number is gone",
    )
    sender.accept.assert_not_awaited()


def test_priority_cursor_rejects_a_non_integer_repository_rank() -> None:
    with pytest.raises(BadRequestError, match="invalid rank"):
        TaskService._encode_cursor(["1", None], task_id=3, sort_key="priority")
