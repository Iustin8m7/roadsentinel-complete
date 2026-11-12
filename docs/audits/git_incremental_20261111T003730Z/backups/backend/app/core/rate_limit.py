"""Sliding-window rate limiting for authentication endpoints.

The in-memory backend is correct for a single API process (the hackathon deployment). The
``RateLimitBackend`` interface exists so a Redis implementation can be dropped in when the API
is scaled horizontally (see docs/ARCHITECTURE_TARGET.md).
"""

from __future__ import annotations

import hashlib
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(frozen=True)
class Limit:
    max_hits: int
    window_seconds: int


# Per-IP limits are looser than per-account ones (shared NAT in police stations).
LOGIN_PER_IP = Limit(30, 300)
LOGIN_PER_ACCOUNT = Limit(10, 300)
MFA_PER_IP = Limit(30, 300)
MFA_PER_ACCOUNT = Limit(10, 300)
INVITE_PER_IP = Limit(20, 300)
REFRESH_PER_IP = Limit(120, 300)


class RateLimitBackend(ABC):
    @abstractmethod
    def hit(self, key: str, limit: Limit) -> tuple[bool, int]:
        """Record a hit. Returns (allowed, retry_after_seconds)."""

    @abstractmethod
    def reset(self) -> None: ...


class InMemoryRateLimiter(RateLimitBackend):
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: Limit) -> tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and q[0] <= now - limit.window_seconds:
                q.popleft()
            if len(q) >= limit.max_hits:
                return False, max(1, int(q[0] + limit.window_seconds - now) + 1)
            q.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_backend: RateLimitBackend = InMemoryRateLimiter()


def get_rate_limiter() -> RateLimitBackend:
    return _backend


def account_key(scope: str, identifier: str) -> str:
    """Rate-limit key for an account identifier. Hashed so e-mails never sit in memory dumps
    keyed in clear, and so unknown accounts are limited exactly like real ones."""
    digest = hashlib.sha256(identifier.strip().lower().encode()).hexdigest()[:32]
    return f"{scope}:acct:{digest}"


def ip_key(scope: str, ip: str | None) -> str:
    return f"{scope}:ip:{ip or 'unknown'}"
