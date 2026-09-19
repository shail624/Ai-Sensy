"""API tests for the audit-log read endpoint (Doc 04 §22)."""

from __future__ import annotations

PASSWORD = "Sup3r-Secret-Pass1"


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_audit_log_captures_actions_and_lists(client, make_user) -> None:
    owner = await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    # Generate an auditable action.
    await client.post("/api/v1/roles", headers=headers, json={"name": "reviewer"})

    resp = await client.get("/api/v1/audit-logs", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"]["total"] >= 1
    actions = {e["action"] for e in body["data"]}
    assert "role.created" in actions
    # login also audited, with the actor resolved to the owner's UUID.
    login_entry = next((e for e in body["data"] if e["action"] == "user.login"), None)
    assert login_entry is not None
    assert login_entry["actor"] == owner.user.public_id


async def test_audit_filters_by_action_and_entity(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    await client.post("/api/v1/roles", headers=headers, json={"name": "r1"})

    by_action = await client.get(
        "/api/v1/audit-logs?filter[action][eq]=role.created", headers=headers
    )
    assert all(e["action"] == "role.created" for e in by_action.json()["data"])

    by_entity = await client.get(
        "/api/v1/audit-logs?filter[entity][eq]=role", headers=headers
    )
    assert all(e["entity_type"] == "role" for e in by_entity.json()["data"])


async def test_audit_filter_by_actor_and_pagination(client, make_user) -> None:
    owner = await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    for i in range(3):
        await client.post("/api/v1/roles", headers=headers, json={"name": f"role{i}"})

    page1 = await client.get(
        f"/api/v1/audit-logs?filter[actor][eq]={owner.user.public_id}&limit=2", headers=headers
    )
    body1 = page1.json()
    assert len(body1["data"]) == 2 and body1["page"]["has_more"] is True

    page2 = await client.get(
        f"/api/v1/audit-logs?cursor={body1['page']['next_cursor']}&limit=2", headers=headers
    )
    assert page2.status_code == 200
    # Distinct entries across pages (keyset).
    ids1 = {e["id"] for e in body1["data"]}
    ids2 = {e["id"] for e in page2.json()["data"]}
    assert ids1.isdisjoint(ids2)


async def test_audit_unknown_actor_returns_empty(client, make_user) -> None:
    import uuid

    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    resp = await client.get(
        f"/api/v1/audit-logs?filter[actor][eq]={uuid.uuid4()}", headers=headers
    )
    assert resp.status_code == 200 and resp.json()["data"] == []


async def test_audit_permission_enforcement(client, make_user) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    headers = await _headers(client, "agent@vi.co")
    assert (await client.get("/api/v1/audit-logs", headers=headers)).status_code == 403
    assert (await client.get("/api/v1/audit-logs")).status_code == 401


async def test_pagination_is_declared_and_bounded(client, make_user) -> None:
    """`limit` and `cursor` are contract parameters, not raw-request reads.

    Doc 04 section 6 fixes them for every collection and section 1 requires the API to be fully
    OpenAPI-describable; undeclared, they cannot be reached from the generated client at all. The
    bounds now come from the declaration, so an out-of-range page size is refused rather than
    silently clamped — a client asking for 9999 rows has a bug, and quietly handing back 200 hides
    it.
    """
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")

    schema = (await client.get("/api/v1/openapi.json")).json()
    declared = {q["name"] for q in schema["paths"]["/api/v1/audit-logs"]["get"]["parameters"]}
    assert {"limit", "cursor"} <= declared

    assert (await client.get("/api/v1/audit-logs?limit=1", headers=headers)).status_code == 200
    assert (await client.get("/api/v1/audit-logs?limit=9999", headers=headers)).status_code == 422
    assert (await client.get("/api/v1/audit-logs?limit=0", headers=headers)).status_code == 422


async def test_the_filter_grammar_stays_on_the_raw_request(client, make_user) -> None:
    """`filter[field][op]` spans any field crossed with eleven operators, so there is no finite
    parameter set to declare. It must keep working, and must stay out of the generated query."""
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    await client.post("/api/v1/roles", headers=headers, json={"name": "auditable"})

    filtered = await client.get("/api/v1/audit-logs?filter[action][eq]=role.created", headers=headers)

    assert filtered.status_code == 200
    assert [entry["action"] for entry in filtered.json()["data"]] == ["role.created"]
    schema = (await client.get("/api/v1/openapi.json")).json()
    declared = {q["name"] for q in schema["paths"]["/api/v1/audit-logs"]["get"]["parameters"]}
    assert not any(name.startswith("filter[") for name in declared)


# --- AUDIT-01: where an action came from, not only who did it -------------------------------------
async def test_every_audited_action_records_its_origin_not_only_sign_in(
    client, make_user
) -> None:
    """`ip_address` has been on the table since the schema was written and only sign-in filled it.

    So the trail answered *who* and *what* for everything and *where* for one action — a gap that
    does not show in the column list and is discovered by whoever has to investigate. The origin
    now fills itself from the request context, so an action audited five layers down carries it
    without every service signature growing two parameters it cannot fill.
    """
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co") | {"User-Agent": "ViDesk/2.1 (Windows)"}

    created = await client.post("/api/v1/roles", headers=headers, json={"name": "reviewer"})
    assert created.status_code == 201, created.text

    body = (await client.get("/api/v1/audit-logs", headers=headers)).json()
    entry = next(e for e in body["data"] if e["action"] == "role.created")

    assert entry["user_agent"] == "ViDesk/2.1 (Windows)"
    assert entry["ip_address"] is not None


async def test_a_long_user_agent_does_not_break_the_write(client, make_user) -> None:
    """A header is attacker-controlled and unbounded.

    An audit write must never fail because somebody sent a long one, and a truncated device string
    is still a useful one — losing the record entirely would be the worse outcome by far.
    """
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co") | {"User-Agent": "A" * 3000}

    created = await client.post("/api/v1/roles", headers=headers, json={"name": "reviewer"})
    assert created.status_code == 201, created.text

    body = (await client.get("/api/v1/audit-logs", headers=headers)).json()
    entry = next(e for e in body["data"] if e["action"] == "role.created")
    assert len(entry["user_agent"]) == 400


async def test_the_hash_chain_still_verifies_across_the_new_column(
    client, make_user, session_factory
) -> None:
    """The origin is deliberately outside `_row_hash`, as `ip_address` already was.

    Widening the canonical form would invalidate every existing row's hash, and a tamper-evidence
    scheme that cannot verify yesterday is worth less than one covering slightly fewer fields.

    The rows are read back through the suite's own session factory rather than the application's:
    `get_sessionmaker()` would open a connection to the configured database, which in a test is a
    *different* in-memory SQLite than the one the request just wrote to.
    """
    from sqlalchemy import select

    from app.models.audit import AuditLog
    from app.services.audit_service import AuditService

    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co") | {"User-Agent": "ViDesk/2.1"}
    await client.post("/api/v1/roles", headers=headers, json={"name": "reviewer"})

    async with session_factory() as session:
        rows = list((await session.scalars(select(AuditLog))).all())

    assert rows, "the action must have been audited"
    assert any(row.user_agent == "ViDesk/2.1" for row in rows), "the origin must have been stored"
    for row in rows:
        # Recomputing from the canonical content reproduces the stored hash, device or no device.
        assert row.row_hash == AuditService._row_hash(row)


async def test_a_row_recomputes_from_what_was_actually_stored(client, make_user, session_factory):
    """`created_at` was left to the column default, which SQLAlchemy applies at flush.

    The digest was taken before that, so every row ever written stored a real timestamp under a
    hash computed over `null`: no row could be recomputed from its own persisted content, and the
    field a tamperer would move was the one field the digest did not cover. Stamping the time at
    construction is what makes the column mean anything.
    """
    from sqlalchemy import select

    from app.models.audit import AuditLog
    from app.services.audit_service import VERIFIED, AuditService

    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    await client.post("/api/v1/roles", headers=headers, json={"name": "reviewer"})

    async with session_factory() as session:
        rows = list((await session.scalars(select(AuditLog))).all())

    assert rows
    for row in rows:
        assert row.created_at is not None
        assert AuditService.verify(row) == VERIFIED


async def test_a_row_written_before_the_fix_is_reported_apart_not_as_tampered(db_session):
    """Calling the existing history tampered would be a false alarm on every row of it.

    Calling it fully verified would overstate what its digest covers. It is reported as its own
    verdict so neither claim is made.
    """
    from app.models.audit import AuditLog
    from app.services.audit_service import VERIFIED_LEGACY, AuditService

    entry = AuditLog(action="role.created", entity_type="role", entity_id=1, created_at=None)
    entry.row_hash = AuditService._row_hash(entry)  # the pre-fix digest: created_at hashed as null
    entry.created_at = __import__("app.db.mixins", fromlist=["utcnow"]).utcnow()

    assert AuditService.verify(entry) == VERIFIED_LEGACY


async def test_an_edited_row_is_reported_as_a_mismatch(db_session):
    """The point of storing a digest is that changing the row afterwards shows."""
    from app.db.mixins import utcnow
    from app.models.audit import AuditLog
    from app.services.audit_service import MISMATCH, UNHASHED, AuditService

    entry = AuditLog(action="role.created", entity_type="role", entity_id=1, created_at=utcnow())
    entry.row_hash = AuditService._row_hash(entry)
    entry.action = "role.deleted"  # somebody rewrote the record after it was written

    assert AuditService.verify(entry) == MISMATCH
    entry.row_hash = None
    assert AuditService.verify(entry) == UNHASHED


async def test_the_reader_of_the_trail_can_see_whether_it_still_vouches_for_itself(
    client, make_user
) -> None:
    """A digest nothing recomputes protects nothing — which is how it went unnoticed this long."""
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    await client.post("/api/v1/roles", headers=headers, json={"name": "reviewer"})

    body = (await client.get("/api/v1/audit-logs", headers=headers)).json()

    assert body["data"]
    assert {entry["integrity"] for entry in body["data"]} == {"verified"}
