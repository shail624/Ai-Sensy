"""Campaign registry repositories (Doc 03 §8.1/§8.3)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, or_, select

from app.models.campaign import (
    RECIPIENT_PENDING,
    RECIPIENT_QUEUED,
    Campaign,
    CampaignBatch,
    CampaignRecipient,
)
from app.models.contact import Contact
from app.repositories.base import BaseRepository


class CampaignRepository(BaseRepository[Campaign]):
    model = Campaign

    async def list_for_org(
        self, organization_id: int, *, status: str | None = None, q: str | None = None
    ) -> list[Campaign]:
        clauses = [Campaign.organization_id == organization_id, Campaign.deleted_at.is_(None)]
        if status:
            clauses.append(Campaign.status == status)
        if q:
            clauses.append(Campaign.name.like(f"%{q}%"))
        stmt = select(Campaign).where(*clauses).order_by(Campaign.created_at.desc())
        return list((await self.session.scalars(stmt)).all())

    async def get_active_by_uuid(
        self, organization_id: int, public_id: bytes
    ) -> Campaign | None:
        stmt = select(Campaign).where(
            Campaign.organization_id == organization_id,
            Campaign.uuid == public_id,
            Campaign.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()


class CampaignRecipientRepository(BaseRepository[CampaignRecipient]):
    model = CampaignRecipient

    async def add_many(self, recipients: list[CampaignRecipient]) -> None:
        self.session.add_all(recipients)
        await self.session.flush()

    async def delete_for_campaign(self, campaign_pk: int) -> int:
        """Drop a draft's roster so it can be re-materialized from a changed audience.

        Hard delete, unlike everywhere else: an unsent roster is a derived list, not a record of
        anything that happened. Only ever called while the campaign is still a draft.
        """
        rows = list(
            (
                await self.session.scalars(
                    select(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign_pk)
                )
            ).all()
        )
        for row in rows:
            await self.session.delete(row)
        await self.session.flush()
        return len(rows)

    async def count_for_campaign(self, campaign_pk: int, *, status: str | None = None) -> int:
        clauses = [CampaignRecipient.campaign_id == campaign_pk]
        if status:
            clauses.append(CampaignRecipient.status == status)
        stmt = select(func.count()).select_from(CampaignRecipient).where(*clauses)
        return int((await self.session.scalar(stmt)) or 0)

    async def paginate(
        self,
        campaign_pk: int,
        *,
        status: str | None = None,
        limit: int,
        cursor: tuple[datetime, int] | None,
    ) -> tuple[list[CampaignRecipient], bool]:
        """Keyset page over the roster, newest first — the 100M+ table is never offset-paged."""
        clauses = [CampaignRecipient.campaign_id == campaign_pk]
        if status:
            clauses.append(CampaignRecipient.status == status)
        if cursor is not None:
            c_created, c_id = cursor
            clauses.append(
                or_(
                    CampaignRecipient.created_at < c_created,
                    and_(
                        CampaignRecipient.created_at == c_created, CampaignRecipient.id < c_id
                    ),
                )
            )
        stmt = (
            select(CampaignRecipient)
            .where(*clauses)
            .order_by(CampaignRecipient.created_at.desc(), CampaignRecipient.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self.session.scalars(stmt)).all())
        return rows[:limit], len(rows) > limit

    async def list_unsent(self, campaign_pk: int) -> list[CampaignRecipient]:
        """Recipients that still owe a send — what a resumed dispatch picks up (FR-CAM-09)."""
        stmt = (
            select(CampaignRecipient)
            .where(
                CampaignRecipient.campaign_id == campaign_pk,
                CampaignRecipient.status == RECIPIENT_PENDING,
            )
            .order_by(CampaignRecipient.id)
        )
        return list((await self.session.scalars(stmt)).all())

    async def list_for_batch(self, batch_pk: int) -> list[CampaignRecipient]:
        stmt = (
            select(CampaignRecipient)
            .where(
                CampaignRecipient.batch_id == batch_pk,
                CampaignRecipient.status == RECIPIENT_PENDING,
            )
            .order_by(CampaignRecipient.id)
        )
        return list((await self.session.scalars(stmt)).all())

    async def count_unsettled(self, campaign_pk: int, batch_pk: int) -> int:
        """How many of a batch's recipients have not reached a terminal state yet."""
        stmt = (
            select(func.count())
            .select_from(CampaignRecipient)
            .where(
                CampaignRecipient.campaign_id == campaign_pk,
                CampaignRecipient.batch_id == batch_pk,
                CampaignRecipient.status.in_((RECIPIENT_PENDING, RECIPIENT_QUEUED)),
            )
        )
        return int((await self.session.scalar(stmt)) or 0)

    async def counts_by_status(self, campaign_pk: int) -> dict[str, int]:
        """The roster's live shape — the authoritative source the counters mirror (Doc 03 §8.1)."""
        stmt = (
            select(CampaignRecipient.status, func.count())
            .where(CampaignRecipient.campaign_id == campaign_pk)
            .group_by(CampaignRecipient.status)
        )
        return {status: int(count) for status, count in await self.session.execute(stmt)}

    async def contacts_for(
        self, campaign_pk: int, recipients: list[CampaignRecipient]
    ) -> dict[int, Contact]:
        """The contacts behind a page of recipients, in one query (no N+1 on the roster)."""
        ids = [r.contact_id for r in recipients]
        if not ids:
            return {}
        stmt = select(Contact).where(Contact.id.in_(ids))
        return {c.id: c for c in (await self.session.scalars(stmt)).all()}


class CampaignBatchRepository(BaseRepository[CampaignBatch]):
    model = CampaignBatch

    async def list_for_campaign(self, campaign_pk: int) -> list[CampaignBatch]:
        stmt = (
            select(CampaignBatch)
            .where(CampaignBatch.campaign_id == campaign_pk)
            .order_by(CampaignBatch.batch_index)
        )
        return list((await self.session.scalars(stmt)).all())
