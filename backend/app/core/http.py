"""HTTP-level controls: cookies, CSRF, security headers, request context."""

from __future__ import annotations

import logging
import secrets
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import get_settings
from app.core.audit import RequestContext, request_context
from app.core.metrics import metrics

log = logging.getLogger("app.http")

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
CSRF_HEADER = "X-CSRF-Token"
MACHINE_PREFIX = "/api/ingest/"


def _prefix() -> str:
    # The __Secure- prefix makes browsers reject the cookie unless it is Secure and set over TLS.
    return "__Secure-" if get_settings().cookie_secure else ""


def cookie_name(kind: str) -> str:
    return f"{_prefix()}rs_{kind}"


ACCESS, REFRESH, MFA, CSRF = "access", "refresh", "mfa", "csrf"
COOKIE_PATHS = {ACCESS: "/api", REFRESH: "/api/auth", MFA: "/api/auth", CSRF: "/"}


def set_cookie(response: Response, kind: str, value: str, max_age: int) -> None:
    response.set_cookie(
        cookie_name(kind),
        value,
        max_age=max_age,
        path=COOKIE_PATHS[kind],
        secure=get_settings().cookie_secure,
        httponly=kind != CSRF,  # the CSRF token must be readable by the SPA (double submit)
        samesite="strict",
    )


def clear_cookie(response: Response, kind: str) -> None:
    response.delete_cookie(
        cookie_name(kind),
        path=COOKIE_PATHS[kind],
        secure=get_settings().cookie_secure,
        httponly=kind != CSRF,
        samesite="strict",
    )


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def client_ip(request: Request) -> str | None:
    if get_settings().trust_proxy:
        # Caddy appends the real client address as the right-most X-Forwarded-For entry.
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[-1].strip()[:64]
    return request.client.host if request.client else None


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        ctx = RequestContext(
            ip=client_ip(request),
            user_agent=request.headers.get("user-agent"),
            request_id=uuid.uuid4().hex,
        )
        request.state.request_id = ctx.request_id
        token = request_context.set(ctx)
        try:
            response = await call_next(request)
        finally:
            request_context.reset(token)
        response.headers["X-Request-ID"] = ctx.request_id or ""
        metrics.inc(
            "rs_http_requests_total",
            method=request.method,
            status=f"{response.status_code // 100}xx",
        )
        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit cookie check for every state-changing /api request, plus an Origin check.

    SameSite=Strict already blocks cross-site cookie sending in modern browsers; this layer
    covers older browsers, same-site subdomain attacks and login CSRF.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        # Machine endpoints: authenticated by an HMAC signature over the request, never by
        # cookies (ambient credentials), so there is nothing for CSRF to ride on.
        if (
            request.method not in SAFE_METHODS
            and path.startswith("/api/")
            and not path.startswith(MACHINE_PREFIX)
        ):
            origin = request.headers.get("origin")
            settings = get_settings()
            allowed = {settings.public_origin.rstrip("/"), *settings.cors_origin_list}
            if origin and origin.rstrip("/") not in allowed:
                log.warning("csrf: origin mismatch", extra={"path": request.url.path})
                return JSONResponse({"detail": "CSRF validation failed"}, status_code=403)
            if request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse({"detail": "CSRF validation failed"}, status_code=403)
            cookie = request.cookies.get(cookie_name(CSRF), "")
            header = request.headers.get(CSRF_HEADER, "")
            if not cookie or not header or not secrets.compare_digest(cookie, header):
                log.warning("csrf: token mismatch", extra={"path": request.url.path})
                return JSONResponse({"detail": "CSRF validation failed"}, status_code=403)
        return await call_next(request)


API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
APP_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob: https://a.tile.openstreetmap.org https://b.tile.openstreetmap.org https://c.tile.openstreetmap.org; "
    "media-src 'self' blob:; connect-src 'self'; font-src 'self'; manifest-src 'self'; "
    "worker-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; "
    "form-action 'self'"
)

SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=(), "
        "interest-cohort=(), browsing-topics=()"
    ),
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if request.url.path.startswith("/api"):
            response.headers["Content-Security-Policy"] = API_CSP
            # Never let browsers, proxies or the service worker cache API data.
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        else:
            response.headers.setdefault("Content-Security-Policy", APP_CSP)
        return response
