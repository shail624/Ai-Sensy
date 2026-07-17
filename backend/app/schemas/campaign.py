"""Campaign schemas (Doc 04 §17)."""

from __future__ import annotations

import uuid as uuidlib
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.campaign import Campaign, CampaignRecipient, CampaignSchedule
from app.models.contact import Contact
from app.services.cost_estimation_service import UNRESOLVED_COUNTRY, Estimate

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


class CampaignDispatchResponse(BaseModel):
    """The ``202`` a dispatch answers with (FR-CAM-05)."""

    id: str
    status: str
    total_recipients: int
    #: Where to watch it from here.
    progress_url: str


class CampaignProgressResponse(BaseModel):
    """Live campaign state (FR-CAM-10).

    Derived from the roster, which is the authority; the campaign's counters mirror it.
    """

    status: str
    total: int
    pending: int
    queued: int
    sent: int
    delivered: int
    read: int
    failed: int
    batches_total: int
    batches_done: int


class CampaignStateResponse(BaseModel):
    """The campaign after a lifecycle transition (Doc 04 §17)."""

    id: str
    status: str
    total_recipients: int
    sent_count: int
    failed_count: int

    @classmethod
    def from_campaign(cls, campaign: Campaign) -> CampaignStateResponse:
        return cls(
            id=campaign.public_id,
            status=campaign.status,
            total_recipients=campaign.total_recipients,
            sent_count=campaign.sent_count,
            failed_count=campaign.failed_count,
        )


class CampaignRetryResponse(BaseModel):
    """What a manual retry re-queued (FR-CAM-08)."""

    id: str
    status: str
    #: Failed recipients reset to pending and handed back to the send fabric.
    retried: int


class EstimateBreakdownEntry(BaseModel):
    """One priced ``(country, category)`` group (Doc 04 §17).

    ``unit`` and ``subtotal`` are decimals serialized as fixed-scale strings — a JSON number cannot
    carry scale and lands in a binary float, which is what money must never touch.
    """

    country: str
    category: str
    count: int
    unit: Decimal
    subtotal: Decimal


class EstimateUnresolved(BaseModel):
    """Recipients that could not be priced (Doc 03 §8.5.4).

    Reported rather than dropped: excluding them from the total while hiding the count would
    understate the number FR-CAM-11 calls exact.
    """

    count: int
    reason: str = UNRESOLVED_COUNTRY


class CampaignEstimateResponse(BaseModel):
    """Pre-send cost estimate (FR-CAM-11; Doc 04 §17).

    Invariant: ``recipients == sum(b.count for b in breakdown) + unresolved.count``.
    """

    recipients: int
    breakdown: list[EstimateBreakdownEntry]
    unresolved: EstimateUnresolved
    #: Resolved recipients only, rounded once to 4 dp (Doc 03 §8.5.3).
    estimated_total: Decimal
    #: The rate card's single currency — there is no FX (Doc 03 §8.5.3).
    currency: str
    #: Advisory prose. Clients must not parse it; `unresolved` is the machine-readable outcome.
    notes: list[str]

    @classmethod
    def from_estimate(cls, estimate: Estimate) -> CampaignEstimateResponse:
        return cls(
            recipients=estimate.recipients,
            breakdown=[
                EstimateBreakdownEntry(
                    country=row.country,
                    category=row.category,
                    count=row.count,
                    unit=row.unit,
                    subtotal=row.subtotal,
                )
                for row in estimate.breakdown
            ],
            unresolved=EstimateUnresolved(count=estimate.unresolved_count),
            estimated_total=estimate.estimated_total,
            currency=estimate.currency,
            notes=estimate.notes,
        )


#: What a caller may ask for. ``drip`` is an API shape, not a stored type: it expands into a series
#: of one-time schedules (Doc 06 §10.3), which is why it has no counterpart in Doc 03 §8.2's
#: ``ck_csched_type``.
ScheduleTypeName = Literal["one_time", "recurring", "drip"]


class CampaignScheduleRequest(BaseModel):
    """When a campaign should fire (Doc 04 §17; FR-CAM-03/04).

    One model over three shapes, because they are one decision — "when" — and the fields that do
    not apply are simply absent. The service rejects a shape missing what it needs (422).
    """

    schedule_type: ScheduleTypeName
    #: IANA zone the schedule is read in; the cron's meaning depends on it (Doc 06 §10.4).
    timezone: str = Field(default="UTC", max_length=64)

    #: one_time — the single fire, UTC.
    run_at: datetime | None = None

    #: recurring — five-field cron, plus an optional window.
    cron_expr: str | None = Field(default=None, max_length=120)
    starts_on: date | None = None
    ends_on: date | None = None

    #: drip — the anchor every step is measured from.
    starts_at: datetime | None = None
    #: drip — minute offsets from ``starts_at``; each becomes one one-time schedule.
    steps: list[int] | None = None


class ScheduleEntry(BaseModel):
    """One stored schedule row (Doc 03 §8.2)."""

    id: str
    schedule_type: str
    timezone: str
    run_at: datetime | None
    cron_expr: str | None
    starts_on: date | None
    ends_on: date | None
    next_run_at: datetime | None
    last_run_at: datetime | None
    is_active: bool

    @classmethod
    def from_schedule(cls, schedule: CampaignSchedule) -> ScheduleEntry:
        return cls(
            id=schedule.public_id,
            schedule_type=schedule.schedule_type,
            timezone=schedule.timezone,
            run_at=schedule.run_at,
            cron_expr=schedule.cron_expr,
            starts_on=schedule.starts_on,
            ends_on=schedule.ends_on,
            next_run_at=schedule.next_run_at,
            last_run_at=schedule.last_run_at,
            is_active=schedule.is_active,
        )


class CampaignScheduleResponse(BaseModel):
    """The campaign and the schedule(s) now attached to it (FR-CAM-03/04).

    A list, not a single row: a drip request produces one row per step, and returning all of them
    is what lets the caller see the sequence it actually created.
    """

    id: str
    status: str
    schedules: list[ScheduleEntry]
