"""Job metadata & dead-letter repositories (Doc 03 §11.7, Doc 06 §7)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select

from app.models.job import DL_PARKED, DeadLetter, JobMetadata
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository[JobMetadata]):
    model = JobMetadata

    async def get_by_task_id(self, task_id: str) -> JobMetadata | None:
        stmt = select(JobMetadata).where(JobMetadata.task_id == task_id)
        return (await self.session.scalars(stmt)).first()

    def _filters(self, *, status: str | None, task_name: str | None, queue: str | None) -> list:
        clauses: list = []
        if status:
            clauses.append(JobMetadata.status == status)
        if task_name:
            clauses.append(JobMetadata.task_name == task_name)
        if queue:
            clauses.append(JobMetadata.queue == queue)
        return clauses

    async def paginate(
        self,
        *,
        limit: int,
        cursor: tuple[datetime, int] | None,
        status: str | None = None,
        task_name: str | None = None,
        queue: str | None = None,
    ) -> tuple[list[JobMetadata], bool]:
        clauses = self._filters(status=status, task_name=task_name, queue=queue)
        if cursor is not None:
            c_created, c_id = cursor
            clauses.append(
                (JobMetadata.created_at < c_created)
                | ((JobMetadata.created_at == c_created) & (JobMetadata.id < c_id))
            )
        stmt = (
            select(JobMetadata)
            .where(*clauses)
            .order_by(JobMetadata.created_at.desc(), JobMetadata.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self.session.scalars(stmt)).all())
        return rows[:limit], len(rows) > limit

    async def count(
        self, *, status: str | None = None, task_name: str | None = None, queue: str | None = None
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(JobMetadata)
            .where(*self._filters(status=status, task_name=task_name, queue=queue))
        )
        return int((await self.session.scalar(stmt)) or 0)


class DeadLetterRepository(BaseRepository[DeadLetter]):
    model = DeadLetter

    async def list_parked(self, limit: int = 50) -> list[DeadLetter]:
        stmt = (
            select(DeadLetter)
            .where(DeadLetter.status == DL_PARKED)
            .order_by(DeadLetter.created_at.desc(), DeadLetter.id.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).all())

    async def count_parked(self) -> int:
        stmt = (
            select(func.count()).select_from(DeadLetter).where(DeadLetter.status == DL_PARKED)
        )
        return int((await self.session.scalar(stmt)) or 0)

    async def oldest_parked_at(self) -> datetime | None:
        stmt = select(func.min(DeadLetter.created_at)).where(DeadLetter.status == DL_PARKED)
        return await self.session.scalar(stmt)
