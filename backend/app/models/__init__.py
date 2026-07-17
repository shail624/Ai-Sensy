"""ORM model registry.

Importing this package registers every table on :data:`app.db.base.Base.metadata`.
The Alembic environment and the test schema builder import it so migrations and
``create_all`` see the full schema. Import models from here (or their modules); never
rely on import side effects elsewhere.
"""

from __future__ import annotations

from app.models.api_key import ApiKey
from app.models.attribute import ContactAttributeValue, CustomAttributeDefinition
from app.models.audit import AuditLog
from app.models.contact import Contact
from app.models.contact_event import ContactEvent
from app.models.job import DeadLetter, JobMetadata
from app.models.job_records import BulkJob, ExportJob, ImportJob
from app.models.lead import LeadPipeline, LeadStage
from app.models.media import MediaAsset
from app.models.organization import Organization
from app.models.role import Permission, Role, UserRole, role_permissions
from app.models.segment import Segment, SegmentRule
from app.models.settings import FeatureFlag, Setting
from app.models.tag import Tag, contact_tags
from app.models.token import RefreshToken, UserSession
from app.models.user import User
from app.models.waba import PhoneNumber, WhatsAppBusinessAccount

__all__ = [
    "ApiKey",
    "AuditLog",
    "BulkJob",
    "Contact",
    "ContactAttributeValue",
    "ContactEvent",
    "CustomAttributeDefinition",
    "DeadLetter",
    "ExportJob",
    "FeatureFlag",
    "ImportJob",
    "JobMetadata",
    "LeadPipeline",
    "LeadStage",
    "MediaAsset",
    "Organization",
    "Permission",
    "PhoneNumber",
    "RefreshToken",
    "Role",
    "Segment",
    "SegmentRule",
    "Setting",
    "Tag",
    "User",
    "UserRole",
    "UserSession",
    "WhatsAppBusinessAccount",
    "contact_tags",
    "role_permissions",
]
