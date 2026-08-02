"""Tenant-scoped persistence for the CORE-02 Vi domain."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from app.models.vi_domain import (
    EligibilityCheck,
    KycDecision,
    ReactivationCase,
    ReactivationStageEvent,
    SimOrderEvent,
    SlaEvent,
    SlaPolicy,
)
from app.repositories.base import BaseRepository


class ViDomainRepository(BaseRepository[ReactivationCase]):
    """One repository boundary for related aggregates and immutable histories."""

    model = ReactivationCase

    async def by_uuid(self, model: Any, organization_id: int, public_id: bytes) -> Any | None:
        clauses: list[Any] = [model.organization_id == organization_id, model.uuid == public_id]
        if hasattr(model, "deleted_at"):
            clauses.append(model.deleted_at.is_(None))
        return (await self.session.scalars(select(model).where(*clauses))).first()

    async def by_idempotency(self, model: Any, organization_id: int, key: bytes) -> Any | None:
        return (
            await self.session.scalars(
                select(model).where(
                    model.organization_id == organization_id, model.idempotency_key == key
                )
            )
        ).first()

    async def list_aggregates(
        self,
        model: Any,
        organization_id: int,
        *,
        contact_id: int | None = None,
        parent_column: Any | None = None,
        parent_id: int | None = None,
        limit: int = 100,
    ) -> tuple[list[Any], int]:
        clauses: list[Any] = [model.organization_id == organization_id]
        if hasattr(model, "deleted_at"):
            clauses.append(model.deleted_at.is_(None))
        if contact_id is not None and hasattr(model, "contact_id"):
            clauses.append(model.contact_id == contact_id)
        if parent_column is not None and parent_id is not None:
            clauses.append(parent_column == parent_id)
        rows = list(
            (
                await self.session.scalars(
                    select(model)
                    .where(*clauses)
                    .order_by(model.updated_at.desc(), model.id.desc())
                    .limit(limit)
                )
            ).all()
        )
        total = int(
            (await self.session.scalar(select(func.count()).select_from(model).where(*clauses)))
            or 0
        )
        return rows, total

    async def reactivation_for_contact(
        self, organization_id: int, contact_id: int
    ) -> ReactivationCase | None:
        return (
            await self.session.scalars(
                select(ReactivationCase).where(
                    ReactivationCase.organization_id == organization_id,
                    ReactivationCase.contact_id == contact_id,
                    ReactivationCase.deleted_at.is_(None),
                )
            )
        ).first()

    async def child_for_case(self, model: Any, organization_id: int, case_id: int) -> Any | None:
        return (
            await self.session.scalars(
                select(model).where(
                    model.organization_id == organization_id, model.reactivation_case_id == case_id
                )
            )
        ).first()

    async def immutable_by_uuid(
        self, model: Any, organization_id: int, public_id: bytes
    ) -> Any | None:
        return (
            await self.session.scalars(
                select(model).where(
                    model.organization_id == organization_id, model.uuid == public_id
                )
            )
        ).first()

    async def immutable_by_idempotency(
        self, model: Any, organization_id: int, key: bytes
    ) -> Any | None:
        return (
            await self.session.scalars(
                select(model).where(
                    model.organization_id == organization_id, model.idempotency_key == key
                )
            )
        ).first()

    async def stage_events(self, case_id: int) -> list[ReactivationStageEvent]:
        return list(
            (
                await self.session.scalars(
                    select(ReactivationStageEvent)
                    .where(ReactivationStageEvent.case_id == case_id)
                    .order_by(ReactivationStageEvent.created_at, ReactivationStageEvent.id)
                )
            ).all()
        )

    async def eligibility_checks(self, case_id: int) -> list[EligibilityCheck]:
        return list(
            (
                await self.session.scalars(
                    select(EligibilityCheck)
                    .where(EligibilityCheck.case_id == case_id)
                    .order_by(EligibilityCheck.created_at, EligibilityCheck.id)
                )
            ).all()
        )

    async def kyc_decisions(self, kyc_case_id: int) -> list[KycDecision]:
        return list(
            (
                await self.session.scalars(
                    select(KycDecision)
                    .where(KycDecision.kyc_case_id == kyc_case_id)
                    .order_by(KycDecision.created_at, KycDecision.id)
                )
            ).all()
        )

    async def sim_events(self, sim_order_id: int) -> list[SimOrderEvent]:
        return list(
            (
                await self.session.scalars(
                    select(SimOrderEvent)
                    .where(SimOrderEvent.sim_order_id == sim_order_id)
                    .order_by(SimOrderEvent.created_at, SimOrderEvent.id)
                )
            ).all()
        )

    async def list_sla_events(
        self, organization_id: int, *, limit: int
    ) -> tuple[list[SlaEvent], int]:
        clauses = [SlaEvent.organization_id == organization_id]
        rows = list(
            (
                await self.session.scalars(
                    select(SlaEvent)
                    .where(*clauses)
                    .order_by(SlaEvent.created_at.desc(), SlaEvent.id.desc())
                    .limit(limit)
                )
            ).all()
        )
        total = int(
            (await self.session.scalar(select(func.count()).select_from(SlaEvent).where(*clauses)))
            or 0
        )
        return rows, total

    async def list_sla_policies(
        self, organization_id: int, *, limit: int
    ) -> tuple[list[SlaPolicy], int]:
        clauses = [SlaPolicy.organization_id == organization_id]
        rows = list(
            (
                await self.session.scalars(
                    select(SlaPolicy)
                    .where(*clauses)
                    .order_by(SlaPolicy.updated_at.desc(), SlaPolicy.id.desc())
                    .limit(limit)
                )
            ).all()
        )
        total = int(
            (await self.session.scalar(select(func.count()).select_from(SlaPolicy).where(*clauses)))
            or 0
        )
        return rows, total
