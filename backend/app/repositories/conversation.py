"""Conversation repository (Doc 03 §9.1)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, or_, select

from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.conversation_tag import conversation_tags
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    model = Conversation

    async def get_for_number_contact(
        self, phone_number_pk: int, contact_pk: int
    ) -> Conversation | None:
        """The thread for a (number, contact) pair — the ``uq_conv_number_contact`` key.

        Soft-deleted rows still hold the unique key, so this deliberately ignores ``deleted_at``:
        an inbound message on an archived thread revives it rather than colliding with it.
        """
        stmt = select(Conversation).where(
            Conversation.phone_number_id == phone_number_pk,
            Conversation.contact_id == contact_pk,
        )
        return (await self.session.scalars(stmt)).first()

    async def get_for_endpoint_contact(
        self, channel_endpoint_pk: int, contact_pk: int
    ) -> Conversation | None:
        """The thread for a (channel endpoint, contact) pair — the ``uq_conv_endpoint_contact``
        key (QR-08). The provider-neutral analogue of :meth:`get_for_number_contact`, kept as its
        own straight-line method rather than a unified/branching one so a WAHA read can never be
        satisfied by a Meta row or vice versa (ADR-0020 "independent failure domains").
        """
        stmt = select(Conversation).where(
            Conversation.channel_endpoint_id == channel_endpoint_pk,
            Conversation.contact_id == contact_pk,
        )
        return (await self.session.scalars(stmt)).first()

    async def get_active_by_uuid(
        self, organization_id: int, public_id: bytes
    ) -> Conversation | None:
        """An active thread by its public id, scoped to the caller's org (Doc 04 §18.1).

        Org-scoped so a valid uuid from another tenant reads as a 404, not another org's thread.
        """
        stmt = select(Conversation).where(
            Conversation.organization_id == organization_id,
            Conversation.uuid == public_id,
            Conversation.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def list_page(
        self,
        organization_id: int,
        *,
        contact_id: int | None = None,
        status: str | None = None,
        assignee_id: int | None = None,
        unassigned: bool = False,
        phone_number_id: int | None = None,
        tag_id: int | None = None,
        q: str | None = None,
        limit: int,
        cursor: tuple[datetime, int] | None = None,
    ) -> tuple[list[Conversation], bool]:
        """A keyset page of the inbox, newest activity first (Doc 04 §18.1).

        Ordered by ``last_message_at``, as the frozen contract requires — but the column is nullable
        (a thread can exist before its first message settles the preview), so the sort key is
        ``COALESCE(last_message_at, created_at)``: never null, so the keyset cursor is always
        well-defined, and equal to ``last_message_at`` for every thread that has one.
        """
        # The effective, never-null sort key. `ix_conv_org_status` covers the org+status prefix;
        # the coalesce is a small ordering cost on an already-filtered set.
        sort_key = func.coalesce(Conversation.last_message_at, Conversation.created_at)
        clauses = [
            Conversation.organization_id == organization_id,
            Conversation.deleted_at.is_(None),
        ]
        if contact_id is not None:
            clauses.append(Conversation.contact_id == contact_id)
        if status:
            clauses.append(Conversation.status == status)
        if unassigned:
            clauses.append(Conversation.assigned_user_id.is_(None))
        elif assignee_id is not None:
            clauses.append(Conversation.assigned_user_id == assignee_id)
        if phone_number_id is not None:
            clauses.append(Conversation.phone_number_id == phone_number_id)

        stmt = select(Conversation)
        if tag_id is not None:
            # The by-tag folder (Doc 04 §18.1, v1.3): threads carrying tag X, via the reverse index
            # `ix_convtag_tag`. Single tag only — multi-tag AND/OR filtering is out of scope.
            stmt = stmt.join(
                conversation_tags, conversation_tags.c.conversation_id == Conversation.id
            )
            clauses.append(conversation_tags.c.tag_id == tag_id)
        if q:
            # Search the customer the thread is with — name or number — which is what "search the
            # inbox" means (Doc 05 B7); message-text search is the separate `/messages/search`.
            like = f"%{q}%"
            stmt = stmt.join(Contact, Contact.id == Conversation.contact_id)
            clauses.append(
                or_(
                    Contact.full_name.like(like),
                    Contact.profile_name.like(like),
                    Contact.phone_e164.like(like),
                    Contact.wa_id.like(like),
                )
            )
        if cursor is not None:
            c_ts, c_id = cursor
            clauses.append(
                or_(sort_key < c_ts, and_(sort_key == c_ts, Conversation.id < c_id))
            )

        stmt = (
            stmt.where(*clauses)
            .order_by(sort_key.desc(), Conversation.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self.session.scalars(stmt)).all())
        return rows[:limit], len(rows) > limit
