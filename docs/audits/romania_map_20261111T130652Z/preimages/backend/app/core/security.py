"""Password hashing (Argon2id), password policy, JWTs, TOTP and random tokens."""

from __future__ import annotations

import secrets
import time
import uuid
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any

import jwt
import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config import get_settings

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 256
RECOVERY_CODE_COUNT = 8
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "roadsentinel"


@lru_cache
def password_hasher() -> PasswordHasher:
    s = get_settings()
    return PasswordHasher(
        time_cost=s.argon2_time_cost,
        memory_cost=s.argon2_memory_cost_kib,
        parallelism=s.argon2_parallelism,
    )  # argon2-cffi defaults to Argon2id


def hash_password(password: str) -> str:
    return password_hasher().hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    try:
        return password_hasher().verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


@lru_cache
def _dummy_hash() -> str:
    return hash_password(secrets.token_urlsafe(16))


def burn_password_check(password: str) -> None:
    """Spend the same time as a real verification when the account does not exist."""
    verify_password(_dummy_hash(), password)


@lru_cache
def common_passwords() -> frozenset[str]:
    text = resources.files("app.core").joinpath("common_passwords.txt").read_text("utf-8")
    lines = (line.strip().lower() for line in text.splitlines())
    return frozenset(line for line in lines if line and not line.startswith("#"))


def password_policy_errors(password: str, *, email: str | None = None) -> list[str]:
    errors = []
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(password) > MAX_PASSWORD_LENGTH:
        errors.append(f"Password must be at most {MAX_PASSWORD_LENGTH} characters.")
    lowered = password.lower()
    if lowered in common_passwords():
        errors.append("Password is too common.")
    if email and email.split("@")[0].lower() in lowered and len(email.split("@")[0]) >= 4:
        errors.append("Password must not contain your e-mail name.")
    return errors


def random_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def generate_recovery_codes() -> list[str]:
    # 10 random base32 chars (50 bits) per code, shown as XXXXX-XXXXX.
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
    codes = []
    for _ in range(RECOVERY_CODE_COUNT):
        raw = "".join(secrets.choice(alphabet) for _ in range(10))
        codes.append(f"{raw[:5]}-{raw[5:]}")
    return codes


def normalize_recovery_code(code: str) -> str:
    return code.replace("-", "").replace(" ", "").upper()


# --------------------------------------------------------------------------- JWT


@dataclass(frozen=True)
class AccessClaims:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    session_id: uuid.UUID


@dataclass(frozen=True)
class MfaPendingClaims:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    enrollment: bool


def _encode(payload: dict[str, Any], ttl: int) -> str:
    now = int(time.time())
    payload = {**payload, "iss": JWT_ISSUER, "iat": now, "exp": now + ttl, "jti": random_token(8)}
    return jwt.encode(payload, get_settings().jwt_secret.get_secret_value(), JWT_ALGORITHM)


def _decode(token: str, typ: str) -> dict[str, Any]:
    payload: dict[str, Any] = jwt.decode(
        token,
        get_settings().jwt_secret.get_secret_value(),
        algorithms=[JWT_ALGORITHM],
        issuer=JWT_ISSUER,
        options={"require": ["exp", "iat", "iss", "sub", "typ"]},
    )
    if payload.get("typ") != typ:
        raise jwt.InvalidTokenError("wrong token type")
    return payload


def create_access_token(user_id: uuid.UUID, tenant_id: uuid.UUID, session_id: uuid.UUID) -> str:
    return _encode(
        {"typ": "access", "sub": str(user_id), "tid": str(tenant_id), "sid": str(session_id)},
        get_settings().access_token_ttl_seconds,
    )


def decode_access_token(token: str) -> AccessClaims:
    p = _decode(token, "access")
    return AccessClaims(uuid.UUID(p["sub"]), uuid.UUID(p["tid"]), uuid.UUID(p["sid"]))


def create_mfa_pending_token(user_id: uuid.UUID, tenant_id: uuid.UUID, enrollment: bool) -> str:
    return _encode(
        {"typ": "mfa_pending", "sub": str(user_id), "tid": str(tenant_id), "enr": enrollment},
        get_settings().mfa_pending_ttl_seconds,
    )


def decode_mfa_pending_token(token: str) -> MfaPendingClaims:
    p = _decode(token, "mfa_pending")
    return MfaPendingClaims(uuid.UUID(p["sub"]), uuid.UUID(p["tid"]), bool(p.get("enr")))


# --------------------------------------------------------------------------- TOTP


TOTP_INTERVAL = 30
TOTP_ISSUER = "RoadSentinel"


def new_totp_secret() -> str:
    return pyotp.random_base32(32)


def totp_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=TOTP_ISSUER)


def verify_totp(secret: str, code: str, last_step: int | None) -> int | None:
    """Return the accepted time-step, or None. Accepts +/-1 step of clock drift and rejects
    any step at or before ``last_step`` (replay protection)."""
    code = code.strip().replace(" ", "")
    if not (code.isdigit() and len(code) == 6):
        return None
    totp = pyotp.TOTP(secret)
    now_step = int(time.time()) // TOTP_INTERVAL
    for step in (now_step - 1, now_step, now_step + 1):
        if last_step is not None and step <= last_step:
            continue
        if secrets.compare_digest(totp.at(step * TOTP_INTERVAL), code):
            return step
    return None
