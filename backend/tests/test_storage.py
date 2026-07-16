"""Storage foundation tests: providers, signing, validation, scanning (Doc 08 §14, FR-MED)."""

from __future__ import annotations

import pytest

from app.storage import scanning, signing
from app.storage.base import StorageError, available_backends, get_provider
from app.storage.local import LocalStorageProvider
from app.storage.scanning import InfectedFile, ScanResult, VirusScanner
from app.storage.validation import (
    InvalidMedia,
    MediaTooLarge,
    UnsupportedMediaType,
    validate,
)


# --- Provider registry / abstraction (FR-MED-06, DD16) ----------------------
def test_local_backend_is_registered_and_unknown_fails_loudly() -> None:
    import app.storage.local  # noqa: F401 - registers 'local'

    assert "local" in available_backends()
    assert get_provider("local").backend == "local"
    with pytest.raises(StorageError, match="not available"):
        get_provider("s3")  # abstraction exists; no concrete provider registered yet


# --- Local provider ---------------------------------------------------------
async def test_local_put_get_exists_delete(tmp_path) -> None:
    provider = LocalStorageProvider(root=str(tmp_path))
    stored = await provider.put("a/b/file.txt", b"hello", content_type="text/plain")
    assert stored.byte_size == 5 and stored.backend == "local"
    assert await provider.exists("a/b/file.txt") is True
    assert await provider.get("a/b/file.txt") == b"hello"
    assert await provider.delete("a/b/file.txt") is True
    assert await provider.delete("a/b/file.txt") is False  # already gone
    assert await provider.exists("a/b/file.txt") is False


async def test_local_get_missing_raises(tmp_path) -> None:
    provider = LocalStorageProvider(root=str(tmp_path))
    with pytest.raises(StorageError):
        await provider.get("nope.bin")


async def test_local_rejects_empty_key_and_path_traversal(tmp_path) -> None:
    provider = LocalStorageProvider(root=str(tmp_path))
    with pytest.raises(StorageError):
        await provider.put("", b"x", content_type="text/plain")
    # Any key resolving outside the storage root is refused, not silently rewritten.
    for evil in ("../escape.txt", "a/../../escape.txt"):
        with pytest.raises(StorageError, match="escapes the storage root"):
            await provider.put(evil, b"x", content_type="text/plain")
    assert not (tmp_path.parent / "escape.txt").exists()

    # An absolute-looking key is confined to the root rather than re-rooting the write.
    await provider.put("/etc/passwd", b"x", content_type="text/plain")
    assert (tmp_path / "etc" / "passwd").is_file()


# --- Signed URLs (FR-MED-09) ------------------------------------------------
def test_signature_roundtrip() -> None:
    expires_at, sig = signing.issue("media-1", expires_in=60, now=1000)
    assert expires_at == 1060
    signing.verify("media-1", expires_at, sig, now=1000)  # no raise


def test_signature_rejects_tampering() -> None:
    expires_at, sig = signing.issue("media-1", expires_in=60, now=1000)
    with pytest.raises(signing.SignatureInvalid):
        signing.verify("media-2", expires_at, sig, now=1000)  # different asset
    with pytest.raises(signing.SignatureInvalid):
        signing.verify("media-1", expires_at + 3600, sig, now=1000)  # extended expiry
    with pytest.raises(signing.SignatureInvalid):
        signing.verify("media-1", expires_at, "deadbeef", now=1000)


def test_signature_expiry_is_distinct_from_invalid() -> None:
    expires_at, sig = signing.issue("media-1", expires_in=60, now=1000)
    with pytest.raises(signing.SignatureExpired):
        signing.verify("media-1", expires_at, sig, now=2000)


def test_local_signed_url_points_at_download_route() -> None:
    url = LocalStorageProvider(root="/tmp").signed_url(
        "k", media_id="018f-abc", expires_in=60
    )
    assert "/api/v1/media/018f-abc/download?expires=" in url and "signature=" in url


# --- Validation (FR-MED-01..04 → 413/415/422) -------------------------------
def test_validate_accepts_documented_types() -> None:
    validate(media_type="image", mime_type="image/jpeg", byte_size=1024)
    validate(media_type="document", mime_type="application/pdf", byte_size=1024)


def test_validate_rejects_wrong_mime_for_type() -> None:
    with pytest.raises(UnsupportedMediaType):
        validate(media_type="image", mime_type="application/pdf", byte_size=10)


def test_validate_enforces_per_type_size_ceiling() -> None:
    with pytest.raises(MediaTooLarge):
        validate(media_type="image", mime_type="image/jpeg", byte_size=6 * 1024 * 1024)
    # the same size is fine for video (16MB ceiling)
    validate(media_type="video", mime_type="video/mp4", byte_size=6 * 1024 * 1024)


def test_validate_rejects_unknown_type_and_empty_file() -> None:
    with pytest.raises(InvalidMedia):
        validate(media_type="hologram", mime_type="image/jpeg", byte_size=10)
    with pytest.raises(InvalidMedia):
        validate(media_type="image", mime_type="image/jpeg", byte_size=0)


# --- Virus scan interface (abstraction only) --------------------------------
class _CleanScanner(VirusScanner):
    name = "clean"

    async def scan(self, data: bytes, *, file_name: str | None = None) -> ScanResult:
        return ScanResult(clean=True)


class _InfectedScanner(VirusScanner):
    name = "infected"

    async def scan(self, data: bytes, *, file_name: str | None = None) -> ScanResult:
        return ScanResult(clean=False, signature="EICAR")


class _BrokenScanner(VirusScanner):
    name = "broken"

    async def scan(self, data: bytes, *, file_name: str | None = None) -> ScanResult:
        raise RuntimeError("daemon down")


async def test_no_scanner_configured_is_an_explicit_noop() -> None:
    scanning.register_scanner(None)
    assert scanning.active_scanner() is None
    assert await scanning.scan_or_raise(b"x") is None


async def test_scanner_clean_and_infected() -> None:
    try:
        scanning.register_scanner(_CleanScanner())
        assert (await scanning.scan_or_raise(b"x")).clean is True

        scanning.register_scanner(_InfectedScanner())
        with pytest.raises(InfectedFile, match="EICAR"):
            await scanning.scan_or_raise(b"x")
    finally:
        scanning.register_scanner(None)


async def test_scanner_failure_fails_closed() -> None:
    try:
        scanning.register_scanner(_BrokenScanner())
        # An unscannable file is treated as unsafe, never waved through.
        with pytest.raises(InfectedFile, match="scan failed"):
            await scanning.scan_or_raise(b"x")
    finally:
        scanning.register_scanner(None)
