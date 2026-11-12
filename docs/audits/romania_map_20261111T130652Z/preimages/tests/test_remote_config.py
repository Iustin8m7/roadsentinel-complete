"""Pure control/data-plane handshake tests; no external sources or invented detections."""

import hashlib
import pytest
from roadsentinel.remote_config import ManagedCamera, source_identity


class Reply:
    def __init__(self, value):
        self.value = value

    def json(self):
        return self.value


class Sink:
    def __init__(self):
        self.calls = []
        self.revision = 3
        self.allow = True

    def _send(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        if method == "GET":
            return Reply(
                dict(
                    managed=True,
                    run=True,
                    source_kind="recorded_replay",
                    revision=3,
                    fingerprint="a" * 64,
                    source_fingerprint=hashlib.sha256(b"replay://fixture").hexdigest(),
                    config=dict(
                        model=dict(id="stock-yolox-s", sha256="b" * 64),
                        rules=[],
                        zones=[],
                        calibration=None,
                        thresholds={},
                    ),
                )
            )
        return Reply(dict(directive="run" if self.allow else "stop", desired_revision=self.revision))


def test_lease_before_capture_and_model_checked_before_ack():
    sink = Sink()
    worker = ManagedCamera(
        sink, dict(id="camera", video="/private/fixture.mp4", control_source_reference="replay://fixture")
    )
    assert sink.calls[-1][2]["json"]["health"] == "starting"
    with pytest.raises(RuntimeError, match="Model"):
        worker.acknowledge("stock-yolox-s", "c" * 64)
    worker.acknowledge("stock-yolox-s", "b" * 64)
    assert sink.calls[-1][1].endswith("/config/ack")
    sink.revision = 4
    with pytest.raises(RuntimeError, match="revision"):
        worker.heartbeat()


def test_revocation_stops_without_fallback_and_source_identity_omits_credentials():
    sink = Sink()
    worker = ManagedCamera(sink, dict(id="camera", video="unused", control_source_reference="replay://fixture"))
    sink.allow = False
    with pytest.raises(RuntimeError, match="stopped"):
        worker.heartbeat()
    assert source_identity("https://name:secret@EXAMPLE.org:443/live?token=private") == "https://example.org/live"


def test_critical_only_work_queue_cannot_exceed_capacity():
    import threading
    from roadsentinel.live import BoundedWorker

    entered, release = threading.Event(), threading.Event()

    def blocked():
        entered.set()
        release.wait(5)

    worker = BoundedWorker(maxsize=1, retries=0)
    try:
        assert worker.submit(blocked, critical=True)
        assert entered.wait(2)
        assert worker.submit(lambda: None, critical=True)
        assert not worker.submit(lambda: None, critical=True)
        assert worker.pending() == 1
        assert worker.stats()["dropped"] == 1
    finally:
        release.set()
        worker.shutdown()
