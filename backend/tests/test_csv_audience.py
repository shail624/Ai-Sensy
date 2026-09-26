"""CSV Broadcast: numbers from an uploaded file become a campaign audience (UI-AIS-16)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.exceptions import ValidationError
from app.models.contact import Contact
from app.services.csv_audience_service import MAX_ROWS, CsvAudienceService


@pytest.mark.anyio
async def test_numbers_become_contacts_once(db_session, organization, make_user) -> None:
    actor = (await make_user(email="csv-aud@vi.co", is_superuser=True)).user
    existing = Contact(
        organization_id=organization.id, wa_id="919891000010", phone_e164="+919891000010"
    )
    db_session.add(existing)
    await db_session.commit()

    result = await CsvAudienceService(db_session).resolve(
        organization_id=organization.id,
        actor=actor,
        rows=[
            ("98910 00010", "Already here"),
            ("+91 98765-43210", "Ravi"),
            ("9876543210", "Ravi again"),  # duplicate of the row above
            ("12", None),  # not a number
        ],
    )
    assert (result.created, result.existing, result.invalid_rows) == (1, 1, [4])
    assert len(result.contact_ids) == 2
    new = await db_session.scalar(select(Contact).where(Contact.wa_id == "919876543210"))
    assert new.full_name == "Ravi" and new.source == "csv_broadcast"
    await db_session.refresh(existing)
    assert existing.full_name is None  # an existing customer's name is never overwritten


@pytest.mark.anyio
async def test_empty_or_oversized_uploads_are_refused(db_session, organization, make_user) -> None:
    actor = (await make_user(email="csv-aud-2@vi.co", is_superuser=True)).user
    service = CsvAudienceService(db_session)
    with pytest.raises(ValidationError):
        await service.resolve(organization_id=organization.id, actor=actor, rows=[])
    with pytest.raises(ValidationError):
        await service.resolve(
            organization_id=organization.id,
            actor=actor,
            rows=[("9891000010", None)] * (MAX_ROWS + 1),
        )
