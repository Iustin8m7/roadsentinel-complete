"""Standalone signed ingestion probe (requires httpx).

Set RS_API_URL, RS_INGEST_KEY_ID and RS_INGEST_SECRET, then run:
    python pipeline/client_example.py

The service key must be issued by the secure backend. No operator session is used.
"""
import base64
import hashlib
import hmac
import os
import secrets
import time

import httpx


def sign_request(request, key_id, secret):
    """Sign the final encoded path/query and exact body bytes sent on the wire."""
    body = request.read()
    timestamp, nonce = str(int(time.time())), secrets.token_urlsafe(18)
    message = "\n".join([request.method, request.url.raw_path.decode(), timestamp,
                         nonce, hashlib.sha256(body).hexdigest()]).encode()
    signature = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), message, hashlib.sha256).digest()).decode().rstrip("=")
    request.headers.update({"X-RS-Key-Id": key_id, "X-RS-Timestamp": timestamp,
                            "X-RS-Nonce": nonce, "X-RS-Signature": signature})
    return request


def main():
    names = ("RS_API_URL", "RS_INGEST_KEY_ID", "RS_INGEST_SECRET")
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise SystemExit("Missing: " + ", ".join(missing))
    with httpx.Client(base_url=os.environ["RS_API_URL"].rstrip("/"), timeout=30) as client:
        request = client.build_request("POST", "/api/ingest/ping")
        sign_request(request, os.environ["RS_INGEST_KEY_ID"], os.environ["RS_INGEST_SECRET"])
        response = client.send(request)
        response.raise_for_status()
        print(response.text)


if __name__ == "__main__":
    main()
