"""Export the live FastAPI schema to ``frontend/openapi.json`` (Doc 14 §2 decoupling contract).

OpenAPI is **generated from the backend**, never hand-written: the backend is the single source of
truth for the API contract, and the frontend consumes only types generated from this file
(``npm run gen:api`` → ``src/lib/api/schema.d.ts``).

Run from the ``backend`` directory::

    .venv/Scripts/python.exe scripts/export_openapi.py          # write
    .venv/Scripts/python.exe scripts/export_openapi.py --check  # verify it is up to date (CI)

``--check`` exits non-zero when the committed file has drifted from the application, so a route
added without regenerating the contract is caught rather than silently shipped.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
TARGET = BACKEND_DIR.parent / "frontend" / "openapi.json"


def render() -> str:
    """The application's schema as the on-disk JSON document."""
    # Imported lazily so ``--help`` does not pay for application startup.
    sys.path.insert(0, str(BACKEND_DIR))
    from app.main import create_app

    return json.dumps(create_app().openapi(), indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if the committed schema differs from the application (writes nothing)",
    )
    args = parser.parse_args()

    generated = render()
    current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else None

    if args.check:
        if generated == current:
            print(f"openapi.json is up to date ({TARGET})")
            return 0
        print(f"openapi.json is STALE — run: python scripts/export_openapi.py ({TARGET})")
        return 1

    if generated == current:
        print(f"openapi.json already current, nothing written ({TARGET})")
        return 0

    TARGET.write_text(generated, encoding="utf-8")
    paths = len(json.loads(generated)["paths"])
    print(f"wrote {TARGET} ({paths} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
