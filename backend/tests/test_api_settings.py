"""API tests for system settings & feature flags (Doc 04 §22)."""

from __future__ import annotations

from app.services.inbox_operations_service import InboxOperationsService

PASSWORD = "Sup3r-Secret-Pass1"


def test_unsafe_timezone_key_fails_closed() -> None:
    assert InboxOperationsService._safe_zone("../UTC") is None


async def _headers(client, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_settings_get_empty_then_update(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")

    assert (await client.get("/api/v1/settings", headers=headers)).json() == []

    updated = await client.put(
        "/api/v1/settings",
        headers=headers,
        json={"values": {"business_hours": {"start": "09:00"}, "auto_reply": True}},
    )
    assert updated.status_code == 200
    by_key = {s["key"]: s for s in updated.json()}
    assert by_key["auto_reply"]["value"] is True
    assert by_key["auto_reply"]["value_type"] == "boolean"
    assert by_key["business_hours"]["value"] == {"start": "09:00"}


async def test_settings_upsert_is_idempotent_per_key(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    await client.put("/api/v1/settings", headers=headers, json={"values": {"k": 1}})
    second = await client.put("/api/v1/settings", headers=headers, json={"values": {"k": 2}})
    values = {s["key"]: s["value"] for s in second.json()}
    assert values == {"k": 2}  # updated in place, not duplicated


async def test_settings_permission_enforcement(client, make_user) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    headers = await _headers(client, "agent@vi.co")
    assert (await client.get("/api/v1/settings", headers=headers)).status_code == 403
    assert (
        await client.put("/api/v1/settings", headers=headers, json={"values": {"k": 1}})
    ).status_code == 403
    assert (await client.get("/api/v1/settings")).status_code == 401


async def test_inbox_operations_defaults_are_available_to_every_authenticated_user(
    client, make_user
) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    headers = await _headers(client, "agent@vi.co")

    response = await client.get("/api/v1/settings/inbox-operations", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "assignment_mode": "manual",
        "auto_mark_read": True,
        "consent": {
            "enabled": False,
            "opt_in_keywords": ["START", "YES"],
            "opt_out_keywords": ["STOP", "UNSUBSCRIBE"],
        },
        "working_hours": {
            "enabled": False,
            "days": [
                {
                    "day": day,
                    "enabled": day not in {"saturday", "sunday"},
                    "start": "09:00",
                    "end": "18:00",
                }
                for day in (
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                )
            ],
        },
        "automatic_replies": {
            "welcome_enabled": False,
            "welcome_body": "",
            "off_hours_enabled": False,
            "off_hours_body": "",
        },
        "auto_resolve": {"enabled": False, "inactive_after_hours": 72},
        "configured": False,
        "updated_at": None,
        "organization_timezone": "UTC",
    }


async def test_inbox_operations_update_is_validated_normalized_and_audited(
    client, make_user, session_factory
) -> None:
    from sqlalchemy import select

    from app.models.audit import AuditLog

    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")
    payload = {
        "assignment_mode": "least_open",
        "auto_mark_read": False,
        "consent": {
            "enabled": True,
            "opt_in_keywords": [" start ", "YES", "yes"],
            "opt_out_keywords": [" stop ", "unsubscribe"],
        },
        "working_hours": {
            "enabled": True,
            "days": [
                {"day": day, "enabled": True, "start": "22:00", "end": "06:00"}
                for day in (
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                )
            ],
        },
        "automatic_replies": {
            "welcome_enabled": True,
            "welcome_body": "  Thanks for contacting us.  ",
            "off_hours_enabled": True,
            "off_hours_body": "  We are currently closed.  ",
        },
        "auto_resolve": {"enabled": True, "inactive_after_hours": 48},
    }

    response = await client.put("/api/v1/settings/inbox-operations", headers=headers, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["configured"] is True
    assert body["assignment_mode"] == "least_open"
    assert body["auto_mark_read"] is False
    assert body["consent"]["opt_in_keywords"] == ["START", "YES"]
    assert body["consent"]["opt_out_keywords"] == ["STOP", "UNSUBSCRIBE"]
    assert body["working_hours"]["days"][0]["end"] == "06:00"
    assert body["automatic_replies"]["welcome_body"] == "Thanks for contacting us."
    assert body["auto_resolve"] == {"enabled": True, "inactive_after_hours": 48}
    assert body["organization_timezone"] == "UTC"
    assert body["updated_at"] is not None
    async with session_factory() as session:
        audit = (
            await session.scalars(select(AuditLog).where(AuditLog.action == "setting.updated"))
        ).one()
    assert audit.after_json["key"] == "inbox.operations.v1"


async def test_inbox_operations_rejects_overlapping_keywords_and_unprivileged_updates(
    client, make_user
) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    headers = await _headers(client, "agent@vi.co")
    payload = {
        "assignment_mode": "manual",
        "auto_mark_read": True,
        "consent": {
            "enabled": True,
            "opt_in_keywords": ["YES"],
            "opt_out_keywords": [" yes "],
        },
    }

    assert (
        await client.put("/api/v1/settings/inbox-operations", headers=headers, json=payload)
    ).status_code == 403

    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    owner_headers = await _headers(client, "owner@vi.co")
    invalid = await client.put(
        "/api/v1/settings/inbox-operations", headers=owner_headers, json=payload
    )
    assert invalid.status_code == 422


async def test_generic_settings_endpoint_cannot_bypass_inbox_policy_validation(
    client, make_user
) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")

    response = await client.put(
        "/api/v1/settings",
        headers=headers,
        json={"values": {"inbox.operations.v1": {"assignment_mode": "anything"}}},
    )

    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "reserved_setting"


async def test_inbox_operations_rejects_unsafe_reply_and_schedule_combinations(
    client, make_user
) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")

    off_hours_without_hours = await client.put(
        "/api/v1/settings/inbox-operations",
        headers=headers,
        json={
            "automatic_replies": {
                "off_hours_enabled": True,
                "off_hours_body": "We are closed.",
            }
        },
    )
    assert off_hours_without_hours.status_code == 422

    duplicate_days = await client.put(
        "/api/v1/settings/inbox-operations",
        headers=headers,
        json={
            "working_hours": {
                "enabled": True,
                "days": [
                    {"day": "monday", "enabled": True, "start": "09:00", "end": "18:00"}
                    for _ in range(7)
                ],
            }
        },
    )
    assert duplicate_days.status_code == 422

    empty_enabled_message = await client.put(
        "/api/v1/settings/inbox-operations",
        headers=headers,
        json={"automatic_replies": {"welcome_enabled": True, "welcome_body": "   "}},
    )
    assert empty_enabled_message.status_code == 422

    for invalid_hours in (0, 721):
        invalid_auto_resolve = await client.put(
            "/api/v1/settings/inbox-operations",
            headers=headers,
            json={"auto_resolve": {"enabled": True, "inactive_after_hours": invalid_hours}},
        )
        assert invalid_auto_resolve.status_code == 422


async def test_feature_flag_lifecycle(client, make_user) -> None:
    await make_user(email="owner@vi.co", password=PASSWORD, is_superuser=True)
    headers = await _headers(client, "owner@vi.co")

    assert (await client.get("/api/v1/feature-flags", headers=headers)).json() == []

    created = await client.patch(
        "/api/v1/feature-flags/new_inbox",
        headers=headers,
        json={"is_enabled": True, "description": "New inbox UI", "rollout": {"percent": 50}},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["key"] == "new_inbox" and body["is_enabled"] is True
    assert body["rollout"] == {"percent": 50}

    listed = await client.get("/api/v1/feature-flags", headers=headers)
    assert [f["key"] for f in listed.json()] == ["new_inbox"]

    toggled = await client.patch(
        "/api/v1/feature-flags/new_inbox", headers=headers, json={"is_enabled": False}
    )
    assert toggled.json()["is_enabled"] is False
    assert toggled.json()["description"] == "New inbox UI"  # preserved


async def test_feature_flag_permission_enforcement(client, make_user) -> None:
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    headers = await _headers(client, "agent@vi.co")
    assert (await client.get("/api/v1/feature-flags", headers=headers)).status_code == 403
    assert (
        await client.patch("/api/v1/feature-flags/x", headers=headers, json={"is_enabled": True})
    ).status_code == 403


async def test_admin_can_manage_settings_and_flags(client, make_user) -> None:
    await make_user(email="admin@vi.co", password=PASSWORD, roles=("admin",))
    headers = await _headers(client, "admin@vi.co")
    assert (
        await client.put("/api/v1/settings", headers=headers, json={"values": {"k": "v"}})
    ).status_code == 200
    assert (
        await client.patch("/api/v1/feature-flags/f", headers=headers, json={"is_enabled": True})
    ).status_code == 200
