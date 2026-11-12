# Speed calibration

Speed = distance on the road plane / time. The plane comes from a **homography** that maps image pixels to metres.
Until a camera's calibration is **validated against vehicles of known speed**, every speed in alerts is labelled
*orientativ* (`details.speed_calibration = "unvalidated"`) and the UI says so. Video speed is for triage, not enforcement
(certified equipment is required for fines).

## 1. Measure reference points (on site or from a reliable plan)
Four or more points on the road surface, spread over the monitored area, with their real coordinates in metres on the road
plane (e.g. X across the road, Y along it): lane markings of known length/width, stop lines, painted arrows.
Store them as `points.json`: `[{"px": [x, y], "m": [X_m, Y_m]}, ...]`.

## 2. Fit
```bash
python scripts/calibrate_camera.py fit points.json
```
Prints residuals in metres (mean/max; aim for < 0.3 m) and the `calibration: points: [[px, py, X, Y], ...]` block for
`cameras/<id>.yaml` (the pipeline also accepts the older `source` + `target_width_m/length_m` rectangle form).

## 3. Validate with vehicles of known speed
Record ≥ 3 runs with a reference speed (GPS logger, odometer, radar) across the speed range of interest. For each run write
the vehicle's foot point per frame: `[t_s, x_px, y_px]` (from the pipeline's tracks or manual clicks) and the true speed:
```json
[{"label": "GPS run 1", "true_kmh": 48.0, "samples": [[0.0, 812, 640], [0.2, 815, 652], ...]}]
```
```bash
python scripts/calibrate_camera.py validate cameras/<id>.yaml runs.json --tolerance-kmh 5 --tolerance-pct 5 --apply
```
It passes only with ≥ 3 runs **all** within tolerance, then writes `validated: true`, the date, run count and max error
into the camera yaml. Alerts from that camera then say `speed_calibration: validated`.

## Limits (be honest)
* **Lens distortion is not corrected.** Wide-angle / fisheye cameras (the Piața Unirii webcam) bend the road plane; a
  single homography is then wrong away from the points it was fitted on. Undistortion is roadmap.
* The foot point (bottom-centre of the box) is not the contact point of the wheels; errors grow for large vehicles and close ranges.
* Low frame rates and tracker ID switches add error (`docs/RULES.md`).
* Cameras mounted so that the road is not planar (slopes, bridges) violate the model.
* The demo calibrations (`demo-highway`, `mx-*`) come from tutorial numbers / rough estimates and are **unvalidated**.
