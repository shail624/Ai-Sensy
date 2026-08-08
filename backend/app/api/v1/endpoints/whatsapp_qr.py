"""QR-07 — WhatsApp Scan/Connect API.

Thin HTTP layer over :class:`~app.services.whatsapp_qr_service.WhatsAppQrService`. Every response
is provider-neutral; the QR image is the only binary response and is served with ``no-store``
caching so neither a browser cache nor an intermediary retains it.
"""

from __future__ import annotations

import dataclasses
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.deps import ChannelFoundationDep, SessionDep, require_permissions
from app.channels.waha import WahaQrChallenge
from app.models.user import User
from app.schemas.whatsapp_qr import WhatsAppQrLogoutRequest, WhatsAppQrStatus
from app.services.whatsapp_qr_service import OPERATE_PERMISSION, READ_PERMISSION, WhatsAppQrService

router = APIRouter(prefix="/channels/whatsapp-qr", tags=["WhatsApp QR Connection"])

Reader = Annotated[User, Depends(require_permissions(READ_PERMISSION))]
Operator = Annotated[User, Depends(require_permissions(OPERATE_PERMISSION))]


def _service(session: SessionDep, foundation: ChannelFoundationDep) -> WhatsAppQrService:
    return WhatsAppQrService(
        session, providers=foundation.providers, runtimes=foundation.runtimes
    )


@router.get("/session", response_model=WhatsAppQrStatus, summary="Get WhatsApp QR connection status")
async def get_session_status(
    session: SessionDep,
    actor: Reader,
    foundation: ChannelFoundationDep,
) -> WhatsAppQrStatus:
    service = _service(session, foundation)
    state = await service.get_status(organization_id=actor.organization_id, actor=actor)
    return WhatsAppQrStatus(**dataclasses.asdict(state))


@router.post(
    "/session/connect", response_model=WhatsAppQrStatus, summary="Start a WhatsApp QR connection"
)
async def connect(
    session: SessionDep,
    actor: Operator,
    foundation: ChannelFoundationDep,
) -> WhatsAppQrStatus:
    service = _service(session, foundation)
    state = await service.connect(organization_id=actor.organization_id, actor=actor)
    return WhatsAppQrStatus(**dataclasses.asdict(state))


@router.post(
    "/session/pair", response_model=WhatsAppQrStatus, summary="Begin pairing and request a QR"
)
async def begin_pairing(
    session: SessionDep,
    actor: Operator,
    foundation: ChannelFoundationDep,
) -> WhatsAppQrStatus:
    service = _service(session, foundation)
    state = await service.begin_pairing(organization_id=actor.organization_id, actor=actor)
    return WhatsAppQrStatus(**dataclasses.asdict(state))


@router.get(
    "/session/qr",
    summary="Fetch the current transient QR image",
    responses={200: {"content": {"image/png": {}}}},
)
async def get_qr_image(
    session: SessionDep,
    actor: Operator,
    foundation: ChannelFoundationDep,
) -> Response:
    service = _service(session, foundation)
    challenge: WahaQrChallenge = await service.qr_image(
        organization_id=actor.organization_id, actor=actor
    )
    return Response(
        content=challenge.data,
        media_type=challenge.mimetype,
        headers={
            "Cache-Control": "no-store, private, max-age=0",
            "Pragma": "no-cache",
        },
    )


@router.post(
    "/session/reconnect", response_model=WhatsAppQrStatus, summary="Reconnect a paired session"
)
async def reconnect(
    session: SessionDep,
    actor: Operator,
    foundation: ChannelFoundationDep,
) -> WhatsAppQrStatus:
    service = _service(session, foundation)
    state = await service.reconnect(organization_id=actor.organization_id, actor=actor)
    return WhatsAppQrStatus(**dataclasses.asdict(state))


@router.post(
    "/session/logout",
    response_model=WhatsAppQrStatus,
    summary="Log out — invalidates WhatsApp credentials and requires a new scan",
)
async def logout(
    body: WhatsAppQrLogoutRequest,
    session: SessionDep,
    actor: Operator,
    foundation: ChannelFoundationDep,
) -> WhatsAppQrStatus:
    service = _service(session, foundation)
    state = await service.logout(
        organization_id=actor.organization_id, actor=actor, confirm=body.confirm
    )
    return WhatsAppQrStatus(**dataclasses.asdict(state))
