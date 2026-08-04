from __future__ import annotations

import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()


def replace_expected(path_name: str, old: str, new: str) -> None:
    path = root / path_name
    source = path.read_text(encoding="utf-8")
    if source.count(old) != 1:
        raise SystemExit(f"verified marker changed in {path_name}: {source.count(old)}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


replace_expected(
    "backend/tests/test_api_vi_domain.py",
    '    assert len(schema["paths"]) == 193\n',
    '    assert len(schema["paths"]) == 200\n',
)
replace_expected(
    "backend/tests/test_migrations.py",
    '        assert version == "0035_notification_center"\n',
    '        assert version == "0036_customer_identity_resolution"\n',
)
