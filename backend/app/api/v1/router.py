"""Aggregate API v1 router.

Every versioned endpoint group is mounted here under the ``/api/v1`` prefix (Doc 04
§2). Feature routers (auth, users, roles, …) are added in later steps; this file is
the single composition point so the surface stays organized and discoverable.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    api_keys,
    attributes,
    audit,
    auth,
    campaigns,
    contacts,
    conversations,
    jobs,
    leads,
    media,
    messages,
    organization,
    roles,
    segments,
    settings,
    tags,
    templates,
    users,
    waba,
    webhooks,
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
api_router.include_router(attributes.router, tags=["Custom Attributes"])
api_router.include_router(segments.router, tags=["Segments"])
api_router.include_router(leads.router, tags=["Leads"])

# Module 6 — Queue Engine (Doc 04 §22; Doc 06).
api_router.include_router(jobs.router, tags=["Queue"])

# Storage foundation (Doc 04 §16; Doc 08 §14).
api_router.include_router(media.router, tags=["Media"])

# Module 4 — WhatsApp Core: WABAs & phone numbers (Doc 04 §13.2/§13.3; Doc 07 §5).
api_router.include_router(waba.router, tags=["WhatsApp Infrastructure"])
# Module 4 — inbound webhooks (Doc 04 §23; Doc 06 §11). Public + signature-gated, not authenticated.
api_router.include_router(webhooks.router, tags=["Webhooks"])
# Module 4 — outbound send + message reads (Doc 04 §18.2).
api_router.include_router(messages.router, tags=["Messaging"])

# Module 5 — template registry (Doc 04 §15; Doc 03 §7.1).
api_router.include_router(templates.router, tags=["Templates"])

# Phase 6 — campaign registry & audience (Doc 04 §17; Doc 03 §8.1/§8.3).
api_router.include_router(campaigns.router, tags=["Campaigns"])

# Phase 7 — Shared Inbox: conversation assignment, status & internal notes (Doc 04 §18.1).
api_router.include_router(conversations.router, tags=["Inbox"])
