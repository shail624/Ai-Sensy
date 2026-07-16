"""API tests for lead pipelines & stages (Doc 07 §19, §23.2)."""

from __future__ import annotations

from app.crm.seeding import sync_default_pipeline
from app.models.lead import DEFAULT_STAGES

PASSWORD = "Sup3r-Secret-Pass1"


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_default_pipeline_seeded(session_factory, organization) -> None:
    """The platform ships a default pipeline with the Doc 07 §19.2 stages, idempotently."""
    async with session_factory() as session:
        pipeline = await sync_default_pipeline(session, organization.id)
        await session.commit()
        assert pipeline.is_default is True
        assert [s.name for s in sorted(pipeline.stages, key=lambda x: x.position)] == [
            name for name, _ in DEFAULT_STAGES
        ]
        assert [s.name for s in pipeline.stages if s.is_terminal] != []

    async with session_factory() as session:  # re-run must not duplicate
        again = await sync_default_pipeline(session, organization.id)
        await session.commit()
        assert len(again.stages) == len(DEFAULT_STAGES)


async def test_pipeline_crud(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")

    created = await client.post(
        "/api/v1/lead-pipelines", headers=h, json={"name": "Reactivation", "is_default": True}
    )
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Reactivation" and body["is_default"] is True and body["stages"] == []

    assert (
        await client.post("/api/v1/lead-pipelines", headers=h, json={"name": "Reactivation"})
    ).status_code == 409

    got = await client.get(f"/api/v1/lead-pipelines/{body['id']}", headers=h)
    assert got.status_code == 200

    renamed = await client.patch(
        f"/api/v1/lead-pipelines/{body['id']}", headers=h, json={"name": "Renewals"}
    )
    assert renamed.json()["name"] == "Renewals"

    # The default pipeline cannot be deleted.
    assert (
        await client.delete(f"/api/v1/lead-pipelines/{body['id']}", headers=h)
    ).status_code == 409


async def test_stage_lifecycle_and_ordering(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    pipeline = (
        await client.post("/api/v1/lead-pipelines", headers=h, json={"name": "P1"})
    ).json()

    first = await client.post(
        f"/api/v1/lead-pipelines/{pipeline['id']}/stages", headers=h, json={"name": "New Lead"}
    )
    assert first.status_code == 201 and first.json()["position"] == 0
    second = await client.post(
        f"/api/v1/lead-pipelines/{pipeline['id']}/stages",
        headers=h,
        json={"name": "Won", "is_terminal": True},
    )
    assert second.json()["position"] == 1 and second.json()["is_terminal"] is True

    # Duplicate stage name in the same pipeline is rejected.
    assert (
        await client.post(
            f"/api/v1/lead-pipelines/{pipeline['id']}/stages", headers=h, json={"name": "Won"}
        )
    ).status_code == 409

    # Reorder (drag-and-drop → position).
    moved = await client.patch(
        f"/api/v1/lead-stages/{second.json()['id']}", headers=h, json={"position": 0}
    )
    assert moved.json()["position"] == 0
    stages = (await client.get(f"/api/v1/lead-pipelines/{pipeline['id']}", headers=h)).json()[
        "stages"
    ]
    assert [s["name"] for s in stages] == ["Won", "New Lead"]

    # Archive (soft delete) a stage.
    assert (
        await client.delete(f"/api/v1/lead-stages/{first.json()['id']}", headers=h)
    ).status_code == 204
    stages = (await client.get(f"/api/v1/lead-pipelines/{pipeline['id']}", headers=h)).json()[
        "stages"
    ]
    assert [s["name"] for s in stages] == ["Won"]


async def test_setting_new_default_clears_previous(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    h = await _headers(client, "owner@vi.co")
    a = (
        await client.post("/api/v1/lead-pipelines", headers=h, json={"name": "A", "is_default": True})
    ).json()
    b = (
        await client.post("/api/v1/lead-pipelines", headers=h, json={"name": "B", "is_default": True})
    ).json()
    listing = {p["name"]: p["is_default"] for p in (await client.get("/api/v1/lead-pipelines", headers=h)).json()}
    assert listing == {"A": False, "B": True}
    assert a["id"] != b["id"]


async def test_leads_permission_enforcement(client, make_user) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    await make_user(email="nobody@vi.co", password=PASSWORD)
    agent_h = await _headers(client, "agent@vi.co")
    nobody_h = await _headers(client, "nobody@vi.co")
    assert (await client.get("/api/v1/lead-pipelines", headers=agent_h)).status_code == 200
    assert (
        await client.post("/api/v1/lead-pipelines", headers=agent_h, json={"name": "X"})
    ).status_code == 403
    assert (await client.get("/api/v1/lead-pipelines", headers=nobody_h)).status_code == 403
    assert (await client.get("/api/v1/lead-pipelines")).status_code == 401
