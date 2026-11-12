import pytest
from pydantic import ValidationError

from app.api.ingest import Heartbeat


def test_heartbeat_accepts_bounded_source_and_traffic_measurements():
    heartbeat = Heartbeat.model_validate(
        {
            "fps": 4.5,
            "source": {
                "kind": "file",
                "state": "healthy",
                "width": 1280,
                "height": 720,
                "frames": 100,
            },
            "traffic": {
                "total_crossings": 3,
                "counts_by_line_lane_class": [
                    {"line": "northbound", "lane": "lane-1", "object_class": "car", "count": 3}
                ],
                "rolling_flow_per_minute": {
                    "window_seconds": 60,
                    "total": 3,
                    "by_class": {"car": 3},
                    "by_direction": {"positive": 3},
                    "by_line": {"northbound": 3},
                },
            },
        }
    )
    assert heartbeat.source and heartbeat.source.width == 1280
    assert heartbeat.traffic and heartbeat.traffic.total_crossings == 3


def test_heartbeat_accepts_explicit_physical_device_source_kind():
    heartbeat = Heartbeat.model_validate(
        {
            "source": {
                "kind": "device",
                "transport": "uvc",
                "state": "healthy",
                "frames": 2,
                "replay": False,
            }
        }
    )
    assert heartbeat.source and heartbeat.source.kind == "device"


def test_heartbeat_accepts_real_pipeline_telemetry_and_marks_replay():
    heartbeat = Heartbeat.model_validate(
        {
            "fps": 2.9,
            "processing_fps": 1.8,
            "inference_latency_ms_p50": 84.5,
            "inference_latency_ms_p95": 93.1,
            "detections": 1085,
            "unique_tracks": 67,
            "tracks_by_class": {"car": 32, "bus": 13, "truck": 16},
            "model": "YOLOX-S ONNX / Supervision ByteTrack",
            "model_sha256": "c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063",
            "source": {"kind": "file", "state": "healthy", "frames": 105, "replay": True},
        }
    )
    assert heartbeat.source and heartbeat.source.replay
    assert heartbeat.unique_tracks == 67 and heartbeat.processing_fps == 1.8
    assert heartbeat.tracks_by_class["car"] == 32


def test_heartbeat_rejects_bad_model_hash_and_negative_track_counts():
    with pytest.raises(ValidationError):
        Heartbeat.model_validate({"model_sha256": "not-a-hash"})
    with pytest.raises(ValidationError):
        Heartbeat.model_validate({"tracks_by_class": {"car": -1}})


@pytest.mark.parametrize(
    "source",
    [
        {"kind": "network", "state": "healthy", "video_url": "rtsp://camera/private"},
        {"kind": "network", "state": "healthy", "width": 0},
    ],
)
def test_heartbeat_rejects_source_urls_and_invalid_dimensions(source):
    with pytest.raises(ValidationError):
        Heartbeat.model_validate({"source": source})


def test_heartbeat_rejects_unbounded_traffic_line_arrays():
    with pytest.raises(ValidationError):
        Heartbeat.model_validate(
            {
                "traffic": {
                    "total_crossings": 0,
                    "counts_by_line_lane_class": [
                        {"line": f"line-{i}", "lane": "lane", "object_class": "car", "count": 0}
                        for i in range(33)
                    ],
                    "rolling_flow_per_minute": {"window_seconds": 60, "total": 0},
                }
            }
        )


def test_heartbeat_rejects_negative_or_unbounded_summary_counts():
    with pytest.raises(ValidationError):
        Heartbeat.model_validate(
            {
                "traffic": {
                    "total_crossings": 0,
                    "rolling_flow_per_minute": {
                        "window_seconds": 60,
                        "total": 0,
                        "by_class": {"car": -1},
                    },
                }
            }
        )
