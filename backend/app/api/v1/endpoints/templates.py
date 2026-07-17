"""Template endpoints (Doc 04 §15) — Module 5, template registry.

Reads require ``templates:read``, writes ``templates:write``, sync ``templates:sync``.

Two contract details worth stating: **create is a Meta round-trip** unless held as a draft, so a
channel failure surfaces as ``502``; and **sync is async** (``202`` + job), because reconciling a
WABA's templates cannot block a request.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import SessionDep, require_permissions
from app.api.v1.endpoints.waba import ChannelUnavailableError
from app.channels.errors import ChannelError
from app.core.config import settings
from app.models.user import User
from app.schemas.import_job import JobAcceptedResponse, JobEnvelope
from app.schemas.template import (
    TemplateCreateRequest,
    TemplateListResponse,
    TemplatePreviewResponse,
    TemplateResponse,
    TemplateUpdateRequest,
    TemplateVersionEntry,
    TemplateVersionsResponse,
)
from app.services.template_service import TemplateService

router = APIRouter()

TemplateReader = Annotated[User, Depends(require_permissions("templates:read"))]
TemplateWriter = Annotated[User, Depends(require_permissions("templates:write"))]
TemplateSyncer = Annotated[User, Depends(require_permissions("templates:sync"))]


async def _render(service: TemplateService, template) -> TemplateResponse:
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
    request: Request,
    session: SessionDep,
    actor: TemplateReader,
) -> TemplatePreviewResponse:
    """Pure render (FR-TPL-08): nothing is stored and nothing is sent.

    Sample values ride the query string (`?body=Priya&body=%231234`) because Doc 04 §15 makes this
    a `GET` — it is a projection of the template, not a change to it.
    """
    service = TemplateService(session)
    template = await service.get_template(actor.organization_id, template_id)
    return TemplatePreviewResponse(
        **await service.preview(
            template,
            header=request.query_params.getlist("header"),
            body=request.query_params.getlist("body"),
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
