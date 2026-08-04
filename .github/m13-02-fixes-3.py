from __future__ import annotations

import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
path = root / "backend/tests/test_identity_resolution.py"
source = path.read_text(encoding="utf-8")
old = '"future-provider"'
new = '"future_provider"'
old_count = source.count(old)
new_count = source.count(new)
if old_count == 6 and new_count == 0:
    source = source.replace(old, new)
elif old_count == 0 and new_count == 6:
    pass
else:
    raise SystemExit(
        f"verified connector fixture counts changed: old={old_count} new={new_count}"
    )
path.write_text(source, encoding="utf-8")
