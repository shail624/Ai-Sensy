"""Audit service — records every security-relevant action (Doc 03 §11.2, Doc 01 NFR-SEC-07).

Writes immutable ``audit_logs`` rows in the caller's transaction, so the audit entry commits
atomically with the action it records (Audit Integration, Doc 12 §58 governance). A per-row
content digest (``row_hash``) is stored for integrity; the optional cross-row hash chain
(``prev_hash``) is a later hardening (Doc 03 §11.2 marks it optional).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.models.audit import ACTOR_USER, AuditLog
from app.repositories.audit import AuditRepository


class AuditAction:
    """Canonical action names for security events (``entity.verb``, Doc 03 §11.2)."""

    LOGIN = "user.login"
    LOGIN_FAILED = "user.login_failed"
    LOGIN_LOCKED = "user.login_locked"
    LOGOUT = "user.logout"
    LOGOUT_ALL = "user.logout_all"
    TOKEN_REFRESH = "user.token_refresh"
    TOKEN_REUSE_DETECTED = "user.token_reuse_detected"
    PASSWORD_CHANGED = "user.password_changed"
    SESSION_REVOKED = "user.session_revoked"
    ROLE_CREATED = "role.created"
    ROLE_UPDATED = "role.updated"
    ROLE_DELETED = "role.deleted"
    ROLE_PERMISSIONS_UPDATED = "role.permissions_updated"
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_ACTIVATED = "user.activated"
    USER_DEACTIVATED = "user.deactivated"
    USER_DELETED = "user.deleted"
    ORGANIZATION_UPDATED = "organization.updated"
    SETTING_UPDATED = "setting.updated"
    FEATURE_FLAG_UPDATED = "feature_flag.updated"
    PREFERENCES_UPDATED = "preferences.updated"
    API_KEY_CREATED = "api_key.created"
    API_KEY_REVOKED = "api_key.revoked"
    CONTACT_CREATED = "contact.created"
    CONTACT_UPDATED = "contact.updated"
    CONTACT_DELETED = "contact.deleted"
    CONTACT_TAGGED = "contact.tagged"
    CONTACT_UNTAGGED = "contact.untagged"
    TAG_CREATED = "tag.created"
    TAG_UPDATED = "tag.updated"
    TAG_DELETED = "tag.deleted"
    LEAD_PIPELINE_CREATED = "lead_pipeline.created"
    LEAD_PIPELINE_UPDATED = "lead_pipeline.updated"
    LEAD_PIPELINE_DELETED = "lead_pipeline.deleted"
    JOB_CANCELLED = "job.cancelled"
    DEAD_LETTER_REPLAYED = "dead_letter.replayed"
    DEAD_LETTER_DISCARDED = "dead_letter.discarded"
    ATTRIBUTE_CREATED = "custom_attribute.created"
    ATTRIBUTE_UPDATED = "custom_attribute.updated"
    ATTRIBUTE_DELETED = "custom_attribute.deleted"
    CONTACT_ATTRIBUTES_SET = "contact.attributes_set"
    SEGMENT_CREATED = "segment.created"
    SEGMENT_UPDATED = "segment.updated"
    SEGMENT_DELETED = "segment.deleted"
    SEGMENT_REFRESHED = "segment.refreshed"
    LEAD_STAGE_CREATED = "lead_stage.created"
    LEAD_STAGE_UPDATED = "lead_stage.updated"
    LEAD_STAGE_DELETED = "lead_stage.deleted"


class AuditService:
    def __init__(self, session) -> None:
        self._repo = AuditRepository(session)

    async def record(
        self,
        action: str,
        *,
        actor_user_id: int | None = None,
        actor_type: str = ACTOR_USER,
        organization_id: int | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        ip_address: bytes | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Append one audit entry (does not commit — shares the caller's transaction)."""
        entry = AuditLog(
            action=action,
            actor_user_id=actor_user_id,
            actor_type=actor_type,
            organization_id=organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            before_json=before,
            after_json=after,
            metadata_json=metadata,
        )
        entry.row_hash = self._row_hash(entry)
        return await self._repo.record(entry)

    @staticmethod
    def _row_hash(entry: AuditLog) -> str:
        """SHA-256 of the entry's canonical content (tamper-evidence, Doc 03 §11.2)."""
        canonical = json.dumps(
            {
                "action": entry.action,
                "actor_user_id": entry.actor_user_id,
                "actor_type": entry.actor_type,
                "organization_id": entry.organization_id,
                "entity_type": entry.entity_type,
                "entity_id": entry.entity_id,
                "before": entry.before_json,
                "after": entry.after_json,
                "metadata": entry.metadata_json,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
