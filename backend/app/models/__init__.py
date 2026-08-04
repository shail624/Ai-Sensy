"""ORM model registry.

Importing this package registers every table on :data:`app.db.base.Base.metadata`.
The Alembic environment and the test schema builder import it so migrations and
``create_all`` see the full schema. Import models from here (or their modules); never
rely on import side effects elsewhere.
"""

from __future__ import annotations

from app.models.analytics import (
    AnalyticsCampaignRollup,
    AnalyticsContactRollup,
    AnalyticsConversationRollup,
    AnalyticsFailureRollup,
    AnalyticsMessageRollup,
    AnalyticsRollupRun,
    AnalyticsTaskRollup,
)
from app.models.api_key import ApiKey
from app.models.attribute import ContactAttributeValue, CustomAttributeDefinition
from app.models.audit import AuditLog
from app.models.automation import (
    AutomationFlow,
    AutomationFlowVersion,
    AutomationRun,
    AutomationStepAttempt,
    AutomationTriggerReceipt,
)
from app.models.business_event import BusinessEvent, BusinessEventType
from app.models.campaign import (
    Campaign,
    CampaignBatch,
    CampaignRecipient,
    CampaignRetry,
    CampaignSchedule,
)
from app.models.contact import Contact
from app.models.contact_document import (
    ContactDocument,
    ContactDocumentEvent,
    ContactDocumentVersion,
)
from app.models.contact_event import ContactEvent
from app.models.contact_identity import (
    ContactIdentity,
    IdentityConflict,
    IdentityMergeRecommendation,
)
from app.models.conversation import Conversation
from app.models.conversation_tag import conversation_tags
from app.models.internal_note import InternalNote
from app.models.job import DeadLetter, JobMetadata
from app.models.job_records import BulkJob, ExportJob, ImportJob
from app.models.lead import LeadPipeline, LeadStage
from app.models.media import MediaAsset
from app.models.message import Message, MessageStatusHistory
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.quick_reply import QuickReply
from app.models.rate_card import RateCard
from app.models.role import Permission, Role, UserRole, role_permissions
from app.models.segment import Segment, SegmentRule
from app.models.settings import FeatureFlag, Setting
from app.models.tag import Tag, contact_tags
from app.models.task import Task
from app.models.task_event import TaskEvent
from app.models.template import MessageTemplate, TemplateVersion
from app.models.token import RefreshToken, UserSession
from app.models.user import User
from app.models.vi_domain import (
    ActivationRecord,
    EligibilityCheck,
    KycCase,
    KycDecision,
    KycDocumentReference,
    ReactivationCase,
    ReactivationCaseLabel,
    ReactivationStageEvent,
    SimOrder,
    SimOrderEvent,
    SlaEvent,
    SlaPolicy,
)
from app.models.waba import PhoneNumber, WhatsAppBusinessAccount
from app.models.webhook import WebhookDeadLetter, WebhookEvent

__all__ = [
    "ApiKey",
    "AuditLog",
    "AutomationFlow",
    "AutomationFlowVersion",
    "AutomationRun",
    "AutomationStepAttempt",
    "AutomationTriggerReceipt",
    "BusinessEvent",
    "BusinessEventType",
    "BulkJob",
    "Campaign",
    "CampaignBatch",
    "CampaignRecipient",
    "CampaignRetry",
    "CampaignSchedule",
    "Contact",
    "ContactIdentity",
    "IdentityConflict",
    "IdentityMergeRecommendation",
    "ContactDocument",
    "ContactDocumentEvent",
    "ContactDocumentVersion",
    "ContactAttributeValue",
    "ContactEvent",
    "Conversation",
    "CustomAttributeDefinition",
    "conversation_tags",
    "DeadLetter",
    "ExportJob",
    "FeatureFlag",
    "ImportJob",
    "InternalNote",
    "JobMetadata",
    "LeadPipeline",
    "LeadStage",
    "MediaAsset",
    "Message",
    "MessageTemplate",
    "MessageStatusHistory",
    "Notification",
    "Organization",
    "Permission",
    "QuickReply",
    "RateCard",
    "PhoneNumber",
    "RefreshToken",
    "Role",
    "Segment",
    "SegmentRule",
    "Setting",
    "Tag",
    "AnalyticsCampaignRollup",
    "AnalyticsContactRollup",
    "AnalyticsConversationRollup",
    "AnalyticsFailureRollup",
    "AnalyticsMessageRollup",
    "AnalyticsRollupRun",
    "AnalyticsTaskRollup",
    "Task",
    "TaskEvent",
    "TemplateVersion",
    "User",
    "UserRole",
    "UserSession",
    "WebhookDeadLetter",
    "WebhookEvent",
    "WhatsAppBusinessAccount",
    "contact_tags",
    "role_permissions",
    "ActivationRecord",
    "EligibilityCheck",
    "KycCase",
    "KycDecision",
    "KycDocumentReference",
    "ReactivationCase",
    "ReactivationCaseLabel",
    "ReactivationStageEvent",
    "SimOrder",
    "SimOrderEvent",
    "SlaEvent",
    "SlaPolicy",
]
