"""Aggregate API v1 router.

Every versioned endpoint group is mounted here under the ``/api/v1`` prefix (Doc 04
§2). Feature routers (auth, users, roles, …) are added in later steps; this file is
the single composition point so the surface stays organized and discoverable.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    api_keys,
    audit,
    auth,
    contacts,
    leads,
    organization,
    roles,
    segments,
    settings,
    tags,
    users,
)

api_router = APIRouter()

# Module 1 — Authentication, RBAC & administration (Doc 04 §11–§13, §22).
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(users.router, tags=["Users"])
api_router.include_router(roles.router, tags=["RBAC"])
api_router.include_router(organization.router, tags=["Organization"])
api_router.include_router(settings.router, tags=["Settings"])
api_router.include_router(api_keys.router, tags=["API Keys"])
api_router.include_router(audit.router, tags=["Audit"])

# Module 2 — Contacts CRM (Doc 04 §14; Doc 07 §19/§23 lead model).
api_router.include_router(contacts.router, tags=["Contacts"])
api_router.include_router(tags.router, tags=["Tags"])
api_router.include_router(segments.router, tags=["Segments"])
api_router.include_router(leads.router, tags=["Leads"])
