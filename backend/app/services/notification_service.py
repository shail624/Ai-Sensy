"""Unified notification projection over existing Task and Reactivation authorities."""

from __future__ import annotations

import builtins
import uuid as uuidlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.pagination import decode_cursor, encode_cursor
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.mixins import utcnow
from app.models.contact import Contact
from app.models.notification import Notification
from app.models.task import Task
from app.models.user import User
from app.models.vi_domain import ReactivationCase
from app.repositories.notification import NotificationRepository
from app.services.audit_service import AuditAction, AuditService


@dataclass(slots=True)
class NotificationListResult:
    items: list[dict[str, Any]]
    has_more: bool
    next_cursor: str | None


class NotificationService:
    """Creates idempotent deliveries without taking ownership of source workflows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = NotificationRepository(session)
        self._audit = AuditService(session)

    async def emit(
        self,
        *,
        organization_id: int,
        recipient_user_id: int,
        notification_type: str,
        title: str,
        body: str,
        dedup_key: str,
        actor_user_id: int | None = None,
        contact_id: int | None = None,
        reactivation_case_id: int | None = None,
        task_id: int | None = None,
        due_at: datetime | None = None,
    ) -> Notification:
        existing = await self._repo.by_dedup(organization_id, dedup_key)
        if existing is not None:
            return existing
        row = Notification(
            organization_id=organization_id,
            recipient_user_id=recipient_user_id,
            actor_user_id=actor_user_id,
            contact_id=contact_id,
            reactivation_case_id=reactivation_case_id,
            task_id=task_id,
            notification_type=notification_type,
            title=title,
            body=body,
            dedup_key=dedup_key,
            due_at=due_at,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def list(
        self,
        *,
        actor: User,
        assignee_id: uuidlib.UUID | None,
        can_view_team: bool,
        notification_type: str | None,
        status: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        cursor: str | None,
        limit: int,
    ) -> NotificationListResult:
        recipient = await self._recipient(actor, assignee_id, can_view_team)
        decoded = decode_cursor(cursor) if cursor else None
        rows, has_more = await self._repo.list_page(
            actor.organization_id,
            recipient.id,
            notification_type=notification_type,
            status=status,
            date_from=date_from,
            date_to=date_to,
            overdue_before=self._day_start(actor.timezone),
            cursor=decoded,
            limit=limit,
        )
        items = await self._views(rows, actor.timezone)
        next_cursor = encode_cursor(rows[-1].created_at, rows[-1].id) if has_more and rows else None
        return NotificationListResult(items, has_more, next_cursor)

    async def unread_count(self, actor: User) -> int:
        return await self._repo.unread_count(actor.organization_id, actor.id)

    async def mark_read(self, actor: User, public_id: uuidlib.UUID) -> dict[str, Any]:
        row = await self._repo.get_for_recipient(actor.organization_id, actor.id, public_id.bytes)
        if row is None:
            raise NotFoundError("Notification not found.")
        if row.read_at is None:
            row.read_at = utcnow()
            await self._audit.record(
                AuditAction.NOTIFICATION_READ,
                actor_user_id=actor.id,
                organization_id=actor.organization_id,
                entity_type="notification",
                entity_id=row.id,
                after={"read_at": row.read_at.isoformat()},
            )
            await self._session.commit()
        return (await self._views([row], actor.timezone))[0]

    async def mark_all_read(self, actor: User) -> int:
        now = utcnow()
        count = await self._repo.mark_all_read(actor.organization_id, actor.id, now)
        if count:
            await self._audit.record(
                AuditAction.NOTIFICATIONS_READ_ALL,
                actor_user_id=actor.id,
                organization_id=actor.organization_id,
                entity_type="notification",
                after={"read_at": now.isoformat(), "count": count},
            )
        await self._session.commit()
        return count

    async def resolve_task(self, task: Task) -> int:
        return await self._repo.resolve_task(task.organization_id, task.id, utcnow())

    async def _recipient(
        self, actor: User, public_id: uuidlib.UUID | None, can_view_team: bool
    ) -> User:
        if public_id is None or public_id.bytes == actor.uuid:
            return actor
        if not can_view_team:
            raise ForbiddenError("Viewing another user's notifications requires tasks:assign.")
        row = (
            await self._session.scalars(
                select(User).where(
                    User.organization_id == actor.organization_id,
                    User.uuid == public_id.bytes,
                    User.deleted_at.is_(None),
                )
            )
        ).first()
        if row is None:
            raise NotFoundError("Assignee not found.")
        return row

    async def _views(
        self, rows: builtins.list[Notification], timezone: str
    ) -> builtins.list[dict[str, Any]]:
        contacts = await self._mapped(Contact, {row.contact_id for row in rows if row.contact_id})
        cases = await self._mapped(
            ReactivationCase,
            {row.reactivation_case_id for row in rows if row.reactivation_case_id},
        )
        tasks = await self._mapped(Task, {row.task_id for row in rows if row.task_id})
        users = await self._mapped(
            User,
            {
                user_id
                for row in rows
                for user_id in (row.recipient_user_id, row.actor_user_id)
                if user_id
            },
        )
        day_start = self._day_start(timezone)
        day_end = day_start.replace(hour=23, minute=59, second=59, microsecond=999999)
        result: builtins.list[dict[str, Any]] = []
        for row in rows:
            contact = contacts.get(row.contact_id) if row.contact_id is not None else None
            case = (
                cases.get(row.reactivation_case_id)
                if row.reactivation_case_id is not None
                else None
            )
            task = tasks.get(row.task_id) if row.task_id is not None else None
            lifecycle = "resolved" if row.resolved_at else "active"
            if row.due_at and not row.resolved_at:
                lifecycle = (
                    "overdue"
                    if row.due_at < day_start
                    else "due_today"
                    if row.due_at <= day_end
                    else "upcoming"
                )
            result.append(
                {
                    "id": row.public_id,
                    "type": row.notification_type,
                    "title": row.title,
                    "body": row.body,
                    "read_status": "read" if row.read_at else "unread",
                    "lifecycle_status": lifecycle,
                    "due_at": row.due_at,
                    "read_at": row.read_at,
                    "resolved_at": row.resolved_at,
                    "created_at": row.created_at,
                    "recipient": self._user_ref(users.get(row.recipient_user_id)),
                    "actor": self._user_ref(
                        users.get(row.actor_user_id) if row.actor_user_id is not None else None
                    ),
                    "contact": self._entity_ref(contact),
                    "reactivation_case": self._entity_ref(case),
                    "task": self._entity_ref(task),
                }
            )
        return result

    async def _mapped(self, model: Any, ids: set[int]) -> dict[int, Any]:
        if not ids:
            return {}
        rows = list((await self._session.scalars(select(model).where(model.id.in_(ids)))).all())
        return {row.id: row for row in rows}

    @staticmethod
    def _entity_ref(row: Any | None) -> dict[str, Any] | None:
        if row is None:
            return None
        result: dict[str, Any] = {"id": row.public_id}
        if isinstance(row, Contact):
            result["name"] = row.full_name or row.profile_name or row.phone_e164
        return result

    @staticmethod
    def _user_ref(row: User | None) -> dict[str, Any] | None:
        return {"id": row.public_id, "name": row.full_name} if row else None

    @staticmethod
    def _day_start(timezone: str) -> datetime:
        try:
            zone = ZoneInfo(timezone)
        except ZoneInfoNotFoundError:
            zone = ZoneInfo("UTC")
        local = utcnow().replace(tzinfo=ZoneInfo("UTC")).astimezone(zone)
        return (
            local.replace(hour=0, minute=0, second=0, microsecond=0)
            .astimezone(ZoneInfo("UTC"))
            .replace(tzinfo=None)
        )
