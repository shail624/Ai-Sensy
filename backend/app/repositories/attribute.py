"""Custom attribute repositories (Doc 03 §6.3)."""

from __future__ import annotations

from sqlalchemy import delete, select

from app.models.attribute import ContactAttributeValue, CustomAttributeDefinition
from app.repositories._result import affected_rows
from app.repositories.base import BaseRepository


class AttributeDefinitionRepository(BaseRepository[CustomAttributeDefinition]):
    model = CustomAttributeDefinition

    async def list_for_org(self, organization_id: int) -> list[CustomAttributeDefinition]:
        stmt = (
            select(CustomAttributeDefinition)
            .where(
                CustomAttributeDefinition.organization_id == organization_id,
                CustomAttributeDefinition.deleted_at.is_(None),
            )
            .order_by(CustomAttributeDefinition.key_name)
        )
        return list((await self.session.scalars(stmt)).all())

    async def get_active_by_uuid(
        self, organization_id: int, public_id: bytes
    ) -> CustomAttributeDefinition | None:
        stmt = select(CustomAttributeDefinition).where(
            CustomAttributeDefinition.organization_id == organization_id,
            CustomAttributeDefinition.uuid == public_id,
            CustomAttributeDefinition.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()

    async def get_by_key(
        self, organization_id: int, key_name: str
    ) -> CustomAttributeDefinition | None:
        stmt = select(CustomAttributeDefinition).where(
            CustomAttributeDefinition.organization_id == organization_id,
            CustomAttributeDefinition.key_name == key_name,
            CustomAttributeDefinition.deleted_at.is_(None),
        )
        return (await self.session.scalars(stmt)).first()


class ContactAttributeValueRepository(BaseRepository[ContactAttributeValue]):
    model = ContactAttributeValue

    async def get(self, contact_id: int, attribute_id: int) -> ContactAttributeValue | None:
        stmt = select(ContactAttributeValue).where(
            ContactAttributeValue.contact_id == contact_id,
            ContactAttributeValue.attribute_id == attribute_id,
        )
        return (await self.session.scalars(stmt)).first()

    async def list_for_contact(self, contact_id: int) -> list[ContactAttributeValue]:
        stmt = select(ContactAttributeValue).where(
            ContactAttributeValue.contact_id == contact_id
        )
        return list((await self.session.scalars(stmt)).all())

    async def delete_for_attribute(self, attribute_id: int) -> int:
        result = await self.session.execute(
            delete(ContactAttributeValue).where(
                ContactAttributeValue.attribute_id == attribute_id
            )
        )
        await self.session.flush()
        return affected_rows(result)

    async def delete_value(self, contact_id: int, attribute_id: int) -> int:
        result = await self.session.execute(
            delete(ContactAttributeValue).where(
                ContactAttributeValue.contact_id == contact_id,
                ContactAttributeValue.attribute_id == attribute_id,
            )
        )
        await self.session.flush()
        return affected_rows(result)
