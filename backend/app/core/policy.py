"""Central RBAC policy. Routers declare *what* they need (a Permission); this module alone
decides *who* has it. Object-level rules (patrol sees only assigned alerts) also live here so
they cannot drift between endpoints."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Select, String, cast, select

from app.models import Alert, AuditLog, Role

if TYPE_CHECKING:
    from app.deps import Principal


class Permission(enum.StrEnum):
    map_read = "map:read"
    location_edit = "location:edit"
    map_demo_read = "map:demo_read"
    alerts_read = "alerts:read"
    alerts_create = "alerts:create"
    alerts_decide = "alerts:decide"
    alerts_assign = "alerts:assign"
    alerts_plate_search = "alerts:plate_search"
    cameras_read = "cameras:read"
    cameras_manage = "cameras:manage"
    videos_read = "videos:read"
    videos_analyze = "videos:analyze"
    evidence_read = "evidence:read"
    approvals_request = "approvals:request"
    approvals_read_all = "approvals:read_all"
    approvals_decide = "approvals:decide"
    users_manage = "users:manage"
    sessions_manage_all = "sessions:manage_all"
    audit_read = "audit:read"
    audit_verify = "audit:verify"
    tenants_create = "tenants:create"
    keys_rotate = "keys:rotate"
    push_subscribe = "push:subscribe"
    service_accounts_manage = "service_accounts:manage"
    retention_manage = "retention:manage"
    patrol_respond = "patrol:respond"
    stats_read = "stats:read"
    cameras_status_read = "cameras:status_read"
    cases_annotate = "cases:annotate"
    cases_legal_hold = "cases:legal_hold"


P = Permission

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.system_admin: frozenset(
        {P.tenants_create, P.users_manage, P.sessions_manage_all, P.audit_read, P.audit_verify}
    ),
    Role.tenant_admin: frozenset(
        {
            P.alerts_read,
            P.map_read,
            P.location_edit,
            P.map_demo_read,
            P.alerts_create,
            P.alerts_decide,
            P.alerts_assign,
            P.alerts_plate_search,
            P.stats_read,
            P.cameras_read,
            P.cameras_manage,
            P.cameras_status_read,
            P.cases_annotate,
            P.cases_legal_hold,
            P.videos_read,
            P.videos_analyze,
            P.evidence_read,
            P.approvals_request,
            P.approvals_read_all,
            P.approvals_decide,
            P.users_manage,
            P.sessions_manage_all,
            P.audit_read,
            P.audit_verify,
            P.keys_rotate,
            P.service_accounts_manage,
            P.retention_manage,
            P.push_subscribe,
        }
    ),
    Role.operator: frozenset(
        {
            P.alerts_read,
            P.map_read,
            P.location_edit,
            P.map_demo_read,
            P.alerts_create,
            P.alerts_decide,
            P.alerts_assign,
            P.alerts_plate_search,
            P.stats_read,
            P.cameras_read,
            P.cameras_status_read,
            P.cases_annotate,
            P.videos_read,
            P.videos_analyze,
            P.evidence_read,
            P.approvals_request,
            P.push_subscribe,
        }
    ),
    Role.patrol: frozenset(
        {P.map_read, P.alerts_read, P.cameras_read, P.evidence_read, P.push_subscribe, P.patrol_respond}
    ),
    Role.auditor: frozenset({P.audit_read, P.audit_verify, P.cameras_status_read}),
}

# Roles a tenant admin may grant through invitations / role changes.
TENANT_ASSIGNABLE_ROLES = frozenset({Role.tenant_admin, Role.operator, Role.patrol, Role.auditor})


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def permissions_for(role: Role) -> list[str]:
    return sorted(p.value for p in ROLE_PERMISSIONS.get(role, frozenset()))


def scope_alerts[S: Select](stmt: S, principal: Principal) -> S:
    """Object-level filter for alerts. Tenant filtering is done by RLS; this adds role rules."""
    if principal.role == Role.patrol:
        return stmt.where(Alert.assigned_to == principal.user_id)
    return stmt


def scope_audit[S: Select](stmt: S, principal: Principal) -> S:
    """Object-level filter for audit history shown to alert readers: patrol users only see
    entries about alerts assigned to them (no other alerts, no logins of colleagues)."""
    if principal.role == Role.patrol:
        assigned = select(cast(Alert.id, String)).where(Alert.assigned_to == principal.user_id)
        return stmt.where(AuditLog.resource_type == "alerts", AuditLog.resource_id.in_(assigned))
    return stmt


def can_view_alert(principal: Principal, alert: Alert) -> bool:
    if not has_permission(principal.role, Permission.alerts_read):
        return False
    if principal.role == Role.patrol:
        return alert.assigned_to == principal.user_id
    return True
