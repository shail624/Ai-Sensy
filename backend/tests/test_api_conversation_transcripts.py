"""Governed Chat History transcript exports and shared artifact delivery."""

from __future__ import annotations

import csv
import io
import uuid as uuidlib
from datetime import timedelta

import pytest
from anyio import Path
from sqlalchemy import select

from app.core.config import settings
from app.db.mixins import utcnow
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.job import JobMetadata
from app.models.job_records import STATUS_READY, ExportJob
from app.models.message import DIRECTION_INBOUND, DIRECTION_OUTBOUND, MSG_SENT, Message
from app.models.waba import PhoneNumber
from app.services.export_service import ExportService
from tests.test_api_webhooks import _seed_number

PASSWORD = "Sup3r-Secret-Pass1"
BASE = "/api/v1/conversation-transcripts/export"


@pytest.fixture(autouse=True)
def _local_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_local_path", str(tmp_path))
    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "storage_public_base_url", "")
    import app.storage.local  # noqa: F401 - registers the provider


async def _headers(client, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _thread(client, make_user, session_factory, monkeypatch) -> tuple[str, list]:
    await _seed_number(client, make_user, session_factory, monkeypatch)
    now = utcnow().replace(microsecond=0)
    async with session_factory() as session:
        number = (await session.scalars(select(PhoneNumber))).one()
        contact = Contact(
            organization_id=number.organization_id,
            wa_id="919990000001",
            phone_e164="+919990000001",
            full_name="Ramesh K.",
            source="manual",
        )
        session.add(contact)
        await session.flush()
        conversation = Conversation(
            organization_id=number.organization_id,
            phone_number_id=number.id,
            contact_id=contact.id,
            last_message_at=now,
        )
        session.add(conversation)
        await session.flush()
        messages = [
            Message(
                organization_id=number.organization_id,
                conversation_id=conversation.id,
                phone_number_id=number.id,
                contact_id=contact.id,
                direction=DIRECTION_INBOUND,
                message_type="text",
                content_json={"body": "First message"},
                status=MSG_SENT,
                created_at=now - timedelta(minutes=3),
            ),
            Message(
                organization_id=number.organization_id,
                conversation_id=conversation.id,
                phone_number_id=number.id,
                contact_id=contact.id,
                direction=DIRECTION_OUTBOUND,
                message_type="text",
                content_json={"text": {"body": "=HYPERLINK(\"bad\")"}},
                status=MSG_SENT,
                created_at=now - timedelta(minutes=2),
            ),
            Message(
                organization_id=number.organization_id,
                conversation_id=conversation.id,
                phone_number_id=number.id,
                contact_id=contact.id,
                direction=DIRECTION_INBOUND,
                message_type="image",
                content_json={
                    "media": {
                        "kind": "image",
                        "filename": "proof.jpg",
                        "caption": "Final proof",
                        "link": "https://private.example/signed-token",
                        "channel_media_id": "provider-secret",
                        "media_asset_id": "internal-secret",
                    }
                },
                status=MSG_SENT,
                created_at=now - timedelta(minutes=1),
            ),
        ]
        session.add_all(messages)
        await session.commit()
        return conversation.public_id, [message.created_at for message in messages]


async def test_transcript_export_requires_entitlement_and_enqueues_personal_job(
    client, make_user, session_factory, organization, monkeypatch
) -> None:
    conversation_id, moments = await _thread(client, make_user, session_factory, monkeypatch)
    manager = await make_user(email="manager@vi.co", password=PASSWORD, roles=("manager",))
    await make_user(email="agent@vi.co", password=PASSWORD, roles=("agent",))
    await make_user(email="other@vi.co", password=PASSWORD, roles=("manager",))

    import app.crm.tasks as tasks

    dispatched: list[tuple[list[str], str | None]] = []
    monkeypatch.setattr(
        tasks.run_conversation_transcript_export,
        "apply_async",
        lambda args, task_id=None: dispatched.append((args, task_id)),
    )
    payload = {
        "conversation_id": conversation_id,
        "format": "csv",
        "from": moments[0].isoformat(),
        "to": (moments[-1] + timedelta(seconds=1)).isoformat(),
    }

    denied = await client.post(
        BASE, headers=await _headers(client, "agent@vi.co"), json=payload
    )
    accepted = await client.post(
        BASE, headers=await _headers(client, "manager@vi.co"), json=payload
    )

    assert denied.status_code == 403
    assert accepted.status_code == 202, accepted.text
    job_id = accepted.json()["job"]["id"]
    assert accepted.json()["job"]["poll_url"] == f"{BASE}/{job_id}"
    assert dispatched and dispatched[0][0] == [job_id]

    async with session_factory() as session:
        job = (await session.scalars(select(ExportJob))).one()
        metadata = (await session.scalars(select(JobMetadata))).one()
        assert job.organization_id == organization.id
        assert job.requested_by == manager.user.id
        assert job.entity == "conversation_transcript"
        assert job.filters_json == {
            "conversation_id": conversation_id,
            "from": moments[0].isoformat(),
            "to": (moments[-1] + timedelta(seconds=1)).isoformat(),
        }
        assert metadata.task_name == "app.crm.tasks.run_conversation_transcript_export"
        assert metadata.queue == "exports"

    own = await client.get(f"{BASE}/{job_id}", headers=await _headers(client, "manager@vi.co"))
    foreign = await client.get(f"{BASE}/{job_id}", headers=await _headers(client, "other@vi.co"))
    assert own.status_code == 200 and own.json()["status"] == "pending"
    assert foreign.status_code == 404


async def test_transcript_export_validates_range_format_and_tenant_scoped_conversation(
    client, make_user, session_factory, organization, monkeypatch
) -> None:
    conversation_id, moments = await _thread(client, make_user, session_factory, monkeypatch)
    await make_user(email="manager@vi.co", password=PASSWORD, roles=("manager",))
    headers = await _headers(client, "manager@vi.co")

    invalid_range = await client.post(
        BASE,
        headers=headers,
        json={
            "conversation_id": conversation_id,
            "format": "pdf",
            "from": moments[-1].isoformat(),
            "to": moments[0].isoformat(),
        },
    )
    invalid_format = await client.post(
        BASE,
        headers=headers,
        json={"conversation_id": conversation_id, "format": "zip"},
    )
    unknown = await client.post(
        BASE,
        headers=headers,
        json={"conversation_id": "11111111-1111-4111-8111-111111111111", "format": "csv"},
    )

    assert invalid_range.status_code == 422
    assert invalid_format.status_code == 422
    assert unknown.status_code == 404


async def test_transcript_worker_streams_oldest_first_and_redacts_provider_references(
    client, make_user, session_factory, organization, monkeypatch
) -> None:
    conversation_id, moments = await _thread(client, make_user, session_factory, monkeypatch)
    manager = await make_user(email="manager@vi.co", password=PASSWORD, roles=("manager",))
    dispatched: list[str] = []

    async with session_factory() as session:
        job = await ExportService(session).start_transcript(
            organization_id=organization.id,
            actor=manager.user,
            conversation_id=uuidlib.UUID(conversation_id),
            file_format="csv",
            start=moments[0],
            end=moments[-1] + timedelta(seconds=1),
            dispatch=lambda export_id, _task_id: dispatched.append(export_id),
        )
        export_id = job.public_id

    async with session_factory() as session:
        ready = await ExportService(session).run(export_id)
        assert ready.status == STATUS_READY
        assert ready.row_count == 3
        assert ready.storage_key is not None
        artifact = await Path(settings.storage_local_path, ready.storage_key).read_bytes()

    rows = list(csv.DictReader(io.StringIO(artifact.decode("utf-8"))))
    assert [row["content"] for row in rows] == [
        "First message",
        "'=HYPERLINK(\"bad\")",
        "[Image] proof.jpg — Final proof",
    ]
    assert [row["direction"] for row in rows] == ["inbound", "outbound", "inbound"]
    assert [row["participant"] for row in rows] == ["Ramesh K.", "Business", "Ramesh K."]
    combined = artifact.decode("utf-8")
    assert "private.example" not in combined
    assert "provider-secret" not in combined
    assert "internal-secret" not in combined
