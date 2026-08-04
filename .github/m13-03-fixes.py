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


models = root / "backend/app/models/__init__.py"
source = models.read_text(encoding="utf-8")
channel_block = """from app.models.channel_connection import (
    ChannelConnection,
    ChannelEndpoint,
    ChannelSecret,
)
"""
campaign_block = """from app.models.campaign import (
    Campaign,
    CampaignBatch,
    CampaignRecipient,
    CampaignRetry,
    CampaignSchedule,
)
"""
if source.count(channel_block) != 1 or source.count(campaign_block) != 1:
    raise SystemExit("model import authority changed")
source = source.replace(channel_block, "", 1)
source = source.replace(campaign_block, campaign_block + channel_block, 1)
models.write_text(source, encoding="utf-8")

replace_once(
    "backend/app/services/channel_connection_service.py",
    "from typing import Any\n",
    "from typing import Any, Protocol\n",
)
replace_once(
    "backend/app/services/channel_connection_service.py",
    '_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{1,63}$")\n',
    'class _VersionedRow(Protocol):\n    row_version: int\n\n\n_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{1,63}$")\n',
)
replace_once(
    "backend/app/services/channel_connection_service.py",
    '    def _check_version(row: object, expected: int) -> None:\n        actual = getattr(row, "row_version")\n',
    "    def _check_version(row: _VersionedRow, expected: int) -> None:\n        actual = row.row_version\n",
)
replace_once(
    "backend/tests/test_channel_persistence.py",
    "from app.models.channel_connection import ChannelConnection, ChannelEndpoint, ChannelSecret\n",
    "from app.models.channel_connection import ChannelConnection, ChannelSecret\n",
)
