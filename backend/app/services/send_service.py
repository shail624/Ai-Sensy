"""Outbound send (Doc 04 §18.2; Doc 06 §2.3 ``sends.priority``) — FR-WA-10/12.

**Accept, then deliver.** The request path validates the send and writes an `accepted` ledger row;
the queue talks to Meta. That is why the endpoint answers `202` with `wamid: null` (Doc 04 §18.2):
the platform has taken responsibility for the message, but only Meta can say it left, and only a
webhook can say it arrived (Doc 06 §11).

**The rules are enforced here, server-side, not at the edge** (Doc 01 §7): opt-out and the 24-hour
window are Meta compliance obligations, so they are checked where every caller must pass — an
agent, an automation, or a future campaign — rather than in a request schema.

**Template sends are the exception that proves the window rule.** A template is the only thing that
may cross a closed 24-hour window (Doc 04 §18.2), which is precisely why it must be approved and
its variables must match: the checks that free-form gets from the window, a template gets from the
registry (FR-TPL-03).

**Throughput is gated, not assumed** (FR-WA-13, Doc 06 §5). :meth:`deliver` takes budget from the
per-number rate gate before Meta is called; no budget is a `THROTTLE`, which the retry engine backs
off and re-queues (§6.2) rather than a failure. The one exception is a RED number carrying
marketing: waiting cannot fix that, so it fails the message (§5.4).
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.errors import ChannelError
from app.channels.models import (
    InteractiveContent,
    MediaContent,
    MediaKind,
    MessageType,
    OutboundMessage,
    TemplateButtonValue,
    TemplateContent,
    TextContent,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.db.mixins import utcnow
from app.models.contact import OPT_IN_OPTED_OUT
from app.models.conversation import Conversation
from app.models.message import (
    DIRECTION_OUTBOUND,
    MSG_ACCEPTED,
    MSG_FAILED,
    Message,
    MessageStatusHistory,
)
from app.models.template import MessageTemplate
from app.models.user import User
from app.models.waba import PhoneNumber
from app.queue.retry import FailureClass, register_error_map
from app.repositories.contact import ContactRepository
from app.repositories.media import MediaRepository
from app.repositories.message import MessageRepository, MessageStatusHistoryRepository
from app.repositories.template import TemplateRepository
from app.repositories.waba import PhoneNumberRepository, WabaRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.contact_service import wa_id_from_e164
from app.services.conversation_service import ConversationService
from app.services.media_ingest_service import MediaIngestService
from app.services.rate_gate import RateGate, is_paused
from app.services.template_validation import VARIABLE_BUTTONS, expected_variables, render
from app.services.waba_service import WabaService

logger = get_logger(__name__)

#: Doc 06 §2.3 — transactional sends; a user is waiting.
SEND_QUEUE = "sends.priority"
SEND_TASK = "app.channels.tasks.send_message"

#: Doc 03 ``contacts.source`` for someone we messaged first.
SOURCE_API = "api"

#: Free-form types need an open window; a template is the only type that may cross a closed one
#: (Doc 04 §18.2, FR-WA-12).
FREE_FORM = (MessageType.TEXT, MessageType.MEDIA, MessageType.INTERACTIVE)


class WindowClosedError(ValidationError):
    """The 24-hour customer-service window has lapsed (Doc 04 §18.2 → 422; FR-WA-12)."""

    code = "window_closed"
    title = "Messaging Window Closed"


class OptedOutError(ValidationError):
    """The contact has opted out (Doc 04 §18.2 → 422; Doc 01 CMP)."""

    code = "opt_out"
    title = "Contact Opted Out"


class NumberPausedError(ValidationError):
    """The number is RED and this is marketing, so the platform will not send it (§5.4).

    Refused here as well as at the gate because a caller can act on it now — pick another number,
    or send utility traffic — rather than finding out from a message that failed an hour later.
    """

    code = "number_quality_paused"
    title = "Number Paused For Quality"


class SendThrottled(Exception):
    """No budget on this number right now — a wait, not a failure (Doc 06 §5.3/§6.2)."""

    def __init__(self, message: str, *, reason: str, retry_after: float) -> None:
        self.reason = reason
        self.retry_after = retry_after
        super().__init__(message)


def _classify_send(exc: BaseException) -> FailureClass | None:
    """The one class this module owns (Doc 06 §6.6, D12)."""
    if isinstance(exc, SendThrottled):
        # Not a failure at all: the number is at its ceiling and the send waits its turn.
        return FailureClass.THROTTLE
    return None


register_error_map("sends", _classify_send)


class TemplateNotSendableError(ValidationError):
    """The template is not approved, so Meta would reject the send (FR-TPL-03)."""

    code = "template_not_sendable"
    title = "Template Not Sendable"


class TemplateVariablesError(ValidationError):
    """The values supplied do not fill the template's placeholders (FR-TPL-04)."""

    code = "template_variables"
    title = "Template Variables Invalid"


class SendService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._messages = MessageRepository(session)
        self._history = MessageStatusHistoryRepository(session)
        self._contacts = ContactRepository(session)
        self._assets = MediaRepository(session)
        self._templates = TemplateRepository(session)
        self._numbers = PhoneNumberRepository(session)
        self._wabas = WabaRepository(session)
        self._conversations = ConversationService(session)
        self._audit = AuditService(session)

    # --- Accept (request path) ----------------------------------------------
    async def accept(
        self,
        *,
        organization_id: int,
        actor: User,
        number: PhoneNumber,
        to: str,
        message_type: MessageType,
        content: dict[str, Any],
        campaign_id: int | None = None,
        audit: bool = True,
    ) -> Message:
        """Validate, persist as ``accepted``, and hand off. No Meta call on this path.

        ``campaign_id`` stamps the broadcast a message belongs to (Doc 03 §9.2). ``audit=False`` is
        for it: a campaign is **one** operator decision, already audited as `campaign.dispatched`,
        so auditing each of its hundred thousand messages would bury the trail rather than build it.
        """
        wa_id = wa_id_from_e164(to)
        if not wa_id:
            raise ValidationError(
                "A recipient phone number in E.164 format is required.",
                errors=[{"field": "to", "code": "invalid", "message": "Not a phone number."}],
            )

        contact = await self._conversations.resolve_recipient(
            organization_id=organization_id, wa_id=wa_id, source=SOURCE_API
        )
        if contact.opt_in_status == OPT_IN_OPTED_OUT:
            raise OptedOutError(
                "This contact has opted out of messages and cannot be contacted."
            )

        conversation = await self._conversations.thread_for(number=number, contact=contact)
        self._require_window(conversation, message_type)

        template = None
        if message_type is MessageType.TEMPLATE:
            template = await self._template_for(organization_id, content)
            if is_paused(number, template.category):
                raise NumberPausedError(
                    f"{number.display_number} has a RED quality rating; marketing is paused on it "
                    "until quality recovers."
                )
            # Stamp what the template *is* onto the message: the registry row may be edited or
            # re-synced later, and the ledger must still say what was actually sent.
            content["template"]["name"] = template.name
            content["template"]["language"] = template.language
        asset = await self._asset_for(organization_id, content)
        if asset is not None:
            # What keeps an asset a message depends on from being deleted (Doc 04 §16 → 409).
            asset.usage_count += 1
        now = utcnow()
        message = Message(
            organization_id=organization_id,
            conversation_id=conversation.id,
            phone_number_id=number.id,
            contact_id=contact.id,
            direction=DIRECTION_OUTBOUND,
            # Doc 03 §9.2's vocabulary is per-kind, so an image is an `image`, not a `media`.
            message_type=(content.get("media") or {}).get("kind")
            if message_type is MessageType.MEDIA
            else message_type.value,
            content_json=content,
            campaign_id=campaign_id,
            media_asset_id=asset.id if asset else None,
            template_id=template.id if template else None,
            # Doc 03 §9.2's `category` is what the cost engine bills on, and only a template has
            # one — Meta prices the conversation by the template's category.
            category=template.category if template else None,
            status=MSG_ACCEPTED,
            created_at=now,
        )
        await self._messages.add(message)
        await self._conversations.record_outbound_message(
            conversation,
            contact=contact,
            preview=self._preview_of(message.message_type, content, template),
            occurred_at=now,
        )
        # An operator-initiated send is an action a person took, and low-volume by nature — unlike
        # the inbound firehose, which is data rather than an act.
        if audit:
            await self._audit.record(
                AuditAction.MESSAGE_SENT,
                actor_user_id=actor.id,
                organization_id=organization_id,
                entity_type="message",
                entity_id=message.id,
                after={"type": message.message_type, "conversation_id": conversation.public_id},
            )
        await self._session.commit()
        return message

    async def _asset_for(self, organization_id: int, content: dict[str, Any]):
        """Resolve a `media_asset_id` reference to the asset, or fail before anything is queued.

        Checked on the request path so a caller learns immediately that the asset is unknown,
        rather than from a message that silently never arrives (Doc 07 §17.3).
        """
        # A media send references the asset directly; a template references it as its header.
        reference = content.get("media") or (content.get("template") or {}).get("header_media")
        public_id = (reference or {}).get("media_asset_id")
        if not public_id:
            return None
        asset = await self._assets.get_active_by_uuid(
            organization_id, uuidlib.UUID(str(public_id)).bytes
        )
        if asset is None:
            raise NotFoundError("Media asset not found.")
        return asset

    async def _template_for(
        self, organization_id: int, content: dict[str, Any]
    ) -> MessageTemplate:
        """Resolve and vet the template a send names (FR-TPL-03/04).

        Both checks happen here, on the request path, because both have an answer the caller can
        act on: an unapproved template needs a different template, and wrong variables need a
        corrected call. Learning either from a failed delivery an hour later helps nobody.
        """
        spec = content.get("template") or {}
        template = await self._templates.get_active_by_uuid(
            organization_id, uuidlib.UUID(str(spec["id"])).bytes
        )
        if template is None:
            raise NotFoundError("Template not found.")
        if not template.is_sendable:
            raise TemplateNotSendableError(
                f"Template {template.name!r} is {template.status} and cannot be sent.",
                errors=[
                    {"field": "template.id", "code": template.status, "message": template.status}
                ],
            )

        header_vars, body_vars = expected_variables(template.components_json or [])
        supplied_header = list(spec.get("header") or [])
        supplied_body = list(spec.get("body") or [])
        for label, expected, supplied in (
            ("header", header_vars, supplied_header),
            ("body", body_vars, supplied_body),
        ):
            if len(supplied) != expected:
                raise TemplateVariablesError(
                    f"Template {template.name!r} needs {expected} {label} variable(s); "
                    f"{len(supplied)} supplied.",
                    errors=[
                        {
                            "field": f"template.{label}",
                            "code": "count_mismatch",
                            "message": f"expected {expected}, got {len(supplied)}",
                        }
                    ],
                )
        for index, button in enumerate(spec.get("buttons") or []):
            if str(button.get("type")) not in VARIABLE_BUTTONS:
                raise TemplateVariablesError(
                    f"Button values can only be bound to {', '.join(VARIABLE_BUTTONS)} buttons.",
                    errors=[
                        {
                            "field": f"template.buttons.{index}.type",
                            "code": "invalid",
                            "message": str(button.get("type")),
                        }
                    ],
                )
        if template.has_media_header and not (spec.get("header_media") or {}):
            raise TemplateVariablesError(
                f"Template {template.name!r} has a media header and needs header_media.",
                errors=[
                    {"field": "template.header_media", "code": "required", "message": "Required."}
                ],
            )
        return template

    @staticmethod
    def _preview_of(
        message_type: str, content: dict[str, Any], template: MessageTemplate | None
    ) -> str:
        """What the inbox shows for this message.

        A template renders to the text the customer will actually read; anything else falls back to
        the shared rule, so the inbox never shows the operator a placeholder it cannot explain.
        """
        if template is None:
            return ConversationService.preview_of(message_type, content)
        spec = content.get("template") or {}
        rendered = render(
            template.components_json or [],
            header=list(spec.get("header") or []),
            body=list(spec.get("body") or []),
        )
        return rendered["body"] or f"[{template.name}]"

    @staticmethod
    def _require_window(conversation: Conversation, message_type: MessageType) -> None:
        """Free-form is only allowed inside the 24-hour window (FR-WA-12, Doc 04 §18.2)."""
        if message_type in FREE_FORM and not conversation.window_is_open:
            raise WindowClosedError(
                "The 24-hour customer-service window is closed for this conversation; "
                "use an approved template to re-engage."
            )

    # --- Deliver (queue path) -----------------------------------------------
    async def deliver(self, message_pk: int) -> dict[str, Any]:
        """Hand the message to the channel and record what it said (Doc 06 §2.3).

        Idempotent by `wamid` (Doc 06 §8): a redelivered task finds the id the channel already
        gave us and stops, because at-least-once delivery must not become at-least-once *sending*.
        """
        message = await self._messages.get_by_id(message_pk)
        if message is None:
            logger.warning("send_message_missing", extra={"message_pk": message_pk})
            return {"status": "missing", "message_pk": message_pk}
        if message.wamid:
            return {"status": "already_sent", "message_pk": message_pk, "wamid": message.wamid}
        if message.status == MSG_FAILED:
            return {"status": MSG_FAILED, "message_pk": message_pk}

        number = await self._numbers.get_by_id(message.phone_number_id)
        waba = await self._wabas.get_by_id(number.waba_id) if number else None
        if number is None or waba is None:
            raise ChannelError("the sending number is no longer connected")

        contact = await self._contacts.get_by_id(message.contact_id)
        recipient = contact.wa_id if contact else ""
        # Before the adapter, not after: the gate exists to stop the call, not to measure it.
        decision = await RateGate().acquire(
            number, recipient=recipient, category=message.category
        )
        if not decision.allowed:
            if decision.terminal:
                return await self.fail(
                    message.id,
                    error=f"marketing is paused on {number.display_number} (quality RED)",
                    code=decision.reason,
                )
            raise SendThrottled(
                f"number {number.display_number} is at its {decision.reason} limit",
                reason=decision.reason,
                retry_after=decision.retry_after,
            )

        adapter = WabaService(self._session).adapter_for(
            waba, phone_number_id=number.phone_number_id
        )
        try:
            # A stored asset becomes a channel id here, at the last moment: the id expires, so
            # resolving it at accept time would let it lapse in the queue (Doc 07 §17.3).
            media_id = await self._resolve_media(message, adapter)
            result = await adapter.send(
                self._outbound(message, to=recipient, media_id=media_id)
            )
        finally:
            await adapter.close()

        # The channel has accepted it; `sent`/`delivered`/`read` arrive by webhook (Doc 06 §11) and
        # advance the row from here, which is why the status is not touched.
        message.wamid = result.channel_message_id
        await self._messages.flush()
        await self._session.commit()
        return {"status": "sent", "message_pk": message_pk, "wamid": message.wamid}

    async def _resolve_media(self, message: Message, adapter) -> str | None:
        """Upload the referenced asset to the channel and return its id (Doc 07 §17.3)."""
        if message.media_asset_id is None:
            return None
        asset = await self._assets.get_by_id(message.media_asset_id)
        if asset is None:
            raise ChannelError(f"media asset {message.media_asset_id} no longer exists")
        return await MediaIngestService(self._session).channel_media_id(asset, adapter)

    @staticmethod
    def _outbound(message: Message, *, to: str, media_id: str | None = None) -> OutboundMessage:
        """Ledger row → the canonical message the adapter sends. No channel vocabulary here."""
        content = message.content_json or {}
        if "body" in content:
            return OutboundMessage(
                to=to,
                type=MessageType.TEXT,
                content=TextContent(
                    body=content["body"], preview_url=bool(content.get("preview_url"))
                ),
            )
        if "media" in content:
            media = content["media"]
            # A resolved asset wins: it is the id the channel just told us it has.
            reference = media_id or media.get("channel_media_id")
            return OutboundMessage(
                to=to,
                type=MessageType.MEDIA,
                content=MediaContent(
                    kind=MediaKind(media["kind"]),
                    media_id=reference,
                    # The adapter requires exactly one source; an uploaded asset replaces the link.
                    link=None if reference else media.get("link"),
                    caption=media.get("caption"),
                    filename=media.get("filename"),
                ),
            )
        if "interactive" in content:
            return OutboundMessage(
                to=to,
                type=MessageType.INTERACTIVE,
                content=InteractiveContent(payload=content["interactive"]),
            )
        if "template" in content:
            spec = content["template"]
            header_media = spec.get("header_media") or {}
            return OutboundMessage(
                to=to,
                type=MessageType.TEMPLATE,
                # Values, never components: building Graph's parameter lists is the adapter's job
                # (Doc 07 §5.3).
                content=TemplateContent(
                    name=spec["name"],
                    language=spec["language"],
                    header=list(spec.get("header") or []),
                    body=list(spec.get("body") or []),
                    buttons=[
                        TemplateButtonValue(
                            index=int(b["index"]), type=str(b["type"]), value=str(b["value"])
                        )
                        for b in spec.get("buttons") or []
                    ],
                    header_media=MediaContent(
                        kind=MediaKind(header_media["kind"]),
                        media_id=media_id or header_media.get("channel_media_id"),
                        link=None if media_id else header_media.get("link"),
                    )
                    if header_media
                    else None,
                ),
            )
        raise ChannelError(f"message {message.id} carries no sendable content")

    async def fail(self, message_pk: int, *, error: str, code: str | None = None) -> dict[str, Any]:
        """Terminal send failure: the ledger is where this belongs, not a parked task.

        `messages.status`/`error_code` and the status history are what the operator, the inbox and
        analytics read (Doc 03 §9.2/§9.3) — parking it in the generic DLQ would hide the outcome
        from every one of them.
        """
        message = await self._messages.get_by_id(message_pk)
        if message is None:
            return {"status": "missing", "message_pk": message_pk}
        message.status = MSG_FAILED
        message.error_code = (code or None) and code[:24]
        await self._history.add(
            MessageStatusHistory(
                message_id=message.id,
                wamid=message.wamid,
                status=MSG_FAILED,
                error_code=message.error_code,
                error_detail=error[:512],
                occurred_at=utcnow(),
            )
        )
        await self._session.commit()
        logger.error("send_failed", extra={"message_pk": message_pk, "error": error[:256]})
        return {"status": MSG_FAILED, "message_pk": message_pk, "error": error[:256]}
