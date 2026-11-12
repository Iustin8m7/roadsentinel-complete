"""Event identity regressions; these exercise deterministic IDs, not event detection."""

from roadsentinel.pipeline import event_idempotency_key


def test_event_identity_is_stable_across_retries_and_ignores_evidence_paths() -> None:
    event = {
        "type": "congestion",
        "video_t": 12.345,
        "track_id": None,
        "object_class": None,
        "details": {"zone": "north", "vehicles": 6},
        "stem": "temporary-name-a",
        "keyframe_path": "/tmp/a.jpg",
    }

    key = event_idempotency_key("camera-a", event)
    retried = {**event, "stem": "temporary-name-b", "keyframe_path": "/tmp/b.jpg"}
    assert event_idempotency_key("camera-a", retried) == key
    assert key.startswith("evt-") and len(key) == 44


def test_event_identity_changes_with_camera_source_time_track_or_zone() -> None:
    event = {
        "type": "wrong_way",
        "video_t": 12.345,
        "track_id": 42,
        "object_class": "car",
        "details": {"zone": "north"},
    }
    base = event_idempotency_key("camera-a", event)
    assert event_idempotency_key("camera-b", event) != base
    assert event_idempotency_key("camera-a", {**event, "video_t": 12.346}) != base
    assert event_idempotency_key("camera-a", {**event, "track_id": 43}) != base
    assert event_idempotency_key(
        "camera-a", {**event, "details": {"zone": "south"}}
    ) != base

