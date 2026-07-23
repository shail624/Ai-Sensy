"""Job-artifact download endpoint (Doc 04 §16 signed-URL rules; Doc 08 §14).

Serves the files that background jobs produce — a contact export, an import error report, a
bulk-operation report — to a valid signed URL. Like ``/media/{id}/download`` this route is **not**
Bearer-authenticated: the signature *is* the credential, and it binds the artifact id to an expiry
(``app/storage/signing.py``), so a leaked link dies on its own and cannot be edited to address a
different artifact.

Why this exists separately from the media route: a job artifact is not a ``media_assets`` row. The
media route is typed ``media_id: UUID`` and resolves the id against that table, so the prefixed
ids these jobs sign (``export-<uuid>`` and friends) could not be served there at all.
"""

from __future__ import annotations

import uuid as uuidlib
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.api.deps import SessionDep

# GoneError is shared with the media download route rather than redefined: both implement the same
# expired-signature contract (Doc 04 §5.1/§16) and must return the same machine `code`, so a second
# definition would be free to drift away from it.
from app.api.v1.endpoints.media import GoneError
from app.core.config import settings
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.crm.formats import CONTENT_TYPES
from app.repositories.bulk_job import BulkJobRepository
from app.repositories.export_job import ExportRepository
from app.repositories.import_job import ImportRepository
from app.storage.base import StorageError, get_provider
from app.storage.signing import SignatureExpired, SignatureInvalid, verify

router = APIRouter()

#: ``kind`` prefix -> (storage-key resolver, downloaded filename stem).
#:
#: Each resolver returns ``(storage_key, content_type, filename)`` or ``None`` when the job is
#: unknown or has produced no artifact. Keeping the mapping declarative means adding a fourth
#: artifact kind is one entry, not another branch in the handler.
_CSV = "text/csv"


async def _export(session, public_id: uuidlib.UUID) -> tuple[str, str, str] | None:
    job = await ExportRepository(session).get_by_uuid(public_id)
    if job is None or not job.storage_key:
        return None
    return job.storage_key, CONTENT_TYPES.get(job.format, _CSV), f"export-{public_id}.{job.format}"


async def _import(session, public_id: uuidlib.UUID) -> tuple[str, str, str] | None:
    job = await ImportRepository(session).get_by_uuid(public_id)
    if job is None or not job.error_report_key:
        return None
    return job.error_report_key, _CSV, f"import-errors-{public_id}.csv"


async def _bulk(session, public_id: uuidlib.UUID) -> tuple[str, str, str] | None:
    job = await BulkJobRepository(session).get_by_uuid(public_id)
    if job is None or not job.error_report_key:
        return None
    return job.error_report_key, _CSV, f"bulk-report-{public_id}.csv"


_RESOLVERS: dict[str, Callable[..., Awaitable[tuple[str, str, str] | None]]] = {
    "export": _export,
    "import": _import,
    "bulk": _bulk,
}


@router.get(
    "/artifacts/{artifact_id}/download",
    summary="Signed-URL download target for job artifacts (signature-authenticated)",
)
async def download_artifact(artifact_id: str, request: Request, session: SessionDep) -> Response:
    """Serve a job artifact's bytes to a valid signed URL."""
    params = request.query_params
    signature = params.get("signature")
    raw_expires = params.get("expires")
    if not signature or not raw_expires:
        raise BadRequestError("Missing signed URL parameters.")
    try:
        expires_at = int(raw_expires)
    except ValueError as exc:
        raise BadRequestError("Invalid 'expires' parameter.") from exc

    # Verify before touching the database: an unsigned request must not be able to probe which
    # artifact ids exist by comparing response times or error bodies.
    try:
        verify(artifact_id, expires_at, signature)
    except SignatureExpired as exc:
        raise GoneError("This link has expired.") from exc
    except SignatureInvalid as exc:
        raise ForbiddenError("Invalid signature.") from exc

    kind, _, raw_uuid = artifact_id.partition("-")
    resolver = _RESOLVERS.get(kind)
    if resolver is None:
        raise BadRequestError("Unknown artifact type.")
    try:
        public_id = uuidlib.UUID(raw_uuid)
    except ValueError as exc:
        raise BadRequestError("Invalid artifact id.") from exc

    resolved = await resolver(session, public_id)
    if resolved is None:
        raise NotFoundError("Artifact not found.")
    storage_key, content_type, filename = resolved

    try:
        data = await get_provider(settings.storage_backend).get(storage_key)
    except StorageError as exc:
        raise NotFoundError("Artifact content is unavailable.") from exc

    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
