"""Customer-document endpoints (Design Book 19, Phase 4A)."""

from __future__ import annotations

import uuid as uuidlib
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import SessionDep, require_permissions
from app.models.user import User
from app.schemas.contact_document import (
    DocumentContentResponse,
    DocumentCreateRequest,
    DocumentEventResponse,
    DocumentHistoryResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentStatus,
    DocumentTransitionRequest,
    DocumentType,
    DocumentVerificationRequest,
    DocumentVersionCreateRequest,
)
from app.services.contact_document_service import ContactDocumentService

router = APIRouter()

DocumentReader = Annotated[User, Depends(require_permissions("documents:read"))]
DocumentWriter = Annotated[User, Depends(require_permissions("documents:write"))]
DocumentVerifier = Annotated[User, Depends(require_permissions("documents:verify"))]


@router.get(
    "/contacts/{contact_id}/documents",
    response_model=DocumentListResponse,
    summary="List a customer's documents",
)
async def list_contact_documents(
    contact_id: uuidlib.UUID,
    session: SessionDep,
    actor: DocumentReader,
    document_status: Annotated[list[DocumentStatus] | None, Query(alias="status")] = None,
    document_type: Annotated[list[DocumentType] | None, Query(alias="type")] = None,
    q: Annotated[str | None, Query(max_length=160)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> DocumentListResponse:
    views, total = await ContactDocumentService(session).list_for_contact(
        organization_id=actor.organization_id,
        contact_public_id=contact_id,
        statuses=list(document_status) if document_status else None,
        document_types=list(document_type) if document_type else None,
        q=q,
        limit=limit,
    )
    return DocumentListResponse(data=[DocumentResponse.of(view) for view in views], total=total)


@router.post(
    "/contacts/{contact_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a customer document",
)
async def create_contact_document(
    contact_id: uuidlib.UUID,
    payload: DocumentCreateRequest,
    session: SessionDep,
    actor: DocumentWriter,
) -> DocumentResponse:
    view = await ContactDocumentService(session).create(
        organization_id=actor.organization_id,
        actor=actor,
        contact_public_id=contact_id,
        document_type=payload.document_type,
        title=payload.title,
        media_asset_id=payload.media_asset_id,
        expires_at=payload.expires_at,
        note=payload.note,
    )
    return DocumentResponse.of(view)


@router.get("/documents/{document_id}", response_model=DocumentResponse, summary="Get a document")
async def get_contact_document(
    document_id: uuidlib.UUID, session: SessionDep, actor: DocumentReader
) -> DocumentResponse:
    view = await ContactDocumentService(session).get(
        organization_id=actor.organization_id, public_id=document_id
    )
    return DocumentResponse.of(view)


@router.post(
    "/documents/{document_id}/versions",
    response_model=DocumentResponse,
    summary="Add an immutable document version",
)
async def add_contact_document_version(
    document_id: uuidlib.UUID,
    payload: DocumentVersionCreateRequest,
    session: SessionDep,
    actor: DocumentWriter,
) -> DocumentResponse:
    view = await ContactDocumentService(session).add_version(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=document_id,
        media_asset_id=payload.media_asset_id,
        note=payload.note,
        expected_row_version=payload.expected_row_version,
    )
    return DocumentResponse.of(view)


@router.post(
    "/documents/{document_id}/verification",
    response_model=DocumentResponse,
    summary="Verify or reject a document",
)
async def verify_contact_document(
    document_id: uuidlib.UUID,
    payload: DocumentVerificationRequest,
    session: SessionDep,
    actor: DocumentVerifier,
) -> DocumentResponse:
    view = await ContactDocumentService(session).verify(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=document_id,
        decision=payload.decision,
        reason=payload.reason,
        expected_row_version=payload.expected_row_version,
    )
    return DocumentResponse.of(view)


@router.post(
    "/documents/{document_id}/expire",
    response_model=DocumentResponse,
    summary="Mark a due document expired",
)
async def expire_contact_document(
    document_id: uuidlib.UUID,
    payload: DocumentTransitionRequest,
    session: SessionDep,
    actor: DocumentVerifier,
) -> DocumentResponse:
    view = await ContactDocumentService(session).expire(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=document_id,
        reason=payload.reason,
        expected_row_version=payload.expected_row_version,
    )
    return DocumentResponse.of(view)


@router.post(
    "/documents/{document_id}/archive",
    response_model=DocumentResponse,
    summary="Archive a document",
)
async def archive_contact_document(
    document_id: uuidlib.UUID,
    payload: DocumentTransitionRequest,
    session: SessionDep,
    actor: DocumentWriter,
) -> DocumentResponse:
    view = await ContactDocumentService(session).archive(
        organization_id=actor.organization_id,
        actor=actor,
        public_id=document_id,
        reason=payload.reason,
        expected_row_version=payload.expected_row_version,
    )
    return DocumentResponse.of(view)


@router.get(
    "/documents/{document_id}/history",
    response_model=DocumentHistoryResponse,
    summary="Get immutable document history",
)
async def contact_document_history(
    document_id: uuidlib.UUID, session: SessionDep, actor: DocumentReader
) -> DocumentHistoryResponse:
    views = await ContactDocumentService(session).history(
        organization_id=actor.organization_id, public_id=document_id
    )
    return DocumentHistoryResponse(data=[DocumentEventResponse.of(view) for view in views])


@router.get(
    "/documents/{document_id}/versions/{version_id}/content",
    response_model=DocumentContentResponse,
    summary="Get a signed document preview URL",
)
async def contact_document_content(
    document_id: uuidlib.UUID,
    version_id: uuidlib.UUID,
    session: SessionDep,
    actor: DocumentReader,
) -> DocumentContentResponse:
    url, ttl = await ContactDocumentService(session).content(
        organization_id=actor.organization_id,
        document_public_id=document_id,
        version_public_id=version_id,
    )
    return DocumentContentResponse(url=url, expires_in=ttl)
