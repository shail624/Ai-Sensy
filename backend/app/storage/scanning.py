"""Virus scan interface (Doc 08 §26 — abstraction only).

The **contract** an anti-virus backend implements, plus the hook the upload path calls. No
scanner ships here: the concrete engine (e.g. a ClamAV daemon) is infrastructure and is
registered by its own module.

Fail-closed by design: if a scanner **is** configured and it errors, the upload is rejected —
an unscannable file is treated as unsafe rather than waved through. When no scanner is
registered the hook is a documented no-op, so this never silently pretends to scan.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScanResult:
    clean: bool
    signature: str | None = None
    detail: str | None = None


class InfectedFile(Exception):
    """The scanner flagged the upload (→ 422)."""


class VirusScanner(ABC):
    """Anti-virus contract (Doc 08 §26)."""

    name: str

    @abstractmethod
    async def scan(self, data: bytes, *, file_name: str | None = None) -> ScanResult:
        """Scan bytes; return a :class:`ScanResult`."""


_scanner: VirusScanner | None = None


def register_scanner(scanner: VirusScanner | None) -> None:
    """Install (or clear, with ``None``) the active scanner."""
    global _scanner
    _scanner = scanner


def active_scanner() -> VirusScanner | None:
    return _scanner


async def scan_or_raise(data: bytes, *, file_name: str | None = None) -> ScanResult | None:
    """Scan when a scanner is configured; raise :class:`InfectedFile` if unsafe/unscannable."""
    scanner = _scanner
    if scanner is None:
        return None
    try:
        result = await scanner.scan(data, file_name=file_name)
    except InfectedFile:
        raise
    except Exception as exc:  # noqa: BLE001 - fail closed: unscannable == unsafe
        raise InfectedFile(f"virus scan failed: {exc}") from exc
    if not result.clean:
        raise InfectedFile(result.detail or f"infected: {result.signature or 'unknown'}")
    return result
