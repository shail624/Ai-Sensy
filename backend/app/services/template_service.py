"""Template registry service (Doc 04 §15; Doc 03 §7.1) — FR-TPL-01/02/03/04/08.

The registry is a **mirror, not a source**: Meta owns approval, quality and — since its category
review — the category itself. So every write here is careful about which side owns what. We own the
definition of a draft; Meta owns everything about it the moment it is submitted, which is why an
approved template cannot be edited (Doc 04 §15 → 409) and why sync overwrites state without asking.

Meta is reached only through the adapter resolved from the registry (Doc 07 §5.4), and validation
runs before submission to cut rejection loops (Doc 04 §15).
"""

from __future__ import annotations

import uuid as uuidlib
from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.models import ChannelTemplate
from app.core.exceptions import ConflictError, NotFoundError, VersionConflictError
from app.core.logging import get_logger
from app.db.mixins import utcnow
from app.models.audit import ACTOR_SYSTEM
from app.models.template import (
    TPL_DRAFT,
    TPL_PENDING,
    MessageTemplate,
    TemplateVersion,
)
from app.models.user import User
from app.models.waba import WhatsAppBusinessAccount
from app.repositories.template import TemplateRepository, TemplateVersionRepository
from app.repositories.waba import WabaRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.job_service import JobService
from app.services.template_validation import (
    has_media_header,
    render,
    validate_definition,
    variable_count,
)
from app.services.waba_service import WabaService

logger = get_logger(__name__)

#: Doc 06 §2.3's on-demand Meta sync lane — the same lane the WABA's numbers use.
SYNC_QUEUE = "templates.sync"
SYNC_TASK = "app.channels.tasks.run_template_sync"


class TemplateService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._templates = TemplateRepository(session)
        self._versions = TemplateVersionRepository(session)
        self._wabas = WabaRepository(session)
        self._audit = AuditService(session)

    # --- Reads ---------------------------------------------------------------
    async def list_templates(
        self,
        organization_id: int,
        *,
        waba_uuid: uuidlib.UUID | None = None,
        **filters: str | None,
    ) -> list[MessageTemplate]:
        waba_pk = (await self._waba(organization_id, waba_uuid)).id if waba_uuid else None
        return await self._templates.list_for_org(organization_id, waba_pk=waba_pk, **filters)

    async def get_template(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> MessageTemplate:
        template = await self._templates.get_active_by_uuid(organization_id, public_id.bytes)
        if template is None:
            raise NotFoundError("Template not found.")
        return template

    async def waba_public_id(self, template: MessageTemplate) -> str:
        waba = await self._wabas.get_by_id(template.waba_id)
        return waba.public_id if waba else ""

    async def versions(self, template: MessageTemplate) -> list[TemplateVersion]:
        return await self._versions.list_for_template(template.id)

    async def preview(
        self, template: MessageTemplate, *, header: list[str], body: list[str]
    ) -> dict[str, str]:
        """Render with sample values (FR-TPL-08). Pure: nothing is stored, nothing is sent."""
        return render(template.components_json or [], header=header, body=body)

    # --- Writes --------------------------------------------------------------
    async def create(
        self,
        *,
        organization_id: int,
        actor: User,
        waba_public_id: uuidlib.UUID,
        name: str,
        language: str,
        category: str,
        components: list[dict[str, Any]],
        submit: bool,
    ) -> MessageTemplate:
        """Create a template and, unless held as a draft, submit it to Meta (FR-TPL-02)."""
        waba = await self._waba(organization_id, waba_public_id)
        validate_definition(category=category, components=components)

        existing = await self._templates.get_by_name_language(waba.id, name, language)
        if existing is not None and existing.deleted_at is None:
            raise ConflictError(f"Template {name!r} already exists in {language!r} on this WABA.")

        template = existing or MessageTemplate(
            organization_id=organization_id, waba_id=waba.id, name=name, language=language
        )
        if existing is not None:
            # Revive rather than violate `uq_tpl_waba_name_lang`, which spans soft-deleted rows.
            template.deleted_at = None
            template.meta_template_id = None
        self._apply_definition(template, category=category, components=components)
        template.status = TPL_DRAFT
        template.rejection_reason = None
        template.created_by = actor.id
        await self._templates.add(template)
        await self._record_version(template, actor_id=actor.id)

        if submit:
            await self._submit(waba, template)

        await self._audit.record(
            AuditAction.TEMPLATE_CREATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="template",
            entity_id=template.id,
            after={"name": name, "language": language, "category": category,
                   "status": template.status},
        )
        await self._session.commit()
        return template

    async def update(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        category: str | None,
        components: list[dict[str, Any]] | None,
        submit: bool,
        expected_version: int | None,
    ) -> MessageTemplate:
        """Edit a draft or a rejected template (Doc 04 §15 → 409 once Meta owns it)."""
        template = await self.get_template(organization_id, public_id)
        if expected_version is not None and expected_version != template.row_version:
            raise VersionConflictError("The template was modified by someone else; reload.")
        if not template.is_editable:
            raise ConflictError(
                f"A {template.status} template cannot be edited; create a new one instead."
            )

        category = category or template.category
        components = components if components is not None else (template.components_json or [])
        validate_definition(category=category, components=components)
        self._apply_definition(template, category=category, components=components)
        template.updated_by = actor.id
        template.row_version += 1
        template.rejection_reason = None
        template.status = TPL_DRAFT
        await self._templates.flush()
        await self._record_version(template, actor_id=actor.id)

        if submit:
            waba = await self._wabas.get_by_id(template.waba_id)
            if waba is None:
                raise NotFoundError("WABA not found.")
            await self._submit(waba, template)

        await self._audit.record(
            AuditAction.TEMPLATE_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="template",
            entity_id=template.id,
            after={"status": template.status, "category": template.category},
        )
        await self._session.commit()
        return template

    async def delete(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> None:
        """Withdraw from Meta, then soft-delete locally (Doc 04 §15).

        Meta first: if the remote call fails the row stays, so the registry never claims a template
        is gone while Meta still holds it.
        """
        template = await self.get_template(organization_id, public_id)
        if template.meta_template_id:
            waba = await self._wabas.get_by_id(template.waba_id)
            if waba is None:
                raise NotFoundError("WABA not found.")
            adapter = WabaService(self._session).adapter_for(waba)
            try:
                await adapter.delete_template(template.name, account_id=waba.waba_id)
            finally:
                await adapter.close()

        template.deleted_at = utcnow()
        template.updated_by = actor.id
        template.row_version += 1
        await self._templates.flush()
        await self._audit.record(
            AuditAction.TEMPLATE_DELETED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="template",
            entity_id=template.id,
            before={"name": template.name, "language": template.language},
        )
        await self._session.commit()

    async def _submit(self, waba: WhatsAppBusinessAccount, template: MessageTemplate) -> None:
        """Hand a definition to Meta and take back the state it assigns (FR-TPL-02/03)."""
        adapter = WabaService(self._session).adapter_for(waba)
        try:
            remote = await adapter.create_template(
                name=template.name,
                language=template.language,
                category=template.category,
                components=template.components_json or [],
                account_id=waba.waba_id,
            )
        finally:
            await adapter.close()
        template.meta_template_id = remote.channel_template_id
        # Meta may re-categorise on submission; its answer wins over what we asked for.
        template.category = remote.category or template.category
        template.status = remote.status or TPL_PENDING
        template.last_synced_at = utcnow()
        await self._templates.flush()

    @staticmethod
    def _apply_definition(
        template: MessageTemplate, *, category: str, components: list[dict[str, Any]]
    ) -> None:
        """Set the definition and everything derived from it — one place, so they cannot diverge."""
        template.category = category
        template.components_json = components
        template.variable_count = variable_count(components)
        template.has_media_header = has_media_header(components)

    async def _record_version(self, template: MessageTemplate, *, actor_id: int | None) -> None:
        await self._versions.add(
            TemplateVersion(
                template_id=template.id,
                version_no=await self._versions.next_version_no(template.id),
                components_json=template.components_json,
                category=template.category,
                status=template.status,
                created_by=actor_id,
            )
        )

    async def _waba(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> WhatsAppBusinessAccount:
        waba = await self._wabas.get_active_by_uuid(organization_id, public_id.bytes)
        if waba is None:
            raise NotFoundError("WABA not found.")
        return waba

    # --- Sync (Doc 04 §15 — 202 + job; FR-TPL-01/03) ------------------------
    async def start_sync(
        self,
        *,
        organization_id: int,
        actor: User,
        waba_public_id: uuidlib.UUID | None,
        dispatch: Callable[[list[str], str], Any],
    ) -> str:
        """Enqueue a sync of one WABA or all of them — no Meta call on the request path."""
        if waba_public_id is not None:
            wabas = [await self._waba(organization_id, waba_public_id)]
        else:
            wabas = await self._wabas.list_for_org(organization_id)

        task_id = str(uuidlib.uuid4())
        job = await JobService(self._session).record_queued(
            task_id=task_id,
            task_name=SYNC_TASK,
            queue=SYNC_QUEUE,
            args={"wabas": [w.public_id for w in wabas]},
            ref_type="waba",
            ref_id=wabas[0].id if wabas else None,
        )
        await self._audit.record(
            AuditAction.TEMPLATE_SYNC_STARTED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="template",
            after={"wabas": len(wabas)},
        )
        await self._session.commit()
        dispatch([w.public_id for w in wabas], task_id)
        return job.public_id

    async def run_sync(self, waba_public_ids: list[str]) -> dict[str, int]:
        """Reconcile the registry with Meta (task body; FR-TPL-01/03).

        Idempotent: templates are matched on Meta's own key — (WABA, name, language) — so a
        redelivered task updates in place. Templates Meta no longer reports are soft-deleted; a
        template is never hard-deleted, because sent messages reference it.
        """
        totals = {"created": 0, "updated": 0, "removed": 0}
        for public_id in waba_public_ids:
            waba = await self._wabas.get_by_uuid(uuidlib.UUID(public_id))
            if waba is None:
                continue
            for key, value in (await self._sync_waba(waba)).items():
                totals[key] += value
        await self._session.commit()
        return totals

    async def _sync_waba(self, waba: WhatsAppBusinessAccount) -> dict[str, int]:
        adapter = WabaService(self._session).adapter_for(waba)
        try:
            remotes = await adapter.list_templates(waba.waba_id)
        finally:
            await adapter.close()

        existing = {
            (t.name, t.language): t for t in await self._templates.list_for_waba(waba.id)
        }
        seen: set[tuple[str, str]] = set()
        created = updated = 0

        for remote in remotes:
            if not remote.name or not remote.language:
                continue
            key = (remote.name, remote.language)
            seen.add(key)
            template = existing.get(key) or await self._templates.get_by_name_language(
                waba.id, remote.name, remote.language
            )
            if template is None:
                template = MessageTemplate(
                    organization_id=waba.organization_id,
                    waba_id=waba.id,
                    name=remote.name,
                    language=remote.language,
                )
                self._apply_remote(template, remote)
                await self._templates.add(template)
                created += 1
            else:
                template.deleted_at = None
                self._apply_remote(template, remote)
                updated += 1

        removed = 0
        for key, template in existing.items():
            # A draft we have never submitted is ours, not Meta's — its absence proves nothing.
            if key not in seen and template.meta_template_id:
                template.deleted_at = utcnow()
                removed += 1

        await self._templates.flush()
        await self._audit.record(
            AuditAction.TEMPLATE_SYNCED,
            actor_type=ACTOR_SYSTEM,
            organization_id=waba.organization_id,
            entity_type="waba",
            entity_id=waba.id,
            after={"created": created, "updated": updated, "removed": removed},
        )
        return {"created": created, "updated": updated, "removed": removed}

    def _apply_remote(self, template: MessageTemplate, remote: ChannelTemplate) -> None:
        """Copy Meta-owned facts onto a stored template. Meta owns all of these (FR-TPL-03)."""
        template.meta_template_id = remote.channel_template_id or template.meta_template_id
        template.status = remote.status
        template.quality_score = remote.quality_score
        template.rejection_reason = remote.rejection_reason
        if remote.components:
            self._apply_definition(
                template, category=remote.category, components=remote.components
            )
        else:
            template.category = remote.category
        template.last_synced_at = utcnow()
