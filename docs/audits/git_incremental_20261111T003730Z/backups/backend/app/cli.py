"""Operational commands: ``python -m app.cli <command>``.

bootstrap-db        create roles + database (needs RS_ADMIN_DATABASE_URL, superuser)
migrate             alembic upgrade head (needs RS_MIGRATOR_DATABASE_URL)
seed                create dev tenants/users/data (dev only, needs RS_SEED_PASSWORD)
rotate-tenant-key   new DEK version for a tenant and re-encrypt its fields
rewrap-keys         re-wrap all tenant keys under the current master key version
verify-audit        verify a tenant's audit chain
create-service-account  create a pipeline identity and its first HMAC key (secret shown once)
register-camera     create or update a camera by slug (the pipeline's camera id)
set-mfa-exempt      allow (or with --off, revoke) password-only login for one account
purge-nonces        delete expired ingestion nonces
purge-evidence      retention job: delete evidence past the tenant policy (--dry-run first)
reset-account       break-glass account recovery: prints a single-use reset token (audited)
demo-accounts       local/demo only: admin@/operator@ accounts (never in production)
demo-alert          create a fake alert and send the generic push (dev only)
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

from app.config import get_settings


def _tenant(slug: str) -> uuid.UUID:
    from app.services.seed import tenant_id_for_slug

    tid = tenant_id_for_slug(slug)
    if tid is None:
        sys.exit(f"unknown tenant slug: {slug}")
    return tid


def cmd_bootstrap(_: argparse.Namespace) -> None:
    from app.bootstrap import bootstrap

    s = get_settings()
    if not s.admin_database_url or not s.migrator_database_url:
        sys.exit("RS_ADMIN_DATABASE_URL and RS_MIGRATOR_DATABASE_URL are required")
    bootstrap(
        s.admin_database_url.get_secret_value(),
        s.migrator_database_url.get_secret_value(),
        s.database_url.get_secret_value(),
    )
    print("database and roles ready")


def cmd_migrate(_: argparse.Namespace) -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    command.upgrade(cfg, "head")


def cmd_seed(args: argparse.Namespace) -> None:
    from app.services.seed import seed

    s = get_settings()
    if s.is_production:
        sys.exit("refusing to seed in production")
    if not s.seed_password:
        sys.exit("RS_SEED_PASSWORD is required (run scripts/gen_dev_secrets.py)")
    users = seed(s.seed_password.get_secret_value(), users_only=args.users_only)
    print("Development accounts (new accounts use RS_SEED_PASSWORD; existing passwords/MFA are preserved):")
    for u in users:
        print(f"  {u.role:<13} {u.email:<34} {u.tenant}")


def cmd_rotate(args: argparse.Namespace) -> None:
    from app.core import audit
    from app.core.audit import AuditAction
    from app.db import tenant_session
    from app.services.keys import rotate_data_key

    tid = _tenant(args.tenant)
    with tenant_session(tid) as db:
        version = rotate_data_key(db, tid, reencrypt=not args.no_reencrypt)
        db.commit()
    audit.record(tid, AuditAction.key_rotated, details={"new_version": version, "source": "cli"})
    print(f"tenant {args.tenant}: active data key is now version {version}")


def cmd_rewrap(args: argparse.Namespace) -> None:
    from app.core import audit
    from app.core.audit import AuditAction
    from app.db import tenant_session
    from app.services.keys import rewrap_tenant_keys

    for slug in args.tenant:
        tid = _tenant(slug)
        with tenant_session(tid) as db:
            count = rewrap_tenant_keys(db, tid)
            db.commit()
        master = get_settings().master_key_current
        audit.record(
            tid, AuditAction.keys_rewrapped, details={"keys": count, "master_version": master}
        )
        print(f"tenant {slug}: re-wrapped {count} keys under master key v{master}")


def cmd_demo_alert(args: argparse.Namespace) -> None:
    """Create a fake alert (dev only) and send the generic push notification."""
    from datetime import UTC, datetime

    from sqlalchemy import select

    from app.core import audit
    from app.core.audit import AuditAction
    from app.db import tenant_session
    from app.models import Alert, Camera, Priority
    from app.services.push import notify_new_alert

    if get_settings().is_production:
        sys.exit("refusing to create demo data in production")
    tid = _tenant(args.tenant)
    with tenant_session(tid) as db:
        camera = db.scalars(select(Camera).limit(1)).first()
        if camera is None:
            sys.exit("tenant has no cameras (run the seed first)")
        alert = Alert(
            tenant_id=tid,
            camera_id=camera.id,
            priority=Priority(args.priority),
            event_type="demo_event",
            description="Demo alert created from the CLI",
            detected_at=datetime.now(UTC),
        )
        db.add(alert)
        db.commit()
        alert_id = alert.id
    audit.record(
        tid,
        AuditAction.alert_created,
        resource_type="alerts",
        resource_id=alert_id,
        details={"priority": args.priority, "source": "cli"},
    )
    thread = notify_new_alert(tid, Priority(args.priority), None)
    if thread:
        thread.join(timeout=15)
    print(f"created alert {alert_id} ({args.priority}); push {'sent' if thread else 'disabled'}")


def cmd_service_account(args: argparse.Namespace) -> None:
    from app.core import audit
    from app.core.audit import AuditAction
    from app.db import tenant_session
    from app.services import ingest_auth
    from app.services.keys import load_keyring

    tid = _tenant(args.tenant)
    with tenant_session(tid) as db:
        account = ingest_auth.create_account(db, tid, args.name)
        issued = ingest_auth.issue_key(db, load_keyring(db, tid), account)
        db.commit()
        account_id = account.id
    audit.record(
        tid,
        AuditAction.service_account_created,
        resource_type="service_accounts",
        resource_id=account_id,
        details={"name": args.name, "source": "cli", "key_id": issued.key_id},
    )
    print(f"service account {args.name} ({account_id}) for tenant {args.tenant}")
    print(f"RS_INGEST_KEY_ID={issued.key_id}")
    print(f"RS_INGEST_SECRET={issued.secret}")
    print("The secret is shown only now and cannot be retrieved later.")


def cmd_register_camera(args: argparse.Namespace) -> None:
    import re

    from sqlalchemy import select

    from app.core import audit
    from app.core.audit import AuditAction
    from app.db import tenant_session
    from app.models import Camera

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", args.slug):
        sys.exit("slug must match ^[A-Za-z0-9_-]{1,64}$ (same as cameras/*.yaml 'id')")
    if args.timezone:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        try:
            ZoneInfo(args.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            sys.exit(f"unknown timezone: {args.timezone} (use an IANA name, e.g. Europe/Bucharest)")
    tid = _tenant(args.tenant)
    with tenant_session(tid) as db:
        camera = db.scalar(select(Camera).where(Camera.slug == args.slug))
        created = camera is None
        if camera is None:
            camera = Camera(tenant_id=tid, slug=args.slug, name=args.name, location=args.location)
            db.add(camera)
        else:
            camera.name, camera.location = args.name, args.location
        if args.timezone:
            camera.timezone = args.timezone
        db.commit()
        camera_id = camera.id
    if created:
        audit.record(
            tid,
            AuditAction.camera_created,
            resource_type="cameras",
            resource_id=camera_id,
            details={"slug": args.slug, "source": "cli"},
        )
    print(
        f"{'created' if created else 'updated'} camera {args.slug} ({camera_id}) in {args.tenant}"
    )


def cmd_set_mfa_exempt(args: argparse.Namespace) -> None:
    from sqlalchemy import select

    from app.core import audit
    from app.core.audit import AuditAction
    from app.db import tenant_session
    from app.models import User

    tid = _tenant(args.tenant)
    with tenant_session(tid) as db:
        user = db.scalar(select(User).where(User.email == args.email.strip().lower()))
        if user is None:
            sys.exit(f"no user {args.email} in {args.tenant}")
        user.mfa_exempt = not args.off
        db.commit()
        user_id = user.id
    audit.record(
        tid,
        AuditAction.user_updated,
        resource_type="users",
        resource_id=user_id,
        details={"mfa_exempt": not args.off, "source": "cli"},
    )
    print(f"{args.email}: mfa_exempt={'false' if args.off else 'true'}")


def cmd_purge_nonces(_: argparse.Namespace) -> None:
    from sqlalchemy import text

    from app.db import tenant_session
    from app.services.ingest_auth import purge_expired_nonces

    total = 0
    with tenant_session() as db:
        tenants = [r[0] for r in db.execute(text("SELECT id FROM tenants")).all()]
    for tid in tenants:
        with tenant_session(tid) as db:
            total += purge_expired_nonces(db)
            db.commit()
    print(f"purged {total} expired nonces")


def cmd_verify(args: argparse.Namespace) -> None:
    from app.core.audit import verify_chain
    from app.db import tenant_session

    tid = _tenant(args.tenant)
    with tenant_session(tid) as db:
        result = verify_chain(db, tid)
    print(result)
    sys.exit(0 if result.ok else 1)


def cmd_anchor_audit(args: argparse.Namespace) -> None:
    """Sign the verified current chain head to a local checkpoint file."""
    from app.core.audit import GENESIS_HASH, verify_chain
    from app.core.audit_anchor import LocalFileAnchor, public_key_fingerprint
    from app.db import tenant_session

    tid = _tenant(args.tenant)
    with tenant_session(tid) as db:
        result = verify_chain(db, tid)
    if not result.ok:
        sys.exit(f"refusing to anchor invalid audit chain at seq {result.first_broken_seq}")
    checkpoint = LocalFileAnchor(args.anchor_file, args.signing_key).publish(
        tid, result.checked, result.head_hash or GENESIS_HASH
    )
    public_file = Path(args.signing_key).with_suffix(Path(args.signing_key).suffix + ".pub")
    print(
        f"tenant {args.tenant}: anchored seq={checkpoint.sequence} "
        f"head={checkpoint.head_hash} public_key_sha256={public_key_fingerprint(public_file)}"
    )


def cmd_verify_audit_anchor(args: argparse.Namespace) -> None:
    """Verify signed checkpoints and confirm the latest one is in this verified DB chain."""
    from sqlalchemy import select

    from app.core.audit import GENESIS_HASH, verify_chain
    from app.core.audit_anchor import verify_anchor_file
    from app.db import tenant_session
    from app.models import AuditLog

    tid = _tenant(args.tenant)
    checkpoints = verify_anchor_file(args.anchor_file, args.public_key)
    checkpoint = next((item for item in reversed(checkpoints) if item.tenant_id == str(tid)), None)
    if checkpoint is None:
        sys.exit("no signed checkpoint exists for this tenant")
    with tenant_session(tid) as db:
        chain = verify_chain(db, tid)
        stored_head = (
            GENESIS_HASH
            if checkpoint.sequence == 0
            else db.scalar(
                select(AuditLog.entry_hash).where(
                    AuditLog.tenant_id == tid, AuditLog.seq == checkpoint.sequence
                )
            )
        )
    if not chain.ok:
        sys.exit(f"database audit chain is invalid at seq {chain.first_broken_seq}")
    if chain.checked < checkpoint.sequence or stored_head != checkpoint.head_hash:
        sys.exit("signed checkpoint does not match the verified database chain")
    print(
        f"tenant {args.tenant}: signature and chain match through seq={checkpoint.sequence}; "
        f"database currently verifies {chain.checked} entries"
    )


def cmd_demo_accounts(args: argparse.Namespace) -> None:
    """Local/demo only: create or reset two accounts (admin@ and operator@roadsentinel.local).

    Refuses to run in production. Without ``--password`` a random one is generated and printed
    once. MFA stays mandatory; ``--exempt-mfa`` additionally flags the accounts, which only has
    an effect when RS_MFA_EXEMPTION_ENABLED=true in a non-production environment.
    With ``--only-demo`` every other user of the platform tenants is deactivated (not deleted,
    so the audit chain keeps its actors).
    """
    import secrets

    from sqlalchemy import select

    from app.core.security import hash_password, password_policy_errors
    from app.db import tenant_session
    from app.models import Role, User
    from app.services.seed import tenant_id_for_slug

    if get_settings().is_production:
        sys.exit("demo-accounts is disabled in production (RS_ENV=production)")
    generated = args.password is None
    password = secrets.token_urlsafe(18) if generated else args.password
    errors = password_policy_errors(password)
    if errors:
        sys.exit("password rejected: " + "; ".join(errors))
    tenant_id = tenant_id_for_slug(args.tenant)
    if tenant_id is None:
        sys.exit(f"unknown tenant {args.tenant!r} (run the seed or create the unit first)")
    pw_hash = hash_password(password)
    keep = {
        "admin@roadsentinel.local": (Role.tenant_admin, "Administrator"),
        "operator@roadsentinel.local": (Role.operator, "Operator"),
    }
    with tenant_session(tenant_id) as db:
        users = {u.email: u for u in db.scalars(select(User))}
        for email, (role, name) in keep.items():
            u = users.get(email) or User(
                tenant_id=tenant_id, email=email, display_name=name, role=role
            )
            u.role, u.display_name, u.password_hash = role, name, pw_hash
            u.is_active = True
            u.mfa_exempt = bool(args.exempt_mfa)
            u.failed_login_count, u.locked_until = 0, None
            db.add(u)
        db.commit()
    if args.only_demo:
        for slug in ("platform", "unit-a", "unit-b", args.tenant):
            tid = tenant_id_for_slug(slug)
            if tid is None:
                continue
            with tenant_session(tid) as db:
                for u in db.scalars(select(User).where(User.email.not_in(list(keep)))):
                    u.is_active = False
                db.commit()
    mfa = (
        "password-only ONLY if RS_MFA_EXEMPTION_ENABLED=true (local, non-production)"
        if args.exempt_mfa
        else "MFA required"
    )
    print(f"demo accounts in {args.tenant}: admin@ / operator@roadsentinel.local ({mfa})")
    if generated:
        print(f"one-time password (shown once, not stored): {password}")


def cmd_reset_account(args: argparse.Namespace) -> None:
    """Break-glass account recovery (no second admin available, or a system admin account).

    Needs database access, i.e. an operator of the deployment, and is audited. Prints a single-use
    token ONCE; MFA stays mandatory (with --reset-mfa it must be enrolled again)."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from app.core import audit
    from app.core.audit import AuditAction
    from app.core.crypto import token_hash
    from app.core.security import random_token
    from app.db import tenant_session
    from app.models import Invitation, User

    tenant_id = _tenant(args.tenant)
    with tenant_session(tenant_id) as db:
        user = db.scalars(select(User).where(User.email == args.email.strip().lower())).first()
        if user is None or not user.is_active:
            sys.exit("no such active account in this tenant")
        token = random_token(32)
        inv = Invitation(
            tenant_id=tenant_id,
            email=user.email,
            role=user.role,
            token_hash=token_hash(token),
            kind="reset",
            user_id=user.id,
            reset_mfa=bool(args.reset_mfa),
            expires_at=datetime.now(UTC)
            + timedelta(seconds=get_settings().reset_token_ttl_seconds),
        )
        db.add(inv)
        db.commit()
        inv_id, uid = inv.id, user.id
    audit.record(
        tenant_id,
        AuditAction.account_reset_issued,
        actor_id=None,
        resource_type="users",
        resource_id=uid,
        details={"source": "cli", "reset_mfa": bool(args.reset_mfa), "invitation_id": str(inv_id)},
    )
    minutes = get_settings().reset_token_ttl_seconds // 60
    print(f"single-use token (shown once, valid {minutes} min): {token}")
    print("hand it to the user; they open /reset#<token> and choose a new password")


def cmd_purge_evidence(args: argparse.Namespace) -> None:
    """Scheduled retention job (cron): `purge-evidence --tenant unit-a unit-b [--dry-run]`.
    Audited per tenant; items of alerts under legal hold are never purged."""
    from sqlalchemy import select

    from app.db import tenant_session
    from app.models import Tenant
    from app.services import retention

    ids = [_tenant(slug) for slug in args.tenant]
    for tid in ids:
        with tenant_session(tid) as db:
            name = db.scalar(select(Tenant.name).where(Tenant.id == tid))
            rep = retention.purge(db, tid, dry_run=args.dry_run, actor_id=None, source="cli")
        mode = "DRY RUN" if args.dry_run else "PURGED"
        print(
            f"{name}: {mode} candidates={rep.candidates} purged={rep.purged} "
            f"held={rep.held_skipped} errors={rep.errors}"
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("bootstrap-db").set_defaults(func=cmd_bootstrap)
    sub.add_parser("migrate").set_defaults(func=cmd_migrate)
    p = sub.add_parser("seed")
    p.add_argument("--users-only", action="store_true", help="accounts only, no sample alerts")
    p.set_defaults(func=cmd_seed)
    p = sub.add_parser("rotate-tenant-key")
    p.add_argument("--tenant", required=True, help="tenant slug, e.g. unit-a")
    p.add_argument("--no-reencrypt", action="store_true")
    p.set_defaults(func=cmd_rotate)
    p = sub.add_parser("rewrap-keys")
    p.add_argument("--tenant", nargs="+", required=True)
    p.set_defaults(func=cmd_rewrap)
    p = sub.add_parser("demo-alert")
    p.add_argument("--tenant", required=True)
    p.add_argument("--priority", default="critical", choices=["critical", "high", "medium", "info"])
    p.set_defaults(func=cmd_demo_alert)
    p = sub.add_parser("create-service-account")
    p.add_argument("--tenant", required=True)
    p.add_argument("--name", required=True)
    p.set_defaults(func=cmd_service_account)
    p = sub.add_parser("register-camera")
    p.add_argument("--tenant", required=True)
    p.add_argument("--slug", required=True, help="camera id used by the pipeline")
    p.add_argument("--name", required=True)
    p.add_argument("--location", required=True)
    p.add_argument("--timezone", help="IANA zone, default Europe/Bucharest")
    p.set_defaults(func=cmd_register_camera)
    p = sub.add_parser("set-mfa-exempt")
    p.add_argument("--tenant", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--off", action="store_true", help="require MFA again")
    p.set_defaults(func=cmd_set_mfa_exempt)
    sub.add_parser("purge-nonces").set_defaults(func=cmd_purge_nonces)
    p = sub.add_parser("demo-accounts")
    p.add_argument("--tenant", default="unit-a")
    p.add_argument("--password", help="omit to generate a random one-time password")
    p.add_argument("--exempt-mfa", action="store_true", help="flag accounts mfa_exempt (demo only)")
    p.add_argument("--only-demo", action="store_true", help="deactivate every other user")
    p.set_defaults(func=cmd_demo_accounts)
    p = sub.add_parser("purge-evidence")
    p.add_argument("--tenant", nargs="+", required=True, help="tenant slug(s)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_purge_evidence)
    p = sub.add_parser("reset-account")
    p.add_argument("--tenant", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--reset-mfa", action="store_true", help="also remove TOTP and recovery codes")
    p.set_defaults(func=cmd_reset_account)
    p = sub.add_parser("verify-audit")
    p.add_argument("--tenant", required=True)
    p.set_defaults(func=cmd_verify)
    p = sub.add_parser("anchor-audit")
    p.add_argument("--tenant", required=True)
    p.add_argument("--anchor-file", required=True)
    p.add_argument("--signing-key", required=True, help="local Ed25519 key file; created mode 0600")
    p.set_defaults(func=cmd_anchor_audit)
    p = sub.add_parser("verify-audit-anchor")
    p.add_argument("--tenant", required=True)
    p.add_argument("--anchor-file", required=True)
    p.add_argument("--public-key", required=True, help="public key file for separate custody")
    p.set_defaults(func=cmd_verify_audit_anchor)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
