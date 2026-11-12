"""Refuse to start with an insecure production configuration.

Checked at application start-up when ``APP_ENV=prod``. Each problem is reported (without the
secret value) and the process exits instead of running half-protected.
"""

from __future__ import annotations

import base64
import binascii
import math
from collections import Counter

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.config import Settings

MIN_SECRET_CHARS = 32

# Values that must never reach production (placeholders, documentation examples, test fixtures).
KNOWN_WEAK_VALUES = frozenset(
    {
        "__generate__",
        "changeme",
        "change-me",
        "secret",
        "password",
        "development",
        "dev",
        "test",
        "jwt-secret",
        "supersecret",
        "insecure",
        "roadsentinel",
    }
)
# Base64 encodings of trivially weak 32-byte keys (all zeros, all 0xff, 0x00..0x1f).
KNOWN_WEAK_KEYS = frozenset(
    base64.b64encode(k).decode()
    for k in (bytes(32), b"\xff" * 32, bytes(range(32)), b"A" * 32, b"0" * 32)
)


class InsecureConfigurationError(RuntimeError):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("refusing to start in production: " + "; ".join(problems))
        self.problems = problems


def _entropy_bits_per_char(value: str) -> float:
    counts = Counter(value)
    return -sum(c / len(value) * math.log2(c / len(value)) for c in counts.values())


def _check_secret(name: str, value: str, problems: list[str]) -> None:
    lowered = value.strip().lower()
    if not value:
        problems.append(f"{name} is missing")
    elif lowered in KNOWN_WEAK_VALUES or any(w in lowered for w in ("changeme", "__generate__")):
        problems.append(f"{name} is a known default/placeholder value")
    elif len(value) < MIN_SECRET_CHARS:
        problems.append(f"{name} is shorter than {MIN_SECRET_CHARS} characters")
    elif _entropy_bits_per_char(value) < 3.0:
        problems.append(f"{name} has too little entropy")


def _check_master_keys(spec: str, problems: list[str]) -> None:
    if not spec.strip():
        problems.append("RS_MASTER_KEYS is missing")
        return
    for part in spec.split(","):
        _, _, b64 = part.strip().partition(":")
        try:
            raw = base64.b64decode(b64, validate=True)
        except (binascii.Error, ValueError):
            problems.append("RS_MASTER_KEYS contains an invalid key")
            continue
        if len(raw) != 32:
            problems.append("RS_MASTER_KEYS keys must be 32 bytes")
        elif b64 in KNOWN_WEAK_KEYS or len(set(raw)) < 8:
            problems.append("RS_MASTER_KEYS contains a known weak key")


def config_problems(settings: Settings) -> list[str]:
    """Static checks (no I/O)."""
    problems: list[str] = []
    _check_secret("RS_JWT_SECRET", settings.jwt_secret.get_secret_value(), problems)
    _check_secret("RS_URL_SIGNING_KEY", settings.url_signing_key.get_secret_value(), problems)
    if settings.jwt_secret.get_secret_value() == settings.url_signing_key.get_secret_value():
        problems.append("RS_JWT_SECRET and RS_URL_SIGNING_KEY must differ")
    _check_master_keys(settings.master_keys.get_secret_value(), problems)
    if settings.debug:
        problems.append("RS_DEBUG must be false")
    if not settings.cookie_secure:
        problems.append("RS_COOKIE_SECURE must be true")
    if not settings.public_origin.startswith("https://"):
        problems.append("RS_PUBLIC_ORIGIN must be https")
    for origin in settings.cors_origin_list:
        if "*" in origin:
            problems.append("RS_CORS_ORIGINS must not contain wildcards")
        elif not origin.startswith("https://"):
            problems.append("RS_CORS_ORIGINS must only contain https origins")
    if settings.mfa_exemption_enabled:
        problems.append("RS_MFA_EXEMPTION_ENABLED must be false in production")
    if settings.seed_password is not None and settings.seed_password.get_secret_value():
        problems.append("RS_SEED_PASSWORD must not be set in production")
    if settings.admin_database_url is not None:
        problems.append("RS_ADMIN_DATABASE_URL (superuser) must not be given to the API process")
    return problems


def database_role_problems(engine: Engine) -> list[str]:
    """The runtime role must not be able to bypass Row-Level Security."""
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT rolsuper, rolbypassrls, "
                "(SELECT count(*) FROM pg_tables WHERE schemaname = 'public' "
                " AND tableowner = current_user) "
                "FROM pg_roles WHERE rolname = current_user"
            )
        ).one()
    problems = []
    if row[0]:
        problems.append("database role is a superuser")
    if row[1]:
        problems.append("database role has BYPASSRLS")
    if row[2]:
        problems.append("database role owns tables (RLS is bypassed for owners without FORCE)")
    return problems


def enforce_production_safety(settings: Settings, engine: Engine) -> None:
    if not settings.is_production:
        return
    problems = config_problems(settings)
    try:
        problems += database_role_problems(engine)
    except Exception as exc:  # an unreachable DB is itself a reason to stop
        problems.append(f"cannot verify database role ({type(exc).__name__})")
    if problems:
        raise InsecureConfigurationError(problems)


EPHEMERAL_PREFIXES = ("/tmp", "/var/tmp", "/dev/shm")  # noqa: S108


def evidence_storage_warnings(settings: Settings) -> list[str]:
    """Warnings (never fatal) about evidence being stored where a redeploy can destroy it."""
    if settings.evidence_s3_bucket:
        return []
    path = str(settings.evidence_dir.resolve())
    if path.startswith(EPHEMERAL_PREFIXES):
        return [
            f"evidence storage {path} is ephemeral (container /tmp): every redeploy DELETES "
            "evidence files while the alerts remain. Use RS_EVIDENCE_S3_BUCKET or a persistent "
            "volume."
        ]
    if settings.is_production:
        return [
            f"evidence is stored on local disk ({path}); make sure it is a persistent volume, "
            "otherwise a redeploy loses it (alternative: RS_EVIDENCE_S3_BUCKET)."
        ]
    return []
