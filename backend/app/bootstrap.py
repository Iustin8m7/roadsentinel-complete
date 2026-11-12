"""Create the database and its two roles. Needs a superuser connection; run once per environment.

* ``rs_owner``: owns the schema and runs migrations. It has BYPASSRLS so that the narrowly
  scoped SECURITY DEFINER lookup functions (login, refresh, invitation) can find a tenant
  before a tenant context exists. Never used by the API process.
* ``rs_app``: the only role the API uses. NOSUPERUSER, NOBYPASSRLS, owns nothing, so every
  query it runs is filtered by Row-Level Security (tables also use FORCE ROW LEVEL SECURITY).

Role names, passwords and the database name are taken from the connection URLs, so there is
a single source of truth (the environment).
"""

from __future__ import annotations

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url


def _plain(url: str) -> str:
    """SQLAlchemy URL -> libpq URL."""
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _ensure_role(cur: psycopg.Cursor, name: str, password: str, *, bypass_rls: bool) -> None:
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (name,))
    verb = "ALTER" if cur.fetchone() else "CREATE"
    attrs = "LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION"
    attrs += " BYPASSRLS" if bypass_rls else " NOBYPASSRLS"
    cur.execute(
        sql.SQL("{} ROLE {} WITH " + attrs + " PASSWORD {}").format(
            sql.SQL(verb), sql.Identifier(name), sql.Literal(password)
        )
    )
    # ALTER ROLE is intentional here: existing deployments may have created the migration role
    # before the pre-tenant SECURITY DEFINER functions relied on its BYPASSRLS attribute.
    cur.execute("SELECT rolbypassrls FROM pg_roles WHERE rolname = %s", (name,))
    actual = cur.fetchone()
    if actual is None or bool(actual[0]) != bypass_rls:
        raise RuntimeError(f"database role {name} has incorrect BYPASSRLS setting")


def bootstrap(admin_url: str, migrator_url: str, app_url: str) -> None:
    owner, app = make_url(migrator_url), make_url(app_url)
    if owner.database != app.database:
        raise ValueError("migrator and app URLs must point to the same database")
    if not owner.username or not owner.password or not app.username or not app.password:
        raise ValueError("migrator and app URLs must include username and password")
    db_name = owner.database
    assert db_name

    with psycopg.connect(_plain(admin_url), autocommit=True) as conn, conn.cursor() as cur:
        _ensure_role(cur, owner.username, owner.password, bypass_rls=True)
        _ensure_role(cur, app.username, app.password, bypass_rls=False)
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        if not cur.fetchone():
            cur.execute(
                sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(db_name), sql.Identifier(owner.username)
                )
            )
        cur.execute(
            sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(db_name))
        )
        cur.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(db_name), sql.Identifier(app.username)
            )
        )

    db_admin_url = make_url(admin_url).set(database=db_name).render_as_string(hide_password=False)
    with psycopg.connect(_plain(db_admin_url), autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            sql.SQL("ALTER SCHEMA public OWNER TO {}").format(sql.Identifier(owner.username))
        )
        cur.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        cur.execute(
            sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(app.username))
        )
