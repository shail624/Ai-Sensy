"""Shared-inbox collaboration service (Doc 04 §18.1; Doc 05 Shared Inbox) — Phase 7 Step 1.

The **actor-driven** half of the inbox: an agent assigning a thread, moving its status, or leaving a
note for a colleague. Deliberately separate from
:class:`~app.services.conversation_service.ConversationService`, which is **system-driven** — it
upserts threads and windows from inbound webhooks and has no actor. Mixing the two would put "who is
the customer" logic next to "who owns this thread", which are opposite contracts (one must never
reject, the other authorizes every call).

It reuses the existing primitives rather than restating them: the ``conversations`` row already
carries ``status`` and ``assigned_user_id`` (Module 4), so status and assignment are transitions on
an existing row, and only the ``internal_notes`` table is new. Every mutation is audited through the
shared framework and bumps ``row_version``.
"""

from __future__ import annotations

import uuid as uuidlib
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.db.mixins import utcnow
from app.models.conversation import CONV_STATUSES, Conversation
from app.models.internal_note import InternalNote
from app.models.user import User
from app.repositories.conversation import ConversationRepository
from app.repositories.internal_note import InternalNoteRepository
from app.repositories.user import UserRepository
from app.services.audit_service import AuditAction, AuditService

logger = get_logger(__name__)


class AssigneeInvalid(ValidationError):
    """The assignment target is not a user who can own a thread here (Doc 04 §18.1 → 422)."""

    code = "assignee_invalid"
    title = "Invalid Assignee"


class ConversationStatusInvalid(ValidationError):
    """The requested status is not one of the four the schema allows (Doc 03 §9.1 → 422)."""

    code = "conversation_status_invalid"
    title = "Invalid Conversation Status"


@dataclass(slots=True)
class ConversationState:
    """The thread after an assignment or status transition (Doc 04 §18.1)."""

    public_id: str
    status: str
    #: The assignee's public id, or ``None`` when unassigned.
    assigned_to: str | None
    row_version: int
    updated_at: datetime


@dataclass(slots=True)
class NoteView:
    """One internal note, with its author rendered as a public id (Doc 04 §18.1)."""

    public_id: str
    author: str | None
    body: str
    created_at: datetime


class InboxService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._conversations = ConversationRepository(session)
        self._notes = InternalNoteRepository(session)
        self._users = UserRepository(session)
        self._audit = AuditService(session)

    # --- Assignment ----------------------------------------------------------
    async def assign(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        assignee_public_id: uuidlib.UUID,
    ) -> ConversationState:
        """Assign or reassign a conversation to a user (FR-INB; Doc 04 §18.1).

        The target must be an active user of the same organization — otherwise assigning would hand
        a thread to someone who cannot open it, or leak it across a tenant boundary (→ 422).
        """
        conversation = await self._conversation(organization_id, public_id)
        assignee = await self._resolve_assignee(organization_id, assignee_public_id)

        before = conversation.assigned_user_id
        conversation.assigned_user_id = assignee.id
        conversation.row_version += 1
        await self._conversations.flush()
        await self._audit.record(
            AuditAction.CONVERSATION_ASSIGNED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="conversation",
            entity_id=conversation.id,
            before={"assigned_user_id": before},
            after={"assigned_user_id": assignee.id},
        )
        await self._session.commit()
        return ConversationState(
            public_id=conversation.public_id,
            status=conversation.status,
            assigned_to=assignee.public_id,
            row_version=conversation.row_version,
            updated_at=conversation.updated_at,
        )

    async def _resolve_assignee(
        self, organization_id: int, assignee_public_id: uuidlib.UUID
    ) -> User:
        user = await self._users.get_by_uuid(assignee_public_id)
        if user is None or user.organization_id != organization_id or not user.is_active:
            # One 422 for every reason the target cannot own a thread — existence, tenancy and
            # active state are all "not a valid assignee" from the caller's side.
            raise AssigneeInvalid("The assignee is not an active user of this organization.")
        return user

    # --- Status --------------------------------------------------------------
    async def set_status(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID, status: str
    ) -> ConversationState:
        """Move a conversation to open/pending/resolved/snoozed (Doc 03 §9.1; Doc 04 §18.1).

        Snoozed is only a status here: snooze-until timers and SLA behaviour are out of this
        milestone, so nothing schedules a wake-up — the frozen schema stores a status, not a timer.
        """
        if status not in CONV_STATUSES:
            raise ConversationStatusInvalid(
                f"{status!r} is not a conversation status; use one of {', '.join(CONV_STATUSES)}."
            )
        conversation = await self._conversation(organization_id, public_id)

        before = conversation.status
        conversation.status = status
        conversation.row_version += 1
        await self._conversations.flush()
        await self._audit.record(
            AuditAction.CONVERSATION_STATUS_CHANGED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="conversation",
            entity_id=conversation.id,
            before={"status": before},
            after={"status": status},
        )
        await self._session.commit()
        return ConversationState(
            public_id=conversation.public_id,
            status=conversation.status,
            assigned_to=await self._assignee_public_id(conversation),
            row_version=conversation.row_version,
            updated_at=conversation.updated_at,
        )

    # --- Notes ---------------------------------------------------------------
    async def add_note(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID, body: str
    ) -> NoteView:
        """Leave a staff-only note on a conversation (Doc 04 §18.1)."""
        conversation = await self._conversation(organization_id, public_id)
        note = InternalNote(
            conversation_id=conversation.id, author_user_id=actor.id, body=body
        )
        await self._notes.add(note)
        await self._audit.record(
            AuditAction.INTERNAL_NOTE_ADDED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="internal_note",
            entity_id=note.id,
            after={"conversation_id": conversation.id},
        )
        await self._session.commit()
        return NoteView(
            public_id=note.public_id,
            author=actor.public_id,
            body=note.body,
            created_at=note.created_at,
        )

    async def list_notes(
        self, *, organization_id: int, public_id: uuidlib.UUID
    ) -> list[NoteView]:
        """A conversation's notes, oldest first, authors resolved to public ids (Doc 04 §18.1)."""
        conversation = await self._conversation(organization_id, public_id)
        notes = await self._notes.list_for_conversation(conversation.id)
        authors = await self._authors_for(notes)
        return [
            NoteView(
                public_id=note.public_id,
                author=authors.get(note.author_user_id),
                body=note.body,
                created_at=note.created_at,
            )
            for note in notes
        ]

    async def delete_note(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        note_public_id: uuidlib.UUID,
    ) -> None:
        """Soft-delete a note (Doc 04 §18.1).

        Soft, not hard: a removed note stays a record of what a colleague said. The note must belong
        to this conversation, so a uuid from another thread is a 404, not a cross-thread delete.
        """
        conversation = await self._conversation(organization_id, public_id)
        note = await self._notes.get_active_for_conversation(
            conversation.id, note_public_id.bytes
        )
        if note is None:
            raise NotFoundError("Note not found.")
        note.deleted_at = utcnow()
        await self._notes.flush()
        await self._audit.record(
            AuditAction.INTERNAL_NOTE_DELETED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="internal_note",
            entity_id=note.id,
            before={"conversation_id": conversation.id},
        )
        await self._session.commit()

    # --- Helpers -------------------------------------------------------------
    async def _authors_for(self, notes: list[InternalNote]) -> dict[int, str]:
        """Resolve every note's author to a public id in one query (no N+1 on the list)."""
        ids = {note.author_user_id for note in notes}
        if not ids:
            return {}
        rows = (await self._session.scalars(select(User).where(User.id.in_(ids)))).all()
        return {user.id: user.public_id for user in rows}

    async def _assignee_public_id(self, conversation: Conversation) -> str | None:
        if conversation.assigned_user_id is None:
            return None
        user = await self._users.get_by_id(conversation.assigned_user_id)
        return user.public_id if user is not None else None

    async def _conversation(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> Conversation:
        conversation = await self._conversations.get_active_by_uuid(
            organization_id, public_id.bytes
        )
        if conversation is None:
            raise NotFoundError("Conversation not found.")
        return conversation
