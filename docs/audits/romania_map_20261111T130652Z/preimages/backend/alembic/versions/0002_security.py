"""Security layer: Row-Level Security, app-role grants, append-only audit log, auth lookups.

* Every tenant-scoped table gets ENABLE + FORCE ROW LEVEL SECURITY and a single policy that
  compares ``tenant_id`` with the transaction-local setting ``app.tenant_id``. A missing
  setting yields NULL, which matches nothing: the database fails closed.
* The runtime role (``rs_app``) receives only DML grants. On ``audit_log`` it can only SELECT
  and INSERT; a trigger additionally blocks UPDATE/DELETE/TRUNCATE for every role.
* Composite foreign keys (tenant_id, x_id) stop a row from referencing another tenant's row,
  because plain FK checks are not subject to RLS.
* Three SECURITY DEFINER functions answer the only questions that must be asked *before* a
  tenant is known (login by e-mail, refresh by token hash, invitation by token hash). They
  return identifiers only, never secrets. A fourth one (``rs_resource_tenant``) lets the API
  detect cross-tenant probing so it can be audited; its answer never reaches the client.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-17
"""

import os
from collections.abc import Sequence

from sqlalchemy.engine import make_url

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_TABLES = (
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
)

# (child table, child column, parent table, constraint name)
TENANT_FKS = (
    ("alerts", "camera_id", "cameras", "fk_alerts_tenant_camera"),
    ("alerts", "assigned_to", "users", "fk_alerts_tenant_assignee"),
    ("evidence", "alert_id", "alerts", "fk_evidence_tenant_alert"),
    ("user_sessions", "user_id", "users", "fk_user_sessions_tenant_user"),
    ("refresh_tokens", "session_id", "user_sessions", "fk_refresh_tokens_tenant_session"),
    ("recovery_codes", "user_id", "users", "fk_recovery_codes_tenant_user"),
    ("approval_requests", "requester_id", "users", "fk_approval_requests_tenant_requester"),
    ("push_subscriptions", "user_id", "users", "fk_push_subscriptions_tenant_user"),
)


def _app_role() -> str:
    url = os.environ.get("RS_DATABASE_URL")
    name = make_url(url).username if url else None
    name = name or "rs_app"
    if not name.replace("_", "").isalnum():
        raise ValueError("unexpected app role name")
    return name


def upgrade() -> None:
    app = _app_role()

    op.execute("""
        CREATE FUNCTION rs_current_tenant() RETURNS uuid
        LANGUAGE sql STABLE PARALLEL SAFE
        AS $$ SELECT nullif(current_setting('app.tenant_id', true), '')::uuid $$
    """)

    for parent in {p for _, _, p, _ in TENANT_FKS}:
        op.create_unique_constraint(f"uq_{parent}_tenant_id_id", parent, ["tenant_id", "id"])
    for child, col, parent, name in TENANT_FKS:
        op.create_foreign_key(name, child, parent, ["tenant_id", col], ["tenant_id", "id"])

    # Row-Level Security.
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenants FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON tenants
        USING (id = rs_current_tenant()) WITH CHECK (id = rs_current_tenant())
    """)
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id = rs_current_tenant())
            WITH CHECK (tenant_id = rs_current_tenant())
        """)

    # Grants for the runtime role.
    op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {app}")
    for table in ("tenants", *TENANT_TABLES):
        if table == "audit_log":
            op.execute(f"GRANT SELECT, INSERT ON audit_log TO {app}")
        elif table == "tenant_keys":
            op.execute(f"GRANT SELECT, INSERT, UPDATE ON tenant_keys TO {app}")
        else:
            op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO {app}")
    op.execute(f"GRANT USAGE, SELECT ON SEQUENCE audit_log_id_seq TO {app}")
    op.execute(f"GRANT EXECUTE ON FUNCTION rs_current_tenant() TO {app}")

    # Append-only audit log, enforced for every role (including the owner).
    op.execute("""
        CREATE FUNCTION rs_audit_log_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log is append-only (% blocked)', TG_OP
                USING ERRCODE = 'insufficient_privilege';
        END $$
    """)
    op.execute("""
        CREATE TRIGGER audit_log_no_update_delete BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION rs_audit_log_immutable()
    """)
    op.execute("""
        CREATE TRIGGER audit_log_no_truncate BEFORE TRUNCATE ON audit_log
        FOR EACH STATEMENT EXECUTE FUNCTION rs_audit_log_immutable()
    """)

    # Pre-tenant lookups (SECURITY DEFINER, fixed search_path, identifiers only).
    op.execute("""
        CREATE FUNCTION rs_auth_find_user(p_email text)
        RETURNS TABLE (user_id uuid, tenant_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$ SELECT u.id, u.tenant_id FROM users u WHERE u.email = lower(p_email) $$
    """)
    op.execute("""
        CREATE FUNCTION rs_auth_find_refresh_tenant(p_hash text) RETURNS uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$ SELECT r.tenant_id FROM refresh_tokens r WHERE r.token_hash = p_hash $$
    """)
    op.execute("""
        CREATE FUNCTION rs_auth_find_invitation_tenant(p_hash text) RETURNS uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
            SELECT i.tenant_id FROM invitations i
            WHERE i.token_hash = p_hash AND i.used_at IS NULL AND i.revoked_at IS NULL
              AND i.expires_at > now()
        $$
    """)
    op.execute("""
        CREATE FUNCTION rs_platform_tenant() RETURNS uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$ SELECT t.id FROM tenants t WHERE t.is_platform ORDER BY t.created_at LIMIT 1 $$
    """)
    op.execute("""
        CREATE FUNCTION rs_tenant_id_by_slug(p_slug text) RETURNS uuid
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$ SELECT t.id FROM tenants t WHERE t.slug = p_slug $$
    """)
    # Used only to *detect and audit* cross-tenant probing after a lookup returned nothing.
    # The caller always answers 404; the owning tenant id is written to the audit log only.
    allowed = ", ".join(
        f"'{t}'"
        for t in (
            "users",
            "cameras",
            "alerts",
            "evidence",
            "approval_requests",
            "user_sessions",
            "invitations",
        )
    )
    resource_tenant_sql = f"""
        CREATE FUNCTION rs_resource_tenant(p_table text, p_id uuid) RETURNS uuid
        LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
        DECLARE result uuid;
        BEGIN
            IF p_table NOT IN ({allowed}) THEN
                RAISE EXCEPTION 'table not allowed';
            END IF;
            EXECUTE format('SELECT tenant_id FROM %I WHERE id = $1', p_table)
                INTO result USING p_id;
            RETURN result;
        END $$
    """  # noqa: S608 - fixed allow-list built above, no user input
    op.execute(resource_tenant_sql)
    for fn in (
        "rs_tenant_id_by_slug(text)",
        "rs_resource_tenant(text, uuid)",
        "rs_auth_find_user(text)",
        "rs_auth_find_refresh_tenant(text)",
        "rs_auth_find_invitation_tenant(text)",
        "rs_platform_tenant()",
    ):
        op.execute(f"REVOKE ALL ON FUNCTION {fn} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {fn} TO {app}")


def downgrade() -> None:
    for fn in (
        "rs_tenant_id_by_slug(text)",
        "rs_resource_tenant(text, uuid)",
        "rs_platform_tenant()",
        "rs_auth_find_invitation_tenant(text)",
        "rs_auth_find_refresh_tenant(text)",
        "rs_auth_find_user(text)",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {fn}")
    op.execute("DROP TRIGGER IF EXISTS audit_log_no_truncate ON audit_log")
    op.execute("DROP TRIGGER IF EXISTS audit_log_no_update_delete ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS rs_audit_log_immutable()")
    for table in ("tenants", *TENANT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    for child, _, _, name in TENANT_FKS:
        op.drop_constraint(name, child, type_="foreignkey")
    for parent in {p for _, _, p, _ in TENANT_FKS}:
        op.drop_constraint(f"uq_{parent}_tenant_id_id", parent, type_="unique")
    op.execute("DROP FUNCTION IF EXISTS rs_current_tenant()")
