"""Audit-log read endpoint (Doc 04 §22).

Read-only, cursor-paginated audit trail with actor/entity/action/date filters. Requires
``audit:read`` (Owner superuser bypasses). Scoped to the caller's organization plus system
events.
"""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import SessionDep, require_permissions
from app.api.pagination import DEFAULT_LIMIT, MAX_LIMIT, Page, decode_cursor, encode_cursor
from app.core.exceptions import BadRequestError
from app.models.user import User
from app.schemas.audit import AuditLogPage, AuditLogResponse
from app.services.audit_query_service import AuditQueryService

router = APIRouter()

AuditReadActor = Annotated[User, Depends(require_permissions("audit:read"))]


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError as exc:
        raise BadRequestError("Invalid date filter; use ISO-8601.") from exc


@router.get("/audit-logs", response_model=AuditLogPage, summary="Query the audit trail")
async def list_audit_logs(
    request: Request,
    session: SessionDep,
    actor: AuditReadActor,
    limit_param: Annotated[
        int | None, Query(alias="limit", ge=1, le=MAX_LIMIT, description="Page size (default 50).")
    ] = None,
    cursor_param: Annotated[
        str | None, Query(alias="cursor", description="Opaque token from a prior next_cursor.")
    ] = None,
) -> AuditLogPage:
    """The audit trail, newest first.

    Pagination is declared, because Doc 04 section 6 fixes `limit` and `cursor` for every
    collection and section 1 requires the API to be fully OpenAPI-describable — undeclared, they
    are unreachable from the generated client, which is the only contract the frontend may use.

    The `filter[field][op]` grammar of section 7.1 stays on the raw request deliberately: it spans
    any field crossed with eleven operators, so there is no finite set of parameters to declare.
    """
    params = request.query_params
    limit = limit_param if limit_param is not None else DEFAULT_LIMIT
    cursor = decode_cursor(cursor_param) if cursor_param else None

    service = AuditQueryService(session)
    actor_user_id: int | None = None
    actor_filter = params.get("filter[actor][eq]")
    if actor_filter:
        try:
            actor_user_id = await service.resolve_actor_id(uuidlib.UUID(actor_filter))
        except ValueError as exc:
            raise BadRequestError("Invalid actor filter; expected a user UUID.") from exc
        if actor_user_id is None:
            # Unknown actor → no results (valid, empty page).
            return AuditLogPage(data=[], page=Page(limit=limit, has_more=False, total=0))

    result = await service.list_entries(
        actor.organization_id,
        limit=limit,
        cursor=cursor,
        actor_user_id=actor_user_id,
        entity_type=params.get("filter[entity][eq]"),
        action=params.get("filter[action][eq]"),
        date_from=_parse_dt(params.get("filter[created_at][gte]")),
        date_to=_parse_dt(params.get("filter[created_at][lte]")),
    )
    data = [
        AuditLogResponse.from_entry(
            entry,
            result.actor_uuids.get(entry.actor_user_id)
            if entry.actor_user_id is not None
            else None,
        )
        for entry in result.entries
    ]
    next_cursor = (
        encode_cursor(result.entries[-1].created_at, result.entries[-1].id)
        if result.has_more and result.entries
        else None
    )
    return AuditLogPage(
        data=data,
        page=Page(limit=limit, has_more=result.has_more, next_cursor=next_cursor, total=result.total),
    )
