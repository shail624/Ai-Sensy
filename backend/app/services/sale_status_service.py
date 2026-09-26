"""A customer's sale status and number release date, set from Live Chat (UI-AIS-06).

Both live on the contact, so a customer who writes on the official number and on the QR phone
carries one status everywhere. A release date is backed by an ordinary reminder task (the Tasks
module already notifies on due work), and the task is moved or cancelled when the date changes —
never duplicated.
"""

from __future__ import annotations

import uuid as uuidlib
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.task import TASK_STATUS_OPEN, TASK_TYPE_REMINDER, Task
from app.models.user import User
from app.services.audit_service import AuditService
from app.services.task_service import CHAT_RELEASE_TASK_TITLE, TaskService

#: Release reminders fire at 10:00 India time on the release date (04:30 UTC; stored naive UTC).
RELEASE_REMINDER_UTC = time(4, 30)


@dataclass(slots=True)
class SaleDetails:
    sale_status: str | None
    release_date: date | None
    release_task_id: str | None


class SaleStatusService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def update(
        self,
        *,
        organization_id: int,
        actor: User,
        conversation_public_id: uuidlib.UUID,
        **changes: Any,
    ) -> SaleDetails:
        """Apply only the fields present in ``changes`` (``sale_status``, ``release_date``)."""
        conversation, contact = await self._load(organization_id, conversation_public_id)
        before = {"sale_status": contact.sale_status, "release_date": _iso(contact.release_date)}

        if "sale_status" in changes:
            contact.sale_status = changes["sale_status"]
        if "release_date" in changes and changes["release_date"] != contact.release_date:
            new_date: date | None = changes["release_date"]
            await self._move_release_task(organization_id, actor, conversation, contact, new_date)
            contact.release_date = new_date

        await AuditService(self._session).record(
            "contact.sale_details_updated",
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="contact",
            entity_id=contact.id,
            before=before,
            after={"sale_status": contact.sale_status, "release_date": _iso(contact.release_date)},
        )
        await self._session.commit()
        return await self._details(contact)

    async def _move_release_task(
        self,
        organization_id: int,
        actor: User,
        conversation: Conversation,
        contact: Contact,
        new_date: date | None,
    ) -> None:
        tasks = TaskService(self._session)
        current = await self._open_release_task(contact)
        if new_date is None:
            if current is not None:
                await tasks.cancel(
                    organization_id=organization_id,
                    actor=actor,
                    public_id=uuidlib.UUID(bytes=current.uuid),
                    expected_row_version=None,
                    reason="Release date removed",
                    commit=False,
                )
            contact.release_task_id = None
            return
        due_at = datetime.combine(new_date, RELEASE_REMINDER_UTC)
        if current is not None:
            await tasks.update(
                organization_id=organization_id,
                actor=actor,
                public_id=uuidlib.UUID(bytes=current.uuid),
                expected_row_version=None,
                title=None,
                description=None,
                task_type=None,
                priority=None,
                due_at=due_at,
                has_time=None,
                reminder_at=due_at - timedelta(days=1),
                commit=False,
            )
            return
        view = await tasks.create(
            organization_id=organization_id,
            actor=actor,
            contact_id=uuidlib.UUID(bytes=contact.uuid),
            conversation_id=uuidlib.UUID(bytes=conversation.uuid),
            title=CHAT_RELEASE_TASK_TITLE,
            task_type=TASK_TYPE_REMINDER,
            priority="high",
            due_at=due_at,
            has_time=True,
            reminder_at=due_at - timedelta(days=1),
            description="Contact the customer: their number is released today.",
            assigned_agent_id=None,
            commit=False,
        )
        created = await self._session.scalar(
            select(Task).where(Task.uuid == uuidlib.UUID(view.public_id).bytes)
        )
        contact.release_task_id = created.id if created is not None else None

    async def _open_release_task(self, contact: Contact) -> Task | None:
        if contact.release_task_id is None:
            return None
        task = await self._session.get(Task, contact.release_task_id)
        if task is None or task.status != TASK_STATUS_OPEN:
            return None
        return task

    async def _load(
        self, organization_id: int, conversation_public_id: uuidlib.UUID
    ) -> tuple[Conversation, Contact]:
        conversation = await self._session.scalar(
            select(Conversation).where(
                Conversation.uuid == conversation_public_id.bytes,
                Conversation.organization_id == organization_id,
                Conversation.deleted_at.is_(None),
            )
        )
        if conversation is None:
            raise NotFoundError("Conversation not found.")
        contact = await self._session.scalar(
            select(Contact).where(
                Contact.id == conversation.contact_id,
                Contact.organization_id == organization_id,
            )
        )
        if contact is None:
            raise NotFoundError("Customer not found.")
        return conversation, contact

    async def _details(self, contact: Contact) -> SaleDetails:
        task_public = None
        if contact.release_task_id is not None:
            task = await self._session.get(Task, contact.release_task_id)
            task_public = str(uuidlib.UUID(bytes=task.uuid)) if task is not None else None
        return SaleDetails(contact.sale_status, contact.release_date, task_public)


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None
