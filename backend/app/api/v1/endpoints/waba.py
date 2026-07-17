"""WABA & phone-number endpoints (Doc 04 §13.2/§13.3) — Module 4 Step 2.

Reads require ``waba:read``; writes require ``waba:manage`` (Owner superuser bypasses). Everything
is organization-scoped.

Two contract details worth stating: the system-user **token is write-only** — accepted here, never
rendered back (`token_set` says only whether one exists) — and **sync is async** (`202` + job),
because reconciling numbers is a Meta round-trip that must not block a request. A channel failure
surfaces as ``502`` per Doc 04 §13.2/§13.3.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import SessionDep, require_permissions
from app.channels.errors import ChannelError
from app.core.config import settings
from app.core.exceptions import AppError
from app.models.user import User
from app.schemas.import_job import JobAcceptedResponse, JobEnvelope
from app.schemas.waba import (
    PhoneNumberHealthResponse,
    PhoneNumberResponse,
    PhoneNumbersListResponse,
    PhoneNumberUpdateRequest,
    WabaCreateRequest,
    WabaListResponse,
    WabaResponse,
    WabaUpdateRequest,
)
from app.services.phone_number_service import PhoneNumberService
from app.services.waba_service import WabaService

router = APIRouter()

WabaReadActor = Annotated[User, Depends(require_permissions("waba:read"))]
WabaManageActor = Annotated[User, Depends(require_permissions("waba:manage"))]


class ChannelUnavailableError(AppError):
    """A channel call failed — the platform is fine, Meta (or the credentials) is not."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "channel_error"
    title = "Channel Error"


# --- WABAs (Doc 04 §13.2) ----------------------------------------------------
@router.get("/waba", response_model=WabaListResponse, summary="List connected WABAs")
async def list_wabas(session: SessionDep, actor: WabaReadActor) -> WabaListResponse:
    pairs = await WabaService(session).list_wabas(actor.organization_id)
    return WabaListResponse(
        data=[WabaResponse.from_waba(waba, phone_number_count=count) for waba, count in pairs]
    )


@router.post(
    "/waba",
    response_model=WabaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Connect a WABA",
)
async def connect_waba(
    payload: WabaCreateRequest, session: SessionDep, actor: WabaManageActor
) -> WabaResponse:
    waba = await WabaService(session).connect(
        organization_id=actor.organization_id,
        actor=actor,
        waba_id=payload.waba_id,
        business_name=payload.business_name,
        access_token=payload.access_token,
        meta_business_id=payload.meta_business_id,
        currency=payload.currency,
        timezone=payload.timezone,
        token_expires_at=payload.token_expires_at,
    )
    return WabaResponse.from_waba(waba, phone_number_count=0)


@router.get("/waba/{waba_id}", response_model=WabaResponse, summary="Get a WABA")
async def get_waba(
    waba_id: uuidlib.UUID, session: SessionDep, actor: WabaReadActor
) -> WabaResponse:
    service = WabaService(session)
    waba = await service.get_waba(actor.organization_id, waba_id)
    return WabaResponse.from_waba(waba, phone_number_count=await service.number_count(waba))


@router.patch("/waba/{waba_id}", response_model=WabaResponse, summary="Update or rotate a WABA")
async def update_waba(
    waba_id: uuidlib.UUID,
    payload: WabaUpdateRequest,
    session: SessionDep,
    actor: WabaManageActor,
) -> WabaResponse:
    provided = payload.model_dump(exclude_unset=True)
    provided.pop("row_version", None)
    access_token = provided.pop("access_token", None)
    service = WabaService(session)
    waba = await service.update(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=waba_id,
        fields=provided,
        access_token=access_token,
        expected_version=payload.row_version,
    )
    return WabaResponse.from_waba(waba, phone_number_count=await service.number_count(waba))


@router.delete(
    "/waba/{waba_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect a WABA",
)
async def disconnect_waba(
    waba_id: uuidlib.UUID, session: SessionDep, actor: WabaManageActor
) -> None:
    await WabaService(session).disconnect(
        organization_id=actor.organization_id, actor=actor, public_id=waba_id
    )


@router.post(
    "/waba/{waba_id}/sync",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Pull phone numbers from Meta (async)",
)
async def sync_waba(
    waba_id: uuidlib.UUID, session: SessionDep, actor: WabaManageActor
) -> JobAcceptedResponse:
    """Enqueue the sync and return immediately — no Meta call on this path."""
    from app.channels.tasks import run_waba_sync

    _, job_id = await WabaService(session).start_sync(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=waba_id,
        dispatch=lambda waba_public_id, task_id: run_waba_sync.apply_async(
            args=[waba_public_id], task_id=task_id
        ),
    )
    return JobAcceptedResponse(
        job=JobEnvelope(
            id=job_id,
            type="waba_sync",
            status="queued",
            # Job progress is the operations surface (Doc 04 §22); `GET /waba/{id}` and
            # `/phone-numbers` show the reconciled result.
            poll_url=f"{settings.api_v1_prefix}/jobs/{job_id}",
        )
    )


# --- Phone numbers (Doc 04 §13.3) -------------------------------------------
@router.get(
    "/phone-numbers", response_model=PhoneNumbersListResponse, summary="List phone numbers"
)
async def list_phone_numbers(
    request: Request, session: SessionDep, actor: WabaReadActor
) -> PhoneNumbersListResponse:
    params = request.query_params
    raw_waba = params.get("filter[waba][eq]") or params.get("waba")
    service = PhoneNumberService(session)
    numbers = await service.list_numbers(
        actor.organization_id,
        waba_uuid=uuidlib.UUID(raw_waba) if raw_waba else None,
        status=params.get("filter[status][eq]"),
        quality_rating=params.get("filter[quality_rating][eq]"),
    )
    return PhoneNumbersListResponse(
        data=[
            PhoneNumberResponse.from_number(n, waba_public_id=await service.waba_public_id(n))
            for n in numbers
        ]
    )


@router.get(
    "/phone-numbers/{number_id}", response_model=PhoneNumberResponse, summary="Get a phone number"
)
async def get_phone_number(
    number_id: uuidlib.UUID, session: SessionDep, actor: WabaReadActor
) -> PhoneNumberResponse:
    service = PhoneNumberService(session)
    number = await service.get_number(actor.organization_id, number_id)
    return PhoneNumberResponse.from_number(
        number, waba_public_id=await service.waba_public_id(number)
    )


@router.patch(
    "/phone-numbers/{number_id}",
    response_model=PhoneNumberResponse,
    summary="Update a phone number (default flag, mps limit, name)",
)
async def update_phone_number(
    number_id: uuidlib.UUID,
    payload: PhoneNumberUpdateRequest,
    session: SessionDep,
    actor: WabaManageActor,
) -> PhoneNumberResponse:
    provided = payload.model_dump(exclude_unset=True)
    provided.pop("row_version", None)
    service = PhoneNumberService(session)
    number = await service.update(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=number_id,
        fields=provided,
        expected_version=payload.row_version,
    )
    return PhoneNumberResponse.from_number(
        number, waba_public_id=await service.waba_public_id(number)
    )


@router.get(
    "/phone-numbers/{number_id}/health",
    response_model=PhoneNumberHealthResponse,
    summary="Quality rating, messaging tier & limits",
)
async def phone_number_health(
    number_id: uuidlib.UUID, session: SessionDep, actor: WabaReadActor
) -> PhoneNumberHealthResponse:
    """Stored health — cheap and always available. Use ``/refresh`` to re-pull from Meta."""
    number = await PhoneNumberService(session).get_number(actor.organization_id, number_id)
    return PhoneNumberHealthResponse.from_number(number)


@router.post(
    "/phone-numbers/{number_id}/refresh",
    response_model=PhoneNumberHealthResponse,
    summary="Re-pull health/limits from Meta",
)
async def refresh_phone_number(
    number_id: uuidlib.UUID, session: SessionDep, actor: WabaManageActor
) -> PhoneNumberHealthResponse:
    try:
        number = await PhoneNumberService(session).refresh(
            organization_id=actor.organization_id, actor=actor, public_id=number_id
        )
    except ChannelError as exc:
        # The channel failed, not the request (Doc 04 §13.3 → 502).
        raise ChannelUnavailableError(str(exc)) from exc
    return PhoneNumberHealthResponse.from_number(number)
