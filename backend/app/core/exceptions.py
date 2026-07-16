"""Application error framework — RFC 7807 Problem Details.

Every error response uses ``application/problem+json`` with the shape defined in
Doc 04 §5 (type, title, status, detail, instance, code, request_id, errors[]).
Domain code raises subclasses of :class:`AppError`; FastAPI/validation errors are
mapped to the same shape by the handlers registered in :func:`register_exception_handlers`.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.core.logging import get_logger, request_id_ctx

logger = get_logger(__name__)

PROBLEM_CONTENT_TYPE = "application/problem+json"
# Base URI namespace for machine-readable problem types (Doc 04 §5.1).
ERROR_TYPE_BASE = "https://api.internal/errors"


class AppError(Exception):
    """Base class for all domain errors rendered as RFC 7807 problems.

    Subclasses set ``status_code``, a machine ``code``, a human ``title`` and an
    optional per-field ``errors`` list.
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "server_error"
    title: str = "Internal Server Error"

    def __init__(
        self,
        detail: str | None = None,
        *,
        errors: list[dict[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.detail = detail or self.title
        self.errors = errors
        self.headers = headers
        super().__init__(self.detail)

    def to_problem(self, instance: str) -> dict[str, Any]:
        problem: dict[str, Any] = {
            "type": f"{ERROR_TYPE_BASE}/{self.code.replace('_', '-')}",
            "title": self.title,
            "status": self.status_code,
            "detail": self.detail,
            "instance": instance,
            "code": self.code,
            "request_id": request_id_ctx.get(),
        }
        if self.errors:
            problem["errors"] = self.errors
        return problem


# --- Concrete domain errors (foundation set; extended per module) -----------
class BadRequestError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "bad_request"
    title = "Bad Request"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"
    title = "Unauthorized"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"
    title = "Forbidden"


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"
    title = "Not Found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"
    title = "Conflict"


class VersionConflictError(ConflictError):
    code = "version_conflict"
    title = "Version Conflict"


class ValidationError(AppError):
    status_code = 422  # numeric literal — 422 constant name differs across Starlette versions
    code = "validation_error"
    title = "Validation failed"


class LockedError(AppError):
    status_code = status.HTTP_423_LOCKED
    code = "locked"
    title = "Account Locked"


class RateLimitError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limit"
    title = "Too Many Requests"


class ServiceUnavailableError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "unavailable"
    title = "Service Unavailable"


def _problem_response(problem: dict[str, Any], headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=problem["status"],
        content=jsonable_encoder(problem),
        media_type=PROBLEM_CONTENT_TYPE,
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register handlers so *all* errors return the RFC 7807 shape (Doc 04 §5)."""

    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error("app_error", extra={"code": exc.code, "path": request.url.path})
        return _problem_response(exc.to_problem(request.url.path), exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "field": ".".join(str(p) for p in err.get("loc", []) if p != "body"),
                "code": err.get("type", "invalid"),
                "message": err.get("msg", "Invalid value"),
            }
            for err in exc.errors()
        ]
        problem = ValidationError(
            "One or more fields are invalid.", errors=errors
        ).to_problem(request.url.path)
        return _problem_response(problem)

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        mapping = {
            400: BadRequestError,
            401: UnauthorizedError,
            403: ForbiddenError,
            404: NotFoundError,
            409: ConflictError,
            422: ValidationError,
            423: LockedError,
            429: RateLimitError,
            503: ServiceUnavailableError,
        }
        error_cls = mapping.get(exc.status_code, AppError)
        error = error_cls(detail=exc.detail if isinstance(exc.detail, str) else None)
        error.status_code = exc.status_code
        headers = getattr(exc, "headers", None)
        return _problem_response(error.to_problem(request.url.path), headers)

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", extra={"path": request.url.path})
        problem = AppError("An unexpected error occurred.").to_problem(request.url.path)
        return _problem_response(problem)
