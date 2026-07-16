"""Custom attribute service (Doc 04 §14.1/§14.4, Doc 03 §6.3) — FR-CON-11.

Definition CRUD plus typed value writes on a contact. Values are validated against the
declared ``data_type`` (422 on mismatch) and stored in the matching typed column. Hot
(``is_indexed``) attributes are mirrored into ``contacts.attributes_cache`` for fast list
rendering (Doc 03 §6.3). Every change is audited.
"""

from __future__ import annotations

import uuid as uuidlib
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.crm.attribute_types import (
    DATA_TYPES,
    TYPE_ENUM,
    VALUE_COLUMN,
    AttributeValueError,
    coerce_value,
    read_value,
)
from app.db.mixins import utcnow
from app.models.attribute import ContactAttributeValue, CustomAttributeDefinition
from app.models.contact import Contact
from app.models.contact_event import EVENT_CONTACT_UPDATED
from app.models.user import User
from app.repositories.attribute import (
    AttributeDefinitionRepository,
    ContactAttributeValueRepository,
)
from app.repositories.contact import ContactRepository
from app.services.audit_service import AuditAction, AuditService
from app.services.contact_event_service import ContactEventService

_VALUE_FIELDS = ("value_string", "value_number", "value_datetime", "value_boolean")


class AttributeService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._defs = AttributeDefinitionRepository(session)
        self._values = ContactAttributeValueRepository(session)
        self._contacts = ContactRepository(session)
        self._events = ContactEventService(session)
        self._audit = AuditService(session)

    # --- Definitions ---------------------------------------------------------
    async def list_definitions(self, organization_id: int) -> list[CustomAttributeDefinition]:
        return await self._defs.list_for_org(organization_id)

    async def get_definition(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> CustomAttributeDefinition:
        definition = await self._defs.get_active_by_uuid(organization_id, public_id.bytes)
        if definition is None:
            raise NotFoundError("Custom attribute not found.")
        return definition

    @staticmethod
    def _validate_definition(data_type: str, enum_values: list[str] | None) -> None:
        if data_type not in DATA_TYPES:
            raise ValidationError(
                "Invalid attribute definition.",
                errors=[
                    {
                        "field": "data_type",
                        "code": "invalid_type",
                        "message": f"must be one of {list(DATA_TYPES)}",
                    }
                ],
            )
        if data_type == TYPE_ENUM and not enum_values:
            raise ValidationError(
                "Invalid attribute definition.",
                errors=[
                    {
                        "field": "enum_values",
                        "code": "required",
                        "message": "enum attributes require a non-empty enum_values list",
                    }
                ],
            )

    async def create_definition(
        self,
        *,
        organization_id: int,
        actor: User,
        key_name: str,
        label: str,
        data_type: str,
        enum_values: list[str] | None,
        is_indexed: bool,
        is_pii: bool,
    ) -> CustomAttributeDefinition:
        self._validate_definition(data_type, enum_values)
        if await self._defs.get_by_key(organization_id, key_name) is not None:
            raise ConflictError(f"An attribute named {key_name!r} already exists.")
        definition = CustomAttributeDefinition(
            organization_id=organization_id,
            key_name=key_name,
            label=label,
            data_type=data_type,
            enum_values_json=enum_values,
            is_indexed=is_indexed,
            is_pii=is_pii,
        )
        await self._defs.add(definition)
        await self._audit.record(
            AuditAction.ATTRIBUTE_CREATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="custom_attribute",
            entity_id=definition.id,
            after={"key_name": key_name, "data_type": data_type},
        )
        await self._session.commit()
        return definition

    async def update_definition(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        label: str | None,
        enum_values: list[str] | None,
        is_indexed: bool | None,
        is_pii: bool | None,
    ) -> CustomAttributeDefinition:
        """Update label / indexing / enum values (Doc 04 §14.4).

        ``key_name`` and ``data_type`` are immutable: changing them would invalidate every
        stored value's column and any segment rule referencing the key.
        """
        definition = await self.get_definition(organization_id, public_id)
        before = {"label": definition.label, "is_indexed": definition.is_indexed}
        if enum_values is not None:
            self._validate_definition(definition.data_type, enum_values)
            definition.enum_values_json = enum_values
        if label is not None:
            definition.label = label
        if is_indexed is not None:
            definition.is_indexed = is_indexed
        if is_pii is not None:
            definition.is_pii = is_pii
        await self._defs.flush()
        await self._audit.record(
            AuditAction.ATTRIBUTE_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="custom_attribute",
            entity_id=definition.id,
            before=before,
            after={"label": definition.label, "is_indexed": definition.is_indexed},
        )
        await self._session.commit()
        return definition

    async def delete_definition(
        self, *, organization_id: int, actor: User, public_id: uuidlib.UUID
    ) -> None:
        """Remove the definition and all its values (Doc 04 §14.4)."""
        definition = await self.get_definition(organization_id, public_id)
        removed = await self._values.delete_for_attribute(definition.id)
        definition.deleted_at = utcnow()
        await self._defs.flush()
        await self._audit.record(
            AuditAction.ATTRIBUTE_DELETED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="custom_attribute",
            entity_id=definition.id,
            before={"key_name": definition.key_name},
            metadata={"values_removed": removed},
        )
        await self._session.commit()

    # --- Values on a contact -------------------------------------------------
    async def refresh_cache(self, contact: Contact) -> None:
        """Mirror indexed (hot) attributes into ``contacts.attributes_cache`` (Doc 03 §6.3).

        Public because any writer that moves attribute values (e.g. a duplicate merge) must
        rebuild the cache by the same rule rather than restating it.
        """
        rows = await self._values.list_for_contact(contact.id)
        cache: dict[str, Any] = {}
        for row in rows:
            definition = await self._defs.get_by_id(row.attribute_id)
            if definition is None or not definition.is_indexed:
                continue
            value = read_value(definition.data_type, row)
            cache[definition.key_name] = value.isoformat() if hasattr(value, "isoformat") else value
        contact.attributes_cache = cache or None

    async def set_contact_attributes(
        self,
        *,
        organization_id: int,
        actor: User,
        contact_uuid: uuidlib.UUID,
        values: dict[str, Any],
    ) -> Contact:
        """Set custom attribute values for a contact (Doc 04 §14.1 — 422 on type mismatch)."""
        contact = await self._contacts.get_active_by_uuid(organization_id, contact_uuid.bytes)
        if contact is None:
            raise NotFoundError("Contact not found.")

        errors: list[dict[str, str]] = []
        resolved: list[tuple[CustomAttributeDefinition, Any]] = []
        for key, raw in values.items():
            definition = await self._defs.get_by_key(organization_id, key)
            if definition is None:
                errors.append(
                    {"field": key, "code": "unknown_attribute", "message": "no such attribute"}
                )
                continue
            try:
                resolved.append(
                    (definition, coerce_value(definition.data_type, raw, definition.enum_values_json))
                )
            except AttributeValueError as exc:
                errors.append({"field": key, "code": "invalid_value", "message": str(exc)})
        if errors:
            raise ValidationError("One or more attribute values are invalid.", errors=errors)

        for definition, value in resolved:
            if value is None:
                await self._values.delete_value(contact.id, definition.id)
                continue
            row = await self._values.get(contact.id, definition.id)
            if row is None:
                row = ContactAttributeValue(contact_id=contact.id, attribute_id=definition.id)
                self._session.add(row)
            for field in _VALUE_FIELDS:
                setattr(row, field, None)
            setattr(row, VALUE_COLUMN[definition.data_type], value)
        await self._session.flush()

        await self.refresh_cache(contact)
        contact.updated_by = actor.id
        contact.row_version += 1
        await self._contacts.flush()
        await self._events.record(
            organization_id=organization_id,
            contact_id=contact.id,
            event_type=EVENT_CONTACT_UPDATED,
            payload={"attributes": sorted(values.keys())},
        )
        await self._audit.record(
            AuditAction.CONTACT_ATTRIBUTES_SET,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="contact",
            entity_id=contact.id,
            after={"attributes": sorted(values.keys())},
        )
        await self._session.commit()
        await self._session.refresh(contact, ["tags", "attribute_values"])
        return contact
