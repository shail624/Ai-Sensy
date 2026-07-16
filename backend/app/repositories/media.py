"""Media asset repository (Doc 03 §7.2)."""

from __future__ import annotations

from sqlalchemy import func, or_, select

from app.models.media import MediaAsset
from app.repositories.base import BaseRepository


class MediaRepository(BaseRepository[MediaAsset]):
    model = MediaAsset

    async def get_active_by_uuid(self, organization_id: int, public_id: bytes) -> MediaAsset | None:
        stmt = select(MediaAsset).where(
            MediaAsset.organization_id == organization_id,
            MediaAsset.uuid == public_id,
            MediaAsset.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def get_by_sha256(self, organization_id: int, sha256: str) -> MediaAsset | None:
        """Content dedup lookup — one blob reused org-wide (FR-MED-05)."""
        stmt = select(MediaAsset).where(
            MediaAsset.organization_id == organization_id, MediaAsset.sha256 == sha256
        )
        return (await self.session.scalars(stmt)).first()

    def _filters(self, organization_id: int, *, media_type: str | None, q: str | None) -> list:
        clauses = [
            MediaAsset.organization_id == organization_id,
            MediaAsset.deleted_at.is_(None),
        ]
        if media_type:
            clauses.append(MediaAsset.media_type == media_type)
        if q:
            like = f"%{q.strip().lower()}%"
            clauses.append(
                or_(
                    func.lower(MediaAsset.file_name).like(like),
                    func.lower(MediaAsset.mime_type).like(like),
                )
            )
        return clauses

    async def list_for_org(
        self, organization_id: int, *, media_type: str | None = None, q: str | None = None,
        limit: int = 50,
    ) -> list[MediaAsset]:
        stmt = (
            select(MediaAsset)
            .where(*self._filters(organization_id, media_type=media_type, q=q))
            .order_by(MediaAsset.created_at.desc(), MediaAsset.id.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).all())

    async def count(
        self, organization_id: int, *, media_type: str | None = None, q: str | None = None
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(MediaAsset)
            .where(*self._filters(organization_id, media_type=media_type, q=q))
        )
        return int((await self.session.scalar(stmt)) or 0)
