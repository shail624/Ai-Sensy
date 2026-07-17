"""Template registry repositories (Doc 03 §7.1)."""

from __future__ import annotations

from sqlalchemy import func, select

from app.models.template import MessageTemplate, TemplateVersion
from app.repositories.base import BaseRepository


class TemplateRepository(BaseRepository[MessageTemplate]):
    model = MessageTemplate

    def _filters(
        self,
        organization_id: int,
        *,
        waba_pk: int | None = None,
        status: str | None = None,
        category: str | None = None,
        language: str | None = None,
        q: str | None = None,
    ) -> list:
        clauses = [
            MessageTemplate.organization_id == organization_id,
            MessageTemplate.deleted_at.is_(None),
        ]
        if waba_pk is not None:
            clauses.append(MessageTemplate.waba_id == waba_pk)
        if status:
            clauses.append(MessageTemplate.status == status)
        if category:
            clauses.append(MessageTemplate.category == category)
        if language:
            clauses.append(MessageTemplate.language == language)
        if q:
            clauses.append(MessageTemplate.name.like(f"%{q}%"))
        return clauses

    async def list_for_org(self, organization_id: int, **filters) -> list[MessageTemplate]:
        stmt = (
            select(MessageTemplate)
            .where(*self._filters(organization_id, **filters))
            .order_by(MessageTemplate.name, MessageTemplate.language)
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_active_by_uuid(
        self, organization_id: int, public_id: bytes
    ) -> MessageTemplate | None:
        stmt = select(MessageTemplate).where(
            MessageTemplate.organization_id == organization_id,
            MessageTemplate.uuid == public_id,
            MessageTemplate.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def get_by_name_language(
        self, waba_pk: int, name: str, language: str
    ) -> MessageTemplate | None:
        """The ``uq_tpl_waba_name_lang`` lookup — Meta's own uniqueness rule (Doc 03 §7.1).

        Ignores ``deleted_at``: a soft-deleted row still holds the unique key, so sync must find
        and revive it rather than collide with it.
        """
        stmt = select(MessageTemplate).where(
            MessageTemplate.waba_id == waba_pk,
            MessageTemplate.name == name,
            MessageTemplate.language == language,
        )
        return (await self.session.scalars(stmt)).first()

    async def list_for_waba(self, waba_pk: int) -> list[MessageTemplate]:
        stmt = select(MessageTemplate).where(
            MessageTemplate.waba_id == waba_pk, MessageTemplate.deleted_at.is_(None)
        )
        return list((await self.session.scalars(stmt)).all())


class TemplateVersionRepository(BaseRepository[TemplateVersion]):
    model = TemplateVersion

    async def list_for_template(self, template_pk: int) -> list[TemplateVersion]:
        stmt = (
            select(TemplateVersion)
            .where(TemplateVersion.template_id == template_pk)
            .order_by(TemplateVersion.version_no.desc())
        )
        return list((await self.session.scalars(stmt)).all())

    async def next_version_no(self, template_pk: int) -> int:
        stmt = select(func.max(TemplateVersion.version_no)).where(
            TemplateVersion.template_id == template_pk
        )
        return int((await self.session.scalar(stmt)) or 0) + 1
