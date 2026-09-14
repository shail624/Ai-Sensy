"""Current, tenant-scoped team workload assembled from operational authorities.

This is deliberately a snapshot rather than an Analytics rollup. Pending conversations and open
tasks are stock values whose historical samples must never be added together. Conversation and
Task remain the authorities; this service only performs bounded indexed groupings for the team
workload screen.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mixins import utcnow
from app.models.conversation import CONV_RESOLVED, Conversation
from app.models.task import TASK_STATUS_OPEN, Task
from app.repositories.user import UserRepository

_UTC = ZoneInfo("UTC")


@dataclass(frozen=True, slots=True)
class TeamWorkloadItem:
    user_id: str | None
    user_name: str
    is_active: bool | None
    unresolved_conversations: int
    unread_conversations: int
    unread_messages: int
    open_tasks: int
    overdue_tasks: int
    due_today_tasks: int

    @property
    def attention_required(self) -> bool:
        return bool(
            self.user_id is None
            or (self.is_active is False and (self.unresolved_conversations or self.open_tasks))
            or self.unread_conversations
            or self.overdue_tasks
        )


@dataclass(frozen=True, slots=True)
class TeamWorkloadSnapshot:
    as_of: datetime
    timezone: str
    data: list[TeamWorkloadItem]


def _day_bounds_utc(timezone_name: str) -> tuple[datetime, datetime, str]:
    """Return today's half-open bounds in stored naive UTC and the effective timezone name."""
    try:
        timezone = ZoneInfo(timezone_name)
        effective_name = timezone_name
    except (ZoneInfoNotFoundError, ValueError):
        timezone = _UTC
        effective_name = "UTC"
    local_now = datetime.now(timezone)
    local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    local_end = local_start + timedelta(days=1)
    return (
        local_start.astimezone(_UTC).replace(tzinfo=None),
        local_end.astimezone(_UTC).replace(tzinfo=None),
        effective_name,
    )


class TeamWorkloadService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)

    async def snapshot(
        self, *, organization_id: int, timezone_name: str
    ) -> TeamWorkloadSnapshot:
        """Return active teammates plus any inactive/unassigned cohort that still owns work."""
        as_of = utcnow()
        day_start, day_end, effective_timezone = _day_bounds_utc(timezone_name)

        conversation_stmt = (
            select(
                Conversation.assigned_user_id,
                func.count(Conversation.id),
                func.sum(case((Conversation.unread_count > 0, 1), else_=0)),
                func.sum(Conversation.unread_count),
            )
            .where(
                Conversation.organization_id == organization_id,
                Conversation.deleted_at.is_(None),
                Conversation.status != CONV_RESOLVED,
            )
            .group_by(Conversation.assigned_user_id)
        )
        conversation_counts = {
            assignee_id: (int(unresolved or 0), int(unread or 0), int(messages or 0))
            for assignee_id, unresolved, unread, messages in (
                await self._session.execute(conversation_stmt)
            ).all()
        }

        task_stmt = (
            select(
                Task.assigned_agent_id,
                func.count(Task.id),
                func.sum(case((Task.due_at < as_of, 1), else_=0)),
                func.sum(
                    case(
                        ((Task.due_at >= day_start) & (Task.due_at < day_end), 1),
                        else_=0,
                    )
                ),
            )
            .where(
                Task.organization_id == organization_id,
                Task.deleted_at.is_(None),
                Task.status == TASK_STATUS_OPEN,
            )
            .group_by(Task.assigned_agent_id)
        )
        task_counts = {
            int(assignee_id): (int(open_count or 0), int(overdue or 0), int(today or 0))
            for assignee_id, open_count, overdue, today in (
                await self._session.execute(task_stmt)
            ).all()
        }

        items: list[TeamWorkloadItem] = []
        for user in await self._users.list_workload_owners(organization_id):
            conversations = conversation_counts.get(user.id, (0, 0, 0))
            tasks = task_counts.get(user.id, (0, 0, 0))
            if not user.is_active and not any((*conversations, *tasks)):
                continue
            items.append(
                TeamWorkloadItem(
                    user_id=user.public_id,
                    user_name=user.full_name,
                    is_active=user.is_active,
                    unresolved_conversations=conversations[0],
                    unread_conversations=conversations[1],
                    unread_messages=conversations[2],
                    open_tasks=tasks[0],
                    overdue_tasks=tasks[1],
                    due_today_tasks=tasks[2],
                )
            )

        unassigned = conversation_counts.get(None, (0, 0, 0))
        if any(unassigned):
            items.append(
                TeamWorkloadItem(
                    user_id=None,
                    user_name="Unassigned",
                    is_active=None,
                    unresolved_conversations=unassigned[0],
                    unread_conversations=unassigned[1],
                    unread_messages=unassigned[2],
                    open_tasks=0,
                    overdue_tasks=0,
                    due_today_tasks=0,
                )
            )

        items.sort(
            key=lambda row: (
                not row.attention_required,
                -row.overdue_tasks,
                -row.unread_conversations,
                -(row.unresolved_conversations + row.open_tasks),
                row.user_name.casefold(),
            )
        )
        return TeamWorkloadSnapshot(
            as_of=as_of, timezone=effective_timezone, data=items
        )
