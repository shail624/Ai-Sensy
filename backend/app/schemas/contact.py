"""Contact schemas (Doc 04 §14.1)."""

from __future__ import annotations

import re
import uuid as uuidlib
from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator

from app.api.pagination import Page
from app.models.contact import OPT_IN_STATUSES, Contact
from app.models.reactivation_view import WorkspaceView
from app.schemas.attribute import attributes_map
from app.schemas.tag import TagSummary

# E.164: '+' then 8–15 digits, first digit non-zero (Doc 04 §14 validation).
_E164 = re.compile(r"^\+[1-9]\d{7,14}$")


def validate_e164(value: str) -> str:
    value = value.strip()
    if not _E164.match(value):
        raise ValueError("phone_e164 must be E.164, e.g. +14155552671")
    return value


def _validate_opt_in(value: str) -> str:
    if value not in OPT_IN_STATUSES:
        raise ValueError(f"opt_in_status must be one of {OPT_IN_STATUSES}")
    return value


class ContactResponse(BaseModel):
    id: str
    type: str = "contact"
    wa_id: str
    phone_e164: str
    country_code: str | None
    full_name: str | None
    first_name: str | None
    last_name: str | None
    email: str | None
    locale: str | None
    profile_name: str | None
    opt_in_status: str
    opt_in_at: datetime | None
    opt_out_at: datetime | None
    is_active_on_wa: bool | None
    last_inbound_at: datetime | None
    last_outbound_at: datetime | None
    last_contacted_at: datetime | None
    source: str | None
    #: Where the sale stands (``SALE_STATUSES``), set from Live Chat; ``null`` when not marked.
    sale_status: str | None = None
    #: The customer's number release date, when one is recorded.
    release_date: date | None = None
    tags: list[TagSummary]
    attributes: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    row_version: int

    @classmethod
    def from_contact(cls, contact: Contact) -> ContactResponse:
        return cls(
            tags=[TagSummary.from_tag(tag) for tag in contact.tags],
            attributes=attributes_map(contact.attribute_values),
            id=contact.public_id,
            wa_id=contact.wa_id,
            phone_e164=contact.phone_e164,
            country_code=contact.country_code,
            full_name=contact.full_name,
            first_name=contact.first_name,
            last_name=contact.last_name,
            email=contact.email,
            locale=contact.locale,
            profile_name=contact.profile_name,
            opt_in_status=contact.opt_in_status,
            opt_in_at=contact.opt_in_at,
            opt_out_at=contact.opt_out_at,
            is_active_on_wa=contact.is_active_on_wa,
            last_inbound_at=contact.last_inbound_at,
            last_outbound_at=contact.last_outbound_at,
            last_contacted_at=contact.last_contacted_at,
            source=contact.source,
            sale_status=contact.sale_status,
            release_date=contact.release_date,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
            row_version=contact.row_version,
        )


class ContactsPage(BaseModel):
    data: list[ContactResponse]
    page: Page


ContactViewVisibility = Literal["private", "shared"]
ContactViewAttributeKey = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=60,
        pattern=r"^[A-Za-z][A-Za-z0-9_]*$",
    ),
]
ContactViewAttributeValue = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=160),
]


class ContactViewFilters(BaseModel):
    """Portable Contacts filters; cursor position is intentionally never persisted."""

    q: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
        | None
    ) = None
    tag_id: uuidlib.UUID | None = None
    attributes: dict[ContactViewAttributeKey, ContactViewAttributeValue] = Field(
        default_factory=dict,
        max_length=25,
    )


class ContactViewCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    visibility: ContactViewVisibility = "private"
    display: Literal["list"] = "list"
    filters: ContactViewFilters


class ContactViewResponse(BaseModel):
    id: uuidlib.UUID
    name: str
    visibility: ContactViewVisibility
    display: Literal["list"]
    filters: ContactViewFilters
    is_owner: bool
    can_delete: bool
    created_at: datetime

    @classmethod
    def from_view(
        cls,
        row: WorkspaceView,
        *,
        actor_user_id: int,
        can_manage_shared: bool,
    ) -> ContactViewResponse:
        is_owner = row.created_by_user_id == actor_user_id
        return cls(
            id=uuidlib.UUID(row.public_id),
            name=row.name,
            visibility=row.visibility,
            display="list",
            filters=ContactViewFilters.model_validate(row.filters_json),
            is_owner=is_owner,
            can_delete=is_owner if row.visibility == "private" else can_manage_shared,
            created_at=row.created_at,
        )


class ContactViewsResponse(BaseModel):
    data: list[ContactViewResponse]


class ContactCreateRequest(BaseModel):
    phone_e164: str
    full_name: str | None = Field(default=None, max_length=160)
    first_name: str | None = Field(default=None, max_length=80)
    last_name: str | None = Field(default=None, max_length=80)
    email: EmailStr | None = None
    locale: str | None = Field(default=None, max_length=10)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    opt_in_status: str = "unknown"
    source: str = Field(default="manual", max_length=40)

    @field_validator("phone_e164")
    @classmethod
    def _phone(cls, value: str) -> str:
        return validate_e164(value)

    @field_validator("opt_in_status")
    @classmethod
    def _opt_in(cls, value: str) -> str:
        return _validate_opt_in(value)


class ContactUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=160)
    first_name: str | None = Field(default=None, max_length=80)
    last_name: str | None = Field(default=None, max_length=80)
    email: EmailStr | None = None
    locale: str | None = Field(default=None, max_length=10)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    opt_in_status: str | None = None
    source: str | None = Field(default=None, max_length=40)
    row_version: int | None = None

    @field_validator("opt_in_status")
    @classmethod
    def _opt_in(cls, value: str | None) -> str | None:
        return _validate_opt_in(value) if value is not None else None
