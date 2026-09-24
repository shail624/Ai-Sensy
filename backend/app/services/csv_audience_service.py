"""Turn the numbers in an uploaded CSV into contacts for a broadcast (UI-AIS-16, "CSV Broadcast").

Each number becomes the customer it already is, or a new contact (``source="csv_broadcast"``); the
resulting ids feed the campaign wizard's "Selected contacts" audience, so the broadcast then goes
through the ordinary campaign path — templates, opt-out protection, approval and scheduling.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.user import User
from app.repositories.contact import ContactRepository
from app.services.audit_service import AuditService
from app.services.conversation_service import ConversationService
from app.services.whatsapp_qr_service import normalize_phone_input

MAX_ROWS = 5000
SOURCE = "csv_broadcast"


@dataclass(slots=True)
class ResolvedAudience:
    contact_ids: list[str] = field(default_factory=list)
    created: int = 0
    existing: int = 0
    #: Row numbers (1-based, as in the uploaded file) whose number could not be read.
    invalid_rows: list[int] = field(default_factory=list)


class CsvAudienceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._conversations = ConversationService(session)
        self._contacts = ContactRepository(session)

    async def resolve(
        self, *, organization_id: int, actor: User, rows: list[tuple[str, str | None]]
    ) -> ResolvedAudience:
        if not rows:
            raise ValidationError("The file has no numbers.")
        if len(rows) > MAX_ROWS:
            raise ValidationError(f"Upload at most {MAX_ROWS:,} numbers at a time.")
        result = ResolvedAudience()
        seen: set[str] = set()
        for index, (phone, name) in enumerate(rows, start=1):
            try:
                wa_id = normalize_phone_input(phone)
            except ValidationError:
                result.invalid_rows.append(index)
                continue
            if wa_id in seen:
                continue
            seen.add(wa_id)
            before = await self._contacts.get_active_by_wa_id(organization_id, wa_id)
            contact = before or await self._conversations.resolve_recipient(
                organization_id=organization_id, wa_id=wa_id, source=SOURCE
            )
            if before is None:
                result.created += 1
                clean = (name or "").strip()
                if clean and not contact.full_name:
                    contact.full_name = clean[:160]
            else:
                result.existing += 1
            result.contact_ids.append(contact.public_id)

        await AuditService(self._session).record(
            "contacts.csv_audience_resolved",
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="contact",
            after={
                "numbers": len(result.contact_ids),
                "created": result.created,
                "invalid": len(result.invalid_rows),
            },
        )
        await self._session.commit()
        return result
