"""Contact service (Doc 04 §14.1) — Module 2 foundation.

Contact CRUD with dedup by ``(organization_id, wa_id)`` (409), opt-in state transitions,
optimistic concurrency (``row_version`` → 409), soft delete, and audit integration. The
``wa_id`` is derived from the E.164 phone (digits only) and is immutable after creation
(it is the dedup key). Tags/attributes/timeline/import/export/bulk are later steps.
"""

from __future__ import annotations

import uuid as uuidlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, VersionConflictError
from app.db.mixins import utcnow
from app.models.business_event import BUSINESS_EVENT_ACTOR_USER
from app.models.contact import (
    OPT_IN_OPTED_IN,
    OPT_IN_OPTED_OUT,
    Contact,
)
from app.models.contact_event import EVENT_CONTACT_CREATED, EVENT_OPTIN_CHANGED
from app.models.user import User
from app.repositories.contact import ContactRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.business_event_service import BusinessEventService
from app.services.contact_event_service import ContactEventService


def wa_id_from_e164(phone_e164: str) -> str:
    """Derive the WhatsApp id (normalized E.164, digits only) from the display phone."""
    return "".join(ch for ch in phone_e164 if ch.isdigit())


@dataclass(slots=True)
class ContactListPage:
    contacts: list[Contact]
    has_more: bool
    total: int
    next_sort: str


class ContactService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._contacts = ContactRepository(session)
        self._events = ContactEventService(session)
        self._business_events = BusinessEventService(session)
        self._audit = AuditService(session)

    @staticmethod
    def _apply_opt_in(contact: Contact, status: str, now: datetime) -> None:
        contact.opt_in_status = status
        if status == OPT_IN_OPTED_IN:
            contact.opt_in_at = now
        elif status == OPT_IN_OPTED_OUT:
            contact.opt_out_at = now

    async def list_contacts(
        self,
        organization_id: int,
        *,
        limit: int,
        sort: str | None,
        cursor: tuple[Any, int, bool] | None,
        q: str | None,
        opt_in_status: list[str] | None,
        source: str | None,
        is_active_on_wa: bool | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> ContactListPage:
        contacts, has_more, sort_name = await self._contacts.paginate(
            organization_id,
            limit=limit,
            sort=sort,
            cursor=cursor,
            q=q,
            opt_in_status=opt_in_status,
            source=source,
            is_active_on_wa=is_active_on_wa,
            created_from=created_from,
            created_to=created_to,
        )
        total = await self._contacts.count(
            organization_id,
            q=q,
            opt_in_status=opt_in_status,
            source=source,
            is_active_on_wa=is_active_on_wa,
            created_from=created_from,
            created_to=created_to,
        )
        return ContactListPage(
            contacts=contacts, has_more=has_more, total=total, next_sort=sort_name
        )

    async def get_contact(self, organization_id: int, public_id: uuidlib.UUID) -> Contact:
        contact = await self._contacts.get_active_by_uuid(organization_id, public_id.bytes)
        if contact is None:
            raise NotFoundError("Contact not found.")
        return contact

    async def create_contact(
        self,
        *,
        organization_id: int,
        actor: User,
        phone_e164: str,
        opt_in_status: str,
        source: str,
        fields: dict[str, Any],
    ) -> Contact:
        wa_id = wa_id_from_e164(phone_e164)
        if await self._contacts.wa_id_exists(organization_id, wa_id):
            raise ConflictError("A contact with this phone number already exists.")
        now = utcnow()
        contact = Contact(
            organization_id=organization_id,
            wa_id=wa_id,
            phone_e164=phone_e164,
            source=source,
            created_by=actor.id,
            **fields,
        )
        self._apply_opt_in(contact, opt_in_status, now)
        await self._contacts.add(contact)
        await self._events.record(
            organization_id=organization_id,
            contact_id=contact.id,
            event_type=EVENT_CONTACT_CREATED,
            payload={"source": source},
        )
        await self._business_events.record_contact_created(
            contact=contact,
            actor_type=BUSINESS_EVENT_ACTOR_USER,
            actor_id=actor.id,
            occurred_at=now,
            source="contacts",
        )
        await self._audit.record(
            AuditAction.CONTACT_CREATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="contact",
            entity_id=contact.id,
            after={"wa_id": wa_id, "phone_e164": phone_e164},
        )
        await self._session.commit()
        # A newly created row never loaded its relationships; populate them here (in the
        # async context) so serialization never triggers a lazy load.
        await self._session.refresh(contact, ["tags", "attribute_values"])
        return contact

    async def update_contact(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        opt_in_status: str | None,
        fields: dict[str, Any],
        expected_version: int | None,
    ) -> Contact:
        contact = await self.get_contact(organization_id, public_id)
        if expected_version is not None and expected_version != contact.row_version:
            raise VersionConflictError(
                "The contact was modified by someone else; reload and retry."
            )
        for key, value in fields.items():
            setattr(contact, key, value)
        if opt_in_status is not None and opt_in_status != contact.opt_in_status:
            previous = contact.opt_in_status
            self._apply_opt_in(contact, opt_in_status, utcnow())
            await self._events.record(
                organization_id=organization_id,
                contact_id=contact.id,
                event_type=EVENT_OPTIN_CHANGED,
                payload={"from": previous, "to": opt_in_status},
            )
        contact.updated_by = actor.id
        contact.row_version += 1
        await self._contacts.flush()
        await self._audit.record(
            AuditAction.CONTACT_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="contact",
            entity_id=contact.id,
        )
        await self._session.commit()
        return contact

    async def delete_contact(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> None:
        contact = await self.get_contact(organization_id, public_id)
        contact.deleted_at = utcnow()
        contact.updated_by = actor.id
        contact.row_version += 1
        await self._contacts.flush()
        await self._audit.record(
            AuditAction.CONTACT_DELETED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="contact",
            entity_id=contact.id,
        )
        await self._session.commit()
