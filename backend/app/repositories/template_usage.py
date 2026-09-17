"""How each template has actually performed (Templates: usage analytics).

Templates are chosen by name today, which means they are chosen by memory. The platform already
knows which ones were sent, to how many people, and how often those messages arrived — the facts
sit in ``campaigns`` and ``campaign_recipients`` and nothing reads them per template.

Counts are aggregated per template rather than per recipient on purpose. "Which template works"
is a template question, and answering it does not require naming a single customer or campaign.

A template nobody has sent is reported with zeros rather than omitted. Its absence from a list is
the thing an operator most needs to see: an unused template is either new or quietly broken, and
dropping it would make the list flatter to read and less useful to act on.

Only campaigns that were actually dispatched count, and only recipients a send was actually
attempted for. A campaign materialises its entire roster at creation, while it is still a draft, so
the ledger carries rows for sends nobody has authorised yet; counting those made a template that
delivers to everyone read as a failure because a colleague was midway through drafting a large
campaign with it. The screen answers "which template works", and the obvious response to a bad
number here is to retire a template.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import (
    RECIPIENT_ATTEMPTED,
    RECIPIENT_FAILED,
    Campaign,
    CampaignRecipient,
)
from app.models.template import MessageTemplate


@dataclass(slots=True)
class TemplateUsage:
    template: MessageTemplate
    #: Campaigns that were actually dispatched, never ones still sitting as drafts.
    campaigns: int
    #: Recipients a send was actually attempted for -- not the size of the roster. A campaign
    #: materialises its whole roster at creation, so an undispatched draft's rows sit in the ledger
    #: having never been tried; see ``RECIPIENT_ATTEMPTED``.
    recipients: int
    delivered: int
    failed: int
    #: When the template was last *sent*, not when somebody last drafted a campaign with it.
    last_used_at: datetime | None

    @property
    def delivery_rate(self) -> float | None:
        """Delivered as a share of attempted, or ``None`` when nothing was attempted.

        Zero would be a lie about an unused template -- it reads as "everything failed" when the
        truth is that nothing was tried. The absent value is the honest one and the UI renders it
        as a dash.
        """
        if self.recipients == 0:
            return None
        return round(self.delivered / self.recipients, 4)


class TemplateUsageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_usage(self, organization_id: int) -> list[TemplateUsage]:
        """Every template with its send history, most recently used first.

        One grouped scan over the recipient ledger rather than a query per template: a busy account
        has hundreds of templates, and the per-template version would be hundreds of round trips to
        render one screen.
        """
        delivered = case(
            (
                CampaignRecipient.delivered_at.is_not(None)
                | CampaignRecipient.read_at.is_not(None),
                1,
            ),
            else_=0,
        )
        failed = case((CampaignRecipient.status == RECIPIENT_FAILED, 1), else_=0)
        attempted = case((CampaignRecipient.status.in_(RECIPIENT_ATTEMPTED), 1), else_=0)
        # A campaign counts once it has been dispatched, never while it is a draft. ``CASE`` rather
        # than a ``WHERE`` so a template whose only campaigns are drafts still appears in the list
        # with zeros, which is the state an operator most needs to see.
        dispatched = case((Campaign.started_at.is_not(None), Campaign.id))
        usage = (
            select(
                Campaign.template_id.label("template_id"),
                func.count(func.distinct(dispatched)).label("campaigns"),
                func.coalesce(func.sum(attempted), 0).label("recipients"),
                func.coalesce(func.sum(delivered), 0).label("delivered"),
                func.coalesce(func.sum(failed), 0).label("failed"),
                # When the template was last *sent*, not when somebody last opened a draft with it.
                func.max(Campaign.started_at).label("last_used_at"),
            )
            .outerjoin(CampaignRecipient, CampaignRecipient.campaign_id == Campaign.id)
            .where(Campaign.organization_id == organization_id)
            .group_by(Campaign.template_id)
            .subquery()
        )

        stmt = (
            select(
                MessageTemplate,
                usage.c.campaigns,
                usage.c.recipients,
                usage.c.delivered,
                usage.c.failed,
                usage.c.last_used_at,
            )
            .outerjoin(usage, usage.c.template_id == MessageTemplate.id)
            .where(
                MessageTemplate.organization_id == organization_id,
                MessageTemplate.deleted_at.is_(None),
            )
            # Nulls last without relying on the dialect's default: an unused template sorts after
            # every used one on both MySQL and SQLite, which otherwise disagree.
            .order_by(
                case((usage.c.last_used_at.is_(None), 1), else_=0),
                usage.c.last_used_at.desc(),
                MessageTemplate.name.asc(),
            )
        )
        return [
            TemplateUsage(
                template=template,
                campaigns=int(campaigns or 0),
                recipients=int(recipients or 0),
                delivered=int(delivered_count or 0),
                failed=int(failed_count or 0),
                last_used_at=last_used_at,
            )
            for template, campaigns, recipients, delivered_count, failed_count, last_used_at in (
                await self.session.execute(stmt)
            ).all()
        ]
