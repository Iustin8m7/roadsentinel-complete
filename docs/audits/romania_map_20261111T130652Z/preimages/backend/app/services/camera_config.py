"""Camera configuration schema (v1): validation, canonical form, fingerprint and diff.

The shape mirrors the pipeline's ``cameras/*.yaml`` semantics (``roadsentinel/pipeline.py``,
``rules.py``, ``geometry.py``) WITHOUT the video path or any secret: the source is registered
separately on the camera. Pure functions only (no database, no network), shared by the API,
the editor contract (``docs/camera-config-contract.md``) and the tests.

Validation never stops at the first problem: it returns every error it can find, each
addressed by a path such as ``zones[1].polygon[2]``.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from typing import Any

from app.core.catalog import EVENT_TYPES

SCHEMA_VERSION = 1
MAX_CONFIG_BYTES = 64 * 1024
COORDINATE_CONVENTION = "pixels_top_left"  # x right, y down, origin at the top-left pixel
ZONE_KINDS = ("carriageway", "emergency_lane")
VEHICLE_CLASSES = ("car", "truck", "bus", "motorcycle")
ZONE_ID = re.compile(r"^[a-z0-9_]{1,40}$")
MODEL_ID = re.compile(r"^[A-Za-z0-9._/-]{1,120}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")

TOP_LEVEL = (
    "schema_version",
    "reference_frame",
    "calibration",
    "min_y",
    "zones",
    "counting_lines",
    "rules",
    "thresholds",
    "acquisition",
    "model",
)

# Threshold name -> (min, max, integer?). Names are the keys read by roadsentinel/rules.py
# (tests/test_camera_config_contract.py at the repo root keeps them in sync).
REQUIRED_THRESHOLDS: dict[str, tuple[float, float, bool]] = {
    "speed_limit_kmh": (5, 200, False),
    "very_high_speed_kmh": (5, 300, False),
    "stopped_speed_kmh": (0.5, 30, False),
    "stopped_seconds": (1, 3600, False),
    "hard_brake_mps2": (1, 15, False),
    "headway_seconds": (0.2, 5, False),
    "headway_min_speed_kmh": (0, 200, False),
    "lane_change_m": (0.5, 10, False),
    "lane_change_window_s": (0.5, 5, False),
    "wrong_way_min_px": (10, 5000, False),
    "congestion_vehicles": (1, 500, True),
    "congestion_avg_speed_kmh": (1, 200, False),
    "congestion_seconds": (1, 3600, False),
}
OPTIONAL_THRESHOLDS: dict[str, tuple[float, float, bool]] = {
    "min_track_age_s": (0.2, 10, False),
    "crash_window_s": (0.5, 30, False),
}
LIST_THRESHOLDS = ("crash_ignore_classes",)


@dataclass(frozen=True)
class RuleSpec:
    """What a rule needs, derived from roadsentinel/rules.py.

    ``min_fps``: speeds need >= 5 samples within 1 s (``_update_speed``); hard braking needs
    >= 10 speed samples within 1.4 s; wrong way needs >= 20 positions within 2 s."""

    calibration: bool
    min_fps: float
    zone_kinds: tuple[str, ...] = ()
    needs_direction: bool = False


RULES: dict[str, RuleSpec] = {
    "pedestrian_on_road": RuleSpec(False, 1.0, ("carriageway", "emergency_lane")),
    "very_high_speed": RuleSpec(True, 5.0),
    "stopped_on_road": RuleSpec(True, 5.0, ("carriageway",)),
    "stopped_emergency_lane": RuleSpec(True, 5.0, ("emergency_lane",)),
    "hard_braking": RuleSpec(True, 7.2),
    "probable_crash": RuleSpec(True, 7.2, ("carriageway", "emergency_lane")),
    "tailgating": RuleSpec(True, 5.0, ("carriageway",)),
    "dangerous_lane_change": RuleSpec(True, 5.0, ("carriageway",)),
    "wrong_way": RuleSpec(True, 10.0, ("carriageway", "emergency_lane"), needs_direction=True),
    "congestion": RuleSpec(True, 5.0, ("carriageway",)),
}
assert set(RULES) <= set(EVENT_TYPES), "configured camera rules must be known event types"

ACQUISITION: dict[str, tuple[float, float, bool]] = {
    "target_fps": (0.5, 60, False),
    "reconnect_backoff_s": (0.5, 300, False),
    "read_timeout_s": (1, 120, False),
    "max_reconnect_attempts": (1, 10000, True),
}


@dataclass(frozen=True)
class ConfigError:
    path: str
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def _num(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


class _Collector:
    def __init__(self) -> None:
        self.errors: list[ConfigError] = []

    def add(self, path: str, code: str, message: str) -> None:
        self.errors.append(ConfigError(path, code, message))

    def number(
        self, path: str, value: Any, lo: float, hi: float, integer: bool = False
    ) -> float | None:
        if not _num(value) or (integer and not float(value).is_integer()):
            kind = "an integer" if integer else "a number"
            self.add(path, "invalid_type", f"must be {kind}")
            return None
        if not lo <= value <= hi:
            self.add(path, "out_of_range", f"must be between {lo:g} and {hi:g}")
            return None
        return float(value)

    def point(self, path: str, value: Any, limit: float) -> tuple[float, float] | None:
        if not (isinstance(value, list) and len(value) == 2 and all(_num(v) for v in value)):
            self.add(path, "invalid_point", "must be [x, y] with two numbers")
            return None
        if abs(value[0]) > limit or abs(value[1]) > limit:
            self.add(path, "out_of_range", f"coordinates must be within +/-{limit:g}")
            return None
        return float(value[0]), float(value[1])


def _area(points: list[tuple[float, float]]) -> float:
    return abs(
        sum(
            x1 * y2 - x2 * y1
            for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1], strict=True)
        )
        / 2
    )


def _cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _segments_cross(
    p1: tuple[float, float],
    p2: tuple[float, float],
    q1: tuple[float, float],
    q2: tuple[float, float],
) -> bool:
    d1, d2 = _cross(q1, q2, p1), _cross(q1, q2, p2)
    d3, d4 = _cross(p1, p2, q1), _cross(p1, p2, q2)
    return d1 * d2 < 0 and d3 * d4 < 0


def _self_intersects(points: list[tuple[float, float]]) -> bool:
    n = len(points)
    edges = [(points[i], points[(i + 1) % n]) for i in range(n)]
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue  # adjacent through the closing edge
            if _segments_cross(*edges[i], *edges[j]):
                return True
    return False


def validate(config: Any) -> list[ConfigError]:
    """Every problem in ``config`` (empty list = valid). Never raises on bad input."""
    c = _Collector()
    if not isinstance(config, dict):
        c.add("", "invalid_type", "configuration must be a JSON object")
        return c.errors
    if len(json.dumps(config, default=str)) > MAX_CONFIG_BYTES:
        c.add("", "too_large", f"configuration must be at most {MAX_CONFIG_BYTES} bytes")
        return c.errors
    for key in sorted(set(config) - set(TOP_LEVEL)):
        c.add(key, "unknown_field", "unknown field (video paths and secrets do not belong here)")

    if config.get("schema_version") != SCHEMA_VERSION:
        c.add("schema_version", "unsupported_schema", f"must be {SCHEMA_VERSION}")

    # Reference frame: the pixel domain every coordinate below refers to.
    frame = config.get("reference_frame")
    width = height = None
    if not isinstance(frame, dict):
        c.add("reference_frame", "required", "reference_frame {width, height} is required")
    else:
        for key in sorted(set(frame) - {"width", "height", "coordinate_convention"}):
            c.add(f"reference_frame.{key}", "unknown_field", "unknown field")
        width = c.number("reference_frame.width", frame.get("width"), 64, 8192, True)
        height = c.number("reference_frame.height", frame.get("height"), 64, 8192, True)
        if frame.get("coordinate_convention", COORDINATE_CONVENTION) != COORDINATE_CONVENTION:
            c.add(
                "reference_frame.coordinate_convention",
                "unsupported_value",
                f"only '{COORDINATE_CONVENTION}' is supported",
            )
    limit = 4 * max(width or 8192, height or 8192)

    # Calibration: 4 image points of a road rectangle and its size in metres. Never invented.
    calibration = config.get("calibration")
    has_calibration = False
    if calibration is not None:
        if not isinstance(calibration, dict):
            c.add("calibration", "invalid_type", "must be an object or null")
        else:
            for key in sorted(set(calibration) - {"source", "target_width_m", "target_length_m"}):
                c.add(f"calibration.{key}", "unknown_field", "unknown field")
            src = calibration.get("source")
            pts: list[tuple[float, float]] = []
            if not (isinstance(src, list) and len(src) == 4):
                c.add(
                    "calibration.source", "invalid_calibration", "must be exactly 4 [x, y] points"
                )
            else:
                for i, p in enumerate(src):
                    pt = c.point(f"calibration.source[{i}]", p, limit)
                    if pt:
                        pts.append(pt)
                if len(pts) == 4:
                    collinear = any(
                        abs(_cross(pts[a], pts[b], pts[d])) < 1e-6
                        for a, b, d in ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3))
                    )
                    if collinear or _self_intersects(pts):
                        c.add(
                            "calibration.source",
                            "degenerate_calibration",
                            "points must form a simple quadrilateral (no three collinear)",
                        )
            w_m = c.number(
                "calibration.target_width_m", calibration.get("target_width_m"), 0.5, 500
            )
            l_m = c.number(
                "calibration.target_length_m", calibration.get("target_length_m"), 0.5, 5000
            )
            has_calibration = len(pts) == 4 and w_m is not None and l_m is not None

    if config.get("min_y") is not None:
        c.number("min_y", config.get("min_y"), 0, height or 8192, True)

    # Zones.
    zones = config.get("zones")
    zone_kinds: dict[str, bool] = {}  # kind -> any zone of that kind has a direction
    if not isinstance(zones, list) or not 1 <= len(zones) <= 32:
        c.add("zones", "invalid_zones", "must be a list of 1 to 32 zones")
        zones = zones if isinstance(zones, list) else []
    seen_ids: set[str] = set()
    for i, zone in enumerate(zones[:32]):
        zp = f"zones[{i}]"
        if not isinstance(zone, dict):
            c.add(zp, "invalid_type", "must be an object")
            continue
        for key in sorted(set(zone) - {"id", "name", "kind", "direction", "polygon"}):
            c.add(f"{zp}.{key}", "unknown_field", "unknown field")
        zid = zone.get("id")
        if not (isinstance(zid, str) and ZONE_ID.match(zid)):
            c.add(f"{zp}.id", "invalid_id", "must match ^[a-z0-9_]{1,40}$")
        elif zid in seen_ids:
            c.add(f"{zp}.id", "duplicate_id", f"zone id '{zid}' is used more than once")
        else:
            seen_ids.add(zid)
        name = zone.get("name")
        if not (isinstance(name, str) and 1 <= len(name.strip()) <= 80):
            c.add(f"{zp}.name", "invalid_name", "must be 1 to 80 characters")
        kind = zone.get("kind")
        if kind not in ZONE_KINDS:
            c.add(f"{zp}.kind", "unsupported_value", f"must be one of {', '.join(ZONE_KINDS)}")
        direction = zone.get("direction")
        if direction is not None:
            d = c.point(f"{zp}.direction", direction, 1e4)
            if d and d == (0.0, 0.0):
                c.add(f"{zp}.direction", "invalid_direction", "must not be [0, 0]")
                direction = None
        elif kind == "carriageway":
            # rules.py reads zone.direction[1] for every carriageway zone (vehicle ahead).
            c.add(f"{zp}.direction", "required", "carriageway zones need a direction [dx, dy]")
        if kind in ZONE_KINDS:
            zone_kinds[kind] = zone_kinds.get(kind, False) or direction is not None
        poly = zone.get("polygon")
        if not (isinstance(poly, list) and 3 <= len(poly) <= 64):
            c.add(f"{zp}.polygon", "invalid_polygon", "must have 3 to 64 [x, y] points")
            continue
        points: list[tuple[float, float]] = []
        for j, p in enumerate(poly):
            pt = c.point(f"{zp}.polygon[{j}]", p, limit)
            if pt is None:
                continue
            if (
                width is not None
                and height is not None
                and not (0 <= pt[0] <= width and 0 <= pt[1] <= height)
            ):
                c.add(
                    f"{zp}.polygon[{j}]",
                    "outside_reference_frame",
                    f"point must lie within the {width:g}x{height:g} reference frame",
                )
            points.append(pt)
        if len(points) == len(poly):
            if _self_intersects(points):
                c.add(f"{zp}.polygon", "self_intersecting", "polygon edges cross each other")
            elif _area(points) < 1.0:
                c.add(f"{zp}.polygon", "degenerate_polygon", "polygon has no area")

    # Optional counting geometry uses the same reference-frame pixel coordinates as zones.
    lines = config.get("counting_lines", [])
    if not isinstance(lines, list) or len(lines) > 16:
        c.add("counting_lines", "invalid_lines", "at most16 counting lines are allowed")
    else:
        line_ids = set()
        for i, line in enumerate(lines):
            lp = f"counting_lines[{i}]"
            if not isinstance(line, dict) or set(line) - {"id", "points", "lane"}:
                c.add(lp, "invalid_line", "line requires id, two points and optional lane")
                continue
            lid = line.get("id")
            if not isinstance(lid, str) or not ZONE_ID.fullmatch(lid) or lid in line_ids:
                c.add(lp + ".id", "invalid_id", "counting-line ids must be valid and unique")
            line_ids.add(str(lid))
            points = line.get("points")
            if not isinstance(points, list) or len(points) != 2:
                c.add(lp + ".points", "invalid_points", "exactly two endpoints required")
                continue
            parsed = [c.point(f"{lp}.points[{j}]", point, 1e7) for j, point in enumerate(points)]
            if all(point is not None for point in parsed):
                if parsed[0] == parsed[1]:
                    c.add(lp + ".points", "degenerate_line", "endpoints must differ")
                if (
                    width is not None
                    and height is not None
                    and any(not (0 <= x <= width and 0 <= y <= height) for x, y in parsed)
                ):
                    c.add(
                        lp + ".points",
                        "outside_reference_frame",
                        "line must lie inside reference frame",
                    )
            if line.get("lane") is not None and (
                not isinstance(line["lane"], str) or not 1 <= len(line["lane"]) <= 60
            ):
                c.add(lp + ".lane", "invalid_lane", "lane label must be1-60 characters")

    # Acquisition cadence and source handling bounds.
    acq = config.get("acquisition")
    target_fps = None
    if not isinstance(acq, dict):
        c.add("acquisition", "required", "acquisition {target_fps, ...} is required")
    else:
        for key in sorted(set(acq) - set(ACQUISITION)):
            c.add(f"acquisition.{key}", "unknown_field", "unknown field")
        for key, (lo, hi, integer) in ACQUISITION.items():
            value = c.number(f"acquisition.{key}", acq.get(key), lo, hi, integer)
            if key == "target_fps":
                target_fps = value

    # Rules: known ids, their geometry/calibration needs and their minimum processing rate.
    rules = config.get("rules")
    if not isinstance(rules, list) or not rules:
        c.add("rules", "invalid_rules", "must be a non-empty list of rule ids")
        rules = []
    seen_rules: set[str] = set()
    for i, rule in enumerate(rules):
        rp = f"rules[{i}]"
        if not isinstance(rule, str) or rule not in RULES:
            c.add(rp, "unknown_rule", "unknown rule id")
            continue
        if rule in seen_rules:
            c.add(rp, "duplicate_rule", f"rule '{rule}' is listed more than once")
            continue
        seen_rules.add(rule)
        spec = RULES[rule]
        if spec.calibration and not has_calibration:
            c.add(rp, "calibration_required", f"'{rule}' needs a pixel-to-metre calibration")
        if target_fps is not None and target_fps < spec.min_fps:
            c.add(
                rp,
                "unsupported_at_fps",
                f"'{rule}' needs at least {spec.min_fps:g} processed frames/s",
            )
        if spec.zone_kinds and not any(k in zone_kinds for k in spec.zone_kinds):
            c.add(rp, "zone_required", f"'{rule}' needs a {' or '.join(spec.zone_kinds)} zone")
        if spec.needs_direction and not any(zone_kinds.get(k) for k in spec.zone_kinds):
            c.add(rp, "direction_required", f"'{rule}' needs a zone with a direction")

    # Thresholds: exact names read by rules.py, bounded values.
    th = config.get("thresholds")
    if not isinstance(th, dict):
        c.add("thresholds", "required", "thresholds object is required")
    else:
        known = set(REQUIRED_THRESHOLDS) | set(OPTIONAL_THRESHOLDS) | set(LIST_THRESHOLDS)
        for key in sorted(set(th) - known):
            c.add(f"thresholds.{key}", "unknown_threshold", "unknown threshold")
        values: dict[str, float | None] = {}
        for key, (lo, hi, integer) in REQUIRED_THRESHOLDS.items():
            if key not in th:
                c.add(f"thresholds.{key}", "required", "threshold is required by the rule engine")
            else:
                values[key] = c.number(f"thresholds.{key}", th[key], lo, hi, integer)
        for key, (lo, hi, integer) in OPTIONAL_THRESHOLDS.items():
            if key in th:
                c.number(f"thresholds.{key}", th[key], lo, hi, integer)
        if "crash_ignore_classes" in th:
            classes = th["crash_ignore_classes"]
            if not (
                isinstance(classes, list)
                and len(classes) <= len(VEHICLE_CLASSES)
                and all(x in VEHICLE_CLASSES for x in classes)
                and len(set(classes)) == len(classes)
            ):
                c.add(
                    "thresholds.crash_ignore_classes",
                    "unsupported_value",
                    f"must be a list of distinct classes from {', '.join(VEHICLE_CLASSES)}",
                )
        limit_kmh, very_high = values.get("speed_limit_kmh"), values.get("very_high_speed_kmh")
        if limit_kmh is not None and very_high is not None and very_high < limit_kmh:
            c.add(
                "thresholds.very_high_speed_kmh",
                "inconsistent",
                "must be greater than or equal to speed_limit_kmh",
            )

    model = config.get("model")
    if not isinstance(model, dict):
        c.add("model", "required", "model {id, sha256?} is required")
    else:
        for key in sorted(set(model) - {"id", "sha256"}):
            c.add(f"model.{key}", "unknown_field", "unknown field")
        if not (isinstance(model.get("id"), str) and MODEL_ID.match(model["id"])):
            c.add("model.id", "invalid_id", "must match ^[A-Za-z0-9._/-]{1,120}$")
        elif ".." in model["id"].split("/") or model["id"].startswith("/"):
            c.add("model.id", "invalid_id", "must be a relative model reference")
        if model.get("sha256") is not None and not (
            isinstance(model["sha256"], str) and SHA256.match(model["sha256"])
        ):
            c.add("model.sha256", "invalid_hash", "must be 64 lowercase hex characters")
    return c.errors


# Starting values the editor offers for a new camera. Conservative for a town road: a wide margin
# over the limit before a speed alert, long dwell before "stopped", dense and slow before
# "congestion". They are a starting point for a human, never applied without an approved version.
DEFAULT_THRESHOLDS: dict[str, float] = {
    "speed_limit_kmh": 50,
    "very_high_speed_kmh": 80,
    "stopped_speed_kmh": 3,
    "stopped_seconds": 60,
    "hard_brake_mps2": 5,
    "headway_seconds": 1,
    "headway_min_speed_kmh": 30,
    "lane_change_m": 3,
    "lane_change_window_s": 1.5,
    "wrong_way_min_px": 150,
    "congestion_vehicles": 12,
    "congestion_avg_speed_kmh": 5,
    "congestion_seconds": 30,
}
DEFAULT_ACQUISITION: dict[str, float] = {
    "target_fps": 10,
    "reconnect_backoff_s": 2,
    "read_timeout_s": 10,
    "max_reconnect_attempts": 100,
}
assert set(DEFAULT_THRESHOLDS) == set(REQUIRED_THRESHOLDS)
assert set(DEFAULT_ACQUISITION) == set(ACQUISITION)


def catalog() -> dict[str, Any]:
    """What ``validate`` accepts, as data: the editor builds its rule list, threshold fields and
    limits from this, so a form can never offer what the validator (and the worker) refuses."""

    defaults = {**DEFAULT_THRESHOLDS, **DEFAULT_ACQUISITION}

    def bounds(table: dict[str, tuple[float, float, bool]], required: bool) -> list[dict[str, Any]]:
        return [
            {
                "id": key,
                "min": lo,
                "max": hi,
                "integer": integer,
                "required": required,
                "default": defaults.get(key),
            }
            for key, (lo, hi, integer) in table.items()
        ]

    return {
        "schema_version": SCHEMA_VERSION,
        "coordinate_convention": COORDINATE_CONVENTION,
        "zone_kinds": list(ZONE_KINDS),
        "vehicle_classes": list(VEHICLE_CLASSES),
        "rules": [
            {
                "id": rule,
                "needs_calibration": spec.calibration,
                "min_fps": spec.min_fps,
                "zone_kinds": list(spec.zone_kinds),
                "needs_direction": spec.needs_direction,
            }
            for rule, spec in RULES.items()
        ],
        "thresholds": bounds(REQUIRED_THRESHOLDS, True) + bounds(OPTIONAL_THRESHOLDS, False),
        "acquisition": bounds(ACQUISITION, True),
        "limits": {"zones": 32, "polygon_points": 64, "frame_min": 64, "frame_max": 8192},
    }


def storable(value: Any) -> bool:
    """False for what JSONB cannot hold: NaN, Infinity and NUL characters, at any depth."""
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, str):
        return "\x00" not in value
    if isinstance(value, dict):
        return all(storable(k) and storable(v) for k, v in value.items())
    if isinstance(value, list):
        return all(storable(v) for v in value)
    return True


def min_fps(config: dict[str, Any]) -> float:
    """Minimum processing rate the enabled rules need (1 when none is known)."""
    rules = [r for r in config.get("rules") or [] if isinstance(r, str) and r in RULES]
    return max([1.0, *(RULES[r].min_fps for r in rules)])


# --------------------------------------------------------------------------- canonical form


def _canon(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _canon(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_canon(v) for v in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def canonicalize(config: dict[str, Any]) -> dict[str, Any]:
    """Stable form: integral floats become ints, order-insensitive lists are sorted. Zone and
    polygon order is kept (the pipeline assigns a point to the FIRST zone containing it)."""
    out: dict[str, Any] = _canon(config)
    if isinstance(out.get("rules"), list) and all(isinstance(r, str) for r in out["rules"]):
        out["rules"] = sorted(out["rules"])
    th = out.get("thresholds")
    if isinstance(th, dict) and isinstance(th.get("crash_ignore_classes"), list):
        th["crash_ignore_classes"] = sorted(map(str, th["crash_ignore_classes"]))
    frame = out.get("reference_frame")
    if isinstance(frame, dict):
        frame.setdefault("coordinate_convention", COORDINATE_CONVENTION)
    return out


def canonical_json(config: dict[str, Any]) -> str:
    return json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(config: dict[str, Any]) -> str:
    """SHA-256 of the canonical JSON (the worker recomputes it before applying)."""
    return hashlib.sha256(canonical_json(canonicalize(config)).encode()).hexdigest()


# --------------------------------------------------------------------------- diff


def _flatten(value: Any, path: str, out: dict[str, Any]) -> None:
    if isinstance(value, dict):
        if not value and path:
            out[path] = {}
        for key in sorted(value):
            _flatten(value[key], f"{path}.{key}" if path else str(key), out)
    elif (
        isinstance(value, list) and value and all(isinstance(v, dict) and "id" in v for v in value)
    ):
        for item in value:  # zones are compared by id, not by position
            _flatten({k: v for k, v in item.items() if k != "id"}, f"{path}[id={item['id']}]", out)
        out[f"{path}#order"] = [item["id"] for item in value]
    else:
        out[path] = value


def diff(before: dict[str, Any] | None, after: dict[str, Any]) -> list[dict[str, Any]]:
    """Sorted, deterministic list of {path, op, before, after} between canonical configs."""
    a: dict[str, Any] = {}
    b: dict[str, Any] = {}
    if before is not None:
        _flatten(canonicalize(before), "", a)
    _flatten(canonicalize(after), "", b)
    changes = []
    for path in sorted(set(a) | set(b)):
        if path not in a:
            changes.append({"path": path, "op": "added", "before": None, "after": b[path]})
        elif path not in b:
            changes.append({"path": path, "op": "removed", "before": a[path], "after": None})
        elif a[path] != b[path]:
            changes.append({"path": path, "op": "changed", "before": a[path], "after": b[path]})
    return changes
