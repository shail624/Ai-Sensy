"""Contact CRUD endpoints (Doc 04 §14.1) — Module 2 foundation.

Reads require ``contacts:read``; writes require ``contacts:write`` (Owner superuser bypasses).
Contacts are organization-scoped. Listing supports keyset pagination, quick search (``q``),
filters (``filter[...]``), and whitelisted sorting. Tags/attributes/timeline/import/export/
bulk are later steps and are not implemented here.
"""

from __future__ import annotations

import base64
import json
import uuid as uuidlib
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import SessionDep, require_permissions
from app.api.pagination import Page, clamp_limit, decode_cursor, encode_cursor
from app.core.exceptions import BadRequestError
from app.models.user import User
from app.repositories.contact import ContactRepository
from app.schemas.contact import (
    ContactCreateRequest,
    ContactResponse,
    ContactsPage,
    ContactUpdateRequest,
)
from app.schemas.contact_event import ContactEventResponse, ContactTimelinePage
from app.schemas.tag import ContactTagsRequest
from app.services.contact_event_service import ContactEventService
from app.services.contact_service import ContactService
from app.services.tag_service import TagService

router = APIRouter()

ContactsReadActor = Annotated[User, Depends(require_permissions("contacts:read"))]
ContactsWriteActor = Annotated[User, Depends(require_permissions("contacts:write"))]

_DT_SORTS = {"created_at", "last_inbound_at"}


def _bool_param(value: str | None) -> bool | None:
    if value is None:
        return None
    return value.strip().lower() in {"true", "1", "yes"}


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError as exc:
        raise BadRequestError("Invalid date filter; use ISO-8601.") from exc


def _encode_cursor(sort_name: str, value: Any, entity_id: int) -> str:
    serialized = value.isoformat() if isinstance(value, datetime) else value
    raw = json.dumps({"s": sort_name, "v": serialized, "id": entity_id}).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str, sort_name: str) -> tuple[Any, int, bool]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        if data["s"] != sort_name:
            raise BadRequestError("Cursor does not match the requested sort order.")
        value = data["v"]
        is_null = value is None
        if not is_null and sort_name in _DT_SORTS:
            value = datetime.fromisoformat(value)
        return value, int(data["id"]), is_null
    except (ValueError, KeyError, TypeError) as exc:
        raise BadRequestError("Invalid pagination cursor.") from exc


def _opt_in_filter(params) -> list[str] | None:
    csv = params.get("filter[opt_in_status][in]")
    if csv:
        return [v for v in (s.strip() for s in csv.split(",")) if v]
    single = params.get("filter[opt_in_status][eq]")
    return [single] if single else None


@router.get("/contacts", response_model=ContactsPage, summary="List/search/filter contacts")
async def list_contacts(
    request: Request, session: SessionDep, actor: ContactsReadActor
) -> ContactsPage:
    params = request.query_params
    limit = clamp_limit(params.get("limit"))
    sort = params.get("sort") or "-created_at"
    raw_cursor = params.get("cursor")
    sort_name, _ = ContactRepository.parse_sort(sort)
    cursor = _decode_cursor(raw_cursor, sort_name) if raw_cursor else None

    result = await ContactService(session).list_contacts(
        actor.organization_id,
        limit=limit,
        sort=sort,
        cursor=cursor,
        q=params.get("q"),
        opt_in_status=_opt_in_filter(params),
        source=params.get("filter[source][eq]"),
        is_active_on_wa=_bool_param(params.get("filter[is_active_on_wa][bool]")),
        created_from=_parse_dt(params.get("filter[created_at][gte]")),
        created_to=_parse_dt(params.get("filter[created_at][lte]")),
    )
    data = [ContactResponse.from_contact(c) for c in result.contacts]
    next_cursor = None
    if result.has_more and result.contacts:
        last = result.contacts[-1]
        next_cursor = _encode_cursor(result.next_sort, getattr(last, result.next_sort), last.id)
    return ContactsPage(
        data=data,
        page=Page(limit=limit, has_more=result.has_more, next_cursor=next_cursor, total=result.total),
    )


@router.post(
    "/contacts",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a contact",
)
async def create_contact(
    payload: ContactCreateRequest, session: SessionDep, actor: ContactsWriteActor
) -> ContactResponse:
    contact = await ContactService(session).create_contact(
        organization_id=actor.organization_id,
        actor=actor,
        phone_e164=payload.phone_e164,
        opt_in_status=payload.opt_in_status,
        source=payload.source,
        fields={
            "full_name": payload.full_name,
            "first_name": payload.first_name,
            "last_name": payload.last_name,
            "email": str(payload.email) if payload.email else None,
            "locale": payload.locale,
            "country_code": payload.country_code,
        },
    )
    return ContactResponse.from_contact(contact)


@router.get("/contacts/{contact_id}", response_model=ContactResponse, summary="Get a contact")
async def get_contact(
    contact_id: uuidlib.UUID, session: SessionDep, actor: ContactsReadActor
) -> ContactResponse:
    contact = await ContactService(session).get_contact(actor.organization_id, contact_id)
    return ContactResponse.from_contact(contact)


@router.patch("/contacts/{contact_id}", response_model=ContactResponse, summary="Update a contact")
async def update_contact(
    contact_id: uuidlib.UUID,
    payload: ContactUpdateRequest,
    session: SessionDep,
    actor: ContactsWriteActor,
) -> ContactResponse:
    provided = payload.model_dump(exclude_unset=True)
    provided.pop("row_version", None)
    opt_in_status = provided.pop("opt_in_status", None)
    if provided.get("email") is not None:
        provided["email"] = str(provided["email"])
    contact = await ContactService(session).update_contact(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=contact_id,
        opt_in_status=opt_in_status,
        fields=provided,
        expected_version=payload.row_version,
    )
    return ContactResponse.from_contact(contact)


@router.delete(
    "/contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a contact",
)
async def delete_contact(
    contact_id: uuidlib.UUID, session: SessionDep, actor: ContactsWriteActor
) -> None:
    await ContactService(session).delete_contact(
        organization_id=actor.organization_id, actor=actor, public_id=contact_id
    )


# --- Contact sub-resources: tags & timeline (Doc 04 §14.1) ------------------
@router.post(
    "/contacts/{contact_id}/tags",
    response_model=ContactResponse,
    summary="Add tags to a contact",
)
async def add_contact_tags(
    contact_id: uuidlib.UUID,
    payload: ContactTagsRequest,
    session: SessionDep,
    actor: ContactsWriteActor,
) -> ContactResponse:
    contact = await TagService(session).add_tags_to_contact(
        organization_id=actor.organization_id,
        actor=actor,
        contact_uuid=contact_id,
        tag_uuids=payload.tags,
    )
    return ContactResponse.from_contact(contact)


@router.delete(
    "/contacts/{contact_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a tag from a contact",
)
async def remove_contact_tag(
    contact_id: uuidlib.UUID,
    tag_id: uuidlib.UUID,
    session: SessionDep,
    actor: ContactsWriteActor,
) -> None:
    await TagService(session).remove_tag_from_contact(
        organization_id=actor.organization_id,
        actor=actor,
        contact_uuid=contact_id,
        tag_uuid=tag_id,
    )


@router.get(
    "/contacts/{contact_id}/timeline",
    response_model=ContactTimelinePage,
    summary="Contact activity timeline",
)
async def contact_timeline(
    contact_id: uuidlib.UUID,
    request: Request,
    session: SessionDep,
    actor: ContactsReadActor,
) -> ContactTimelinePage:
    contact = await ContactService(session).get_contact(actor.organization_id, contact_id)
    params = request.query_params
    limit = clamp_limit(params.get("limit"))
    raw_cursor = params.get("cursor")
    events, has_more, total = await ContactEventService(session).list_for_contact(
        contact.id,
        limit=limit,
        cursor=decode_cursor(raw_cursor) if raw_cursor else None,
        event_type=params.get("filter[event_type][eq]"),
    )
    next_cursor = (
        encode_cursor(events[-1].created_at, events[-1].id) if has_more and events else None
    )
    return ContactTimelinePage(
        data=[ContactEventResponse.from_event(e) for e in events],
        page=Page(limit=limit, has_more=has_more, next_cursor=next_cursor, total=total),
    )
