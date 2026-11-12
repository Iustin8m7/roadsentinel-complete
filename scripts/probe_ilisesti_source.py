"""Bounded, non-recording probe of the public Ilișești page's published live image."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PAGE = "https://webcamromania.ro/webcam-orase/webcam-ilisesti-dn17/"
ALLOWED_HOST = "webcamromania.ro"
MAX_PAGE_BYTES = 2_000_000
MAX_IMAGE_BYTES = 4_000_000


class PublishedImages(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sources: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return
        values = dict(attrs)
        alt = values.get("alt", "") or ""
        src = values.get("src")
        if src:
            self.sources.append((src, alt))
        srcset = values.get("srcset", "")
        for item in srcset.split(","):
            if item.strip():
                self.sources.append((item.strip().split()[0], alt))


def _published_live_image_url(html: str, page_url: str = PAGE) -> str:
    parser = PublishedImages()
    parser.feed(html)
    candidates: set[str] = set()
    for image_src, alt in parser.sources:
        if "ilisesti" not in alt.casefold() and "dn17" not in alt.casefold():
            continue
        absolute = urljoin(page_url, image_src)
        parsed = urlsplit(absolute)
        if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST or parsed.username:
            continue
        if parsed.path.rstrip("/") != "/_next/image":
            continue
        original = parse_qs(parsed.query).get("url", [""])[0]
        original_path = unquote(original)
        if original_path.startswith("/media/snapshots/") and original_path.endswith("/latest.jpg"):
            candidates.add(urljoin(page_url, original_path))
    if len(candidates) != 1:
        raise ValueError(f"expected one provider-published latest.jpg URL; found {len(candidates)}")
    return candidates.pop()


def _get(url: str, *, timeout_s: float, headers: dict[str, str] | None = None) -> tuple[bytes, dict[str, str]]:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST or parsed.username or parsed.password:
        raise ValueError("probe accepts only an HTTPS WebcamRomania URL without credentials")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "RoadSentinelLocalCameraProbe/1.0", **(headers or {})},
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        final = urlsplit(response.geturl())
        if final.hostname != ALLOWED_HOST or final.scheme != "https":
            raise ValueError("provider redirected outside the approved WebcamRomania host")
        content_length = int(response.headers.get("Content-Length", "0") or 0)
        if content_length > MAX_IMAGE_BYTES:
            raise ValueError("provider image response exceeds 4 MB")
        content = response.read(MAX_PAGE_BYTES + 1)
        if len(content) > MAX_PAGE_BYTES:
            raise ValueError("provider camera page exceeds 2 MB")
        return content, {key.lower(): value for key, value in response.headers.items()}


def _snapshot(url: str, timeout_s: float, etag: str | None) -> dict:
    headers = {"Cache-Control": "no-cache", "Pragma": "no-cache", "Accept": "image/jpeg"}
    if etag:
        headers["If-None-Match"] = etag
    try:
        body, response_headers = _get(url, timeout_s=timeout_s, headers=headers)
    except urllib.error.HTTPError as exc:
        if exc.code == 304:
            return {
                "http_status": 304,
                "unchanged": True,
                "decoded": False,
                "server_date": exc.headers.get("Date"),
                "etag": exc.headers.get("ETag"),
                "last_modified": exc.headers.get("Last-Modified"),
            }
        raise
    content_type = response_headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type != "image/jpeg":
        raise ValueError(f"expected image/jpeg, received {content_type or 'no Content-Type'}")
    if len(body) > MAX_IMAGE_BYTES:
        raise ValueError("provider image response exceeds 4 MB")
    frame = cv2.imdecode(np.frombuffer(body, np.uint8), cv2.IMREAD_COLOR)
    if frame is None or frame.size == 0:
        raise ValueError("provider response did not decode as an image")
    now = datetime.now(UTC)
    modified = response_headers.get("last-modified")
    date = response_headers.get("date")
    modified_at = parsedate_to_datetime(modified).astimezone(UTC) if modified else None
    response_at = parsedate_to_datetime(date).astimezone(UTC) if date else None
    age_s = (response_at - modified_at).total_seconds() if response_at and modified_at else None
    return {
        "http_status": 200,
        "decoded": True,
        "width": int(frame.shape[1]),
        "height": int(frame.shape[0]),
        "sha256": hashlib.sha256(body).hexdigest(),
        "etag": response_headers.get("etag"),
        "last_modified": modified,
        "server_date": date,
        "server_reported_image_age_s": age_s,
        "local_observed_at": now.isoformat(),
        "cache_control": response_headers.get("cache-control"),
        "cache_age_header": response_headers.get("age"),
    }


def probe(*, interval_s: float = 15, timeout_s: float = 8) -> dict:
    page_bytes, page_headers = _get(PAGE, timeout_s=timeout_s)
    image_url = _published_live_image_url(page_bytes.decode("utf-8", errors="replace"))
    first = _snapshot(image_url, timeout_s, None)
    time.sleep(interval_s)
    second = _snapshot(image_url, timeout_s, first.get("etag"))
    first_version = (first.get("etag"), first.get("last_modified"), first.get("sha256"))
    second_version = (second.get("etag"), second.get("last_modified"), second.get("sha256"))
    current_image = second if second.get("http_status") == 200 else first
    current_date = second.get("server_date") or current_image.get("server_date")
    current_modified = current_image.get("last_modified")
    current_age = None
    if current_date and current_modified:
        current_age = (
            parsedate_to_datetime(current_date).astimezone(UTC)
            - parsedate_to_datetime(current_modified).astimezone(UTC)
        ).total_seconds()
    return {
        "camera": "Ilișești DN17",
        "source_page": PAGE,
        "source_transport": "provider-published periodically refreshed JPEG candidate",
        "source_url": image_url,
        "page_cache_control": page_headers.get("cache-control"),
        "probe_interval_s": interval_s,
        "requests": [first, second],
        "two_distinct_provider_versions_observed": (
            second.get("http_status") == 200
            and any(second_version)
            and first_version != second_version
        ),
        "current_snapshot_server_age_s": current_age,
        "current_snapshot_under_20m_policy": current_age is not None and 0 <= current_age <= 1200,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval-s", type=float, default=15)
    parser.add_argument("--timeout-s", type=float, default=8)
    args = parser.parse_args()
    if not 10 <= args.interval_s <= 300 or not 1 <= args.timeout_s <= 15:
        parser.error("interval must be 10–300s and timeout 1–15s")
    try:
        result = probe(interval_s=args.interval_s, timeout_s=args.timeout_s)
    except (OSError, ValueError, urllib.error.URLError, TimeoutError) as exc:
        print(json.dumps({"camera": "Ilișești DN17", "error": f"{type(exc).__name__}: {exc}"}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["current_snapshot_under_20m_policy"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
