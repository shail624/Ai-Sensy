"""Tenant-scoped queries for the durable notification projection."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.engine import CursorResult

from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    async def by_dedup(self, organization_id: int, dedup_key: str) -> Notification | None:
        return (
            await self.session.scalars(
                select(Notification).where(
                    Notification.organization_id == organization_id,
                    Notification.dedup_key == dedup_key,
                )
            )
        ).first()

    async def get_for_recipient(
        self, organization_id: int, recipient_id: int, public_id: bytes
    ) -> Notification | None:
        return (
            await self.session.scalars(
                select(Notification).where(
                    Notification.organization_id == organization_id,
                    Notification.recipient_user_id == recipient_id,
                    Notification.uuid == public_id,
                )
            )
        ).first()

    async def list_page(
        self,
        organization_id: int,
        recipient_id: int,
        *,
        notification_type: str | None,
        status: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        overdue_before: datetime,
        cursor: tuple[datetime, int] | None,
        limit: int,
    ) -> tuple[list[Notification], bool]:
        clauses = [
            Notification.organization_id == organization_id,
            Notification.recipient_user_id == recipient_id,
        ]
        if notification_type:
            clauses.append(Notification.notification_type == notification_type)
        if status == "unread":
            clauses.append(Notification.read_at.is_(None))
        elif status == "read":
            clauses.append(Notification.read_at.is_not(None))
        elif status == "overdue":
            clauses.extend(
                [Notification.resolved_at.is_(None), Notification.due_at < overdue_before]
            )
        elif status == "resolved":
            clauses.append(Notification.resolved_at.is_not(None))
        if date_from:
            clauses.append(Notification.created_at >= date_from)
        if date_to:
            clauses.append(Notification.created_at <= date_to)
        if cursor:
            created_at, row_id = cursor
            clauses.append(
                or_(
                    Notification.created_at < created_at,
                    and_(Notification.created_at == created_at, Notification.id < row_id),
                )
            )
        stmt = (
            select(Notification)
            .where(*clauses)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self.session.scalars(stmt)).all())
        return rows[:limit], len(rows) > limit

    async def unread_count(self, organization_id: int, recipient_id: int) -> int:
        return int(
            (
                await self.session.scalar(
                    select(func.count())
                    .select_from(Notification)
                    .where(
                        Notification.organization_id == organization_id,
                        Notification.recipient_user_id == recipient_id,
                        Notification.read_at.is_(None),
                    )
                )
            )
            or 0
        )

    async def mark_all_read(
        self, organization_id: int, recipient_id: int, read_at: datetime
    ) -> int:
        result = cast(
            CursorResult[Any],
            await self.session.execute(
                update(Notification)
                .where(
                    Notification.organization_id == organization_id,
                    Notification.recipient_user_id == recipient_id,
                    Notification.read_at.is_(None),
                )
                .values(read_at=read_at, updated_at=read_at)
            ),
        )
        return int(result.rowcount or 0)

    async def resolve_task(self, organization_id: int, task_id: int, resolved_at: datetime) -> int:
        result = cast(
            CursorResult[Any],
            await self.session.execute(
                update(Notification)
                .where(
                    Notification.organization_id == organization_id,
                    Notification.task_id == task_id,
                    Notification.resolved_at.is_(None),
                )
                .values(resolved_at=resolved_at, updated_at=resolved_at)
            ),
        )
        return int(result.rowcount or 0)
