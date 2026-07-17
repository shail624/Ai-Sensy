"""Inbound webhook endpoints (Doc 04 §23; Doc 06 §11) — Module 4 Step 3.

The platform's only **public** write surface, and deliberately unlike every other endpoint:

- **No authentication, by design.** Meta cannot hold a JWT. The gate is the signature over the raw
  body (``X-Hub-Signature-256``) — checked before the body is parsed, so an unverified payload is
  never interpreted. Failure is ``403`` and nothing is stored.
- **No rate limit** (Doc 04 §9 ``webhook`` class). Throttling Meta would make it redeliver for
  seven days; the signature is what makes unlimited safe.
- **Nothing slow.** Verify, persist, ack (<200 ms, FR-WA-05); the queues do the rest.

The raw body is read here rather than through a Pydantic model on purpose: FastAPI would hand back
re-serialized JSON, and an HMAC over re-serialized bytes is not the HMAC Meta computed.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import PlainTextResponse

from app.api.deps import SessionDep
from app.channels.errors import ChannelConfigError
from app.channels.meta.webhooks import SIGNATURE_HEADER
from app.core.exceptions import AppError
from app.schemas.webhook import WebhookAckResponse
from app.services.webhook_service import WebhookService

router = APIRouter()


class WebhookNotConfiguredError(AppError):
    """The inbound secrets are missing — our fault, not the caller's.

    ``503`` rather than ``500`` because it is honest and because it is *useful*: Meta redelivers a
    non-200 for up to seven days, so events that arrive during a misconfiguration are recovered by
    the retry once the secret is set. Answering ``403`` would be worse than either — it would drop
    real events while looking indistinguishable from an attack in the logs.
    """

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "webhook_not_configured"
    title = "Webhook Not Configured"


@router.get(
    "/webhooks/whatsapp",
    response_class=PlainTextResponse,
    summary="Meta verification handshake (public)",
    responses={200: {"content": {"text/plain": {}}}, 403: {"description": "Verification failed"}},
)
async def verify_webhook(request: Request, session: SessionDep) -> Response:
    """Echo ``hub.challenge`` when ``hub.verify_token`` matches (Doc 04 §23).

    Meta requires the bare challenge as the body — not JSON, not an envelope — or it refuses to
    activate the subscription.
    """
    try:
        echo = await WebhookService(session).challenge(dict(request.query_params))
    except ChannelConfigError as exc:
        raise WebhookNotConfiguredError(str(exc)) from exc
    return PlainTextResponse(echo)


@router.post(
    "/webhooks/whatsapp",
    response_model=WebhookAckResponse,
    status_code=status.HTTP_200_OK,
    summary="Receive inbound messages & status callbacks (public, signature-gated)",
)
async def receive_webhook(request: Request, session: SessionDep) -> WebhookAckResponse:
    """Persist the delivery and ack; processing happens on the ``webhooks.*`` queues."""
    from app.channels.tasks import ingest_webhook_events

    try:
        event_ids = await WebhookService(session).ingest(
            body=await request.body(), signature=request.headers.get(SIGNATURE_HEADER)
        )
    except ChannelConfigError as exc:
        raise WebhookNotConfiguredError(str(exc)) from exc
    # After the commit, never before: the task must not outrun the rows it reads (Doc 06 §11.2).
    # If the broker is down this raises, Meta retries, and the redelivery dedups (FR-WA-07) —
    # better than acking work that nothing will pick up.
    ingest_webhook_events.apply_async(args=[event_ids])
    return WebhookAckResponse(events=len(event_ids))
