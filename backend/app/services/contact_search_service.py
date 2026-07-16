"""Advanced contact search (Doc 04 §14.1 ``POST /contacts/search``) — FR-CON-12.

An advanced search is an **unsaved segment**: it accepts the same nested AND/OR rule
structure, is validated by the same compiler, and is evaluated by the same engine — so a
saved filter and an ad-hoc search always return identical results (saved-filter
compatibility). Quick list filters (``?q``, ``filter[...]``) stay on ``GET /contacts``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.crm.segment_compiler import AttributeSpec, compile_rules, validate_rule
from app.models.contact import Contact
from app.repositories.attribute import AttributeDefinitionRepository
from app.repositories.segment import SegmentRepository


@dataclass(slots=True)
class SearchResult:
    contacts: list[Contact]
    has_more: bool
    total: int


class ContactSearchService:
    def __init__(self, session: AsyncSession) -> None:
        self._attributes = AttributeDefinitionRepository(session)
        self._evaluator = SegmentRepository(session)

    async def _attribute_specs(self, organization_id: int) -> dict[str, AttributeSpec]:
        return {
            definition.key_name: AttributeSpec(
                attribute_id=definition.id,
                data_type=definition.data_type,
                enum_values=definition.enum_values_json,
            )
            for definition in await self._attributes.list_for_org(organization_id)
        }

    async def search(
        self,
        organization_id: int,
        *,
        match_type: str,
        rules: list[dict[str, Any]],
        limit: int,
        cursor: tuple[datetime, int] | None,
    ) -> SearchResult:
        specs = await self._attribute_specs(organization_id)
        for rule in rules:
            validate_rule(
                rule["field_source"],
                rule["field_key"],
                rule["operator"],
                rule.get("value"),
                specs,
            )
        condition = compile_rules(
            organization_id=organization_id,
            match_type=match_type,
            rules=rules,
            attributes=specs,
        )
        contacts, has_more = await self._evaluator.paginate_matching(
            organization_id, condition, limit=limit, cursor=cursor
        )
        total = await self._evaluator.count_matching(organization_id, condition)
        return SearchResult(contacts=contacts, has_more=has_more, total=total)
