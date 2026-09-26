"""Unified Download Center over the existing export artifact pipeline.

The center is deliberately personal: an authenticated operator sees only jobs they requested,
inside their organization, and only for export families they are still permitted to access.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.api.deps import CurrentUserDep, SessionDep
from app.api.pagination import Page, decode_cursor, encode_cursor
from app.core.exceptions import ForbiddenError
from app.db.mixins import utcnow
from app.repositories.export_job import ExportRepository
from app.schemas.export_job import DownloadItemResponse, DownloadsPage
from app.services.export_service import ExportService
from app.services.rbac_service import RBACService

router = APIRouter()

DownloadCategory = Literal["all", "contacts", "analytics", "chat_history", "campaigns"]
DownloadStatus = Literal["pending", "processing", "ready", "failed", "expired"]


@router.get(
    "/downloads",
    response_model=DownloadsPage,
    summary="List the current user's generated exports",
)
async def list_downloads(
    session: SessionDep,
    actor: CurrentUserDep,
    category: Annotated[DownloadCategory, Query()] = "all",
    status: Annotated[DownloadStatus | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: Annotated[str | None, Query()] = None,
) -> DownloadsPage:
    """Return a tenant-, owner-, and current-permission-scoped artifact history."""
    rbac = RBACService(session)
    can_contacts = await rbac.has_permissions(actor, {"contacts:export"})
    can_analytics = await rbac.has_permissions(actor, {"analytics:export"})
    can_transcripts = await rbac.has_permissions(actor, {"inbox:export"})
    can_campaigns = await rbac.has_permissions(actor, {"campaigns:export"})
    if not can_contacts and not can_analytics and not can_transcripts and not can_campaigns:
        raise ForbiddenError("You do not have permission to access generated exports.")

    include_contacts = can_contacts and category in ("all", "contacts")
    include_reports = can_analytics and category in ("all", "analytics")
    include_transcripts = can_transcripts and category in ("all", "chat_history")
    include_campaigns = can_campaigns and category in ("all", "campaigns")
    if not include_contacts and not include_reports and not include_transcripts and not include_campaigns:
        return DownloadsPage(data=[], page=Page(limit=limit, has_more=False, total=0))

    rows, has_more, total = await ExportRepository(session).list_downloads(
        actor.organization_id,
        actor.id,
        contacts=include_contacts,
        reports=include_reports,
        transcripts=include_transcripts,
        campaigns=include_campaigns,
        status=status,
        now=utcnow(),
        limit=limit,
        cursor=decode_cursor(cursor) if cursor else None,
    )
    service = ExportService(session)
    data = [
        DownloadItemResponse.from_job(job, await service.download_url(job)) for job in rows
    ]
    next_cursor = (
        encode_cursor(rows[-1].created_at, rows[-1].id) if has_more and rows else None
    )
    return DownloadsPage(
        data=data,
        page=Page(limit=limit, has_more=has_more, next_cursor=next_cursor, total=total),
    )
