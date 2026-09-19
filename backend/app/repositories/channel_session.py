"""Tenant-scoped persistence queries for provider-neutral channel sessions."""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime

from sqlalchemy import Select, select

from app.channels.runtime import PairingState
from app.channels.session import SESSION_TERMINAL_STATES, SessionState
from app.models.channel_session import ChannelSession
from app.repositories.base import BaseRepository

_TERMINAL_VALUES = tuple(state.value for state in SESSION_TERMINAL_STATES)


class ChannelSessionRepository(BaseRepository[ChannelSession]):
    model = ChannelSession

    @staticmethod
    def _active(stmt: Select[tuple[ChannelSession]]) -> Select[tuple[ChannelSession]]:
        return stmt.where(ChannelSession.deleted_at.is_(None))

    async def get_scoped(
        self,
        organization_id: int,
        public_id: uuidlib.UUID,
        *,
        for_update: bool = False,
        include_deleted: bool = False,
    ) -> ChannelSession | None:
        stmt = select(ChannelSession).where(
            ChannelSession.organization_id == organization_id,
            ChannelSession.uuid == public_id.bytes,
        )
        if not include_deleted:
            stmt = self._active(stmt)
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.session.scalars(stmt)).first()

    async def list_scoped(
        self,
        organization_id: int,
        *,
        connection_id: int | None = None,
        states: frozenset[SessionState] | None = None,
        include_deleted: bool = False,
    ) -> list[ChannelSession]:
        stmt = select(ChannelSession).where(ChannelSession.organization_id == organization_id)
        if connection_id is not None:
            stmt = stmt.where(ChannelSession.connection_id == connection_id)
        if states:
            stmt = stmt.where(ChannelSession.state.in_(tuple(state.value for state in states)))
        if not include_deleted:
            stmt = self._active(stmt)
        stmt = stmt.order_by(
            ChannelSession.connection_id.asc(),
            ChannelSession.session_revision.desc(),
            ChannelSession.id.desc(),
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_current_for_connection(
        self,
        organization_id: int,
        connection_id: int,
        *,
        for_update: bool = False,
        include_terminal: bool = False,
    ) -> ChannelSession | None:
        stmt = self._active(
            select(ChannelSession).where(
                ChannelSession.organization_id == organization_id,
                ChannelSession.connection_id == connection_id,
            )
        )
        if not include_terminal:
            stmt = stmt.where(ChannelSession.state.not_in(_TERMINAL_VALUES))
        stmt = stmt.order_by(
            ChannelSession.session_revision.desc(), ChannelSession.id.desc()
        ).limit(1)
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.session.scalars(stmt)).first()

    async def get_latest_revision(
        self, organization_id: int, connection_id: int
    ) -> ChannelSession | None:
        stmt = (
            select(ChannelSession)
            .where(
                ChannelSession.organization_id == organization_id,
                ChannelSession.connection_id == connection_id,
            )
            .order_by(ChannelSession.session_revision.desc(), ChannelSession.id.desc())
            .limit(1)
        )
        return (await self.session.scalars(stmt)).first()

    async def list_due_pairings(
        self, organization_id: int, at: datetime, *, limit: int = 100
    ) -> list[ChannelSession]:
        """Lock non-terminal pairing revisions whose published availability has expired."""

        stmt = (
            self._active(
                select(ChannelSession).where(
                    ChannelSession.organization_id == organization_id,
                    ChannelSession.pairing_state == PairingState.PAIRING_AVAILABLE.value,
                    ChannelSession.pairing_expires_at.is_not(None),
                    ChannelSession.pairing_expires_at <= at,
                )
            )
            .order_by(ChannelSession.pairing_expires_at.asc(), ChannelSession.id.asc())
            .limit(limit)
            .with_for_update()
        )
        return list((await self.session.scalars(stmt)).all())

    async def list_due_for_expiration(
        self, organization_id: int, at: datetime
    ) -> list[ChannelSession]:
        stmt = (
            self._active(
                select(ChannelSession).where(
                    ChannelSession.organization_id == organization_id,
                    ChannelSession.expires_at.is_not(None),
                    ChannelSession.expires_at <= at,
                    ChannelSession.state.not_in(_TERMINAL_VALUES),
                )
            )
            .order_by(ChannelSession.expires_at.asc(), ChannelSession.id.asc())
            .with_for_update()
        )
        return list((await self.session.scalars(stmt)).all())
