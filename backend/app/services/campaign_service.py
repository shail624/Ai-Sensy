"""Campaign registry service (Doc 04 §17; Doc 03 §8.1/§8.3) — FR-CAM-01/02.

A campaign is a **draft** here and nothing more: a number, an approved template, a resolved
audience, and a mapping from the template's variables to each contact's data. Sending is Step 2.

**Everything is checked before the roster exists.** An approved template, a connected number, a
variable map that fills exactly the placeholders the template declares — all of it is validated at
create/update time, because a campaign whose problems surface at send time has already cost the
operator the window they scheduled it for (Doc 04 §17 → 422).

**Materialization is the point.** Resolving the audience produces `campaign_recipients` rows with
each contact's variables already substituted, so what the operator approved in the preview is
literally what will be sent — not a query that may return something else an hour later.
"""

from __future__ import annotations

import uuid as uuidlib
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError, VersionConflictError
from app.core.logging import get_logger
from app.db.mixins import utcnow
from app.models.campaign import (
    AUDIENCE_TYPES,
    CAMPAIGN_DRAFT,
    RECIPIENT_PENDING,
    Campaign,
    CampaignRecipient,
)
from app.models.contact import Contact
from app.models.template import MessageTemplate
from app.models.user import User
from app.repositories.campaign import CampaignRecipientRepository, CampaignRepository
from app.repositories.template import TemplateRepository
from app.repositories.waba import PhoneNumberRepository
from app.services.audience_service import AudienceService
from app.services.audit_service import AuditAction, AuditService
from app.services.phone_number_service import PhoneNumberService
from app.services.template_validation import expected_variables, render

logger = get_logger(__name__)

#: Where a variable's value may come from (FR-CAM-01 "variable mapping").
SOURCE_FIELD = "field"
SOURCE_ATTRIBUTE = "attribute"
SOURCE_LITERAL = "literal"
SOURCES = (SOURCE_FIELD, SOURCE_ATTRIBUTE, SOURCE_LITERAL)

#: Contact columns a variable may be mapped to. Deliberately a whitelist: a campaign must not be
#: able to interpolate `password_hash` into a message to a customer.
MAPPABLE_FIELDS = (
    "full_name",
    "first_name",
    "last_name",
    "phone_e164",
    "wa_id",
    "email",
    "profile_name",
    "locale",
    "country_code",
)

#: What a variable resolves to when a contact has no value for it. Empty would render a hole in the
#: message and Meta rejects empty parameters, so a mapping must say what to fall back to.
DEFAULT_FALLBACK = ""


class CampaignInvalid(ValidationError):
    """The campaign cannot be built as specified (Doc 04 §17 → 422)."""

    code = "campaign_invalid"
    title = "Campaign Invalid"


class TemplateNotEligible(ValidationError):
    """The template is not approved, so a campaign on it could never send (FR-CAM-02)."""

    code = "template_not_eligible"
    title = "Template Not Eligible"


@dataclass(slots=True)
class CampaignPreview:
    """What ``POST /campaigns/{uuid}/preview`` answers (Doc 04 §17)."""

    total: int
    excluded_opted_out: int
    samples: list[dict[str, Any]]


class CampaignService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._campaigns = CampaignRepository(session)
        self._recipients = CampaignRecipientRepository(session)
        self._templates = TemplateRepository(session)
        self._numbers = PhoneNumberService(session)
        self._number_rows = PhoneNumberRepository(session)
        self._audience = AudienceService(session)
        self._audit = AuditService(session)

    # --- Reads ---------------------------------------------------------------
    async def list_campaigns(
        self, organization_id: int, *, status: str | None = None, q: str | None = None
    ) -> list[Campaign]:
        return await self._campaigns.list_for_org(organization_id, status=status, q=q)

    async def get_campaign(self, organization_id: int, public_id: uuidlib.UUID) -> Campaign:
        campaign = await self._campaigns.get_active_by_uuid(organization_id, public_id.bytes)
        if campaign is None:
            raise NotFoundError("Campaign not found.")
        return campaign

    async def refs(self, campaign: Campaign) -> tuple[str, str]:
        """The public ids of the campaign's number and template, for rendering."""
        number = await self._number_rows.get_by_id(campaign.phone_number_id)
        template = await self._templates.get_by_id(campaign.template_id)
        return (
            number.public_id if number else "",
            template.public_id if template else "",
        )

    # --- Writes --------------------------------------------------------------
    async def create(
        self,
        *,
        organization_id: int,
        actor: User,
        name: str,
        number_public_id: uuidlib.UUID,
        template_public_id: uuidlib.UUID,
        audience_type: str,
        audience_ref: dict[str, Any] | None,
        variable_map: dict[str, Any] | None,
    ) -> Campaign:
        """Create a draft and materialize its roster (FR-CAM-01/02)."""
        number = await self._numbers.get_number(organization_id, number_public_id)
        template = await self._template(organization_id, template_public_id)
        self._validate(audience_type=audience_type, template=template, variable_map=variable_map)

        campaign = Campaign(
            organization_id=organization_id,
            name=name,
            phone_number_id=number.id,
            template_id=template.id,
            status=CAMPAIGN_DRAFT,
            audience_type=audience_type,
            audience_ref_json=audience_ref,
            variable_map_json=variable_map,
            created_by=actor.id,
        )
        await self._campaigns.add(campaign)
        await self._materialize(campaign, template)
        await self._audit.record(
            AuditAction.CAMPAIGN_CREATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="campaign",
            entity_id=campaign.id,
            after={
                "name": name,
                "audience_type": audience_type,
                "total_recipients": campaign.total_recipients,
            },
        )
        await self._session.commit()
        return campaign

    async def update(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        fields: dict[str, Any],
        number_public_id: uuidlib.UUID | None,
        template_public_id: uuidlib.UUID | None,
        expected_version: int | None,
    ) -> Campaign:
        """Edit a draft (Doc 04 §17 → 409 once it is no longer one)."""
        campaign = await self.get_campaign(organization_id, public_id)
        if expected_version is not None and expected_version != campaign.row_version:
            raise VersionConflictError("The campaign was modified by someone else; reload.")
        if not campaign.is_editable:
            raise ConflictError(f"A {campaign.status} campaign cannot be edited.")

        if number_public_id is not None:
            campaign.phone_number_id = (
                await self._numbers.get_number(organization_id, number_public_id)
            ).id
        template = (
            await self._template(organization_id, template_public_id)
            if template_public_id is not None
            else await self._templates.get_by_id(campaign.template_id)
        )
        if template is None:
            raise NotFoundError("Template not found.")
        campaign.template_id = template.id
        for key, value in fields.items():
            setattr(campaign, key, value)

        self._validate(
            audience_type=campaign.audience_type,
            template=template,
            variable_map=campaign.variable_map_json,
        )
        campaign.updated_by = actor.id
        campaign.row_version += 1
        await self._campaigns.flush()
        # The audience or the mapping may have changed, so the roster is rebuilt rather than
        # patched: a stale recipient row would send the wrong message to a real person.
        await self._materialize(campaign, template)
        await self._audit.record(
            AuditAction.CAMPAIGN_UPDATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="campaign",
            entity_id=campaign.id,
            after={"fields": sorted(fields), "total_recipients": campaign.total_recipients},
        )
        await self._session.commit()
        return campaign

    async def delete(self, *, organization_id: int, actor: User, public_id: uuidlib.UUID) -> None:
        """Soft-delete a campaign. Refuses one that is in flight (Doc 04 §17 → 409)."""
        campaign = await self.get_campaign(organization_id, public_id)
        if not campaign.is_editable:
            raise ConflictError(
                f"A {campaign.status} campaign cannot be deleted; cancel it first."
            )
        campaign.deleted_at = utcnow()
        campaign.updated_by = actor.id
        campaign.row_version += 1
        await self._campaigns.flush()
        await self._audit.record(
            AuditAction.CAMPAIGN_DELETED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="campaign",
            entity_id=campaign.id,
            before={"name": campaign.name, "total_recipients": campaign.total_recipients},
        )
        await self._session.commit()

    # --- Preview (Doc 04 §17) ------------------------------------------------
    async def preview(
        self, *, organization_id: int, public_id: uuidlib.UUID, samples: int
    ) -> CampaignPreview:
        """Audience size + sample renders, from the stored roster.

        Reads what was materialized rather than re-resolving: the preview must show what will be
        sent, and re-running the audience would answer a subtly different question.
        """
        campaign = await self.get_campaign(organization_id, public_id)
        template = await self._templates.get_by_id(campaign.template_id)
        rows, _ = await self._recipients.paginate(campaign.id, limit=samples, cursor=None)
        contacts = await self._recipients.contacts_for(campaign.id, rows)

        rendered: list[dict[str, Any]] = []
        for row in rows:
            variables = row.variables_json or {}
            contact = contacts.get(row.contact_id)
            rendered.append(
                {
                    "contact_id": contact.public_id if contact else None,
                    "wa_id": contact.wa_id if contact else None,
                    "variables": variables,
                    "rendered": render(
                        (template.components_json or []) if template else [],
                        header=list(variables.get("header") or []),
                        body=list(variables.get("body") or []),
                    ),
                }
            )
        return CampaignPreview(
            total=campaign.total_recipients,
            excluded_opted_out=(campaign.audience_ref_json or {}).get("_excluded_opted_out", 0),
            samples=rendered,
        )

    async def recipients(
        self, campaign: Campaign, *, status: str | None, limit: int, cursor: Any
    ) -> tuple[list[CampaignRecipient], bool, dict[int, Contact]]:
        rows, has_more = await self._recipients.paginate(
            campaign.id, status=status, limit=limit, cursor=cursor
        )
        return rows, has_more, await self._recipients.contacts_for(campaign.id, rows)

    # --- Internals -----------------------------------------------------------
    async def _template(
        self, organization_id: int, public_id: uuidlib.UUID
    ) -> MessageTemplate:
        template = await self._templates.get_active_by_uuid(organization_id, public_id.bytes)
        if template is None:
            raise NotFoundError("Template not found.")
        if not template.is_sendable:
            # FR-CAM-02: a campaign on an unapproved template is a campaign that cannot run.
            raise TemplateNotEligible(
                f"Template {template.name!r} is {template.status} and cannot be broadcast.",
                errors=[
                    {"field": "template_id", "code": template.status, "message": template.status}
                ],
            )
        return template

    def _validate(
        self,
        *,
        audience_type: str,
        template: MessageTemplate,
        variable_map: dict[str, Any] | None,
    ) -> None:
        if audience_type not in AUDIENCE_TYPES:
            raise CampaignInvalid(
                f"Audience type must be one of {', '.join(AUDIENCE_TYPES)}.",
                errors=[{"field": "audience_type", "code": "invalid", "message": audience_type}],
            )
        self._validate_map(template, variable_map or {})

    @staticmethod
    def _validate_map(template: MessageTemplate, variable_map: dict[str, Any]) -> None:
        """The map must fill exactly the placeholders the template declares (FR-CAM-01)."""
        header_vars, body_vars = expected_variables(template.components_json or [])
        for label, expected in (("header", header_vars), ("body", body_vars)):
            mappings = variable_map.get(label) or []
            if len(mappings) != expected:
                raise CampaignInvalid(
                    f"Template {template.name!r} needs {expected} {label} variable mapping(s); "
                    f"{len(mappings)} supplied.",
                    errors=[
                        {
                            "field": f"variable_map.{label}",
                            "code": "count_mismatch",
                            "message": f"expected {expected}, got {len(mappings)}",
                        }
                    ],
                )
            for index, mapping in enumerate(mappings):
                CampaignService._validate_mapping(f"variable_map.{label}.{index}", mapping)

    @staticmethod
    def _validate_mapping(field: str, mapping: Any) -> None:
        if not isinstance(mapping, dict):
            raise CampaignInvalid(
                "Each variable mapping must be an object.",
                errors=[{"field": field, "code": "invalid", "message": "Not an object."}],
            )
        source = mapping.get("source")
        if source not in SOURCES:
            raise CampaignInvalid(
                f"Variable source must be one of {', '.join(SOURCES)}.",
                errors=[{"field": f"{field}.source", "code": "invalid", "message": str(source)}],
            )
        if source == SOURCE_FIELD and mapping.get("key") not in MAPPABLE_FIELDS:
            raise CampaignInvalid(
                f"Field {mapping.get('key')!r} cannot be used in a message.",
                errors=[
                    {"field": f"{field}.key", "code": "invalid", "message": str(mapping.get("key"))}
                ],
            )
        if source in (SOURCE_ATTRIBUTE, SOURCE_LITERAL) and not mapping.get("key" if source == SOURCE_ATTRIBUTE else "value"):
            raise CampaignInvalid(
                f"A {source} mapping needs a {'key' if source == SOURCE_ATTRIBUTE else 'value'}.",
                errors=[{"field": field, "code": "required", "message": source}],
            )

    async def _materialize(self, campaign: Campaign, template: MessageTemplate) -> None:
        """Resolve the audience into `campaign_recipients` (FR-CAM-01/02/10).

        Rebuilt wholesale on every edit: the roster is derived, and a partial update could leave a
        contact carrying variables from a template the campaign no longer uses.
        """
        await self._recipients.delete_for_campaign(campaign.id)
        audience = await self._audience.resolve(
            organization_id=campaign.organization_id,
            audience_type=campaign.audience_type,
            audience_ref=campaign.audience_ref_json,
        )
        variable_map = campaign.variable_map_json or {}
        rows = [
            CampaignRecipient(
                campaign_id=campaign.id,
                contact_id=contact.id,
                status=RECIPIENT_PENDING,
                variables_json=self._variables_for(contact, variable_map),
            )
            for contact in audience.contacts
        ]
        await self._recipients.add_many(rows)

        campaign.total_recipients = audience.total
        # Kept beside the audience it came from so the preview can report what compliance removed
        # without re-resolving (FR-CAM-02).
        campaign.audience_ref_json = {
            **(campaign.audience_ref_json or {}),
            "_excluded_opted_out": audience.excluded_opted_out,
        }
        await self._campaigns.flush()
        logger.info(
            "campaign_materialized",
            extra={
                "campaign": campaign.id,
                "recipients": audience.total,
                "excluded_opted_out": audience.excluded_opted_out,
            },
        )

    @staticmethod
    def _variables_for(contact: Contact, variable_map: dict[str, Any]) -> dict[str, list[str]]:
        """This contact's values for the template's placeholders, in order."""
        return {
            label: [
                CampaignService._value_of(contact, mapping)
                for mapping in (variable_map.get(label) or [])
            ]
            for label in ("header", "body")
        }

    @staticmethod
    def _value_of(contact: Contact, mapping: dict[str, Any]) -> str:
        source = mapping.get("source")
        fallback = str(mapping.get("fallback") or DEFAULT_FALLBACK)
        if source == SOURCE_LITERAL:
            return str(mapping.get("value") or fallback)
        if source == SOURCE_FIELD:
            value = getattr(contact, str(mapping.get("key")), None)
        else:
            # Attributes are denormalized onto the contact for exactly this kind of read
            # (Doc 03 §6.1 `attributes_cache`).
            value = (contact.attributes_cache or {}).get(str(mapping.get("key")))
        text = "" if value is None else str(value)
        return text.strip() or fallback
