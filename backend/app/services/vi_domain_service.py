"""CORE-02 Vi domain commands, transition rules, audit and timeline projections."""

from __future__ import annotations

import hashlib
import json
import uuid as uuidlib
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError, VersionConflictError
from app.db.mixins import utcnow
from app.models.business_event import (
    BUSINESS_EVENT_ACTIVATION_TRANSITIONED,
    BUSINESS_EVENT_ELIGIBILITY_DECIDED,
    BUSINESS_EVENT_KYC_DECIDED,
    BUSINESS_EVENT_REACTIVATION_CREATED,
    BUSINESS_EVENT_REACTIVATION_TRANSITIONED,
    BUSINESS_EVENT_SIM_TRANSITIONED,
    BUSINESS_EVENT_SLA_RECORDED,
)
from app.models.contact import Contact
from app.models.contact_document import DOCUMENT_STATUS_VERIFIED, ContactDocument
from app.models.contact_event import (
    EVENT_ACTIVATION_UPDATED,
    EVENT_ELIGIBILITY_RECORDED,
    EVENT_KYC_DECIDED,
    EVENT_KYC_UPDATED,
    EVENT_REACTIVATION_CREATED,
    EVENT_REACTIVATION_NOTE_ADDED,
    EVENT_REACTIVATION_TRANSITIONED,
    EVENT_SIM_ORDER_UPDATED,
    EVENT_SLA_RECORDED,
    REF_TYPE_ACTIVATION_RECORD,
    REF_TYPE_KYC_CASE,
    REF_TYPE_REACTIVATION_CASE,
    REF_TYPE_SIM_ORDER,
    REF_TYPE_SLA_EVENT,
)
from app.models.user import User
from app.models.vi_domain import (
    ACTIVATION_TRANSITIONS,
    KYC_DECISIONS,
    KYC_PREPARATION_TRANSITIONS,
    REACTIVATION_STAGES,
    REACTIVATION_TRANSITIONS,
    SIM_ORDER_TRANSITIONS,
    ActivationRecord,
    EligibilityCheck,
    KycCase,
    KycDecision,
    ReactivationCase,
    ReactivationStageEvent,
    SimOrder,
    SimOrderEvent,
    SlaEvent,
    SlaPolicy,
)
from app.repositories.contact import ContactRepository
from app.repositories.vi_domain import ViDomainRepository
from app.schemas.attribute import attributes_map
from app.services.audit_service import AuditAction, AuditService
from app.services.business_event_service import BusinessEventService
from app.services.contact_event_service import ContactEventService


class DomainTransitionError(ConflictError):
    code = "invalid_domain_transition"
    title = "Invalid Domain Transition"


class IdempotencyConflictError(ConflictError):
    code = "idempotency_conflict"
    title = "Idempotency Conflict"


class ViDomainService:
    """Single transactional boundary for the related Vi lifecycle aggregates."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ViDomainRepository(session)
        self._contacts = ContactRepository(session)
        self._audit = AuditService(session)
        self._timeline = ContactEventService(session)
        self._business_events = BusinessEventService(session)

    async def list_reactivation(
        self, organization_id: int, *, contact_id: uuidlib.UUID | None, limit: int
    ) -> tuple[list[dict[str, Any]], int]:
        internal_contact = None
        if contact_id is not None:
            internal_contact = (await self._require_contact(organization_id, contact_id)).id
        rows, total = await self._repo.list_aggregates(
            ReactivationCase, organization_id, contact_id=internal_contact, limit=limit
        )
        return await self.views(rows), total

    async def reactivation_pipeline(
        self,
        organization_id: int,
        *,
        q: str | None,
        stages: list[str] | None,
        owner_user_id: uuidlib.UUID | None,
        limit: int,
    ) -> dict[str, Any]:
        """One bounded, factual projection for Kanban/list consumers."""
        owner_id = await self._user_id(organization_id, owner_user_id)
        rows, total = await self._repo.pipeline_cases(
            organization_id,
            q=q,
            stages=stages,
            owner_user_id=owner_id,
            limit=limit,
        )
        cases = [row[0] for row in rows]
        evidence = await self._repo.latest_pipeline_evidence(
            organization_id, [case.id for case in cases], [case.contact_id for case in cases]
        )
        cards: list[dict[str, Any]] = []
        now = utcnow()
        for case, contact, owner in rows:
            eligibility = evidence["eligibility"].get(case.id)
            stage_event = evidence["stage_event"].get(case.id)
            sla = evidence["sla"].get(case.id)
            tasks = evidence["tasks"].get(case.contact_id, {})
            documents = evidence["documents"].get(case.contact_id, {})
            attributes = attributes_map(contact.attribute_values)
            sla_status = "not_configured"
            if sla is not None:
                if sla.event_type == "resolved":
                    sla_status = "resolved"
                elif sla.event_type == "breached" or sla.due_at < now:
                    sla_status = "breached"
                else:
                    sla_status = "on_track"
            cards.append(
                {
                    "id": case.public_id,
                    "contact_id": contact.public_id,
                    "stage": case.stage,
                    "owner_user_id": owner.public_id if owner else None,
                    "previous_vi_number": case.previous_vi_number,
                    "active_delhi_number": case.active_delhi_number,
                    "source": case.source,
                    "closed_reason": case.closed_reason,
                    "row_version": case.row_version,
                    "created_at": case.created_at,
                    "updated_at": case.updated_at,
                    "available_transitions": sorted(REACTIVATION_TRANSITIONS[case.stage]),
                    "contact_name": contact.full_name or contact.profile_name or contact.phone_e164,
                    "contact_phone": contact.phone_e164,
                    "contact_email": contact.email,
                    "contact_attributes": attributes,
                    "owner_name": owner.full_name if owner else None,
                    "stage_entered_at": stage_event.created_at if stage_event else case.created_at,
                    "latest_eligibility_status": eligibility.status if eligibility else None,
                    "latest_eligibility_reason": eligibility.reason if eligibility else None,
                    "open_task_count": int(tasks.get("open", 0)),
                    "overdue_task_count": int(tasks.get("overdue", 0)),
                    "next_task_due_at": tasks.get("next_due_at"),
                    "document_count": int(documents.get("total", 0)),
                    "verified_document_count": int(documents.get("verified", 0)),
                    "sla_status": sla_status,
                    "sla_due_at": sla.due_at if sla else None,
                    "reservation_status": self._first_attribute(
                        attributes, "number_reservation_status", "reservation_status"
                    ),
                    "family_plan_required": self._bool_attribute(
                        attributes.get("family_plan_required")
                    ),
                    "family_numbers": self._string_list_attribute(
                        attributes.get("related_family_numbers", attributes.get("family_numbers"))
                    ),
                    "conversion_indicator": (
                        "converted"
                        if case.stage == "completed"
                        else "lost"
                        if case.stage in {"not_eligible", "not_interested"}
                        else "open"
                    ),
                }
            )
        counts = await self._repo.pipeline_stage_counts(organization_id)
        return {
            "data": cards,
            "total": total,
            "visible": len(cards),
            "stage_counts": [
                {"stage": stage, "count": counts.get(stage, 0)} for stage in REACTIVATION_STAGES
            ],
        }

    async def list_reactivation_notes(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> list[dict[str, Any]]:
        case = await self._require(ReactivationCase, organization_id, public_id)
        events = await self._timeline.list_for_reference(
            organization_id,
            contact_id=case.contact_id,
            ref_type=REF_TYPE_REACTIVATION_CASE,
            ref_id=case.id,
            event_type=EVENT_REACTIVATION_NOTE_ADDED,
        )
        return [
            {
                "id": event.id,
                "case_id": public_id,
                "actor_user_id": uuidlib.UUID(str((event.payload_json or {})["actor_user_id"])),
                "body": str((event.payload_json or {})["body"]),
                "created_at": event.created_at,
            }
            for event in events
        ]

    async def add_reactivation_note(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        body: str,
    ) -> dict[str, Any]:
        case = await self._require(ReactivationCase, organization_id, public_id)
        cleaned = body.strip()
        event = await self._timeline.record(
            organization_id=organization_id,
            contact_id=case.contact_id,
            event_type=EVENT_REACTIVATION_NOTE_ADDED,
            ref_type=REF_TYPE_REACTIVATION_CASE,
            ref_id=case.id,
            payload={"actor_user_id": str(actor.public_id), "body": cleaned},
        )
        await self._session.flush()
        await self._audit.record(
            AuditAction.REACTIVATION_NOTE_ADDED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="reactivation_case",
            entity_id=case.id,
            after={"timeline_event_id": event.id, "body": cleaned},
        )
        await self._session.commit()
        return {
            "id": event.id,
            "case_id": public_id,
            "actor_user_id": uuidlib.UUID(str(actor.public_id)),
            "body": cleaned,
            "created_at": event.created_at,
        }

    async def get_reactivation(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> dict[str, Any]:
        return (
            await self.views([await self._require(ReactivationCase, organization_id, public_id)])
        )[0]

    async def create_reactivation(
        self,
        *,
        organization_id: int,
        actor: User,
        contact_id: uuidlib.UUID,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        request_hash = self._hash(payload)
        existing = await self._idempotent(
            ReactivationCase, organization_id, payload["idempotency_key"], request_hash
        )
        if existing is not None:
            return (await self.views([existing]))[0]
        contact = await self._require_contact(organization_id, contact_id)
        if await self._repo.reactivation_for_contact(organization_id, contact.id) is not None:
            raise ConflictError("This contact already has a reactivation case.")
        owner_id = await self._user_id(organization_id, payload.get("owner_user_id"))
        case = ReactivationCase(
            organization_id=organization_id,
            contact_id=contact.id,
            owner_user_id=owner_id,
            previous_vi_number=self._clean(payload.get("previous_vi_number")),
            active_delhi_number=self._clean(payload.get("active_delhi_number")),
            source=payload.get("source", "manual").strip(),
            stage="new_lead",
            idempotency_key=payload["idempotency_key"].bytes,
            request_hash=request_hash,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self._session.add(case)
        await self._session.flush()
        self._session.add(
            ReactivationStageEvent(
                organization_id=organization_id,
                case_id=case.id,
                contact_id=contact.id,
                from_stage=None,
                to_stage="new_lead",
                actor_user_id=actor.id,
                idempotency_key=payload["idempotency_key"].bytes,
                request_hash=request_hash,
            )
        )
        await self._record(
            case,
            actor,
            AuditAction.REACTIVATION_CASE_CREATED,
            EVENT_REACTIVATION_CREATED,
            BUSINESS_EVENT_REACTIVATION_CREATED,
            {"stage": case.stage},
        )
        await self._session.commit()
        return (await self.views([case]))[0]

    async def update_reactivation(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        case = await self._require(ReactivationCase, organization_id, public_id)
        self._check_version(case, payload["expected_row_version"])
        before = {
            "owner_user_id": case.owner_user_id,
            "previous_vi_number": case.previous_vi_number,
            "active_delhi_number": case.active_delhi_number,
        }
        case.owner_user_id = await self._user_id(organization_id, payload.get("owner_user_id"))
        case.previous_vi_number = self._clean(payload.get("previous_vi_number"))
        case.active_delhi_number = self._clean(payload.get("active_delhi_number"))
        self._bump(case, actor.id)
        await self._audit.record(
            AuditAction.REACTIVATION_CASE_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="reactivation_case",
            entity_id=case.id,
            before=before,
            after={
                "owner_user_id": case.owner_user_id,
                "previous_vi_number": case.previous_vi_number,
                "active_delhi_number": case.active_delhi_number,
            },
        )
        await self._session.commit()
        return (await self.views([case]))[0]

    async def transition_reactivation(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        request_hash = self._hash(payload)
        prior = await self._idempotent(
            ReactivationStageEvent, organization_id, payload["idempotency_key"], request_hash
        )
        case = await self._require(ReactivationCase, organization_id, public_id)
        if prior is not None:
            if prior.case_id != case.id:
                raise IdempotencyConflictError("Idempotency key belongs to another case.")
            return (await self.views([case]))[0]
        self._check_version(case, payload["expected_row_version"])
        target = payload["to_stage"]
        if target not in REACTIVATION_TRANSITIONS[case.stage]:
            raise DomainTransitionError(f"Reactivation cannot move from {case.stage} to {target}.")
        await self._validate_reactivation_gate(case, target)
        previous = case.stage
        case.stage = target
        case.closed_reason = (
            self._clean(payload.get("reason"))
            if target in {"not_eligible", "not_interested"}
            else None
        )
        self._bump(case, actor.id)
        event = ReactivationStageEvent(
            organization_id=organization_id,
            case_id=case.id,
            contact_id=case.contact_id,
            from_stage=previous,
            to_stage=target,
            actor_user_id=actor.id,
            reason=self._clean(payload.get("reason")),
            idempotency_key=payload["idempotency_key"].bytes,
            request_hash=request_hash,
        )
        self._session.add(event)
        await self._session.flush()
        await self._record(
            case,
            actor,
            AuditAction.REACTIVATION_STAGE_TRANSITIONED,
            EVENT_REACTIVATION_TRANSITIONED,
            BUSINESS_EVENT_REACTIVATION_TRANSITIONED,
            {"from_stage": previous, "to_stage": target, "reason": event.reason},
            event_id=uuidlib.UUID(bytes=event.uuid),
        )
        await self._session.commit()
        return (await self.views([case]))[0]

    async def stage_events(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> list[dict[str, Any]]:
        case = await self._require(ReactivationCase, organization_id, public_id)
        return await self.views(await self._repo.stage_events(case.id))

    async def list_eligibility(
        self, organization_id: int, case_id: uuidlib.UUID
    ) -> list[dict[str, Any]]:
        case = await self._require(ReactivationCase, organization_id, case_id)
        return await self.views(await self._repo.eligibility_checks(case.id))

    async def get_eligibility(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> dict[str, Any]:
        return (
            await self.views(
                [await self._require_immutable(EligibilityCheck, organization_id, public_id)]
            )
        )[0]

    async def create_eligibility(
        self, *, organization_id: int, actor: User, case_id: uuidlib.UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        request_hash = self._hash(payload)
        existing = await self._idempotent(
            EligibilityCheck, organization_id, payload["idempotency_key"], request_hash
        )
        if existing is not None:
            return (await self.views([existing]))[0]
        case = await self._require(ReactivationCase, organization_id, case_id)
        if case.stage != "eligibility_check":
            raise DomainTransitionError(
                "Eligibility can only be recorded during eligibility_check."
            )
        check = EligibilityCheck(
            organization_id=organization_id,
            case_id=case.id,
            contact_id=case.contact_id,
            status=payload["status"],
            source=payload["source"],
            reason=self._clean(payload.get("reason")),
            approval_reference=self._clean(payload.get("approval_reference")),
            checked_by=actor.id,
            idempotency_key=payload["idempotency_key"].bytes,
            request_hash=request_hash,
        )
        self._session.add(check)
        await self._session.flush()
        await self._record(
            check,
            actor,
            AuditAction.ELIGIBILITY_RECORDED,
            EVENT_ELIGIBILITY_RECORDED,
            BUSINESS_EVENT_ELIGIBILITY_DECIDED,
            {
                "status": check.status,
                "source": check.source,
                "approval_reference": check.approval_reference,
            },
            contact_id=case.contact_id,
            ref_type=REF_TYPE_REACTIVATION_CASE,
            ref_id=case.id,
        )
        await self._session.commit()
        return (await self.views([check]))[0]

    async def list_kyc(
        self, organization_id: int, *, contact_id: uuidlib.UUID | None, limit: int
    ) -> tuple[list[dict[str, Any]], int]:
        internal_contact = (
            (await self._require_contact(organization_id, contact_id)).id if contact_id else None
        )
        rows, total = await self._repo.list_aggregates(
            KycCase, organization_id, contact_id=internal_contact, limit=limit
        )
        return await self.views(rows), total

    async def get_kyc(self, organization_id: int, public_id: uuidlib.UUID) -> dict[str, Any]:
        return (await self.views([await self._require(KycCase, organization_id, public_id)]))[0]

    async def create_kyc(
        self,
        *,
        organization_id: int,
        actor: User,
        reactivation_id: uuidlib.UUID,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        request_hash = self._hash(payload)
        existing = await self._idempotent(
            KycCase, organization_id, payload["idempotency_key"], request_hash
        )
        if existing is not None:
            return (await self.views([existing]))[0]
        case = await self._require(ReactivationCase, organization_id, reactivation_id)
        if case.stage not in {"documents_received", "kyc_pending", "verification"}:
            raise DomainTransitionError("KYC can only begin after documents are received.")
        if await self._repo.child_for_case(KycCase, organization_id, case.id) is not None:
            raise ConflictError("This reactivation case already has a KYC case.")
        kyc = KycCase(
            organization_id=organization_id,
            reactivation_case_id=case.id,
            contact_id=case.contact_id,
            owner_user_id=await self._user_id(organization_id, payload.get("owner_user_id")),
            appointment_at=payload.get("appointment_at"),
            idempotency_key=payload["idempotency_key"].bytes,
            request_hash=request_hash,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self._session.add(kyc)
        await self._session.flush()
        await self._audit_and_timeline(
            kyc,
            actor,
            AuditAction.KYC_CASE_CREATED,
            EVENT_KYC_UPDATED,
            {"status": kyc.status},
            REF_TYPE_KYC_CASE,
        )
        await self._session.commit()
        return (await self.views([kyc]))[0]

    async def update_kyc(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        kyc = await self._require(KycCase, organization_id, public_id)
        self._check_version(kyc, payload["expected_row_version"])
        if kyc.status in {"approved", "rejected"}:
            raise DomainTransitionError("A decided KYC case is immutable.")
        before = self._kyc_state(kyc)
        target_status = payload["status"]
        if (
            target_status != kyc.status
            and target_status not in KYC_PREPARATION_TRANSITIONS[kyc.status]
        ):
            raise DomainTransitionError(
                f"KYC preparation cannot move from {kyc.status} to {target_status}."
            )
        kyc.status = target_status
        kyc.owner_user_id = await self._user_id(organization_id, payload.get("owner_user_id"))
        kyc.holder_verified = payload["holder_verified"]
        kyc.delhi_presence_verified = payload["delhi_presence_verified"]
        kyc.active_delhi_number_verified = payload["active_delhi_number_verified"]
        kyc.appointment_at = payload.get("appointment_at")
        self._bump(kyc, actor.id)
        await self._audit.record(
            AuditAction.KYC_CASE_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="kyc_case",
            entity_id=kyc.id,
            before=before,
            after=self._kyc_state(kyc),
        )
        await self._timeline.record(
            organization_id=organization_id,
            contact_id=kyc.contact_id,
            event_type=EVENT_KYC_UPDATED,
            ref_type=REF_TYPE_KYC_CASE,
            ref_id=kyc.id,
            payload=self._kyc_state(kyc),
        )
        await self._session.commit()
        return (await self.views([kyc]))[0]

    async def list_kyc_decisions(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> list[dict[str, Any]]:
        kyc = await self._require(KycCase, organization_id, public_id)
        return await self.views(await self._repo.kyc_decisions(kyc.id))

    async def get_kyc_decision(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> dict[str, Any]:
        return (
            await self.views(
                [await self._require_immutable(KycDecision, organization_id, public_id)]
            )
        )[0]

    async def decide_kyc(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        payload: dict[str, Any],
        manager_approval: bool,
    ) -> dict[str, Any]:
        request_hash = self._hash({**payload, "manager_approval": manager_approval})
        existing = await self._idempotent(
            KycDecision, organization_id, payload["idempotency_key"], request_hash
        )
        if existing is not None:
            return (await self.views([existing]))[0]
        kyc = await self._require(KycCase, organization_id, public_id)
        self._check_version(kyc, payload["expected_row_version"])
        decision = payload["decision"]
        if decision not in KYC_DECISIONS:
            raise BadRequestError("Unknown KYC decision.")
        prior = await self._repo.kyc_decisions(kyc.id)
        if manager_approval:
            if not any(
                row.decision_type == "review" and row.decision == "approved" for row in prior
            ):
                raise DomainTransitionError(
                    "Manager approval requires an approved review decision."
                )
        elif kyc.status not in {"under_review", "documents_pending"}:
            raise DomainTransitionError("KYC review requires an active review state.")
        if decision == "approved":
            await self._validate_kyc_approval(kyc)
        row = KycDecision(
            organization_id=organization_id,
            kyc_case_id=kyc.id,
            contact_id=kyc.contact_id,
            decision_type="manager_approval" if manager_approval else "review",
            decision=decision,
            reason=self._clean(payload.get("reason")),
            decided_by=actor.id,
            idempotency_key=payload["idempotency_key"].bytes,
            request_hash=request_hash,
        )
        self._session.add(row)
        if manager_approval:
            kyc.status = (
                "approved"
                if decision == "approved"
                else ("rejected" if decision == "rejected" else "documents_pending")
            )
        elif decision != "approved":
            kyc.status = "rejected" if decision == "rejected" else "documents_pending"
        self._bump(kyc, actor.id)
        await self._session.flush()
        await self._record(
            row,
            actor,
            AuditAction.KYC_DECISION_RECORDED,
            EVENT_KYC_DECIDED,
            BUSINESS_EVENT_KYC_DECIDED,
            {
                "decision_type": row.decision_type,
                "decision": row.decision,
                "kyc_status": kyc.status,
            },
            contact_id=kyc.contact_id,
            ref_type=REF_TYPE_KYC_CASE,
            ref_id=kyc.id,
        )
        await self._session.commit()
        return (await self.views([row]))[0]

    async def list_sim_orders(
        self, organization_id: int, *, case_id: uuidlib.UUID | None, limit: int
    ) -> tuple[list[dict[str, Any]], int]:
        parent = (
            await self._require(ReactivationCase, organization_id, case_id) if case_id else None
        )
        rows, total = await self._repo.list_aggregates(
            SimOrder,
            organization_id,
            parent_column=SimOrder.reactivation_case_id if parent else None,
            parent_id=parent.id if parent else None,
            limit=limit,
        )
        return await self.views(rows), total

    async def get_sim_order(self, organization_id: int, public_id: uuidlib.UUID) -> dict[str, Any]:
        return (await self.views([await self._require(SimOrder, organization_id, public_id)]))[0]

    async def create_sim_order(
        self,
        *,
        organization_id: int,
        actor: User,
        reactivation_id: uuidlib.UUID,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        request_hash = self._hash(payload)
        existing = await self._idempotent(
            SimOrder, organization_id, payload["idempotency_key"], request_hash
        )
        if existing is not None:
            return (await self.views([existing]))[0]
        case = await self._require(ReactivationCase, organization_id, reactivation_id)
        if case.stage not in {"confirmed", "sim_order"}:
            raise DomainTransitionError("SIM ordering requires a confirmed reactivation case.")
        if await self._repo.child_for_case(SimOrder, organization_id, case.id) is not None:
            raise ConflictError("This reactivation case already has a SIM order.")
        order = SimOrder(
            organization_id=organization_id,
            reactivation_case_id=case.id,
            contact_id=case.contact_id,
            delivery_address=payload["delivery_address"].strip(),
            service_area=payload["service_area"].strip(),
            delivery_owner_user_id=await self._user_id(
                organization_id, payload.get("delivery_owner_user_id")
            ),
            idempotency_key=payload["idempotency_key"].bytes,
            request_hash=request_hash,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self._session.add(order)
        await self._session.flush()
        self._session.add(
            SimOrderEvent(
                organization_id=organization_id,
                sim_order_id=order.id,
                contact_id=order.contact_id,
                from_status=None,
                to_status="requested",
                actor_user_id=actor.id,
                idempotency_key=payload["idempotency_key"].bytes,
                request_hash=request_hash,
            )
        )
        await self._audit_and_timeline(
            order,
            actor,
            AuditAction.SIM_ORDER_CREATED,
            EVENT_SIM_ORDER_UPDATED,
            {"status": order.status},
            REF_TYPE_SIM_ORDER,
        )
        await self._session.commit()
        return (await self.views([order]))[0]

    async def update_sim_order(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        order = await self._require(SimOrder, organization_id, public_id)
        self._check_version(order, payload["expected_row_version"])
        if order.status == "cancelled":
            raise DomainTransitionError("A terminal SIM order cannot be edited.")
        before = self._sim_state(order)
        order.delivery_address = payload["delivery_address"].strip()
        order.service_area = payload["service_area"].strip()
        order.delivery_owner_user_id = await self._user_id(
            organization_id, payload.get("delivery_owner_user_id")
        )
        order.sim_serial = self._clean(payload.get("sim_serial"))
        order.customer_confirmed = payload["customer_confirmed"]
        self._bump(order, actor.id)
        await self._audit.record(
            AuditAction.SIM_ORDER_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="sim_order",
            entity_id=order.id,
            before=before,
            after=self._sim_state(order),
        )
        await self._timeline.record(
            organization_id=organization_id,
            contact_id=order.contact_id,
            event_type=EVENT_SIM_ORDER_UPDATED,
            ref_type=REF_TYPE_SIM_ORDER,
            ref_id=order.id,
            payload=self._sim_state(order),
        )
        await self._session.commit()
        return (await self.views([order]))[0]

    async def transition_sim_order(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        request_hash = self._hash(payload)
        prior = await self._idempotent(
            SimOrderEvent, organization_id, payload["idempotency_key"], request_hash
        )
        order = await self._require(SimOrder, organization_id, public_id)
        if prior is not None:
            if prior.sim_order_id != order.id:
                raise IdempotencyConflictError("Idempotency key belongs to another SIM order.")
            return (await self.views([order]))[0]
        self._check_version(order, payload["expected_row_version"])
        target = payload["to_status"]
        if target not in SIM_ORDER_TRANSITIONS[order.status]:
            raise DomainTransitionError(f"SIM order cannot move from {order.status} to {target}.")
        if target == "dispatched" and (
            order.delivery_owner_user_id is None or not order.sim_serial
        ):
            raise DomainTransitionError(
                "Dispatch requires an assigned delivery owner and SIM serial."
            )
        previous = order.status
        order.status = target
        now = utcnow()
        if target == "dispatched":
            order.dispatched_at = now
        if target == "delivered":
            order.delivered_at = now
        if target == "failed":
            order.failed_at, order.failure_reason = now, self._clean(payload.get("reason"))
        self._bump(order, actor.id)
        event = SimOrderEvent(
            organization_id=organization_id,
            sim_order_id=order.id,
            contact_id=order.contact_id,
            from_status=previous,
            to_status=target,
            actor_user_id=actor.id,
            reason=self._clean(payload.get("reason")),
            idempotency_key=payload["idempotency_key"].bytes,
            request_hash=request_hash,
        )
        self._session.add(event)
        await self._session.flush()
        await self._record(
            order,
            actor,
            AuditAction.SIM_ORDER_TRANSITIONED,
            EVENT_SIM_ORDER_UPDATED,
            BUSINESS_EVENT_SIM_TRANSITIONED,
            {"from_status": previous, "to_status": target, "reason": event.reason},
            event_id=uuidlib.UUID(bytes=event.uuid),
        )
        await self._session.commit()
        return (await self.views([order]))[0]

    async def sim_events(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> list[dict[str, Any]]:
        order = await self._require(SimOrder, organization_id, public_id)
        return await self.views(await self._repo.sim_events(order.id))

    async def get_sim_event(self, organization_id: int, public_id: uuidlib.UUID) -> dict[str, Any]:
        return (
            await self.views(
                [await self._require_immutable(SimOrderEvent, organization_id, public_id)]
            )
        )[0]

    async def list_activations(
        self, organization_id: int, *, case_id: uuidlib.UUID | None, limit: int
    ) -> tuple[list[dict[str, Any]], int]:
        parent = (
            await self._require(ReactivationCase, organization_id, case_id) if case_id else None
        )
        rows, total = await self._repo.list_aggregates(
            ActivationRecord,
            organization_id,
            parent_column=ActivationRecord.reactivation_case_id if parent else None,
            parent_id=parent.id if parent else None,
            limit=limit,
        )
        return await self.views(rows), total

    async def get_activation(self, organization_id: int, public_id: uuidlib.UUID) -> dict[str, Any]:
        return (
            await self.views([await self._require(ActivationRecord, organization_id, public_id)])
        )[0]

    async def create_activation(
        self,
        *,
        organization_id: int,
        actor: User,
        reactivation_id: uuidlib.UUID,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        request_hash = self._hash(payload)
        existing = await self._idempotent(
            ActivationRecord, organization_id, payload["idempotency_key"], request_hash
        )
        if existing is not None:
            return (await self.views([existing]))[0]
        case = await self._require(ReactivationCase, organization_id, reactivation_id)
        if case.stage not in {"sim_order", "activation_pending"}:
            raise DomainTransitionError("Activation requires a SIM-order stage case.")
        if await self._repo.child_for_case(ActivationRecord, organization_id, case.id) is not None:
            raise ConflictError("This reactivation case already has an activation record.")
        sim = await self._require_optional_sim(
            organization_id, payload.get("sim_order_id"), case.id
        )
        activation = ActivationRecord(
            organization_id=organization_id,
            reactivation_case_id=case.id,
            sim_order_id=sim.id if sim else None,
            contact_id=case.contact_id,
            owner_user_id=await self._user_id(organization_id, payload.get("owner_user_id")),
            idempotency_key=payload["idempotency_key"].bytes,
            request_hash=request_hash,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self._session.add(activation)
        await self._session.flush()
        await self._audit_and_timeline(
            activation,
            actor,
            AuditAction.ACTIVATION_CREATED,
            EVENT_ACTIVATION_UPDATED,
            {"status": activation.status},
            REF_TYPE_ACTIVATION_RECORD,
        )
        await self._session.commit()
        return (await self.views([activation]))[0]

    async def update_activation(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        activation = await self._require(ActivationRecord, organization_id, public_id)
        self._check_version(activation, payload["expected_row_version"])
        if activation.status in {"completed", "rejected"}:
            raise DomainTransitionError("A terminal activation record cannot be edited.")
        before = {
            "owner_user_id": activation.owner_user_id,
            "sim_order_id": activation.sim_order_id,
        }
        activation.owner_user_id = await self._user_id(
            organization_id, payload.get("owner_user_id")
        )
        sim = await self._require_optional_sim(
            organization_id, payload.get("sim_order_id"), activation.reactivation_case_id
        )
        activation.sim_order_id = sim.id if sim else None
        self._bump(activation, actor.id)
        await self._audit.record(
            AuditAction.ACTIVATION_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="activation_record",
            entity_id=activation.id,
            before=before,
            after={
                "owner_user_id": activation.owner_user_id,
                "sim_order_id": activation.sim_order_id,
            },
        )
        await self._session.commit()
        return (await self.views([activation]))[0]

    async def transition_activation(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        payload: dict[str, Any],
        approval_command: bool,
    ) -> dict[str, Any]:
        activation = await self._require(ActivationRecord, organization_id, public_id)
        existing_event = await self._business_events.find_domain_event(
            organization_id, payload["idempotency_key"]
        )
        if existing_event is not None:
            if existing_event.subject_id != activation.id:
                raise IdempotencyConflictError("Idempotency key belongs to another activation.")
            if (existing_event.payload_json or {}).get("request_hash") != self._hash(payload):
                raise IdempotencyConflictError(
                    "Idempotency key was already used with a different command."
                )
            return (await self.views([activation]))[0]
        self._check_version(activation, payload["expected_row_version"])
        target = payload["to_status"]
        if target not in ACTIVATION_TRANSITIONS[activation.status]:
            raise DomainTransitionError(
                f"Activation cannot move from {activation.status} to {target}."
            )
        if (target in {"approved", "completed"}) != approval_command:
            raise DomainTransitionError("Approval states require the approval command boundary.")
        if target == "approved":
            if activation.sim_order_id is None:
                raise DomainTransitionError("Approval requires a linked SIM order.")
            sim = await self._session.get(SimOrder, activation.sim_order_id)
            if (
                sim is None
                or sim.organization_id != organization_id
                or sim.status != "delivered"
                or not sim.customer_confirmed
            ):
                raise DomainTransitionError(
                    "Approval requires delivered, customer-confirmed SIM fulfilment."
                )
        previous = activation.status
        activation.status = target
        now = utcnow()
        if target in {"approved", "completed"}:
            activation.approval_reference = self._clean(payload.get("approval_reference"))
            activation.approved_by = actor.id
            activation.approved_at = activation.approved_at or now
        if target == "completed":
            activation.completed_at = now
        if target == "rejected":
            activation.rejection_reason = self._clean(payload.get("reason"))
        self._bump(activation, actor.id)
        await self._record(
            activation,
            actor,
            AuditAction.ACTIVATION_TRANSITIONED,
            EVENT_ACTIVATION_UPDATED,
            BUSINESS_EVENT_ACTIVATION_TRANSITIONED,
            {
                "from_status": previous,
                "to_status": target,
                "approval_reference": activation.approval_reference,
                "request_hash": self._hash(payload),
            },
            event_id=payload["idempotency_key"],
        )
        await self._session.commit()
        return (await self.views([activation]))[0]

    async def list_sla_policies(
        self, organization_id: int, limit: int
    ) -> tuple[list[dict[str, Any]], int]:
        rows, total = await self._repo.list_sla_policies(organization_id, limit=limit)
        return await self.views(rows), total

    async def get_sla_policy(self, organization_id: int, public_id: uuidlib.UUID) -> dict[str, Any]:
        return (await self.views([await self._require(SlaPolicy, organization_id, public_id)]))[0]

    async def create_sla_policy(
        self, *, organization_id: int, actor: User, payload: dict[str, Any]
    ) -> dict[str, Any]:
        policy = SlaPolicy(
            organization_id=organization_id,
            domain=payload["domain"],
            trigger_name=payload["trigger_name"].strip(),
            target_minutes=payload["target_minutes"],
            escalation_minutes=payload["escalation_minutes"],
            is_active=payload["is_active"],
            created_by=actor.id,
            updated_by=actor.id,
        )
        self._session.add(policy)
        await self._session.flush()
        await self._audit.record(
            AuditAction.SLA_POLICY_CREATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="sla_policy",
            entity_id=policy.id,
            after={
                "domain": policy.domain,
                "trigger_name": policy.trigger_name,
                "target_minutes": policy.target_minutes,
                "escalation_minutes": policy.escalation_minutes,
            },
        )
        await self._session.commit()
        return (await self.views([policy]))[0]

    async def update_sla_policy(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        policy = await self._require(SlaPolicy, organization_id, public_id)
        self._check_version(policy, payload["expected_row_version"])
        before = self._sla_policy_state(policy)
        policy.domain, policy.trigger_name = payload["domain"], payload["trigger_name"].strip()
        policy.target_minutes, policy.escalation_minutes, policy.is_active = (
            payload["target_minutes"],
            payload["escalation_minutes"],
            payload["is_active"],
        )
        self._bump(policy, actor.id)
        await self._audit.record(
            AuditAction.SLA_POLICY_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="sla_policy",
            entity_id=policy.id,
            before=before,
            after=self._sla_policy_state(policy),
        )
        await self._session.commit()
        return (await self.views([policy]))[0]

    async def list_sla_events(
        self, organization_id: int, limit: int
    ) -> tuple[list[dict[str, Any]], int]:
        rows, total = await self._repo.list_sla_events(organization_id, limit=limit)
        return await self.views(rows), total

    async def get_sla_event(self, organization_id: int, public_id: uuidlib.UUID) -> dict[str, Any]:
        return (
            await self.views([await self._require_immutable(SlaEvent, organization_id, public_id)])
        )[0]

    async def create_sla_event(
        self, *, organization_id: int, actor: User, payload: dict[str, Any]
    ) -> dict[str, Any]:
        request_hash = self._hash(payload)
        existing = await self._idempotent(
            SlaEvent, organization_id, payload["idempotency_key"], request_hash
        )
        if existing is not None:
            return (await self.views([existing]))[0]
        policy = await self._require(SlaPolicy, organization_id, payload["policy_id"])
        contact = await self._require_contact(organization_id, payload["contact_id"])
        entity = await self._resolve_entity(
            organization_id, payload["entity_type"], payload["entity_id"]
        )
        if entity.contact_id != contact.id:
            raise BadRequestError("SLA entity does not belong to the selected contact.")
        event = SlaEvent(
            organization_id=organization_id,
            policy_id=policy.id,
            contact_id=contact.id,
            entity_type=payload["entity_type"],
            entity_id=entity.id,
            event_type=payload["event_type"],
            due_at=payload["due_at"],
            actor_user_id=actor.id,
            reason=self._clean(payload.get("reason")),
            idempotency_key=payload["idempotency_key"].bytes,
            request_hash=request_hash,
        )
        self._session.add(event)
        await self._session.flush()
        await self._record(
            event,
            actor,
            AuditAction.SLA_EVENT_RECORDED,
            EVENT_SLA_RECORDED,
            BUSINESS_EVENT_SLA_RECORDED,
            {
                "event_type": event.event_type,
                "entity_type": event.entity_type,
                "due_at": event.due_at.isoformat(),
            },
            contact_id=contact.id,
            ref_type=REF_TYPE_SLA_EVENT,
            ref_id=event.id,
        )
        await self._session.commit()
        return (await self.views([event]))[0]

    async def views(self, rows: list[Any]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for row in rows:
            users = {
                name: await self._user_public(getattr(row, name, None))
                for name in (
                    "owner_user_id",
                    "actor_user_id",
                    "checked_by",
                    "decided_by",
                    "delivery_owner_user_id",
                    "approved_by",
                )
            }
            if isinstance(row, ReactivationCase):
                result.append(
                    {
                        "id": row.public_id,
                        "contact_id": await self._contact_public(row.contact_id),
                        "stage": row.stage,
                        "owner_user_id": users["owner_user_id"],
                        "previous_vi_number": row.previous_vi_number,
                        "active_delhi_number": row.active_delhi_number,
                        "source": row.source,
                        "closed_reason": row.closed_reason,
                        "row_version": row.row_version,
                        "created_at": row.created_at,
                        "updated_at": row.updated_at,
                    }
                )
            elif isinstance(row, ReactivationStageEvent):
                result.append(
                    {
                        "id": row.public_id,
                        "case_id": await self._case_public(row.case_id),
                        "from_stage": row.from_stage,
                        "to_stage": row.to_stage,
                        "actor_user_id": users["actor_user_id"],
                        "reason": row.reason,
                        "created_at": row.created_at,
                    }
                )
            elif isinstance(row, EligibilityCheck):
                result.append(
                    {
                        "id": row.public_id,
                        "case_id": await self._case_public(row.case_id),
                        "status": row.status,
                        "source": row.source,
                        "reason": row.reason,
                        "approval_reference": row.approval_reference,
                        "checked_by": users["checked_by"],
                        "checked_at": row.checked_at,
                    }
                )
            elif isinstance(row, KycCase):
                result.append(
                    {
                        "id": row.public_id,
                        "reactivation_case_id": await self._case_public(row.reactivation_case_id),
                        "contact_id": await self._contact_public(row.contact_id),
                        "status": row.status,
                        "owner_user_id": users["owner_user_id"],
                        "holder_verified": row.holder_verified,
                        "delhi_presence_verified": row.delhi_presence_verified,
                        "active_delhi_number_verified": row.active_delhi_number_verified,
                        "appointment_at": row.appointment_at,
                        "row_version": row.row_version,
                        "created_at": row.created_at,
                        "updated_at": row.updated_at,
                    }
                )
            elif isinstance(row, KycDecision):
                result.append(
                    {
                        "id": row.public_id,
                        "kyc_case_id": await self._aggregate_public(KycCase, row.kyc_case_id),
                        "decision_type": row.decision_type,
                        "decision": row.decision,
                        "reason": row.reason,
                        "decided_by": users["decided_by"],
                        "decided_at": row.decided_at,
                    }
                )
            elif isinstance(row, SimOrder):
                result.append(
                    {
                        "id": row.public_id,
                        "reactivation_case_id": await self._case_public(row.reactivation_case_id),
                        "contact_id": await self._contact_public(row.contact_id),
                        "status": row.status,
                        "delivery_address": row.delivery_address,
                        "service_area": row.service_area,
                        "delivery_owner_user_id": users["delivery_owner_user_id"],
                        "dispatched_at": row.dispatched_at,
                        "delivered_at": row.delivered_at,
                        "failed_at": row.failed_at,
                        "failure_reason": row.failure_reason,
                        "sim_serial": row.sim_serial,
                        "customer_confirmed": row.customer_confirmed,
                        "row_version": row.row_version,
                        "created_at": row.created_at,
                        "updated_at": row.updated_at,
                    }
                )
            elif isinstance(row, SimOrderEvent):
                result.append(
                    {
                        "id": row.public_id,
                        "sim_order_id": await self._aggregate_public(SimOrder, row.sim_order_id),
                        "from_status": row.from_status,
                        "to_status": row.to_status,
                        "actor_user_id": users["actor_user_id"],
                        "reason": row.reason,
                        "created_at": row.created_at,
                    }
                )
            elif isinstance(row, ActivationRecord):
                result.append(
                    {
                        "id": row.public_id,
                        "reactivation_case_id": await self._case_public(row.reactivation_case_id),
                        "sim_order_id": await self._aggregate_public(SimOrder, row.sim_order_id)
                        if row.sim_order_id
                        else None,
                        "contact_id": await self._contact_public(row.contact_id),
                        "status": row.status,
                        "owner_user_id": users["owner_user_id"],
                        "approval_reference": row.approval_reference,
                        "approved_by": users["approved_by"],
                        "approved_at": row.approved_at,
                        "completed_at": row.completed_at,
                        "rejection_reason": row.rejection_reason,
                        "row_version": row.row_version,
                        "created_at": row.created_at,
                        "updated_at": row.updated_at,
                    }
                )
            elif isinstance(row, SlaPolicy):
                result.append(
                    {
                        "id": row.public_id,
                        "domain": row.domain,
                        "trigger_name": row.trigger_name,
                        "target_minutes": row.target_minutes,
                        "escalation_minutes": row.escalation_minutes,
                        "is_active": row.is_active,
                        "row_version": row.row_version,
                        "created_at": row.created_at,
                        "updated_at": row.updated_at,
                    }
                )
            elif isinstance(row, SlaEvent):
                result.append(
                    {
                        "id": row.public_id,
                        "policy_id": await self._aggregate_public(SlaPolicy, row.policy_id),
                        "contact_id": await self._contact_public(row.contact_id),
                        "entity_type": row.entity_type,
                        "entity_id": await self._entity_public(row.entity_type, row.entity_id),
                        "event_type": row.event_type,
                        "due_at": row.due_at,
                        "actor_user_id": users["actor_user_id"],
                        "reason": row.reason,
                        "created_at": row.created_at,
                    }
                )
        return result

    async def _record(
        self,
        row: Any,
        actor: User,
        audit_action: str,
        timeline_event: str,
        business_event: str,
        payload: dict[str, Any],
        *,
        event_id: uuidlib.UUID | None = None,
        contact_id: int | None = None,
        ref_type: str | None = None,
        ref_id: int | None = None,
    ) -> None:
        actual_contact = contact_id if contact_id is not None else row.contact_id
        actual_ref_type = ref_type or self._ref_type(row)
        actual_ref_id = ref_id if ref_id is not None else row.id
        await self._audit.record(
            audit_action,
            actor_user_id=actor.id,
            organization_id=row.organization_id,
            entity_type=actual_ref_type,
            entity_id=actual_ref_id,
            after=payload,
        )
        await self._timeline.record(
            organization_id=row.organization_id,
            contact_id=actual_contact,
            event_type=timeline_event,
            ref_type=actual_ref_type,
            ref_id=actual_ref_id,
            payload={**payload, "id": row.public_id},
        )
        await self._business_events.record_domain_event(
            organization_id=row.organization_id,
            event_id=event_id or uuidlib.UUID(bytes=row.uuid),
            event_type=business_event,
            actor_id=actor.id,
            subject_type=actual_ref_type,
            subject_id=actual_ref_id,
            contact_id=actual_contact,
            occurred_at=utcnow(),
            source="vi_domain",
            payload={**payload, "id": row.public_id},
        )

    async def _audit_and_timeline(
        self,
        row: Any,
        actor: User,
        action: str,
        timeline_event: str,
        payload: dict[str, Any],
        ref_type: str,
    ) -> None:
        await self._audit.record(
            action,
            actor_user_id=actor.id,
            organization_id=row.organization_id,
            entity_type=ref_type,
            entity_id=row.id,
            after=payload,
        )
        await self._timeline.record(
            organization_id=row.organization_id,
            contact_id=row.contact_id,
            event_type=timeline_event,
            ref_type=ref_type,
            ref_id=row.id,
            payload={**payload, "id": row.public_id},
        )

    async def _validate_reactivation_gate(self, case: ReactivationCase, target: str) -> None:
        if target in {"eligible", "not_eligible"}:
            checks = await self._repo.eligibility_checks(case.id)
            expected = "eligible" if target == "eligible" else "not_eligible"
            if not checks or checks[-1].status != expected:
                raise DomainTransitionError(
                    f"Transition to {target} requires a matching latest eligibility decision."
                )
        if target == "documents_received":
            count = await self._session.scalar(
                select(func.count())
                .select_from(ContactDocument)
                .where(
                    ContactDocument.organization_id == case.organization_id,
                    ContactDocument.contact_id == case.contact_id,
                    ContactDocument.deleted_at.is_(None),
                )
            )
            if not count:
                raise DomainTransitionError(
                    "Documents received requires at least one governed customer document."
                )
        if target == "confirmed":
            kyc = await self._repo.child_for_case(KycCase, case.organization_id, case.id)
            if kyc is None or kyc.status != "approved":
                raise DomainTransitionError("Confirmation requires manager-approved KYC.")
        if (
            target == "sim_order"
            and await self._repo.child_for_case(SimOrder, case.organization_id, case.id) is None
        ):
            raise DomainTransitionError("SIM-order stage requires an existing SIM order.")
        if target == "activation_pending":
            sim = await self._repo.child_for_case(SimOrder, case.organization_id, case.id)
            activation = await self._repo.child_for_case(
                ActivationRecord, case.organization_id, case.id
            )
            if (
                sim is None
                or sim.status != "delivered"
                or not sim.customer_confirmed
                or activation is None
            ):
                raise DomainTransitionError(
                    "Activation pending requires delivered, customer-confirmed SIM fulfilment and an activation record."
                )
        if target == "completed":
            activation = await self._repo.child_for_case(
                ActivationRecord, case.organization_id, case.id
            )
            if activation is None or activation.status != "completed":
                raise DomainTransitionError("Completion requires a completed activation record.")

    async def _validate_kyc_approval(self, kyc: KycCase) -> None:
        if not (
            kyc.holder_verified and kyc.delhi_presence_verified and kyc.active_delhi_number_verified
        ):
            raise DomainTransitionError(
                "KYC approval requires all Vi identity and Delhi verification checks."
            )
        count = await self._session.scalar(
            select(func.count())
            .select_from(ContactDocument)
            .where(
                ContactDocument.organization_id == kyc.organization_id,
                ContactDocument.contact_id == kyc.contact_id,
                ContactDocument.status == DOCUMENT_STATUS_VERIFIED,
                ContactDocument.deleted_at.is_(None),
            )
        )
        if not count:
            raise DomainTransitionError(
                "KYC approval requires at least one verified governed document."
            )

    async def _require_contact(self, organization_id: int, public_id: uuidlib.UUID) -> Contact:
        contact = await self._contacts.get_active_by_uuid(organization_id, public_id.bytes)
        if contact is None:
            raise NotFoundError("Contact not found.")
        return contact

    async def _require(self, model: Any, organization_id: int, public_id: uuidlib.UUID) -> Any:
        row = await self._repo.by_uuid(model, organization_id, public_id.bytes)
        if row is None:
            raise NotFoundError(f"{model.__name__} not found.")
        return row

    async def _require_immutable(
        self, model: Any, organization_id: int, public_id: uuidlib.UUID
    ) -> Any:
        row = await self._repo.immutable_by_uuid(model, organization_id, public_id.bytes)
        if row is None:
            raise NotFoundError(f"{model.__name__} not found.")
        return row

    async def _idempotent(
        self, model: Any, organization_id: int, key: uuidlib.UUID, request_hash: str
    ) -> Any | None:
        row = await self._repo.immutable_by_idempotency(model, organization_id, key.bytes)
        if row is not None and row.request_hash != request_hash:
            raise IdempotencyConflictError(
                "Idempotency key was already used with a different command."
            )
        return row

    async def _user_id(self, organization_id: int, public_id: uuidlib.UUID | None) -> int | None:
        if public_id is None:
            return None
        row = (
            await self._session.scalars(
                select(User).where(
                    User.organization_id == organization_id,
                    User.uuid == public_id.bytes,
                    User.deleted_at.is_(None),
                    User.is_active.is_(True),
                )
            )
        ).first()
        if row is None:
            raise NotFoundError("User not found.")
        return row.id

    async def _require_optional_sim(
        self, organization_id: int, public_id: uuidlib.UUID | None, case_id: int
    ) -> SimOrder | None:
        if public_id is None:
            return None
        sim = await self._require(SimOrder, organization_id, public_id)
        if sim.reactivation_case_id != case_id:
            raise BadRequestError("SIM order belongs to another reactivation case.")
        return sim  # type: ignore[no-any-return]

    async def _resolve_entity(
        self, organization_id: int, entity_type: str, public_id: uuidlib.UUID
    ) -> Any:
        mapping = {
            "reactivation_case": ReactivationCase,
            "kyc_case": KycCase,
            "sim_order": SimOrder,
            "activation_record": ActivationRecord,
        }
        return await self._require(mapping[entity_type], organization_id, public_id)

    async def _user_public(self, internal_id: int | None) -> str | None:
        if internal_id is None:
            return None
        row = await self._session.get(User, internal_id)
        return row.public_id if row else None

    async def _contact_public(self, internal_id: int) -> str:
        row = await self._session.get(Contact, internal_id)
        if row is None:
            raise NotFoundError("Contact not found.")
        return str(row.public_id)

    async def _aggregate_public(self, model: Any, internal_id: int) -> str:
        row: Any | None = await self._session.get(model, internal_id)
        if row is None:
            raise NotFoundError(f"{model.__name__} not found.")
        return str(row.public_id)

    async def _case_public(self, internal_id: int) -> str:
        return await self._aggregate_public(ReactivationCase, internal_id)

    async def _entity_public(self, entity_type: str, internal_id: int) -> str:
        mapping = {
            "reactivation_case": ReactivationCase,
            "kyc_case": KycCase,
            "sim_order": SimOrder,
            "activation_record": ActivationRecord,
        }
        return await self._aggregate_public(mapping[entity_type], internal_id)

    @staticmethod
    def _hash(payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    @staticmethod
    def _clean(value: str | None) -> str | None:
        return value.strip() or None if value else None

    @staticmethod
    def _first_attribute(attributes: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = attributes.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return None

    @staticmethod
    def _bool_attribute(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"yes", "true", "required", "1"}:
                return True
            if normalized in {"no", "false", "not_required", "0"}:
                return False
        return None

    @staticmethod
    def _string_list_attribute(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    @staticmethod
    def _check_version(row: Any, expected: int) -> None:
        if row.row_version != expected:
            raise VersionConflictError("The record changed since it was loaded.")

    @staticmethod
    def _bump(row: Any, actor_id: int) -> None:
        row.row_version += 1
        row.updated_by = actor_id
        row.updated_at = utcnow()

    @staticmethod
    def _ref_type(row: Any) -> str:
        if isinstance(row, (ReactivationCase, EligibilityCheck)):
            return REF_TYPE_REACTIVATION_CASE
        if isinstance(row, (KycCase, KycDecision)):
            return REF_TYPE_KYC_CASE
        if isinstance(row, (SimOrder, SimOrderEvent)):
            return REF_TYPE_SIM_ORDER
        if isinstance(row, ActivationRecord):
            return REF_TYPE_ACTIVATION_RECORD
        return REF_TYPE_SLA_EVENT

    @staticmethod
    def _kyc_state(row: KycCase) -> dict[str, Any]:
        return {
            "status": row.status,
            "owner_user_id": row.owner_user_id,
            "holder_verified": row.holder_verified,
            "delhi_presence_verified": row.delhi_presence_verified,
            "active_delhi_number_verified": row.active_delhi_number_verified,
            "appointment_at": row.appointment_at,
        }

    @staticmethod
    def _sim_state(row: SimOrder) -> dict[str, Any]:
        return {
            "status": row.status,
            "delivery_owner_user_id": row.delivery_owner_user_id,
            "service_area": row.service_area,
            "sim_serial": row.sim_serial,
            "customer_confirmed": row.customer_confirmed,
        }

    @staticmethod
    def _sla_policy_state(row: SlaPolicy) -> dict[str, Any]:
        return {
            "domain": row.domain,
            "trigger_name": row.trigger_name,
            "target_minutes": row.target_minutes,
            "escalation_minutes": row.escalation_minutes,
            "is_active": row.is_active,
        }
