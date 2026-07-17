"""WABA & phone-number services (Doc 04 §13.2/§13.3; FR-WA-01/02/03/04/13).

Provisioning for Channel 1. Meta is reached **only** through the channel adapter resolved from the
registry (Doc 07 §5.4) — no Graph call is constructed here, which is what keeps the seam honest.

Token handling (FR-WA-03, Doc 04 §13.2): the system-user token is encrypted on the way in
(:mod:`app.core.crypto`) and decrypted only to build adapter credentials. It is never returned,
never logged, and never audited.

Sync is async (Doc 04 §13.2 → ``202`` + job): reconciling a WABA's numbers is a Meta round-trip, so
the request path records intent and hands off to the Queue Engine. It runs on ``templates.sync``,
which Doc 06 §2.3 defines as the on-demand "sync from Meta" lane keyed by ``waba_id`` + run —
numbers now; templates join the same job when M5 lands.
"""

from __future__ import annotations

import uuid as uuidlib
from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import get_adapter
from app.channels.capabilities import CONNECTOR_META_CLOUD, ChannelType
from app.channels.meta.client import MetaCredentials
from app.channels.models import ChannelPhoneNumber
from app.core.crypto import decrypt, encrypt
from app.core.exceptions import ConflictError, NotFoundError, VersionConflictError
from app.db.mixins import utcnow
from app.models.user import User
from app.models.waba import PhoneNumber, WhatsAppBusinessAccount
from app.repositories.waba import PhoneNumberRepository, WabaRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.job_service import JobService

#: Doc 06 §2.3's on-demand Meta sync lane (Maint pool, singleton-per-WABA, 60s/120s).
SYNC_QUEUE = "templates.sync"
SYNC_TASK = "app.channels.tasks.run_waba_sync"


class WabaService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._wabas = WabaRepository(session)
        self._numbers = PhoneNumberRepository(session)
        self._audit = AuditService(session)

    # --- Adapter access ------------------------------------------------------
    def adapter_for(self, waba: WhatsAppBusinessAccount, *, phone_number_id: str = ""):
        """Resolve the channel adapter bound to this WABA's credentials (Doc 07 §5.4)."""
        return get_adapter(
            CONNECTOR_META_CLOUD,
            credentials=MetaCredentials(
                access_token=decrypt(waba.access_token_enc),
                phone_number_id=phone_number_id,
                waba_id=waba.waba_id,
            ),
        )

    # --- Reads ---------------------------------------------------------------
    async def list_wabas(self, organization_id: int) -> list[tuple[WhatsAppBusinessAccount, int]]:
        wabas = await self._wabas.list_for_org(organization_id)
        return [(waba, len(waba.phone_numbers)) for waba in wabas]

    async def get_waba(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> WhatsAppBusinessAccount:
        waba = await self._wabas.get_active_by_uuid(organization_id, public_id.bytes)
        if waba is None:
            raise NotFoundError("WABA not found.")
        return waba

    async def number_count(self, waba: WhatsAppBusinessAccount) -> int:
        return await self._wabas.count_numbers(waba.id)

    # --- Writes --------------------------------------------------------------
    async def connect(
        self,
        *,
        organization_id: int,
        actor: User,
        waba_id: str,
        business_name: str,
        access_token: str,
        meta_business_id: str | None,
        currency: str | None,
        timezone: str | None,
        token_expires_at: Any = None,
    ) -> WhatsAppBusinessAccount:
        """Connect a WABA (FR-WA-01). The token is encrypted before it is ever persisted."""
        if await self._wabas.meta_id_exists(waba_id):
            raise ConflictError(f"WABA {waba_id!r} is already connected.")
        waba = WhatsAppBusinessAccount(
            organization_id=organization_id,
            waba_id=waba_id,
            business_name=business_name,
            meta_business_id=meta_business_id,
            access_token_enc=encrypt(access_token),
            token_expires_at=token_expires_at,
            currency=currency,
            timezone=timezone,
            created_by=actor.id,
        )
        await self._wabas.add(waba)
        await self._audit.record(
            AuditAction.WABA_CONNECTED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="waba",
            entity_id=waba.id,
            # Never the token — only that one was supplied.
            after={"waba_id": waba_id, "business_name": business_name, "token_set": True},
        )
        await self._session.commit()
        await self._session.refresh(waba, ["phone_numbers"])
        return waba

    async def update(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        fields: dict[str, Any],
        access_token: str | None,
        expected_version: int | None,
    ) -> WhatsAppBusinessAccount:
        """Amend metadata and/or rotate the token (Doc 04 §13.2)."""
        waba = await self.get_waba(organization_id, public_id)
        if expected_version is not None and expected_version != waba.row_version:
            raise VersionConflictError("The WABA was modified by someone else; reload and retry.")
        for key, value in fields.items():
            setattr(waba, key, value)
        if access_token:
            waba.access_token_enc = encrypt(access_token)
        waba.updated_by = actor.id
        waba.row_version += 1
        await self._wabas.flush()
        await self._audit.record(
            AuditAction.WABA_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="waba",
            entity_id=waba.id,
            after={"fields": sorted(fields), "token_rotated": bool(access_token)},
        )
        await self._session.commit()
        return waba

    async def disconnect(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> None:
        """Soft-disconnect a WABA. Refuses while it still owns numbers (Doc 04 §13.2 → 409)."""
        waba = await self.get_waba(organization_id, public_id)
        remaining = await self._wabas.count_numbers(waba.id)
        if remaining:
            raise ConflictError(
                f"WABA still has {remaining} phone number(s); remove them before disconnecting."
            )
        waba.deleted_at = utcnow()
        waba.updated_by = actor.id
        waba.row_version += 1
        await self._wabas.flush()
        await self._audit.record(
            AuditAction.WABA_DISCONNECTED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="waba",
            entity_id=waba.id,
            before={"waba_id": waba.waba_id},
        )
        await self._session.commit()

    # --- Sync (Doc 04 §13.2 — 202 + job) ------------------------------------
    async def start_sync(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        dispatch: Callable[[str, str], Any],
    ) -> tuple[WhatsAppBusinessAccount, str]:
        """Enqueue a sync and return immediately — no Meta call on the request path."""
        waba = await self.get_waba(organization_id, public_id)
        task_id = str(uuidlib.uuid4())
        job = await JobService(self._session).record_queued(
            task_id=task_id,
            task_name=SYNC_TASK,
            queue=SYNC_QUEUE,
            args={"waba_id": waba.public_id},
            ref_type="waba",
            ref_id=waba.id,
        )
        await self._audit.record(
            AuditAction.WABA_SYNC_STARTED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="waba",
            entity_id=waba.id,
            after={"waba_id": waba.waba_id},
        )
        await self._session.commit()
        dispatch(waba.public_id, task_id)
        return waba, job.public_id

    def _apply(self, number: PhoneNumber, remote: ChannelPhoneNumber) -> None:
        """Copy Meta-owned facts onto a stored number. Operator-owned fields are left alone."""
        number.display_number = remote.display_number or number.display_number
        number.verified_name = remote.verified_name
        number.quality_rating = remote.quality_rating
        number.messaging_tier = remote.messaging_tier
        number.throughput_level = remote.throughput_level
        if remote.status:
            number.status = remote.status
        number.last_synced_at = utcnow()

    async def run_sync(self, waba_public_id: str) -> dict[str, int]:
        """Reconcile a WABA's numbers against Meta (task body).

        Idempotent: numbers are matched on Meta's ``phone_number_id``, so a redelivered task
        updates in place rather than duplicating (Doc 06 §8). Numbers Meta no longer reports are
        soft-deleted; a number is never hard-deleted, because history may reference it.
        """
        waba = await self._wabas.get_by_uuid(uuidlib.UUID(waba_public_id))
        if waba is None:
            raise NotFoundError("WABA not found.")

        adapter = self.adapter_for(waba)
        try:
            remotes = await adapter.list_phone_numbers()
        finally:
            await adapter.close()

        existing = {n.phone_number_id: n for n in await self._numbers.list_for_waba(waba.id)}
        seen: set[str] = set()
        created = updated = 0

        for remote in remotes:
            if not remote.phone_number_id:
                continue
            seen.add(remote.phone_number_id)
            number = existing.get(remote.phone_number_id)
            if number is None:
                # A number may have been soft-deleted by an earlier sync, or belong elsewhere:
                # the Meta id is globally unique, so reuse the row rather than collide on it.
                number = await self._numbers.get_by_meta_id(remote.phone_number_id)
            if number is None:
                number = PhoneNumber(
                    organization_id=waba.organization_id,
                    waba_id=waba.id,
                    channel_type=ChannelType.WHATSAPP.value,
                    phone_number_id=remote.phone_number_id,
                    display_number=remote.display_number,
                )
                self._apply(number, remote)
                await self._numbers.add(number)
                created += 1
            else:
                number.waba_id = waba.id
                number.deleted_at = None
                self._apply(number, remote)
                updated += 1

        removed = 0
        for phone_number_id, number in existing.items():
            if phone_number_id not in seen:
                number.deleted_at = utcnow()
                removed += 1

        await self._numbers.flush()
        await self._audit.record(
            AuditAction.WABA_SYNCED,
            actor_user_id=waba.updated_by or waba.created_by,
            organization_id=waba.organization_id,
            entity_type="waba",
            entity_id=waba.id,
            after={"created": created, "updated": updated, "removed": removed},
        )
        await self._session.commit()
        return {"created": created, "updated": updated, "removed": removed}
