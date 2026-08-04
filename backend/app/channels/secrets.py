"""Provider-neutral encrypted-secret primitives for the channel control plane.

The persistence layer stores only authenticated ciphertext plus an explicit key version.
This module deliberately has no provider, API, session, or runtime knowledge. A future KMS-backed
implementation can satisfy :class:`SecretCipher` without changing connection or credential models.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from app.core.crypto import EncryptionError, decrypt, encrypt

_CURRENT_KEY_VERSION = 1
_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "access_token",
        "refresh_token",
        "auth_token",
        "token",
        "secret",
        "client_secret",
        "password",
        "private_key",
        "credential",
        "credentials",
        "session_secret",
        "session_material",
    }
)


@dataclass(frozen=True, slots=True)
class SealedSecret:
    """Ciphertext envelope persisted by ``channel_secrets``."""

    ciphertext: bytes
    key_version: int


@runtime_checkable
class SecretCipher(Protocol):
    """Encryption boundary suitable for local AES-GCM now and external KMS later."""

    @property
    def current_key_version(self) -> int: ...

    def seal(self, plaintext: str) -> SealedSecret: ...

    def open(self, ciphertext: bytes, *, key_version: int) -> str: ...


class AesGcmSecretCipher:
    """Use the repository's authenticated AES-GCM envelope behind a versioned interface."""

    @property
    def current_key_version(self) -> int:
        return _CURRENT_KEY_VERSION

    def seal(self, plaintext: str) -> SealedSecret:
        return SealedSecret(
            ciphertext=encrypt(plaintext),
            key_version=self.current_key_version,
        )

    def open(self, ciphertext: bytes, *, key_version: int) -> str:
        if key_version != self.current_key_version:
            raise EncryptionError(f"unsupported channel secret key version: {key_version}")
        return decrypt(ciphertext)


def assert_no_secret_material(value: object, *, field_name: str) -> None:
    """Reject plaintext credential-shaped keys from configuration or metadata JSON.

    Provider configuration and factual metadata remain inspectable JSON. Credential values belong
    only in ``channel_secrets``. The recursive check closes the common accidental path where a token
    is nested several levels inside otherwise harmless configuration.
    """

    if isinstance(value, Mapping):
        for raw_key, nested in value.items():
            key = str(raw_key).strip().lower().replace("-", "_")
            if key in _SENSITIVE_KEYS:
                raise ValueError(
                    f"{field_name} must not contain plaintext credential field {raw_key!r}"
                )
            assert_no_secret_material(nested, field_name=field_name)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            assert_no_secret_material(nested, field_name=field_name)
