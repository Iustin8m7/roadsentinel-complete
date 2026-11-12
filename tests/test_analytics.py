import pytest

from roadsentinel.analytics import CountLine, TrafficAnalytics
from roadsentinel.camera_ranking import assess_camera, rank_cameras


def line():
    return CountLine.from_config({"id": "northbound", "points": [[50, 0], [50, 100]], "lane": "lane-1"})


def test_counting_line_counts_one_track_once_and_reports_class_and_direction():
    stats = TrafficAnalytics([line()], window_seconds=60)
    stats.update(1, [(12, "car", (20, 40))])
    stats.update(2, [(12, "car", (80, 40))])
    stats.update(3, [(12, "car", (90, 40))])
    result = stats.snapshot(3)
    assert result["total_crossings"] == 1
    assert result["counts_by_line_lane_class"] == [
        {"line": "northbound", "lane": "lane-1", "object_class": "car", "count": 1}
    ]
    assert result["rolling_flow_per_minute"]["total"] == 1


def test_counting_line_ignores_tracks_that_do_not_intersect_the_segment():
    stats = TrafficAnalytics([line()])
    stats.update(1, [(7, "truck", (20, 120))])
    stats.update(2, [(7, "truck", (80, 120))])
    assert stats.snapshot(2)["total_crossings"] == 0


def test_count_line_validation_and_unique_ids():
    with pytest.raises(ValueError):
        CountLine.from_config({"id": "bad", "points": [[0, 0], [0, 0]]})
    with pytest.raises(ValueError, match="unique"):
        TrafficAnalytics([line(), line()])


def test_track_state_is_bounded():
    stats = TrafficAnalytics([line()], max_track_states=2)
    stats.update(1, [(1, "car", (20, 10)), (2, "car", (20, 20))])
    stats.update(2, [(1, "car", (80, 10)), (2, "car", (80, 20))])
    stats.update(3, [(3, "car", (20, 30)), (4, "car", (20, 40))])
    assert len(stats.previous) == 2
    assert len(stats.seen) == 2


def test_unpermitted_or_unassessed_camera_is_not_ranked():
    candidate = {"id": "city-cam", "permission_status": "unknown", "ratings": {"traffic_volume": 5}}
    result = assess_camera(candidate)
    assert not result["eligible"] and result["score_0_to_100"] is None
    assert "vehicle_visibility" in result["missing_criteria"]


def test_camera_rank_requires_granted_permission_and_complete_ratings():
    ratings = {
        key: 4
        for key in (
            "vehicle_visibility",
            "traffic_volume",
            "camera_angle",
            "resolution",
            "reliability",
            "road_coverage",
            "low_occlusion",
            "lighting",
            "authorization",
        )
    }
    ranked = rank_cameras(
        [
            {"id": "unauthorized", "permission_status": "unknown", "ratings": ratings},
            {"id": "approved", "permission_status": "granted", "ratings": ratings},
        ]
    )
    assert [item["id"] for item in ranked] == ["approved", "unauthorized"]
    assert ranked[0]["eligible"] and ranked[0]["score_0_to_100"] == 80
    assert not ranked[1]["eligible"]


def test_camera_rank_rejects_invalid_rating():
    with pytest.raises(ValueError, match="invalid"):
        assess_camera({"ratings": {"traffic_volume": 6}})
