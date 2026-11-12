"""Typed, explainable rules evaluated on tracked objects.

Each rule fires at most once per track (or once per cooldown for scene-level rules)
and returns an event dict describing exactly which threshold was crossed.

Terminology: the engine produces *events* (a rule matched on a track). Whether an event becomes an
*alert* sent to operators is decided afterwards by roadsentinel/alerts.py (dedupe, cooldowns,
rate limits). Rules are NOT validated on real footage until the evaluation harness (training/eval.py)
says so; see docs/RULES.md for each definition.

Sampling rate: the defaults need ~5 samples per second. Cameras that deliver far fewer frames per
second (a slow live stream) set `speed_window_s`, `speed_min_samples`, `sustain_s`,
`sustain_samples`, ... in their config (see docs/RULES.md). Alerts produced that way carry
`details.confidence = "low"`. Rules that cannot work at the measured rate are switched off and
reported by `rule_capabilities()` instead of silently never firing.
"""
from collections import defaultdict, deque

import numpy as np

VEHICLES = {"car", "truck", "bus", "motorcycle"}

# type -> (priority, Romanian label)
EVENT_TYPES = {
    "wrong_way": ("critical", "Sens interzis"),
    "pedestrian_on_road": ("critical", "Pieton pe carosabil"),
    "probable_crash": ("high", "Posibilă coliziune – necesită verificare"),
    "very_high_speed": ("high", "Viteză foarte mare"),
    "stopped_emergency_lane": ("high", "Vehicul oprit pe banda de urgență"),
    "stopped_on_road": ("high", "Vehicul oprit pe carosabil"),
    "hard_braking": ("medium", "Frânare bruscă"),
    "tailgating": ("medium", "Distanță prea mică"),
    "dangerous_lane_change": ("medium", "Schimbare de bandă periculoasă"),
    "congestion": ("info", "Aglomerare"),
    "near_miss": ("high", "Aproape de coliziune"),
    "object_on_roadway": ("critical", "Obiect pe carosabil"),
}

# Defaults of the sampling-dependent parameters (normal sources: >= ~5 fps).
RATE_DEFAULTS = {
    "speed_window_s": 1.0, "speed_min_samples": 5,
    "sustain_s": 1.0, "sustain_samples": 5,
    "wrong_way_window_s": 2.0, "wrong_way_min_samples": 20,
    "hard_brake_window_s": 1.4, "hard_brake_min_samples": 10,
}


def _p(th, key):
    return th.get(key, RATE_DEFAULTS[key])


def rule_capabilities(th, fps, rules=None):
    """Which rules can work at a measured frame rate, computed from the camera's own sampling
    parameters (not hard-coded per camera). Returns {rule: {"supported", "min_fps", "reason"}}."""
    speed_fps = _p(th, "speed_min_samples") / _p(th, "speed_window_s")
    sustain_fps = _p(th, "sustain_samples") / _p(th, "sustain_s")
    need = {
        "very_high_speed": max(speed_fps, sustain_fps),
        "stopped_on_road": speed_fps, "stopped_emergency_lane": speed_fps,
        "tailgating": speed_fps, "congestion": speed_fps, "near_miss": speed_fps,
        "hard_braking": max(speed_fps, _p(th, "hard_brake_min_samples") / _p(th, "hard_brake_window_s")),
        "probable_crash": max(speed_fps, _p(th, "hard_brake_min_samples") / _p(th, "hard_brake_window_s")),
        "wrong_way": max(speed_fps, _p(th, "wrong_way_min_samples") / _p(th, "wrong_way_window_s")),
        "dangerous_lane_change": 5 / th.get("lane_change_window_s", 1.5),
        "pedestrian_on_road": 0.0, "object_on_roadway": 0.0,
    }
    out = {}
    for rule in (rules if rules is not None else need):
        m = need.get(rule, 0.0)
        ok = fps is None or fps >= m * 0.95  # 5 % slack for jittery frame timing
        out[rule] = {"supported": ok, "min_fps": round(m, 2),
                     "reason": None if ok else f"necesită ≥ {m:.1f} cadre/s, camera dă {fps:.2f}"}
    return out


class Track:
    def __init__(self, tid, cls):
        self.id = tid
        self.cls = cls
        self.px = deque(maxlen=150)      # (t, x, y) bottom-centre pixels
        self.m = deque(maxlen=150)       # (t, x_m, y_m) road-plane metres
        self.speeds = deque(maxlen=150)  # (t, km/h)
        self.zone = None
        self.bbox = None
        self.stopped_since = None
        self.tailgate_since = None
        self.fired = set()

    def age(self):
        return self.px[-1][0] - self.px[0][0] if self.px else 0.0

    def speed_kmh(self):
        return self.speeds[-1][1] if self.speeds else None

    def window(self, seq, seconds):
        if not seq:
            return []
        t_end = seq[-1][0]
        return [s for s in seq if s[0] >= t_end - seconds]


class RuleEngine:
    def __init__(self, zones, thresholds, rules=None):
        self.enabled = set(EVENT_TYPES if rules is None else rules)
        self.zones = zones
        self.th = thresholds
        self.tracks = {}
        self.collision_pairs = set()
        self.congestion_since = {}     # zone id -> time the jam started
        self.congestion_fired_at = {}
        self.class_counts = defaultdict(int)
        self.unsupported = {}          # rule -> reason, set by set_rate() from the measured fps
        self.low_rate = (_p(thresholds, "speed_window_s") > RATE_DEFAULTS["speed_window_s"]
                         or _p(thresholds, "speed_min_samples") < RATE_DEFAULTS["speed_min_samples"])

    def set_rate(self, fps):
        """Switch off rules that cannot work at the measured frame rate; returns the capability map."""
        caps = rule_capabilities(self.th, fps, sorted(self.enabled))
        self.unsupported = {r: c["reason"] for r, c in caps.items() if not c["supported"]}
        return caps

    def update(self, t, detections, calib):
        """detections: list of (track_id, cls, (x, y) bottom-centre px, bbox). Returns new events."""
        events = []
        seen = set()
        for tid, cls, pt, bbox in detections:
            tr = self.tracks.get(tid)
            if tr is None:
                tr = self.tracks[tid] = Track(tid, cls)
                self.class_counts[cls] += 1
            seen.add(tid)
            tr.bbox = bbox
            tr.px.append((t, pt[0], pt[1]))
            if calib is not None:
                mx, my = calib.to_metres([pt])[0]
                tr.m.append((t, float(mx), float(my)))
            tr.zone = next((z for z in self.zones if z.contains(pt)), None)
            self._update_speed(tr)
            events += self._check_track(t, tr)
        events += self._check_scene(t, seen)
        return events

    def _update_speed(self, tr):
        window = _p(self.th, "speed_window_s")
        w = tr.window(tr.m, window)
        if len(w) < _p(self.th, "speed_min_samples") or w[-1][0] - w[0][0] < self.th.get("speed_min_span_s", 0.5 * window):
            return
        # Least-squares slope over the window: robust to per-frame box jitter.
        ts = np.array([s[0] for s in w])
        vx = np.polyfit(ts, [s[1] for s in w], 1)[0]
        vy = np.polyfit(ts, [s[2] for s in w], 1)[0]
        tr.speeds.append((w[-1][0], float(np.hypot(vx, vy)) * 3.6))

    def _event(self, etype, tr, rule, speed=None, **details):
        priority, label = EVENT_TYPES[etype]
        speed = speed if speed is not None else (tr.speed_kmh() if tr else None)
        if self.low_rate:
            details.setdefault("confidence", "low")
            details.setdefault("rate_mode", "low_fps")
        return {"type": etype, "priority": priority, "label": label, "rule": rule,
                "track_id": tr.id if tr else None, "object_class": tr.cls if tr else None,
                "speed_kmh": round(speed, 1) if speed else None,
                "bbox": tr.bbox if tr else None, "details": details}

    def _fire_once(self, tr, etype):
        if etype not in self.enabled or etype in self.unsupported or etype in tr.fired:
            return False
        tr.fired.add(etype)
        return True

    def _check_track(self, t, tr):
        th, out = self.th, []
        z = tr.zone
        speed = tr.speed_kmh()

        if tr.cls == "object":
            # Debris: a static object lying in a road zone for object_seconds (position stays put).
            if z and z.kind in ("carriageway", "emergency_lane"):
                ow = tr.window(tr.m, th.get("object_seconds", 5.0))
                dwell = ow[-1][0] - ow[0][0] if ow else 0.0
                if dwell >= th.get("object_seconds", 5.0) * 0.95 and len(ow) >= 2:
                    drift = max(np.hypot(a[1] - ow[-1][1], a[2] - ow[-1][2]) for a in ow)
                    if drift <= th.get("object_max_drift_m", 0.5) and self._fire_once(tr, "object_on_roadway"):
                        out.append(self._event("object_on_roadway", tr,
                                               f"Obiect nemișcat {dwell:.0f} s în zona „{z.name}” (deplasare ≤ {drift:.1f} m)",
                                               zone=z.id, dwell_s=round(dwell, 1)))
            return out
        if tr.cls == "person":
            if z and z.kind in ("carriageway", "emergency_lane") and self._fire_once(tr, "pedestrian_on_road"):
                out.append(self._event("pedestrian_on_road", tr, f"Persoană detectată în zona „{z.name}”", zone=z.id))
            return out
        # Speeds need ~1 s of stable history before any rule may use them.
        if tr.cls not in VEHICLES or speed is None or tr.age() < th.get("min_track_age_s", 1.0):
            return out

        # Very high speed: sustained for 1 s above threshold.
        recent = [s for _, s in tr.window(tr.speeds, _p(th, "sustain_s"))]
        if len(recent) >= _p(th, "sustain_samples") and min(recent) > th["very_high_speed_kmh"] and self._fire_once(tr, "very_high_speed"):
            out.append(self._event("very_high_speed", tr, speed=float(np.median(recent)), rule=
                                   f"Viteză {np.median(recent):.0f} km/h > prag {th['very_high_speed_kmh']} km/h (limită {th['speed_limit_kmh']})",
                                   limit_kmh=th["speed_limit_kmh"], measured_kmh=round(float(np.median(recent)), 1)))

        # Stopped vehicle (dwell time).
        if speed < th["stopped_speed_kmh"]:
            tr.stopped_since = tr.stopped_since or t
            dwell = t - tr.stopped_since
            if z and dwell >= th["stopped_seconds"]:
                etype = "stopped_emergency_lane" if z.kind == "emergency_lane" else "stopped_on_road"
                if self._fire_once(tr, etype):
                    out.append(self._event(etype, tr, f"Staționare {dwell:.0f} s ≥ {th['stopped_seconds']} s în „{z.name}”",
                                           zone=z.id, dwell_s=round(dwell, 1)))
        else:
            tr.stopped_since = None

        # Wrong way: moving against the zone's direction for the last 2 s, step after step
        # (a tracker ID jumping between two cars gives one big jump, not steady motion).
        ww = _p(th, "wrong_way_window_s")
        pw = tr.window(tr.px, ww)
        if (z and z.direction is not None and len(pw) >= _p(th, "wrong_way_min_samples")
                and pw[-1][0] - pw[0][0] > 0.75 * ww and speed > 10):
            steps = np.diff(np.array([(x, y) for _, x, y in pw]), axis=0) @ z.direction
            against = -float(steps.sum())
            steady = (steps < 0).mean() > 0.7
            if against > th["wrong_way_min_px"] and steady and self._fire_once(tr, "wrong_way"):
                out.append(self._event("wrong_way", tr, f"Deplasare {against:.0f} px contra sensului zonei „{z.name}”", zone=z.id))

        # Hard braking: mean speed 1 s ago vs now (two separate 0.4 s windows).
        hw = _p(th, "hard_brake_window_s")
        w = tr.window(tr.speeds, hw)
        if len(w) >= _p(th, "hard_brake_min_samples") and w[-1][0] - w[0][0] > hw - 0.2:
            before = [s for ts, s in w if ts <= w[0][0] + 0.4]
            after = [s for ts, s in w if ts >= w[-1][0] - 0.4]
            v0, v1 = float(np.mean(before)), float(np.mean(after))
            decel = (v0 - v1) / 3.6 / (w[-1][0] - w[0][0] - 0.4)
            if decel > th["hard_brake_mps2"] and v0 > 30:
                tr.hard_brake_at = (t, v0, decel)  # remembered for the probable-crash rule below
            if decel > th["hard_brake_mps2"] and v0 > 30 and self._fire_once(tr, "hard_braking"):
                out.append(self._event("hard_braking", tr, f"Decelerare {decel:.1f} m/s² > {th['hard_brake_mps2']} m/s²",
                                       decel_mps2=round(decel, 2), from_kmh=round(v0, 1), to_kmh=round(v1, 1)))

        # A hard stop alone is ordinary traffic. Only a calibrated, sustained two-vehicle
        # closing episode may raise a review-only collision candidate. Contact is never inferred.
        hb = getattr(tr, "hard_brake_at", None)
        # crash_ignore_classes: e.g. [bus] where trams (detected as buses) brake hard at every stop.
        if (hb and z and z.kind in ("carriageway", "emergency_lane") and speed < th["stopped_speed_kmh"]
                and tr.cls not in th.get("crash_ignore_classes", ())):
            stop_at = getattr(tr, "crash_stop_at", None)
            if stop_at is None and t - hb[0] <= th.get("crash_window_s", 4.0):
                tr.crash_stop_at = stop_at = t
                tr.crash_partner = self._collision_partner(tr, t)
            hold = th.get("crash_stationary_s", 2.0)
            partner = getattr(tr, "crash_partner", None)
            pair = tuple(sorted((tr.id, partner[0]))) if partner else None
            if (stop_at is not None and t - stop_at >= hold and pair
                    and pair not in self.collision_pairs and self._fire_once(tr, "probable_crash")):
                self.collision_pairs.add(pair)
                out.append(self._event("probable_crash", tr,
                                       f"Două vehicule s-au apropiat, unul a frânat de la {hb[1]:.0f} km/h "
                                       f"și a rămas oprit {t - stop_at:.1f} s; contactul nu este demonstrat",
                                       zone=z.id, from_kmh=round(hb[1], 1), decel_mps2=round(hb[2], 2),
                                       stationary_s=round(t - stop_at, 1), partner_track_id=partner[0],
                                       closing_distance_m=partner[1], distance_at_stop_m=partner[2],
                                       confidence="low", review_only=True, contact_observed=False))
        elif speed >= th["stopped_speed_kmh"]:
            tr.crash_stop_at = None  # moving again: the stop was not an impact
            tr.crash_partner = None

        # Tailgating: time headway to the vehicle ahead in the same lane.
        if z and z.kind == "carriageway" and speed > th["headway_min_speed_kmh"]:
            lead, gap = self._vehicle_ahead(tr, z)
            headway = gap / (speed / 3.6) if lead is not None else None
            if headway is None or headway >= th["headway_seconds"]:
                tr.tailgate_since = None
            else:
                # Must hold for 1 s, so a single noisy frame can't raise an alert.
                tr.tailgate_since = tr.tailgate_since or t
                if t - tr.tailgate_since >= 1.0 and self._fire_once(tr, "tailgating"):
                    out.append(self._event("tailgating", tr,
                                           f"Distanță {gap:.0f} m = {headway:.2f} s la {speed:.0f} km/h (< {th['headway_seconds']} s)",
                                           gap_m=round(gap, 1), headway_s=round(headway, 2), lead_track=lead.id))

        # Dangerous lane change: big lateral move with a vehicle close by.
        lw = tr.window(tr.m, th["lane_change_window_s"])
        if z and z.kind == "carriageway" and len(lw) >= 5:
            lateral = abs(lw[-1][1] - lw[0][1])
            if lateral > th["lane_change_m"]:
                near = self._nearest(tr)
                if near is not None and near < 15 and self._fire_once(tr, "dangerous_lane_change"):
                    out.append(self._event("dangerous_lane_change", tr,
                                           f"Deplasare laterală {lateral:.1f} m în {th['lane_change_window_s']} s, vecin la {near:.0f} m",
                                           lateral_m=round(lateral, 1), nearest_m=round(near, 1)))
        return out

    def _active(self, tr):
        return [o for o in self.tracks.values()
                if o is not tr and o.m and o.cls in VEHICLES and o.m[-1][0] >= tr.m[-1][0] - 0.1]

    def _vehicle_ahead(self, tr, zone):
        x, y = tr.m[-1][1], tr.m[-1][2]
        # Ahead means further along the expected direction (image down -> larger y_m).
        sign = 1 if zone.direction[1] > 0 else -1
        best, best_gap = None, None
        for o in self._active(tr):
            if o.zone is not zone:
                continue
            ox, oy = o.m[-1][1], o.m[-1][2]
            gap = (oy - y) * sign
            if abs(ox - x) < 1.6 and gap > 0 and (best_gap is None or gap < best_gap):
                best, best_gap = o, gap
        return best, best_gap

    def _nearest(self, tr):
        x, y = tr.m[-1][1], tr.m[-1][2]
        d = [np.hypot(o.m[-1][1] - x, o.m[-1][2] - y) for o in self._active(tr)]
        return min(d) if d else None

    def _collision_partner(self, tr, t):
        """Return a stable, same-zone vehicle whose measured gap closed before the stop.

        Road-plane positions are required; no calibration means no candidate. This is
        only interaction evidence for human review, never proof of physical contact.
        """
        if not tr.m or tr.age() < self.th.get("min_track_age_s", 1.0):
            return None
        window = self.th.get("crash_interaction_s", 2.0)
        min_samples = max(5, int(_p(self.th, "speed_min_samples")))
        best = None
        for other in self._active(tr):
            if other.zone is not tr.zone or other.age() < self.th.get("min_track_age_s", 1.0):
                continue
            a = {round(s[0], 3): s for s in tr.window(tr.m, window)}
            b = {round(s[0], 3): s for s in other.window(other.m, window)}
            common = sorted(a.keys() & b.keys())
            if len(common) < min_samples or common[-1] - common[0] < min(1.0, window * 0.7):
                continue
            gaps = [float(np.hypot(a[c][1] - b[c][1], a[c][2] - b[c][2])) for c in common]
            final_gap = gaps[-1]
            closing = gaps[0] - final_gap
            if (final_gap > self.th.get("crash_partner_max_m", 5.0)
                    or closing < self.th.get("crash_min_closing_m", 3.0)
                    or abs(a[common[-1]][1] - b[common[-1]][1]) > self.th.get("crash_lateral_max_m", 2.5)):
                continue
            # The partner must itself have moved recently, excluding a fixed obstacle
            # or long-parked vehicle from this vehicle-interaction rule.
            partner_motion = float(np.hypot(b[common[-1]][1] - b[common[0]][1],
                                            b[common[-1]][2] - b[common[0]][2]))
            if partner_motion < self.th.get("crash_partner_min_motion_m", 2.0):
                continue
            toward_partner = ((a[common[-1]][1] - a[common[0]][1]) * (b[common[0]][1] - a[common[0]][1])
                              + (a[common[-1]][2] - a[common[0]][2]) * (b[common[0]][2] - a[common[0]][2]))
            if toward_partner <= 0:
                continue
            if best is None or final_gap < best[2]:
                best = (other.id, round(closing, 2), round(final_gap, 2))
        return best

    def _check_near_miss(self, t, seen):
        """Near miss = two moving vehicles closing on each other with a time-to-collision below
        `near_miss_ttc_s` while closer than `near_miss_max_m`. Closing speed is the slope of their
        road-plane distance over the speed window (needs >= speed_min_samples for both)."""
        th, out = self.th, []
        window = _p(th, "speed_window_s")
        veh = [self.tracks[i] for i in seen if self.tracks[i].cls in VEHICLES and self.tracks[i].speed_kmh() is not None
               and self.tracks[i].speed_kmh() > th.get("near_miss_min_kmh", 15)]
        for i, a in enumerate(veh):
            for b in veh[i + 1:]:
                key = ("near_miss", min(a.id, b.id), max(a.id, b.id))
                if key in a.fired:
                    continue
                wa, wb = a.window(a.m, window), b.window(b.m, window)
                common = sorted({x[0] for x in wa} & {x[0] for x in wb})
                if len(common) < _p(th, "speed_min_samples"):
                    continue
                pa, pb = {x[0]: x for x in wa}, {x[0]: x for x in wb}
                d = np.array([np.hypot(pa[c][1] - pb[c][1], pa[c][2] - pb[c][2]) for c in common])
                closing = -float(np.polyfit(np.array(common), d, 1)[0])  # m/s, positive = approaching
                dist = float(d[-1])
                if closing <= 0.5 or dist > th.get("near_miss_max_m", 15.0):
                    continue
                ttc = dist / closing
                if ttc < th.get("near_miss_ttc_s", 1.5) and "near_miss" in self.enabled and "near_miss" not in self.unsupported:
                    a.fired.add(key)
                    b.fired.add(key)
                    ev = self._event("near_miss", a,
                                     f"Timp până la coliziune {ttc:.1f} s < {th.get('near_miss_ttc_s', 1.5)} s, "
                                     f"distanță {dist:.1f} m, apropiere {closing * 3.6:.0f} km/h (#{a.id} și #{b.id})",
                                     other_track=b.id, ttc_s=round(ttc, 2), distance_m=round(dist, 1),
                                     closing_kmh=round(closing * 3.6, 1))
                    out.append(ev)
        return out

    def _check_scene(self, t, seen):
        """Congestion, evaluated per carriageway: one direction can jam while the other flows."""
        th, out = self.th, []
        out += self._check_near_miss(t, seen)
        # Scene-level congestion consumes the same calibrated speed estimates as vehicle-level
        # rules.  It must respect the measured-rate capability gate too; otherwise a sparse
        # source can eventually accumulate a misleading dwell and emit despite being marked
        # unsupported by set_rate().
        if "congestion" not in self.enabled or "congestion" in self.unsupported:
            return out
        for z in self.zones:
            if z.kind != "carriageway":
                continue
            on_road = [self.tracks[i] for i in seen if self.tracks[i].zone is z
                       and self.tracks[i].cls in VEHICLES and self.tracks[i].speed_kmh() is not None]
            avg = float(np.mean([tr.speed_kmh() for tr in on_road])) if on_road else None
            if len(on_road) < th["congestion_vehicles"] or avg >= th["congestion_avg_speed_kmh"]:
                self.congestion_since.pop(z.id, None)
                continue
            since = self.congestion_since.setdefault(z.id, t)
            if t - since >= th["congestion_seconds"] and t - self.congestion_fired_at.get(z.id, -1e9) > 60:
                self.congestion_fired_at[z.id] = t
                priority, label = EVENT_TYPES["congestion"]
                out.append({"type": "congestion", "priority": priority, "label": label, "track_id": None,
                            "object_class": None, "speed_kmh": round(avg, 1), "bbox": None,
                            "rule": f"„{z.name}”: {len(on_road)} vehicule, viteză medie {avg:.0f} km/h < "
                                    f"{th['congestion_avg_speed_kmh']} km/h timp de {th['congestion_seconds']} s",
                            "details": {"zone": z.id, "vehicles": len(on_road), "avg_speed_kmh": round(avg, 1)}})
        return out
