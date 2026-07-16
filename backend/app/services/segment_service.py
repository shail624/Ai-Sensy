"""Segment service (Doc 04 §14.3, Doc 03 §6.4) — FR-CON-10.

Saved dynamic filters: CRUD over segments and their normalized rule tree, preview of matching
contacts, and cached-count refresh. Rules are validated at write time (422) and compiled into
a parameterized SQL condition; the compiled tree is cached in ``compiled_json`` and the last
evaluated size in ``cached_count``/``last_evaluated_at``. Every change is audited.
"""

from __future__ import annotations

import uuid as uuidlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.crm.segment_compiler import compile_rules, validate_rule
from app.db.mixins import utcnow
from app.models.contact import Contact
from app.models.segment import MATCH_ALL, Segment, SegmentRule
from app.models.user import User
from app.repositories.segment import SegmentRepository
from app.services.audit_service import AuditAction, AuditService


@dataclass(slots=True)
class SegmentPreview:
    contacts: list[Contact]
    has_more: bool
    total: int


class SegmentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._segments = SegmentRepository(session)
        self._audit = AuditService(session)

    # --- Helpers -------------------------------------------------------------
    @staticmethod
    def _rule_dicts(segment: Segment) -> list[dict[str, Any]]:
        return [
            {
                "group_index": rule.group_index,
                "field_source": rule.field_source,
                "field_key": rule.field_key,
                "operator": rule.operator,
                "value": rule.value_json,
            }
            for rule in segment.rules
        ]

    def _condition(self, segment: Segment) -> Any | None:
        return compile_rules(
            organization_id=segment.organization_id,
            match_type=segment.match_type,
            rules=self._rule_dicts(segment),
        )

    @staticmethod
    def _compiled_tree(match_type: str, rules: list[dict[str, Any]]) -> dict[str, Any]:
        groups: dict[int, list[dict[str, Any]]] = {}
        for rule in rules:
            groups.setdefault(int(rule.get("group_index", 0)), []).append(
                {
                    "field_source": rule["field_source"],
                    "field_key": rule["field_key"],
                    "operator": rule["operator"],
                    "value": rule.get("value"),
                }
            )
        return {
            "match_type": match_type,
            "groups": [
                {"group_index": index, "rules": items} for index, items in sorted(groups.items())
            ],
        }

    def _apply_rules(
        self, segment: Segment, match_type: str, rules: list[dict[str, Any]]
    ) -> None:
        for rule in rules:
            validate_rule(
                rule["field_source"], rule["field_key"], rule["operator"], rule.get("value")
            )
        segment.match_type = match_type
        segment.rules = [
            SegmentRule(
                group_index=int(rule.get("group_index", 0)),
                field_source=rule["field_source"],
                field_key=rule["field_key"],
                operator=rule["operator"],
                value_json=rule.get("value"),
            )
            for rule in rules
        ]
        segment.compiled_json = self._compiled_tree(match_type, rules)
        # Rules changed → the cached size is stale until re-evaluated.
        segment.cached_count = None
        segment.last_evaluated_at = None

    # --- Queries -------------------------------------------------------------
    async def list_segments(self, organization_id: int) -> list[Segment]:
        return await self._segments.list_for_org(organization_id)

    async def get_segment(self, organization_id: int, public_id: uuidlib.UUID) -> Segment:
        segment = await self._segments.get_active_by_uuid(organization_id, public_id.bytes)
        if segment is None:
            raise NotFoundError("Segment not found.")
        return segment

    # --- Mutations -----------------------------------------------------------
    async def create_segment(
        self,
        *,
        organization_id: int,
        actor: User,
        name: str,
        description: str | None,
        match_type: str,
        rules: list[dict[str, Any]],
    ) -> Segment:
        if await self._segments.get_by_name(organization_id, name) is not None:
            raise ConflictError(f"A segment named {name!r} already exists.")
        segment = Segment(
            organization_id=organization_id,
            name=name,
            description=description,
            match_type=match_type or MATCH_ALL,
            created_by=actor.id,
        )
        self._apply_rules(segment, segment.match_type, rules)
        await self._segments.add(segment)
        await self._audit.record(
            AuditAction.SEGMENT_CREATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="segment",
            entity_id=segment.id,
            after={"name": name, "match_type": segment.match_type, "rules": len(rules)},
        )
        await self._session.commit()
        await self._session.refresh(segment, ["rules"])
        return segment

    async def update_segment(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        name: str | None,
        description: str | None,
        match_type: str | None,
        rules: list[dict[str, Any]] | None,
    ) -> Segment:
        segment = await self.get_segment(organization_id, public_id)
        before = {"name": segment.name, "match_type": segment.match_type}
        if name is not None and name != segment.name:
            if await self._segments.get_by_name(organization_id, name) is not None:
                raise ConflictError(f"A segment named {name!r} already exists.")
            segment.name = name
        if description is not None:
            segment.description = description
        if rules is not None:
            self._apply_rules(segment, match_type or segment.match_type, rules)
        elif match_type is not None and match_type != segment.match_type:
            # Match type alone changes the compiled tree and invalidates the cached size.
            self._apply_rules(segment, match_type, self._rule_dicts(segment))
        await self._segments.flush()
        await self._audit.record(
            AuditAction.SEGMENT_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="segment",
            entity_id=segment.id,
            before=before,
            after={"name": segment.name, "match_type": segment.match_type},
        )
        await self._session.commit()
        await self._session.refresh(segment, ["rules"])
        return segment

    async def delete_segment(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> None:
        segment = await self.get_segment(organization_id, public_id)
        segment.deleted_at = utcnow()
        await self._segments.flush()
        await self._audit.record(
            AuditAction.SEGMENT_DELETED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="segment",
            entity_id=segment.id,
            before={"name": segment.name},
        )
        await self._session.commit()

    # --- Evaluation ----------------------------------------------------------
    async def preview(
        self,
        *,
        organization_id: int,
        public_id: uuidlib.UUID,
        limit: int,
        cursor: tuple[datetime, int] | None,
    ) -> SegmentPreview:
        segment = await self.get_segment(organization_id, public_id)
        condition = self._condition(segment)
        contacts, has_more = await self._segments.paginate_matching(
            organization_id, condition, limit=limit, cursor=cursor
        )
        total = await self._segments.count_matching(organization_id, condition)
        return SegmentPreview(contacts=contacts, has_more=has_more, total=total)

    async def refresh_count(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> Segment:
        """Recompute and cache the segment size (Doc 04 §14.3 refresh)."""
        segment = await self.get_segment(organization_id, public_id)
        segment.cached_count = await self._segments.count_matching(
            organization_id, self._condition(segment)
        )
        segment.last_evaluated_at = utcnow()
        await self._segments.flush()
        await self._audit.record(
            AuditAction.SEGMENT_REFRESHED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="segment",
            entity_id=segment.id,
            after={"cached_count": segment.cached_count},
        )
        await self._session.commit()
        return segment
