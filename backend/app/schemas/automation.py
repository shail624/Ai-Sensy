"""Typed API contract for versioned automation definitions (Design Book 22)."""

from __future__ import annotations

import uuid as uuidlib
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.automation_service import AutomationFlowView, AutomationVersionView, GraphIssue

NodeId = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TriggerConfig(StrictModel):
    event: Literal["message.received", "contact.created", "lead.stage_changed", "schedule"]
    schedule_cron: str | None = Field(default=None, min_length=5, max_length=120)

    @model_validator(mode="after")
    def schedule_shape(self) -> TriggerConfig:
        if self.event == "schedule" and self.schedule_cron is None:
            raise ValueError("schedule_cron is required for a schedule trigger")
        if self.event != "schedule" and self.schedule_cron is not None:
            raise ValueError("schedule_cron is only valid for a schedule trigger")
        return self


class ConditionConfig(StrictModel):
    field: str = Field(min_length=1, max_length=100)
    operator: Literal["eq", "ne", "contains", "exists", "gt", "gte", "lt", "lte"]
    value: str | int | float | bool | list[str] | None = None


class ActionConfig(StrictModel):
    action: Literal["create_task"]
    title: str = Field(min_length=1, max_length=160)


class DelayConfig(StrictModel):
    seconds: int = Field(ge=60, le=2_592_000)


class TagConfig(StrictModel):
    tag_id: uuidlib.UUID


class AssignmentConfig(StrictModel):
    mode: Literal["round_robin", "user"]
    user_id: uuidlib.UUID | None = None

    @model_validator(mode="after")
    def assignment_shape(self) -> AssignmentConfig:
        if self.mode == "user" and self.user_id is None:
            raise ValueError("user_id is required for user assignment")
        if self.mode == "round_robin" and self.user_id is not None:
            raise ValueError("user_id is only valid for user assignment")
        return self


class WaitConfig(StrictModel):
    event: Literal["message.received", "lead.stage_changed", "task.completed"]
    timeout_seconds: int | None = Field(default=None, ge=60, le=2_592_000)


class WebhookConfig(StrictModel):
    webhook_id: uuidlib.UUID


class CampaignConfig(StrictModel):
    campaign_id: uuidlib.UUID


class NotificationConfig(StrictModel):
    message: str = Field(min_length=1, max_length=500)


class ApprovalConfig(StrictModel):
    permission: Literal["messages:send", "campaigns:send"]


class AutomationNodeBase(StrictModel):
    id: NodeId
    label: str | None = Field(default=None, min_length=1, max_length=120)


class TriggerNode(AutomationNodeBase):
    kind: Literal["trigger"]
    config: TriggerConfig


class ConditionNode(AutomationNodeBase):
    kind: Literal["condition"]
    config: ConditionConfig


class ActionNode(AutomationNodeBase):
    kind: Literal["action"]
    config: ActionConfig


class DelayNode(AutomationNodeBase):
    kind: Literal["delay"]
    config: DelayConfig


class TagNode(AutomationNodeBase):
    kind: Literal["tag"]
    config: TagConfig


class AssignmentNode(AutomationNodeBase):
    kind: Literal["assignment"]
    config: AssignmentConfig


class WaitNode(AutomationNodeBase):
    kind: Literal["wait"]
    config: WaitConfig


class WebhookNode(AutomationNodeBase):
    kind: Literal["webhook"]
    config: WebhookConfig


class CampaignNode(AutomationNodeBase):
    kind: Literal["campaign"]
    config: CampaignConfig


class NotificationNode(AutomationNodeBase):
    kind: Literal["notification"]
    config: NotificationConfig


class ApprovalNode(AutomationNodeBase):
    kind: Literal["approval"]
    config: ApprovalConfig


AutomationNode = Annotated[
    TriggerNode
    | ConditionNode
    | ActionNode
    | DelayNode
    | TagNode
    | AssignmentNode
    | WaitNode
    | WebhookNode
    | CampaignNode
    | NotificationNode
    | ApprovalNode,
    Field(discriminator="kind"),
]


class AutomationEdge(StrictModel):
    id: NodeId
    source: NodeId
    target: NodeId
    label: str | None = Field(default=None, min_length=1, max_length=80)


class AutomationGraph(StrictModel):
    nodes: list[AutomationNode] = Field(default_factory=list, max_length=100)
    edges: list[AutomationEdge] = Field(default_factory=list, max_length=200)


class AutomationCreateRequest(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    graph: AutomationGraph = Field(default_factory=AutomationGraph)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name cannot be blank")
        return value


class AutomationUpdateRequest(StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    graph: AutomationGraph | None = None
    expected_row_version: int | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("name cannot be blank")
        return value


class AutomationVersionGuardRequest(StrictModel):
    expected_row_version: int | None = Field(default=None, ge=0)


class AutomationValidationIssueResponse(BaseModel):
    code: str
    message: str
    node_id: str | None

    @classmethod
    def of(cls, issue: GraphIssue) -> AutomationValidationIssueResponse:
        return cls(code=issue.code, message=issue.message, node_id=issue.node_id)


class AutomationValidationResponse(BaseModel):
    valid: bool
    issues: list[AutomationValidationIssueResponse]

    @classmethod
    def of(cls, issues: list[GraphIssue]) -> AutomationValidationResponse:
        return cls(
            valid=not issues,
            issues=[AutomationValidationIssueResponse.of(issue) for issue in issues],
        )


class AutomationFlowResponse(BaseModel):
    id: str
    name: str
    description: str | None
    status: Literal["draft", "published", "disabled"]
    graph: AutomationGraph
    active_version_no: int | None
    has_unpublished_changes: bool
    row_version: int
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    updated_by: str | None

    @classmethod
    def of(cls, view: AutomationFlowView) -> AutomationFlowResponse:
        return cls(
            id=view.id,
            name=view.name,
            description=view.description,
            status=view.status,
            graph=AutomationGraph.model_validate(view.graph),
            active_version_no=view.active_version_no,
            has_unpublished_changes=view.has_unpublished_changes,
            row_version=view.row_version,
            created_at=view.created_at,
            updated_at=view.updated_at,
            created_by=view.created_by,
            updated_by=view.updated_by,
        )


class AutomationListResponse(BaseModel):
    data: list[AutomationFlowResponse]
    total: int


class AutomationVersionResponse(BaseModel):
    id: str
    version_no: int
    name: str
    description: str | None
    graph: AutomationGraph
    content_hash: str
    published_by: str | None
    published_at: datetime

    @classmethod
    def of(cls, view: AutomationVersionView) -> AutomationVersionResponse:
        return cls(
            id=view.id,
            version_no=view.version_no,
            name=view.name,
            description=view.description,
            graph=AutomationGraph.model_validate(view.graph),
            content_hash=view.content_hash,
            published_by=view.published_by,
            published_at=view.published_at,
        )


class AutomationVersionsResponse(BaseModel):
    data: list[AutomationVersionResponse]
