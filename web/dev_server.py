"""Serve the legacy dashboard and demonstration API together for local development."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from roadsentinel.server import app as demo_api

WEB = Path(__file__).resolve().parent
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; "
    "img-src 'self'; media-src 'self'; connect-src 'self'; object-src 'none'; "
    "base-uri 'none'; frame-ancestors 'none'"
)
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = CSP
    return response


@app.get("/app.js", include_in_schema=False)
def script():
    return FileResponse(WEB / "app.js", media_type="text/javascript")


@app.get("/app.css", include_in_schema=False)
def stylesheet():
    return FileResponse(WEB / "app.css", media_type="text/css")


app.mount("/", demo_api)
