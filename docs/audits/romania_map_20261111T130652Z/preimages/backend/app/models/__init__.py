from app.models.approval import ApprovalKind, ApprovalRequest, ApprovalStatus
from app.models.audit import AuditLog
from app.models.auth import Invitation, RecoveryCode, RefreshToken, UserSession
from app.models.base import Base
from app.models.operations import (
    PRIORITY_ORDER,
    Alert,
    AlertStatus,
    Camera,
    Evidence,
    Priority,
)
from app.models.push import PushSubscription
from app.models.retention import RETENTION_KINDS, RetentionPolicy
from app.models.saved_search import SavedSearch
from app.models.offline_video import AnalysisRun, Recording
from app.models.service import IngestNonce, ServiceAccount, ServiceKey
from app.models.tenant import Tenant, TenantKey
from app.models.user import Role, User

# Tables protected by tenant RLS (column ``tenant_id``); ``tenants`` uses ``id``.
TENANT_SCOPED_TABLES = (
    "tenant_keys",
    "users",
    "invitations",
    "recovery_codes",
    "user_sessions",
    "refresh_tokens",
    "cameras",
    "alerts",
    "evidence",
    "approval_requests",
    "push_subscriptions",
    "audit_log",
    "service_accounts",
    "service_keys",
    "ingest_nonces",
    "retention_policies",
    "saved_searches",
    "recordings",
    "analysis_runs",
)

__all__ = [
    "PRIORITY_ORDER",
    "RETENTION_KINDS",
    "TENANT_SCOPED_TABLES",
    "Alert",
    "AlertStatus",
    "AnalysisRun",
    "ApprovalKind",
    "ApprovalRequest",
    "ApprovalStatus",
    "AuditLog",
    "Base",
    "Camera",
    "Evidence",
    "IngestNonce",
    "Invitation",
    "Priority",
    "PushSubscription",
    "RecoveryCode",
    "RefreshToken",
    "RetentionPolicy",
    "Recording",
    "Role",
    "SavedSearch",
    "ServiceAccount",
    "ServiceKey",
    "Tenant",
    "TenantKey",
    "User",
    "UserSession",
]

from app.models.camera_control import *  # noqa: F401,F403
from app.models.casework import *  # noqa: F401,F403
from app.models.investigation import *  # noqa: F401,F403
# Integration additions participate in isolation checks and disposable-fixture cleanup too.
TENANT_SCOPED_TABLES = tuple(
    table.name for table in Base.metadata.sorted_tables if "tenant_id" in table.c
)
