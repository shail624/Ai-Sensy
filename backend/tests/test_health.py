"""Foundation tests: liveness/readiness probes and the request-id contract.

Verifies the Step-1 foundation (Doc 04 §22 health/ready, Doc 04 §10 request id,
Doc 04 §5 problem+json). Feature tests are added per module step (Doc 10).
"""

from __future__ import annotations

import app.api.health as health_module
from app.core.middleware import REQUEST_ID_HEADER


async def test_health_returns_ok(client) -> None:
    """GET /health is a cheap liveness probe with no dependency checks."""
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"
    assert "version" in body


async def test_request_id_header_is_returned(client) -> None:
    """Every response carries an X-Request-Id correlation header (Doc 04 §10)."""
    response = await client.get("/health")
    assert response.headers.get(REQUEST_ID_HEADER)


async def test_request_id_is_propagated_when_supplied(client) -> None:
    """A client-supplied request id is echoed back unchanged."""
    supplied = "test-correlation-id-123"
    response = await client.get("/health", headers={REQUEST_ID_HEADER: supplied})
    assert response.headers.get(REQUEST_ID_HEADER) == supplied


async def test_ready_when_all_dependencies_up(client, monkeypatch) -> None:
    """GET /ready returns 200 + 'ready' when the database, Redis and storage are up."""
    monkeypatch.setattr(health_module, "redis_ping", _always(True))
    monkeypatch.setattr(health_module, "_check_storage", _always(True))
    response = await client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    names = {dep["name"]: dep["status"] for dep in body["dependencies"]}
    assert names == {"database": "up", "redis": "up", "storage": "up"}


async def test_ready_degraded_when_storage_down(client, monkeypatch) -> None:
    """Exports and media are written through storage, so a node that cannot reach it is not ready."""
    monkeypatch.setattr(health_module, "redis_ping", _always(True))
    monkeypatch.setattr(health_module, "_check_storage", _always(False))
    response = await client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    names = {dep["name"]: dep["status"] for dep in body["dependencies"]}
    assert names["storage"] == "down"
    assert names["database"] == "up"


async def test_ready_degraded_when_redis_down(client, monkeypatch) -> None:
    """GET /ready returns 503 + 'degraded' when a dependency is down (Doc 01 NFR-DR-08)."""
    monkeypatch.setattr(health_module, "redis_ping", _always(False))
    response = await client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    names = {dep["name"]: dep["status"] for dep in body["dependencies"]}
    assert names["database"] == "up"
    assert names["redis"] == "down"


async def test_unknown_route_returns_problem_json(client) -> None:
    """Errors use RFC 7807 application/problem+json (Doc 04 §5)."""
    response = await client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == 404
    assert body["code"] == "not_found"
    assert body["instance"] == "/api/v1/does-not-exist"


def _always(value: bool):
    async def _fn() -> bool:
        return value

    return _fn
