"""Idempotent CRM seeding (Doc 07 §19.2).

"The platform ships a default pipeline" — provisioned per organization at bootstrap. Safe to
re-run: an existing default pipeline is left untouched and missing default stages are added
without disturbing custom ones.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import DEFAULT_PIPELINE_NAME, DEFAULT_STAGES, LeadPipeline, LeadStage


async def sync_default_pipeline(session: AsyncSession, organization_id: int) -> LeadPipeline:
    """Create/complete the organization's default lead pipeline (Doc 07 §19.2)."""
    pipeline = (
        await session.scalars(
            select(LeadPipeline).where(
                LeadPipeline.organization_id == organization_id,
                LeadPipeline.name == DEFAULT_PIPELINE_NAME,
                LeadPipeline.deleted_at.is_(None),
            )
        )
    ).first()
    if pipeline is None:
        pipeline = LeadPipeline(
            organization_id=organization_id, name=DEFAULT_PIPELINE_NAME, is_default=True
        )
        session.add(pipeline)
        await session.flush()

    existing = {
        stage.name
        for stage in (
            await session.scalars(
                select(LeadStage).where(
                    LeadStage.pipeline_id == pipeline.id, LeadStage.deleted_at.is_(None)
                )
            )
        ).all()
    }
    for position, (name, is_terminal) in enumerate(DEFAULT_STAGES):
        if name in existing:
            continue
        session.add(
            LeadStage(
                pipeline_id=pipeline.id, name=name, position=position, is_terminal=is_terminal
            )
        )
    await session.flush()
    # Populate the stage collection in the async context so callers can read it safely.
    await session.refresh(pipeline, ["stages"])
    return pipeline
