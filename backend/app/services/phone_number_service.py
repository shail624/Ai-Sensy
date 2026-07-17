"""Phone-number service (Doc 04 §13.3; FR-WA-02/04/13).

Reads and operator-owned edits over stored numbers, plus ``refresh`` — the one operation that
reaches Meta, and only through the adapter (Doc 07 §5.4).

Division of ownership: quality rating, tier, throughput and verified name are **Meta's** and only
sync/refresh write them; ``mps_limit`` and ``is_default`` are the **operator's** and Meta never
overwrites them. Keeping that line sharp is why `PATCH` accepts so few fields.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, VersionConflictError
from app.db.mixins import utcnow
from app.models.user import User
from app.models.waba import PhoneNumber
from app.repositories.waba import PhoneNumberRepository, WabaRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.waba_service import WabaService


class PhoneNumberService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._numbers = PhoneNumberRepository(session)
        self._wabas = WabaRepository(session)
        self._audit = AuditService(session)

    async def list_numbers(
        self,
        organization_id: int,
        *,
        waba_uuid: uuidlib.UUID | None = None,
        status: str | None = None,
        quality_rating: str | None = None,
    ) -> list[PhoneNumber]:
        waba_pk: int | None = None
        if waba_uuid is not None:
            waba = await self._wabas.get_active_by_uuid(organization_id, waba_uuid.bytes)
            if waba is None:
                raise NotFoundError("WABA not found.")
            waba_pk = waba.id
        return await self._numbers.list_for_org(
            organization_id, waba_pk=waba_pk, status=status, quality_rating=quality_rating
        )

    async def get_number(self, organization_id: int, public_id: uuidlib.UUID) -> PhoneNumber:
        number = await self._numbers.get_active_by_uuid(organization_id, public_id.bytes)
        if number is None:
            raise NotFoundError("Phone number not found.")
        return number

    async def waba_public_id(self, number: PhoneNumber) -> str:
        waba = await self._wabas.get_by_id(number.waba_id)
        return waba.public_id if waba else ""

    async def update(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        fields: dict[str, Any],
        expected_version: int | None,
    ) -> PhoneNumber:
        number = await self.get_number(organization_id, public_id)
        if expected_version is not None and expected_version != number.row_version:
            raise VersionConflictError(
                "The phone number was modified by someone else; reload and retry."
            )
        make_default = fields.pop("is_default", None)
        for key, value in fields.items():
            setattr(number, key, value)
        number.updated_by = actor.id
        number.row_version += 1
        await self._numbers.flush()
        if make_default is not None:
            number.is_default = make_default
            if make_default:
                # Exactly one default per org (Doc 03 §5.2 `is_default`).
                await self._numbers.clear_default(organization_id, except_pk=number.id)
            await self._numbers.flush()
        await self._audit.record(
            AuditAction.PHONE_NUMBER_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="phone_number",
            entity_id=number.id,
            after={"fields": sorted(fields) + (["is_default"] if make_default is not None else [])},
        )
        await self._session.commit()
        return number

    async def refresh(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> PhoneNumber:
        """Re-pull health/limits from Meta for one number (Doc 04 §13.3 → 502 on channel error).

        Synchronous by contract: unlike WABA sync this is a single cheap read, and the operator is
        waiting on the answer.
        """
        number = await self.get_number(organization_id, public_id)
        waba = await self._wabas.get_by_id(number.waba_id)
        if waba is None:
            raise NotFoundError("The owning WABA no longer exists.")

        adapter = WabaService(self._session).adapter_for(
            waba, phone_number_id=number.phone_number_id
        )
        try:
            signal = await adapter.health_signal()
        finally:
            await adapter.close()

        number.quality_rating = signal.quality_rating
        number.messaging_tier = signal.messaging_tier
        number.throughput_level = signal.throughput_limit
        if signal.detail:
            number.verified_name = signal.detail
        number.last_synced_at = utcnow()
        number.updated_by = actor.id
        number.row_version += 1
        await self._numbers.flush()
        await self._audit.record(
            AuditAction.PHONE_NUMBER_REFRESHED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="phone_number",
            entity_id=number.id,
            after={"quality_rating": signal.quality_rating, "tier": signal.messaging_tier},
        )
        await self._session.commit()
        return number
