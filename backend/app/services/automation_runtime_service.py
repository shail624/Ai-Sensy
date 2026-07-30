"""Deterministic, side-effect-free automation test runtime (Design Book 23)."""

from __future__ import annotations

import copy
import hashlib
import heapq
import json
import uuid as uuidlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.db.mixins import utcnow, uuid7
from app.models.automation import (
    AUTOMATION_ATTEMPT_FAILED,
    AUTOMATION_ATTEMPT_INTERRUPTED,
    AUTOMATION_ATTEMPT_RUNNING,
    AUTOMATION_ATTEMPT_SUCCEEDED,
    AUTOMATION_RUN_FAILED,
    AUTOMATION_RUN_QUEUED,
    AUTOMATION_RUN_RETRYING,
    AUTOMATION_RUN_RUNNING,
    AUTOMATION_RUN_SUCCEEDED,
    AUTOMATION_RUN_TERMINAL_STATUSES,
    AutomationFlow,
    AutomationFlowVersion,
    AutomationRun,
    AutomationStepAttempt,
)
from app.models.user import User
from app.queue.registry import AUTOMATION_RUN
from app.repositories.automation import AutomationRepository
from app.repositories.automation_runtime import (
    AutomationAttemptRepository,
    AutomationRunRepository,
)
from app.services.audit_service import AuditAction, AuditService
from app.services.automation_service import AutomationService
from app.services.job_service import JobService

AUTOMATION_TEST_TASK = "app.automation.tasks.execute_automation_test_run"
MAX_TEST_INPUT_BYTES = 32_768


class AutomationRunConflict(ConflictError):
    code = "automation_run_conflict"
    title = "Automation run conflict"


class AutomationRunInvalid(ValidationError):
    code = "automation_run_invalid"
    title = "Automation run invalid"


class AutomationRunExecutionError(RuntimeError):
    """A published graph cannot be executed deterministically."""


@dataclass(frozen=True, slots=True)
class AutomationAttemptView:
    id: str
    node_id: str
    node_kind: str
    attempt_no: int
    status: str
    output: dict[str, Any] | None
    error_code: str | None
    error_detail: str | None
    started_at: datetime
    finished_at: datetime | None


@dataclass(frozen=True, slots=True)
class AutomationRunView:
    id: str
    automation_id: str
    version_no: int
    mode: str
    status: str
    correlation_id: str
    total_steps: int
    completed_steps: int
    created_by: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_code: str | None
    error_detail: str | None
    attempts: list[AutomationAttemptView]


class AutomationRuntimeService:
    """Create, read and execute immutable-version test runs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._runs = AutomationRunRepository(session)
        self._attempts = AutomationAttemptRepository(session)
        self._automations = AutomationRepository(session)
        self._audit = AuditService(session)

    async def create_test_run(
        self,
        *,
        organization_id: int,
        actor: User,
        automation_id: uuidlib.UUID,
        idempotency_key: uuidlib.UUID,
        trigger_input: dict[str, Any],
    ) -> tuple[AutomationRunView, bool, int]:
        encoded = json.dumps(
            trigger_input, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        if len(encoded) > MAX_TEST_INPUT_BYTES:
            raise AutomationRunInvalid(
                f"Test input must be no larger than {MAX_TEST_INPUT_BYTES // 1024} KB."
            )

        flow = await self._automations.get_by_public_id(
            organization_id, automation_id.bytes
        )
        if flow is None:
            raise NotFoundError("Automation not found.")
        version = await self._active_version(flow, organization_id)
        if flow.active_content_hash != flow.draft_content_hash:
            raise AutomationRunConflict(
                "Publish or restore the saved draft before testing an immutable version."
            )
        request_hash = self._request_hash(flow, version, trigger_input)
        existing = await self._runs.by_idempotency_key(
            organization_id, idempotency_key.bytes
        )
        if existing is not None:
            self._check_replay(existing, request_hash)
            return await self._view(existing), False, existing.id

        correlation_id = str(uuid7())
        run = AutomationRun(
            organization_id=organization_id,
            flow_id=flow.id,
            version_id=version.id,
            mode="test",
            status=AUTOMATION_RUN_QUEUED,
            idempotency_key=idempotency_key.bytes,
            request_hash=request_hash,
            correlation_id=correlation_id,
            trigger_input_json=copy.deepcopy(trigger_input),
            total_steps=len(version.graph_json.get("nodes", [])),
            created_by=actor.id,
        )
        await self._runs.add(run)
        await self._runs.flush()
        await JobService(self._session).record_queued(
            task_id=correlation_id,
            task_name=AUTOMATION_TEST_TASK,
            queue=AUTOMATION_RUN,
            ref_type="automation_run",
            ref_id=run.id,
        )
        await self._audit.record(
            AuditAction.AUTOMATION_TEST_RUN_CREATED,
            actor_user_id=actor.id,
            organization_id=organization_id,
            entity_type="automation_run",
            entity_id=run.id,
            after={
                "automation_id": flow.public_id,
                "version_no": version.version_no,
                "mode": "test",
                "status": run.status,
                "correlation_id": correlation_id,
            },
        )
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            existing = await self._runs.by_idempotency_key(
                organization_id, idempotency_key.bytes
            )
            if existing is None:
                raise
            self._check_replay(existing, request_hash)
            return await self._view(existing), False, existing.id
        return await self._view(run), True, run.id

    async def list_runs(
        self,
        *,
        organization_id: int,
        automation_id: uuidlib.UUID,
        limit: int,
    ) -> list[AutomationRunView]:
        flow = await self._automations.get_by_public_id(
            organization_id, automation_id.bytes
        )
        if flow is None:
            raise NotFoundError("Automation not found.")
        rows = await self._runs.list_for_flow(organization_id, flow.id, limit=limit)
        return [await self._view(row, include_attempts=False) for row in rows]

    async def get_run(
        self, *, organization_id: int, run_id: uuidlib.UUID
    ) -> AutomationRunView:
        run = await self._runs.by_public_id(organization_id, run_id.bytes)
        if run is None:
            raise NotFoundError("Automation run not found.")
        return await self._view(run)

    async def execute_test_run(self, run_pk: int) -> str:
        run = await self._runs.by_pk(run_pk, for_update=True)
        if run is None:
            raise AutomationRunExecutionError("Automation run no longer exists.")
        if run.status in AUTOMATION_RUN_TERMINAL_STATUSES:
            return run.status
        version = await self._runs.version(run.version_id)
        if version is None:
            raise AutomationRunExecutionError("Pinned automation version no longer exists.")
        issues = AutomationService.validate_graph(version.graph_json)
        if issues:
            raise AutomationRunExecutionError("Pinned automation graph failed validation.")
        order = self._topological_nodes(version.graph_json)

        now = utcnow()
        for attempt in await self._attempts.running(run.id):
            attempt.status = AUTOMATION_ATTEMPT_INTERRUPTED
            attempt.error_code = "worker_interrupted"
            attempt.error_detail = "The prior worker attempt ended before a terminal checkpoint."
            attempt.finished_at = now
        run.status = AUTOMATION_RUN_RUNNING
        run.started_at = run.started_at or now
        run.finished_at = None
        run.error_code = None
        run.error_detail = None
        await self._session.commit()

        successful = await self._attempts.successful_node_ids(run.id)
        for node in order:
            node_id = str(node["id"])
            if node_id in successful:
                continue
            attempt = AutomationStepAttempt(
                organization_id=run.organization_id,
                run_id=run.id,
                node_id=node_id,
                node_kind=str(node["kind"]),
                attempt_no=await self._attempts.next_attempt_no(run.id, node_id),
                status=AUTOMATION_ATTEMPT_RUNNING,
                input_json=self._step_input(node, run.trigger_input_json),
            )
            await self._attempts.add(attempt)
            await self._session.commit()
            try:
                attempt.output_json = self._simulate_node(node, run.trigger_input_json)
                attempt.status = AUTOMATION_ATTEMPT_SUCCEEDED
                attempt.finished_at = utcnow()
                run.completed_steps += 1
                await self._session.commit()
            except Exception as exc:
                attempt.status = AUTOMATION_ATTEMPT_FAILED
                attempt.error_code = "step_test_failed"
                attempt.error_detail = f"{type(exc).__name__}: {exc}"[:1024]
                attempt.finished_at = utcnow()
                await self._session.commit()
                raise

        run.status = AUTOMATION_RUN_SUCCEEDED
        run.completed_steps = run.total_steps
        run.finished_at = utcnow()
        await self._session.commit()
        return run.status

    async def mark_task_failure(
        self, run_pk: int, *, retrying: bool, error: BaseException
    ) -> None:
        run = await self._runs.by_pk(run_pk, for_update=True)
        if run is None or run.status in AUTOMATION_RUN_TERMINAL_STATUSES:
            return
        run.status = AUTOMATION_RUN_RETRYING if retrying else AUTOMATION_RUN_FAILED
        run.error_code = "task_retry" if retrying else "task_failed"
        run.error_detail = f"{type(error).__name__}: {error}"[:1024]
        run.finished_at = None if retrying else utcnow()
        await self._session.commit()

    async def mark_dispatch_failed(self, run_pk: int, error: BaseException) -> None:
        await self.mark_task_failure(run_pk, retrying=False, error=error)

    async def _active_version(
        self, flow: AutomationFlow, organization_id: int
    ) -> AutomationFlowVersion:
        if flow.active_version_no is None:
            raise AutomationRunConflict("Publish a valid version before running a test.")
        version = await self._automations.get_version(
            organization_id, flow.id, flow.active_version_no
        )
        if version is None:
            raise AutomationRunConflict("The active automation version is unavailable.")
        return version

    async def _view(
        self, run: AutomationRun, *, include_attempts: bool = True
    ) -> AutomationRunView:
        flow = await self._session.get(AutomationFlow, run.flow_id)
        version = await self._runs.version(run.version_id)
        if flow is None or version is None:
            raise AutomationRunExecutionError("Automation run lineage is incomplete.")
        users = await self._automations.users_by_id(
            {run.created_by} if run.created_by is not None else set()
        )
        attempts = await self._attempts.for_run(run.id) if include_attempts else []
        return AutomationRunView(
            id=run.public_id,
            automation_id=flow.public_id,
            version_no=version.version_no,
            mode=run.mode,
            status=run.status,
            correlation_id=run.correlation_id,
            total_steps=run.total_steps,
            completed_steps=run.completed_steps,
            created_by=users.get(run.created_by) if run.created_by is not None else None,
            created_at=run.created_at,
            started_at=run.started_at,
            finished_at=run.finished_at,
            error_code=run.error_code,
            error_detail=run.error_detail,
            attempts=[self._attempt_view(attempt) for attempt in attempts],
        )

    @staticmethod
    def _attempt_view(attempt: AutomationStepAttempt) -> AutomationAttemptView:
        return AutomationAttemptView(
            id=attempt.public_id,
            node_id=attempt.node_id,
            node_kind=attempt.node_kind,
            attempt_no=attempt.attempt_no,
            status=attempt.status,
            output=copy.deepcopy(attempt.output_json),
            error_code=attempt.error_code,
            error_detail=attempt.error_detail,
            started_at=attempt.started_at,
            finished_at=attempt.finished_at,
        )

    @staticmethod
    def _request_hash(
        flow: AutomationFlow,
        version: AutomationFlowVersion,
        trigger_input: dict[str, Any],
    ) -> str:
        value = {
            "flow_id": flow.id,
            "version_id": version.id,
            "content_hash": version.content_hash,
            "trigger_input": trigger_input,
        }
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _check_replay(run: AutomationRun, request_hash: str) -> None:
        if run.request_hash != request_hash:
            raise AutomationRunConflict(
                "This Idempotency-Key was already used for different test input."
            )

    @staticmethod
    def _topological_nodes(graph: dict[str, Any]) -> list[dict[str, Any]]:
        nodes = {str(node["id"]): node for node in graph.get("nodes", [])}
        if not nodes or len(nodes) > 100:
            raise AutomationRunExecutionError("Published graph has an invalid node count.")
        adjacency: dict[str, list[str]] = {node_id: [] for node_id in nodes}
        indegree: dict[str, int] = dict.fromkeys(nodes, 0)
        for edge in graph.get("edges", []):
            source, target = str(edge["source"]), str(edge["target"])
            if source not in nodes or target not in nodes:
                raise AutomationRunExecutionError("Published graph contains an unknown edge.")
            adjacency[source].append(target)
            indegree[target] += 1
        ready = [node_id for node_id, degree in indegree.items() if degree == 0]
        heapq.heapify(ready)
        ordered: list[dict[str, Any]] = []
        while ready:
            node_id = heapq.heappop(ready)
            ordered.append(nodes[node_id])
            for target in sorted(adjacency[node_id]):
                indegree[target] -= 1
                if indegree[target] == 0:
                    heapq.heappush(ready, target)
        if len(ordered) != len(nodes):
            raise AutomationRunExecutionError("Published graph contains a cycle.")
        return ordered

    @classmethod
    def _simulate_node(
        cls, node: dict[str, Any], trigger_input: dict[str, Any]
    ) -> dict[str, Any]:
        kind = str(node["kind"])
        config = node.get("config", {})
        if kind == "trigger":
            return {"accepted": True, "event": "manual.test"}
        if kind == "condition":
            actual = cls._lookup(trigger_input, str(config["field"]))
            return {
                "matched": cls._compare(actual, str(config["operator"]), config.get("value")),
                "field": str(config["field"]),
                "operator": str(config["operator"]),
            }
        return {
            "simulated": True,
            "node_kind": kind,
            "reason": "Test mode records the step without applying a business or customer effect.",
        }

    @staticmethod
    def _step_input(node: dict[str, Any], trigger_input: dict[str, Any]) -> dict[str, Any] | None:
        if node["kind"] != "condition":
            return None
        field = str(node.get("config", {}).get("field", ""))
        return {"field": field, "present": AutomationRuntimeService._lookup(trigger_input, field) is not None}

    @staticmethod
    def _lookup(payload: dict[str, Any], dotted: str) -> Any:
        value: Any = payload
        for part in dotted.split("."):
            if not isinstance(value, dict) or part not in value:
                return None
            value = value[part]
        return value

    @staticmethod
    def _compare(actual: Any, operator: str, expected: Any) -> bool:
        if operator == "exists":
            return actual is not None
        if operator == "eq":
            return bool(actual == expected)
        if operator == "ne":
            return bool(actual != expected)
        if operator == "contains":
            try:
                return expected in actual
            except TypeError:
                return False
        try:
            if operator == "gt":
                return bool(actual > expected)
            if operator == "gte":
                return bool(actual >= expected)
            if operator == "lt":
                return bool(actual < expected)
            if operator == "lte":
                return bool(actual <= expected)
        except TypeError:
            return False
        raise AutomationRunExecutionError(f"Unsupported condition operator: {operator}")
