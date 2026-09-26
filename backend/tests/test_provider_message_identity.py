"""QR-00 — provider message identity scoping and re-authentication health projection.

Two provider-neutral foundations, both prerequisites for introducing a second (QR) provider:

* **Identity scoping.** A provider message id is unique only inside the endpoint that issued it
  (ADR-0020 "Provider message identity is scoped by connection/endpoint"; Doc 33 §6.1 "Message
  identity"). Meta's ``wamid`` happens to be globally unique, so a global lookup was survivable
  with one provider — it is not once a session-scoped QR id can legitimately repeat. These tests
  pin the scoped behaviour before any such provider exists.
* **Re-auth projection.** Doc 33 §6.1 requires the four operator signals Healthy/Warning/Critical/
  Re-auth Required. These tests pin the derived projection that supplies the fourth without adding
  a redundant persisted state.

No WAHA/provider runtime is exercised here — QR-00 introduces none.
"""

from __future__ import annotations

import pytest

from app.channels.attention import (
    SessionAttentionState,
    project_attention_state,
    requires_reauthentication,
)
from app.channels.foundation import ProviderHealthState
from app.channels.runtime import PairingState
from app.channels.session import SessionState
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.message import DIRECTION_OUTBOUND, MSG_SENT, Message
from app.models.organization import Organization
from app.models.waba import PhoneNumber, WhatsAppBusinessAccount
from app.repositories.message import MessageRepository

# --- helpers ------------------------------------------------------------------------------------


async def _endpoint(session, organization_id: int, *, suffix: str) -> PhoneNumber:
    """A WABA + phone number — the existing 'channel endpoint' authority (ADR-0020)."""
    waba = WhatsAppBusinessAccount(
        organization_id=organization_id,
        waba_id=f"WABA-{suffix}",
        business_name=f"Business {suffix}",
        access_token_enc=b"cipher",
    )
    session.add(waba)
    await session.flush()
    number = PhoneNumber(
        organization_id=organization_id,
        waba_id=waba.id,
        phone_number_id=f"PN-{suffix}",
        display_number=f"+9999000{suffix}",
    )
    session.add(number)
    await session.flush()
    return number


async def _message(session, *, number: PhoneNumber, provider_message_id: str) -> Message:
    contact = Contact(
        organization_id=number.organization_id,
        wa_id=f"9199900{number.id:05d}",
        phone_e164=f"+9199900{number.id:05d}",
        full_name="Preview Customer",
    )
    session.add(contact)
    await session.flush()
    conversation = Conversation(
        organization_id=number.organization_id,
        phone_number_id=number.id,
        contact_id=contact.id,
    )
    session.add(conversation)
    await session.flush()
    message = Message(
        organization_id=number.organization_id,
        conversation_id=conversation.id,
        phone_number_id=number.id,
        contact_id=contact.id,
        direction=DIRECTION_OUTBOUND,
        wamid=provider_message_id,
        message_type="text",
        content_json={"body": "hello"},
        status=MSG_SENT,
    )
    session.add(message)
    await session.flush()
    return message


# --- identity scoping ---------------------------------------------------------------------------


async def test_same_provider_message_id_can_exist_on_two_endpoints(db_session, organization) -> None:
    """The core reason this scoping exists: a QR provider's ids are session-scoped, so the same
    id may legitimately appear on two endpoints. Each must resolve to its own message."""
    endpoint_a = await _endpoint(db_session, organization.id, suffix="A")
    endpoint_b = await _endpoint(db_session, organization.id, suffix="B")

    shared_id = "PROVIDER-MSG-COLLISION-1"
    message_a = await _message(db_session, number=endpoint_a, provider_message_id=shared_id)
    message_b = await _message(db_session, number=endpoint_b, provider_message_id=shared_id)
    assert message_a.id != message_b.id

    repo = MessageRepository(db_session)
    found_a = await repo.get_by_provider_message_id(shared_id, phone_number_id=endpoint_a.id)
    found_b = await repo.get_by_provider_message_id(shared_id, phone_number_id=endpoint_b.id)

    assert found_a is not None and found_a.id == message_a.id
    assert found_b is not None and found_b.id == message_b.id


async def test_endpoints_cannot_resolve_each_others_messages(db_session, organization) -> None:
    endpoint_a = await _endpoint(db_session, organization.id, suffix="A")
    endpoint_b = await _endpoint(db_session, organization.id, suffix="B")
    await _message(db_session, number=endpoint_a, provider_message_id="ONLY-ON-A")

    repo = MessageRepository(db_session)
    assert await repo.get_by_provider_message_id("ONLY-ON-A", phone_number_id=endpoint_a.id)
    assert (
        await repo.get_by_provider_message_id("ONLY-ON-A", phone_number_id=endpoint_b.id) is None
    )


async def test_organizations_cannot_resolve_each_others_messages(db_session, organization) -> None:
    """Tenant isolation: the endpoint pins the tenant because ``phone_numbers.organization_id`` is
    NOT NULL, so an endpoint-scoped read can never cross an organization boundary."""
    other_org = Organization(name="Other Tenant", slug="other-tenant")
    db_session.add(other_org)
    await db_session.flush()

    endpoint_ours = await _endpoint(db_session, organization.id, suffix="A")
    endpoint_theirs = await _endpoint(db_session, other_org.id, suffix="Z")

    shared_id = "CROSS-TENANT-ID"
    ours = await _message(db_session, number=endpoint_ours, provider_message_id=shared_id)
    theirs = await _message(db_session, number=endpoint_theirs, provider_message_id=shared_id)

    repo = MessageRepository(db_session)
    found_ours = await repo.get_by_provider_message_id(shared_id, phone_number_id=endpoint_ours.id)
    found_theirs = await repo.get_by_provider_message_id(
        shared_id, phone_number_id=endpoint_theirs.id
    )

    assert found_ours is not None and found_ours.id == ours.id
    assert found_ours.organization_id == organization.id
    assert found_theirs is not None and found_theirs.id == theirs.id
    assert found_theirs.organization_id == other_org.id
    assert found_ours.id != found_theirs.id


async def test_lookup_scope_cannot_be_omitted() -> None:
    """There is deliberately no unscoped variant — the scope is keyword-only and required, so a
    global cross-tenant fallback cannot be written by accident."""
    import inspect

    signature = inspect.signature(MessageRepository.get_by_provider_message_id)
    scope = signature.parameters["phone_number_id"]
    assert scope.kind is inspect.Parameter.KEYWORD_ONLY
    assert scope.default is inspect.Parameter.empty
    assert not hasattr(MessageRepository, "get_by_wamid")


async def test_unknown_provider_message_id_returns_none(db_session, organization) -> None:
    endpoint = await _endpoint(db_session, organization.id, suffix="A")
    repo = MessageRepository(db_session)
    assert await repo.get_by_provider_message_id("NEVER-SEEN", phone_number_id=endpoint.id) is None


# --- re-authentication projection ---------------------------------------------------------------


@pytest.mark.parametrize(
    "session_state",
    [SessionState.WAITING_FOR_PAIRING, SessionState.EXPIRED],
)
def test_session_states_that_require_reauthentication(session_state: SessionState) -> None:
    assert requires_reauthentication(session_state=session_state, pairing_state=PairingState.PAIRED)


@pytest.mark.parametrize(
    "pairing_state",
    [PairingState.PAIRING_EXPIRED, PairingState.PAIRING_CANCELLED],
)
def test_pairing_states_that_require_reauthentication(pairing_state: PairingState) -> None:
    assert requires_reauthentication(
        session_state=SessionState.ACTIVE, pairing_state=pairing_state
    )


@pytest.mark.parametrize(
    "session_state",
    [
        SessionState.REGISTERED,
        SessionState.INITIALIZING,
        SessionState.ACTIVE,
        SessionState.DEGRADED,
        SessionState.RECONNECTING,
        SessionState.PAUSED,
    ],
)
def test_healthy_lifecycle_states_do_not_require_reauthentication(
    session_state: SessionState,
) -> None:
    assert not requires_reauthentication(
        session_state=session_state, pairing_state=PairingState.PAIRED
    )


def test_terminated_session_never_requires_reauthentication() -> None:
    """A terminated session was ended deliberately — it is finished, not broken. Surfacing it as
    'needs re-auth' would invite re-pairing something an operator intentionally shut down."""
    for pairing_state in PairingState:
        assert not requires_reauthentication(
            session_state=SessionState.TERMINATED, pairing_state=pairing_state
        )


def test_projection_covers_all_four_required_operator_signals() -> None:
    """Doc 33 §6.1 requires Healthy / Warning / Critical / Re-auth Required to be representable."""
    healthy = project_attention_state(
        health_state=ProviderHealthState.HEALTHY,
        session_state=SessionState.ACTIVE,
        pairing_state=PairingState.PAIRED,
    )
    warning = project_attention_state(
        health_state=ProviderHealthState.DEGRADED,
        session_state=SessionState.ACTIVE,
        pairing_state=PairingState.PAIRED,
    )
    critical = project_attention_state(
        health_state=ProviderHealthState.UNHEALTHY,
        session_state=SessionState.ACTIVE,
        pairing_state=PairingState.PAIRED,
    )
    reauth = project_attention_state(
        health_state=ProviderHealthState.UNKNOWN,
        session_state=SessionState.WAITING_FOR_PAIRING,
        pairing_state=PairingState.PAIRING_REQUESTED,
    )

    assert healthy is SessionAttentionState.HEALTHY
    assert warning is SessionAttentionState.WARNING
    assert critical is SessionAttentionState.CRITICAL
    assert reauth is SessionAttentionState.REAUTH_REQUIRED
    assert len({healthy, warning, critical, reauth}) == 4


def test_reauth_outranks_observed_health() -> None:
    """A session awaiting a scan may still report healthy/degraded; the actionable signal wins."""
    for health_state in ProviderHealthState:
        assert (
            project_attention_state(
                health_state=health_state,
                session_state=SessionState.WAITING_FOR_PAIRING,
                pairing_state=PairingState.PAIRING_AVAILABLE,
            )
            is SessionAttentionState.REAUTH_REQUIRED
        )


def test_projection_accepts_stored_string_values() -> None:
    """Callers read these off model columns, which are plain strings."""
    assert (
        project_attention_state(
            health_state="healthy", session_state="active", pairing_state="paired"
        )
        is SessionAttentionState.HEALTHY
    )


def test_projection_is_total_over_every_state_combination() -> None:
    """No combination of the frozen state machines may raise or fall through."""
    for health_state in ProviderHealthState:
        for session_state in SessionState:
            for pairing_state in PairingState:
                result = project_attention_state(
                    health_state=health_state,
                    session_state=session_state,
                    pairing_state=pairing_state,
                )
                assert isinstance(result, SessionAttentionState)


def test_projection_introduces_no_provider_specific_state() -> None:
    """QR-00 stays provider-neutral: no adapter/vendor name may leak into the vocabulary."""
    values = {state.value for state in SessionAttentionState}
    assert values == {"unknown", "healthy", "warning", "critical", "reauth_required"}
    assert not any("waha" in value or "meta" in value for value in values)
