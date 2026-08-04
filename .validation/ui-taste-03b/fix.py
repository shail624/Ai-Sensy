from __future__ import annotations

import sys
from pathlib import Path

root = Path(sys.argv[1])
path = root / "ReactivationPipelineBoard.tsx"
text = path.read_text(encoding="utf-8")
for unused in ("  Clock3,\n", "  FileCheck2,\n"):
    text = text.replace(unused, "")
path.write_text(text, encoding="utf-8")
