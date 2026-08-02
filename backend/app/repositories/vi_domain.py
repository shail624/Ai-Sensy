"""Tenant-scoped persistence for the CORE-02 Vi domain."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, cast

from sqlalchemy import and_, case, func, or_, select

from app.db.mixins import utcnow
from app.models.contact import Contact
from app.models.contact_document import DOCUMENT_STATUS_VERIFIED, ContactDocument
from app.models.task import TASK_STATUS_OPEN, Task
from app.models.user import User
from app.models.vi_domain import (
    EligibilityCheck,
    KycCase,
    KycDecision,
    KycDocumentReference,
    ReactivationCase,
    ReactivationCaseLabel,
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
        labels: list[str] | None,
        owner_user_id: int | None,
        reminder_view: str | None,
        reminder_date: date | None,
        limit: int,
    ) -> tuple[list[tuple[ReactivationCase, Contact, User | None]], int]:
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
        if labels:
            clauses.append(
                select(ReactivationCaseLabel.id)
                .where(
                    ReactivationCaseLabel.organization_id == organization_id,
                    ReactivationCaseLabel.case_id == ReactivationCase.id,
                    ReactivationCaseLabel.label.in_(labels),
                )
                .exists()
            )
        if owner_user_id is not None:
            clauses.append(ReactivationCase.owner_user_id == owner_user_id)
        if reminder_view is not None or reminder_date is not None:
            reminder = [
                Task.organization_id == organization_id,
                Task.reference_type == "reactivation_case",
                Task.reference_id == ReactivationCase.id,
                Task.status == TASK_STATUS_OPEN,
                Task.deleted_at.is_(None),
            ]
            now = utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            if reminder_view == "overdue":
                reminder.append(Task.due_at < today_start)
            elif reminder_view == "due_today":
                reminder.extend((Task.due_at >= today_start, Task.due_at < today_end))
            elif reminder_view == "upcoming":
                reminder.append(Task.due_at >= today_end)
            if reminder_date is not None:
                reminder.append(func.date(Task.due_at) == reminder_date.isoformat())
            clauses.append(select(Task.id).where(*reminder).exists())

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
        return cast(list[tuple[ReactivationCase, Contact, User | None]], rows), total

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

    async def pipeline_reminder_counts(self, organization_id: int) -> dict[str, int]:
        now = utcnow()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        base = (
            Task.organization_id == organization_id,
            Task.reference_type == "reactivation_case",
            Task.status == TASK_STATUS_OPEN,
            Task.deleted_at.is_(None),
        )
        row = (
            await self.session.execute(
                select(
                    func.sum(case((Task.due_at < start, 1), else_=0)),
                    func.sum(case((and_(Task.due_at >= start, Task.due_at < end), 1), else_=0)),
                    func.sum(case((Task.due_at >= end, 1), else_=0)),
                ).where(*base)
            )
        ).one()
        return {
            "overdue": int(row[0] or 0),
            "due_today": int(row[1] or 0),
            "upcoming": int(row[2] or 0),
        }

    async def kyc_operations(
        self,
        organization_id: int,
        *,
        q: str | None,
        statuses: list[str] | None,
        limit: int,
    ) -> tuple[list[tuple[KycCase, ReactivationCase, Contact, User | None]], int]:
        clauses: list[Any] = [
            KycCase.organization_id == organization_id,
            Contact.organization_id == organization_id,
            Contact.deleted_at.is_(None),
            ReactivationCase.organization_id == organization_id,
            ReactivationCase.deleted_at.is_(None),
        ]
        if statuses:
            clauses.append(KycCase.status.in_(statuses))
        if q:
            text = q.strip()
            like = f"%{text.lower()}%"
            clauses.append(
                or_(
                    func.lower(Contact.full_name).like(like),
                    func.lower(Contact.profile_name).like(like),
                    func.lower(Contact.email).like(like),
                    Contact.phone_e164.like(f"%{text}%"),
                )
            )
        base = (
            select(KycCase, ReactivationCase, Contact, User)
            .join(ReactivationCase, ReactivationCase.id == KycCase.reactivation_case_id)
            .join(Contact, Contact.id == KycCase.contact_id)
            .outerjoin(User, User.id == KycCase.owner_user_id)
            .where(*clauses)
        )
        rows = list(
            (
                await self.session.execute(
                    base.order_by(KycCase.updated_at.desc(), KycCase.id.desc()).limit(limit)
                )
            )
            .tuples()
            .all()
        )
        total = int(
            (
                await self.session.scalar(
                    select(func.count())
                    .select_from(KycCase)
                    .join(ReactivationCase, ReactivationCase.id == KycCase.reactivation_case_id)
                    .join(Contact, Contact.id == KycCase.contact_id)
                    .where(*clauses)
                )
            )
            or 0
        )
        return cast(list[tuple[KycCase, ReactivationCase, Contact, User | None]], rows), total

    async def kyc_operations_evidence(
        self, organization_id: int, kyc_ids: list[int]
    ) -> dict[str, dict[int, Any]]:
        result: dict[str, dict[int, Any]] = {
            "documents": {},
            "decisions": {},
            "appointments": {},
            "sla": {},
        }
        if not kyc_ids:
            return result
        document_rows = (
            (
                await self.session.execute(
                    select(KycDocumentReference, ContactDocument)
                    .join(ContactDocument, ContactDocument.id == KycDocumentReference.document_id)
                    .where(
                        KycDocumentReference.organization_id == organization_id,
                        KycDocumentReference.kyc_case_id.in_(kyc_ids),
                        ContactDocument.organization_id == organization_id,
                        ContactDocument.deleted_at.is_(None),
                    )
                    .order_by(KycDocumentReference.kyc_case_id, KycDocumentReference.purpose)
                )
            )
            .tuples()
            .all()
        )
        for reference, document in document_rows:
            result["documents"].setdefault(reference.kyc_case_id, []).append((reference, document))
        decisions = list(
            (
                await self.session.scalars(
                    select(KycDecision)
                    .where(
                        KycDecision.organization_id == organization_id,
                        KycDecision.kyc_case_id.in_(kyc_ids),
                    )
                    .order_by(KycDecision.kyc_case_id, KycDecision.created_at, KycDecision.id)
                )
            ).all()
        )
        for decision in decisions:
            result["decisions"].setdefault(decision.kyc_case_id, []).append(decision)
        appointments = list(
            (
                await self.session.scalars(
                    select(Task)
                    .where(
                        Task.organization_id == organization_id,
                        Task.reference_type == "kyc_case",
                        Task.reference_id.in_(kyc_ids),
                        Task.deleted_at.is_(None),
                    )
                    .order_by(Task.reference_id, Task.due_at.desc(), Task.id.desc())
                )
            ).all()
        )
        for task in appointments:
            if task.reference_id is None:
                continue
            result["appointments"].setdefault(task.reference_id, []).append(task)
        sla_rows = list(
            (
                await self.session.scalars(
                    select(SlaEvent)
                    .where(
                        SlaEvent.organization_id == organization_id,
                        SlaEvent.entity_type == "kyc_case",
                        SlaEvent.entity_id.in_(kyc_ids),
                    )
                    .order_by(SlaEvent.entity_id, SlaEvent.created_at.desc(), SlaEvent.id.desc())
                )
            ).all()
        )
        for event in sla_rows:
            result["sla"].setdefault(event.entity_id, event)
        return result

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
            "labels": {},
            "reminders": {},
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

        label_rows = list(
            (
                await self.session.scalars(
                    select(ReactivationCaseLabel)
                    .where(
                        ReactivationCaseLabel.organization_id == organization_id,
                        ReactivationCaseLabel.case_id.in_(case_ids),
                    )
                    .order_by(ReactivationCaseLabel.case_id, ReactivationCaseLabel.id)
                )
            ).all()
        )
        for label in label_rows:
            result["labels"].setdefault(label.case_id, []).append(label.label)

        reminder_rows = list(
            (
                await self.session.scalars(
                    select(Task)
                    .where(
                        Task.organization_id == organization_id,
                        Task.reference_type == "reactivation_case",
                        Task.reference_id.in_(case_ids),
                        Task.status == TASK_STATUS_OPEN,
                        Task.deleted_at.is_(None),
                    )
                    .order_by(Task.reference_id, Task.due_at, Task.id)
                )
            ).all()
        )
        for reminder in reminder_rows:
            if reminder.reference_id is not None:
                result["reminders"].setdefault(reminder.reference_id, []).append(reminder)

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

    async def case_labels(self, organization_id: int, case_id: int) -> list[ReactivationCaseLabel]:
        return list(
            (
                await self.session.scalars(
                    select(ReactivationCaseLabel)
                    .where(
                        ReactivationCaseLabel.organization_id == organization_id,
                        ReactivationCaseLabel.case_id == case_id,
                    )
                    .order_by(ReactivationCaseLabel.id)
                )
            ).all()
        )

    async def case_reminders(self, organization_id: int, case_id: int) -> list[Task]:
        return list(
            (
                await self.session.scalars(
                    select(Task)
                    .where(
                        Task.organization_id == organization_id,
                        Task.reference_type == "reactivation_case",
                        Task.reference_id == case_id,
                        Task.status == TASK_STATUS_OPEN,
                        Task.deleted_at.is_(None),
                    )
                    .order_by(Task.due_at, Task.id)
                )
            ).all()
        )

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

    async def kyc_document_references(
        self, organization_id: int, kyc_case_id: int
    ) -> list[tuple[KycDocumentReference, ContactDocument]]:
        return list(
            (
                await self.session.execute(
                    select(KycDocumentReference, ContactDocument)
                    .join(ContactDocument, ContactDocument.id == KycDocumentReference.document_id)
                    .where(
                        KycDocumentReference.organization_id == organization_id,
                        KycDocumentReference.kyc_case_id == kyc_case_id,
                        ContactDocument.organization_id == organization_id,
                        ContactDocument.deleted_at.is_(None),
                    )
                    .order_by(KycDocumentReference.purpose)
                )
            )
            .tuples()
            .all()
        )

    async def kyc_document_reference(
        self, organization_id: int, kyc_case_id: int, purpose: str
    ) -> KycDocumentReference | None:
        return (
            await self.session.scalars(
                select(KycDocumentReference).where(
                    KycDocumentReference.organization_id == organization_id,
                    KycDocumentReference.kyc_case_id == kyc_case_id,
                    KycDocumentReference.purpose == purpose,
                )
            )
        ).first()

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
