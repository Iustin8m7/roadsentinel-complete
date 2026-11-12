#!/usr/bin/env python3
"""Camera calibration helper: fit a pixel->metre homography from measured points, and VALIDATE it
against vehicles of known speed. Speeds stay labelled "orientativ" until validation passes.

  fit       python scripts/calibrate_camera.py fit points.json
              points.json: [{"px": [x, y], "m": [X_m, Y_m]}, ...]   (>= 4, road-plane metres, measured on site)
              prints residuals (metres) and the `calibration: points:` block for the camera yaml
  validate  python scripts/calibrate_camera.py validate cameras/<id>.yaml runs.json [--tolerance-kmh 5] [--tolerance-pct 5] [--apply]
              runs.json: [{"label": "GPS run 1", "true_kmh": 48.0, "samples": [[t_s, x_px, y_px], ...]}, ...]
              (foot point of the vehicle in the frames, speed from a GPS/odometer/radar reference)
              needs >= 3 runs, all within tolerance; --apply writes `validated:` into the camera yaml
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from roadsentinel.geometry import Calibration

MIN_RUNS = 3


def fit(points):
    pairs = [[*p["px"], *p["m"]] for p in points]
    cal = Calibration.from_points(pairs)
    arr = np.array(pairs)
    proj = cal.to_metres(arr[:, :2])
    resid = np.hypot(*(proj - arr[:, 2:]).T)
    return cal, pairs, {"points": len(pairs), "residual_m_mean": round(float(resid.mean()), 3),
                        "residual_m_max": round(float(resid.max()), 3), "residuals_m": [round(float(r), 3) for r in resid]}


def estimate_kmh(cal, samples):
    s = np.array(samples, dtype=float)
    m = cal.to_metres(s[:, 1:3])
    vx, vy = np.polyfit(s[:, 0], m[:, 0], 1)[0], np.polyfit(s[:, 0], m[:, 1], 1)[0]
    return float(np.hypot(vx, vy)) * 3.6


def validate(cal, runs, tol_kmh=5.0, tol_pct=5.0):
    rows = []
    for r in runs:
        est, true = estimate_kmh(cal, r["samples"]), float(r["true_kmh"])
        err = est - true
        ok = abs(err) <= max(tol_kmh, true * tol_pct / 100)
        rows.append({"label": r.get("label", ""), "true_kmh": true, "estimated_kmh": round(est, 1),
                     "error_kmh": round(err, 1), "error_pct": round(100 * err / true, 1), "within_tolerance": ok})
    passed = len(rows) >= MIN_RUNS and all(x["within_tolerance"] for x in rows)
    return {"runs": rows, "n_runs": len(rows), "passed": passed,
            "reason": None if passed else (f"need at least {MIN_RUNS} reference runs" if len(rows) < MIN_RUNS
                                           else "at least one run is outside the tolerance"),
            "tolerance": {"kmh": tol_kmh, "pct": tol_pct},
            "max_abs_error_kmh": round(max((abs(x["error_kmh"]) for x in rows), default=0.0), 1)}


def apply_to_yaml(path, report):
    text = Path(path).read_text()
    text = re.sub(r"^  validated:.*(?:\n    .*)*\n", "", text, flags=re.MULTILINE)
    block = (f"  validated: true\n  validated_on: {date.today().isoformat()}\n"
             f"  validation_runs: {report['n_runs']}\n  validation_max_error_kmh: {report['max_abs_error_kmh']}\n")
    out, done = [], False
    for line in text.splitlines(keepends=True):
        out.append(line)
        if not done and re.match(r"^calibration:", line):
            done = True
    if not done:
        raise SystemExit("camera yaml has no calibration: block")
    # insert right after the calibration key line
    idx = next(i for i, ln in enumerate(out) if re.match(r"^calibration:", ln))
    out.insert(idx + 1, block)
    Path(path).write_text("".join(out))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fit")
    f.add_argument("points")
    v = sub.add_parser("validate")
    v.add_argument("camera_yaml")
    v.add_argument("runs")
    v.add_argument("--tolerance-kmh", type=float, default=5.0)
    v.add_argument("--tolerance-pct", type=float, default=5.0)
    v.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "fit":
        _, pairs, rep = fit(json.loads(Path(a.points).read_text()))
        print(json.dumps(rep, indent=1))
        print("calibration:\n  points: " + json.dumps(pairs))
        return 0
    import yaml

    cfg = yaml.safe_load(Path(a.camera_yaml).read_text())
    c = cfg["calibration"]
    cal = Calibration.from_points(c["points"]) if "points" in c else Calibration(c["source"], c["target_width_m"], c["target_length_m"])
    rep = validate(cal, json.loads(Path(a.runs).read_text()), a.tolerance_kmh, a.tolerance_pct)
    print(json.dumps(rep, indent=1))
    if rep["passed"] and a.apply:
        apply_to_yaml(a.camera_yaml, rep)
        print(f"{a.camera_yaml}: calibration marked validated")
    elif not rep["passed"]:
        print(f"NOT validated: {rep['reason']}. Speeds remain 'orientativ'.", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
