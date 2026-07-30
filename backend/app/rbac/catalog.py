"""Permission catalog and preset roles — the RBAC seed definition.

Single source of truth for the seeded permission catalog (Doc 04 §4.3 / Doc 12 §58) and
the default system roles (Doc 01 §2.4). The seed migration inserts the catalog; the
bootstrap routine creates the preset roles from it. At **runtime** the database is the
authority — permission validation queries the ``permissions`` table, not this module — so
adding a permission means an additive migration (governance rule, Doc 12 §58), never a
silent edit here.

Excluded on purpose: the ``(planned)`` permissions (``finance:read``, ``ops:emergency``,
``ops:dlq_delete``, ``analytics:executive``) are seeded when their module is built.
"""

from __future__ import annotations

from typing import TypedDict

# (code, description) — the fixed catalog (Doc 04 §4.3). Order is the seed order.
PERMISSION_CATALOG: tuple[tuple[str, str], ...] = (
    ("auth:self", "Manage own profile and sessions"),
    ("users:read", "View users"),
    ("users:write", "Edit users"),
    ("users:manage", "Administer users (create, deactivate, assign roles, reset password)"),
    ("roles:read", "View roles and permissions"),
    ("roles:write", "Create and edit roles and their permission sets"),
    ("contacts:read", "View contacts"),
    ("contacts:write", "Create and edit contacts"),
    ("contacts:import", "Import contacts"),
    ("contacts:export", "Export contacts"),
    ("segments:read", "View segments"),
    ("segments:write", "Create and edit segments"),
    ("templates:read", "View message templates"),
    ("templates:write", "Create and edit message templates"),
    ("templates:sync", "Synchronise templates with Meta"),
    ("media:read", "View the media library"),
    ("media:write", "Upload and manage media"),
    ("documents:read", "View customer documents, versions and verification history"),
    ("documents:write", "Create, version and archive customer documents"),
    ("documents:verify", "Verify, reject and expire customer documents"),
    ("campaigns:read", "View campaigns"),
    ("campaigns:write", "Create and edit campaigns"),
    ("campaigns:send", "Launch and send campaigns"),
    ("campaigns:manage", "Manage the full campaign lifecycle"),
    ("inbox:read", "View the shared inbox"),
    ("inbox:write", "Reply and act in the inbox"),
    ("inbox:assign", "Assign conversations to agents"),
    ("messages:send", "Send individual messages"),
    ("tasks:read", "View tasks, work queue, history and stats"),
    ("tasks:write", "Create and edit tasks; complete/skip/cancel/reopen/reschedule"),
    ("tasks:assign", "Assign or reassign a task to another agent"),
    ("ai:use", "Use AI assistance"),
    ("ai:manage", "Manage AI configuration and knowledge base"),
    ("analytics:read", "View analytics and reports"),
    ("analytics:export", "Export analytics reports (CSV/Excel/JSON)"),
    ("analytics:executive", "View cost analytics, spend and the executive dashboard"),
    ("waba:read", "View WhatsApp Business Accounts and numbers"),
    ("waba:manage", "Manage WhatsApp Business Accounts and numbers"),
    ("webhooks:manage", "Manage webhooks and replay"),
    ("settings:read", "View platform settings"),
    ("settings:manage", "Change platform settings"),
    ("audit:read", "View the audit log"),
    ("system:read", "View operational monitoring"),
    ("system:manage", "Manage operational subsystems"),
    ("apikeys:manage", "Manage API keys"),
)

# Preset system-role names (Doc 01 §2.4). ``is_system`` roles cannot be deleted/renamed.
ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"
ROLE_AGENT = "agent"
ROLE_ANALYST = "analyst"

_ALL_CODES: tuple[str, ...] = tuple(code for code, _ in PERMISSION_CATALOG)


class SystemRoleSpec(TypedDict):
    """Typed shape of one immutable preset-role definition."""

    name: str
    description: str
    permissions: tuple[str, ...]

# Role → granted permission codes (Doc 01 §2.4; Doc 12 §58 "typical role"). Roles are
# fully customizable afterwards (FR-AUTH-08); these are the shipped defaults. The Owner
# user additionally holds ``is_superuser`` and bypasses checks entirely (FR-AUTH-06).
SYSTEM_ROLES: tuple[SystemRoleSpec, ...] = (
    {
        "name": ROLE_OWNER,
        "description": "Business owner — full control (superuser).",
        "permissions": _ALL_CODES,
    },
    {
        "name": ROLE_ADMIN,
        "description": "Administrator — runs the platform day to day.",
        "permissions": _ALL_CODES,
    },
    {
        "name": ROLE_MANAGER,
        "description": "Campaign Manager — contacts, segments, templates, campaigns, analytics.",
        "permissions": (
            "auth:self",
            "contacts:read", "contacts:write", "contacts:import", "contacts:export",
            "segments:read", "segments:write",
            "templates:read", "templates:write", "templates:sync",
            "media:read", "media:write",
            "documents:read", "documents:write", "documents:verify",
            "campaigns:read", "campaigns:write", "campaigns:send", "campaigns:manage",
            "inbox:read", "messages:send",
            "tasks:read", "tasks:write", "tasks:assign",
            "analytics:read", "analytics:export",
        ),
    },
    {
        "name": ROLE_AGENT,
        "description": "Agent — front-line support in the inbox.",
        "permissions": (
            "auth:self",
            "inbox:read", "inbox:write", "inbox:assign",
            "messages:send",
            "tasks:read", "tasks:write",
            "contacts:read",
            "templates:read",
            "media:read",
            "documents:read", "documents:write",
            "ai:use",
        ),
    },
    {
        "name": ROLE_ANALYST,
        "description": "Analyst — read-only insights and reporting.",
        "permissions": (
            "auth:self",
            "analytics:read", "analytics:export",
            "tasks:read",
            "contacts:read",
            "segments:read",
            "campaigns:read",
            "templates:read",
        ),
    },
)


def permission_rows() -> list[dict[str, str | None]]:
    """Expand the catalog into ``permissions`` rows (code, resource, action, description)."""
    rows: list[dict[str, str | None]] = []
    for code, description in PERMISSION_CATALOG:
        resource, _, action = code.partition(":")
        rows.append(
            {"code": code, "resource": resource, "action": action, "description": description}
        )
    return rows


def all_permission_codes() -> frozenset[str]:
    """The full set of seeded permission codes (used for the superuser effective set)."""
    return frozenset(_ALL_CODES)
