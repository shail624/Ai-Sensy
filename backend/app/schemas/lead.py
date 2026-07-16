"""Lead pipeline & stage schemas (Doc 07 §19, §23.2)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.lead import LeadPipeline, LeadStage


class LeadStageResponse(BaseModel):
    id: str
    type: str = "lead_stage"
    name: str
    position: int
    is_terminal: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_stage(cls, stage: LeadStage) -> LeadStageResponse:
        return cls(
            id=stage.public_id,
            name=stage.name,
            position=stage.position,
            is_terminal=stage.is_terminal,
            created_at=stage.created_at,
            updated_at=stage.updated_at,
        )


class LeadPipelineResponse(BaseModel):
    id: str
    type: str = "lead_pipeline"
    name: str
    is_default: bool
    stages: list[LeadStageResponse]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_pipeline(cls, pipeline: LeadPipeline) -> LeadPipelineResponse:
        return cls(
            id=pipeline.public_id,
            name=pipeline.name,
            is_default=pipeline.is_default,
            stages=[LeadStageResponse.from_stage(s) for s in pipeline.stages],
            created_at=pipeline.created_at,
            updated_at=pipeline.updated_at,
        )


class LeadPipelineCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    is_default: bool = False


class LeadPipelineUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    is_default: bool | None = None


class LeadStageCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    is_terminal: bool = False
    position: int | None = Field(default=None, ge=0)


class LeadStageUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    position: int | None = Field(default=None, ge=0)
    is_terminal: bool | None = None
