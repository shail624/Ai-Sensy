from __future__ import annotations

import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
path = root / "backend/tests/test_identity_resolution.py"
source = path.read_text(encoding="utf-8")
old = '"future-provider"'
new = '"future_provider"'
if source.count(old) != 4:
    raise SystemExit(f"verified connector fixture count changed: {source.count(old)}")
path.write_text(source.replace(old, new), encoding="utf-8")
