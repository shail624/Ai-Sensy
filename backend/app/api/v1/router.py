"""Aggregate API v1 router.

Every versioned endpoint group is mounted here under the ``/api/v1`` prefix (Doc 04
§2). Feature routers (auth, users, roles, …) are added in later steps; this file is
the single composition point so the surface stays organized and discoverable.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import auth, organization, roles, users

api_router = APIRouter()

# Module 1 — Authentication & RBAC (Doc 04 §11–§13).
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(users.router, tags=["Users"])
api_router.include_router(roles.router, tags=["RBAC"])
api_router.include_router(organization.router, tags=["Organization"])
