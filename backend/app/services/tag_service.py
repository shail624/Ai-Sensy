"""Tag service (Doc 04 §14.2, Doc 03 §6.2) — FR-CON-09.

Tag CRUD plus contact tag attach/detach. Maintains the denormalized ``usage_count``,
records timeline events (Doc 03 §6.5), and audits every change. Deleting a tag detaches it
from all contacts (Doc 04 §14.2).
"""

from __future__ import annotations

import uuid as uuidlib

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.db.mixins import utcnow
from app.models.contact import Contact
from app.models.contact_event import EVENT_TAG_ADDED, EVENT_TAG_REMOVED
from app.models.tag import Tag
from app.models.user import User
from app.repositories.contact import ContactRepository
from app.repositories.tag import ContactTagRepository, TagRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.contact_event_service import ContactEventService


class TagService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tags = TagRepository(session)
        self._links = ContactTagRepository(session)
        self._contacts = ContactRepository(session)
        self._events = ContactEventService(session)
        self._audit = AuditService(session)

    # --- Tag CRUD ------------------------------------------------------------
    async def list_tags(self, organization_id: int) -> list[Tag]:
        return await self._tags.list_for_org(organization_id)

    async def get_tag(self, organization_id: int, public_id: uuidlib.UUID) -> Tag:
        tag = await self._tags.get_active_by_uuid(organization_id, public_id.bytes)
        if tag is None:
            raise NotFoundError("Tag not found.")
        return tag

    async def create_tag(
        self,
        *,
        organization_id: int,
        actor: User,
        name: str,
        color: str | None,
        description: str | None,
    ) -> Tag:
        if await self._tags.get_by_name(organization_id, name) is not None:
            raise ConflictError(f"A tag named {name!r} already exists.")
        tag = Tag(
            organization_id=organization_id,
            name=name,
            color=color,
            description=description,
            created_by=actor.id,
        )
        await self._tags.add(tag)
        await self._audit.record(
            AuditAction.TAG_CREATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="tag",
            entity_id=tag.id,
            after={"name": name, "color": color},
        )
        await self._session.commit()
        return tag

    async def update_tag(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        name: str | None,
        color: str | None,
        description: str | None,
    ) -> Tag:
        tag = await self.get_tag(organization_id, public_id)
        before = {"name": tag.name, "color": tag.color}
        if name is not None and name != tag.name:
            if await self._tags.get_by_name(organization_id, name) is not None:
                raise ConflictError(f"A tag named {name!r} already exists.")
            tag.name = name
        if color is not None:
            tag.color = color
        if description is not None:
            tag.description = description
        await self._tags.flush()
        await self._audit.record(
            AuditAction.TAG_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="tag",
            entity_id=tag.id,
            before=before,
            after={"name": tag.name, "color": tag.color},
        )
        await self._session.commit()
        return tag

    async def delete_tag(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> None:
        """Soft-delete the tag and detach it from every contact (Doc 04 §14.2)."""
        tag = await self.get_tag(organization_id, public_id)
        detached = await self._links.detach_tag_everywhere(tag.id)
        tag.deleted_at = utcnow()
        tag.usage_count = 0
        await self._tags.flush()
        await self._audit.record(
            AuditAction.TAG_DELETED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="tag",
            entity_id=tag.id,
            before={"name": tag.name},
            metadata={"detached_contacts": detached},
        )
        await self._session.commit()

    # --- Contact ↔ tag -------------------------------------------------------
    async def _get_contact(self, organization_id: int, public_id: uuidlib.UUID) -> Contact:
        contact = await self._contacts.get_active_by_uuid(organization_id, public_id.bytes)
        if contact is None:
            raise NotFoundError("Contact not found.")
        return contact

    async def add_tags_to_contact(
        self,
        *,
        organization_id: int,
        actor: User,
        contact_uuid: uuidlib.UUID,
        tag_uuids: list[uuidlib.UUID],
    ) -> Contact:
        contact = await self._get_contact(organization_id, contact_uuid)
        raw_ids = [t.bytes for t in dict.fromkeys(tag_uuids)]
        tags = await self._tags.get_by_uuids(organization_id, raw_ids)
        if len(tags) != len(raw_ids):
            found = {t.uuid for t in tags}
            raise ValidationError(
                "One or more tags do not exist.",
                errors=[
                    {"field": "tags", "code": "unknown_tag", "message": str(uuidlib.UUID(bytes=r))}
                    for r in raw_ids
                    if r not in found
                ],
            )
        for tag in tags:
            if await self._links.attach(contact.id, tag.id, tagged_by=actor.id):
                tag.usage_count += 1
                await self._events.record(
                    organization_id=organization_id,
                    contact_id=contact.id,
                    event_type=EVENT_TAG_ADDED,
                    ref_type="tag",
                    ref_id=tag.id,
                    payload={"name": tag.name},
                )
                await self._audit.record(
                    AuditAction.CONTACT_TAGGED,
                    actor_user_id=actor.id,
                    organization_id=organization_id,
                    entity_type="contact",
                    entity_id=contact.id,
                    after={"tag": tag.name},
                )
        await self._session.commit()
        # Reload the association eagerly: the instance was loaded before the attach, so its
        # cached tag collection is stale until refreshed (and must not lazy-load later).
        await self._session.refresh(contact, ["tags"])
        return contact

    async def remove_tag_from_contact(
        self,
        *,
        organization_id: int,
        actor: User,
        contact_uuid: uuidlib.UUID,
        tag_uuid: uuidlib.UUID,
    ) -> None:
        contact = await self._get_contact(organization_id, contact_uuid)
        tag = await self.get_tag(organization_id, tag_uuid)
        if not await self._links.detach(contact.id, tag.id):
            raise NotFoundError("Tag is not attached to this contact.")
        tag.usage_count = max(0, tag.usage_count - 1)
        await self._events.record(
            organization_id=organization_id,
            contact_id=contact.id,
            event_type=EVENT_TAG_REMOVED,
            ref_type="tag",
            ref_id=tag.id,
            payload={"name": tag.name},
        )
        await self._audit.record(
            AuditAction.CONTACT_UNTAGGED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="contact",
            entity_id=contact.id,
            before={"tag": tag.name},
        )
        await self._session.commit()
