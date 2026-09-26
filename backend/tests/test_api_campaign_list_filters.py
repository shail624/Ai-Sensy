"""MAINT-02: typed list filters retain repository semantics and tenant isolation."""

import re

import pytest
from sqlalchemy import select

from app.main import create_app
from app.models.campaign import CAMPAIGN_STATUSES, Campaign
from app.models.organization import Organization
from tests.test_api_campaigns import CAMPAIGNS_URL, _body, _setup
from tests.test_api_messages import _headers


def test_list_contract_declares_filters_without_pagination():
    operation = create_app().openapi()["paths"][CAMPAIGNS_URL]["get"]
    params = {p["name"]: p for p in operation["parameters"]}
    assert set(params) == {"q", "status"}
    pattern = params["status"]["schema"]["anyOf"][0]["pattern"]
    assert all(re.fullmatch(pattern, value) for value in CAMPAIGN_STATUSES)
    assert not re.fullmatch(pattern, "unknown")


@pytest.mark.parametrize("value", ["unknown", "DRAFT", "", "draft,running"])
async def test_invalid_list_status_is_rejected(client, make_user, value):
    headers = await _headers(client, make_user, is_superuser=True)
    response = await client.get(CAMPAIGNS_URL, params={"status": value}, headers=headers)
    assert response.status_code == 422


@pytest.mark.parametrize("value", CAMPAIGN_STATUSES)
async def test_all_existing_statuses_are_accepted(client, make_user, value):
    headers = await _headers(client, make_user, is_superuser=True)
    response = await client.get(CAMPAIGNS_URL, params={"status": value}, headers=headers)
    assert response.status_code == 200
    assert response.json()["data"] == []


async def test_filters_intersect_and_do_not_cross_tenants(client, make_user, session_factory, monkeypatch):
    headers, number, template, contacts = await _setup(client, make_user, session_factory, monkeypatch)
    ids = {}
    for name in ("Alpha draft", "Alpha running", "Bravo draft", "Alpha other tenant"):
        response = await client.post(CAMPAIGNS_URL, headers=headers, json=_body(number, template, contacts, name=name))
        assert response.status_code == 201
        ids[name] = response.json()["id"]
    async with session_factory() as session:
        other = Organization(name="Other tenant", slug="maint02-other")
        session.add(other)
        await session.flush()
        for campaign in (await session.scalars(select(Campaign))).all():
            if campaign.name == "Alpha running":
                campaign.status = "running"
            if campaign.name == "Alpha other tenant":
                campaign.organization_id = other.id
        await session.commit()
    cases = [
        ({"q": "Alpha"}, {ids["Alpha draft"], ids["Alpha running"]}),
        ({"status": "draft"}, {ids["Alpha draft"], ids["Bravo draft"]}),
        ({"q": "Alpha", "status": "draft"}, {ids["Alpha draft"]}),
        ({"q": "missing", "status": "draft"}, set()),
        ({"q": "Alpha", "filter[status][eq]": "running"}, {ids["Alpha running"]}),
    ]
    for params, expected in cases:
        response = await client.get(CAMPAIGNS_URL, headers=headers, params=params)
        assert response.status_code == 200
        assert {row["id"] for row in response.json()["data"]} == expected
