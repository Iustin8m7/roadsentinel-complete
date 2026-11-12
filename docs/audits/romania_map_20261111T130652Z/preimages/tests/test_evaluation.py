"""Evaluation harness with a fake predictor and tiny generated images."""
import json

import cv2
import numpy as np
import pytest

from roadsentinel import evaluation as ev
from roadsentinel.alerts import AlertGate
from roadsentinel.geometry import Calibration, Zone
from roadsentinel.rules import RuleEngine

W, H = 200, 100


def make_set(tmp_path, name, specs):
    """specs: [(stem, camera, captured_at, tags, [(cls_id, cx, cy, w, h)])]; unique image bytes per item."""
    d = tmp_path / name
    d.mkdir()
    items = []
    for i, (stem, camera, at, tags, boxes) in enumerate(specs):
        img = np.full((H, W, 3), (i * 37 + hash(name) % 50) % 255, np.uint8)
        cv2.putText(img, f"{name}{stem}{i}", (2, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.imwrite(str(d / f"{stem}.png"), img)
        (d / f"{stem}.txt").write_text("\n".join(f"{c} {cx} {cy} {w} {h}" for c, cx, cy, w, h in boxes))
        items.append({"image": f"{stem}.png", "labels": f"{stem}.txt", "camera": camera, "captured_at": at, "tags": tags})
    (d / "m.json").write_text(json.dumps({"name": name, "items": items}))
    return ev.load_manifest(d / "m.json")


CAR = (2, 0.5, 0.5, 0.2, 0.3)
TRUCK = (7, 0.2, 0.5, 0.2, 0.3)


def px(cx, cy, w, h):
    return ((cx - w / 2) * W, (cy - h / 2) * H, (cx + w / 2) * W, (cy + h / 2) * H)


def perfect(path):
    """Predictor that reads the label file back: a perfect detector."""
    labels = ev.read_labels(str(path).replace(".png", ".txt"), W, H)
    return [(c, 0.9, b) for c, b in labels]


def blind(path):
    return []


def size(path):
    return W, H


def test_leakage_by_identical_bytes_and_by_time(tmp_path):
    train = make_set(tmp_path, "train", [("a", "cam", "2026-10-20T19:00:00", [], [CAR])])
    test_ok = make_set(tmp_path, "test", [("b", "cam", "2026-10-20T21:00:00", [], [CAR])])
    assert ev.check_leakage(test_ok, [train]) == []
    close = make_set(tmp_path, "close", [("c", "cam", "2026-10-20T19:05:00", [], [CAR])])
    assert "only 300 s" in ev.check_leakage(close, [train])[0]
    other_cam = make_set(tmp_path, "othercam", [("d", "cam2", "2026-10-20T19:05:00", [], [CAR])])
    assert ev.check_leakage(other_cam, [train]) == []
    # an exact copy of a training image
    copy = tmp_path / "copy"
    copy.mkdir()
    (copy / "x.png").write_bytes((tmp_path / "train" / "a.png").read_bytes())
    (copy / "x.txt").write_text("")
    (copy / "m.json").write_text(json.dumps({"name": "copy", "items": [
        {"image": "x.png", "labels": "x.txt", "camera": "cam", "captured_at": "2027-01-01T00:00:00"}]}))
    assert "identical image bytes" in ev.check_leakage(ev.load_manifest(copy / "m.json"), [train])[0]


def test_items_without_a_timestamp_cannot_be_verified(tmp_path):
    train = make_set(tmp_path, "train", [("a", "cam", "2026-10-20T19:00:00", [], [CAR])])
    test = make_set(tmp_path, "test", [("b", "cam", None, [], [CAR])])
    assert "cannot verify" in ev.check_leakage(test, [train])[0]


def test_perfect_and_blind_detectors(tmp_path):
    m = make_set(tmp_path, "t", [(f"i{i}", "cam", f"2026-11-0{i + 1}T10:00:00", ["day"], [CAR, TRUCK]) for i in range(4)])
    good = ev.evaluate(m["items"], perfect, size)["overall"]
    assert good["map50"] == pytest.approx(1.0) and good["map50_95"] == pytest.approx(1.0)
    assert good["classes"]["car"]["gt_boxes"] == 4 and good["classes"]["car"]["low_sample"] is True
    assert good["classes"]["car"]["precision"] == 1.0 and good["classes"]["car"]["recall"] == 1.0
    bad = ev.evaluate(m["items"], blind, size)["overall"]
    assert bad["map50"] == 0.0 and bad["classes"]["truck"]["recall"] == 0.0 and bad["classes"]["truck"]["missed"] == 4


def test_metrics_split_by_camera_and_condition_tag(tmp_path):
    m = make_set(tmp_path, "t", [
        ("a", "cam1", "2026-11-01T10:00:00", ["day"], [CAR]),
        ("b", "cam2", "2026-11-01T23:00:00", ["night"], [CAR]),
    ])

    def only_day(path):                        # finds the car in cam1's image only
        return perfect(path) if path.name == "a.png" else []

    r = ev.evaluate(m["items"], only_day, size)
    assert r["per_camera"]["cam1"]["map50"] == 1.0 and r["per_camera"]["cam2"]["map50"] == 0.0
    assert r["per_tag"]["day"]["images"] == 1 and r["per_tag"]["night"]["map50"] == 0.0
    assert r["overall"]["map50"] == pytest.approx(0.5, abs=0.02)


def test_localisation_quality_shows_in_map5095_but_not_map50(tmp_path):
    m = make_set(tmp_path, "t", [("a", "cam", "2026-11-01T10:00:00", [], [CAR])])
    gx1, gy1, gx2, gy2 = px(*CAR[1:])

    def sloppy(path):                          # shifted box: IoU ~0.6-0.7
        return [("car", 0.9, (gx1 + 4, gy1 + 3, gx2 + 4, gy2 + 3))]

    r = ev.evaluate(m["items"], sloppy, size)["overall"]
    assert r["map50"] == pytest.approx(1.0) and r["map50_95"] < 0.9


def test_comparison_uses_the_same_items_and_reports_deltas(tmp_path):
    m = make_set(tmp_path, "t", [("a", "cam", "2026-11-01T10:00:00", ["day"], [CAR])])
    cand = ev.evaluate(m["items"], perfect, size)
    base = ev.evaluate(m["items"], blind, size)
    d = ev.compare(cand, base)
    assert d["overall"]["map50_95"] == 1.0 and d["per_class"]["car"] == 1.0 and d["per_tag"]["day"] == 1.0


def test_ap_for_ranked_predictions():
    # 2 GT; predictions: TP(0.9), FP(0.8), TP(0.7): precision 1, .5, .67 -> envelope 1,.67,.67
    assert ev.average_precision([(0.9, True), (0.8, False), (0.7, True)], 2) == pytest.approx((51 * 1 + 50 * 2 / 3) / 101, abs=0.01)
    assert ev.average_precision([], 3) == 0.0 and ev.average_precision([], 0) is None


def test_alerts_per_hour_and_review_turn_alerts_into_false_alarm_rate():
    cal = Calibration([[0, 0], [100, 0], [100, 1000], [0, 1000]], 10, 100)
    zone = Zone({"id": "r", "name": "r", "kind": "carriageway", "direction": [0, 1],
                 "polygon": [[0, 0], [90, 0], [90, 1000], [0, 1000]]})
    cfg = {"thresholds": {"speed_limit_kmh": 50, "very_high_speed_kmh": 80, "stopped_speed_kmh": 3, "stopped_seconds": 60,
                          "hard_brake_mps2": 5, "headway_seconds": 1, "headway_min_speed_kmh": 30, "lane_change_m": 3,
                          "lane_change_window_s": 1.5, "wrong_way_min_px": 150, "congestion_vehicles": 12,
                          "congestion_avg_speed_kmh": 5, "congestion_seconds": 30}, "rules": ["very_high_speed"]}
    v = 120 / 3.6 * 10

    def frames():
        for i in range(10 * 25):                    # 10 s at 25 fps: one car at 120 km/h
            t = i / 25
            yield t, (t, v * t)

    tracker = lambda f: [(1, "car", (40, 10 + f[1]), (30, f[1], 50, 10 + f[1]))]
    res = ev.count_alerts(frames(), tracker, cfg, cal, [zone], RuleEngine, AlertGate)
    assert res["alerts"] == 1 and res["by_type"] == {"very_high_speed": 1}
    assert res["alerts_per_hour"] == pytest.approx(1 / (9.96 / 3600), rel=0.05)
    rate = ev.review_to_rate(res, {0: "false"})
    assert rate["false_alarms"] == 1 and rate["precision"] == 0.0 and rate["unreviewed"] == 0
    assert ev.review_to_rate(res, {})["precision"] is None


def test_report_markdown_flags_low_samples_and_registry_gets_metrics_only_from_here(tmp_path):
    from roadsentinel import models

    m = make_set(tmp_path, "t", [("a", "cam", "2026-11-01T10:00:00", ["day"], [CAR])])
    cand = ev.evaluate(m["items"], perfect, size)
    base = ev.evaluate(m["items"], blind, size)
    reg = tmp_path / "reg.json"
    entry = {"id": "rs-x-v1", "file": "models/rs-x-v1.pt", "sha256": "ab" * 32, "status": "candidate", "base_model": "yolo11s.pt",
             "metrics": None, "framework": {}, "cameras": ["*"], "active_cameras": []}
    models.save_registry({"schema_version": 1, "models": [entry]}, reg)
    report = ev.build_report(entry, cand, base, ev.compare(cand, base), m, [], "yolo11s.pt")
    md = ev.render_markdown(report)
    assert "LOW SAMPLE, do not quote" in md and "mAP50-95" in md and "Caveats" in md
    metrics = ev.record_in_registry(reg, report, "models/reports/rs-x-v1.json")
    assert metrics["source"] == "training/eval.py" and metrics["map50"] == 1.0 and metrics["gt_boxes"] == 1
    assert models.find(models.load_registry(reg), "rs-x-v1")["metrics"]["baseline"] == "yolo11s.pt"
    report["model_sha256"] = "cd" * 32
    with pytest.raises(ev.EvalError, match="changed"):
        ev.record_in_registry(reg, report, "x")


def test_make_manifest_reads_times_from_names_and_falls_back_to_mtime(tmp_path):
    import sys

    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "training"))
    import make_manifest

    d = tmp_path / "imgs"
    d.mkdir()
    for n in ("a_20261020_190600.png", "b.png"):
        cv2.imwrite(str(d / n), np.zeros((4, 4, 3), np.uint8))
    (d / "a_20261020_190600.txt").write_text("2 0.5 0.5 0.2 0.2")
    out = tmp_path / "m" / "t.json"
    assert make_manifest.main(["--images", str(d), "--camera", "cam", "--tags", "night", "--out", str(out)]) == 0
    items = ev.load_manifest(out)["items"]
    assert items[0]["captured_at"] == "2026-10-20T19:06:00" and items[0]["time_source"] == "filename"
    assert items[1]["time_source"] == "mtime" and items[1]["labels"] is None and items[0]["tags"] == ["night"]
