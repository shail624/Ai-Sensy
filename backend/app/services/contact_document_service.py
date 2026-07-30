"""Governed customer-document lifecycle service (Design Book 19, Phase 4A)."""

from __future__ import annotations

import uuid as uuidlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError, VersionConflictError
from app.db.mixins import utcnow
from app.models.contact import Contact
from app.models.contact_document import (
    DOCUMENT_EVENT_ARCHIVED,
    DOCUMENT_EVENT_CREATED,
    DOCUMENT_EVENT_EXPIRED,
    DOCUMENT_EVENT_REJECTED,
    DOCUMENT_EVENT_VERIFIED,
    DOCUMENT_EVENT_VERSION_ADDED,
    DOCUMENT_STATUS_ARCHIVED,
    DOCUMENT_STATUS_EXPIRED,
    DOCUMENT_STATUS_REJECTED,
    DOCUMENT_STATUS_SUBMITTED,
    DOCUMENT_STATUS_VERIFIED,
    DOCUMENT_STATUSES,
    DOCUMENT_TYPES,
    ContactDocument,
    ContactDocumentEvent,
    ContactDocumentVersion,
)
from app.models.media import MediaAsset
from app.models.user import User
from app.repositories.contact import ContactRepository
from app.repositories.contact_document import ContactDocumentRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.contact_event_service import ContactEventService
from app.services.media_service import MediaService


class DocumentStateError(ConflictError):
    code = "document_state"
    title = "Document State Conflict"


@dataclass(slots=True)
class DocumentVersionView:
    id: str
    version_no: int
    media_asset_id: str
    file_name: str | None
    mime_type: str
    byte_size: int
    note: str | None
    uploaded_by: str | None
    uploaded_by_name: str | None
    created_at: datetime


@dataclass(slots=True)
class DocumentView:
    id: str
    contact_id: str
    document_type: str
    title: str
    status: str
    is_expired: bool
    expires_at: datetime | None
    verified_at: datetime | None
    verified_by: str | None
    verified_by_name: str | None
    rejection_reason: str | None
    archived_at: datetime | None
    current_version: DocumentVersionView
    versions: list[DocumentVersionView]
    row_version: int
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class DocumentEventView:
    id: int
    event_type: str
    actor_user_id: str | None
    actor_name: str | None
    from_value: dict[str, Any] | None
    to_value: dict[str, Any] | None
    reason: str | None
    created_at: datetime


class ContactDocumentService:
    """Enforces tenant isolation, lifecycle rules, history and audit atomically."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ContactDocumentRepository(session)
        self._contacts = ContactRepository(session)
        self._media = MediaService(session)
        self._audit = AuditService(session)
        self._timeline = ContactEventService(session)

    async def list_for_contact(
        self,
        *,
        organization_id: int,
        contact_public_id: uuidlib.UUID,
        statuses: list[str] | None,
        document_types: list[str] | None,
        q: str | None,
        limit: int,
    ) -> tuple[list[DocumentView], int]:
        self._validate_filters(statuses, document_types)
        contact = await self._require_contact(organization_id, contact_public_id)
        documents, total = await self._repo.list_for_contact(
            organization_id,
            contact.id,
            statuses=statuses,
            document_types=document_types,
            q=q,
            limit=limit,
        )
        return await self._build_views(documents), total

    async def get(self, *, organization_id: int, public_id: uuidlib.UUID) -> DocumentView:
        document = await self._require_document(organization_id, public_id)
        return (await self._build_views([document]))[0]

    async def history(
        self, *, organization_id: int, public_id: uuidlib.UUID
    ) -> list[DocumentEventView]:
        document = await self._require_document(organization_id, public_id)
        events = await self._repo.list_events(document.id)
        users = await self._repo.list_users(
            {event.actor_user_id for event in events if event.actor_user_id is not None}
        )
        return [
            DocumentEventView(
                id=event.id,
                event_type=event.event_type,
                actor_user_id=(
                    users[event.actor_user_id][0]
                    if event.actor_user_id is not None and event.actor_user_id in users
                    else None
                ),
                actor_name=(
                    users[event.actor_user_id][1]
                    if event.actor_user_id is not None and event.actor_user_id in users
                    else None
                ),
                from_value=event.from_json,
                to_value=event.to_json,
                reason=event.reason,
                created_at=event.created_at,
            )
            for event in events
        ]

    async def create(
        self,
        *,
        organization_id: int,
        actor: User,
        contact_public_id: uuidlib.UUID,
        document_type: str,
        title: str,
        media_asset_id: uuidlib.UUID,
        expires_at: datetime | None,
        note: str | None,
    ) -> DocumentView:
        self._validate_filters(None, [document_type])
        contact = await self._require_contact(organization_id, contact_public_id)
        media = await self._require_document_media(organization_id, media_asset_id)
        document = ContactDocument(
            organization_id=organization_id,
            contact_id=contact.id,
            document_type=document_type,
            title=title.strip(),
            status=DOCUMENT_STATUS_SUBMITTED,
            expires_at=expires_at,
            created_by=actor.id,
            updated_by=actor.id,
        )
        await self._repo.add(document)
        version = await self._add_version_row(document, media, actor, note, version_no=1)
        self._add_event(
            document,
            DOCUMENT_EVENT_CREATED,
            actor.id,
            to_value={"status": document.status, "version": version.version_no},
        )
        await self._project(document, "document_created", actor, version_no=1)
        await self._audit.record(
            AuditAction.DOCUMENT_CREATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="contact_document",
            entity_id=document.id,
            after={"status": document.status, "document_type": document.document_type},
        )
        await self._session.commit()
        return (await self._build_views([document]))[0]

    async def add_version(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        media_asset_id: uuidlib.UUID,
        note: str | None,
        expected_row_version: int | None,
    ) -> DocumentView:
        document = await self._require_document(organization_id, public_id)
        self._check_version(document, expected_row_version)
        if document.status == DOCUMENT_STATUS_ARCHIVED:
            raise DocumentStateError("An archived document cannot receive a new version.")
        media = await self._require_document_media(organization_id, media_asset_id)
        if await self._repo.search_duplicate_media(document.id, media.id) is not None:
            raise ConflictError("This file is already attached to the document.")
        previous = document.status
        version_no = await self._repo.next_version_no(document.id)
        await self._add_version_row(document, media, actor, note, version_no=version_no)
        document.status = DOCUMENT_STATUS_SUBMITTED
        document.verified_at = None
        document.verified_by = None
        document.rejection_reason = None
        self._bump(document, actor.id)
        self._add_event(
            document,
            DOCUMENT_EVENT_VERSION_ADDED,
            actor.id,
            from_value={"status": previous},
            to_value={"status": document.status, "version": version_no},
            reason=note,
        )
        await self._project(document, "document_version_added", actor, version_no=version_no)
        await self._audit.record(
            AuditAction.DOCUMENT_VERSION_ADDED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="contact_document",
            entity_id=document.id,
            before={"status": previous},
            after={"status": document.status, "version": version_no},
        )
        await self._session.commit()
        return (await self._build_views([document]))[0]

    async def verify(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        decision: str,
        reason: str | None,
        expected_row_version: int | None,
    ) -> DocumentView:
        document = await self._require_document(organization_id, public_id)
        self._check_version(document, expected_row_version)
        if document.status != DOCUMENT_STATUS_SUBMITTED:
            raise DocumentStateError(
                f"A {document.status} document cannot be verified or rejected."
            )
        previous = document.status
        now = utcnow()
        if decision == DOCUMENT_STATUS_VERIFIED:
            document.status = DOCUMENT_STATUS_VERIFIED
            document.verified_at = now
            document.verified_by = actor.id
            document.rejection_reason = None
            event_type = DOCUMENT_EVENT_VERIFIED
            timeline_event = "document_verified"
            audit_action = AuditAction.DOCUMENT_VERIFIED
        elif decision == DOCUMENT_STATUS_REJECTED:
            cleaned_reason = (reason or "").strip()
            if not cleaned_reason:
                raise BadRequestError("A rejection reason is required.")
            document.status = DOCUMENT_STATUS_REJECTED
            document.verified_at = None
            document.verified_by = actor.id
            document.rejection_reason = cleaned_reason
            event_type = DOCUMENT_EVENT_REJECTED
            timeline_event = "document_rejected"
            audit_action = AuditAction.DOCUMENT_REJECTED
        else:
            raise BadRequestError("decision must be verified or rejected.")
        self._bump(document, actor.id)
        self._add_event(
            document,
            event_type,
            actor.id,
            from_value={"status": previous},
            to_value={"status": document.status},
            reason=reason,
        )
        await self._project(document, timeline_event, actor, reason=reason)
        await self._audit.record(
            audit_action,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="contact_document",
            entity_id=document.id,
            before={"status": previous},
            after={"status": document.status, "reason": reason},
        )
        await self._session.commit()
        return (await self._build_views([document]))[0]

    async def expire(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        reason: str | None,
        expected_row_version: int | None,
    ) -> DocumentView:
        document = await self._require_document(organization_id, public_id)
        self._check_version(document, expected_row_version)
        if document.status != DOCUMENT_STATUS_VERIFIED:
            raise DocumentStateError(f"A {document.status} document cannot be marked expired.")
        if document.expires_at is None or document.expires_at > utcnow():
            raise DocumentStateError("The document has not reached its expiry date.")
        await self._transition(
            document,
            actor,
            DOCUMENT_STATUS_EXPIRED,
            DOCUMENT_EVENT_EXPIRED,
            "document_expired",
            AuditAction.DOCUMENT_EXPIRED,
            reason,
        )
        return (await self._build_views([document]))[0]

    async def archive(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        reason: str | None,
        expected_row_version: int | None,
    ) -> DocumentView:
        document = await self._require_document(organization_id, public_id)
        self._check_version(document, expected_row_version)
        if document.status == DOCUMENT_STATUS_ARCHIVED:
            raise DocumentStateError("The document is already archived.")
        document.archived_at = utcnow()
        await self._transition(
            document,
            actor,
            DOCUMENT_STATUS_ARCHIVED,
            DOCUMENT_EVENT_ARCHIVED,
            "document_archived",
            AuditAction.DOCUMENT_ARCHIVED,
            reason,
        )
        return (await self._build_views([document]))[0]

    async def content(
        self,
        *,
        organization_id: int,
        document_public_id: uuidlib.UUID,
        version_public_id: uuidlib.UUID,
    ) -> tuple[str, int]:
        document = await self._require_document(organization_id, document_public_id)
        version = await self._repo.get_version(
            organization_id, document.id, version_public_id.bytes
        )
        if version is None:
            raise NotFoundError("Document version not found.")
        media = (await self._repo.media_map({version.media_asset_id})).get(version.media_asset_id)
        if media is None or media.deleted_at is not None:
            raise NotFoundError("Document content is unavailable.")
        return await self._media.signed_url(organization_id, uuidlib.UUID(bytes=media.uuid))

    async def _transition(
        self,
        document: ContactDocument,
        actor: User,
        status: str,
        event_type: str,
        timeline_event: str,
        audit_action: str,
        reason: str | None,
    ) -> None:
        previous = document.status
        document.status = status
        self._bump(document, actor.id)
        self._add_event(
            document,
            event_type,
            actor.id,
            from_value={"status": previous},
            to_value={"status": status},
            reason=reason,
        )
        await self._project(document, timeline_event, actor, reason=reason)
        await self._audit.record(
            audit_action,
            actor_user_id=actor.id,
            organization_id=document.organization_id,
            entity_type="contact_document",
            entity_id=document.id,
            before={"status": previous},
            after={"status": status, "reason": reason},
        )
        await self._session.commit()

    async def _add_version_row(
        self,
        document: ContactDocument,
        media: MediaAsset,
        actor: User,
        note: str | None,
        *,
        version_no: int,
    ) -> ContactDocumentVersion:
        version = ContactDocumentVersion(
            organization_id=document.organization_id,
            document_id=document.id,
            version_no=version_no,
            media_asset_id=media.id,
            uploaded_by=actor.id,
            note=(note or "").strip() or None,
        )
        media.usage_count += 1
        self._session.add(version)
        await self._session.flush()
        return version

    def _add_event(
        self,
        document: ContactDocument,
        event_type: str,
        actor_user_id: int,
        *,
        from_value: dict[str, Any] | None = None,
        to_value: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> None:
        self._session.add(
            ContactDocumentEvent(
                organization_id=document.organization_id,
                document_id=document.id,
                event_type=event_type,
                actor_user_id=actor_user_id,
                from_json=from_value,
                to_json=to_value,
                reason=(reason or "").strip() or None,
            )
        )

    async def _project(
        self,
        document: ContactDocument,
        event_type: str,
        actor: User,
        *,
        version_no: int | None = None,
        reason: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "document_id": document.public_id,
            "title": document.title,
            "document_type": document.document_type,
            "status": document.status,
            "actor_name": actor.full_name,
        }
        if version_no is not None:
            payload["version_no"] = version_no
        if reason:
            payload["reason"] = reason
        await self._timeline.record(
            organization_id=document.organization_id,
            contact_id=document.contact_id,
            event_type=event_type,
            ref_type="contact_document",
            ref_id=document.id,
            payload=payload,
        )

    async def _build_views(self, documents: list[ContactDocument]) -> list[DocumentView]:
        if not documents:
            return []
        versions = await self._repo.list_versions([document.id for document in documents])
        media = await self._repo.media_map({version.media_asset_id for version in versions})
        user_ids = {
            user_id
            for document in documents
            for user_id in (document.verified_by,)
            if user_id is not None
        } | {version.uploaded_by for version in versions if version.uploaded_by is not None}
        users = await self._repo.list_users(user_ids)
        contacts = list(
            (
                await self._session.scalars(
                    select(Contact).where(
                        Contact.id.in_({document.contact_id for document in documents})
                    )
                )
            ).all()
        )
        contact_ids = {contact.id: contact.public_id for contact in contacts}
        grouped: dict[int, list[DocumentVersionView]] = {document.id: [] for document in documents}
        for version in versions:
            asset = media.get(version.media_asset_id)
            if asset is None:
                raise NotFoundError("Document content metadata is unavailable.")
            uploader = users.get(version.uploaded_by) if version.uploaded_by is not None else None
            grouped[version.document_id].append(
                DocumentVersionView(
                    id=version.public_id,
                    version_no=version.version_no,
                    media_asset_id=asset.public_id,
                    file_name=asset.file_name,
                    mime_type=asset.mime_type,
                    byte_size=asset.byte_size,
                    note=version.note,
                    uploaded_by=uploader[0] if uploader else None,
                    uploaded_by_name=uploader[1] if uploader else None,
                    created_at=version.created_at,
                )
            )
        now = utcnow()
        result: list[DocumentView] = []
        for document in documents:
            document_versions = grouped[document.id]
            if not document_versions:
                raise NotFoundError("Document has no stored version.")
            verifier = users.get(document.verified_by) if document.verified_by is not None else None
            result.append(
                DocumentView(
                    id=document.public_id,
                    contact_id=contact_ids[document.contact_id],
                    document_type=document.document_type,
                    title=document.title,
                    status=document.status,
                    is_expired=(
                        document.expires_at is not None
                        and document.expires_at <= now
                        and document.status != DOCUMENT_STATUS_ARCHIVED
                    ),
                    expires_at=document.expires_at,
                    verified_at=document.verified_at,
                    verified_by=verifier[0] if verifier else None,
                    verified_by_name=verifier[1] if verifier else None,
                    rejection_reason=document.rejection_reason,
                    archived_at=document.archived_at,
                    current_version=document_versions[-1],
                    versions=document_versions,
                    row_version=document.row_version,
                    created_at=document.created_at,
                    updated_at=document.updated_at,
                )
            )
        return result

    async def _require_contact(self, organization_id: int, public_id: uuidlib.UUID) -> Contact:
        contact = await self._contacts.get_active_by_uuid(organization_id, public_id.bytes)
        if contact is None:
            raise NotFoundError("Contact not found.")
        return contact

    async def _require_document(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> ContactDocument:
        document = await self._repo.get_active_by_uuid(organization_id, public_id.bytes)
        if document is None:
            raise NotFoundError("Document not found.")
        return document

    async def _require_document_media(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> MediaAsset:
        media = await self._media.get_media(organization_id, public_id)
        if media.media_type not in {"document", "image"}:
            raise BadRequestError("Customer documents must use a document or image media asset.")
        return media

    @staticmethod
    def _validate_filters(statuses: list[str] | None, document_types: list[str] | None) -> None:
        invalid_statuses = set(statuses or ()) - set(DOCUMENT_STATUSES)
        invalid_types = set(document_types or ()) - set(DOCUMENT_TYPES)
        if invalid_statuses:
            raise BadRequestError(f"Unknown document status: {sorted(invalid_statuses)[0]}")
        if invalid_types:
            raise BadRequestError(f"Unknown document type: {sorted(invalid_types)[0]}")

    @staticmethod
    def _check_version(document: ContactDocument, expected: int | None) -> None:
        if expected is not None and expected != document.row_version:
            raise VersionConflictError("The document changed since it was loaded.")

    @staticmethod
    def _bump(document: ContactDocument, actor_user_id: int) -> None:
        document.row_version += 1
        document.updated_by = actor_user_id
        document.updated_at = utcnow()
