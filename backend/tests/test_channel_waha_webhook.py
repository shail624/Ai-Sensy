"""QR-04 — WAHA webhook ingestion.

Fully hermetic. The envelope shapes asserted here were captured from HMAC-verified deliveries during
physical-phone certification against ``devlikeapro/waha@sha256:33ecd1b7…`` (2026.7.2 / NOWEB / CORE),
including the real inbound text, the ``message``/``message.any`` pair that shared one
``envelope.id``, and the ``@lid`` addressing inbound events actually arrive with.
"""

from __future__ import annotations

import hmac
from hashlib import sha512

import pytest

from app.channels.capabilities import Capability
from app.channels.errors import ChannelNotSupported
from app.channels.models import InboundEventType
from app.channels.waha import (
    MAX_BODY_BYTES,
    PROHIBITED_CAPABILITIES,
    WahaBodyTooLarge,
    WahaChannelAdapter,
    WahaCredentials,
    canonical_message_id,
    event_identity,
    parse_events,
    verify_signature,
)
from app.core.config import settings

SECRET = "certification-hmac-secret"
CREDS = WahaCredentials(base_url="http://waha.internal:3000", api_key="test-key-never-logged")


def _sign(body: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), body, sha512).hexdigest()


def _inbound(envelope_id: str = "evt_01kzeznz4jfme61wd08t539q4k", event: str = "message") -> dict:
    """A real inbound text delivery, as certification captured it."""
    return {
        "id": envelope_id,
        "timestamp": 1786135647000,
        "event": event,
        "session": "phonecert",
        "me": {"id": "919355585553@c.us", "lid": "210912345485@lid"},
        "payload": {
            "id": "false_651430587620@lid_AC5B2C11AC80006B889303F756CFA349",
            "timestamp": 1786135647,
            "from": "651430587620@lid",
            "fromMe": False,
            "body": "QRCERT-FINAL-INBOUND",
            "hasMedia": False,
            "notifyName": "Second Account",
        },
        "engine": "NOWEB",
        "environment": {"version": "2026.7.2"},
    }


@pytest.fixture
def configured_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "waha_webhook_hmac_secret", SECRET)


# --- Signature verification -----------------------------------------------------------------------


def test_valid_hmac_accepted() -> None:
    body = b'{"event":"message"}'
    assert verify_signature(body, _sign(body), SECRET) is True


def test_signature_is_over_the_raw_body() -> None:
    """Re-serialising the JSON changes the bytes and must break verification."""
    body = b'{"a":1,"b":2}'
    reserialised = b'{"a": 1, "b": 2}'
    signature = _sign(body)
    assert verify_signature(body, signature, SECRET) is True
    assert verify_signature(reserialised, signature, SECRET) is False


@pytest.mark.parametrize("signature", [None, "", "deadbeef", "not-hex", "ZZZZ"])
def test_missing_or_invalid_signature_rejected(signature: str | None) -> None:
    assert verify_signature(b"{}", signature, SECRET) is False


def test_tampered_body_rejected() -> None:
    body = b'{"event":"message"}'
    assert verify_signature(b'{"event":"messagX"}', _sign(body), SECRET) is False


def test_unconfigured_secret_rejects_everything() -> None:
    """An unset secret must never become a silent authentication bypass."""
    body = b"{}"
    assert verify_signature(body, _sign(body, ""), "") is False
    assert verify_signature(body, _sign(body), "") is False


def test_wrong_secret_rejected() -> None:
    body = b'{"event":"message"}'
    assert verify_signature(body, _sign(body, "other-secret"), SECRET) is False


def test_downgraded_algorithm_rejected() -> None:
    body = b"{}"
    assert verify_signature(body, _sign(body), SECRET, algorithm="md5") is False
    assert verify_signature(body, _sign(body), SECRET, algorithm="SHA512") is True


def test_oversized_body_refused_before_hashing() -> None:
    with pytest.raises(WahaBodyTooLarge):
        verify_signature(b"x" * (MAX_BODY_BYTES + 1), "aa", SECRET)


def test_signature_check_is_constant_time() -> None:
    """Uses ``hmac.compare_digest`` rather than ``==``."""
    import inspect

    from app.channels.waha import webhook as module

    source = inspect.getsource(module.verify_signature)
    assert "compare_digest" in source


# --- Event identity / dedupe ------------------------------------------------------------------------


def test_envelope_id_alone_is_not_the_key() -> None:
    """Certification: one provider message arrives as both `message` and `message.any`.

    They share an ``envelope.id``. Keying on it alone would silently discard a genuine event.
    """
    shared = "evt_01kzeznz4jfme61wd08t539q4k"
    a = event_identity(session="phonecert", event_type="message", envelope_id=shared)
    b = event_identity(session="phonecert", event_type="message.any", envelope_id=shared)
    assert a != b


def test_same_event_retry_collapses() -> None:
    """At-least-once delivery: a retry repeats envelope.id and must produce the same key."""
    shared = "evt_01kzeznz4jfme61wd08t539q4k"
    first = event_identity(session="phonecert", event_type="message", envelope_id=shared)
    retry = event_identity(session="phonecert", event_type="message", envelope_id=shared)
    assert first == retry


def test_identity_is_session_scoped() -> None:
    """Two tenants' sessions must never collide on a provider-chosen envelope id."""
    shared = "evt_shared"
    a = event_identity(session="tenant-a", event_type="message", envelope_id=shared)
    b = event_identity(session="tenant-b", event_type="message", envelope_id=shared)
    assert a != b


def test_identity_fits_the_column_regardless_of_component_length() -> None:
    """``webhook_events.event_id`` is String(128). The digest is fixed-length, so this holds for
    any component length rather than depending on where a cut lands."""
    for length in (0, 1, 64, 127, 128, 200, 1000):
        key = event_identity(
            session="s" * length, event_type="message", envelope_id="evt_tail"
        )
        assert len(key) <= 128


def test_long_components_still_discriminate_by_envelope_id() -> None:
    """The specific defect this replaced: previously, once ``session``/``event_type`` alone
    exceeded 128 characters, ``envelope_id`` was cut away entirely and every envelope collapsed
    to one key. The digest must still distinguish them."""
    long_session = "s" * 120
    a = event_identity(session=long_session, event_type="message", envelope_id="AAAA1111")
    b = event_identity(session=long_session, event_type="message", envelope_id="BBBB2222")
    assert a != b


def _old_truncated_identity(session: str, event_type: str, envelope_id: str) -> str:
    """The removed QR-04 algorithm, reconstructed only to prove it collided.

    Not a call into production code — the implementation under test no longer contains this
    logic. Kept purely so the regression below documents the defect it replaced.
    """
    return f"waha:{session}:{event_type}:{envelope_id}"[:128]


def test_old_truncation_algorithm_did_collide_on_long_inputs() -> None:
    """Reproduces the verified defect: Python's ``s[:128]`` keeps the LEFT prefix, so placing
    ``envelope_id`` last did not make it "survive truncation" — it made it the first thing cut.
    Once the fixed prefix alone reaches 128 characters, every envelope_id is discarded and two
    distinct events collapse onto one stored key."""
    long_session = "s" * 120
    prefix = f"waha:{long_session}:message:"
    assert len(prefix) > 128, "prefix must itself exceed the column width to prove the defect"

    a = _old_truncated_identity(long_session, "message", "AAAA1111")
    b = _old_truncated_identity(long_session, "message", "BBBB2222")
    assert a == b, "the old algorithm is expected to collide here — that was the defect"


def test_new_algorithm_does_not_collide_on_the_same_long_inputs() -> None:
    """The exact inputs that collided under the old algorithm must not collide under the new one."""
    long_session = "s" * 120
    a = event_identity(session=long_session, event_type="message", envelope_id="AAAA1111")
    b = event_identity(session=long_session, event_type="message", envelope_id="BBBB2222")
    assert a != b


def test_old_algorithm_was_also_delimiter_ambiguous() -> None:
    """A second, length-independent defect in the removed algorithm: plain ``":"`` joins let one
    component's content be mistaken for another component's boundary."""
    a = _old_truncated_identity("tenant", "a:b", "ENV1")
    b = _old_truncated_identity("tenant:a", "b", "ENV1")
    assert a == b, "the old algorithm is expected to collide here — that was the defect"


@pytest.mark.parametrize(
    ("session_a", "event_type_a", "session_b", "event_type_b"),
    [
        ("tenant", "a:b", "tenant:a", "b"),
        ("tenant", "a|b", "tenant|a", "b"),
        ("1:x", "y", "1", "x:y"),
        ("", "a", "a", ""),
        ("a" * 3 + ":a", "a", "a" * 3, "a:a"),
    ],
)
def test_new_algorithm_resists_delimiter_injection(
    session_a: str, event_type_a: str, session_b: str, event_type_b: str
) -> None:
    """Adversarial component values that were ambiguous under plain concatenation must not
    produce equivalent canonical inputs under the length-prefixed digest."""
    envelope = "ENV1"
    a = event_identity(session=session_a, event_type=event_type_a, envelope_id=envelope)
    b = event_identity(session=session_b, event_type=event_type_b, envelope_id=envelope)
    assert a != b


def test_identity_is_deterministic_across_repeated_calls() -> None:
    """Not Python's ``hash()`` — which is randomized per process via ``PYTHONHASHSEED`` — so the
    same triple must produce the same key on every call, in this process or another."""
    calls = [
        event_identity(session="phonecert", event_type="message", envelope_id="evt_1")
        for _ in range(50)
    ]
    assert len(set(calls)) == 1


def test_identity_does_not_use_python_hash() -> None:
    import inspect

    from app.channels.waha import webhook as module

    source = inspect.getsource(module.event_identity) + inspect.getsource(module._canonicalize)
    assert "hash(" not in source
    assert "sha256" in source


def test_canonicalize_is_injective_for_boundary_edge_cases() -> None:
    """Empty components, components equal to a digit string, and components containing the
    delimiter characters themselves must all still discriminate correctly."""
    from app.channels.waha.webhook import _canonicalize

    cases = [
        ("", "", ""),
        ("0", "", ""),
        ("", "0", ""),
        ("1:2", "3", "4"),
        ("1", "2:3", "4"),
        ("a|1:b", "c", "d"),
    ]
    canon = {_canonicalize(*case) for case in cases}
    assert len(canon) == len(cases)


def test_parse_produces_distinct_keys_for_the_shared_envelope() -> None:
    shared = "evt_01kzeznz4jfme61wd08t539q4k"
    keys = {
        parse_events(_inbound(shared, event))[0].event_id
        for event in ("message", "message.any")
    }
    assert len(keys) == 2


def test_duplicate_delivery_is_byte_identical_and_yields_one_key() -> None:
    delivery = _inbound()
    keys = {parse_events(delivery)[0].event_id for _ in range(5)}
    assert len(keys) == 1


def test_concurrent_duplicate_delivery_is_safe() -> None:
    """Concurrent retries must resolve to one identity.

    ``messages`` is partitioned, so MySQL cannot enforce endpoint/provider-id uniqueness
    (error 1503). Identity must therefore be deterministic in code — proven here rather than
    delegated to a constraint that cannot exist.
    """
    from concurrent.futures import ThreadPoolExecutor

    delivery = _inbound()
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda _: parse_events(delivery)[0].event_id, range(64)))
    assert len(set(results)) == 1
    assert results[0] is not None


# --- Parsing / normalization ------------------------------------------------------------------------


def test_inbound_text_is_a_messages_event() -> None:
    events = parse_events(_inbound())
    assert len(events) == 1
    event = events[0]
    assert event.type is InboundEventType.MESSAGES
    assert event.channel_number_id == "phonecert"
    assert event.payload["payload"]["body"] == "QRCERT-FINAL-INBOUND"


def test_outbound_echo_is_not_ingested_as_inbound() -> None:
    """``fromMe`` true is our own message echoed back; QR-05 owns delivery state, not QR-04."""
    delivery = _inbound()
    delivery["payload"]["fromMe"] = True
    assert parse_events(delivery)[0].type is InboundEventType.UNKNOWN


def test_ack_event_is_recorded_not_applied() -> None:
    delivery = _inbound(event="message.ack")
    delivery["payload"]["fromMe"] = True
    assert parse_events(delivery)[0].type is InboundEventType.UNKNOWN


@pytest.mark.parametrize("event", ["session.status", "state.change", "totally.unknown"])
def test_unknown_event_types_are_emitted_not_dropped(event: str) -> None:
    """Doc 06 §11.6 dead-letters unknown events; that requires the adapter to emit them."""
    events = parse_events(_inbound(event=event))
    assert len(events) == 1
    assert events[0].type is InboundEventType.UNKNOWN


@pytest.mark.parametrize(
    "delivery",
    [
        {},
        {"event": "message"},
        {"id": "evt_1", "event": "message"},
        {"id": "evt_1", "session": "phonecert"},
        {"id": "", "event": "", "session": ""},
        {"id": 7, "event": ["message"], "session": {"a": 1}},
    ],
)
def test_malformed_envelope_fails_closed(delivery: dict) -> None:
    events = parse_events(delivery)
    assert len(events) == 1
    assert events[0].type is InboundEventType.UNKNOWN
    assert events[0].event_id is None


def test_payload_is_preserved_for_replay() -> None:
    delivery = _inbound()
    assert parse_events(delivery)[0].payload == delivery


# --- Identity handling -------------------------------------------------------------------------------


def test_canonical_message_id_extracts_trailing_component() -> None:
    assert (
        canonical_message_id("false_651430587620@lid_AC5B2C11AC80006B889303F756CFA349")
        == "AC5B2C11AC80006B889303F756CFA349"
    )
    assert (
        canonical_message_id("true_919355585553@c.us_3EB0D11C8F76C5EB15AD6B")
        == "3EB0D11C8F76C5EB15AD6B"
    )


@pytest.mark.parametrize("raw", [None, "", "   ", 42, {"id": "x"}])
def test_canonical_message_id_rejects_unusable(raw: object) -> None:
    assert canonical_message_id(raw) is None


def test_provider_addressing_is_not_normalised_away() -> None:
    """@c.us / @lid / @s.whatsapp.net evidence must survive into the stored payload."""
    adapter = WahaChannelAdapter(CREDS)
    message = adapter.to_inbound_message(_inbound())
    assert message.from_id == "651430587620@lid"
    assert message.channel_message_id == "AC5B2C11AC80006B889303F756CFA349"


def test_inbound_text_translation() -> None:
    adapter = WahaChannelAdapter(CREDS)
    message = adapter.to_inbound_message(_inbound())
    assert message.message_type == "text"
    assert message.content == {"body": "QRCERT-FINAL-INBOUND"}
    assert message.profile_name == "Second Account"
    assert message.occurred_at is not None


def test_media_inbound_is_not_faked_as_empty_text() -> None:
    """Media ingestion is a later milestone; it must not masquerade as an empty text message."""
    delivery = _inbound()
    delivery["payload"]["body"] = None
    delivery["payload"]["hasMedia"] = True
    adapter = WahaChannelAdapter(CREDS)
    message = adapter.to_inbound_message(delivery)
    assert message.message_type == "unsupported"
    assert message.content == {"provider_has_media": True}


def test_message_without_provider_id_is_rejected() -> None:
    delivery = _inbound()
    delivery["payload"]["id"] = None
    adapter = WahaChannelAdapter(CREDS)
    with pytest.raises(ValueError):
        adapter.to_inbound_message(delivery)


# --- Adapter wiring / security -----------------------------------------------------------------------


def test_adapter_verifies_against_configured_secret(configured_secret: None) -> None:
    adapter = WahaChannelAdapter(CREDS)
    body = b'{"event":"message"}'
    assert adapter.verify_webhook_signature(body, _sign(body)) is True
    assert adapter.verify_webhook_signature(body, _sign(body, "wrong")) is False
    assert adapter.verify_webhook_signature(body, None) is False


def test_adapter_rejects_when_secret_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "waha_webhook_hmac_secret", "")
    adapter = WahaChannelAdapter(CREDS)
    body = b"{}"
    assert adapter.verify_webhook_signature(body, _sign(body)) is False


def test_secret_defaults_to_empty() -> None:
    """No default secret may exist — an unconfigured deployment must reject, not accept."""
    field = type(settings).model_fields["waha_webhook_hmac_secret"]
    assert field.default == ""


def test_secret_never_appears_in_parsed_output(configured_secret: None) -> None:
    events = parse_events(_inbound())
    assert SECRET not in repr(events)
    assert "test-key-never-logged" not in repr(events)


def test_ingestion_is_capability_gated() -> None:
    class _NoStream(WahaChannelAdapter):
        capabilities = frozenset({Capability.HEALTH})

    adapter = _NoStream(CREDS)
    with pytest.raises(ChannelNotSupported):
        adapter.parse_webhook(_inbound())
    with pytest.raises(ChannelNotSupported):
        adapter.to_inbound_message(_inbound())


def test_session_stream_declared() -> None:
    assert Capability.SESSION_STREAM in WahaChannelAdapter.capabilities


def test_qr04_declares_no_later_capability() -> None:
    withheld = {
        Capability.SESSION_RECONNECT,
        Capability.SESSION_LOGOUT,
        Capability.HISTORY_SYNC,
        Capability.MEDIA,
        Capability.MEDIA_UPLOAD,
        Capability.MEDIA_DOWNLOAD,
    }
    assert not (WahaChannelAdapter.capabilities & withheld)


def test_prohibited_capabilities_unchanged() -> None:
    assert not (WahaChannelAdapter.capabilities & PROHIBITED_CAPABILITIES)
    assert frozenset(
        {Capability.BULK, Capability.CAMPAIGNS, Capability.TEMPLATE}
    ) == PROHIBITED_CAPABILITIES


def test_qr04_adds_no_send_or_teardown() -> None:
    for name in ("stop_session", "restart_session", "logout", "delete_session", "send_image"):
        assert not hasattr(WahaChannelAdapter, name)
