"""Application settings, loaded from environment variables (prefix ``RS_``).

Secrets have no defaults: the app refuses to start without them. Generate dev values with
``python scripts/gen_dev_secrets.py``.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RS_", env_file=None, extra="ignore")

    # APP_ENV / RS_APP_ENV / RS_ENV; accepts dev|development, test, prod|production.
    # Defaults to production: an unset variable must never relax security checks.
    env: str = Field(
        default="production", validation_alias=AliasChoices("RS_ENV", "RS_APP_ENV", "APP_ENV")
    )
    debug: bool = False

    # Extra browser origins allowed to call the API (CORS). Empty = same-origin only (default).
    # Comma-separated https origins, e.g. "https://dispatch.example.police".
    cors_origins: str = ""

    # Database. The app connects ONLY with the restricted, RLS-bound role.
    database_url: SecretStr
    # Owner role used by Alembic migrations (owns tables, not used at runtime).
    migrator_database_url: SecretStr | None = None
    # Superuser, used only by bootstrap/tests/demo scripts, never by the API process.
    admin_database_url: SecretStr | None = None

    # Token signing.
    jwt_secret: SecretStr
    url_signing_key: SecretStr

    # Envelope encryption: "1:<b64 32 bytes>,2:<b64 32 bytes>" and the version used to wrap.
    master_keys: SecretStr
    master_key_current: int = 1

    evidence_dir: Path = Path("data/evidence")
    # Optional S3-compatible bucket for evidence. When set, the encrypted files (ciphertext only)
    # are stored there under the same relative keys as on disk, instead of in evidence_dir.
    evidence_s3_bucket: str | None = None
    evidence_s3_endpoint: str | None = None
    evidence_s3_region: str = "auto"
    evidence_s3_access_key_id: SecretStr | None = None
    evidence_s3_secret_access_key: SecretStr | None = None

    # Public origin of the web app (used for CSRF Origin checks and cookie security).
    public_origin: str = "https://localhost"
    cookie_secure: bool = True
    # Only enable behind the bundled Caddy proxy (it sets X-Forwarded-For).
    trust_proxy: bool = False

    access_token_ttl_seconds: int = 600
    refresh_token_ttl_seconds: int = 7 * 24 * 3600
    # Server-side session limits (in addition to the UI idle lock). The absolute lifetime caps
    # the refresh-token lifetime: a session never outlives one shift.
    session_absolute_seconds: int = 12 * 3600
    session_idle_seconds: int = 30 * 60
    mfa_pending_ttl_seconds: int = 300
    metrics_token: SecretStr | None = None  # /api/metrics is disabled unless this is set
    reset_token_ttl_seconds: int = 3600  # account-recovery token, single use
    # Demo-only: lets accounts flagged ``mfa_exempt`` log in with a password alone. OFF by default;
    # refused at start-up in production (core/startup.py) and ignored by the login path there.
    mfa_exemption_enabled: bool = False
    reauth_window_seconds: int = 300
    invitation_ttl_seconds: int = 24 * 3600
    signed_url_ttl_seconds: int = 60
    # Contract media links (<img>/<video> src). Longer than signed_url_ttl_seconds because a
    # <video> keeps re-requesting while playing; the session is still checked on every request.
    media_view_ttl_seconds: int = 15 * 60
    grant_ttl_seconds: int = 30 * 60

    # Signed pipeline ingestion (HMAC). Skew bounds replay; the cap bounds memory per request.
    ingest_clock_skew_seconds: int = 60
    ingest_max_body_bytes: int = 64 * 1024 * 1024
    ingest_requests_per_minute: int = 600
    ingest_key_overlap_seconds: int = 24 * 3600

    lockout_threshold: int = 5
    lockout_seconds: int = 15 * 60

    # Argon2id parameters (OWASP recommended minimums by default; tests lower them).
    argon2_time_cost: int = 3
    argon2_memory_cost_kib: int = 64 * 1024
    argon2_parallelism: int = 4

    # Web Push (VAPID). Optional: push is disabled when unset.
    vapid_public_key: str | None = None
    vapid_private_key: SecretStr | None = None
    vapid_subject: str = "mailto:security@roadsentinel.invalid"

    # Seed script password for dev accounts (dev only).
    seed_password: SecretStr | None = None

    @field_validator("env")
    @classmethod
    def _check_env(cls, v: str) -> str:
        aliases = {"dev": "development", "prod": "production"}
        v = aliases.get(v.strip().lower(), v.strip().lower())
        if v not in {"production", "development", "test"}:
            raise ValueError("APP_ENV must be dev, test or prod")
        return v

    @property
    def metrics_token_value(self) -> str | None:
        return self.metrics_token.get_secret_value() if self.metrics_token is not None else None

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
