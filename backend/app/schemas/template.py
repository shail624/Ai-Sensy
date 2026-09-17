"""Template schemas (Doc 04 §15)."""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.template import MessageTemplate, TemplateVersion
from app.repositories.template_usage import TemplateUsage

CategoryName = Literal["marketing", "utility", "authentication"]


class TemplateCreateRequest(BaseModel):
    """A template definition (Doc 04 §15).

    ``components`` is the platform's own structure — header/body/footer/buttons — validated before
    Meta ever sees it. ``submit`` is what separates "save a draft" from "ask Meta"; the default is
    to submit, because a template nobody submits can never be sent.
    """

    waba_id: uuidlib.UUID
    name: str = Field(min_length=1, max_length=512, examples=["order_update"])
    language: str = Field(min_length=2, max_length=10, examples=["en_US"])
    category: CategoryName
    components: list[dict[str, Any]]
    submit: bool = True


class TemplateUpdateRequest(BaseModel):
    category: CategoryName | None = None
    components: list[dict[str, Any]] | None = None
    submit: bool = False
    row_version: int | None = None


class TemplateResponse(BaseModel):
    id: str
    type: str = "template"
    waba_id: str
    name: str
    language: str
    category: str
    status: str
    quality_score: str | None
    rejection_reason: str | None
    components: list[dict[str, Any]]
    variable_count: int
    has_media_header: bool
    #: Whether a send would be accepted right now — the one question every caller asks.
    is_sendable: bool
    last_synced_at: datetime | None
    row_version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_template(cls, template: MessageTemplate, *, waba_public_id: str) -> TemplateResponse:
        return cls(
            id=template.public_id,
            waba_id=waba_public_id,
            name=template.name,
            language=template.language,
            category=template.category,
            status=template.status,
            quality_score=template.quality_score,
            rejection_reason=template.rejection_reason,
            components=template.components_json or [],
            variable_count=template.variable_count,
            has_media_header=template.has_media_header,
            is_sendable=template.is_sendable,
            last_synced_at=template.last_synced_at,
            row_version=template.row_version,
            created_at=template.created_at,
            updated_at=template.updated_at,
        )


class TemplateListResponse(BaseModel):
    data: list[TemplateResponse]


class TemplatePreviewResponse(BaseModel):
    header: str
    body: str
    footer: str


class TemplateVersionEntry(BaseModel):
    version_no: int
    category: str
    status: str
    components: list[dict[str, Any]]
    created_at: datetime

    @classmethod
    def from_version(cls, version: TemplateVersion) -> TemplateVersionEntry:
        return cls(
            version_no=version.version_no,
            category=version.category,
            status=version.status,
            components=version.components_json or [],
            created_at=version.created_at,
        )


class TemplateVersionsResponse(BaseModel):
    data: list[TemplateVersionEntry]


class TemplateUsageResponse(BaseModel):
    """One template's send history.

    ``delivery_rate`` is ``None`` rather than ``0`` for a template nobody has sent: zero reads as
    "everything failed" when the truth is that nothing was tried, and the two call for opposite
    actions — fix it, or try it.
    """

    template_id: uuidlib.UUID
    name: str
    language: str
    category: str
    status: str
    campaigns: int = Field(
        description="Campaigns that were actually dispatched; a draft using the template is not one."
    )
    recipients: int = Field(
        description=(
            "Recipients a send was attempted for — not the size of the roster. A campaign "
            "materialises its whole roster while it is still a draft, and those rows were never "
            "tried."
        )
    )
    delivered: int
    failed: int
    delivery_rate: float | None = Field(
        description="Delivered as a share of attempted; null when the template has never been sent."
    )
    last_used_at: datetime | None = Field(
        description="When the template was last sent, not when a campaign using it was drafted."
    )

    @classmethod
    def from_usage(cls, usage: TemplateUsage) -> TemplateUsageResponse:
        return cls(
            template_id=uuidlib.UUID(usage.template.public_id),
            name=usage.template.name,
            language=usage.template.language,
            category=usage.template.category,
            status=usage.template.status,
            campaigns=usage.campaigns,
            recipients=usage.recipients,
            delivered=usage.delivered,
            failed=usage.failed,
            delivery_rate=usage.delivery_rate,
            last_used_at=usage.last_used_at,
        )


class TemplateUsageListResponse(BaseModel):
    data: list[TemplateUsageResponse]
