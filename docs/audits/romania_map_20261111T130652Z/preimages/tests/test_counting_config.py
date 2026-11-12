"""Approved counting geometry must reach the worker; private profiles cannot override it."""

import pytest
import yaml

from backend.app.services.camera_config import validate
from roadsentinel.models import ROOT
from roadsentinel.remote_config import ManagedCamera


def configured():
    return {
        "schema_version": 1,
        "reference_frame": {"width": 100, "height": 100},
        "calibration": None,
        "min_y": 0,
        "zones": [
            {
                "id": "scene",
                "name": "Test zone",
                "kind": "carriageway",
                "polygon": [[0, 0], [99, 0], [99, 99], [0, 99]],
                "direction": [0, 1],
            }
        ],
        "rules": ["pedestrian_on_road"],
        "thresholds": yaml.safe_load((ROOT / "cameras/demo-highway.yaml").read_text())["thresholds"],
        "acquisition": {"target_fps": 3, "reconnect_backoff_s": 1, "read_timeout_s": 3, "max_reconnect_attempts": 3},
        "model": {"id": "test", "sha256": "a" * 64},
        "counting_lines": [{"id": "count", "points": [[1, 50], [99, 50]], "lane": "triage"}],
    }


def test_valid_approved_counting_line_and_legacy_configuration():
    value = configured()
    assert validate(value) == []
    del value["counting_lines"]
    assert validate(value) == []


@pytest.mark.parametrize(
    "lines",
    [
        [{"id": "count", "points": [[1, 50], [1, 50]]}],
        [{"id": "count", "points": [[-1, 50], [99, 50]]}],
        [{"id": "count", "points": [[1, float("nan")], [99, 50]]}],
        [{"id": "count", "points": [[1, 50], [99, 50]], "unknown": True}],
        [{"id": "count", "points": [[1, 50], [99, 50]]}] * 2,
    ],
)
def test_bad_line_geometry_is_denied(lines):
    value = configured()
    value["counting_lines"] = lines
    assert any(error.path.startswith("counting_lines") for error in validate(value))


def test_worker_applies_only_approved_counting_lines():
    worker = object.__new__(ManagedCamera)
    worker.managed = True
    worker.desired = {"config": configured()}
    result = worker.apply({"counting_lines": [{"id": "unapproved-private-line"}]})
    assert result["counting_lines"] == configured()["counting_lines"]
