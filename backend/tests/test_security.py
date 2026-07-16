"""Unit tests for the security primitives (Doc 01 §5.4, Doc 04 §4)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core import security


# --- Passwords --------------------------------------------------------------
def test_password_hash_is_argon2id_and_verifies() -> None:
    hashed = security.hash_password("Sup3r-Secret-Pass!")
    assert hashed.startswith("$argon2id$")
    assert hashed != "Sup3r-Secret-Pass!"  # never stored in plaintext
    assert security.verify_password("Sup3r-Secret-Pass!", hashed) is True


def test_password_verify_rejects_wrong_and_malformed() -> None:
    hashed = security.hash_password("correct horse battery staple")
    assert security.verify_password("wrong password", hashed) is False
    assert security.verify_password("anything", "not-a-valid-hash") is False


def test_password_hashes_are_salted_and_unique() -> None:
    assert security.hash_password("same") != security.hash_password("same")


def test_password_needs_rehash_on_invalid_hash() -> None:
    assert security.password_needs_rehash("garbage") is True


# --- Access tokens ----------------------------------------------------------
def test_access_token_roundtrip() -> None:
    token, expires_in = security.create_access_token(
        subject="018f-user-uuid", jti="fam-1", perms_hash="abc123"
    )
    assert expires_in > 0
    claims = security.decode_access_token(token)
    assert claims.subject == "018f-user-uuid"
    assert claims.jti == "fam-1"
    assert claims.permissions_hash == "abc123"


def test_access_token_rejects_tampered_signature() -> None:
    token, _ = security.create_access_token(subject="u", jti="j", perms_hash="h")
    with pytest.raises(jwt.InvalidTokenError):
        security.decode_access_token(token + "x")


def test_access_token_rejects_expired() -> None:
    past = datetime.now(UTC) - timedelta(hours=2)
    token, _ = security.create_access_token(subject="u", jti="j", perms_hash="h", now=past)
    with pytest.raises(jwt.ExpiredSignatureError):
        security.decode_access_token(token)


def test_access_token_rejects_wrong_type() -> None:
    forged = jwt.encode(
        {
            "sub": "u",
            "jti": "j",
            "type": "refresh",
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        },
        security.settings.secret_key,
        algorithm=security.settings.jwt_algorithm,
    )
    with pytest.raises(jwt.InvalidTokenError):
        security.decode_access_token(forged)


# --- Permissions hash -------------------------------------------------------
def test_permissions_hash_is_order_independent_and_stable() -> None:
    a = security.permissions_hash({"users:read", "roles:read"})
    b = security.permissions_hash({"roles:read", "users:read"})
    assert a == b
    assert a != security.permissions_hash({"users:read"})


# --- Refresh tokens ---------------------------------------------------------
def test_refresh_token_is_opaque_and_unique() -> None:
    t1 = security.generate_refresh_token()
    t2 = security.generate_refresh_token()
    assert t1 != t2
    assert len(t1) >= 32


def test_hash_token_is_deterministic_sha256() -> None:
    digest = security.hash_token("some-token")
    assert digest == security.hash_token("some-token")
    assert len(digest) == 64  # fits CHAR(64) (Doc 03 §4.4)
    assert digest != "some-token"


def test_new_jti_is_unique_uuid() -> None:
    assert security.new_jti() != security.new_jti()


# --- IP packing -------------------------------------------------------------
@pytest.mark.parametrize("ip", ["203.0.113.7", "2001:db8::1"])
def test_ip_pack_roundtrip(ip: str) -> None:
    packed = security.pack_ip(ip)
    assert isinstance(packed, bytes)
    assert security.unpack_ip(packed) == ip


def test_ip_pack_handles_none_and_invalid() -> None:
    assert security.pack_ip(None) is None
    assert security.pack_ip("not-an-ip") is None
    assert security.unpack_ip(None) is None
