#!/usr/bin/env python3
"""Ensure the frozen M13 history feature flag is present exactly once."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: ensure_history_flag.py PRODUCT_ROOT")
    path = Path(sys.argv[1]).resolve() / "backend/app/channels/flags.py"
    content = path.read_text(encoding="utf-8")
    marker = '    HISTORY_SYNC = "omnichannel_qr_history"\n'
    count = content.count(marker)
    if count == 1:
        return
    if count != 0:
        raise SystemExit(f"expected history flag zero or one times, found {count}")
    anchor = '    QR_AUTH = "omnichannel_qr_auth"\n'
    if content.count(anchor) != 1:
        raise SystemExit("QR_AUTH anchor is not unique")
    path.write_text(content.replace(anchor, anchor + marker, 1), encoding="utf-8")


if __name__ == "__main__":
    main()
