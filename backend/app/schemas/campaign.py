"""Campaign schemas (Doc 04 §17)."""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.campaign import Campaign, CampaignRecipient
from app.models.contact import Contact

AudienceTypeName = Literal["segment", "tag", "list", "upload"]


class VariableMapping(BaseModel):
    """Where one template variable's value comes from (FR-CAM-01).

    ``fallback`` matters more than it looks: Meta rejects an empty parameter, so a contact missing
    the mapped value would fail the send unless something fills the gap.
    """

    source: Literal["field", "attribute", "literal"]
    #: Contact column (``field``) or custom-attribute key (``attribute``).
    key: str | None = None
    #: The value itself, for ``literal``.
    value: str | None = None
    fallback: str | None = None


class VariableMap(BaseModel):
    """Mappings positioned to the template's ``{{1}}, {{2}} …``, per component."""

    header: list[VariableMapping] = Field(default_factory=list)
    body: list[VariableMapping] = Field(default_factory=list)


class AudienceRef(BaseModel):
    """Which segment/tags/contacts the audience selects (Doc 03 §8.1 ``audience_ref_json``)."""

    segment_id: uuidlib.UUID | None = None
    tag_ids: list[uuidlib.UUID] = Field(default_factory=list)
    contact_ids: list[uuidlib.UUID] = Field(default_factory=list)


class CampaignCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    phone_number_id: uuidlib.UUID
    template_id: uuidlib.UUID
    audience_type: AudienceTypeName
    audience_ref: AudienceRef = Field(default_factory=AudienceRef)
    variable_map: VariableMap = Field(default_factory=VariableMap)


class CampaignUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    phone_number_id: uuidlib.UUID | None = None
    template_id: uuidlib.UUID | None = None
    audience_type: AudienceTypeName | None = None
    audience_ref: AudienceRef | None = None
    variable_map: VariableMap | None = None
    row_version: int | None = None


class CampaignResponse(BaseModel):
    id: str
    type: str = "campaign"
    name: str
    phone_number_id: str
    template_id: str
    status: str
    audience_type: str
    audience_ref: dict[str, Any] | None
    variable_map: dict[str, Any] | None
    total_recipients: int
    queued_count: int
    sent_count: int
    delivered_count: int
    read_count: int
    failed_count: int
    replied_count: int
    row_version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_campaign(
        cls, campaign: Campaign, *, number_public_id: str, template_public_id: str
    ) -> CampaignResponse:
        ref = dict(campaign.audience_ref_json or {})
        # An internal bookkeeping key, not part of the audience the caller specified.
        ref.pop("_excluded_opted_out", None)
        return cls(
            id=campaign.public_id,
            name=campaign.name,
            phone_number_id=number_public_id,
            template_id=template_public_id,
            status=campaign.status,
            audience_type=campaign.audience_type,
            audience_ref=ref,
            variable_map=campaign.variable_map_json,
            total_recipients=campaign.total_recipients,
            queued_count=campaign.queued_count,
            sent_count=campaign.sent_count,
            delivered_count=campaign.delivered_count,
            read_count=campaign.read_count,
            failed_count=campaign.failed_count,
            replied_count=campaign.replied_count,
            row_version=campaign.row_version,
            created_at=campaign.created_at,
            updated_at=campaign.updated_at,
        )


class CampaignListResponse(BaseModel):
    data: list[CampaignResponse]


class CampaignPreviewResponse(BaseModel):
    """Audience size + sample renders (Doc 04 §17)."""

    total: int
    #: How many the audience matched but opt-out removed (FR-CAM-02).
    excluded_opted_out: int
    samples: list[dict[str, Any]]


class RecipientEntry(BaseModel):
    contact_id: str | None
    wa_id: str | None
    status: str
    variables: dict[str, Any] | None
    error_code: str | None
    created_at: datetime

    @classmethod
    def from_recipient(
        cls, recipient: CampaignRecipient, contact: Contact | None
    ) -> RecipientEntry:
        return cls(
            contact_id=contact.public_id if contact else None,
            wa_id=contact.wa_id if contact else None,
            status=recipient.status,
            variables=recipient.variables_json,
            error_code=recipient.error_code,
            created_at=recipient.created_at,
        )


class RecipientsResponse(BaseModel):
    data: list[RecipientEntry]
    has_more: bool
