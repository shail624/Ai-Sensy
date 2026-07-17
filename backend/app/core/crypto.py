"""Application-side encryption for secrets stored at rest (FR-WA-03, Doc 03 §5.1).

Doc 03 stores channel credentials in ``VARBINARY`` columns as **app-side AES-GCM** ciphertext, so a
database dump (or a backup, or a replica) never yields a usable token. AES-GCM is authenticated:
tampering with the stored bytes fails decryption rather than silently returning altered plaintext.

Wire format: ``version(1) || nonce(12) || ciphertext+tag``. The version byte exists so the key or
algorithm can be rotated later without guessing at what old rows contain.

Key: ``TOKEN_ENCRYPTION_KEY``, 32 bytes, base64url — environment only (Doc 01 §5.4). Outside
production a key is derived from ``SECRET_KEY`` so development and the hermetic suite need no extra
setup; **in production a real key is required** and its absence is a startup-time failure rather
than a silent downgrade.
"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

_VERSION = b"\x01"
_NONCE_BYTES = 12
_KEY_BYTES = 32


class EncryptionError(RuntimeError):
    """The value could not be encrypted or decrypted (bad key, tampered or corrupt data)."""


def _key() -> bytes:
    """Resolve the data-encryption key, or fail loudly."""
    configured = settings.token_encryption_key
    if configured:
        try:
            raw = base64.urlsafe_b64decode(configured)
        except (ValueError, TypeError) as exc:
            raise EncryptionError("TOKEN_ENCRYPTION_KEY is not valid base64url.") from exc
        if len(raw) != _KEY_BYTES:
            raise EncryptionError(
                f"TOKEN_ENCRYPTION_KEY must decode to {_KEY_BYTES} bytes, got {len(raw)}."
            )
        return raw
    if settings.is_production:
        raise EncryptionError(
            "TOKEN_ENCRYPTION_KEY must be set in production; refusing to derive a key."
        )
    # Development/test only: deterministic, so an encrypted row survives a restart.
    return hashlib.sha256(settings.secret_key.encode("utf-8")).digest()


def encrypt(plaintext: str) -> bytes:
    """Encrypt a secret for storage in a ``VARBINARY`` column."""
    if not plaintext:
        raise EncryptionError("refusing to encrypt an empty value")
    nonce = os.urandom(_NONCE_BYTES)
    sealed = AESGCM(_key()).encrypt(nonce, plaintext.encode("utf-8"), None)
    return _VERSION + nonce + sealed


def decrypt(payload: bytes) -> str:
    """Decrypt a stored secret. Raises :class:`EncryptionError` if absent, corrupt or tampered."""
    if not payload or len(payload) <= 1 + _NONCE_BYTES:
        raise EncryptionError("ciphertext is missing or truncated")
    version, nonce, sealed = payload[:1], payload[1 : 1 + _NONCE_BYTES], payload[1 + _NONCE_BYTES :]
    if version != _VERSION:
        raise EncryptionError(f"unsupported ciphertext version {version!r}")
    try:
        return AESGCM(_key()).decrypt(nonce, sealed, None).decode("utf-8")
    except InvalidTag as exc:
        raise EncryptionError("ciphertext failed authentication (wrong key or tampered)") from exc


def generate_key() -> str:
    """A fresh base64url key, for operators provisioning ``TOKEN_ENCRYPTION_KEY``."""
    return base64.urlsafe_b64encode(os.urandom(_KEY_BYTES)).decode("ascii")
