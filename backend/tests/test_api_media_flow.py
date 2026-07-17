"""Channel media tests (Doc 07 §17; Doc 06 §2.3 ``media``; FR-WA-11) — Module 4 media.

No network: Meta is an ``httpx.MockTransport`` behind the adapter, and storage is the local
provider writing to a tmp path.
"""

from __future__ import annotations

import hashlib
import uuid

import httpx
import pytest

import app.channels.meta  # noqa: F401 - registers the 'meta_cloud' adapter
from app.db.mixins import utcnow
from app.models.media import MediaAsset
from app.models.message import Message
from app.services.media_ingest_service import (
    META_MEDIA_TTL,
    MediaIngestService,
    MediaUnavailable,
    media_reference,
)
from app.services.message_service import MessageService
from app.services.send_service import SendService
from app.services.waba_service import WabaService
from app.services.webhook_service import WebhookService
from tests.test_api_conversations import SENDER, _rows
from tests.test_api_messages import (  # one send shape, defined in one place
    SEND_URL,
    _headers,
    _key,
    _number_id,
    _open_window,
)
from tests.test_api_webhooks import _delivery, _events, _post, _seed_number

IMAGE = b"\xff\xd8\xff\xe0 not really a jpeg but bytes are bytes"
IMAGE_SHA = hashlib.sha256(IMAGE).hexdigest()
MEDIA_ID = "media-inbound-1"
UPLOADED_ID = "media-uploaded-9"


@pytest.fixture(autouse=True)
def storage(tmp_path, monkeypatch):
    """Point the local storage backend at a throwaway directory (Doc 08 §14)."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "storage_local_path", str(tmp_path / "media"))
    monkeypatch.setattr(settings, "storage_backend", "local")


@pytest.fixture
def channel(monkeypatch) -> dict:
    """Bind every adapter to a transport that serves Meta's two-step media download."""
    state: dict = {"requests": [], "bytes": IMAGE, "mime": "image/jpeg"}

    def handler(request: httpx.Request) -> httpx.Response:
        state["requests"].append(request)
        path = request.url.path
        if path.rsplit("/", 1)[-1].startswith("media-"):
            # Step 1: the id resolves to a short-lived URL, not to bytes.
            return httpx.Response(
                200,
                json={
                    "url": "https://lookaside.fbcdn.net/whatsapp/media/blob",
                    "mime_type": state["mime"],
                    "sha256": "meta-says-this",
                    "file_size": len(state["bytes"]),
                },
            )
        if "lookaside" in str(request.url):
            return httpx.Response(200, content=state["bytes"])
        if path.endswith("/media"):
            return httpx.Response(200, json={"id": UPLOADED_ID})
        if path.endswith("/messages"):
            return httpx.Response(200, json={"messages": [{"id": "wamid.SENT-MEDIA"}]})
        return httpx.Response(200, json={})

    real = WabaService.adapter_for

    def _adapter_for(self, waba, *, phone_number_id: str = ""):
        adapter = real(self, waba, phone_number_id=phone_number_id)
        adapter.client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        adapter.client._owns_http = True
        return adapter

    monkeypatch.setattr(WabaService, "adapter_for", _adapter_for)
    return state


def _image_message(wamid: str = "wamid.IMG", media_id: str = MEDIA_ID) -> dict:
    return {
        "from": SENDER,
        "id": wamid,
        "timestamp": str(int(utcnow().timestamp())),
        "type": "image",
        "image": {"id": media_id, "mime_type": "image/jpeg", "sha256": "abc", "caption": "my bill"},
    }


async def _inbound_image(client, make_user, session_factory, monkeypatch, message=None) -> dict:
    """Deliver an inbound image and apply it, stopping short of the download."""
    await _seed_number(client, make_user, session_factory, monkeypatch)
    await _post(client, _delivery(messages=[message or _image_message()]))
    routed: list[int] = []
    for row in await _events(session_factory):
        async with session_factory() as session:
            await WebhookService(session).process(row.id, dispatch_inbound=routed.append)
    async with session_factory() as session:
        return await MessageService(session).apply_inbound(routed[0])


# --- Inbound download (FR-WA-11; Doc 07 §17.2) -------------------------------
async def test_inbound_media_is_flagged_pending_but_not_downloaded_inline(
    client, make_user, session_factory, monkeypatch, dispatched, channel
) -> None:
    """A 15 MB video must not hold up the message that carried it (Doc 07 §17.4)."""
    result = await _inbound_image(client, make_user, session_factory, monkeypatch)

    assert result["media_pending"] is True and result["message_pk"]
    (message,) = await _rows(session_factory, Message)
    assert message.media_asset_id is None
    # The message is readable now; the bytes catch up on the media lane.
    assert message.content_json["media"]["channel_media_id"] == MEDIA_ID
    assert await _rows(session_factory, MediaAsset) == []
    assert channel["requests"] == []


async def test_download_stores_the_bytes_and_links_them(
    client, make_user, session_factory, monkeypatch, dispatched, channel
) -> None:
    result = await _inbound_image(client, make_user, session_factory, monkeypatch)

    async with session_factory() as session:
        outcome = await MediaIngestService(session).download_inbound(result["message_pk"])
    assert outcome["status"] == "linked" and outcome["deduplicated"] is False

    (asset,) = await _rows(session_factory, MediaAsset)
    assert asset.media_type == "image" and asset.mime_type == "image/jpeg"
    assert asset.byte_size == len(IMAGE)
    # Recomputed, not taken from the channel: dedup is only as sound as the hash.
    assert asset.sha256 == IMAGE_SHA
    assert asset.file_name is None and asset.created_by is None
    assert asset.usage_count == 1

    (message,) = await _rows(session_factory, Message)
    assert message.media_asset_id == asset.id

    # The bytes really are in storage and really are the bytes.
    from app.storage.base import get_provider

    assert await get_provider(asset.storage_backend).get(asset.storage_key) == IMAGE


async def test_identical_bytes_reuse_one_asset(
    client, make_user, session_factory, monkeypatch, dispatched, channel
) -> None:
    """Two customers sending the same file is one blob, not two (Doc 07 §17.2 dedup)."""
    first = await _inbound_image(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        await MediaIngestService(session).download_inbound(first["message_pk"])

    await _post(
        client, _delivery(messages=[_image_message(wamid="wamid.IMG2", media_id="media-other")])
    )
    routed: list[int] = []
    for row in await _events(session_factory):
        async with session_factory() as session:
            await WebhookService(session).process(row.id, dispatch_inbound=routed.append)
    async with session_factory() as session:
        second = await MessageService(session).apply_inbound(routed[-1])
    async with session_factory() as session:
        result = await MediaIngestService(session).download_inbound(second["message_pk"])

    assert result["deduplicated"] is True
    assets = await _rows(session_factory, MediaAsset)
    assert len(assets) == 1 and assets[0].usage_count == 2
    # Both messages point at the same blob.
    messages = await _rows(session_factory, Message)
    assert {m.media_asset_id for m in messages} == {assets[0].id}


async def test_download_is_idempotent(
    client, make_user, session_factory, monkeypatch, dispatched, channel
) -> None:
    """At-least-once task delivery must not re-fetch or double-count (Doc 06 §2.3)."""
    result = await _inbound_image(client, make_user, session_factory, monkeypatch)
    async with session_factory() as session:
        await MediaIngestService(session).download_inbound(result["message_pk"])
    calls = len(channel["requests"])

    async with session_factory() as session:
        again = await MediaIngestService(session).download_inbound(result["message_pk"])
    assert again["status"] == "already_linked"
    assert len(channel["requests"]) == calls
    (asset,) = await _rows(session_factory, MediaAsset)
    assert asset.usage_count == 1


async def test_a_redelivered_message_still_reports_pending_media(
    client, make_user, session_factory, monkeypatch, dispatched, channel
) -> None:
    """The first attempt may have stored the message and died before queueing the download."""
    result = await _inbound_image(client, make_user, session_factory, monkeypatch)
    (event,) = await _events(session_factory)

    async with session_factory() as session:
        duplicate = await MessageService(session).apply_inbound(event.id)
    assert duplicate["status"] == "duplicate"
    assert duplicate["media_pending"] is True and duplicate["message_pk"] == result["message_pk"]

    async with session_factory() as session:
        await MediaIngestService(session).download_inbound(result["message_pk"])
    async with session_factory() as session:
        settled = await MessageService(session).apply_inbound(event.id)
    assert settled["media_pending"] is False


async def test_a_message_without_media_is_never_downloaded(
    client, make_user, session_factory, monkeypatch, dispatched, channel
) -> None:
    from tests.test_api_webhooks import _message

    result = await _inbound_image(
        client, make_user, session_factory, monkeypatch, message=_message()
    )
    assert result["media_pending"] is False

    async with session_factory() as session:
        with pytest.raises(MediaUnavailable):
            await MediaIngestService(session).download_inbound(result["message_pk"])


async def test_oversized_media_is_rejected_by_the_same_gate_as_an_upload(
    client, make_user, session_factory, monkeypatch, dispatched, channel
) -> None:
    """Nothing a channel sends is trusted more than a file a user picked (Doc 04 §16)."""
    from app.storage.validation import MediaTooLarge

    result = await _inbound_image(client, make_user, session_factory, monkeypatch)
    channel["bytes"] = b"x" * (64 * 1024 * 1024)

    async with session_factory() as session:
        with pytest.raises(MediaTooLarge):
            await MediaIngestService(session).download_inbound(result["message_pk"])
    # Rejected before anything was written.
    assert await _rows(session_factory, MediaAsset) == []
    (message,) = await _rows(session_factory, Message)
    assert message.media_asset_id is None


async def test_missing_message_is_not_an_error(session_factory) -> None:
    async with session_factory() as session:
        assert (await MediaIngestService(session).download_inbound(9999))["status"] == "missing"


def test_media_reference_reads_canonical_content_only() -> None:
    assert media_reference(Message(content_json={"media": {"channel_media_id": "m-1"}})) == "m-1"
    assert media_reference(Message(content_json={"body": "hi"})) is None
    assert media_reference(Message(content_json={"media": {"link": "https://x"}})) is None
    assert media_reference(Message(content_json=None)) is None


def test_download_task_is_bound_to_the_media_lane() -> None:
    import app.channels.tasks as tasks

    assert tasks.download_inbound_media.queue_name == "media"


def test_inbound_task_queues_the_download_only_when_media_is_pending(monkeypatch) -> None:
    import app.channels.tasks as tasks

    queued: list[list[int]] = []
    monkeypatch.setattr(
        tasks.download_inbound_media, "apply_async", lambda args: queued.append(args)
    )

    async def _with_media(event_pk: int):
        return {"status": "applied", "message_pk": 42, "media_pending": True}

    async def _without(event_pk: int):
        return {"status": "applied", "message_pk": 43, "media_pending": False}

    monkeypatch.setattr(tasks, "_apply_inbound", _with_media)
    tasks.process_inbound_message.run(1)
    monkeypatch.setattr(tasks, "_apply_inbound", _without)
    tasks.process_inbound_message.run(2)

    assert queued == [[42]]


# --- Outbound upload (Doc 07 §17.3) ------------------------------------------
async def _stored_asset(session_factory, *, meta_media_id=None, expires_at=None) -> MediaAsset:
    from app.services.media_service import storage_key_for
    from app.storage.base import get_provider

    async with session_factory() as session:
        stored = await get_provider("local").put(
            storage_key_for(1, IMAGE_SHA, "bill.jpg"), IMAGE, content_type="image/jpeg"
        )
        asset = MediaAsset(
            organization_id=1,
            media_type="image",
            mime_type="image/jpeg",
            file_name="bill.jpg",
            byte_size=stored.byte_size,
            sha256=IMAGE_SHA,
            storage_backend=stored.backend,
            storage_key=stored.storage_key,
            meta_media_id=meta_media_id,
            meta_media_expires_at=expires_at,
        )
        session.add(asset)
        await session.commit()
        return asset


async def test_sending_a_stored_asset_uploads_it_and_caches_the_id(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, channel
) -> None:
    await _open_window(client, session_factory, monkeypatch, make_user)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)
    asset = await _stored_asset(session_factory)

    resp = await client.post(
        SEND_URL,
        headers=headers | _key(),
        json={
            "phone_number_id": await _number_id(client, headers),
            "to": f"+{SENDER}",
            "type": "media",
            "media": {"kind": "image", "media_asset_id": asset.public_id, "caption": "your bill"},
        },
    )
    assert resp.status_code == 202, resp.text

    message = [m for m in await _rows(session_factory, Message) if m.direction == "outbound"][0]
    assert message.media_asset_id == asset.id and message.message_type == "image"
    # Referencing an asset is what stops it being deleted out from under the message.
    assert (await _rows(session_factory, MediaAsset))[0].usage_count == 1

    async with session_factory() as session:
        await SendService(session).deliver(message.id)

    import json as _json

    sends = [r for r in channel["requests"] if r.url.path.endswith("/messages")]
    body = _json.loads(sends[0].content)
    # The upload's id is what goes out — not a link, and not our internal id.
    assert body["type"] == "image"
    assert body["image"] == {"id": UPLOADED_ID, "caption": "your bill"}

    refreshed = (await _rows(session_factory, MediaAsset))[0]
    assert refreshed.meta_media_id == UPLOADED_ID
    assert refreshed.meta_media_expires_at is not None


async def test_a_cached_channel_id_is_reused_instead_of_reuploading(
    client, make_user, session_factory, monkeypatch, dispatched, channel
) -> None:
    """The same file sent a hundred times is uploaded once (Doc 06 §2.3 media-id refresh)."""
    asset = await _stored_asset(
        session_factory, meta_media_id="media-cached", expires_at=utcnow() + META_MEDIA_TTL
    )
    await _seed_number(client, make_user, session_factory, monkeypatch)

    async with session_factory() as session:
        from app.repositories.waba import PhoneNumberRepository, WabaRepository

        number = (await PhoneNumberRepository(session).list_for_org(1))[0]
        waba = await WabaRepository(session).get_by_id(number.waba_id)
        adapter = WabaService(session).adapter_for(waba, phone_number_id=number.phone_number_id)
        media_id = await MediaIngestService(session).channel_media_id(asset, adapter)
        await adapter.close()

    assert media_id == "media-cached"
    assert [r for r in channel["requests"] if r.url.path.endswith("/media")] == []


async def test_an_expired_channel_id_is_refreshed(
    client, make_user, session_factory, monkeypatch, dispatched, channel
) -> None:
    """Meta's ids lapse; re-upload before the edge rather than on a rejected send."""
    asset = await _stored_asset(
        session_factory, meta_media_id="media-stale", expires_at=utcnow()
    )
    await _seed_number(client, make_user, session_factory, monkeypatch)

    async with session_factory() as session:
        from app.repositories.waba import PhoneNumberRepository, WabaRepository

        number = (await PhoneNumberRepository(session).list_for_org(1))[0]
        waba = await WabaRepository(session).get_by_id(number.waba_id)
        adapter = WabaService(session).adapter_for(waba, phone_number_id=number.phone_number_id)
        media_id = await MediaIngestService(session).channel_media_id(asset, adapter)
        await adapter.close()

    assert media_id == UPLOADED_ID
    assert [r for r in channel["requests"] if r.url.path.endswith("/media")]


async def test_sending_an_unknown_asset_is_404(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, channel
) -> None:
    await _open_window(client, session_factory, monkeypatch, make_user)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)

    resp = await client.post(
        SEND_URL,
        headers=headers | _key(),
        json={
            "phone_number_id": await _number_id(client, headers),
            "to": f"+{SENDER}",
            "type": "media",
            "media": {"kind": "image", "media_asset_id": str(uuid.uuid4())},
        },
    )
    assert resp.status_code == 404, resp.text
    assert sent == []


async def test_media_send_needs_exactly_one_source(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent, channel
) -> None:
    await _open_window(client, session_factory, monkeypatch, make_user)
    headers = await _headers(client, make_user, email="agent@vi.co", is_superuser=True)
    number_id = await _number_id(client, headers)

    for media in (
        {"kind": "image"},
        {"kind": "image", "link": "https://x/y.jpg", "media_asset_id": str(uuid.uuid4())},
    ):
        resp = await client.post(
            SEND_URL,
            headers=headers | _key(),
            json={"phone_number_id": number_id, "to": f"+{SENDER}", "type": "media", "media": media},
        )
        assert resp.status_code == 422, resp.text
