"""Media library endpoints (Doc 04 §16, Doc 08 §14).

Reads require ``media:read``; uploads/deletes require ``media:write`` (Owner superuser bypasses).
``/media/{id}/content`` returns a **signed, expiring URL** rather than bytes (FR-MED-09); that
URL points at ``/media/{id}/download``, which authenticates by signature — the only route here
that is not Bearer-authenticated, because a signed URL *is* the credential (Doc 08 §14).

Media processing (thumbnails/transcode) and the Meta media-id refresh are separate modules.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import Response

from app.api.deps import SessionDep, require_permissions
from app.core.exceptions import (
    AppError,
    BadRequestError,
    ForbiddenError,
    ValidationError,
)
from app.models.user import User
from app.schemas.media import MediaContentResponse, MediaListResponse, MediaResponse
from app.services.media_service import MediaService
from app.storage.base import StorageError
from app.storage.scanning import InfectedFile
from app.storage.signing import SignatureExpired, SignatureInvalid, verify
from app.storage.validation import InvalidMedia, MediaTooLarge, UnsupportedMediaType

router = APIRouter()

MediaReadActor = Annotated[User, Depends(require_permissions("media:read"))]
MediaWriteActor = Annotated[User, Depends(require_permissions("media:write"))]


class PayloadTooLargeError(AppError):
    """413 — file exceeds the limit for its media type (Doc 04 §16)."""

    status_code = 413  # numeric literal — the constant name differs across Starlette versions
    code = "payload_too_large"
    title = "Payload Too Large"


class UnsupportedMediaTypeError(AppError):
    """415 — MIME type not allowed for the declared media type (Doc 04 §16)."""

    status_code = 415
    code = "unsupported_media_type"
    title = "Unsupported Media Type"


class GoneError(AppError):
    """410 — the signed URL has expired (Doc 04 §5.1/§16)."""

    status_code = 410
    code = "gone"
    title = "Gone"


@router.post(
    "/media/upload",
    response_model=MediaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file (multipart)",
)
async def upload_media(
    session: SessionDep,
    actor: MediaWriteActor,
    file: Annotated[UploadFile, File()],
    media_type: Annotated[str, Form()],
) -> MediaResponse:
    data = await file.read()
    try:
        asset, _ = await MediaService(session).upload(
            organization_id=actor.organization_id,
            actor=actor,
            data=data,
            media_type=media_type,
            mime_type=file.content_type or "application/octet-stream",
            file_name=file.filename,
        )
    except MediaTooLarge as exc:
        raise PayloadTooLargeError(str(exc)) from exc
    except UnsupportedMediaType as exc:
        raise UnsupportedMediaTypeError(str(exc)) from exc
    except (InvalidMedia, InfectedFile) as exc:
        raise ValidationError(str(exc)) from exc
    return MediaResponse.from_asset(asset)


@router.get("/media", response_model=MediaListResponse, summary="List the media library")
async def list_media(
    request: Request, session: SessionDep, actor: MediaReadActor
) -> MediaListResponse:
    params = request.query_params
    assets, total = await MediaService(session).list_media(
        actor.organization_id,
        media_type=params.get("filter[media_type][eq]"),
        q=params.get("q"),
        limit=min(int(params.get("limit") or 50), 200),
    )
    return MediaListResponse(data=[MediaResponse.from_asset(a) for a in assets], total=total)


@router.get("/media/{media_id}", response_model=MediaResponse, summary="Get asset metadata")
async def get_media(
    media_id: uuidlib.UUID, session: SessionDep, actor: MediaReadActor
) -> MediaResponse:
    return MediaResponse.from_asset(
        await MediaService(session).get_media(actor.organization_id, media_id)
    )


@router.get(
    "/media/{media_id}/content",
    response_model=MediaContentResponse,
    summary="Signed, expiring download/preview URL",
)
async def media_content(
    media_id: uuidlib.UUID, session: SessionDep, actor: MediaReadActor
) -> MediaContentResponse:
    url, ttl = await MediaService(session).signed_url(actor.organization_id, media_id)
    return MediaContentResponse(url=url, expires_in=ttl)


@router.get(
    "/media/{media_id}/download",
    summary="Signed-URL download target (signature-authenticated)",
    include_in_schema=True,
)
async def download_media(
    media_id: uuidlib.UUID, request: Request, session: SessionDep
) -> Response:
    """Serve bytes to a valid signed URL. The signature is the credential (FR-MED-09)."""
    params = request.query_params
    signature = params.get("signature")
    raw_expires = params.get("expires")
    if not signature or not raw_expires:
        raise BadRequestError("Missing signed URL parameters.")
    try:
        expires_at = int(raw_expires)
    except ValueError as exc:
        raise BadRequestError("Invalid 'expires' parameter.") from exc
    try:
        verify(str(media_id), expires_at, signature)
    except SignatureExpired as exc:
        raise GoneError("This link has expired.") from exc
    except SignatureInvalid as exc:
        raise ForbiddenError("Invalid signature.") from exc

    service = MediaService(session)
    asset = await service._media.get_by_uuid(media_id)  # noqa: SLF001 - signature is the authz
    if asset is None or asset.deleted_at is not None:
        raise BadRequestError("Media asset not found.")
    try:
        _, data = await service.read_bytes(asset.organization_id, media_id)
    except StorageError as exc:
        raise BadRequestError("Media content is unavailable.") from exc
    return Response(content=data, media_type=asset.mime_type)


@router.delete(
    "/media/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an asset (if unused)",
)
async def delete_media(
    media_id: uuidlib.UUID, session: SessionDep, actor: MediaWriteActor
) -> None:
    await MediaService(session).delete(
        organization_id=actor.organization_id, actor=actor, public_id=media_id
    )
