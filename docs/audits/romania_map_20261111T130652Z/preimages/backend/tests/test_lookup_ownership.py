"""Regression for the observed forced-RLS definer-owner failure; disposable DB only."""

from sqlalchemy import select

from app.core.security import hash_password, verify_password
from app.db import tenant_session
from app.models import User
from app.services.seed import seed, tenant_id_for_slug
from tests.conftest import admin_conn


def test_dedicated_lookup_owner_is_nologin_and_cannot_read_passwords():
    with admin_conn() as conn:
        row = conn.execute(
            "SELECT r.rolname,r.rolcanlogin,r.rolsuper,r.rolbypassrls FROM pg_"
            "proc p JOIN pg_roles r ON r.oid=p.proowner WHERE p.oid='rs_tenant"
            "_id_by_slug(text)'::regprocedure"
        ).fetchone()
        assert row[1:] == (False, False, True)
        role = row[0]
        assert conn.execute(
            "SELECT has_column_privilege(%s,'users','password_hash','SELECT'),"
            "has_schema_privilege(%s,'public','CREATE')",
            (role, role),
        ).fetchone() == (False, False)
        assert (
            conn.execute(
                "SELECT count(*) FROM pg_auth_members WHERE roleid=(SELECT oid FRO"
                "M pg_roles WHERE rolname=%s)",
                (role,),
            ).fetchone()[0]
            == 0
        )


def test_existing_slug_becomes_invisible_without_owner_bypass_and_recovers():
    from psycopg import sql

    seed("Known-Development-Passphrase-2026!", users_only=True)
    expected = tenant_id_for_slug("platform")
    assert expected is not None
    with admin_conn() as conn:
        role = conn.execute(
            "SELECT proowner::regrole::text FROM pg_proc WHERE oid='rs_tenant_"
            "id_by_slug(text)'::regprocedure"
        ).fetchone()[0]
        try:
            conn.execute(sql.SQL("ALTER ROLE {} NOBYPASSRLS").format(sql.Identifier(role)))
            assert tenant_id_for_slug("platform") is None
            assert (
                conn.execute("SELECT count(*) FROM tenants WHERE slug='platform'").fetchone()[0]
                == 1
            )
        finally:
            conn.execute(sql.SQL("ALTER ROLE {} BYPASSRLS").format(sql.Identifier(role)))
    assert tenant_id_for_slug("platform") == expected
    seed("Known-Development-Passphrase-2026!", users_only=True)
    assert tenant_id_for_slug("platform") == expected


def test_repeated_seed_preserves_existing_password_and_identity():
    initial = "Initial-Development-Passphrase-2026!"
    existing = "An-Existing-Account-Password-2026!"
    seed(initial, users_only=True)
    tid = tenant_id_for_slug("unit-a")
    with tenant_session(tid) as db:
        user = db.scalar(select(User).where(User.email == "operator.a@roadsentinel.local"))
        user.password_hash = hash_password(existing)
        db.commit()
        uid = user.id
        previous_hash = user.password_hash
    seed(initial, users_only=True)
    with tenant_session(tid) as db:
        user = db.get(User, uid)
        assert user.password_hash == previous_hash
        assert verify_password(user.password_hash, existing)
        assert not verify_password(user.password_hash, initial)
