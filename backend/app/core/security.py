"""Security primitives — password hashing, JWTs, token hashing, IP packing.

Pure, side-effect-free cryptographic helpers (Doc 01 §5.4, Doc 04 §4). No database or
request state here — services compose these. Raw secrets (passwords, refresh tokens) are
never logged or persisted; only Argon2id / SHA-256 digests leave this module.

- **Passwords:** Argon2id via ``argon2-cffi`` (FR-AUTH-01), tuned from settings.
- **Access tokens:** short-lived HS256 JWTs carrying ``sub``/``jti``/``type``/``perms_hash``
  (Doc 04 §4.1).
- **Refresh tokens:** opaque high-entropy strings; only their SHA-256 hash is stored
  (Doc 03 §4.4), with ``jti`` naming the rotation family.
"""

from __future__ import annotations

import hashlib
import ipaddress
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2 import exceptions as argon2_exceptions

from app.core.config import settings

TOKEN_TYPE_ACCESS = "access"
_REFRESH_TOKEN_BYTES = 48  # 384 bits of entropy for the opaque refresh secret

_HAS_LETTER = re.compile(r"[A-Za-z]")
_HAS_DIGIT = re.compile(r"\d")


def validate_password_policy(password: str) -> None:
    """Enforce the password policy (Doc 01 FR-AUTH-04). Raises ``ValueError`` on violation.

    Single source of truth shared by the API schema and the bootstrap CLI.
    """
    if len(password) < settings.password_min_length:
        raise ValueError(
            f"Password must be at least {settings.password_min_length} characters."
        )
    if not _HAS_LETTER.search(password) or not _HAS_DIGIT.search(password):
        raise ValueError("Password must contain at least one letter and one digit.")

# Process-wide Argon2id hasher, parameterised from settings (Doc 01 §5.4).
_password_hasher = PasswordHasher(
    time_cost=settings.argon2_time_cost,
    memory_cost=settings.argon2_memory_cost,
    parallelism=settings.argon2_parallelism,
)


# --- Passwords --------------------------------------------------------------
def hash_password(password: str) -> str:
    """Return an Argon2id encoded hash for ``password``."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return True iff ``password`` matches ``password_hash`` (constant-time, no raise)."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (
        argon2_exceptions.VerifyMismatchError,
        argon2_exceptions.VerificationError,
        argon2_exceptions.InvalidHashError,
    ):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """True if the hash was made with weaker parameters and should be upgraded on next login."""
    try:
        return _password_hasher.check_needs_rehash(password_hash)
    except argon2_exceptions.InvalidHashError:
        return True


# --- Access tokens (JWT) ----------------------------------------------------
@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    """Decoded, verified access-token claims."""

    subject: str
    jti: str
    permissions_hash: str
    issued_at: datetime
    expires_at: datetime


def permissions_hash(codes: frozenset[str] | set[str]) -> str:
    """Stable short digest of an effective permission set (Doc 04 §4.1 permissions hash)."""
    joined = ",".join(sorted(codes))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def create_access_token(
    *, subject: str, jti: str, perms_hash: str, now: datetime | None = None
) -> tuple[str, int]:
    """Encode a signed access JWT. Returns ``(token, expires_in_seconds)`` (Doc 04 §4.1)."""
    issued = now or datetime.now(UTC)
    expires = issued + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "jti": jti,
        "type": TOKEN_TYPE_ACCESS,
        "perms_hash": perms_hash,
        "iat": int(issued.timestamp()),
        "nbf": int(issued.timestamp()),
        "exp": int(expires.timestamp()),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, int(settings.access_token_expire_minutes * 60)


def decode_access_token(token: str) -> AccessTokenClaims:
    """Verify signature/expiry/type and return claims. Raises ``jwt.InvalidTokenError`` on failure."""
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "iat", "sub", "jti"]},
    )
    if payload.get("type") != TOKEN_TYPE_ACCESS:
        raise jwt.InvalidTokenError("wrong token type")
    return AccessTokenClaims(
        subject=str(payload["sub"]),
        jti=str(payload["jti"]),
        permissions_hash=str(payload.get("perms_hash", "")),
        issued_at=datetime.fromtimestamp(int(payload["iat"]), tz=UTC),
        expires_at=datetime.fromtimestamp(int(payload["exp"]), tz=UTC),
    )


# --- Refresh tokens (opaque) ------------------------------------------------
def generate_refresh_token() -> str:
    """Return a fresh high-entropy opaque refresh token (never stored raw)."""
    return secrets.token_urlsafe(_REFRESH_TOKEN_BYTES)


def hash_token(token: str) -> str:
    """SHA-256 hex digest of a token — the only form persisted (Doc 03 §4.4)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_jti() -> str:
    """A new token-family identifier (Doc 03 §4.4 ``refresh_tokens.jti``)."""
    return str(uuid.uuid4())


# --- IP address packing (Doc 03 §4.4 — VARBINARY(16)) -----------------------
def pack_ip(ip: str | None) -> bytes | None:
    """Pack an IPv4/IPv6 string into its network-order bytes, or None if absent/invalid."""
    if not ip:
        return None
    try:
        return ipaddress.ip_address(ip).packed
    except ValueError:
        return None


def unpack_ip(packed: bytes | None) -> str | None:
    """Render packed IP bytes back to a string, or None."""
    if not packed:
        return None
    try:
        return str(ipaddress.ip_address(packed))
    except ValueError:
        return None
