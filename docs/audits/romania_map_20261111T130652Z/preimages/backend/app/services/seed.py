"""Development seed data: a platform tenant with a system admin, and two police units (Unit A,
Unit B) each with admin / operator / patrol / auditor users, cameras, alerts and evidence.

Everything is fake. Users are created without MFA so the first login walks through the
mandatory TOTP enrollment. Runs entirely through the restricted app role (RLS stays on).
"""

from __future__ import annotations

import random
import struct
import uuid
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.core import audit
from app.core.audit import AuditAction
from app.core.crypto import blind_index, encrypt_field, normalize_plate
from app.core.security import hash_password
from app.db import tenant_session
from app.models import Alert, Camera, Priority, Role, User
from app.services import evidence as evidence_service
from app.services.keys import ensure_tenant_keys, load_keyring
from app.services.tenants import create_tenant

PLATE_FIELD = "alerts.plate"


@dataclass
class SeededUser:
    tenant: str
    email: str
    role: str


UNITS = [
    ("Unit A - Highway Patrol North", "unit-a", "a"),
    ("Unit B - City Traffic South", "unit-b", "b"),
]
ROLES = [
    (Role.tenant_admin, "admin"),
    (Role.operator, "operator"),
    (Role.patrol, "patrol"),
    (Role.auditor, "auditor"),
]
CAMERAS = [
    ("A1 km 23 northbound", "A1 motorway, km 23, northbound", 44.512, 25.912),
    ("Ring road / Exit 4", "Ring road, exit 4 junction", 44.401, 26.004),
    ("Crosswalk Main St", "Main Street pedestrian crossing near school", 44.437, 26.097),
]
ALERTS = [
    (Priority.critical, "wrong_way", "Vehicle driving against traffic in lane 2"),
    (Priority.critical, "pedestrian_on_highway", "Pedestrian walking on the hard shoulder"),
    (Priority.high, "emergency_lane_stop", "Truck stopped in the emergency lane, hazards on"),
    (Priority.high, "excessive_speed", "Estimated 182 km/h in a 130 km/h zone"),
    (Priority.medium, "tailgating", "Following distance under 0.5 s for 12 s"),
    (Priority.medium, "hard_braking", "Sudden deceleration, possible near-miss"),
    (Priority.info, "congestion", "Queue forming, average speed 18 km/h"),
]


def fake_plate(rng: random.Random) -> str:
    letters = "ABCDEFGHJKLMNPRSTUVWXYZ"
    return (
        rng.choice(["B", "IF", "CJ", "TM", "IS"])
        + f"{rng.randint(10, 99)}"
        + "".join(rng.choice(letters) for _ in range(3))
    )


def make_png(width: int, height: int, *, redacted: bool, seed: int) -> bytes:
    """Draw a tiny synthetic 'road scene' PNG. The redacted variant greys out the plate box."""
    rng = random.Random(seed)  # noqa: S311 - synthetic images, not security relevant
    sky, road = (120, 160, 210), (70, 70, 75)
    car = (rng.randint(80, 220), rng.randint(20, 90), rng.randint(20, 90))
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            px = sky if y < height * 0.4 else road
            if height * 0.55 < y < height * 0.8 and width * 0.3 < x < width * 0.7:
                px = car
            if height * 0.7 < y < height * 0.77 and width * 0.43 < x < width * 0.57:
                px = (128, 128, 128) if redacted else (250, 250, 250)
            if (
                not redacted
                and height * 0.72 < y < height * 0.75
                and width * 0.45 < x < width * 0.55
            ):
                px = (20, 20, 20) if (x // 3) % 2 else (250, 250, 250)
            if y > height * 0.9 and (x // 12) % 2 == 0:
                px = (230, 230, 230)
            row += bytes(px)
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def tenant_id_for_slug(slug: str) -> uuid.UUID | None:
    with tenant_session() as db:
        value = db.execute(text("SELECT rs_tenant_id_by_slug(:s)"), {"s": slug}).scalar()
        return value if isinstance(value, uuid.UUID) else None


def seed(password: str, *, users_only: bool = False) -> list[SeededUser]:
    """Dev/demo tenants and one account per role. ``users_only`` skips the sample cameras,
    alerts and evidence (for a demo fed by the real pipeline)."""
    if get_settings().is_production:
        raise ValueError("Development seeding is forbidden in production")
    pw_hash = hash_password(password)
    created: list[SeededUser] = []
    rng = random.Random(2026)  # noqa: S311 - fake plates for dev data

    platform_id, platform_fresh = _ensure_tenant(
        "RoadSentinel Platform", "platform", is_platform=True
    )
    with tenant_session(platform_id) as db:
        ensure_tenant_keys(db, platform_id)
        _ensure_user(
            db,
            platform_id,
            "sysadmin@roadsentinel.local",
            "System Admin",
            Role.system_admin,
            pw_hash,
        )
        db.commit()
        if platform_fresh:
            audit.append(db, platform_id, AuditAction.tenant_created, details={"source": "seed"})
            db.commit()
    created.append(
        SeededUser("RoadSentinel Platform", "sysadmin@roadsentinel.local", Role.system_admin.value)
    )

    for name, slug, letter in UNITS:
        tenant_id, fresh = _ensure_tenant(name, slug)
        for role, prefix in ROLES:
            email = f"{prefix}.{letter}@roadsentinel.local"
            created.append(SeededUser(name, email, role.value))
        with tenant_session(tenant_id) as db:
            ensure_tenant_keys(db, tenant_id)
            users = {}
            for role, prefix in ROLES:
                email = f"{prefix}.{letter}@roadsentinel.local"
                u = _ensure_user(
                    db,
                    tenant_id,
                    email,
                    f"{prefix.title()} {letter.upper()}",
                    role,
                    pw_hash,
                )
                users[role] = u
            db.flush()
            # Existing tenants may be only partly seeded. Avoid duplicating demo data if any
            # camera already exists; users and missing keys above are repaired independently.
            if users_only or db.scalar(select(Camera.id).limit(1)) is not None:
                db.commit()
                if fresh:
                    audit.append(
                        db, tenant_id, AuditAction.tenant_created, details={"source": "seed"}
                    )
                    db.commit()
                continue
            cams = [
                Camera(
                    tenant_id=tenant_id,
                    name=f"{c[0]}",
                    location=c[1],
                    latitude=c[2],
                    longitude=c[3],
                )
                for c in CAMERAS
            ]
            db.add_all(cams)
            db.flush()
            keyring = load_keyring(db, tenant_id)
            now = datetime.now(UTC)
            for i, (prio, etype, desc) in enumerate(ALERTS):
                plate = normalize_plate(fake_plate(rng))
                alert = Alert(
                    tenant_id=tenant_id,
                    camera_id=cams[i % len(cams)].id,
                    priority=prio,
                    event_type=etype,
                    description=f"[{slug}] {desc}",
                    detected_at=now - timedelta(minutes=7 * i + 3),
                    plate_enc=encrypt_field(keyring, PLATE_FIELD, plate),
                    plate_bidx=blind_index(keyring, PLATE_FIELD, plate),
                    assigned_to=users[Role.patrol].id if i in (0, 2) else None,
                    details={"synthetic": True, "source": "app.services.seed"},
                )
                db.add(alert)
                db.flush()
                seed_n = zlib.crc32(f"{slug}-{i}".encode())
                evidence_service.ingest(
                    db,
                    keyring,
                    alert,
                    original=make_png(160, 96, redacted=False, seed=seed_n),
                    redacted=make_png(160, 96, redacted=True, seed=seed_n),
                    content_type="image/png",
                )
            db.commit()
            audit.append(db, tenant_id, AuditAction.tenant_created, details={"source": "seed"})
            db.commit()
    return created


def _ensure_user(
    db, tenant_id: uuid.UUID, email: str, display_name: str, role: Role, pw_hash: str
) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is not None:
        if user.tenant_id != tenant_id or user.role != role:
            raise ValueError(f"development account {email} belongs to an unexpected tenant or role")
        # Existing credentials, MFA, sessions and account state are never replaced by seed.
        # Password recovery is a separate explicit, audited operation.
        return user
    user = User(
        tenant_id=tenant_id,
        email=email,
        display_name=display_name,
        role=role,
        password_hash=pw_hash,
    )
    db.add(user)
    return user


def _ensure_tenant(name: str, slug: str, *, is_platform: bool = False) -> tuple[uuid.UUID, bool]:
    tenant_id = tenant_id_for_slug(slug)
    if tenant_id is not None:
        return tenant_id, False
    try:
        return create_tenant(name, slug, is_platform=is_platform), True
    except IntegrityError:
        # Another seed process may have created the same tenant between lookup and insert.
        existing = tenant_id_for_slug(slug)
        if existing is None:
            raise
        return existing, False
