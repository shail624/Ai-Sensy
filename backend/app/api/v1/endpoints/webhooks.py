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
from app.channels.capabilities import CONNECTOR_WAHA
from app.channels.errors import ChannelConfigError
from app.channels.meta.webhooks import SIGNATURE_HEADER
from app.channels.waha.webhook import SIGNATURE_HEADER as WAHA_SIGNATURE_HEADER
from app.channels.waha.webhook import WahaBodyTooLarge
from app.core.exceptions import AppError, PayloadTooLargeError
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


@router.post(
    "/webhooks/waha",
    response_model=WebhookAckResponse,
    status_code=status.HTTP_200_OK,
    summary="Receive WAHA inbound events (public, HMAC-gated) — QR-08",
)
async def receive_waha_webhook(request: Request, session: SessionDep) -> WebhookAckResponse:
    """The WAHA analogue of :func:`receive_webhook` (QR-04 built the verify/parse/dedupe logic in
    ``app.channels.waha.webhook``; this is the first HTTP route that reaches it).

    No GET handshake: unlike Meta, WAHA has no subscription challenge to answer — it is configured
    with this URL directly and simply starts posting. The gate is the same shape as Meta's: an
    HMAC over the raw body, checked before anything is parsed, failing closed on an unconfigured
    secret. Persist-first, process-async is unchanged — this endpoint does no more than
    :func:`receive_webhook` does for Meta.
    """
    from app.channels.tasks import ingest_webhook_events

    try:
        event_ids = await WebhookService(session, connector_type=CONNECTOR_WAHA).ingest(
            body=await request.body(), signature=request.headers.get(WAHA_SIGNATURE_HEADER)
        )
    except WahaBodyTooLarge as exc:
        # The bound is enforced *before* the body is hashed (see `waha.webhook.verify_signature`),
        # so this costs nothing and leaks nothing — but it is a client error, and saying so matters:
        # WAHA's delivery is at-least-once and retries a 5xx, so answering 500 would turn one
        # oversized delivery into an endless redelivery loop (QR-09-D3). The provider's body is
        # never echoed back; only the bound itself is stated.
        raise PayloadTooLargeError(str(exc)) from exc
    except ChannelConfigError as exc:
        raise WebhookNotConfiguredError(str(exc)) from exc
    ingest_webhook_events.apply_async(args=[event_ids])
    return WebhookAckResponse(events=len(event_ids))
