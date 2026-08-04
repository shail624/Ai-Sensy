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

from sqlalchemy.ext.asyncio import AsyncSession

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
    CONTACT_MERGED = "contact.merged"
    CONTACT_IDENTITY_LINKED = "contact_identity.linked"
    IDENTITY_CONFLICT_DETECTED = "identity_conflict.detected"
    IDENTITY_MERGE_RECOMMENDATION_CREATED = "identity_merge_recommendation.created"
    IDENTITY_MERGE_RECOMMENDATION_APPROVED = "identity_merge_recommendation.approved"
    IDENTITY_MERGE_RECOMMENDATION_REJECTED = "identity_merge_recommendation.rejected"
    DOCUMENT_CREATED = "contact_document.created"
    DOCUMENT_VERSION_ADDED = "contact_document.version_added"
    DOCUMENT_VERIFIED = "contact_document.verified"
    DOCUMENT_REJECTED = "contact_document.rejected"
    DOCUMENT_EXPIRED = "contact_document.expired"
    DOCUMENT_ARCHIVED = "contact_document.archived"
    BULK_STARTED = "bulk.started"
    BULK_COMPLETED = "bulk.completed"
    TAG_CREATED = "tag.created"
    TAG_UPDATED = "tag.updated"
    TAG_DELETED = "tag.deleted"
    LEAD_PIPELINE_CREATED = "lead_pipeline.created"
    LEAD_PIPELINE_UPDATED = "lead_pipeline.updated"
    LEAD_PIPELINE_DELETED = "lead_pipeline.deleted"
    WABA_CONNECTED = "waba.connected"
    WABA_UPDATED = "waba.updated"
    WABA_DISCONNECTED = "waba.disconnected"
    WABA_SYNC_STARTED = "waba.sync_started"
    WABA_SYNCED = "waba.synced"
    PHONE_NUMBER_UPDATED = "phone_number.updated"
    PHONE_NUMBER_REFRESHED = "phone_number.refreshed"
    CHANNEL_CONNECTION_CREATED = "channel_connection.created"
    CHANNEL_CONNECTION_UPDATED = "channel_connection.updated"
    CHANNEL_CONNECTION_OBSERVED = "channel_connection.observed"
    CHANNEL_CONNECTION_DELETED = "channel_connection.deleted"
    CHANNEL_ENDPOINT_CREATED = "channel_endpoint.created"
    CHANNEL_ENDPOINT_UPDATED = "channel_endpoint.updated"
    CHANNEL_ENDPOINT_OBSERVED = "channel_endpoint.observed"
    CHANNEL_ENDPOINT_DELETED = "channel_endpoint.deleted"
    CHANNEL_SECRET_CREATED = "channel_secret.created"
    CHANNEL_SECRET_ROTATED = "channel_secret.rotated"
    CHANNEL_SECRET_REVOKED = "channel_secret.revoked"
    CHANNEL_SECRET_ACCESSED = "channel_secret.accessed"
    CHANNEL_SESSION_REGISTERED = "channel_session.registered"
    CHANNEL_SESSION_OWNER_CHANGED = "channel_session.owner_changed"
    CHANNEL_SESSION_TRANSITIONED = "channel_session.transitioned"
    CHANNEL_SESSION_LOCK_ACQUIRED = "channel_session.lock_acquired"
    CHANNEL_SESSION_LOCK_RELEASED = "channel_session.lock_released"
    CHANNEL_SESSION_HEARTBEAT = "channel_session.heartbeat"
    CHANNEL_SESSION_HEALTH_OBSERVED = "channel_session.health_observed"
    CHANNEL_SESSION_RECOVERY_UPDATED = "channel_session.recovery_updated"
    CHANNEL_SESSION_RESTART_POLICY_UPDATED = "channel_session.restart_policy_updated"
    CHANNEL_SESSION_EXPIRED = "channel_session.expired"
    WEBHOOK_VERIFIED = "webhook.verified"
    WEBHOOK_DEAD_LETTERED = "webhook.dead_lettered"
    MESSAGE_SENT = "message.sent"
    TEMPLATE_CREATED = "template.created"
    TEMPLATE_UPDATED = "template.updated"
    TEMPLATE_DELETED = "template.deleted"
    TEMPLATE_SYNC_STARTED = "template.sync_started"
    TEMPLATE_SYNCED = "template.synced"
    CAMPAIGN_CREATED = "campaign.created"
    CAMPAIGN_UPDATED = "campaign.updated"
    CAMPAIGN_DELETED = "campaign.deleted"
    CAMPAIGN_DISPATCHED = "campaign.dispatched"
    CAMPAIGN_SCHEDULED = "campaign.scheduled"
    CONVERSATION_ASSIGNED = "conversation.assigned"
    CONVERSATION_STATUS_CHANGED = "conversation.status_changed"
    INTERNAL_NOTE_ADDED = "internal_note.added"
    INTERNAL_NOTE_DELETED = "internal_note.deleted"
    CAMPAIGN_PAUSED = "campaign.paused"
    CAMPAIGN_RESUMED = "campaign.resumed"
    CAMPAIGN_CANCELLED = "campaign.cancelled"
    CAMPAIGN_RETRIED = "campaign.retried"
    EXPORT_STARTED = "export.started"
    EXPORT_COMPLETED = "export.completed"
    IMPORT_STARTED = "import.started"
    IMPORT_COMPLETED = "import.completed"
    MEDIA_UPLOADED = "media.uploaded"
    MEDIA_DELETED = "media.deleted"
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
    AUTOMATION_CREATED = "automation.created"
    AUTOMATION_UPDATED = "automation.updated"
    AUTOMATION_PUBLISHED = "automation.published"
    AUTOMATION_RESTORED = "automation.restored"
    AUTOMATION_DISABLED = "automation.disabled"
    AUTOMATION_ENABLED = "automation.enabled"
    AUTOMATION_TEST_RUN_CREATED = "automation.test_run_created"
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_COMPLETED = "task.completed"
    TASK_CANCELLED = "task.cancelled"
    TASK_RESCHEDULED = "task.rescheduled"
    TASK_SNOOZED = "task.snoozed"
    TASK_REASSIGNED = "task.reassigned"
    TASK_DUE_NOTIFIED = "task.due_notified"
    NOTIFICATION_READ = "notification.read"
    NOTIFICATIONS_READ_ALL = "notification.read_all"
    REACTIVATION_CASE_CREATED = "reactivation_case.created"
    REACTIVATION_CASE_UPDATED = "reactivation_case.updated"
    REACTIVATION_STAGE_TRANSITIONED = "reactivation_case.stage_transitioned"
    REACTIVATION_NOTE_ADDED = "reactivation_case.note_added"
    ELIGIBILITY_RECORDED = "eligibility_check.recorded"
    KYC_CASE_CREATED = "kyc_case.created"
    KYC_CASE_UPDATED = "kyc_case.updated"
    KYC_DECISION_RECORDED = "kyc_decision.recorded"
    SIM_ORDER_CREATED = "sim_order.created"
    SIM_ORDER_UPDATED = "sim_order.updated"
    SIM_ORDER_TRANSITIONED = "sim_order.transitioned"
    ACTIVATION_CREATED = "activation_record.created"
    ACTIVATION_UPDATED = "activation_record.updated"
    ACTIVATION_TRANSITIONED = "activation_record.transitioned"
    SLA_POLICY_CREATED = "sla_policy.created"
    SLA_POLICY_UPDATED = "sla_policy.updated"
    SLA_EVENT_RECORDED = "sla_event.recorded"


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
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
