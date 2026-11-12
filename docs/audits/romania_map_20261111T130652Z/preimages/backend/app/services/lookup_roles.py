"""Administrator-only ownership setup for identifier-only pre-tenant lookups.

The NOLOGIN definer has BYPASSRLS but only SELECT on the columns these six functions
read. It owns no tables and has no members. Runtime accounts never inherit this role.
"""

from __future__ import annotations

import re

import psycopg
from psycopg import sql

SIGNATURES = (
    "rs_tenant_id_by_slug(text)",
    "rs_platform_tenant()",
    "rs_auth_find_user(text)",
    "rs_auth_find_refresh_tenant(text)",
    "rs_auth_find_invitation_tenant(text)",
    "rs_resource_tenant(text,uuid)",
)


def install_lookup_owner(conn: psycopg.Connection, app_role: str) -> str:
    """Call only with an already verified administrator connection, in a transaction."""
    role = app_role + "__lookup"
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", role):
        raise ValueError("Invalid dedicated lookup role name")
    cur = conn.cursor()
    cur.execute("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")
    if not cur.fetchone()[0]:
        raise PermissionError(
            "Lookup ownership setup requires an authorized database administrator"
        )
    cur.execute("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=%s", (app_role,))
    if cur.fetchone() != (False, False):
        raise ValueError("Runtime app role must remain NOSUPERUSER NOBYPASSRLS")
    cur.execute(
        "SELECT rolcanlogin,rolsuper,rolbypassrls,rolcreatedb,rolcreaterol"
        "e FROM pg_roles WHERE rolname=%s",
        (role,),
    )
    attributes = cur.fetchone()
    if attributes is None:
        cur.execute(
            sql.SQL(
                "CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHE"
                "RIT NOREPLICATION BYPASSRLS"
            ).format(sql.Identifier(role))
        )
    elif attributes != (False, False, True, False, False):
        raise ValueError("Existing dedicated lookup role has unexpected privileges")
    cur.execute(
        "SELECT 1 FROM pg_auth_members WHERE roleid=(SELECT oid FROM pg_ro"
        "les WHERE rolname=%s) OR member=(SELECT oid FROM pg_roles WHERE r"
        "olname=%s)",
        (role, role),
    )
    if cur.fetchone():
        raise ValueError("Dedicated lookup role must have no memberships or members")
    cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role)))
    columns = {
        "tenants": {"id", "slug", "is_platform", "created_at"},
        "users": {"id", "tenant_id", "email"},
        "refresh_tokens": {"tenant_id", "token_hash"},
        "invitations": {"tenant_id", "token_hash", "used_at", "revoked_at", "expires_at"},
    }
    cur.execute(
        "SELECT prosrc FROM pg_proc WHERE oid='public.rs_resource_tenant(text,uuid)'::regprocedure"
    )
    source = cur.fetchone()[0]
    match = re.search(r"p_table\s+NOT\s+IN\s*\((.*?)\)", source, re.I | re.S)
    if not match:
        raise ValueError("Unrecognized resource lookup allow-list")
    for table in re.findall(r"'([a-z_]+)'", match.group(1)):
        columns.setdefault(table, set()).update({"id", "tenant_id"})
    for table, names in columns.items():
        cur.execute(
            sql.SQL("GRANT SELECT ({}) ON TABLE public.{} TO {}").format(
                sql.SQL(",").join(map(sql.Identifier, sorted(names))),
                sql.Identifier(table),
                sql.Identifier(role),
            )
        )
    for signature in SIGNATURES:
        cur.execute(
            "SELECT p.prosecdef,p.proconfig FROM pg_proc p WHERE p.oid=%s::regprocedure",
            ("public." + signature,),
        )
        props = cur.fetchone()
        if not props or not props[0] or "search_path=public, pg_temp" not in (props[1] or []):
            raise ValueError(
                "Lookup function security/search_path differs from the reviewed contract"
            )
        # Signatures are constants, not caller-supplied identifiers.
        cur.execute(
            sql.SQL("ALTER FUNCTION public." + signature + " OWNER TO {}").format(
                sql.Identifier(role)
            )
        )
        cur.execute(sql.SQL("REVOKE ALL ON FUNCTION public." + signature + " FROM PUBLIC"))
        cur.execute(
            sql.SQL("GRANT EXECUTE ON FUNCTION public." + signature + " TO {}").format(
                sql.Identifier(app_role)
            )
        )
    cur.execute(
        "SELECT has_column_privilege(%s,'public.users','password_hash','SE"
        "LECT'),has_schema_privilege(%s,'public','CREATE')",
        (role, role),
    )
    if cur.fetchone() != (False, False):
        raise ValueError("Lookup role unexpectedly can read hashes or create schema objects")
    return role
