"""Bounded, in-memory annotated camera previews with a short freshness window.

Frames are already redacted and annotated by the vision worker. They are transient display
telemetry, never evidence storage, and are scoped to one backend process and tenant camera.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime

MAX_FRAME_BYTES = 2 * 1024 * 1024
MAX_CAMERAS = 128
PREVIEW_TTL_S = 4.0
MAX_PREVIEW_TTL_S = 120.0


@dataclass(frozen=True)
class PreviewFrame:
    jpeg: bytes
    captured_at: datetime
    sequence: int
    received_monotonic: float
    ttl_s: float


class LivePreviewStore:
    def __init__(self, *, clock=time.monotonic, ttl_s: float = PREVIEW_TTL_S):
        self._clock, self.ttl_s = clock, ttl_s
        self._frames: dict[tuple[uuid.UUID, str], PreviewFrame] = {}
        self._lock = threading.Lock()

    def publish(
        self,
        tenant_id: uuid.UUID,
        camera_slug: str,
        jpeg: bytes,
        captured_at: datetime,
        sequence: int,
        ttl_s: float | None = None,
    ) -> None:
        if not jpeg.startswith(b"\xff\xd8\xff") or len(jpeg) > MAX_FRAME_BYTES:
            raise ValueError("preview must be a bounded JPEG")
        key = (tenant_id, camera_slug)
        now = self._clock()
        ttl = self.ttl_s if ttl_s is None else float(ttl_s)
        if not 0.5 <= ttl <= MAX_PREVIEW_TTL_S:
            raise ValueError("preview ttl is outside safe bounds")
        with self._lock:
            self._expire(now)
            if key not in self._frames and len(self._frames) >= MAX_CAMERAS:
                oldest = min(self._frames, key=lambda item: self._frames[item].received_monotonic)
                del self._frames[oldest]
            previous = self._frames.get(key)
            if previous and sequence <= previous.sequence:
                return
            self._frames[key] = PreviewFrame(jpeg, captured_at, sequence, now, ttl)

    def get(self, tenant_id: uuid.UUID, camera_slug: str) -> PreviewFrame | None:
        now = self._clock()
        key = (tenant_id, camera_slug)
        with self._lock:
            self._expire(now)
            return self._frames.get(key)

    def _expire(self, now: float) -> None:
        expired = [
            key
            for key, frame in self._frames.items()
            if now - frame.received_monotonic > frame.ttl_s
        ]
        for key in expired:
            del self._frames[key]


live_previews = LivePreviewStore()
