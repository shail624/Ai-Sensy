"""Conversation repository (Doc 03 §9.1)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.sql.elements import ColumnElement

from app.models.audit import AuditLog
from app.models.contact import Contact
from app.models.conversation import CONV_OPEN, CONV_PENDING, CONV_RESOLVED, Conversation
from app.models.conversation_tag import conversation_tags
from app.models.message import Message
from app.models.task import TASK_STATUS_OPEN, Task
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

    @staticmethod
    def _customer_match(q: str) -> ColumnElement[bool]:
        """Search the customer the thread is with — name or number — which is what "search the
        inbox" means (Doc 05 B7); message-text search is the separate ``/messages/search``.

        Shared by the list page and the category counts: a count computed over different fields
        than the list it labels would describe a result the operator never sees.
        """
        like = f"%{q}%"
        return or_(
            Contact.full_name.like(like),
            Contact.profile_name.like(like),
            Contact.phone_e164.like(like),
            Contact.wa_id.like(like),
        )

    async def category_counts(
        self, organization_id: int, *, viewer_id: int, q: str | None = None
    ) -> tuple[int, int, int]:
        """Totals for the three inbox categories: active, requesting, intervened.

        Scoped by ``q`` and nothing else, because activating a category *replaces* the status,
        assignee and tag filters and carries only the search term across. A badge counted with
        the current status or assignee applied would advertise a list the click never produces.

        One aggregate over one scan, rather than three round trips: the inbox polls these, and
        ``ix_conv_org_status`` and ``ix_conv_assignee`` already cover the predicates.
        """
        totals = select(
            func.coalesce(
                func.sum(case((Conversation.status == CONV_OPEN, 1), else_=0)), 0
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Conversation.status == CONV_OPEN,
                                Conversation.assigned_user_id.is_(None),
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(case((Conversation.assigned_user_id == viewer_id, 1), else_=0)), 0
            ),
        ).where(
            Conversation.organization_id == organization_id,
            Conversation.deleted_at.is_(None),
        )
        if q:
            totals = totals.join(Contact, Contact.id == Conversation.contact_id).where(
                self._customer_match(q)
            )
        active, requesting, intervened = (await self.session.execute(totals)).one()
        return int(active), int(requesting), int(intervened)

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
        activity_from: datetime | None = None,
        activity_to: datetime | None = None,
        campaign_id: int | None = None,
        has_media: bool = False,
        has_audit: bool = False,
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
        if activity_from is not None:
            clauses.append(sort_key >= activity_from)
        if activity_to is not None:
            clauses.append(sort_key < activity_to)
        if campaign_id is not None:
            clauses.append(
                select(Message.id)
                .where(
                    Message.organization_id == organization_id,
                    Message.conversation_id == Conversation.id,
                    Message.campaign_id == campaign_id,
                )
                .exists()
            )
        if has_media:
            clauses.append(
                select(Message.id)
                .where(
                    Message.organization_id == organization_id,
                    Message.conversation_id == Conversation.id,
                    Message.media_asset_id.is_not(None),
                )
                .exists()
            )
        if has_audit:
            # Only direct conversation actions are in scope: assignment and status events use
            # ``entity_type=conversation``. Internal-note contents and message provider events are
            # deliberately not inferred or exposed by this list filter.
            clauses.append(
                select(AuditLog.id)
                .where(
                    AuditLog.organization_id == organization_id,
                    AuditLog.entity_type == "conversation",
                    AuditLog.entity_id == Conversation.id,
                )
                .exists()
            )

        stmt = select(Conversation)
        if tag_id is not None:
            # The by-tag folder (Doc 04 §18.1, v1.3): threads carrying tag X, via the reverse index
            # `ix_convtag_tag`. Single tag only — multi-tag AND/OR filtering is out of scope.
            stmt = stmt.join(
                conversation_tags, conversation_tags.c.conversation_id == Conversation.id
            )
            clauses.append(conversation_tags.c.tag_id == tag_id)
        if q:
            stmt = stmt.join(Contact, Contact.id == Conversation.contact_id)
            clauses.append(self._customer_match(q))
        if cursor is not None:
            c_ts, c_id = cursor
            clauses.append(or_(sort_key < c_ts, and_(sort_key == c_ts, Conversation.id < c_id)))

        stmt = (
            stmt.where(*clauses).order_by(sort_key.desc(), Conversation.id.desc()).limit(limit + 1)
        )
        rows = list((await self.session.scalars(stmt)).all())
        return rows[:limit], len(rows) > limit

    async def active_counts_by_assignee(
        self, organization_id: int, assignee_ids: list[int]
    ) -> dict[int, int]:
        """Open workload used by the organization assignment policy."""
        if not assignee_ids:
            return {}
        stmt = (
            select(Conversation.assigned_user_id, func.count(Conversation.id))
            .where(
                Conversation.organization_id == organization_id,
                Conversation.deleted_at.is_(None),
                Conversation.status != CONV_RESOLVED,
                Conversation.assigned_user_id.in_(assignee_ids),
            )
            .group_by(Conversation.assigned_user_id)
        )
        return {
            int(assignee_id): int(count)
            for assignee_id, count in (await self.session.execute(stmt)).all()
            if assignee_id is not None
        }

    async def lock_by_id(self, organization_id: int, conversation_id: int) -> Conversation | None:
        """Serialize per-thread policy decisions and refresh facts changed by a prior waiter."""
        stmt = (
            select(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.organization_id == organization_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return (await self.session.scalars(stmt)).first()

    async def auto_resolve_candidates(
        self, *, organization_id: int, cutoff: datetime, limit: int
    ) -> list[Conversation]:
        """A bounded candidate scan; the service row-locks and rechecks before mutation."""
        open_task = (
            select(Task.id)
            .where(
                Task.organization_id == organization_id,
                Task.conversation_id == Conversation.id,
                Task.status == TASK_STATUS_OPEN,
                Task.deleted_at.is_(None),
            )
            .exists()
        )
        stmt = (
            select(Conversation)
            .where(
                Conversation.organization_id == organization_id,
                Conversation.deleted_at.is_(None),
                Conversation.status.in_((CONV_OPEN, CONV_PENDING)),
                Conversation.unread_count == 0,
                Conversation.last_message_at.is_not(None),
                Conversation.last_message_at <= cutoff,
                Conversation.updated_at <= cutoff,
                ~open_task,
            )
            .order_by(Conversation.last_message_at, Conversation.id)
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).all())
