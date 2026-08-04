from __future__ import annotations

import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()


def replace_once(path_name: str, old: str, new: str) -> None:
    path = root / path_name
    source = path.read_text(encoding="utf-8")
    if source.count(old) != 1:
        raise SystemExit(f"verified marker changed in {path_name}: {source.count(old)}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


replace_once(
    "backend/app/services/session_manager.py",
    """        if row.holder_runtime_id is not None and row.lease_expires_at is not None:\n            if row.lease_expires_at > now:\n                raise ConflictError(\"The session lease is held by another active runtime.\")\n""",
    """        if (\n            row.holder_runtime_id is not None\n            and row.lease_expires_at is not None\n            and row.lease_expires_at > now\n        ):\n            raise ConflictError(\"The session lease is held by another active runtime.\")\n""",
)
replace_once(
    "backend/tests/test_session_manager.py",
    """from app.channels.foundation import ProviderDesiredState, ProviderHealthState, ProviderObservedState\nfrom app.channels.foundation import ChannelMetadata\n""",
    """from app.channels.foundation import (\n    ChannelMetadata,\n    ProviderDesiredState,\n    ProviderHealthState,\n    ProviderObservedState,\n)\n""",
)
