"""Contact CRUD endpoints (Doc 04 §14.1) — Module 2 foundation.

Reads require ``contacts:read``; writes require ``contacts:write`` (Owner superuser bypasses).
Contacts are organization-scoped. Listing supports keyset pagination, quick search (``q``),
filters (``filter[...]``), and whitelisted sorting. Import, export, bulk operations and duplicate
merge are async only: they return ``202`` with a poll URL and run on the Queue Engine.
"""

from __future__ import annotations

import base64
import json
import uuid as uuidlib
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from starlette.datastructures import QueryParams

from app.api.deps import SessionDep, require_permissions
from app.api.pagination import Page, clamp_limit, decode_cursor, encode_cursor
from app.core.config import settings
from app.core.exceptions import BadRequestError
from app.models.job_records import BulkJob
from app.models.user import User
from app.repositories.contact import ContactRepository
from app.schemas.attribute import ContactAttributesRequest
from app.schemas.bulk import (
    BulkDeleteRequest,
    BulkProgressResponse,
    BulkUpdateRequest,
    DeduplicateRequest,
)
from app.schemas.contact import (
    ContactCreateRequest,
    ContactResponse,
    ContactsPage,
    ContactUpdateRequest,
)
from app.schemas.contact_event import ContactEventResponse, ContactTimelinePage
from app.schemas.export_job import ExportCreateRequest, ExportProgressResponse
from app.schemas.import_job import (
    ImportCreateRequest,
    ImportInspectRequest,
    ImportInspectResponse,
    ImportProgressResponse,
    JobAcceptedResponse,
    JobEnvelope,
)
from app.schemas.search import ContactSearchRequest
from app.schemas.tag import ContactTagsRequest
from app.services.attribute_service import AttributeService
from app.services.bulk_service import BulkService
from app.services.contact_event_service import ContactEventService
from app.services.contact_search_service import ContactSearchService
from app.services.contact_service import ContactService
from app.services.export_service import ExportService
from app.services.import_service import ImportService
from app.services.tag_service import TagService

router = APIRouter()

ContactsReadActor = Annotated[User, Depends(require_permissions("contacts:read"))]
ContactsWriteActor = Annotated[User, Depends(require_permissions("contacts:write"))]
ContactsImportActor = Annotated[User, Depends(require_permissions("contacts:import"))]
ContactsExportActor = Annotated[User, Depends(require_permissions("contacts:export"))]

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


def _opt_in_filter(params: QueryParams) -> list[str] | None:
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


@router.post(
    "/contacts/search",
    response_model=ContactsPage,
    summary="Advanced AND/OR search (JSON body)",
)
async def search_contacts(
    payload: ContactSearchRequest, session: SessionDep, actor: ContactsReadActor
) -> ContactsPage:
    limit = clamp_limit(str(payload.limit) if payload.limit is not None else None)
    result = await ContactSearchService(session).search(
        actor.organization_id,
        match_type=payload.match_type,
        rules=[r.model_dump() for r in payload.rules],
        limit=limit,
        cursor=decode_cursor(payload.cursor) if payload.cursor else None,
    )
    next_cursor = (
        encode_cursor(result.contacts[-1].created_at, result.contacts[-1].id)
        if result.has_more and result.contacts
        else None
    )
    return ContactsPage(
        data=[ContactResponse.from_contact(c) for c in result.contacts],
        page=Page(
            limit=limit, has_more=result.has_more, next_cursor=next_cursor, total=result.total
        ),
    )


# --- Contact sub-resources: attributes, tags & timeline (Doc 04 §14.1) ------
@router.put(
    "/contacts/{contact_id}/attributes",
    response_model=ContactResponse,
    summary="Set custom attribute values",
)
async def set_contact_attributes(
    contact_id: uuidlib.UUID,
    payload: ContactAttributesRequest,
    session: SessionDep,
    actor: ContactsWriteActor,
) -> ContactResponse:
    contact = await AttributeService(session).set_contact_attributes(
        organization_id=actor.organization_id,
        actor=actor,
        contact_uuid=contact_id,
        values=payload.attributes,
    )
    return ContactResponse.from_contact(contact)


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


# --- Contact import (Doc 04 §14.1) — async only, always 202 -----------------
@router.post(
    "/contacts/import/inspect",
    response_model=ImportInspectResponse,
    summary="Read an uploaded file's columns before mapping (imports nothing)",
)
async def inspect_import(
    payload: ImportInspectRequest, session: SessionDep, actor: ContactsImportActor
) -> ImportInspectResponse:
    """Header row, one sample row and a size estimate for an already-uploaded file.

    Exists because `.xlsx` is a ZIP container: a browser cannot read its headers without shipping a
    second spreadsheet parser, and two parsers would be free to disagree about what a column is
    called. The server already parses workbooks for the import itself, so it answers the question
    with the same code (docs/adr/0002).
    """
    found = await ImportService(session).inspect(
        organization_id=actor.organization_id,
        upload_id=payload.upload_id,
        file_format=payload.format,
    )
    return ImportInspectResponse(
        headers=found.headers,
        sample_row=found.sample_row,
        sheet_name=found.sheet_name,
        estimated_rows=found.estimated_rows,
        errors=found.errors,
    )


@router.post(
    "/contacts/import",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a CSV import (async)",
)
async def start_import(
    payload: ImportCreateRequest, session: SessionDep, actor: ContactsImportActor
) -> JobAcceptedResponse:
    """Enqueue the import and return immediately — no bytes are parsed on this path."""
    from app.crm.tasks import run_contact_import

    job = await ImportService(session).start(
        organization_id=actor.organization_id,
        actor=actor,
        upload_id=payload.upload_id,
        file_format=payload.format,
        mapping=payload.mapping,
        dedup_strategy=payload.dedup_strategy,
        dispatch=lambda import_id, task_id: run_contact_import.apply_async(
            args=[import_id], task_id=task_id
        ),
    )
    return JobAcceptedResponse(
        job=JobEnvelope(
            id=job.public_id,
            type="import",
            status="queued",
            poll_url=f"{settings.api_v1_prefix}/contacts/import/{job.public_id}",
        )
    )


@router.get(
    "/contacts/import/{import_id}",
    response_model=ImportProgressResponse,
    summary="Import progress + error report link",
)
async def import_progress(
    import_id: uuidlib.UUID, session: SessionDep, actor: ContactsImportActor
) -> ImportProgressResponse:
    service = ImportService(session)
    job = await service.get(actor.organization_id, import_id)
    return ImportProgressResponse.from_job(job, await service.error_report_url(job))


# --- Contact export (Doc 04 §14.1) — async only, always 202 -----------------
@router.post(
    "/contacts/export",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start an export (async)",
)
async def start_export(
    payload: ExportCreateRequest, session: SessionDep, actor: ContactsExportActor
) -> JobAcceptedResponse:
    """Enqueue the export and return immediately — no contacts are read on this path."""
    from app.crm.tasks import run_contact_export

    job = await ExportService(session).start(
        organization_id=actor.organization_id,
        actor=actor,
        file_format=payload.format,
        match_type=payload.match_type,
        rules=[r.model_dump() for r in payload.rules],
        dispatch=lambda export_id, task_id: run_contact_export.apply_async(
            args=[export_id], task_id=task_id
        ),
    )
    return JobAcceptedResponse(
        job=JobEnvelope(
            id=job.public_id,
            type="export",
            status="queued",
            poll_url=f"{settings.api_v1_prefix}/contacts/export/{job.public_id}",
        )
    )


@router.get(
    "/contacts/export/{export_id}",
    response_model=ExportProgressResponse,
    summary="Export progress + signed download link",
)
async def export_progress(
    export_id: uuidlib.UUID, session: SessionDep, actor: ContactsExportActor
) -> ExportProgressResponse:
    service = ExportService(session)
    job = await service.get(actor.organization_id, export_id)
    return ExportProgressResponse.from_job(job, await service.download_url(job))


# --- Bulk operations & duplicate merge (Doc 04 §14.1/§30) — async only, always 202 ---
def _accepted(job: BulkJob) -> JobAcceptedResponse:
    return JobAcceptedResponse(
        job=JobEnvelope(
            id=job.public_id,
            type=job.operation,
            status="queued",
            poll_url=f"{settings.api_v1_prefix}/contacts/bulk/{job.public_id}",
        )
    )


@router.post(
    "/contacts/bulk-update",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Bulk edit tags/attributes over a selection or filter (async)",
)
async def bulk_update_contacts(
    payload: BulkUpdateRequest, session: SessionDep, actor: ContactsWriteActor
) -> JobAcceptedResponse:
    """Enqueue the edit and return immediately — no contact is touched on this path."""
    from app.crm.tasks import run_contact_bulk_update

    job = await BulkService(session).start_bulk_update(
        organization_id=actor.organization_id,
        actor=actor,
        action=payload.action,
        payload=payload.payload,
        ids=payload.ids,
        filters=payload.filter.model_dump() if payload.filter else None,
        expected_count=payload.expected_count,
        dispatch=lambda bulk_id, task_id: run_contact_bulk_update.apply_async(
            args=[bulk_id], task_id=task_id
        ),
    )
    return _accepted(job)


@router.post(
    "/contacts/bulk-delete",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Bulk soft-delete over a selection or filter (async)",
)
async def bulk_delete_contacts(
    payload: BulkDeleteRequest, session: SessionDep, actor: ContactsWriteActor
) -> JobAcceptedResponse:
    from app.crm.tasks import run_contact_bulk_delete

    job = await BulkService(session).start_bulk_delete(
        organization_id=actor.organization_id,
        actor=actor,
        ids=payload.ids,
        filters=payload.filter.model_dump() if payload.filter else None,
        expected_count=payload.expected_count,
        dispatch=lambda bulk_id, task_id: run_contact_bulk_delete.apply_async(
            args=[bulk_id], task_id=task_id
        ),
    )
    return _accepted(job)


@router.post(
    "/contacts/deduplicate",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Run a duplicate scan — report or merge (async)",
)
async def deduplicate_contacts(
    payload: DeduplicateRequest, session: SessionDep, actor: ContactsWriteActor
) -> JobAcceptedResponse:
    from app.crm.tasks import run_contact_deduplicate

    job = await BulkService(session).start_deduplicate(
        organization_id=actor.organization_id,
        actor=actor,
        keys=payload.keys,
        mode=payload.mode,
        dispatch=lambda bulk_id, task_id: run_contact_deduplicate.apply_async(
            args=[bulk_id], task_id=task_id
        ),
    )
    return _accepted(job)


@router.get(
    "/contacts/bulk/{bulk_id}",
    response_model=BulkProgressResponse,
    summary="Bulk job progress + partial-success result",
)
async def bulk_progress(
    bulk_id: uuidlib.UUID, session: SessionDep, actor: ContactsWriteActor
) -> BulkProgressResponse:
    """The §29 partial-success envelope.

    Bulk progress lives here rather than on ``GET /jobs/{uuid}`` (Doc 04 §30): that surface is
    gated by ``system:read`` (§22) and ``job_metadata`` carries no organization, so it can serve
    neither a ``contacts:write`` operator nor tenant scoping. This mirrors the import/export
    poll endpoints §14.1 already defines.
    """
    service = BulkService(session)
    job = await service.get(actor.organization_id, bulk_id)
    return BulkProgressResponse.from_job(job, await service.error_report_url(job))
