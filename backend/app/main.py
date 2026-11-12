"""RoadSentinel API application factory (run with ``uvicorn app.main:create_app --factory``)."""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import (
    alerts,
    audit,
    auth,
    camera_control,
    camera_worker,
    cameras,
    casework,
    contract,
    evidence,
    ingest,
    incident_map,
    investigation,
    notifications,
    offline_analytics,
    offline_video,
    ops,
    patrol,
    push,
    retention,
    service_accounts,
    sessions,
    stats_response,
    tenants,
    unblur,
    users,
)
from app.api import (
    health as reliability_health,
)
from app.config import get_settings
from app.core.http import (
    CSRF_HEADER,
    CSRFMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.redaction import install_redacting_filter
from app.core.startup import enforce_production_safety, evidence_storage_warnings
from app.db import get_engine
from app.services.auth import AuthError, PolicyError, RateLimited
from app.services.camera_workers import shutdown_all as shutdown_camera_workers
from app.services.offline_analysis import offline_analysis_manager

log = logging.getLogger("app")


def create_app() -> FastAPI:
    settings = get_settings()
    install_redacting_filter()
    enforce_production_safety(settings, get_engine())
    for warning in evidence_storage_warnings(settings):
        logging.getLogger("app").warning("EVIDENCE STORAGE: %s", warning)
    dev = not settings.is_production

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            shutdown_camera_workers()
            offline_analysis_manager.shutdown()

    app = FastAPI(
        title="RoadSentinel API",
        version="0.1.0",
        docs_url="/api/docs" if dev else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if dev else None,
        lifespan=lifespan,
    )

    # Order: the last added middleware runs first (outermost).
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)
    if settings.cors_origin_list:
        # Explicit allowlist only (validated in production: https, no wildcard).
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["Content-Type", CSRF_HEADER],
            max_age=600,
        )

    for module in (
        auth,
        sessions,
        users,
        tenants,
        cameras,
        alerts,
        evidence,
        unblur,
        audit,
        push,
        service_accounts,
        ingest,
    incident_map,
        contract,
        retention,
        patrol,
        stats_response,
        ops,
        offline_video,
        offline_analytics,
        camera_control,
        camera_worker,
        casework,
        reliability_health,
        investigation,
        notifications,
    ):
        app.include_router(module.router)

    from app.services.exports import ExportError
    from app.services.investigation import CaseError

    @app.exception_handler(ExportError)
    @app.exception_handler(CaseError)
    async def _case_domain_error(_: Request, exc: CaseError | ExportError) -> JSONResponse:
        return investigation.error_response(exc)

    @app.exception_handler(AuthError)
    async def _auth_error(_: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse({"detail": exc.message}, status_code=401)

    @app.exception_handler(RateLimited)
    async def _rate_limited(_: Request, exc: RateLimited) -> JSONResponse:
        return JSONResponse(
            {"detail": "Too many attempts, try again later"},
            status_code=429,
            headers={"Retry-After": str(exc.retry_after)},
        )

    @app.exception_handler(PolicyError)
    async def _policy_error(_: Request, exc: PolicyError) -> JSONResponse:
        return JSONResponse({"detail": exc.errors}, status_code=422)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Do not echo submitted values back (they may contain passwords or codes).
        errors = [
            {"loc": e.get("loc"), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()
        ]
        return JSONResponse({"detail": errors}, status_code=422)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Details (stack trace, SQL, paths) stay in the server log, keyed by the correlation id;
        # the client only gets the id to quote when reporting the problem.
        correlation_id = getattr(request.state, "request_id", None) or uuid.uuid4().hex
        log.error(
            "unhandled error",
            exc_info=exc,
            extra={"correlation_id": correlation_id, "path": request.url.path},
        )
        return JSONResponse(
            {"detail": "Internal server error", "correlation_id": correlation_id},
            status_code=500,
            headers={"X-Request-ID": correlation_id, "Cache-Control": "no-store"},
        )

    @app.get("/api/health", tags=["health"])
    def health() -> dict[str, str]:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app
