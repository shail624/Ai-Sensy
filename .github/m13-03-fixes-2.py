from __future__ import annotations

import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
path = root / "backend/app/models/channel_connection.py"
source = path.read_text(encoding="utf-8")

replacements = (
    ("from typing import Any\n", "from typing import Any, cast\n"),
    (
        "from sqlalchemy.orm import Mapped, mapped_column, relationship, validates\n"
        "from sqlalchemy.orm.attributes import NO_VALUE\n",
        "from sqlalchemy.orm import Mapped, mapped_column, relationship, validates\n"
        "from sqlalchemy.orm.state import InstanceState\n",
    ),
    (
        "def _immutable_when_persisted(instance: object, key: str, value: str | None) -> str | None:\n"
        "    state = inspect(instance)\n"
        "    loaded = state.attrs[key].loaded_value\n"
        "    if state.persistent and loaded is not NO_VALUE and loaded is not None and loaded != value:\n",
        "def _immutable_when_persisted(instance: object, key: str, value: str | None) -> str | None:\n"
        "    state = cast(InstanceState[Any], inspect(instance))\n"
        "    loaded = getattr(instance, key, None)\n"
        "    if state.persistent and loaded is not None and loaded != value:\n",
    ),
)

for old, new in replacements:
    if source.count(old) != 1:
        raise SystemExit(f"verified marker changed in {path.name}: {old!r}")
    source = source.replace(old, new, 1)

path.write_text(source, encoding="utf-8")
