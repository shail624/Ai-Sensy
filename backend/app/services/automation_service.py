"""Versioned automation authoring service (Design Book 22, MD5 Phase 2A).

This service owns draft lifecycle, semantic graph validation and immutable publication snapshots.
It intentionally imports no queue, scheduler, send, provider or domain-mutation authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
import uuid as uuidlib
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError, VersionConflictError
from app.db.mixins import utcnow
from app.models.automation import (
    AUTOMATION_STATUS_DISABLED,
    AUTOMATION_STATUS_DRAFT,
    AUTOMATION_STATUS_PUBLISHED,
    AutomationFlow,
    AutomationFlowVersion,
)
from app.models.user import User
from app.repositories.automation import AutomationRepository
from app.services.audit_service import AuditAction, AuditService

AUTOMATION_FLOW_LIMIT = 200


class AutomationQuotaExceeded(ConflictError):
    code = "automation_quota_exceeded"
    title = "Automation Quota Exceeded"


class AutomationStateConflict(ConflictError):
    code = "automation_state"
    title = "Automation State Conflict"


class AutomationDefinitionInvalid(ValidationError):
    code = "automation_definition_invalid"
    title = "Automation Definition Invalid"


@dataclass(frozen=True, slots=True)
class GraphIssue:
    code: str
    message: str
    node_id: str | None = None


@dataclass(slots=True)
class AutomationFlowView:
    id: str
    name: str
    description: str | None
    status: str
    graph: dict[str, Any]
    active_version_no: int | None
    has_unpublished_changes: bool
    row_version: int
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    updated_by: str | None


@dataclass(slots=True)
class AutomationVersionView:
    id: str
    version_no: int
    name: str
    description: str | None
    graph: dict[str, Any]
    content_hash: str
    published_by: str | None
    published_at: datetime


class AutomationService:
    """Tenant-scoped authoring and publication lifecycle."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AutomationRepository(session)
        self._audit = AuditService(session)

    async def list_flows(
        self,
        *,
        organization_id: int,
        q: str | None,
        statuses: list[str] | None,
        limit: int,
    ) -> tuple[list[AutomationFlowView], int]:
        rows, total = await self._repo.list_flows(
            organization_id, q=q, statuses=statuses, limit=limit
        )
        return await self._flow_views(rows), total

    async def get(
        self, *, organization_id: int, public_id: uuidlib.UUID
    ) -> AutomationFlowView:
        flow = await self._require_flow(organization_id, public_id)
        return (await self._flow_views([flow]))[0]

    async def create(
        self,
        *,
        organization_id: int,
        actor: User,
        name: str,
        description: str | None,
        graph: dict[str, Any],
    ) -> AutomationFlowView:
        if await self._repo.count_for_org(organization_id) >= AUTOMATION_FLOW_LIMIT:
            raise AutomationQuotaExceeded(
                f"An organization may retain at most {AUTOMATION_FLOW_LIMIT} automations."
            )
        description = self._clean_description(description)
        content_hash = self._content_hash(name, description, graph)
        flow = AutomationFlow(
            organization_id=organization_id,
            name=name,
            description=description,
            status=AUTOMATION_STATUS_DRAFT,
            draft_graph_json=copy.deepcopy(graph),
            draft_content_hash=content_hash,
            created_by=actor.id,
            updated_by=actor.id,
        )
        await self._repo.add(flow)
        await self._audit.record(
            AuditAction.AUTOMATION_CREATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="automation_flow",
            entity_id=flow.id,
            after=self._snapshot(flow),
        )
        await self._session.commit()
        return (await self._flow_views([flow]))[0]

    async def update(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        changes: dict[str, Any],
        expected_row_version: int | None,
    ) -> AutomationFlowView:
        flow = await self._require_flow(organization_id, public_id, for_update=True)
        self._check_version(flow, expected_row_version)
        before = self._snapshot(flow)
        changed = False
        if "name" in changes and changes["name"] != flow.name:
            flow.name = str(changes["name"])
            changed = True
        if "description" in changes:
            description = self._clean_description(changes["description"])
            if description != flow.description:
                flow.description = description
                changed = True
        if "graph" in changes and changes["graph"] != flow.draft_graph_json:
            flow.draft_graph_json = copy.deepcopy(changes["graph"])
            changed = True
        if changed:
            flow.draft_content_hash = self._content_hash(
                flow.name, flow.description, flow.draft_graph_json
            )
            self._bump(flow, actor.id)
            await self._repo.flush()
            await self._audit.record(
                AuditAction.AUTOMATION_UPDATED,
                actor_user_id=actor.id,
                organization_id=organization_id,
                entity_type="automation_flow",
                entity_id=flow.id,
                before=before,
                after=self._snapshot(flow),
            )
            await self._session.commit()
        return (await self._flow_views([flow]))[0]

    async def validate(
        self, *, organization_id: int, public_id: uuidlib.UUID
    ) -> list[GraphIssue]:
        flow = await self._require_flow(organization_id, public_id)
        return self.validate_graph(flow.draft_graph_json)

    async def publish(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int | None,
    ) -> AutomationFlowView:
        flow = await self._require_flow(organization_id, public_id, for_update=True)
        self._check_version(flow, expected_row_version)
        issues = self.validate_graph(flow.draft_graph_json)
        if issues:
            raise AutomationDefinitionInvalid(
                "Resolve every validation issue before publishing.",
                errors=[
                    {
                        "field": f"graph.nodes.{issue.node_id}" if issue.node_id else "graph",
                        "code": issue.code,
                        "message": issue.message,
                    }
                    for issue in issues
                ],
            )
        if flow.active_content_hash == flow.draft_content_hash:
            raise AutomationStateConflict("The active version already contains this draft.")
        before = self._snapshot(flow)
        version_no = await self._repo.next_version_no(flow.id)
        version = AutomationFlowVersion(
            organization_id=organization_id,
            flow_id=flow.id,
            version_no=version_no,
            name=flow.name,
            description=flow.description,
            graph_json=copy.deepcopy(flow.draft_graph_json),
            content_hash=flow.draft_content_hash,
            published_by=actor.id,
        )
        self._session.add(version)
        flow.active_version_no = version_no
        flow.active_content_hash = flow.draft_content_hash
        flow.status = AUTOMATION_STATUS_PUBLISHED
        self._bump(flow, actor.id)
        await self._repo.flush()
        await self._audit.record(
            AuditAction.AUTOMATION_PUBLISHED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="automation_flow",
            entity_id=flow.id,
            before=before,
            after=self._snapshot(flow),
            metadata={"version_no": version_no, "content_hash": version.content_hash},
        )
        await self._session.commit()
        return (await self._flow_views([flow]))[0]

    async def versions(
        self, *, organization_id: int, public_id: uuidlib.UUID
    ) -> list[AutomationVersionView]:
        flow = await self._require_flow(organization_id, public_id)
        rows = await self._repo.list_versions(flow.id)
        user_ids = {row.published_by for row in rows if row.published_by is not None}
        users = await self._repo.users_by_id(user_ids)
        return [
            AutomationVersionView(
                id=row.public_id,
                version_no=row.version_no,
                name=row.name,
                description=row.description,
                graph=copy.deepcopy(row.graph_json),
                content_hash=row.content_hash,
                published_by=users.get(row.published_by) if row.published_by else None,
                published_at=row.published_at,
            )
            for row in rows
        ]

    async def restore(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        version_no: int,
        expected_row_version: int | None,
    ) -> AutomationFlowView:
        flow = await self._require_flow(organization_id, public_id, for_update=True)
        self._check_version(flow, expected_row_version)
        version = await self._repo.get_version(organization_id, flow.id, version_no)
        if version is None:
            raise NotFoundError("Automation version not found.")
        before = self._snapshot(flow)
        flow.name = version.name
        flow.description = version.description
        flow.draft_graph_json = copy.deepcopy(version.graph_json)
        flow.draft_content_hash = version.content_hash
        self._bump(flow, actor.id)
        await self._repo.flush()
        await self._audit.record(
            AuditAction.AUTOMATION_RESTORED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="automation_flow",
            entity_id=flow.id,
            before=before,
            after=self._snapshot(flow),
            metadata={"restored_version_no": version_no},
        )
        await self._session.commit()
        return (await self._flow_views([flow]))[0]

    async def disable(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int | None,
    ) -> AutomationFlowView:
        return await self._set_enabled(
            organization_id=organization_id,
            actor=actor,
            public_id=public_id,
            expected_row_version=expected_row_version,
            enabled=False,
        )

    async def enable(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int | None,
    ) -> AutomationFlowView:
        return await self._set_enabled(
            organization_id=organization_id,
            actor=actor,
            public_id=public_id,
            expected_row_version=expected_row_version,
            enabled=True,
        )

    async def _set_enabled(
        self,
        *,
        organization_id: int,
        actor: User,
        public_id: uuidlib.UUID,
        expected_row_version: int | None,
        enabled: bool,
    ) -> AutomationFlowView:
        flow = await self._require_flow(organization_id, public_id, for_update=True)
        self._check_version(flow, expected_row_version)
        if flow.active_version_no is None:
            raise AutomationStateConflict("Publish a valid version before changing availability.")
        target = AUTOMATION_STATUS_PUBLISHED if enabled else AUTOMATION_STATUS_DISABLED
        if flow.status == target:
            raise AutomationStateConflict(
                f"Automation is already {'enabled' if enabled else 'disabled'}."
            )
        before = self._snapshot(flow)
        flow.status = target
        self._bump(flow, actor.id)
        await self._repo.flush()
        await self._audit.record(
            AuditAction.AUTOMATION_ENABLED if enabled else AuditAction.AUTOMATION_DISABLED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="automation_flow",
            entity_id=flow.id,
            before=before,
            after=self._snapshot(flow),
        )
        await self._session.commit()
        return (await self._flow_views([flow]))[0]

    @staticmethod
    def validate_graph(graph: dict[str, Any]) -> list[GraphIssue]:
        """Return deterministic publication issues for a structurally typed draft."""
        nodes = list(graph.get("nodes", []))
        edges = list(graph.get("edges", []))
        issues: list[GraphIssue] = []
        if not nodes:
            return [GraphIssue("nodes_required", "Add at least one node before publishing.")]

        node_ids = [str(node["id"]) for node in nodes]
        unique_node_ids = set(node_ids)
        if len(node_ids) != len(unique_node_ids):
            issues.append(GraphIssue("duplicate_node_id", "Every node id must be unique."))
        kinds = {str(node["id"]): str(node["kind"]) for node in nodes}
        for node in nodes:
            node_id = str(node["id"])
            kind = str(node["kind"])
            config = node.get("config", {})
            reference_key = {
                "tag": "tag_id",
                "webhook": "webhook_id",
                "campaign": "campaign_id",
            }.get(kind)
            if reference_key and config.get(reference_key) == "00000000-0000-0000-0000-000000000000":
                issues.append(
                    GraphIssue(
                        "reference_required",
                        f"Choose a real {kind} before publishing.",
                        node_id,
                    )
                )
            if (
                kind == "assignment"
                and config.get("mode") == "user"
                and config.get("user_id") == "00000000-0000-0000-0000-000000000000"
            ):
                issues.append(
                    GraphIssue(
                        "reference_required",
                        "Choose a real user before publishing.",
                        node_id,
                    )
                )
        trigger_ids = [node_id for node_id, kind in kinds.items() if kind == "trigger"]
        if len(trigger_ids) != 1:
            issues.append(
                GraphIssue("single_trigger_required", "A published automation needs exactly one trigger.")
            )

        adjacency: dict[str, set[str]] = {node_id: set() for node_id in unique_node_ids}
        indegree: dict[str, int] = dict.fromkeys(unique_node_ids, 0)
        edge_ids: set[str] = set()
        edge_pairs: set[tuple[str, str]] = set()
        for edge in edges:
            edge_id = str(edge["id"])
            source = str(edge["source"])
            target = str(edge["target"])
            if edge_id in edge_ids:
                issues.append(GraphIssue("duplicate_edge_id", "Every edge id must be unique."))
            edge_ids.add(edge_id)
            if source not in unique_node_ids or target not in unique_node_ids:
                issues.append(
                    GraphIssue("unknown_edge_node", "Every edge must reference existing nodes.")
                )
                continue
            if source == target:
                issues.append(GraphIssue("self_edge", "A node cannot connect to itself.", source))
                continue
            pair = (source, target)
            if pair in edge_pairs:
                issues.append(
                    GraphIssue("duplicate_edge", "A connection between these nodes already exists.", source)
                )
                continue
            edge_pairs.add(pair)
            adjacency[source].add(target)
            indegree[target] += 1

        if len(trigger_ids) == 1:
            trigger_id = trigger_ids[0]
            if indegree.get(trigger_id, 0):
                issues.append(
                    GraphIssue("trigger_has_input", "The trigger cannot have an incoming connection.", trigger_id)
                )
            reachable: set[str] = set()
            pending = [trigger_id]
            while pending:
                current = pending.pop()
                if current in reachable:
                    continue
                reachable.add(current)
                pending.extend(adjacency.get(current, ()))
            for node_id in sorted(unique_node_ids - reachable):
                issues.append(
                    GraphIssue("unreachable_node", "Connect this node to the trigger path.", node_id)
                )

        work = deque(node_id for node_id, degree in indegree.items() if degree == 0)
        remaining = dict(indegree)
        visited = 0
        while work:
            current = work.popleft()
            visited += 1
            for target in adjacency.get(current, ()):
                remaining[target] -= 1
                if remaining[target] == 0:
                    work.append(target)
        if visited != len(unique_node_ids):
            issues.append(GraphIssue("cycle_detected", "Automation graphs cannot contain a loop."))

        approval_ids = {node_id for node_id, kind in kinds.items() if kind == "approval"}
        for campaign_id, kind in kinds.items():
            if kind != "campaign":
                continue
            downstream: set[str] = set()
            pending = list(adjacency.get(campaign_id, ()))
            while pending:
                current = pending.pop()
                if current in downstream:
                    continue
                downstream.add(current)
                pending.extend(adjacency.get(current, ()))
            if not downstream.intersection(approval_ids):
                issues.append(
                    GraphIssue(
                        "campaign_approval_required",
                        "Connect every campaign proposal to a downstream human approval.",
                        campaign_id,
                    )
                )
        return issues

    async def _require_flow(
        self, organization_id: int, public_id: uuidlib.UUID, *, for_update: bool = False
    ) -> AutomationFlow:
        getter = self._repo.get_for_update if for_update else self._repo.get_by_public_id
        flow = await getter(organization_id, public_id.bytes)
        if flow is None:
            raise NotFoundError("Automation not found.")
        return flow

    async def _flow_views(self, rows: list[AutomationFlow]) -> list[AutomationFlowView]:
        user_ids = {
            user_id
            for row in rows
            for user_id in (row.created_by, row.updated_by)
            if user_id is not None
        }
        users = await self._repo.users_by_id(user_ids)
        return [
            AutomationFlowView(
                id=row.public_id,
                name=row.name,
                description=row.description,
                status=row.status,
                graph=copy.deepcopy(row.draft_graph_json),
                active_version_no=row.active_version_no,
                has_unpublished_changes=row.active_content_hash != row.draft_content_hash,
                row_version=row.row_version,
                created_at=row.created_at,
                updated_at=row.updated_at,
                created_by=users.get(row.created_by) if row.created_by else None,
                updated_by=users.get(row.updated_by) if row.updated_by else None,
            )
            for row in rows
        ]

    @staticmethod
    def _content_hash(name: str, description: str | None, graph: dict[str, Any]) -> str:
        content = {"name": name, "description": description, "graph": graph}
        encoded = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _clean_description(value: Any) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @staticmethod
    def _snapshot(flow: AutomationFlow) -> dict[str, Any]:
        return {
            "name": flow.name,
            "description": flow.description,
            "status": flow.status,
            "active_version_no": flow.active_version_no,
            "draft_content_hash": flow.draft_content_hash,
            "row_version": flow.row_version,
        }

    @staticmethod
    def _check_version(flow: AutomationFlow, expected: int | None) -> None:
        if expected is not None and expected != flow.row_version:
            raise VersionConflictError("The automation changed since it was loaded.")

    @staticmethod
    def _bump(flow: AutomationFlow, actor_user_id: int) -> None:
        flow.row_version += 1
        flow.updated_by = actor_user_id
        flow.updated_at = utcnow()
