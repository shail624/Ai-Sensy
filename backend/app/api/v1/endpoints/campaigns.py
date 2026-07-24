"""Campaign endpoints (Doc 04 §17) — draft lifecycle, audience, dispatch, control and scheduling.

Reads require ``campaigns:read``, writes ``campaigns:write``.

Dispatch answers ``202``: the campaign is validated and handed to ``campaigns.control``, which
batches the roster and fans it out. Nothing is sent on the request path.

Scheduling answers ``200`` and sends nothing either — it writes the row that ``scheduler.tick``
will find when it comes due (Doc 06 §10.2: the database is the schedule, Beat is the heartbeat).
"""

from __future__ import annotations

import uuid as uuidlib
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import SessionDep, require_permissions
from app.api.pagination import decode_cursor
from app.core.config import settings
from app.models.campaign import Campaign
from app.models.user import User
from app.schemas.campaign import (
    CampaignCreateRequest,
    CampaignDispatchResponse,
    CampaignEstimateResponse,
    CampaignListResponse,
    CampaignPreviewResponse,
    CampaignProgressResponse,
    CampaignResponse,
    CampaignRetryResponse,
    CampaignScheduleRequest,
    CampaignScheduleResponse,
    CampaignStateResponse,
    CampaignUpdateRequest,
    RecipientEntry,
    RecipientsResponse,
    ScheduleEntry,
)
from app.services.campaign_dispatch_service import CampaignDispatchService
from app.services.campaign_lifecycle_service import CampaignLifecycleService
from app.services.campaign_schedule_service import CampaignScheduleService
from app.services.campaign_service import CampaignService
from app.services.cost_estimation_service import CostEstimationService

router = APIRouter()

CampaignReader = Annotated[User, Depends(require_permissions("campaigns:read"))]
CampaignWriter = Annotated[User, Depends(require_permissions("campaigns:write"))]
CampaignSender = Annotated[User, Depends(require_permissions("campaigns:send"))]
CampaignManager = Annotated[User, Depends(require_permissions("campaigns:manage"))]

#: How many sample renders a preview returns (Doc 04 §17 "sample renders").
PREVIEW_SAMPLES = 5
RECIPIENT_PAGE = 50


async def _render(service: CampaignService, campaign: Campaign) -> CampaignResponse:
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


@router.post(
    "/campaigns/{campaign_id}/estimate-cost",
    response_model=CampaignEstimateResponse,
    summary="Pre-send cost estimate from the rate card",
)
async def estimate_campaign_cost(
    campaign_id: uuidlib.UUID, session: SessionDep, actor: CampaignReader
) -> CampaignEstimateResponse:
    """Price the materialized roster from the rate card (FR-CAM-11; Doc 04 §17).

    No body: the estimate is derived from what would actually be sent, not a fresh audience query.
    An empty or incomplete card answers `422 rate_card_not_configured` rather than a misleading
    partial total. The endpoint stays on `campaigns:read` because its only write is caching the
    quote on the campaign's own row (Doc 03 §8.5.5)."""
    estimate = await CostEstimationService(session).estimate(
        organization_id=actor.organization_id, public_id=campaign_id
    )
    return CampaignEstimateResponse.from_estimate(estimate)


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


@router.post(
    "/campaigns/{campaign_id}/dispatch",
    response_model=CampaignDispatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Dispatch a campaign (async)",
)
async def dispatch_campaign(
    campaign_id: uuidlib.UUID, session: SessionDep, actor: CampaignSender
) -> CampaignDispatchResponse:
    """Validate and enqueue. The template and number are re-checked here, not just at create:
    Meta may have paused the template since the draft was written."""
    from app.crm.campaign_tasks import dispatch_campaign as dispatch_task

    campaign = await CampaignDispatchService(session).start(
        organization_id=actor.organization_id, actor=actor, public_id=campaign_id
    )
    # After the commit, never before: the task must not outrun the row it reads.
    dispatch_task.apply_async(args=[campaign.id])
    return CampaignDispatchResponse(
        id=campaign.public_id,
        status=campaign.status,
        total_recipients=campaign.total_recipients,
        progress_url=f"{settings.api_v1_prefix}/campaigns/{campaign.public_id}/progress",
    )


@router.post(
    "/campaigns/{campaign_id}/schedule",
    response_model=CampaignScheduleResponse,
    summary="Schedule a campaign (one-time/recurring/drip)",
)
async def schedule_campaign(
    campaign_id: uuidlib.UUID,
    payload: CampaignScheduleRequest,
    session: SessionDep,
    actor: CampaignSender,
) -> CampaignScheduleResponse:
    """Write the schedule and park the campaign in ``scheduled``. Nothing fires on this path:
    ``scheduler.tick`` reads the row when it comes due (Doc 06 §10.2 — the DB is the schedule)."""
    campaign, schedules = await CampaignScheduleService(session).schedule(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=campaign_id,
        schedule_type=payload.schedule_type,
        run_at=payload.run_at,
        cron_expr=payload.cron_expr,
        timezone=payload.timezone,
        starts_on=payload.starts_on,
        ends_on=payload.ends_on,
        starts_at=payload.starts_at,
        steps=payload.steps,
    )
    return CampaignScheduleResponse(
        id=campaign.public_id,
        status=campaign.status,
        schedules=[ScheduleEntry.from_schedule(s) for s in schedules],
    )


@router.get(
    "/campaigns/{campaign_id}/progress",
    response_model=CampaignProgressResponse,
    summary="Live campaign progress",
)
async def campaign_progress(
    campaign_id: uuidlib.UUID, session: SessionDep, actor: CampaignReader
) -> CampaignProgressResponse:
    progress = await CampaignDispatchService(session).progress(actor.organization_id, campaign_id)
    return CampaignProgressResponse(**asdict(progress))


@router.post(
    "/campaigns/{campaign_id}/pause",
    response_model=CampaignStateResponse,
    summary="Pause a running campaign",
)
async def pause_campaign(
    campaign_id: uuidlib.UUID, session: SessionDep, actor: CampaignManager
) -> CampaignStateResponse:
    """Flips the switch every send reads. In-flight tasks are not chased — they will decline."""
    campaign = await CampaignLifecycleService(session).pause(
        organization_id=actor.organization_id, actor=actor, public_id=campaign_id
    )
    return CampaignStateResponse.from_campaign(campaign)


@router.post(
    "/campaigns/{campaign_id}/resume",
    response_model=CampaignStateResponse,
    summary="Resume a paused campaign",
)
async def resume_campaign(
    campaign_id: uuidlib.UUID, session: SessionDep, actor: CampaignManager
) -> CampaignStateResponse:
    """Re-dispatches; planning only ever picks up what still owes a send, so nothing repeats."""
    from app.crm.campaign_tasks import dispatch_campaign as dispatch_task

    campaign = await CampaignLifecycleService(session).resume(
        organization_id=actor.organization_id, actor=actor, public_id=campaign_id
    )
    dispatch_task.apply_async(args=[campaign.id])
    return CampaignStateResponse.from_campaign(campaign)


@router.post(
    "/campaigns/{campaign_id}/cancel",
    response_model=CampaignStateResponse,
    summary="Cancel a campaign and stop pending sends",
)
async def cancel_campaign(
    campaign_id: uuidlib.UUID, session: SessionDep, actor: CampaignManager
) -> CampaignStateResponse:
    campaign = await CampaignLifecycleService(session).cancel(
        organization_id=actor.organization_id, actor=actor, public_id=campaign_id
    )
    return CampaignStateResponse.from_campaign(campaign)


@router.post(
    "/campaigns/{campaign_id}/retry",
    response_model=CampaignRetryResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Retry failed recipients",
)
async def retry_campaign(
    campaign_id: uuidlib.UUID, session: SessionDep, actor: CampaignSender
) -> CampaignRetryResponse:
    """Resets failed recipients and re-dispatches; the retry engine judges each attempt afresh."""
    from app.crm.campaign_tasks import dispatch_campaign as dispatch_task

    campaign, retried = await CampaignLifecycleService(session).retry_failed(
        organization_id=actor.organization_id, actor=actor, public_id=campaign_id
    )
    dispatch_task.apply_async(args=[campaign.id])
    return CampaignRetryResponse(
        id=campaign.public_id, status=campaign.status, retried=len(retried)
    )
