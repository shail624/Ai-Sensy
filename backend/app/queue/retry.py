"""Smart retry framework (Doc 06 §6).

Core rule: **retry only what can succeed on retry, back off politely, cap attempts, and
terminate everything else cleanly.** Failures are mapped to a *class*; each class carries its
own strategy, attempt cap and backoff curve. Backoff is exponential with **full jitter** so a
recovering dependency is not hit by a synchronized retry storm (§6.3).

This module is the generic engine. Channel-specific error maps (e.g. Meta error codes) are
registered by their own modules via :func:`register_error_map` — the engine never hard-codes a
provider's codes (§6.6 "new channels register their own error maps into the same engine").
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum


class FailureClass(StrEnum):
    """Failure taxonomy (Doc 06 §6.2)."""

    THROTTLE = "throttle"
    TRANSIENT = "transient"
    TRANSIENT_META = "transient_meta"
    TRANSIENT_MEDIA = "transient_media"
    TRANSIENT_PROC = "transient_proc"
    TERMINAL = "terminal"
    TERMINAL_DATA = "terminal_data"
    TERMINAL_POLICY = "terminal_policy"
    TERMINAL_CONFIG = "terminal_config"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Per-class strategy (Doc 06 §6.2/§6.3)."""

    max_attempts: int
    base_seconds: float
    cap_seconds: float

    @property
    def retryable(self) -> bool:
        return self.max_attempts > 0


#: Per-class policy. Terminal classes never retry; throttle backs off gently and keeps trying.
POLICIES: dict[FailureClass, RetryPolicy] = {
    FailureClass.THROTTLE: RetryPolicy(max_attempts=10, base_seconds=2.0, cap_seconds=300.0),
    FailureClass.TRANSIENT: RetryPolicy(max_attempts=5, base_seconds=1.0, cap_seconds=120.0),
    FailureClass.TRANSIENT_META: RetryPolicy(max_attempts=4, base_seconds=5.0, cap_seconds=300.0),
    FailureClass.TRANSIENT_MEDIA: RetryPolicy(max_attempts=3, base_seconds=2.0, cap_seconds=60.0),
    FailureClass.TRANSIENT_PROC: RetryPolicy(max_attempts=5, base_seconds=1.0, cap_seconds=120.0),
    FailureClass.TERMINAL: RetryPolicy(max_attempts=0, base_seconds=0.0, cap_seconds=0.0),
    FailureClass.TERMINAL_DATA: RetryPolicy(max_attempts=0, base_seconds=0.0, cap_seconds=0.0),
    FailureClass.TERMINAL_POLICY: RetryPolicy(max_attempts=0, base_seconds=0.0, cap_seconds=0.0),
    FailureClass.TERMINAL_CONFIG: RetryPolicy(max_attempts=0, base_seconds=0.0, cap_seconds=0.0),
    # Unclassifiable → treat as poison: do not retry blindly, send to the DLQ for a human (§7.2).
    FailureClass.UNKNOWN: RetryPolicy(max_attempts=0, base_seconds=0.0, cap_seconds=0.0),
}

#: Classifiers registered by channel/domain modules (name → callable).
_ERROR_MAPS: dict[str, Callable[[BaseException], FailureClass | None]] = {}


def register_error_map(
    name: str, classifier: Callable[[BaseException], FailureClass | None]
) -> None:
    """Register a domain/channel error map (Doc 06 §6.6, decision D12)."""
    _ERROR_MAPS[name] = classifier


def clear_error_maps() -> None:
    """Remove all registered classifiers (test/support helper)."""
    _ERROR_MAPS.clear()


def classify(exc: BaseException) -> FailureClass:
    """Classify a failure, consulting registered error maps first (Doc 06 §6.2)."""
    for classifier in _ERROR_MAPS.values():
        result = classifier(exc)
        if result is not None:
            return result
    if isinstance(exc, TimeoutError | ConnectionError):
        return FailureClass.TRANSIENT
    return FailureClass.UNKNOWN


def policy_for(failure_class: FailureClass) -> RetryPolicy:
    return POLICIES[failure_class]


def should_retry(failure_class: FailureClass, attempt: int) -> bool:
    """True if another attempt is allowed. ``attempt`` is the count already made (1-based)."""
    return attempt < policy_for(failure_class).max_attempts


def backoff_seconds(
    failure_class: FailureClass, attempt: int, *, rng: random.Random | None = None
) -> float:
    """Exponential backoff with **full jitter**, capped per class (Doc 06 §6.3).

    Returns a delay in ``[0, min(cap, base * 2**attempt)]`` — full jitter (rather than a fixed
    curve) is what actually de-synchronizes a fleet of retrying workers.
    """
    policy = policy_for(failure_class)
    if not policy.retryable:
        return 0.0
    ceiling = min(policy.cap_seconds, policy.base_seconds * (2**max(0, attempt)))
    return (rng or random).uniform(0.0, ceiling)
