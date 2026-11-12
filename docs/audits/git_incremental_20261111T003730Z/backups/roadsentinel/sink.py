"""Where the pipeline sends its events.

LocalSink writes straight to the database and data/media (local development).
RemoteSink posts events and their media to a deployed API, so the database and bucket
credentials never leave the server. Selected with RS_API_URL + RS_INGEST_KEY_ID + RS_INGEST_SECRET.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from . import media, store

EVENT_FIELDS = (
    "camera_id",
    "camera_name",
    "location",
    "type",
    "occurred_at",
    "video_t",
    "track_id",
    "object_class",
    "speed_kmh",
    "rule",
    "details",
    "event_key",
    "vlm_status",
    "vlm_text",
)


class LocalSink:
    def __init__(self):
        self.db = store.connect()

    def clear_camera(self, camera_id):
        store.clear_camera(self.db, camera_id)

    def add_event(self, event, keyframe_path, clip_path):
        return store.insert_event(
            self.db, {**event, "keyframe": media.key_for(keyframe_path), "clip": media.key_for(clip_path)}
        )

    def add_camera_video(self, camera_id, path):
        pass  # already in data/media

    def heartbeat(self, camera_id, status=None):
        pass  # the local dashboard has no live status


class RemoteSink:
    def __init__(self, url, key_id, secret):
        import httpx

        self.key_id, self.secret = key_id, secret.encode()
        self.http = httpx.Client(base_url=url.rstrip("/"), timeout=120)

    def _send(self, method, path, **kwargs):
        request = self.http.build_request(method, path, **kwargs)
        body = request.read()  # Render multipart once; send these exact bytes.
        timestamp, nonce = str(int(time.time())), secrets.token_urlsafe(18)
        message = "\n".join(
            [request.method, request.url.raw_path.decode(), timestamp, nonce, hashlib.sha256(body).hexdigest()]
        ).encode()
        signature = (
            base64.urlsafe_b64encode(hmac.new(self.secret, message, hashlib.sha256).digest()).decode().rstrip("=")
        )
        request.headers.update(
            {"X-RS-Key-Id": self.key_id, "X-RS-Timestamp": timestamp, "X-RS-Nonce": nonce, "X-RS-Signature": signature}
        )
        response = self.http.send(request)
        response.raise_for_status()
        return response

    def clear_camera(self, camera_id):
        import httpx

        try:
            self._send("DELETE", f"/api/ingest/cameras/{camera_id}")
        except httpx.HTTPStatusError as err:
            # The secure backend never deletes evidence and refuses camera resets in production;
            # new events are simply appended.
            if err.response.status_code != 403:
                raise
            print(f"Resetarea camerei {camera_id} e refuzată în producție; evenimentele se adaugă.")

    def add_event(self, event, keyframe_path, clip_path):
        body = {k: event.get(k) for k in EVENT_FIELDS}
        if "redaction" in event:
            # The secure ingest schema accepts metadata in details, not extra fields.
            body["details"] = {**(event.get("details") or {}), "redaction": event["redaction"]}
        with open(keyframe_path, "rb") as kf, open(clip_path, "rb") as clip:
            r = self._send(
                "POST",
                "/api/ingest/events",
                data={"event": json.dumps(body, default=str)},
                files={"keyframe": ("keyframe.jpg", kf, "image/jpeg"), "clip": ("clip.mp4", clip, "video/mp4")},
            )
        return r.json()["id"]

    def add_camera_video(self, camera_id, path):
        with open(path, "rb") as f:
            self._send(
                "PUT", f"/api/ingest/cameras/{camera_id}/video", files={"video": ("annotated.mp4", f, "video/mp4")}
            )

    def heartbeat(self, camera_id, status=None):
        if getattr(self, 'control', None) and self.control.managed:
            return self.control.heartbeat(status=status)
        """Send measured rule, source-health and traffic status (never a source URL)."""
        if status is None:
            self._send("POST", f"/api/ingest/cameras/{camera_id}/heartbeat")
        else:
            self._send("POST", f"/api/ingest/cameras/{camera_id}/heartbeat", json=status)

    def preview(self, camera_id, jpeg, captured_at, sequence):
        """Send one bounded redacted/annotated frame; the API retains it only in memory briefly."""
        from urllib.parse import quote

        path = (
            f"/api/ingest/cameras/{camera_id}/preview?captured_at={quote(captured_at.isoformat())}"
            f"&sequence={int(sequence)}"
        )
        control = getattr(self, 'control', None)
        if control and control.managed:
            path += f"&worker_epoch={control.epoch}&revision={control.revision}"
        self._send(
            "POST",
            path,
            content=jpeg,
            headers={"Content-Type": "image/jpeg"},
            timeout=4.0,
        )


def from_env():
    url = os.environ.get("RS_API_URL")
    if url:
        key_id, secret = os.environ.get("RS_INGEST_KEY_ID"), os.environ.get("RS_INGEST_SECRET")
        if not key_id or not secret:
            raise SystemExit("RS_API_URL requires RS_INGEST_KEY_ID and RS_INGEST_SECRET.")
        print(f"Trimit evenimentele către {url}")
        return RemoteSink(url, key_id, secret)
    return LocalSink()
