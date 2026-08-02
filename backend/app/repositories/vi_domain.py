"""Tenant-scoped persistence for the CORE-02 Vi domain."""

from __future__ import annotations

from typing import Any

from sqlalchemy import case, func, or_, select

from app.db.mixins import utcnow
from app.models.contact import Contact
from app.models.contact_document import DOCUMENT_STATUS_VERIFIED, ContactDocument
from app.models.task import TASK_STATUS_OPEN, Task
from app.models.user import User
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

    async def pipeline_cases(
        self,
        organization_id: int,
        *,
        q: str | None,
        stages: list[str] | None,
        owner_user_id: int | None,
        limit: int,
    ) -> tuple[list[tuple[ReactivationCase, Contact, User]], int]:
        """Bounded joined cards for the governed Reactivation workspace."""
        clauses: list[Any] = [
            ReactivationCase.organization_id == organization_id,
            ReactivationCase.deleted_at.is_(None),
            Contact.organization_id == organization_id,
            Contact.deleted_at.is_(None),
        ]
        if q:
            text = q.strip().lower()
            like = f"%{text}%"
            clauses.append(
                or_(
                    func.lower(Contact.full_name).like(like),
                    func.lower(Contact.email).like(like),
                    Contact.phone_e164.like(f"%{q.strip()}%"),
                    Contact.wa_id.like(f"%{q.strip()}%"),
                    ReactivationCase.previous_vi_number.like(f"%{q.strip()}%"),
                    ReactivationCase.active_delhi_number.like(f"%{q.strip()}%"),
                )
            )
        if stages:
            clauses.append(ReactivationCase.stage.in_(stages))
        if owner_user_id is not None:
            clauses.append(ReactivationCase.owner_user_id == owner_user_id)

        base = (
            select(ReactivationCase, Contact, User)
            .join(Contact, Contact.id == ReactivationCase.contact_id)
            .outerjoin(User, User.id == ReactivationCase.owner_user_id)
            .where(*clauses)
        )
        rows = list(
            (
                await self.session.execute(
                    base.order_by(
                        ReactivationCase.updated_at.desc(), ReactivationCase.id.desc()
                    ).limit(limit)
                )
            )
            .tuples()
            .all()
        )
        total = int(
            (
                await self.session.scalar(
                    select(func.count())
                    .select_from(ReactivationCase)
                    .join(Contact, Contact.id == ReactivationCase.contact_id)
                    .where(*clauses)
                )
            )
            or 0
        )
        return rows, total

    async def pipeline_stage_counts(self, organization_id: int) -> dict[str, int]:
        rows = (
            await self.session.execute(
                select(ReactivationCase.stage, func.count())
                .where(
                    ReactivationCase.organization_id == organization_id,
                    ReactivationCase.deleted_at.is_(None),
                )
                .group_by(ReactivationCase.stage)
            )
        ).all()
        return {str(stage): int(count) for stage, count in rows}

    async def latest_pipeline_evidence(
        self, organization_id: int, case_ids: list[int], contact_ids: list[int]
    ) -> dict[str, dict[int, Any]]:
        """Resolve card evidence in bounded batched queries, never per-card N+1 calls."""
        result: dict[str, dict[int, Any]] = {
            "eligibility": {},
            "stage_event": {},
            "sla": {},
            "tasks": {},
            "documents": {},
        }
        if not case_ids:
            return result

        eligibility_rows = list(
            (
                await self.session.scalars(
                    select(EligibilityCheck)
                    .where(
                        EligibilityCheck.organization_id == organization_id,
                        EligibilityCheck.case_id.in_(case_ids),
                    )
                    .order_by(
                        EligibilityCheck.case_id,
                        EligibilityCheck.created_at.desc(),
                        EligibilityCheck.id.desc(),
                    )
                )
            ).all()
        )
        for eligibility in eligibility_rows:
            result["eligibility"].setdefault(eligibility.case_id, eligibility)

        stage_rows = list(
            (
                await self.session.scalars(
                    select(ReactivationStageEvent)
                    .where(
                        ReactivationStageEvent.organization_id == organization_id,
                        ReactivationStageEvent.case_id.in_(case_ids),
                    )
                    .order_by(
                        ReactivationStageEvent.case_id,
                        ReactivationStageEvent.created_at.desc(),
                        ReactivationStageEvent.id.desc(),
                    )
                )
            ).all()
        )
        for stage_event in stage_rows:
            result["stage_event"].setdefault(stage_event.case_id, stage_event)

        sla_rows = list(
            (
                await self.session.scalars(
                    select(SlaEvent)
                    .where(
                        SlaEvent.entity_type == "reactivation_case",
                        SlaEvent.organization_id == organization_id,
                        SlaEvent.entity_id.in_(case_ids),
                    )
                    .order_by(SlaEvent.entity_id, SlaEvent.created_at.desc(), SlaEvent.id.desc())
                )
            ).all()
        )
        for sla_event in sla_rows:
            result["sla"].setdefault(sla_event.entity_id, sla_event)

        task_rows = (
            await self.session.execute(
                select(
                    Task.contact_id,
                    func.count(),
                    func.sum(case((Task.due_at < utcnow(), 1), else_=0)),
                    func.min(Task.due_at),
                )
                .where(
                    Task.contact_id.in_(contact_ids),
                    Task.organization_id == organization_id,
                    Task.status == TASK_STATUS_OPEN,
                    Task.deleted_at.is_(None),
                )
                .group_by(Task.contact_id)
            )
        ).all()
        result["tasks"] = {
            int(contact_id): {
                "open": int(open_count),
                "overdue": int(overdue_count or 0),
                "next_due_at": next_due_at,
            }
            for contact_id, open_count, overdue_count, next_due_at in task_rows
        }

        document_rows = (
            await self.session.execute(
                select(
                    ContactDocument.contact_id,
                    func.count(),
                    func.sum(
                        case((ContactDocument.status == DOCUMENT_STATUS_VERIFIED, 1), else_=0)
                    ),
                )
                .where(
                    ContactDocument.contact_id.in_(contact_ids),
                    ContactDocument.organization_id == organization_id,
                    ContactDocument.deleted_at.is_(None),
                )
                .group_by(ContactDocument.contact_id)
            )
        ).all()
        result["documents"] = {
            int(contact_id): {"total": int(total), "verified": int(verified or 0)}
            for contact_id, total, verified in document_rows
        }
        return result

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
