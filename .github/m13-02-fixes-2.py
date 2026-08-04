from __future__ import annotations

import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
path = root / "backend/app/repositories/contact_identity.py"
source = path.read_text(encoding="utf-8")
old = "from sqlalchemy import func, select\nfrom app.models.contact_identity import (\n"
new = "from sqlalchemy import func, select\n\nfrom app.models.contact_identity import (\n"
if source.count(old) != 1:
    raise SystemExit("verified contact identity import marker changed")
path.write_text(source.replace(old, new, 1), encoding="utf-8")
