"""Custom attribute schemas (Doc 04 §14.1/§14.4)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.crm.attribute_types import read_value
from app.models.attribute import ContactAttributeValue, CustomAttributeDefinition


class AttributeDefinitionResponse(BaseModel):
    id: str
    type: str = "custom_attribute"
    key_name: str
    label: str
    data_type: str
    enum_values: list[str] | None
    is_indexed: bool
    is_pii: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_definition(cls, definition: CustomAttributeDefinition) -> AttributeDefinitionResponse:
        return cls(
            id=definition.public_id,
            key_name=definition.key_name,
            label=definition.label,
            data_type=definition.data_type,
            enum_values=definition.enum_values_json,
            is_indexed=definition.is_indexed,
            is_pii=definition.is_pii,
            created_at=definition.created_at,
            updated_at=definition.updated_at,
        )


class AttributeDefinitionCreateRequest(BaseModel):
    key_name: str = Field(min_length=1, max_length=60)
    label: str = Field(min_length=1, max_length=120)
    data_type: str = Field(max_length=16)
    enum_values: list[str] | None = None
    is_indexed: bool = False
    is_pii: bool = False


class AttributeDefinitionUpdateRequest(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    enum_values: list[str] | None = None
    is_indexed: bool | None = None
    is_pii: bool | None = None


class ContactAttributesRequest(BaseModel):
    """Set custom attribute values on a contact; ``null`` clears a value (Doc 04 §14.1)."""

    attributes: dict[str, Any] = Field(min_length=1)


def attributes_map(values: list[ContactAttributeValue]) -> dict[str, Any]:
    """Build the contact schema's ``attributes`` map from typed value rows (Doc 04 §14)."""
    result: dict[str, Any] = {}
    for row in values:
        definition = row.definition
        if definition is None or definition.deleted_at is not None:
            continue
        result[definition.key_name] = read_value(definition.data_type, row)
    return result
