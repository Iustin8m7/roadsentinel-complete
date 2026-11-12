"""Lease-fenced adapter between approved camera configurations and the existing pipeline.

Sources remain private local profiles. No URL is obtained from control-plane responses.
A revision change stops this process; the existing Supervisor restarts at a clean tracker boundary.
"""

import hashlib
import ipaddress
import posixpath
import secrets
import threading
import time
from urllib.parse import urlsplit


def source_identity(url):
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme == "replay":
        return "replay://" + posixpath.normpath((parts.netloc + parts.path).lstrip("/"))
    if scheme == "device":
        return f"device://{parts.netloc}"
    host = (parts.hostname or "").lower()
    if ":" in host:
        host = f"[{host}]"
    port = parts.port
    suffix = f":{port}" if port and port != {"http": 80, "https": 443, "rtsp": 554}.get(scheme) else ""
    return f"{scheme}://{host}{suffix}{parts.path or '/'}"


class ManagedCamera:
    def __init__(self, sink, cfg):
        self.sink, self.slug = sink, cfg["id"]
        self.epoch, self.seq = secrets.token_hex(16), 0
        self.has_frames = False
        self.last_frame_at = None
        self.acknowledged = False
        self.revision = None
        self.last_poll = 0
        self.lock = threading.RLock()
        self.desired = sink._send("GET", f"/api/ingest/cameras/{self.slug}/config").json()
        self.managed = self.desired["managed"]
        self.fingerprint = None
        if not self.managed:
            return
        if not self.desired["run"] or not self.desired.get("config"):
            raise RuntimeError("Camera is not approved and runnable")
        self.fingerprint = hashlib.sha256(
            source_identity(cfg.get("control_source_reference", cfg["video"])).encode()
        ).hexdigest()
        if self.fingerprint != self.desired.get("source_fingerprint"):
            raise RuntimeError("Registered camera source differs from private worker profile")
        if self.desired.get("source_kind") == "recorded_replay":
            endpoint = urlsplit(cfg["video"])
            if endpoint.scheme in ("http", "https", "rtsp"):
                try:
                    local = ipaddress.ip_address(endpoint.hostname).is_loopback
                except ValueError:
                    local = False
                if not local or not cfg.get("source_replay"):
                    raise RuntimeError("Recorded replay requires an explicit loopback source")
        self.revision = self.desired["revision"]
        self.heartbeat("starting")  # acquire lease before source access

    def apply(self, cfg):
        if not self.managed:
            return cfg
        config = self.desired["config"]
        result = dict(cfg)
        result["managed_target_fps"] = config["acquisition"]["target_fps"]
        for field in ("calibration", "min_y", "zones", "rules", "thresholds"):
            result[field] = config.get(field)
        result["counting_lines"] = config.get("counting_lines", [])
        return result

    def acknowledge(self, model_id, model_sha):
        if not self.managed:
            return
        expected = self.desired["config"]["model"]
        if expected["id"] != model_id or expected.get("sha256") not in (None, model_sha):
            raise RuntimeError("Model does not match approved configuration")
        self.sink._send(
            "POST",
            f"/api/ingest/cameras/{self.slug}/config/ack",
            json={
                "worker_epoch": self.epoch,
                "revision": self.revision,
                "fingerprint": self.desired["fingerprint"],
                "status": "accepted",
            },
        )

        self.acknowledged = True

    def heartbeat(self, health="healthy", status=None):
        with self.lock:
            return self._heartbeat(health, status)

    def _heartbeat(self, health="healthy", status=None):
        if not self.managed:
            return
        self.seq += 1
        if health == "healthy" and self.last_frame_at is not None and time.monotonic() - self.last_frame_at > 5:
            health = "reconnecting"
        if health == "healthy" and not self.has_frames:
            health = "starting"
        body = {
            "worker_epoch": self.epoch,
            "seq": self.seq,
            "health": health,
            "applied_revision": self.revision if health != "starting" else None,
            "source_fingerprint": self.fingerprint,
        }
        if status:
            body["telemetry"] = status
            for old, new in [
                ("processing_fps", "processing_fps"),
                ("fps", "source_fps"),
                ("inference_latency_ms_p50", "inference_p50_ms"),
                ("inference_latency_ms_p95", "inference_p95_ms"),
            ]:
                if status.get(old) is not None:
                    body[new] = status[old]
        response = self.sink._send("POST", f"/api/ingest/cameras/{self.slug}/heartbeat", json=body, timeout=4.0).json()
        if response["directive"] != "run" or response["desired_revision"] != self.revision:
            raise RuntimeError("Camera stopped, lease lost, or approved revision changed")
        self.last_poll = time.monotonic()

    def release(self):
        if not self.managed:
            return
        try:
            self.heartbeat("stopped")
        except Exception:  # noqa: BLE001 - shutdown is best effort; lease expiry fences failure
            # Permission may already be revoked or API unreachable; lease expiry is the fallback.
            return

    def check(self):
        if self.managed and time.monotonic() - self.last_poll >= 2:
            self.heartbeat()

    def stamp(self, event):
        if self.managed:
            event.setdefault("details", {})["origin"] = (
                "local_replay" if self.desired.get("source_kind") == "recorded_replay" else "live_camera"
            )
        if self.managed:
            event["details"].update(worker_epoch=self.epoch, config_revision=self.revision)
