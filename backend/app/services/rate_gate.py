"""Tier-aware sending — the per-number rate gate (Doc 06 §5) — FR-WA-13.

Throughput is a **managed resource, not a free-for-all** (§5.1): exceeding a number's limits or
sending while quality is poor costs throttling, then quality drops, then the number itself. So
every send acquires budget here before Meta is called, and the fleet honours one number's limit no
matter how many workers are pushing it (decision D10).

Three constraints, one decision (§5.2/§5.3):

- **MPS** — a distributed token bucket per number, refilling at ``mps_limit`` tokens/second.
- **Tier** — unique customers per rolling 24h. Unique is the operative word: messaging the same
  customer twice costs one, which is why this is a rolling set of recipients rather than a counter.
- **Quality** — GREEN/YELLOW/RED paces the bucket down, and RED stops marketing outright (§5.4).

**Atomicity.** The whole decision is one Lua script, so the tier check and the token spend cannot
race each other or another worker — a cap that two workers can both pass is not a cap. It is also
the "one Redis round-trip per send" §5.6 budgets for.

**Failure (D11).** If Redis is unreachable the gate does **not** open: it falls back to a
process-local bucket at a fraction of the limit, so a fleet of *N* workers still paces at
*N × fraction × mps* rather than blasting Meta. Conservative pacing beats both a stall and a flood.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.models.waba import PhoneNumber

logger = get_logger(__name__)

#: Doc 06 §12.2's rate-limiter namespace, per number.
BUCKET_KEY = "rl:number:{id}:tokens"
TIER_KEY = "rl:number:{id}:recipients"

#: Meta's messaging tiers → unique customers per rolling 24h (§5.2; Doc 04 §13.3's
#: `unique_customers_24h_cap`). ``None`` is unlimited.
TIER_CAPS: dict[str, int | None] = {
    "TIER_50": 50,
    "TIER_250": 250,
    "TIER_1K": 1_000,
    "TIER_10K": 10_000,
    "TIER_100K": 100_000,
    "TIER_UNLIMITED": None,
}
#: An unknown or unreported tier is treated as the smallest — never as unlimited (§5.1).
DEFAULT_TIER_CAP = 1_000

#: Quality-derived pacing (§5.3 "adaptive pacing", §5.4 "on YELLOW, pacing is automatically
#: reduced"). A degraded number is sent to more slowly, not more loudly.
QUALITY_PACING: dict[str, float] = {"GREEN": 1.0, "YELLOW": 0.5, "RED": 0.25}
DEFAULT_PACING = 1.0

#: The rolling window the tier cap is measured over (§5.2).
TIER_WINDOW_SECONDS = 24 * 60 * 60

#: Categories Meta prices as marketing — the traffic RED pauses (§5.4; Doc 01 CMP-06).
MARKETING = "marketing"

# Reasons a send was refused budget.
REASON_OK = "ok"
REASON_MPS = "mps"
REASON_TIER = "tier_cap"
REASON_QUALITY = "quality_paused"


@dataclass(frozen=True, slots=True)
class Decision:
    """What the gate said, and when to come back if it said no."""

    allowed: bool
    reason: str = REASON_OK
    #: Seconds until budget is expected to exist. Advisory: the retry engine owns the actual
    #: backoff curve (Doc 06 §6.3), so this is for logging and diagnosis.
    retry_after: float = 0.0
    #: True when no amount of waiting helps — the number is RED and this is marketing (§5.4).
    terminal: bool = False


def tier_cap(number: PhoneNumber) -> int | None:
    """Unique recipients this number may reach per rolling 24h (§5.2)."""
    if not number.messaging_tier:
        return DEFAULT_TIER_CAP
    return TIER_CAPS.get(number.messaging_tier.upper(), DEFAULT_TIER_CAP)


def quality_pacing(number: PhoneNumber) -> float:
    return QUALITY_PACING.get((number.quality_rating or "").upper(), DEFAULT_PACING)


def effective_mps(number: PhoneNumber) -> float:
    """``min(mps_limit, quality-derived pacing)`` — the rate this number may be sent at (§5.3).

    The tier's share of the rate is not folded in here: the tier is a *budget*, not a rate, and the
    gate holds at the cap rather than smearing sends thinner and thinner as it approaches one.
    """
    return max(0.1, float(number.mps_limit or 1) * quality_pacing(number))


def is_paused(number: PhoneNumber, category: str | None) -> bool:
    """RED pauses marketing on this number; utility/service traffic keeps flowing (§5.4)."""
    return (number.quality_rating or "").upper() == "RED" and category == MARKETING


@dataclass
class TokenBucket:
    """A token bucket, in one place, in Python.

    Also the D11 fallback: when Redis is unreachable this *is* the gate, per process, which is why
    it is real code rather than a description of the Lua script.
    """

    rate: float
    capacity: float
    tokens: float = 0.0
    #: ``None`` means never used. Not ``0.0``: that is a real timestamp, and conflating the two
    #: would refill the bucket on every call for any clock that starts at zero.
    updated_at: float | None = None

    def consume(self, now: float, *, cost: float = 1.0) -> tuple[bool, float]:
        """Take one token. Returns ``(allowed, retry_after_seconds)``."""
        if self.updated_at is None:
            # A fresh bucket starts full: a number that has been idle may send at once.
            self.tokens, self.updated_at = self.capacity, now
        elapsed = max(0.0, now - self.updated_at)
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.updated_at = now
        if self.tokens >= cost:
            self.tokens -= cost
            return True, 0.0
        return False, (cost - self.tokens) / self.rate


#: One decision, atomically: expire the rolling window, check the cap, then spend a token. Split
#: across round-trips these would race — two workers could both read "cap not reached" and both
#: send. Mirrors :class:`TokenBucket`; keep the two in step.
GATE_SCRIPT = """
local bucket_key, tier_key = KEYS[1], KEYS[2]
local now = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local capacity = tonumber(ARGV[3])
local cap = tonumber(ARGV[4])
local recipient = ARGV[5]
local window = tonumber(ARGV[6])

-- Tier: a rolling window of unique recipients. Re-messaging someone already inside it is free.
local counted = 1
if cap >= 0 then
  redis.call('ZREMRANGEBYSCORE', tier_key, '-inf', now - window)
  if redis.call('ZSCORE', tier_key, recipient) == false then
    if redis.call('ZCARD', tier_key) >= cap then
      local oldest = redis.call('ZRANGE', tier_key, 0, 0, 'WITHSCORES')
      local wait = window
      if oldest[2] then wait = (tonumber(oldest[2]) + window) - now end
      return {0, 'tier_cap', tostring(math.max(wait, 0))}
    end
  else
    counted = 0
  end
end

-- MPS: refill, then spend.
local state = redis.call('HMGET', bucket_key, 'tokens', 'updated_at')
local tokens = tonumber(state[1])
local updated_at = tonumber(state[2])
if tokens == nil or updated_at == nil then
  tokens, updated_at = capacity, now
end
local elapsed = math.max(0, now - updated_at)
tokens = math.min(capacity, tokens + elapsed * rate)
if tokens < 1 then
  redis.call('HSET', bucket_key, 'tokens', tokens, 'updated_at', now)
  redis.call('EXPIRE', bucket_key, 60)
  return {0, 'mps', tostring((1 - tokens) / rate)}
end
redis.call('HSET', bucket_key, 'tokens', tokens - 1, 'updated_at', now)
redis.call('EXPIRE', bucket_key, 60)

if cap >= 0 and counted == 1 then
  redis.call('ZADD', tier_key, now, recipient)
  redis.call('EXPIRE', tier_key, window + 60)
end
return {1, 'ok', '0'}
"""

#: Process-local buckets for the D11 fallback, one per number.
_LOCAL: dict[int, TokenBucket] = {}


def reset_local_buckets() -> None:
    """Drop the fallback state (test/support helper)."""
    _LOCAL.clear()


class RateGate:
    """The gate every send passes through before Meta is called (§5.3)."""

    def __init__(self, redis: Any | None = None) -> None:
        self._redis = redis

    async def acquire(
        self, number: PhoneNumber, *, recipient: str, category: str | None = None
    ) -> Decision:
        """Take budget for one send to ``recipient`` from ``number``."""
        if is_paused(number, category):
            # Not a wait: marketing stays stopped until the number's quality recovers (§5.4).
            logger.error(
                "number_quality_paused",
                extra={"number": number.id, "quality": number.quality_rating},
            )
            return Decision(allowed=False, reason=REASON_QUALITY, terminal=True)
        if not settings.rate_gate_enabled:
            return Decision(allowed=True)

        rate = effective_mps(number)
        cap = tier_cap(number)
        try:
            return await self._acquire_shared(number, rate=rate, cap=cap, recipient=recipient)
        except Exception as exc:  # noqa: BLE001 - D11: degrade, never open
            logger.warning(
                "rate_gate_degraded",
                extra={"number": number.id, "error": type(exc).__name__},
            )
            return self._acquire_local(number, rate=rate)

    async def _acquire_shared(
        self, number: PhoneNumber, *, rate: float, cap: int | None, recipient: str
    ) -> Decision:
        from app.core.redis import get_redis_client

        redis = self._redis or get_redis_client()
        raw = await redis.eval(
            GATE_SCRIPT,
            2,
            BUCKET_KEY.format(id=number.id),
            TIER_KEY.format(id=number.id),
            str(time.time()),
            str(rate),
            # Capacity is one second of sending: the bucket absorbs jitter, not a backlog.
            str(max(1.0, rate)),
            str(-1 if cap is None else cap),
            recipient,
            str(TIER_WINDOW_SECONDS),
        )
        return self._decision(raw)

    @staticmethod
    def _decision(raw: Any) -> Decision:
        allowed, reason, wait = raw[0], _text(raw[1]), _text(raw[2])
        if int(allowed) == 1:
            return Decision(allowed=True)
        return Decision(allowed=False, reason=reason, retry_after=max(0.0, float(wait)))

    def _acquire_local(self, number: PhoneNumber, *, rate: float) -> Decision:
        """Fleet-blind fallback pacing (D11).

        Deliberately a fraction of the real limit: every worker is now pacing independently, so the
        only way the *sum* stays under the number's ceiling is for each to aim well below it. The
        tier cap is not enforced here — it cannot be, without shared state — which is the honest
        cost of Redis being down, and why this path logs.
        """
        share = max(0.1, rate * settings.rate_gate_fallback_fraction)
        bucket = _LOCAL.setdefault(number.id, TokenBucket(rate=share, capacity=max(1.0, share)))
        bucket.rate, bucket.capacity = share, max(1.0, share)
        allowed, retry_after = bucket.consume(time.time())
        if allowed:
            return Decision(allowed=True)
        return Decision(allowed=False, reason=REASON_MPS, retry_after=math.ceil(retry_after * 100) / 100)


def _text(value: Any) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)
