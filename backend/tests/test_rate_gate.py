"""Tier-aware sending tests (Doc 06 §5; FR-WA-13).

The pacing policy and the token bucket are pure and tested directly. The Redis path is exercised
through the D11 fallback — which is the same :class:`TokenBucket`, and real production code — so
every decision the gate makes is covered without a live Redis. The Lua script's own execution is
the one thing that needs a real server; it mirrors ``TokenBucket`` deliberately.
"""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.models.waba import PhoneNumber
from app.services.rate_gate import (
    DEFAULT_TIER_CAP,
    REASON_MPS,
    REASON_QUALITY,
    REASON_TIER,
    RateGate,
    TokenBucket,
    effective_mps,
    is_paused,
    quality_pacing,
    reset_local_buckets,
    tier_cap,
)
from tests.test_api_conversations import _rows
from tests.test_api_messages import _accepted


@pytest.fixture(autouse=True)
def _gate_on(monkeypatch):
    """The suite disables the gate; this is the test that is about it."""
    monkeypatch.setattr(settings, "rate_gate_enabled", True)
    reset_local_buckets()
    yield
    reset_local_buckets()


def _number(**overrides) -> PhoneNumber:
    number = PhoneNumber(
        organization_id=1,
        waba_id=1,
        phone_number_id="pn-1",
        display_number="+14155550001",
        mps_limit=80,
        quality_rating="GREEN",
        messaging_tier="TIER_100K",
    )
    for key, value in overrides.items():
        setattr(number, key, value)
    number.id = 1
    return number


# --- The constraints (Doc 06 §5.2) -------------------------------------------
def test_tier_maps_to_a_24h_unique_recipient_cap() -> None:
    assert tier_cap(_number(messaging_tier="TIER_1K")) == 1_000
    assert tier_cap(_number(messaging_tier="TIER_100K")) == 100_000
    assert tier_cap(_number(messaging_tier="TIER_UNLIMITED")) is None


def test_an_unknown_tier_is_treated_as_the_smallest_never_unlimited() -> None:
    """Guessing high here would blow a real cap; guessing low only paces (§5.1)."""
    assert tier_cap(_number(messaging_tier=None)) == DEFAULT_TIER_CAP
    assert tier_cap(_number(messaging_tier="TIER_MARS")) == DEFAULT_TIER_CAP


def test_quality_paces_the_rate_down_never_up() -> None:
    assert quality_pacing(_number(quality_rating="GREEN")) == 1.0
    assert quality_pacing(_number(quality_rating="YELLOW")) == 0.5
    assert quality_pacing(_number(quality_rating="RED")) == 0.25
    # An unreported rating is not a reason to slow down.
    assert quality_pacing(_number(quality_rating=None)) == 1.0

    assert effective_mps(_number(mps_limit=80, quality_rating="GREEN")) == 80
    assert effective_mps(_number(mps_limit=80, quality_rating="YELLOW")) == 40
    # Never zero: a degraded number still sends, just slowly.
    assert effective_mps(_number(mps_limit=0, quality_rating="RED")) > 0


def test_red_pauses_marketing_but_not_service_traffic() -> None:
    """§5.4: the asset is protected from marketing, not from answering a customer."""
    red = _number(quality_rating="RED")
    assert is_paused(red, "marketing") is True
    assert is_paused(red, "utility") is False
    assert is_paused(red, None) is False
    assert is_paused(_number(quality_rating="YELLOW"), "marketing") is False


# --- The token bucket --------------------------------------------------------
def test_bucket_starts_full_then_refills_at_its_rate() -> None:
    bucket = TokenBucket(rate=10.0, capacity=10.0)
    # An idle number may send at once rather than waiting for a first refill.
    for _ in range(10):
        assert bucket.consume(now=1000.0)[0] is True

    allowed, retry_after = bucket.consume(now=1000.0)
    assert allowed is False
    assert retry_after == pytest.approx(0.1)

    # A tenth of a second buys exactly one token back.
    assert bucket.consume(now=1000.1)[0] is True
    assert bucket.consume(now=1000.1)[0] is False


def test_a_bucket_first_used_at_time_zero_still_paces() -> None:
    """`0.0` is a timestamp, not "never used" — conflating them refills on every call."""
    bucket = TokenBucket(rate=1.0, capacity=2.0)
    assert [bucket.consume(now=0.0)[0] for _ in range(4)] == [True, True, False, False]


def test_bucket_never_banks_more_than_its_capacity() -> None:
    """An hour of idleness must not become an hour's worth of burst at Meta."""
    bucket = TokenBucket(rate=10.0, capacity=10.0)
    bucket.consume(now=0.0)
    allowed = [bucket.consume(now=3600.0)[0] for _ in range(20)]
    assert allowed.count(True) == 10


def test_bucket_enforces_the_rate_over_time() -> None:
    bucket = TokenBucket(rate=5.0, capacity=5.0)
    granted = 0
    for tick in range(100):  # ten seconds at 10 attempts/second
        if bucket.consume(now=tick / 10)[0]:
            granted += 1
    # 5 to start (full bucket) + ~5/second for ~10s.
    assert 50 <= granted <= 55


# --- The gate (Doc 06 §5.3) --------------------------------------------------
async def test_a_red_number_refuses_marketing_terminally(monkeypatch) -> None:
    decision = await RateGate().acquire(
        _number(quality_rating="RED"), recipient="919990329329", category="marketing"
    )
    assert decision.allowed is False and decision.reason == REASON_QUALITY
    # Waiting cannot fix a quality rating, so this must not be retried.
    assert decision.terminal is True


async def test_the_gate_can_be_turned_off(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_gate_enabled", False)
    assert (await RateGate().acquire(_number(), recipient="1")).allowed is True


class _DeadRedis:
    async def eval(self, *args, **kwargs):
        raise ConnectionError("redis is down")


async def test_redis_loss_degrades_to_conservative_pacing_never_a_flood(monkeypatch) -> None:
    """D11: the gate fails safe, and safe means slower — not open, and not stopped."""
    monkeypatch.setattr(settings, "rate_gate_fallback_fraction", 0.25)
    gate = RateGate(_DeadRedis())
    number = _number(mps_limit=8)  # → a local share of 2/second

    granted = [
        (await gate.acquire(number, recipient=f"contact-{i}")).allowed for i in range(20)
    ]
    # It kept sending …
    assert True in granted
    # … but nowhere near the 20 an open gate would have allowed.
    assert granted.count(True) <= 4
    refused = await gate.acquire(number, recipient="contact-x")
    assert refused.allowed is False and refused.reason == REASON_MPS
    assert refused.retry_after > 0


async def test_the_fallback_paces_per_number(monkeypatch) -> None:
    gate = RateGate(_DeadRedis())
    first, second = _number(mps_limit=4), _number(mps_limit=4)
    second.id = 2

    await gate.acquire(first, recipient="a")
    # Numbers are independent lanes (§5.3): exhausting one must not stall the other.
    assert (await gate.acquire(second, recipient="a")).allowed is True


async def test_the_shared_gate_reads_the_scripts_verdict() -> None:
    """The script answers `{allowed, reason, wait}`; the gate must not reinterpret it."""

    class _Redis:
        def __init__(self, reply) -> None:
            self.reply = reply
            self.calls: list = []

        async def eval(self, script, numkeys, *args):
            self.calls.append(args)
            return self.reply

    allowed = _Redis([1, b"ok", b"0"])
    assert (await RateGate(allowed).acquire(_number(), recipient="919990329329")).allowed is True
    # The number's keys, its paced rate, its cap and the recipient all reach the script.
    args = allowed.calls[0]
    assert args[0] == "rl:number:1:tokens" and args[1] == "rl:number:1:recipients"
    assert float(args[3]) == 80.0 and int(args[5]) == 100_000
    assert args[6] == "919990329329"

    capped = await RateGate(_Redis([0, b"tier_cap", b"3600.5"])).acquire(
        _number(), recipient="919990329329"
    )
    assert capped.allowed is False and capped.reason == REASON_TIER
    # Holding at the cap is a wait, not a failure (§5.4).
    assert capped.retry_after == pytest.approx(3600.5) and capped.terminal is False

    throttled = await RateGate(_Redis([0, b"mps", b"0.0125"])).acquire(_number(), recipient="x")
    assert throttled.allowed is False and throttled.reason == REASON_MPS


async def test_an_unlimited_tier_tells_the_script_not_to_count() -> None:
    class _Redis:
        def __init__(self) -> None:
            self.calls: list = []

        async def eval(self, script, numkeys, *args):
            self.calls.append(args)
            return [1, b"ok", b"0"]

    redis = _Redis()
    await RateGate(redis).acquire(_number(messaging_tier="TIER_UNLIMITED"), recipient="x")
    assert int(redis.calls[0][5]) == -1


async def test_a_yellow_number_is_paced_at_half_rate() -> None:
    class _Redis:
        def __init__(self) -> None:
            self.calls: list = []

        async def eval(self, script, numkeys, *args):
            self.calls.append(args)
            return [1, b"ok", b"0"]

    redis = _Redis()
    await RateGate(redis).acquire(_number(quality_rating="YELLOW", mps_limit=80), recipient="x")
    assert float(redis.calls[0][3]) == 40.0


# --- The send path (Doc 06 §5.3/§6.2) ----------------------------------------
def test_throttling_is_classified_as_a_wait_not_a_failure() -> None:
    """A number at its ceiling is not a broken send: the engine backs off and re-queues (§6.2)."""
    from app.queue.retry import FailureClass, classify, should_retry
    from app.services.send_service import SendThrottled

    throttled = SendThrottled("at mps", reason=REASON_MPS, retry_after=0.0125)
    assert classify(throttled) is FailureClass.THROTTLE
    # THROTTLE keeps trying — far longer than a terminal class would.
    assert should_retry(FailureClass.THROTTLE, attempt=5) is True


async def test_no_budget_throttles_the_send_instead_of_calling_meta(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent
) -> None:
    from app.models.message import MSG_ACCEPTED, Message
    from app.services import send_service
    from app.services.rate_gate import Decision
    from app.services.send_service import SendService, SendThrottled

    message = await _accepted(client, make_user, session_factory, monkeypatch)

    async def _no_budget(self, number, *, recipient, category=None):
        return Decision(allowed=False, reason=REASON_MPS, retry_after=0.5)

    monkeypatch.setattr(send_service.RateGate, "acquire", _no_budget)
    async with session_factory() as session:
        with pytest.raises(SendThrottled):
            await SendService(session).deliver(message.id)

    stored = [m for m in await _rows(session_factory, Message) if m.direction == "outbound"][0]
    # The gate stops the call rather than measuring it after the fact: a message that reached Meta
    # would carry a wamid. Nothing is spent and nothing is lost — it waits its turn.
    assert stored.status == MSG_ACCEPTED and stored.wamid is None


async def test_a_paused_number_fails_the_message_rather_than_retrying_forever(
    client, make_user, session_factory, monkeypatch, dispatched, idem, sent
) -> None:
    """RED + marketing is terminal: no amount of backoff improves a quality rating (§5.4)."""
    from app.models.message import MSG_FAILED, Message
    from app.services import send_service
    from app.services.rate_gate import Decision
    from app.services.send_service import SendService

    message = await _accepted(client, make_user, session_factory, monkeypatch)

    async def _paused(self, number, *, recipient, category=None):
        return Decision(allowed=False, reason=REASON_QUALITY, terminal=True)

    monkeypatch.setattr(send_service.RateGate, "acquire", _paused)
    async with session_factory() as session:
        result = await SendService(session).deliver(message.id)

    assert result["status"] == MSG_FAILED
    stored = [m for m in await _rows(session_factory, Message) if m.direction == "outbound"][0]
    assert stored.status == MSG_FAILED and stored.error_code == REASON_QUALITY
    # Never handed to the channel: no wamid was ever issued for it.
    assert stored.wamid is None
