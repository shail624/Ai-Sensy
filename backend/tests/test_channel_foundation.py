"""M13-01 provider-neutral channel foundation regressions."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.channels import base as channel_base
from app.channels.base import ChannelAdapter
from app.channels.capabilities import Capability, ChannelType
from app.channels.dependencies import get_channel_foundation
from app.channels.errors import ChannelConfigError
from app.channels.flags import (
    ChannelFeatureFlagResolver,
    OmnichannelFeatureFlag,
)
from app.channels.foundation import (
    ChannelMetadata,
    CommunicationIntent,
    CommunicationOrigin,
    CommunicationPolicy,
    CommunicationPurpose,
    ProviderDesiredState,
    ProviderHealth,
    ProviderHealthState,
    ProviderLifecycle,
    ProviderObservedState,
)
from app.channels.models import ChannelStatus, OutboundMessage, SendResult
from app.channels.registry import CapabilityRegistry, ProviderRegistry
from app.channels.validation import evaluate_communication_policy
from app.models.settings import FeatureFlag


class _FoundationAdapter(ChannelAdapter):
    channel_type = ChannelType.WHATSAPP
    connector_type = "foundation_test"
    capabilities = frozenset({Capability.TEXT, Capability.HEALTH})

    async def authenticate(self) -> None:
        return None

    async def status(self) -> ChannelStatus:
        return ChannelStatus(connected=True, identity="foundation")

    async def _dispatch(self, message: OutboundMessage) -> SendResult:
        return SendResult(message_id=message.idempotency_key)


def test_provider_registry_uses_existing_adapter_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    capabilities = CapabilityRegistry()
    providers = ProviderRegistry(capabilities)
    metadata = ChannelMetadata(
        connector_type="foundation_test",
        channel_type=ChannelType.WHATSAPP,
        display_name="Foundation Test",
        capabilities=_FoundationAdapter.capabilities,
        lifecycle_managed=True,
        health_managed=True,
    )
    providers.register(metadata)
    monkeypatch.setitem(
        channel_base._ADAPTERS,
        "foundation_test",
        lambda **_: _FoundationAdapter(),
    )

    adapter = providers.resolve_adapter("foundation_test")

    assert isinstance(adapter, _FoundationAdapter)
    assert providers.available() == ("foundation_test",)
    assert capabilities.require("foundation_test") == _FoundationAdapter.capabilities
    assert capabilities.supports("foundation_test", Capability.TEXT)


def test_registry_rejects_conflicting_provider_metadata() -> None:
    capabilities = CapabilityRegistry()
    providers = ProviderRegistry(capabilities)
    providers.register(
        ChannelMetadata(
            connector_type="generic_provider",
            channel_type=ChannelType.WHATSAPP,
            display_name="Generic Provider",
            capabilities=frozenset({Capability.TEXT}),
        )
    )

    with pytest.raises(ChannelConfigError):
        providers.register(
            ChannelMetadata(
                connector_type="generic_provider",
                channel_type=ChannelType.WHATSAPP,
                display_name="Changed Provider",
                capabilities=frozenset({Capability.MEDIA}),
            )
        )


def test_communication_policy_is_provider_independent_and_fail_closed() -> None:
    intent = CommunicationIntent(
        organization_id=7,
        intent_key="customer-service-reply",
        channel_type=ChannelType.WHATSAPP,
        purpose=CommunicationPurpose.SERVICE,
        origin=CommunicationOrigin.MANUAL,
        required_capabilities=frozenset({Capability.TEXT}),
    )
    policy = CommunicationPolicy(
        policy_key="manual-service",
        organization_id=7,
        allowed_purposes=frozenset({CommunicationPurpose.SERVICE}),
        allowed_origins=frozenset({CommunicationOrigin.MANUAL}),
    )

    allowed = evaluate_communication_policy(intent, policy, {Capability.TEXT})
    denied = evaluate_communication_policy(intent, policy, set())

    assert allowed.allowed is True
    assert allowed.reasons == ()
    assert denied.allowed is False
    assert denied.reasons == ("missing_capabilities",)
    assert denied.missing_capabilities == frozenset({Capability.TEXT})


def test_policy_blocks_bulk_and_cross_organization_use() -> None:
    intent = CommunicationIntent(
        organization_id=8,
        intent_key="campaign-attempt",
        channel_type=ChannelType.WHATSAPP,
        purpose=CommunicationPurpose.MARKETING,
        origin=CommunicationOrigin.CAMPAIGN,
        required_capabilities=frozenset({Capability.BULK}),
        bulk=True,
    )
    policy = CommunicationPolicy(
        policy_key="restricted",
        organization_id=9,
        allowed_purposes=frozenset({CommunicationPurpose.SERVICE}),
        allowed_origins=frozenset({CommunicationOrigin.MANUAL}),
        allow_bulk=False,
    )

    result = evaluate_communication_policy(intent, policy, {Capability.BULK})

    assert result.allowed is False
    assert result.reasons == (
        "organization_scope_mismatch",
        "purpose_not_allowed",
        "origin_not_allowed",
        "bulk_not_allowed",
    )


def test_health_and_lifecycle_contracts_require_factual_aware_state() -> None:
    now = datetime.now(UTC)
    health = ProviderHealth(
        connector_type="generic_provider",
        state=ProviderHealthState.HEALTHY,
        observed_at=now,
        score=100,
    )
    lifecycle = ProviderLifecycle(
        connector_type="generic_provider",
        desired_state=ProviderDesiredState.ENABLED,
        observed_state=ProviderObservedState.READY,
        observed_at=now,
    )

    assert health.score == 100
    assert lifecycle.observed_state is ProviderObservedState.READY
    with pytest.raises(ChannelConfigError):
        ProviderHealth(
            connector_type="generic_provider",
            state=ProviderHealthState.HEALTHY,
            observed_at=now,
            score=101,
        )
    with pytest.raises(ChannelConfigError):
        ProviderLifecycle(
            connector_type="generic_provider",
            desired_state=ProviderDesiredState.ENABLED,
            observed_state=ProviderObservedState.READY,
            observed_at=datetime.now(),
        )


@pytest.mark.asyncio
async def test_feature_flags_use_existing_global_and_organization_authority(
    db_session, organization
) -> None:
    db_session.add_all(
        [
            FeatureFlag(
                key_name=OmnichannelFeatureFlag.CONNECTIONS_READ.value,
                is_enabled=True,
                organization_id=None,
            ),
            FeatureFlag(
                key_name=OmnichannelFeatureFlag.CONNECTIONS_WRITE.value,
                is_enabled=True,
                organization_id=None,
            ),
            FeatureFlag(
                key_name=OmnichannelFeatureFlag.CONNECTIONS_WRITE.value,
                is_enabled=False,
                organization_id=organization.id,
            ),
        ]
    )
    await db_session.commit()

    snapshot = await ChannelFeatureFlagResolver(db_session).resolve(organization.id)

    assert snapshot.is_enabled(OmnichannelFeatureFlag.CONNECTIONS_READ)
    assert not snapshot.is_enabled(OmnichannelFeatureFlag.CONNECTIONS_WRITE)


def test_dependency_container_is_stable_and_provider_empty_by_default(monkeypatch) -> None:
    from app.core.config import settings

    # Keep the default-contract test hermetic even when the host running pytest has deliberately
    # configured a live WAHA development runtime in its ignored local `.env`.
    monkeypatch.setattr(settings, "waha_base_url", "")
    monkeypatch.setattr(settings, "waha_api_key", "")
    monkeypatch.setattr(settings, "waha_session_name", "")
    get_channel_foundation.cache_clear()
    first = get_channel_foundation()
    second = get_channel_foundation()

    assert first is second
    assert first.providers.available() == ()
    assert first.capabilities.available() == ()
    assert first.runtimes.available() == ()
    get_channel_foundation.cache_clear()
