"""Audience resolution (Doc 04 §17; FR-CAM-01/02).

Turns "who should get this" into a concrete list of contacts. Three sources, one answer:

- **segment** — the saved rule set, evaluated live through :class:`SegmentService`'s own compiled
  condition. A campaign never reinterprets segment rules; it asks the segment.
- **tag** — every live contact carrying any of the named tags.
- **list** — an explicit selection of contact ids.

(``upload`` is a fourth type in Doc 03 §8.1; it belongs to the import pipeline and is not resolved
here — a campaign built on one would need the upload materialized into contacts first.)

**Opt-out is applied at resolution, not at send** (FR-CAM-02, Doc 01 CMP). A contact who has opted
out is not a recipient at all: excluding them here means the count an operator approves is the
count that will actually be messaged, rather than a number that quietly shrinks later.
"""

from __future__ import annotations

import uuid as uuidlib
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.campaign import AUDIENCE_LIST, AUDIENCE_SEGMENT, AUDIENCE_TAG, AUDIENCE_UPLOAD
from app.models.contact import OPT_IN_OPTED_OUT, Contact
from app.models.tag import Tag, contact_tags
from app.repositories.contact import ContactRepository
from app.repositories.tag import TagRepository
from app.services.segment_service import SegmentService

#: How many contacts to pull per segment preview page while materializing.
SEGMENT_PAGE = 500


class AudienceInvalid(ValidationError):
    """The audience reference cannot be resolved to contacts (Doc 04 §17 → 422)."""

    code = "audience_invalid"
    title = "Audience Invalid"


@dataclass(slots=True)
class Audience:
    """A resolved audience: who is in, and who was excluded and why."""

    contacts: list[Contact]
    #: Contacts the source matched but compliance removed (FR-CAM-02).
    excluded_opted_out: int = 0

    @property
    def total(self) -> int:
        return len(self.contacts)


class AudienceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tags = TagRepository(session)
        self._contacts = ContactRepository(session)
        self._segment_service = SegmentService(session)

    async def resolve(
        self, *, organization_id: int, audience_type: str, audience_ref: dict[str, Any] | None
    ) -> Audience:
        """Every contact this audience selects, minus those who may not be contacted."""
        ref = audience_ref or {}
        if audience_type == AUDIENCE_SEGMENT:
            contacts = await self._from_segment(organization_id, ref)
        elif audience_type == AUDIENCE_TAG:
            contacts = await self._from_tags(organization_id, ref)
        elif audience_type == AUDIENCE_LIST:
            contacts = await self._from_list(organization_id, ref)
        elif audience_type == AUDIENCE_UPLOAD:
            raise AudienceInvalid(
                "Upload audiences must be imported into contacts first, then targeted by tag or "
                "segment.",
                errors=[
                    {"field": "audience_type", "code": "unsupported", "message": "upload"}
                ],
            )
        else:
            raise AudienceInvalid(
                f"Unknown audience type {audience_type!r}.",
                errors=[{"field": "audience_type", "code": "invalid", "message": audience_type}],
            )

        eligible = [c for c in contacts if c.opt_in_status != OPT_IN_OPTED_OUT]
        return Audience(contacts=eligible, excluded_opted_out=len(contacts) - len(eligible))

    async def _from_segment(self, organization_id: int, ref: dict[str, Any]) -> list[Contact]:
        """Walk the segment's own keyset preview to the end.

        Through :class:`SegmentService`'s public API, not its compiled condition: rule compilation
        is Module 2's business and a campaign that reimplemented it would drift from the segment it
        claims to target. Paging is what that API offers, so this pages.
        """
        public_id = _one_id(ref, "segment_id")
        contacts: list[Contact] = []
        cursor: tuple[Any, int] | None = None
        while True:
            page = await self._segment_service.preview(
                organization_id=organization_id,
                public_id=public_id,
                limit=SEGMENT_PAGE,
                cursor=cursor,
            )
            contacts.extend(page.contacts)
            if not page.has_more or not page.contacts:
                return contacts
            last = page.contacts[-1]
            cursor = (last.created_at, last.id)

    async def _from_tags(self, organization_id: int, ref: dict[str, Any]) -> list[Contact]:
        raw = ref.get("tag_ids") or []
        if not raw:
            raise AudienceInvalid(
                "A tag audience needs at least one tag_id.",
                errors=[{"field": "audience_ref.tag_ids", "code": "required", "message": "None."}],
            )
        tag_pks: list[int] = []
        for value in raw:
            tag = await self._tags.get_active_by_uuid(organization_id, _uuid(value).bytes)
            if tag is None:
                raise NotFoundError(f"Tag {value} not found.")
            tag_pks.append(tag.id)

        # Any of the tags, not all: a broadcast to "vi_reactivation OR lapsed" is the common case.
        stmt = (
            select(Contact)
            .join(contact_tags, contact_tags.c.contact_id == Contact.id)
            .join(Tag, Tag.id == contact_tags.c.tag_id)
            .where(
                Contact.organization_id == organization_id,
                Contact.deleted_at.is_(None),
                Tag.id.in_(tag_pks),
            )
            .distinct()
        )
        return list((await self._session.scalars(stmt)).all())

    async def _from_list(self, organization_id: int, ref: dict[str, Any]) -> list[Contact]:
        raw = ref.get("contact_ids") or []
        if not raw:
            raise AudienceInvalid(
                "A list audience needs at least one contact_id.",
                errors=[
                    {"field": "audience_ref.contact_ids", "code": "required", "message": "None."}
                ],
            )
        contacts = await self._contacts.get_active_by_uuids(
            organization_id, [_uuid(value).bytes for value in raw]
        )
        if len(contacts) != len({str(v) for v in raw}):
            raise AudienceInvalid(
                "One or more contacts in the list do not exist.",
                errors=[
                    {
                        "field": "audience_ref.contact_ids",
                        "code": "not_found",
                        "message": f"{len(contacts)} of {len(raw)} resolved",
                    }
                ],
            )
        return contacts


def _uuid(value: Any) -> uuidlib.UUID:
    try:
        return uuidlib.UUID(str(value))
    except ValueError as exc:
        raise AudienceInvalid(
            f"{value!r} is not a valid id.",
            errors=[{"field": "audience_ref", "code": "invalid", "message": str(value)}],
        ) from exc


def _one_id(ref: dict[str, Any], key: str) -> uuidlib.UUID:
    value = ref.get(key)
    if not value:
        raise AudienceInvalid(
            f"This audience needs a {key}.",
            errors=[{"field": f"audience_ref.{key}", "code": "required", "message": "Missing."}],
        )
    return _uuid(value)
