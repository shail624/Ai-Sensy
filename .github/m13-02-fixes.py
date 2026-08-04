from __future__ import annotations

import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()


def replace_expected(path_name: str, old: str, new: str, count: int = 1) -> None:
    path = root / path_name
    source = path.read_text(encoding="utf-8")
    if source.count(old) != count:
        raise SystemExit(
            f"expected {count} marker(s) in {path_name}: {old!r}; found {source.count(old)}"
        )
    path.write_text(source.replace(old, new), encoding="utf-8")


replace_expected(
    "backend/app/models/contact_event.py",
    'REF_TYPE_IDENTITY_RECOMMENDATION = "identity_merge_recommendation"',
    'REF_TYPE_IDENTITY_RECOMMENDATION = "identity_recommendation"',
)

replace_expected(
    "backend/app/services/identity_resolution_service.py",
    "class IdentityRecommendationView:\n    recommendation: IdentityMergeRecommendation\n    primary_contact_id: str\n    duplicate_contact_id: str\n",
    "class IdentityRecommendationView:\n    recommendation: IdentityMergeRecommendation\n    conflict_id: str\n    primary_contact_id: str\n    duplicate_contact_id: str\n",
)
replace_expected(
    "backend/app/services/identity_resolution_service.py",
    "        return IdentityRecommendationView(\n            recommendation=recommendation,\n            primary_contact_id=primary.public_id,\n            duplicate_contact_id=duplicate.public_id,\n        )\n\n    async def decide_recommendation",
    "        return IdentityRecommendationView(\n            recommendation=recommendation,\n            conflict_id=conflict.public_id,\n            primary_contact_id=primary.public_id,\n            duplicate_contact_id=duplicate.public_id,\n        )\n\n    async def decide_recommendation",
)
replace_expected(
    "backend/app/services/identity_resolution_service.py",
    "        return IdentityRecommendationView(\n            recommendation=recommendation,\n            primary_contact_id=primary.public_id,\n            duplicate_contact_id=duplicate.public_id,\n        )\n\n    def _normalize_unique",
    "        return IdentityRecommendationView(\n            recommendation=recommendation,\n            conflict_id=conflict.public_id,\n            primary_contact_id=primary.public_id,\n            duplicate_contact_id=duplicate.public_id,\n        )\n\n    def _normalize_unique",
)
replace_expected(
    "backend/app/services/identity_resolution_service.py",
    "                IdentityRecommendationView(\n                    recommendation=recommendation,\n                    primary_contact_id=primary.public_id,\n                    duplicate_contact_id=duplicate.public_id,\n                )",
    "                IdentityRecommendationView(\n                    recommendation=recommendation,\n                    conflict_id=conflict.public_id,\n                    primary_contact_id=primary.public_id,\n                    duplicate_contact_id=duplicate.public_id,\n                )",
)

replace_expected(
    "backend/app/schemas/contact_identity.py",
    "    def from_view(\n        cls, view: IdentityRecommendationView, conflict_public_id: str\n    ) -> IdentityMergeRecommendationResponse:\n",
    "    def from_view(\n        cls, view: IdentityRecommendationView\n    ) -> IdentityMergeRecommendationResponse:\n",
)
replace_expected(
    "backend/app/schemas/contact_identity.py",
    "            conflict_id=conflict_public_id,",
    "            conflict_id=view.conflict_id,",
)
replace_expected(
    "backend/app/schemas/contact_identity.py",
    "                IdentityMergeRecommendationResponse.from_view(item, row.public_id)\n",
    "                IdentityMergeRecommendationResponse.from_view(item)\n",
)
replace_expected(
    "backend/app/schemas/contact_identity.py",
    "    IdentityConflictStatus,\n",
    "",
)

replace_expected(
    "backend/app/api/v1/endpoints/contact_identity.py",
    "    return IdentityMergeRecommendationResponse.from_view(view, str(conflict_id))",
    "    return IdentityMergeRecommendationResponse.from_view(view)",
)
replace_expected(
    "backend/app/api/v1/endpoints/contact_identity.py",
    "    conflict = await service.get_conflict(actor.organization_id, uuidlib.UUID(int=0))\n    return IdentityMergeRecommendationResponse.from_view(view, conflict.conflict.public_id)",
    "    return IdentityMergeRecommendationResponse.from_view(view)",
    count=2,
)
replace_expected(
    "backend/app/api/v1/endpoints/contact_identity.py",
    '    conflict_status: IdentityConflictStatus | None = Query(default=None, alias="status"),\n'
    '    limit: int = Query(default=50, ge=1, le=100),\n'
    '    offset: int = Query(default=0, ge=0),\n',
    '    conflict_status: Annotated[\n'
    '        IdentityConflictStatus | None, Query(alias="status")\n'
    '    ] = None,\n'
    '    limit: Annotated[int, Query(ge=1, le=100)] = 50,\n'
    '    offset: Annotated[int, Query(ge=0)] = 0,\n',
)

replace_expected(
    "backend/app/models/__init__.py",
    "from app.models.contact_identity import (\n"
    "    ContactIdentity,\n"
    "    IdentityConflict,\n"
    "    IdentityMergeRecommendation,\n"
    ")\n",
    "",
)
replace_expected(
    "backend/app/models/__init__.py",
    "from app.models.contact_event import ContactEvent\n",
    "from app.models.contact_event import ContactEvent\n"
    "from app.models.contact_identity import (\n"
    "    ContactIdentity,\n"
    "    IdentityConflict,\n"
    "    IdentityMergeRecommendation,\n"
    ")\n",
)

replace_expected(
    "backend/app/repositories/contact_identity.py",
    "from sqlalchemy.ext.asyncio import AsyncSession\n\n",
    "",
)

replace_expected(
    "backend/tests/test_identity_resolution.py",
    '        assert identity.contact_id == primary["row_version"] + 1\n',
    '        primary_row = (\n            await session.scalars(select(Contact).where(Contact.wa_id == "14155550001"))\n        ).one()\n        assert identity.contact_id == primary_row.id\n',
)
