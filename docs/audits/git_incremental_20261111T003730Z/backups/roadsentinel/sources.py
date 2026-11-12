"""Configured video source validation and adapters.

Network sources are opt-in twice: the camera must be enabled and a written source permission
record must pass ``check_source_consent``. This module never discovers or probes feed URLs.
OpenCV/FFmpeg handles authorized video transports (RTSP/RTSPS, HTTP(S), HLS and MJPEG); explicit
``image`` mode handles an authorized periodically refreshed HTTP(S) image endpoint.
"""

from __future__ import annotations

import ipaddress
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

import cv2
import numpy as np

from .consent import check_source_consent


class SourceError(ValueError):
    """A source config is invalid, disabled, or failed to produce a frame."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        # A redirect can silently move processing to a host for which permission was not granted.
        return None


def _open_image_request(request: urllib.request.Request, timeout: float) -> Any:
    return urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout)


def _open_manifest_request(request: urllib.request.Request, timeout: float) -> Any:
    """Fetch a small HLS playlist without following redirects to an unapproved host."""
    return urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout)


def parse_hls_attributes(value: str) -> dict[str, str]:
    """Parse the quoted/unquoted attribute syntax used by EXT-X-STREAM-INF."""
    attrs: dict[str, str] = {}
    for match in re.finditer(r'(?:^|,)([A-Z0-9-]+)=((?:"[^"]*")|[^,]*)', value.strip()):
        attrs[match.group(1)] = match.group(2).strip().strip('"')
    return attrs


def select_hls_variant(
    playlist: str, master_url: str, *, max_height: int, max_bandwidth: int,
    allowed_hosts: tuple[str, ...] = (),
) -> str:
    """Choose the highest resolution/bandwidth variant within configured bounds.

    A media playlist is returned unchanged. Variant URLs must remain on the master host unless
    their hostname is explicitly listed in the reviewed source config.
    """
    lines = [line.strip() for line in playlist.splitlines() if line.strip()]
    variants: list[tuple[int, int, str]] = []
    for i, line in enumerate(lines):
        if not line.startswith("#EXT-X-STREAM-INF:"):
            continue
        attrs = parse_hls_attributes(line.partition(":")[2])
        uri = next((entry for entry in lines[i + 1 :] if not entry.startswith("#")), None)
        if uri is None:
            continue
        try:
            bandwidth = int(attrs.get("AVERAGE-BANDWIDTH", attrs.get("BANDWIDTH", "0")))
        except ValueError:
            continue
        resolution = attrs.get("RESOLUTION", "")
        try:
            height = int(resolution.lower().split("x", 1)[1]) if "x" in resolution.lower() else 0
        except ValueError:
            height = 0
        target = urljoin(master_url, uri)
        original_host = (urlsplit(master_url).hostname or "").lower()
        target_host = (urlsplit(target).hostname or "").lower()
        if target_host != original_host and target_host not in {h.lower() for h in allowed_hosts}:
            raise SourceError("HLS variant host is not allowed by source configuration")
        variants.append((height, bandwidth, target))
    if not variants:
        return master_url
    within = [v for v in variants if (not v[0] or v[0] <= max_height) and (not v[1] or v[1] <= max_bandwidth)]
    if not within:
        raise SourceError("HLS master has no variant within configured resolution/bandwidth limits")
    return max(within, key=lambda variant: (variant[0], variant[1]))[2]


def validate_hls_resource_hosts(playlist: str, playlist_url: str, allowed_hosts: tuple[str, ...] = ()) -> None:
    """Reject cross-host segment/key references unless the source profile explicitly allows them."""
    base_host = (urlsplit(playlist_url).hostname or "").lower()
    approved = {base_host, *(host.lower() for host in allowed_hosts)}
    references = [line.strip() for line in playlist.splitlines() if line.strip() and not line.startswith("#")]
    references.extend(re.findall(r'URI="([^"]+)"', playlist))
    for reference in references:
        parsed = urlsplit(urljoin(playlist_url, reference))
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise SourceError("HLS playlist contains an invalid resource URI")
        if parsed.username is not None or parsed.password is not None:
            raise SourceError("HLS playlist resource credentials are not allowed")
        if parsed.hostname.lower() not in approved:
            raise SourceError("HLS resource host is not allowed by source configuration")


@dataclass(frozen=True)
class SourceSpec:
    source: str = field(repr=False)
    kind: str
    mode: str
    enabled: bool
    timeout_s: float
    poll_interval_s: float
    max_image_bytes: int
    replay: bool = False
    transport: str = "auto"
    hls_max_height: int = 1080
    hls_max_bandwidth: int = 5_000_000
    hls_allowed_hosts: tuple[str, ...] = ()
    snapshot_max_age_s: float = 1200
    max_image_pixels: int = 16_000_000

    @property
    def network(self) -> bool:
        return self.kind == "network"

    @property
    def live_capture(self) -> bool:
        """Sources that deliver newly captured frames instead of replaying a local file."""
        return self.kind in {"network", "device"}

    @classmethod
    def from_camera(cls, cfg: dict[str, Any]) -> SourceSpec:
        raw = str(cfg.get("video", "")).strip()
        if not raw:
            raise SourceError("camera video source is empty")
        parsed = urlsplit(raw)
        if parsed.scheme.lower() == "device":
            index_text = parsed.path or parsed.netloc
            if not index_text.isdecimal() or int(index_text) > 15:
                raise SourceError("camera device must use an explicit index from 0 to 15 (device:N)")
            if cfg.get("source_replay"):
                raise SourceError("source_replay is not valid for an optical camera device")
            mode = str(cfg.get("source_mode", "video")).lower()
            if mode != "video":
                raise SourceError("camera devices support video mode only")
            timeout_s = float(cfg.get("source_timeout_s", 10))
            poll_s = float(cfg.get("source_poll_interval_s", 1))
            max_bytes = int(cfg.get("source_max_image_bytes", 8 * 1024 * 1024))
            if not 0.2 <= timeout_s <= 60:
                raise SourceError("source_timeout_s must be between 0.2 and 60 seconds")
            return cls(str(int(index_text)), "device", "video", bool(cfg.get("enabled", True)),
                       timeout_s, poll_s, max_bytes, False, "uvc")
        network = bool(parsed.scheme)
        if network and parsed.scheme.lower() not in {"rtsp", "rtsps", "http", "https"}:
            raise SourceError("source scheme must be rtsp, rtsps, http, or https")
        if network and (parsed.username is not None or parsed.password is not None):
            raise SourceError("credentials must not be embedded in a source URL")
        if network and not parsed.hostname:
            raise SourceError("network source URL must include a host")
        mode = str(cfg.get("source_mode", "video")).lower()
        if mode not in {"video", "image"}:
            raise SourceError("source_mode must be video or image")
        if mode == "image" and (not network or parsed.scheme.lower() not in {"http", "https"}):
            raise SourceError("image mode requires an HTTP(S) image URL")
        enabled = bool(cfg.get("enabled", not network))
        replay = bool(cfg.get("source_replay", False))
        transport = str(cfg.get("source_transport", "auto")).lower()
        if transport not in {"auto", "hls", "rtsp", "http_video", "snapshot"}:
            raise SourceError("unsupported source_transport")
        if mode == "image":
            if transport not in {"auto", "snapshot"}:
                raise SourceError("image mode cannot use a video transport")
            transport = "snapshot"
        elif transport == "auto":
            transport = "hls" if parsed.path.lower().endswith(".m3u8") else (
                "rtsp" if parsed.scheme.lower() in {"rtsp", "rtsps"} else "http_video"
            )
        if not network:
            transport = "file"
        if network and transport == "hls" and parsed.scheme.lower() not in {"http", "https"}:
            raise SourceError("HLS transport requires an HTTP(S) source URL")
        if network and transport == "rtsp" and parsed.scheme.lower() not in {"rtsp", "rtsps"}:
            raise SourceError("RTSP transport requires an RTSP(S) source URL")
        if network and transport == "http_video" and parsed.scheme.lower() not in {"http", "https"}:
            raise SourceError("HTTP video transport requires an HTTP(S) source URL")
        if transport == "snapshot" and mode != "image":
            raise SourceError("snapshot transport requires source_mode: image")
        if network:
            # Check permission even when disabled, so malformed/incomplete source records are
            # caught at configuration review time. No request is made to the source.
            authorized = check_source_consent(
                {**cfg, "id": str(cfg.get("id", "configured-source")), "video": raw}
            )
            if not authorized:
                raise SourceError("network source is not authorized")
            if not enabled:
                raise SourceError("network source is disabled")
            if replay:
                try:
                    loopback = parsed.hostname == "localhost" or ipaddress.ip_address(parsed.hostname).is_loopback
                except ValueError:
                    loopback = False
                if not loopback:
                    raise SourceError("source_replay is only valid for a loopback source")
        else:
            transport = "file"
        timeout_s = float(cfg.get("source_timeout_s", 10))
        poll_s = float(cfg.get("source_poll_interval_s", 1))
        max_bytes = int(cfg.get("source_max_image_bytes", 8 * 1024 * 1024))
        hls_max_height = int(cfg.get("hls_max_height", 1080))
        hls_max_bandwidth = int(cfg.get("hls_max_bandwidth", 5_000_000))
        snapshot_max_age_s = float(cfg.get("snapshot_max_age_s", 1200))
        max_image_pixels = int(cfg.get("source_max_image_pixels", 16_000_000))
        raw_allowed_hosts = cfg.get("hls_allowed_hosts", [])
        if not isinstance(raw_allowed_hosts, list) or any(not isinstance(host, str) for host in raw_allowed_hosts):
            raise SourceError("hls_allowed_hosts must be a list of hostnames")
        if not 144 <= hls_max_height <= 2160 or not 100_000 <= hls_max_bandwidth <= 100_000_000:
            raise SourceError("HLS resolution/bandwidth limits are outside safe bounds")
        allowed_hosts = tuple(host.lower().rstrip(".") for host in raw_allowed_hosts)
        if any(not host or "/" in host or "@" in host for host in allowed_hosts):
            raise SourceError("HLS allowed hosts must contain hostnames only")
        if not 0.2 <= timeout_s <= 60:
            raise SourceError("source_timeout_s must be between 0.2 and 60 seconds")
        if not 0.1 <= poll_s <= 60:
            raise SourceError("source_poll_interval_s must be between 0.1 and 60 seconds")
        if not 1024 <= max_bytes <= 32 * 1024 * 1024:
            raise SourceError("source_max_image_bytes must be between 1 KiB and 32 MiB")
        if not 30 <= snapshot_max_age_s <= 3600:
            raise SourceError("snapshot_max_age_s must be between 30 and 3600 seconds")
        if not 10_000 <= max_image_pixels <= 32_000_000:
            raise SourceError("source_max_image_pixels must be between 10000 and 32000000")
        return cls(raw, "network" if network else "file", mode, enabled, timeout_s, poll_s,
                   max_bytes, replay, transport, hls_max_height, hls_max_bandwidth, allowed_hosts,
                   snapshot_max_age_s, max_image_pixels)


class ImagePollingCapture:
    """Small VideoCapture-compatible reader for authorized, refreshed image sources."""

    def __init__(
        self,
        spec: SourceSpec,
        *,
        cv_module: Any = cv2,
        opener: Any = None,
        sleep: Any = time.sleep,
        clock: Any = time.monotonic,
    ) -> None:
        self.spec, self.cv = spec, cv_module
        self.opener = opener or _open_image_request
        self.sleep, self.clock = sleep, clock
        self.last_read = 0.0
        self.etag: str | None = None
        self.last_modified: str | None = None
        self.last_modified_at: datetime | None = None
        self.version: tuple[str | None, str | None] | None = None
        self.last_error: str | None = None
        self.closed = False

    def isOpened(self) -> bool:
        return not self.closed

    @property
    def is_snapshot(self) -> bool:
        return True

    def read(self) -> tuple[bool, Any]:
        if self.closed:
            return False, None
        delay = self.spec.poll_interval_s - (self.clock() - self.last_read)
        if self.last_read and delay > 0:
            self.sleep(delay)
        headers = {
            "User-Agent": "RoadSentinel/0.1",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        if self.etag:
            headers["If-None-Match"] = self.etag
        elif self.last_modified:
            headers["If-Modified-Since"] = self.last_modified
        request = urllib.request.Request(self.spec.source, headers=headers)
        try:
            response = self.opener(request, timeout=self.spec.timeout_s)
            with response:
                content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
                if not content_type.startswith("image/"):
                    raise SourceError("image source did not return an image content type")
                etag = response.headers.get("ETag")
                last_modified = response.headers.get("Last-Modified")
                if not etag and not last_modified:
                    raise SourceError("image source omitted freshness validators")
                date_header = response.headers.get("Date")
                try:
                    observed_at = parsedate_to_datetime(date_header).astimezone(UTC) if date_header else datetime.now(UTC)
                    modified_at = parsedate_to_datetime(last_modified).astimezone(UTC) if last_modified else None
                except (TypeError, ValueError, OverflowError):
                    raise SourceError("image source returned an invalid freshness timestamp") from None
                self.etag, self.last_modified = etag, last_modified
                if modified_at:
                    age_s = (observed_at - modified_at).total_seconds()
                    if age_s < -30 or age_s > self.spec.snapshot_max_age_s:
                        self.last_modified_at = modified_at
                        self.last_error = (
                            f"image snapshot is stale ({max(0, int(age_s))} s; "
                            f"limit {int(self.spec.snapshot_max_age_s)} s)"
                        )
                        self.last_read = self.clock()
                        return None, None
                version = (etag, last_modified)
                if self.version == version:
                    self.last_read = self.clock()
                    return None, None
                raw = response.read(self.spec.max_image_bytes + 1)
            if len(raw) > self.spec.max_image_bytes:
                raise SourceError("image source response exceeds configured size limit")
        except urllib.error.HTTPError as exc:
            if exc.code == 304 and (self.etag or self.last_modified):
                self.last_read = self.clock()
                return None, None
            raise SourceError(f"image source request failed: HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise SourceError(f"image source request failed: {type(exc).__name__}") from exc
        image = self.cv.imdecode(np.frombuffer(raw, dtype=np.uint8), self.cv.IMREAD_COLOR)
        if image is None or image.size == 0:
            raise SourceError("image source returned an invalid image")
        if int(image.shape[0]) * int(image.shape[1]) > self.spec.max_image_pixels:
            raise SourceError("image source exceeds the configured pixel limit")
        self.etag, self.last_modified, self.version = etag, last_modified, version
        self.last_modified_at = modified_at
        self.last_error = None
        self.last_read = self.clock()
        return True, image

    def get(self, prop: int) -> float:
        return 0.0

    def release(self) -> None:
        self.closed = True


def open_capture(spec: SourceSpec, *, cv_module: Any = cv2) -> Any:
    """Open one configured source, applying bounded FFmpeg open/read timeouts."""
    if not spec.enabled:
        raise SourceError("source is disabled")
    if spec.mode == "image":
        return ImagePollingCapture(spec, cv_module=cv_module)
    if spec.network and spec.transport == "hls":
        return HlsCapture(spec, cv_module=cv_module)
    if spec.kind == "device":
        index = int(spec.source)
        if cv_module is cv2 and not Path(f"/dev/video{index}").exists():
            raise SourceError(f"camera device /dev/video{index} is missing")
        backend = getattr(cv_module, "CAP_V4L2", 0)
        capture = cv_module.VideoCapture(index, backend)
    elif not spec.network:
        capture = cv_module.VideoCapture(str(Path(spec.source).expanduser()))
    else:
        # FFmpeg timeout options are milliseconds. They prevent a worker from hanging forever on
        # connect/read; LiveReader supervises subsequent stalls and reconnects.
        options = [
            cv_module.CAP_PROP_OPEN_TIMEOUT_MSEC,
            int(spec.timeout_s * 1000),
            cv_module.CAP_PROP_READ_TIMEOUT_MSEC,
            int(spec.timeout_s * 1000),
        ]
        capture = cv_module.VideoCapture(spec.source, cv_module.CAP_FFMPEG, options)
    if not capture or not capture.isOpened():
        if capture:
            capture.release()
        raise SourceError("video source could not be opened")
    return capture


class HlsCapture:
    """Bounded HLS manifest selection followed by OpenCV/FFmpeg media decoding.

    The caller's ``SourceSpec`` has already enforced enablement and source permission. Only the
    master and selected media playlist are read here; FFmpeg handles segment fetching and decoder
    buffering. Redirects are rejected, playlists are capped, and URLs never enter repr/log output.
    """

    MAX_PLAYLIST_BYTES = 256 * 1024

    def __init__(self, spec: SourceSpec, *, cv_module: Any = cv2, opener: Any = None) -> None:
        self.spec = spec
        self.cv = cv_module
        self.opener = opener or _open_manifest_request
        master_text = self._fetch(spec.source)
        media_url = select_hls_variant(
            master_text,
            spec.source,
            max_height=spec.hls_max_height,
            max_bandwidth=spec.hls_max_bandwidth,
            allowed_hosts=spec.hls_allowed_hosts,
        )
        media_text = master_text if media_url == spec.source else self._fetch(media_url)
        if "#EXTM3U" not in media_text[:32]:
            raise SourceError("HLS source did not return a valid playlist")
        if "#EXT-X-ENDLIST" in media_text and not spec.replay:
            raise SourceError("HLS playlist is finite/VOD; live mode requires a rolling playlist")
        validate_hls_resource_hosts(media_text, media_url, spec.hls_allowed_hosts)
        self.capture = cv_module.VideoCapture(
            media_url,
            cv_module.CAP_FFMPEG,
            [
                cv_module.CAP_PROP_OPEN_TIMEOUT_MSEC,
                int(spec.timeout_s * 1000),
                cv_module.CAP_PROP_READ_TIMEOUT_MSEC,
                int(spec.timeout_s * 1000),
            ],
        )
        if not self.capture or not self.capture.isOpened():
            if self.capture:
                self.capture.release()
            raise SourceError("HLS media playlist could not be opened by the configured decoder")

    def _fetch(self, url: str) -> str:
        request = urllib.request.Request(url, headers={"User-Agent": "RoadSentinel/0.1"})
        try:
            response = self.opener(request, timeout=self.spec.timeout_s)
            with response:
                raw = response.read(self.MAX_PLAYLIST_BYTES + 1)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise SourceError(f"HLS playlist request failed ({type(exc).__name__})") from exc
        if len(raw) > self.MAX_PLAYLIST_BYTES:
            raise SourceError("HLS playlist exceeds configured size limit")
        try:
            return raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise SourceError("HLS playlist is not UTF-8 text") from exc

    def isOpened(self) -> bool:
        return self.capture.isOpened()

    def read(self) -> tuple[bool, Any]:
        return self.capture.read()

    def get(self, prop: int) -> float:
        return self.capture.get(prop)

    def release(self) -> None:
        self.capture.release()


@dataclass
class SourceHealth:
    """Bounded source telemetry suitable for a camera heartbeat (never includes source URL)."""

    kind: str
    transport: str = "auto"
    last_frame_at: float | None = None
    width: int | None = None
    height: int | None = None
    frames: int = 0
    failures: int = 0
    reconnects: int = 0

    def frame(self, image: Any, now: float | None = None) -> None:
        self.last_frame_at = time.time() if now is None else now
        self.height, self.width = int(image.shape[0]), int(image.shape[1])
        self.frames += 1

    def snapshot(self, now: float | None = None) -> dict[str, Any]:
        current = time.time() if now is None else now
        age = None if self.last_frame_at is None else max(0.0, current - self.last_frame_at)
        return {
            "kind": self.kind,
            "transport": self.transport,
            "state": "waiting" if age is None else "healthy" if age < 30 else "stale",
            "last_frame_age_s": None if age is None else round(age, 2),
            "width": self.width,
            "height": self.height,
            "frames": self.frames,
            "failures": self.failures,
            "reconnects": self.reconnects,
        }
