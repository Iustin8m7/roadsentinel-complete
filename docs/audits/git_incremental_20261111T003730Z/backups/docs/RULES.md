# Rule definitions

Events come from `roadsentinel/rules.py`; whether an event becomes an **alert** is decided by
`roadsentinel/alerts.py` (dedupe, cooldown, per-minute cap). All rules are tested on **synthetic**
tracks only (`tests/test_rules*.py`). **None is validated on real footage** until `training/eval.py`
reports on a labelled set; until then treat them as heuristics. Speeds are *indicative* until a camera's
calibration is validated against a known-speed reference (`docs/CALIBRATION.md`).

| Type | Priority | Definition (thresholds in `cameras/<id>.yaml`, `thresholds:`) | Needs |
|---|---|---|---|
| `very_high_speed` | high | median speed over `sustain_s` above `very_high_speed_kmh`, with `sustain_samples` samples | speed |
| `stopped_on_road` / `stopped_emergency_lane` | high | speed < `stopped_speed_kmh` for `stopped_seconds` inside a road / emergency-lane zone | speed |
| `wrong_way` | critical | steady motion against the zone `direction` over `wrong_way_window_s` (> `wrong_way_min_px`) | ≥ ~10 fps |
| `pedestrian_on_road` | critical | a person inside a carriageway/emergency-lane zone (no crosswalk exemption yet: do not enable on crossings) | none |
| `probable_crash` | critical | hard braking (> `hard_brake_mps2`, from > 30 km/h) → full stop on the road within `crash_window_s` → stays stationary `crash_stationary_s` (default 2 s). **No contact detection**; `crash_ignore_classes` for trams | speed, ≥ ~7 fps |
| `near_miss` | high | two moving vehicles (> `near_miss_min_kmh`) closer than `near_miss_max_m` (15) whose distance shrinks so that time-to-collision < `near_miss_ttc_s` (1.5 s); once per pair | speed |
| `object_on_roadway` | critical | a detected non-vehicle, non-person object (COCO backpack/handbag/suitcase only) inside a road zone, moving ≤ `object_max_drift_m` (0.5) for `object_seconds` (5). A generic detector misses most debris; needs a trained class for real use | none |
| `hard_braking` | medium | deceleration > `hard_brake_mps2` | speed, ≥ ~7 fps |
| `tailgating` | medium | time headway to the vehicle ahead in the same lane < `headway_seconds` for 1 s | speed, calibration |
| `dangerous_lane_change` | medium | lateral move > `lane_change_m` within `lane_change_window_s` with a vehicle < 15 m away | calibration |
| `congestion` | info | ≥ `congestion_vehicles` vehicles, mean speed < `congestion_avg_speed_kmh` for `congestion_seconds` | speed |
| fog / ice / road conditions | – | **not implemented**: no measurable method here; roadmap | – |

## Low-frame-rate sources
The defaults need ~5 samples per second. A slow live stream (e.g. 0.4–0.5 processed fps) never produces
speeds with them. Per-camera overrides (in `thresholds:`) switch to a time-window mode:
```yaml
thresholds:
  speed_window_s: 12        # default 1.0
  speed_min_samples: 3      # default 5
  speed_min_span_s: 4       # default 0.5 * speed_window_s
  sustain_s: 12             # very_high_speed: window the speed must stay above the threshold
  sustain_samples: 2        # default 5
  min_track_age_s: 4        # default 1.0
```
Alerts produced this way carry `details.confidence = "low"` / `rate_mode = "low_fps"` and are shown as
*lower confidence*. At 0.5 fps this still cannot support `hard_braking`, `probable_crash` or `wrong_way`: the
pipeline measures its real fps (`rates.RateTracker`), computes with `rule_capabilities()` which rules cannot
work at that rate, switches them off, and reports them in the heartbeat (`cameras.status_info`), which the
Cameras page shows ("Nu poate produce la acest ritm: …"). The result depends on the measured rate, not on a
hard-coded list.

## Alert gate (`alerts:` in the camera yaml)
```yaml
alerts:
  dedupe_s: 8           # same type + zone + within dedupe_px of an earlier alert = duplicate (tracker ID switch)
  dedupe_px: 200
  cooldown_s: {congestion: 120}
  max_per_minute: 12    # per camera; critical alerts are never dropped by this cap
```
Everything suppressed is counted in the pipeline log. Ingestion is idempotent: every alert carries an
`event_key`, a retry returns the same alert instead of a duplicate.
