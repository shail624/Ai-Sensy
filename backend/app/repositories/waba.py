"""WABA & phone-number repositories (Doc 03 §5.1/§5.2)."""

from __future__ import annotations

from sqlalchemy import func, select, update

from app.models.waba import PhoneNumber, WhatsAppBusinessAccount
from app.repositories.base import BaseRepository


class WabaRepository(BaseRepository[WhatsAppBusinessAccount]):
    model = WhatsAppBusinessAccount

    async def list_for_org(self, organization_id: int) -> list[WhatsAppBusinessAccount]:
        stmt = (
            select(WhatsAppBusinessAccount)
            .where(
                WhatsAppBusinessAccount.organization_id == organization_id,
                WhatsAppBusinessAccount.deleted_at.is_(None),
            )
            .order_by(WhatsAppBusinessAccount.business_name)
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_active_by_uuid(
        self, organization_id: int, public_id: bytes
    ) -> WhatsAppBusinessAccount | None:
        stmt = select(WhatsAppBusinessAccount).where(
            WhatsAppBusinessAccount.organization_id == organization_id,
            WhatsAppBusinessAccount.uuid == public_id,
            WhatsAppBusinessAccount.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def meta_id_exists(self, waba_id: str) -> bool:
        """``uq_waba_metaid`` is global (Doc 03 §5.1) — a WABA cannot be connected twice (409).

        Soft-deleted rows still hold the unique key, so this deliberately ignores ``deleted_at``.
        """
        stmt = select(WhatsAppBusinessAccount.id).where(
            WhatsAppBusinessAccount.waba_id == waba_id
        )
        return (await self.session.scalars(stmt)).first() is not None

    async def count_numbers(self, waba_pk: int) -> int:
        """Live numbers under a WABA — disconnecting one that still has numbers is a 409."""
        stmt = (
            select(func.count())
            .select_from(PhoneNumber)
            .where(PhoneNumber.waba_id == waba_pk, PhoneNumber.deleted_at.is_(None))
        )
        return int((await self.session.scalar(stmt)) or 0)


class PhoneNumberRepository(BaseRepository[PhoneNumber]):
    model = PhoneNumber

    def _filters(
        self,
        organization_id: int,
        *,
        waba_pk: int | None = None,
        status: str | None = None,
        quality_rating: str | None = None,
    ) -> list:
        clauses = [
            PhoneNumber.organization_id == organization_id,
            PhoneNumber.deleted_at.is_(None),
        ]
        if waba_pk is not None:
            clauses.append(PhoneNumber.waba_id == waba_pk)
        if status:
            clauses.append(PhoneNumber.status == status)
        if quality_rating:
            clauses.append(PhoneNumber.quality_rating == quality_rating)
        return clauses

    async def list_for_org(
        self,
        organization_id: int,
        *,
        waba_pk: int | None = None,
        status: str | None = None,
        quality_rating: str | None = None,
    ) -> list[PhoneNumber]:
        stmt = (
            select(PhoneNumber)
            .where(*self._filters(
                organization_id, waba_pk=waba_pk, status=status, quality_rating=quality_rating
            ))
            .order_by(PhoneNumber.display_number)
        )
        return list((await self.session.scalars(stmt)).all())

    async def list_for_waba(self, waba_pk: int) -> list[PhoneNumber]:
        stmt = select(PhoneNumber).where(
            PhoneNumber.waba_id == waba_pk, PhoneNumber.deleted_at.is_(None)
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_active_by_uuid(
        self, organization_id: int, public_id: bytes
    ) -> PhoneNumber | None:
        stmt = select(PhoneNumber).where(
            PhoneNumber.organization_id == organization_id,
            PhoneNumber.uuid == public_id,
            PhoneNumber.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def get_by_meta_id(self, phone_number_id: str) -> PhoneNumber | None:
        """Lookup by Meta's id — the sync reconciliation key (and, later, webhook routing)."""
        stmt = select(PhoneNumber).where(PhoneNumber.phone_number_id == phone_number_id)
        return (await self.session.scalars(stmt)).first()

    async def clear_default(self, organization_id: int, *, except_pk: int) -> None:
        """Only one number may be the org default; promoting one demotes the rest."""
        await self.session.execute(
            update(PhoneNumber)
            .where(
                PhoneNumber.organization_id == organization_id,
                PhoneNumber.id != except_pk,
                PhoneNumber.is_default.is_(True),
            )
            .values(is_default=False)
        )
        await self.session.flush()
