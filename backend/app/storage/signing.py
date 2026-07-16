"""Signed URL framework (FR-MED-09, Doc 08 §14).

Media is served **only** via signed, expiring URLs — no public bucket, no unauthenticated
object reads. A signature binds the media id to an expiry with an HMAC over the application
secret, so a leaked URL stops working on its own and cannot be edited to point elsewhere.

Verification is constant-time and distinguishes *expired* (410, per Doc 04 §16) from *invalid*
(403), because those mean different things to a caller.
"""

from __future__ import annotations

import hashlib
import hmac
import time

from app.core.config import settings


class SignatureExpired(Exception):
    """The URL was valid but its expiry has passed (→ 410 Gone)."""


class SignatureInvalid(Exception):
    """The signature does not match (tampered/forged) (→ 403 Forbidden)."""


def _payload(media_id: str, expires_at: int) -> bytes:
    return f"{media_id}:{expires_at}".encode()


def sign(media_id: str, expires_at: int) -> str:
    """HMAC-SHA256 signature binding ``media_id`` to ``expires_at``."""
    return hmac.new(
        settings.secret_key.encode("utf-8"), _payload(media_id, expires_at), hashlib.sha256
    ).hexdigest()


def issue(media_id: str, *, expires_in: int | None = None, now: int | None = None) -> tuple[int, str]:
    """Return ``(expires_at, signature)`` for a new signed URL."""
    ttl = expires_in if expires_in is not None else settings.storage_signed_url_ttl_seconds
    expires_at = int(now if now is not None else time.time()) + ttl
    return expires_at, sign(media_id, expires_at)


def verify(media_id: str, expires_at: int, signature: str, *, now: int | None = None) -> None:
    """Validate a signature; raises :class:`SignatureInvalid` / :class:`SignatureExpired`."""
    if not hmac.compare_digest(sign(media_id, expires_at), signature):
        raise SignatureInvalid("bad signature")
    if int(now if now is not None else time.time()) > expires_at:
        raise SignatureExpired("url expired")
