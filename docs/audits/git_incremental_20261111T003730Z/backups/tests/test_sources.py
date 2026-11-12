from email.message import Message

import numpy as np
import pytest

from roadsentinel.consent import ConsentError
from roadsentinel.sources import (
    ImagePollingCapture,
    SourceError,
    SourceHealth,
    SourceSpec,
    open_capture,
    parse_hls_attributes,
    select_hls_variant,
    validate_hls_resource_hosts,
)

PERMISSION = {
    "granted": True,
    "by": "Camera owner",
    "date": "2026-11-01",
    "scope": "internal test processing",
    "evidence": "local authorization record",
}


def test_local_source_is_enabled_without_network_permission():
    spec = SourceSpec.from_camera({"video": "data/test.mp4"})
    assert spec.kind == "file" and spec.enabled


def test_explicit_uvc_device_is_live_capture_without_network_consent():
    spec = SourceSpec.from_camera({"video": "device:0"})
    assert spec.kind == "device" and spec.live_capture and spec.enabled
    assert not spec.network and not spec.replay


@pytest.mark.parametrize("value", ["device:", "device:-1", "device:16", "device:0/1", "device:camera"])
def test_uvc_device_index_is_explicit_and_bounded(value):
    with pytest.raises(SourceError, match="device"):
        SourceSpec.from_camera({"video": value})


def test_uvc_device_does_not_allow_replay_or_image_polling():
    with pytest.raises(SourceError, match="replay"):
        SourceSpec.from_camera({"video": "device:0", "source_replay": True})
    with pytest.raises(SourceError, match="video mode"):
        SourceSpec.from_camera({"video": "device:0", "source_mode": "image"})


def test_hls_master_selects_best_variant_within_resolution_and_bandwidth_caps():
    master = """#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=1200000,RESOLUTION=640x360,CODECS="avc1.4d401e,mp4a.40.2"
low/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2800000,RESOLUTION=1280x720
mid/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=6000000,RESOLUTION=1920x1080
high/index.m3u8
"""
    assert parse_hls_attributes('BANDWIDTH=2800000,RESOLUTION=1280x720,CODECS="avc1,mp4a"')["CODECS"] == "avc1,mp4a"
    assert select_hls_variant(
        master, "https://media.example/master.m3u8", max_height=720, max_bandwidth=3_000_000
    ) == "https://media.example/mid/index.m3u8"
    with pytest.raises(SourceError, match="no variant within"):
        select_hls_variant(master, "https://media.example/master.m3u8", max_height=240, max_bandwidth=500_000)


def test_hls_variant_and_segment_hosts_are_fail_closed():
    master = "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=640x360\nhttps://cdn.example/v.m3u8\n"
    with pytest.raises(SourceError, match="variant host"):
        select_hls_variant(master, "https://media.example/master.m3u8", max_height=720, max_bandwidth=2_000_000)
    with pytest.raises(SourceError, match="resource host"):
        validate_hls_resource_hosts(
            "#EXTM3U\n#EXTINF:2,\nhttps://other.example/segment.ts\n",
            "https://media.example/v.m3u8",
        )


def test_hls_adapter_selects_variant_and_opens_only_authorized_configured_source():
    from roadsentinel.sources import HlsCapture

    requests = []
    responses = {
        "https://media.example/master.m3u8": (
            "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=640x360\nlow.m3u8\n"
            "#EXT-X-STREAM-INF:BANDWIDTH=2500000,RESOLUTION=1280x720\nmid.m3u8\n"
        ),
        "https://media.example/mid.m3u8": "#EXTM3U\n#EXT-X-MEDIA-SEQUENCE:4\n#EXTINF:2,\nseg4.ts\n",
    }

    class Response:
        def __init__(self, value):
            self.value = value.encode()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, limit):
            return self.value[:limit]

    def opener(request, timeout):
        requests.append((request.full_url, timeout))
        return Response(responses[request.full_url])

    class FakeCapture:
        def isOpened(self):
            return True

        def read(self):
            return True, "frame"

        def get(self, _prop):
            return 0

        def release(self):
            pass

    class FakeCV:
        CAP_FFMPEG = 1900
        CAP_PROP_OPEN_TIMEOUT_MSEC = 53
        CAP_PROP_READ_TIMEOUT_MSEC = 54

        @staticmethod
        def VideoCapture(*args):
            FakeCV.args = args
            return FakeCapture()

    config = {
        "id": "hls-test", "video": "https://media.example/master.m3u8", "enabled": True,
        "source_transport": "hls", "source_consent": PERMISSION, "hls_max_height": 720,
        "hls_max_bandwidth": 3_000_000,
    }
    spec = SourceSpec.from_camera(config)
    capture = HlsCapture(spec, cv_module=FakeCV, opener=opener)
    assert [url for url, _ in requests] == ["https://media.example/master.m3u8", "https://media.example/mid.m3u8"]
    assert FakeCV.args[0] == "https://media.example/mid.m3u8"
    assert capture.read() == (True, "frame")
    capture.release()


def test_hls_vod_is_rejected_for_live_but_loopback_replay_is_accepted():
    config = {
        "id": "hls-test", "video": "https://media.example/v.m3u8", "enabled": True,
        "source_transport": "hls", "source_consent": PERMISSION,
    }
    spec = SourceSpec.from_camera(config)

    class Response:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self, _limit): return b"#EXTM3U\n#EXTINF:4,\nseg.ts\n#EXT-X-ENDLIST\n"

    with pytest.raises(SourceError, match="finite/VOD"):
        from roadsentinel.sources import HlsCapture
        HlsCapture(spec, opener=lambda *_args, **_kwargs: Response())

    replay = SourceSpec.from_camera({
        "id": "replay", "video": "http://127.0.0.1:8000/v.m3u8", "enabled": True,
        "source_transport": "hls", "source_replay": True, "source_consent": PERMISSION,
    })
    assert replay.replay and replay.transport == "hls"


def test_hls_adapter_decodes_local_mpegts_fixture_through_opencv_ffmpeg(tmp_path):
    """A real local HLS decode regression; this is synthetic fixture media, never road evidence."""
    av = pytest.importorskip("av")
    import socketserver
    import threading
    from functools import partial
    from http.server import SimpleHTTPRequestHandler

    import cv2

    if "FFMPEG:                      YES" not in cv2.getBuildInformation():
        pytest.skip("OpenCV was built without FFmpeg")

    segment = tmp_path / "segment.ts"
    container = av.open(str(segment), mode="w", format="mpegts")
    stream = container.add_stream("mpeg2video", rate=5)
    stream.width, stream.height, stream.pix_fmt = 64, 48, "yuv420p"
    for index in range(10):
        pixels = np.full((48, 64, 3), index * 20, dtype=np.uint8)
        frame = av.VideoFrame.from_ndarray(pixels, format="bgr24")
        for packet in stream.encode(frame):
            container.mux(packet)
    for packet in stream.encode():
        container.mux(packet)
    container.close()
    (tmp_path / "fixture.m3u8").write_text(
        "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:2\n"
        "#EXT-X-MEDIA-SEQUENCE:0\n#EXTINF:2.0,\nsegment.ts\n#EXT-X-ENDLIST\n"
    )

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *_args):
            pass

    server = socketserver.ThreadingTCPServer(
        ("127.0.0.1", 0), partial(QuietHandler, directory=str(tmp_path))
    )
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    capture = None
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/fixture.m3u8"
        spec = SourceSpec.from_camera(
            {
                "id": "hls-fixture",
                "video": url,
                "source_transport": "hls",
                "enabled": True,
                "source_replay": True,
                "source_consent": PERMISSION,
                "source_timeout_s": 3,
            }
        )
        capture = open_capture(spec)
        ok, frame = capture.read()
        assert ok and frame.shape == (48, 64, 3)
    finally:
        if capture is not None:
            capture.release()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_uvc_device_opens_only_the_explicit_capture_index(monkeypatch):
    calls = []

    class FakeCapture:
        def isOpened(self):
            return True

        def release(self):
            pass

    class FakeCV:
        CAP_V4L2 = 200

        @staticmethod
        def VideoCapture(*args):
            calls.append(args)
            return FakeCapture()

    opened = open_capture(SourceSpec.from_camera({"video": "device:2"}), cv_module=FakeCV)
    assert opened.isOpened()
    assert calls == [(2, 200)]


def test_local_uvc_profile_requires_no_fabricated_geometry():
    from roadsentinel.pipeline import load_camera

    cfg, calibration, zones = load_camera("cameras/local-uvc.yaml")
    assert cfg["video"] == "device:0"
    assert calibration is None and zones == []


def test_local_mp4_source_opens_and_decodes_frames(tmp_path):
    import cv2

    path = tmp_path / "synthetic.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 5.0, (32, 24))
    if not writer.isOpened():
        pytest.skip("installed OpenCV build has no MP4 encoder")
    for value in (30, 90, 180):
        writer.write(np.full((24, 32, 3), value, dtype=np.uint8))
    writer.release()

    capture = open_capture(SourceSpec.from_camera({"video": str(path)}))
    try:
        ok, frame = capture.read()
        assert ok and frame.shape == (24, 32, 3)
    finally:
        capture.release()


def test_network_sources_require_documented_permission_and_explicit_enablement():
    with pytest.raises(ConsentError):
        SourceSpec.from_camera({"id": "blocked", "video": "https://example.invalid/feed.m3u8"})
    with pytest.raises(SourceError, match="disabled"):
        SourceSpec.from_camera(
            {"id": "blocked", "video": "https://example.invalid/feed.m3u8", "source_consent": PERMISSION}
        )


def test_authorized_network_source_is_parsed_without_revealing_url_in_repr():
    cfg = {"id": "authorized", "video": "rtsp://camera.example/live", "enabled": True, "source_consent": PERMISSION}
    spec = SourceSpec.from_camera(cfg)
    assert spec.network and spec.enabled and "camera.example" not in repr(spec)


def test_local_replay_marker_is_restricted_to_loopback_network_sources():
    spec = SourceSpec.from_camera(
        {
            "video": "http://127.0.0.1:8091/stream.mjpg",
            "enabled": True,
            "source_replay": True,
            "source_consent": PERMISSION,
        }
    )
    assert spec.network and spec.replay
    with pytest.raises(SourceError, match="loopback"):
        SourceSpec.from_camera(
            {
                "video": "https://camera.example/live.m3u8",
                "enabled": True,
                "source_replay": True,
                "source_consent": PERMISSION,
            }
        )


@pytest.mark.parametrize("url", ["ftp://example.invalid/x", "https://user:pass@example.invalid/live"])
def test_unsupported_or_credential_bearing_urls_are_rejected(url):
    with pytest.raises(SourceError):
        SourceSpec.from_camera({"video": url, "source_consent": PERMISSION})


def test_image_polling_reader_decodes_only_bounded_image_responses(monkeypatch):
    from email.utils import formatdate

    import cv2

    ok, encoded = cv2.imencode(".png", np.zeros((5, 8, 3), dtype=np.uint8))
    assert ok

    class Response:
        headers = Message()

        def __init__(self, data):
            self.data = data
            self.headers["Content-Type"] = "image/png"
            self.headers["ETag"] = '"fixture-v1"'
            self.headers["Date"] = formatdate(usegmt=True)
            self.headers["Last-Modified"] = formatdate(usegmt=True)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, size=-1):
            return self.data[:size]

    spec = SourceSpec.from_camera(
        {
            "id": "still",
            "video": "https://camera.example/current.jpg",
            "source_mode": "image",
            "enabled": True,
            "source_consent": PERMISSION,
        }
    )
    capture = ImagePollingCapture(spec, opener=lambda *_args, **_kwargs: Response(encoded.tobytes()))
    success, frame = capture.read()
    assert success and frame.shape == (5, 8, 3)
    capture.release()
    assert capture.read() == (False, None)


def test_snapshot_polling_uses_conditional_cache_validation_and_skips_unchanged_image():
    import cv2

    ok, encoded = cv2.imencode(".jpg", np.zeros((5, 8, 3), dtype=np.uint8))
    assert ok

    class Response:
        def __init__(self):
            self.data = encoded.tobytes()
            self.headers = {
                "Content-Type": "image/jpeg",
                "ETag": '"snapshot-v1"',
                "Date": "Sat, 07 Nov 2026 21:00:00 GMT",
                "Last-Modified": "Sat, 07 Nov 2026 21:00:00 GMT",
            }

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, size=-1):
            return self.data[:size]

    requests = []

    def opener(request, **_kwargs):
        requests.append(request)
        return Response()

    spec = SourceSpec.from_camera(
        {
            "id": "still",
            "video": "https://camera.example/current.jpg",
            "source_mode": "image",
            "source_poll_interval_s": 0.1,
            "enabled": True,
            "source_consent": PERMISSION,
        }
    )
    capture = ImagePollingCapture(spec, opener=opener, sleep=lambda _delay: None)
    success, frame = capture.read()
    assert success and frame.shape == (5, 8, 3)
    assert capture.read() == (None, None)
    assert requests[1].get_header("Cache-control") == "no-cache"
    assert requests[1].get_header("If-none-match") == '"snapshot-v1"'


def test_snapshot_polling_accepts_not_modified_response_as_no_new_frame():
    import urllib.error
    from email.utils import formatdate

    import cv2

    ok, encoded = cv2.imencode(".jpg", np.zeros((5, 8, 3), dtype=np.uint8))
    assert ok

    class Response:
        def __init__(self):
            self.headers = {
                "Content-Type": "image/jpeg",
                "ETag": '"conditional-v1"',
                "Date": formatdate(usegmt=True),
                "Last-Modified": formatdate(usegmt=True),
            }

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, size=-1):
            return encoded.tobytes()[:size]

    call_count = [0]

    def opener(request, **_kwargs):
        call_count[0] += 1
        if call_count[0] == 2:
            raise urllib.error.HTTPError(request.full_url, 304, "Not Modified", {}, None)
        return Response()

    spec = SourceSpec.from_camera(
        {
            "id": "still",
            "video": "https://camera.example/current.jpg",
            "source_mode": "image",
            "source_poll_interval_s": 0.1,
            "enabled": True,
            "source_consent": PERMISSION,
        }
    )
    capture = ImagePollingCapture(spec, opener=opener, sleep=lambda _delay: None)
    assert capture.read()[0] is True
    assert capture.read() == (None, None)


def test_snapshot_polling_rejects_old_provider_image():
    import cv2

    ok, encoded = cv2.imencode(".jpg", np.zeros((5, 8, 3), dtype=np.uint8))
    assert ok

    class Response:
        def __init__(self):
            self.headers = {
                "Content-Type": "image/jpeg",
                "ETag": '"stale-v1"',
                "Date": "Sat, 07 Nov 2026 21:39:18 GMT",
                "Last-Modified": "Sat, 07 Nov 2026 21:01:23 GMT",
            }

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, size=-1):
            return encoded.tobytes()[:size]

    spec = SourceSpec.from_camera(
        {
            "id": "still",
            "video": "https://camera.example/current.jpg",
            "source_mode": "image",
            "snapshot_max_age_s": 1200,
            "enabled": True,
            "source_consent": PERMISSION,
        }
    )
    capture = ImagePollingCapture(spec, opener=lambda *_a, **_k: Response())
    assert capture.read() == (None, None)
    assert capture.last_error == "image snapshot is stale (2275 s; limit 1200 s)"


def test_image_polling_rejects_non_image_content_type():
    class Response:
        def __init__(self):
            self.headers = {"Content-Type": "text/html"}

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, size=-1):
            return b"not an image"

    spec = SourceSpec.from_camera(
        {
            "id": "still",
            "video": "https://camera.example/current",
            "source_mode": "image",
            "enabled": True,
            "source_consent": PERMISSION,
        }
    )
    with pytest.raises(SourceError, match="content type"):
        ImagePollingCapture(spec, opener=lambda *_args, **_kwargs: Response()).read()


def test_source_health_reports_dimensions_and_staleness_without_source_details():
    health = SourceHealth("network")
    health.frame(np.zeros((720, 1280, 3)), now=10)
    assert health.snapshot(now=12) == {
        "kind": "network",
        "transport": "auto",
        "state": "healthy",
        "last_frame_age_s": 2,
        "width": 1280,
        "height": 720,
        "frames": 1,
        "failures": 0,
        "reconnects": 0,
    }
    assert health.snapshot(now=50)["state"] == "stale"
