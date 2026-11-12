"""Redaction of secrets in logs and audit details.

Two mechanisms: structured redaction by key name (dicts, lists), and pattern redaction for
free text (JWTs, bearer tokens, ``key=value`` pairs with sensitive keys, plate numbers).
"""

from __future__ import annotations

import logging
import re
from typing import Any

REDACTED = "[REDACTED]"

SENSITIVE_KEYS = re.compile(
    r"(pass(word)?|secret|token|api[_-]?key|private[_-]?key|master[_-]?key|authorization|"
    r"cookie|session|csrf|totp|otp|recovery|code|plate|dek|signature|sig)",
    re.IGNORECASE,
)
# Identifiers and metadata about a secret are not the secret itself.
_SAFE_SUFFIXES = ("_id", "_ids", "_count", "_at", "_type", "_version", "_masked", "_reason")


def is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    if lowered.endswith(_SAFE_SUFFIXES):
        return False
    return bool(SENSITIVE_KEYS.search(lowered))


_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # JWTs (three base64url segments starting with eyJ).
    (re.compile(r"eyJ[\w-]+\.[\w-]+\.[\w-]+"), REDACTED),
    # Authorization headers.
    (re.compile(r"(?i)\b(bearer|basic)\s+[\w\-.~+/=]+"), r"\1 " + REDACTED),
    # key=value / key: value / "key": "value" with a sensitive key name.
    (
        re.compile(r"""(?ix)
            (["']?\b[\w-]*(?:pass(?:word)?|secret|token|api[_-]?key|private[_-]?key|
            master[_-]?keys?|authorization|cookie|csrf|totp|otp|recovery[_-]?codes?|plate|
            sig(?:nature)?)\b["']?\s*[:=]\s*)
            (["']?)[^\s"',;&}]+\2
            """),
        r"\1\2" + REDACTED + r"\2",
    ),
    # Cookie values set/sent by this app.
    (re.compile(r"(__Secure-rs_\w+=)[^;\s]+"), r"\1" + REDACTED),
]


def redact_text(value: str) -> str:
    for pattern, repl in _PATTERNS:
        value = pattern.sub(repl, value)
    return value


def redact(value: Any, *, _depth: int = 0) -> Any:
    """Recursively redact a structure. Keys that look sensitive have their value replaced."""
    if _depth > 8:
        return REDACTED
    if isinstance(value, dict):
        return {
            k: (
                REDACTED
                if isinstance(k, str) and is_sensitive_key(k)
                else redact(v, _depth=_depth + 1)
            )
            for k, v in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact(v, _depth=_depth + 1) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


class RedactingFilter(logging.Filter):
    """Logging filter that scrubs the formatted message and structured ``extra`` args."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            message = str(record.msg)
        record.msg = redact_text(message)
        record.args = None
        for key, val in list(record.__dict__.items()):
            if key in _STANDARD_ATTRS:
                continue
            if is_sensitive_key(key):
                record.__dict__[key] = REDACTED
            else:
                record.__dict__[key] = redact(val)
        return True


_STANDARD_ATTRS = set(
    logging.LogRecord("x", logging.INFO, "x", 0, "x", None, None).__dict__.keys()
) | {"message", "asctime", "taskName"}


def install_redacting_filter() -> None:
    """Attach the filter to the root logger's handlers and to well-known noisy loggers."""
    flt = RedactingFilter()
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
        )
    for handler in root.handlers:
        if not any(isinstance(f, RedactingFilter) for f in handler.filters):
            handler.addFilter(flt)
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "sqlalchemy.engine", "app"):
        logger = logging.getLogger(name)
        if not any(isinstance(f, RedactingFilter) for f in logger.filters):
            logger.addFilter(flt)
