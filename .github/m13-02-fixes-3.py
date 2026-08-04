from __future__ import annotations

import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
path = root / "backend/tests/test_identity_resolution.py"
source = path.read_text(encoding="utf-8")
old = '"future-provider"'
new = '"future_provider"'
count = source.count(old)
if count == 6:
    path.write_text(source.replace(old, new), encoding="utf-8")
elif count != 0:
    raise SystemExit(f"verified connector fixture count changed: {count}")
