"""Tenant-scoped persistence for governed customer documents."""

from __future__ import annotations

from sqlalchemy import func, select

from app.models.contact_document import (
    ContactDocument,
    ContactDocumentEvent,
    ContactDocumentVersion,
)
from app.models.media import MediaAsset
from app.repositories.base import BaseRepository


class ContactDocumentRepository(BaseRepository[ContactDocument]):
    model = ContactDocument

    async def get_active_by_uuid(
        self, organization_id: int, public_id: bytes
    ) -> ContactDocument | None:
        stmt = select(ContactDocument).where(
            ContactDocument.organization_id == organization_id,
            ContactDocument.uuid == public_id,
            ContactDocument.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def list_for_contact(
        self,
        organization_id: int,
        contact_id: int,
        *,
        statuses: list[str] | None,
        document_types: list[str] | None,
        q: str | None,
        limit: int,
    ) -> tuple[list[ContactDocument], int]:
        clauses = [
            ContactDocument.organization_id == organization_id,
            ContactDocument.contact_id == contact_id,
            ContactDocument.deleted_at.is_(None),
        ]
        if statuses:
            clauses.append(ContactDocument.status.in_(statuses))
        if document_types:
            clauses.append(ContactDocument.document_type.in_(document_types))
        if q:
            like = f"%{q.strip().lower()}%"
            clauses.append(func.lower(ContactDocument.title).like(like))
        stmt = (
            select(ContactDocument)
            .where(*clauses)
            .order_by(ContactDocument.updated_at.desc(), ContactDocument.id.desc())
            .limit(limit)
        )
        count_stmt = select(func.count()).select_from(ContactDocument).where(*clauses)
        rows = list((await self.session.scalars(stmt)).all())
        total = int((await self.session.scalar(count_stmt)) or 0)
        return rows, total

    async def list_versions(self, document_ids: list[int]) -> list[ContactDocumentVersion]:
        if not document_ids:
            return []
        stmt = (
            select(ContactDocumentVersion)
            .where(ContactDocumentVersion.document_id.in_(document_ids))
            .order_by(
                ContactDocumentVersion.document_id.asc(),
                ContactDocumentVersion.version_no.asc(),
            )
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_version(
        self, organization_id: int, document_id: int, public_id: bytes
    ) -> ContactDocumentVersion | None:
        stmt = select(ContactDocumentVersion).where(
            ContactDocumentVersion.organization_id == organization_id,
            ContactDocumentVersion.document_id == document_id,
            ContactDocumentVersion.uuid == public_id,
        )
        return (await self.session.scalars(stmt)).first()

    async def list_events(self, document_id: int) -> list[ContactDocumentEvent]:
        stmt = (
            select(ContactDocumentEvent)
            .where(ContactDocumentEvent.document_id == document_id)
            .order_by(ContactDocumentEvent.created_at.asc(), ContactDocumentEvent.id.asc())
        )
        return list((await self.session.scalars(stmt)).all())

    async def media_map(self, media_ids: set[int]) -> dict[int, MediaAsset]:
        if not media_ids:
            return {}
        rows = list(
            (
                await self.session.scalars(select(MediaAsset).where(MediaAsset.id.in_(media_ids)))
            ).all()
        )
        return {row.id: row for row in rows}

    async def search_duplicate_media(
        self, document_id: int, media_asset_id: int
    ) -> ContactDocumentVersion | None:
        stmt = select(ContactDocumentVersion).where(
            ContactDocumentVersion.document_id == document_id,
            ContactDocumentVersion.media_asset_id == media_asset_id,
        )
        return (await self.session.scalars(stmt)).first()

    async def next_version_no(self, document_id: int) -> int:
        value = await self.session.scalar(
            select(func.max(ContactDocumentVersion.version_no)).where(
                ContactDocumentVersion.document_id == document_id
            )
        )
        return int(value or 0) + 1

    async def list_users(self, ids: set[int]) -> dict[int, tuple[str, str]]:
        if not ids:
            return {}
        from app.models.user import User

        rows = list((await self.session.scalars(select(User).where(User.id.in_(ids)))).all())
        return {row.id: (row.public_id, row.full_name) for row in rows}
