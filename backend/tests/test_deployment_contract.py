"""Contract tests for the production Compose manifest.

These assert properties of `docker-compose.production.yml` that no other gate covers. The
deployed-stack gate starts the stack, but it creates its owner with an explicit
`run --env OWNER_EMAIL --env OWNER_PASSWORD api ...`, so it proves its own invocation works and
says nothing about the one an operator is told to run. The documented first-deploy command was
broken for exactly that reason: Compose gives a container only the variables named in its own
`environment:` block, while `--env-file` governs interpolation of the manifest on the host, and
no service declared `OWNER_*` at all.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = REPOSITORY_ROOT / "docker-compose.production.yml"
DEPLOYMENT_GUIDE = REPOSITORY_ROOT / "deploy" / "DEPLOYMENT.md"
MIGRATIONS = REPOSITORY_ROOT / "backend" / "alembic" / "versions"

# Roles that run for the life of the deployment, as opposed to the one-shots.
LONG_LIVED_SERVICES = (
    "api",
    "worker-realtime",
    "worker-bulk",
    "worker-jobs",
    "beat",
)


@pytest.fixture(scope="module")
def compose() -> dict[str, Any]:
    # safe_load applies YAML merge keys, so each service's environment already carries the
    # shared `x-backend-env` anchor the way Compose would resolve it.
    loaded: dict[str, Any] = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    return loaded


def _env(compose: dict[str, Any], service: str) -> dict[str, str]:
    return compose["services"][service].get("environment", {}) or {}


def test_bootstrap_service_carries_the_owner_credentials(compose: dict[str, Any]) -> None:
    """The documented first-deploy command must be able to read what the CLI requires."""
    env = _env(compose, "bootstrap")
    for variable in ("OWNER_EMAIL", "OWNER_PASSWORD", "OWNER_FULL_NAME"):
        assert variable in env, f"{variable} never reaches the bootstrap container"
    assert "BOOTSTRAP_ORG_NAME" in env
    assert "BOOTSTRAP_ORG_SLUG" in env
    # It still needs the ordinary backend environment to reach the database at all.
    assert "DATABASE_URL" in env


def test_owner_password_never_reaches_a_long_lived_container(compose: dict[str, Any]) -> None:
    """A plaintext owner credential must not sit in `docker inspect` for the life of the stack."""
    for service in LONG_LIVED_SERVICES:
        assert "OWNER_PASSWORD" not in _env(compose, service), (
            f"{service} carries OWNER_PASSWORD; it belongs only to the bootstrap one-shot"
        )


def test_bootstrap_is_profile_gated_and_does_not_restart(compose: dict[str, Any]) -> None:
    service = compose["services"]["bootstrap"]
    assert "bootstrap" in service.get("profiles", []), (
        "bootstrap must not start with a plain `up -d`"
    )
    # `restart: unless-stopped` on a command that exits 0 is an infinite loop.
    assert service.get("restart") == "no"
    assert service["depends_on"]["migrate"]["condition"] == "service_completed_successfully"


def test_owner_variables_are_not_mandatory_for_a_normal_start(compose: dict[str, Any]) -> None:
    """`${VAR:?}` inside a profiled service still aborts `up` for the whole stack.

    Compose interpolates every service in the file regardless of which profiles are active, so a
    required-variable marker on an owner variable would break the stack the moment §5 tells the
    operator to clear `OWNER_*` after bootstrapping.
    """
    raw = COMPOSE_FILE.read_text(encoding="utf-8")
    required = set(re.findall(r"\$\{(OWNER_[A-Z_]*|BOOTSTRAP_[A-Z_]*):\?", raw))
    assert not required, f"these abort `up -d` once cleared after bootstrap: {sorted(required)}"


def test_api_docs_flag_reaches_containers_with_a_parseable_default(compose: dict[str, Any]) -> None:
    """A documented setting that no container receives is decoration.

    The default must also survive validation: the field is `bool | None`, and pydantic rejects an
    empty string, so `${API_DOCS_ENABLED:-}` would crash-loop every backend container the moment
    an operator left it unset — which is the default case.
    """
    from app.core.config import Settings

    for service in LONG_LIVED_SERVICES:
        assert "API_DOCS_ENABLED" in _env(compose, service), (
            f"API_DOCS_ENABLED is documented but never reaches {service}"
        )

    reference = _env(compose, "api")["API_DOCS_ENABLED"]
    default = re.fullmatch(r"\$\{API_DOCS_ENABLED:-(?P<value>.*)\}", str(reference))
    assert default is not None, f"unexpected form: {reference!r}"
    fallback = default.group("value")
    assert fallback != "", "an empty default fails validation and crash-loops the container"

    settings = Settings(
        secret_key="x" * 32,
        environment="production",
        api_docs_enabled=fallback,
    )
    # Unset must keep production's existing behaviour: the reference stays withheld.
    assert settings.serve_api_docs is False


def test_deployment_guide_names_the_current_migration_head() -> None:
    """§4 told operators to expect a revision 41 migrations behind the repository."""
    revisions = sorted(p.stem for p in MIGRATIONS.glob("[0-9]*.py"))
    head = revisions[-1]
    guide = DEPLOYMENT_GUIDE.read_text(encoding="utf-8")
    assert f"**`{head}`**" in guide, f"DEPLOYMENT.md §4 does not name the current head {head!r}"
