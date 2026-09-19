"""Template endpoints (Doc 04 §15) — Module 5, template registry.

Reads require ``templates:read``, writes ``templates:write``, sync ``templates:sync``.

Two contract details worth stating: **create is a Meta round-trip** unless held as a draft, so a
channel failure surfaces as ``502``; and **sync is async** (``202`` + job), because reconciling a
WABA's templates cannot block a request.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import SessionDep, require_permissions
from app.api.v1.endpoints.waba import ChannelUnavailableError
from app.channels.errors import ChannelError
from app.core.config import settings
from app.models.template import MessageTemplate
from app.models.user import User
from app.repositories.template_usage import TemplateUsageRepository
from app.schemas.import_job import JobAcceptedResponse, JobEnvelope
from app.schemas.template import (
    TemplateCreateRequest,
    TemplateListResponse,
    TemplatePreviewResponse,
    TemplateResponse,
    TemplateUpdateRequest,
    TemplateUsageListResponse,
    TemplateUsageResponse,
    TemplateVersionEntry,
    TemplateVersionsResponse,
)
from app.services.template_service import TemplateService

router = APIRouter()

TemplateReader = Annotated[User, Depends(require_permissions("templates:read"))]
TemplateWriter = Annotated[User, Depends(require_permissions("templates:write"))]
TemplateSyncer = Annotated[User, Depends(require_permissions("templates:sync"))]


async def _render(service: TemplateService, template: MessageTemplate) -> TemplateResponse:
    return TemplateResponse.from_template(
        template, waba_public_id=await service.waba_public_id(template)
    )


@router.get("/templates", response_model=TemplateListResponse, summary="List templates")
async def list_templates(
    request: Request, session: SessionDep, actor: TemplateReader
) -> TemplateListResponse:
    params = request.query_params
    raw_waba = params.get("filter[waba][eq]") or params.get("waba")
    service = TemplateService(session)
    templates = await service.list_templates(
        actor.organization_id,
        waba_uuid=uuidlib.UUID(raw_waba) if raw_waba else None,
        status=params.get("filter[status][eq]") or params.get("status"),
        category=params.get("filter[category][eq]") or params.get("category"),
        language=params.get("filter[language][eq]") or params.get("language"),
        q=params.get("q"),
    )
    return TemplateListResponse(data=[await _render(service, t) for t in templates])


@router.post(
    "/templates",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and submit a template",
)
async def create_template(
    payload: TemplateCreateRequest, session: SessionDep, actor: TemplateWriter
) -> TemplateResponse:
    service = TemplateService(session)
    try:
        template = await service.create(
            organization_id=actor.organization_id,
            actor=actor,
            waba_public_id=payload.waba_id,
            name=payload.name,
            language=payload.language,
            category=payload.category,
            components=payload.components,
            submit=payload.submit,
        )
    except ChannelError as exc:
        raise ChannelUnavailableError(str(exc)) from exc
    return await _render(service, template)


@router.post(
    "/templates/sync",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Sync templates + statuses from Meta (async)",
)
async def sync_templates(
    request: Request, session: SessionDep, actor: TemplateSyncer
) -> JobAcceptedResponse:
    """Enqueue the sync and return immediately — no Meta call on this path."""
    from app.channels.tasks import run_template_sync

    raw_waba = request.query_params.get("waba")
    job_id = await TemplateService(session).start_sync(
        organization_id=actor.organization_id,
        actor=actor,
        waba_public_id=uuidlib.UUID(raw_waba) if raw_waba else None,
        dispatch=lambda wabas, task_id: run_template_sync.apply_async(
            args=[wabas], task_id=task_id
        ),
    )
    return JobAcceptedResponse(
        job=JobEnvelope(
            id=job_id,
            type="template_sync",
            status="queued",
            poll_url=f"{settings.api_v1_prefix}/jobs/{job_id}",
        )
    )


@router.get(
    "/templates/usage",
    response_model=TemplateUsageListResponse,
    summary="How each template has actually performed",
)
async def template_usage(session: SessionDep, actor: TemplateReader) -> TemplateUsageListResponse:
    """Campaigns sent, people reached, delivered, failed and when each template was last used.

    Templates are chosen by name today, which means they are chosen by memory. Every one of these
    numbers was already in `campaigns` and `campaign_recipients`; nothing read them per template.

    Aggregates only: "which template works" is a template question, and answering it names no
    customer and no campaign. A template nobody has sent is listed with zeros rather than omitted,
    because an unused template is either new or quietly broken and its absence from the list is the
    thing most worth seeing.

    Counts what was sent, not what was planned. A campaign materialises its entire roster the
    moment it is created, while it is still a draft, so an unfinished draft puts rows in the ledger
    for sends nobody has authorised. Those are not campaigns here, not recipients, and do not make
    the template look recently used — a template delivering to everyone must not read as a failure
    because a colleague is midway through drafting a large campaign with it.

    Declared before `/templates/{template_id}` so "usage" is not read as an identifier.
    """
    usage = await TemplateUsageRepository(session).list_usage(actor.organization_id)
    return TemplateUsageListResponse(
        data=[TemplateUsageResponse.from_usage(row) for row in usage]
    )


@router.get("/templates/{template_id}", response_model=TemplateResponse, summary="Get a template")
async def get_template(
    template_id: uuidlib.UUID, session: SessionDep, actor: TemplateReader
) -> TemplateResponse:
    service = TemplateService(session)
    return await _render(service, await service.get_template(actor.organization_id, template_id))


@router.patch(
    "/templates/{template_id}", response_model=TemplateResponse, summary="Edit a draft template"
)
async def update_template(
    template_id: uuidlib.UUID,
    payload: TemplateUpdateRequest,
    session: SessionDep,
    actor: TemplateWriter,
) -> TemplateResponse:
    service = TemplateService(session)
    try:
        template = await service.update(
            organization_id=actor.organization_id,
            actor=actor,
            public_id=template_id,
            category=payload.category,
            components=payload.components,
            submit=payload.submit,
            expected_version=payload.row_version,
        )
    except ChannelError as exc:
        raise ChannelUnavailableError(str(exc)) from exc
    return await _render(service, template)


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a template (local + Meta)",
)
async def delete_template(
    template_id: uuidlib.UUID, session: SessionDep, actor: TemplateWriter
) -> None:
    try:
        await TemplateService(session).delete(
            organization_id=actor.organization_id, actor=actor, public_id=template_id
        )
    except ChannelError as exc:
        raise ChannelUnavailableError(str(exc)) from exc


@router.get(
    "/templates/{template_id}/preview",
    response_model=TemplatePreviewResponse,
    summary="Render with sample variables",
)
async def preview_template(
    template_id: uuidlib.UUID,
    session: SessionDep,
    actor: TemplateReader,
    header: Annotated[
        list[str] | None,
        Query(description="Sample values for the header's variables, in order."),
    ] = None,
    body: Annotated[
        list[str] | None,
        Query(description="Sample values for the body's variables, in order."),
    ] = None,
    button: Annotated[
        list[str] | None,
        Query(description="Sample values for the buttons that take one, in button order."),
    ] = None,
) -> TemplatePreviewResponse:
    """Pure render (FR-TPL-08): nothing is stored and nothing is sent.

    Sample values ride the query string (`?body=Priya&body=%231234&button=TXN9931`) because Doc 04
    §15 makes this a `GET` — it is a projection of the template, not a change to it.

    They are declared as parameters rather than read off the raw request. Read raw they worked, but
    they were absent from the published contract, so the generated client could not send them and
    no screen ever did: the endpoint had a sample-value feature that nothing could reach.

    Buttons are rendered with the text, and their destinations with them. A URL button carries its
    variable inside the link — `https://vi.in/pay/{{1}}` — which appears on no other screen, so a
    variable mapped to the wrong column is invisible right up until a customer taps it. By then the
    same link has gone to everyone in the campaign.

    `expects` says how many values each part takes, so a caller can offer exactly that many boxes
    without re-implementing Meta's numbering rules in a second place.
    """
    service = TemplateService(session)
    template = await service.get_template(actor.organization_id, template_id)
    return TemplatePreviewResponse(
        **await service.preview(
            template, header=header or [], body=body or [], buttons=button or []
        )
    )


@router.get(
    "/templates/{template_id}/versions",
    response_model=TemplateVersionsResponse,
    summary="Version history",
)
async def template_versions(
    template_id: uuidlib.UUID, session: SessionDep, actor: TemplateReader
) -> TemplateVersionsResponse:
    service = TemplateService(session)
    template = await service.get_template(actor.organization_id, template_id)
    return TemplateVersionsResponse(
        data=[TemplateVersionEntry.from_version(v) for v in await service.versions(template)]
    )
