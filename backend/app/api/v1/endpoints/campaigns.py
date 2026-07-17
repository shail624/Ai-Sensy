"""Campaign endpoints (Doc 04 §17) — Phase 6 Step 1: registry & audience.

Reads require ``campaigns:read``, writes ``campaigns:write``.

Only the draft lifecycle exists here: create, edit, delete, preview and read the roster. Sending,
scheduling and lifecycle control are later steps, so the endpoints that trigger them are not
mounted rather than stubbed — a route that returns "not implemented" is worse than a 404, because
it implies the feature is nearly there.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import SessionDep, require_permissions
from app.api.pagination import decode_cursor
from app.models.user import User
from app.schemas.campaign import (
    CampaignCreateRequest,
    CampaignListResponse,
    CampaignPreviewResponse,
    CampaignResponse,
    CampaignUpdateRequest,
    RecipientEntry,
    RecipientsResponse,
)
from app.services.campaign_service import CampaignService

router = APIRouter()

CampaignReader = Annotated[User, Depends(require_permissions("campaigns:read"))]
CampaignWriter = Annotated[User, Depends(require_permissions("campaigns:write"))]

#: How many sample renders a preview returns (Doc 04 §17 "sample renders").
PREVIEW_SAMPLES = 5
RECIPIENT_PAGE = 50


async def _render(service: CampaignService, campaign) -> CampaignResponse:
    number_id, template_id = await service.refs(campaign)
    return CampaignResponse.from_campaign(
        campaign, number_public_id=number_id, template_public_id=template_id
    )


@router.get("/campaigns", response_model=CampaignListResponse, summary="List campaigns")
async def list_campaigns(
    request: Request, session: SessionDep, actor: CampaignReader
) -> CampaignListResponse:
    params = request.query_params
    service = CampaignService(session)
    campaigns = await service.list_campaigns(
        actor.organization_id,
        status=params.get("filter[status][eq]") or params.get("status"),
        q=params.get("q"),
    )
    return CampaignListResponse(data=[await _render(service, c) for c in campaigns])


@router.post(
    "/campaigns",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft campaign",
)
async def create_campaign(
    payload: CampaignCreateRequest, session: SessionDep, actor: CampaignWriter
) -> CampaignResponse:
    """Creates the draft **and** materializes its roster, so the response counts are real."""
    service = CampaignService(session)
    campaign = await service.create(
        organization_id=actor.organization_id,
        actor=actor,
        name=payload.name,
        number_public_id=payload.phone_number_id,
        template_public_id=payload.template_id,
        audience_type=payload.audience_type,
        audience_ref=payload.audience_ref.model_dump(mode="json", exclude_none=True),
        variable_map=payload.variable_map.model_dump(mode="json"),
    )
    return await _render(service, campaign)


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse, summary="Get a campaign")
async def get_campaign(
    campaign_id: uuidlib.UUID, session: SessionDep, actor: CampaignReader
) -> CampaignResponse:
    service = CampaignService(session)
    return await _render(service, await service.get_campaign(actor.organization_id, campaign_id))


@router.patch(
    "/campaigns/{campaign_id}", response_model=CampaignResponse, summary="Edit a draft campaign"
)
async def update_campaign(
    campaign_id: uuidlib.UUID,
    payload: CampaignUpdateRequest,
    session: SessionDep,
    actor: CampaignWriter,
) -> CampaignResponse:
    provided = payload.model_dump(mode="json", exclude_unset=True)
    provided.pop("row_version", None)
    number = provided.pop("phone_number_id", None)
    template = provided.pop("template_id", None)
    fields = {}
    if "name" in provided:
        fields["name"] = provided["name"]
    if "audience_type" in provided:
        fields["audience_type"] = provided["audience_type"]
    if "audience_ref" in provided:
        fields["audience_ref_json"] = {
            k: v for k, v in (provided["audience_ref"] or {}).items() if v not in (None, [])
        }
    if "variable_map" in provided:
        fields["variable_map_json"] = provided["variable_map"]

    service = CampaignService(session)
    campaign = await service.update(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=campaign_id,
        fields=fields,
        number_public_id=uuidlib.UUID(number) if number else None,
        template_public_id=uuidlib.UUID(template) if template else None,
        expected_version=payload.row_version,
    )
    return await _render(service, campaign)


@router.delete(
    "/campaigns/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a draft campaign",
)
async def delete_campaign(
    campaign_id: uuidlib.UUID, session: SessionDep, actor: CampaignWriter
) -> None:
    await CampaignService(session).delete(
        organization_id=actor.organization_id, actor=actor, public_id=campaign_id
    )


@router.post(
    "/campaigns/{campaign_id}/preview",
    response_model=CampaignPreviewResponse,
    summary="Resolve audience size + sample renders",
)
async def preview_campaign(
    campaign_id: uuidlib.UUID, session: SessionDep, actor: CampaignReader
) -> CampaignPreviewResponse:
    """Reads the materialized roster: the preview shows what will be sent, not a fresh query."""
    preview = await CampaignService(session).preview(
        organization_id=actor.organization_id, public_id=campaign_id, samples=PREVIEW_SAMPLES
    )
    return CampaignPreviewResponse(
        total=preview.total,
        excluded_opted_out=preview.excluded_opted_out,
        samples=preview.samples,
    )


@router.get(
    "/campaigns/{campaign_id}/recipients",
    response_model=RecipientsResponse,
    summary="Per-recipient status (paginated)",
)
async def campaign_recipients(
    campaign_id: uuidlib.UUID,
    request: Request,
    session: SessionDep,
    actor: CampaignReader,
) -> RecipientsResponse:
    service = CampaignService(session)
    campaign = await service.get_campaign(actor.organization_id, campaign_id)
    raw_cursor = request.query_params.get("cursor")
    rows, has_more, contacts = await service.recipients(
        campaign,
        status=request.query_params.get("filter[status][eq]")
        or request.query_params.get("status"),
        limit=RECIPIENT_PAGE,
        cursor=decode_cursor(raw_cursor) if raw_cursor else None,
    )
    return RecipientsResponse(
        data=[RecipientEntry.from_recipient(r, contacts.get(r.contact_id)) for r in rows],
        has_more=has_more,
    )
