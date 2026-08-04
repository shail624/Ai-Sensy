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
    "backend/app/services/session_manager.py",
    """                \"fencing_token\": row.fencing_token,\n                \"lease_expires_at\": row.lease_expires_at,\n                \"row_version\": row.row_version,\n""",
    """                \"fencing_token\": row.fencing_token,\n                \"lease_expires_at\": (\n                    row.lease_expires_at.isoformat()\n                    if row.lease_expires_at is not None\n                    else None\n                ),\n                \"row_version\": row.row_version,\n""",
)
replace_once(
    "backend/app/services/session_manager.py",
    """                \"last_heartbeat_at\": row.last_heartbeat_at,\n                \"lease_expires_at\": row.lease_expires_at,\n""",
    """                \"last_heartbeat_at\": (\n                    row.last_heartbeat_at.isoformat()\n                    if row.last_heartbeat_at is not None\n                    else None\n                ),\n                \"lease_expires_at\": (\n                    row.lease_expires_at.isoformat()\n                    if row.lease_expires_at is not None\n                    else None\n                ),\n""",
)
replace_once(
    "backend/app/services/session_manager.py",
    """    def _validate_metadata(value: dict[str, Any] | None, field_name: str) -> None:\n        if value is not None:\n            assert_no_secret_material(value, field_name=field_name)\n""",
    """    def _validate_metadata(value: dict[str, Any] | None, field_name: str) -> None:\n        if value is None:\n            return\n        try:\n            assert_no_secret_material(value, field_name=field_name)\n        except ValueError as exc:\n            raise ValidationError(str(exc)) from exc\n""",
)
replace_once(
    "backend/tests/test_session_manager.py",
    """from app.channels.foundation import ProviderDesiredState, ProviderHealthState, ProviderObservedState\nfrom app.channels.foundation import ChannelMetadata\n""",
    """from app.channels.foundation import (\n    ChannelMetadata,\n    ProviderDesiredState,\n    ProviderHealthState,\n    ProviderObservedState,\n)\n""",
)
