import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from roadsentinel.geometry import Calibration

spec = importlib.util.spec_from_file_location("calibrate_camera", Path(__file__).resolve().parent.parent / "scripts" / "calibrate_camera.py")
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)

# ground truth: 10 px = 1 m, plus a perspective-free plane
TRUE = Calibration([[0, 0], [100, 0], [100, 1000], [0, 1000]], 10, 100)


def run(kmh, jitter=0.0, seed=0):
    rng = np.random.default_rng(seed)
    v = kmh / 3.6 * 10
    ts = np.arange(0, 3, 0.2)
    return [[float(t), 50 + rng.normal(0, jitter), 100 + v * t + rng.normal(0, jitter)] for t in ts]


def points(noise=0.0, seed=1):
    rng = np.random.default_rng(seed)
    px = [[0, 0], [100, 0], [100, 1000], [0, 1000], [50, 500]]
    return [{"px": p, "m": [p[0] / 10 + rng.normal(0, noise), p[1] / 10 + rng.normal(0, noise)]} for p in px]


def test_fit_recovers_the_plane_and_reports_residuals():
    cal, pairs, rep = cc.fit(points())
    assert rep["points"] == 5 and rep["residual_m_max"] < 0.01
    assert cal.to_metres([[50, 500]])[0] == pytest.approx([5.0, 50.0], abs=0.01)
    assert Calibration.from_points(pairs).to_metres([[100, 1000]])[0] == pytest.approx([10, 100], abs=0.01)


def test_fit_needs_four_points():
    with pytest.raises(ValueError):
        Calibration.from_points([[0, 0, 0, 0]] * 3)


def test_noisy_reference_points_show_up_in_the_residuals():
    _, _, rep = cc.fit(points(noise=0.5))
    assert rep["residual_m_max"] > 0.1


def test_validation_passes_only_with_enough_accurate_runs():
    good = [{"label": f"r{k}", "true_kmh": k, "samples": run(k, jitter=1.0)} for k in (30, 50, 70)]
    rep = cc.validate(TRUE, good)
    assert rep["passed"] and rep["n_runs"] == 3 and rep["max_abs_error_kmh"] < 3
    assert not cc.validate(TRUE, good[:2])["passed"] and "at least 3" in cc.validate(TRUE, good[:2])["reason"]


def test_a_wrong_calibration_fails_validation():
    bad = Calibration([[0, 0], [100, 0], [100, 1000], [0, 1000]], 10, 140)   # length overestimated by 40 %
    runs = [{"true_kmh": k, "samples": run(k)} for k in (30, 50, 70)]
    rep = cc.validate(bad, runs)
    assert not rep["passed"] and rep["reason"] == "at least one run is outside the tolerance"
    assert rep["runs"][1]["error_pct"] == pytest.approx(40, abs=1)


def test_apply_marks_the_yaml_and_pipeline_reads_it(tmp_path):
    yml = tmp_path / "c.yaml"
    yml.write_text("id: c\ncalibration:\n  source: [[0,0],[100,0],[100,1000],[0,1000]]\n  target_width_m: 10\n  target_length_m: 100\nrules: []\n")
    rep = cc.validate(TRUE, [{"true_kmh": k, "samples": run(k)} for k in (30, 50, 70)])
    cc.apply_to_yaml(yml, rep)
    cc.apply_to_yaml(yml, rep)           # idempotent: no duplicate keys
    import yaml

    cal = yaml.safe_load(yml.read_text())["calibration"]
    assert cal["validated"] is True and cal["validation_runs"] == 3 and yml.read_text().count("validated:") == 1
    assert cal["target_length_m"] == 100


def test_cli_validate_exit_codes(tmp_path):
    yml = tmp_path / "c.yaml"
    yml.write_text("id: c\ncalibration:\n  source: [[0,0],[100,0],[100,1000],[0,1000]]\n  target_width_m: 10\n  target_length_m: 140\n")
    runs = tmp_path / "r.json"
    runs.write_text(json.dumps([{"true_kmh": k, "samples": run(k)} for k in (30, 50, 70)]))
    assert cc.main(["validate", str(yml), str(runs)]) == 3          # 40 % too long: not validated
    assert "validated" not in yml.read_text()


def test_check_dataset_rejects_leakage_missing_card_and_bad_labels(tmp_path):
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))
    import check_dataset
    from test_evaluation import CAR, make_set

    train = make_set(tmp_path, "train", [("a", "cam", "2026-10-20T19:00:00", ["night"], [CAR])])
    test = make_set(tmp_path, "test", [("b", "cam", "2026-10-20T19:03:00", ["day"], [CAR])])
    r = check_dataset.check(train, None, test, 600, None)
    assert any("only 180 s" in e for e in r["errors"]) and any("no data card" in e for e in r["errors"])
    assert any("single camera" in w for w in r["warnings"]) and any("'rain'" in w for w in r["warnings"])
    (tmp_path / "test" / "b.txt").write_text("2 1.5 0.5 0.2 0.2")
    assert any("out of range" in e for e in check_dataset.check(train, None, ev_reload(test), 600, None)["errors"])
    card = tmp_path / "card.md"
    card.write_text("## Sources\nx\n## Licence\nCC\n## Consent\nn/a\n## Retention\n30d\n## Redaction\nblur\n## Labelling\nhuman\n")
    far = make_set(tmp_path, "far", [("c", "cam", "2026-11-20T10:00:00", ["day", "night", "rain", "fog"], [CAR])])
    ok = check_dataset.check(train, None, far, 600, card)
    assert ok["errors"] == []


def ev_reload(m):
    from roadsentinel import evaluation as ev

    return ev.load_manifest(m["path"])
