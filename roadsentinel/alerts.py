"""From events to alerts.

The rule engine (rules.py) emits *events*: "this rule matched on this track". An *alert* is an event
that survived this gate and is sent to operators. The gate removes duplicates that come from the
tracker (an ID switch re-fires the same rule on the same vehicle), enforces per-type cooldowns
and caps how many alerts per minute a camera may raise, so one bad scene cannot flood a dispatcher.

Configuration (camera yaml, all optional):
    alerts:
      dedupe_s: 8            # same type + zone + near the same place within this time = duplicate
      dedupe_px: 200         # "near" in image pixels (bbox centre)
      cooldown_s: {congestion: 120, very_high_speed: 5}   # per type, per camera
      max_per_minute: 12     # per camera, critical events are never dropped by this cap
Everything suppressed is counted and reported, never silently lost.
"""
from collections import Counter, deque

DEFAULTS = {"dedupe_s": 8.0, "dedupe_px": 200.0, "cooldown_s": {}, "max_per_minute": 12}


def _centre(bbox):
    return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2) if bbox else None


class AlertGate:
    def __init__(self, config=None):
        cfg = {**DEFAULTS, **(config or {})}
        self.dedupe_s = float(cfg["dedupe_s"])
        self.dedupe_px = float(cfg["dedupe_px"])
        self.cooldown_s = dict(cfg["cooldown_s"])
        self.max_per_minute = int(cfg["max_per_minute"])
        self.recent = deque()          # (t, type, zone, centre) of alerts that passed
        self.last_by_type = {}
        self.sent_times = deque()
        self.suppressed = Counter()    # reason -> count

    def filter(self, t, events):
        """Return the events that become alerts, in order. `t` is stream time in seconds."""
        out = []
        while self.recent and t - self.recent[0][0] > self.dedupe_s:
            self.recent.popleft()
        while self.sent_times and t - self.sent_times[0] > 60:
            self.sent_times.popleft()
        for e in events:
            reason = self._reject(t, e)
            if reason:
                self.suppressed[reason] += 1
                continue
            out.append(e)
            self.recent.append((t, e["type"], (e.get("details") or {}).get("zone"), _centre(e.get("bbox"))))
            self.last_by_type[e["type"]] = t
            self.sent_times.append(t)
        return out

    def _reject(self, t, e):
        cd = self.cooldown_s.get(e["type"])
        if cd and t - self.last_by_type.get(e["type"], -1e9) < cd:
            return "cooldown"
        c = _centre(e.get("bbox"))
        zone = (e.get("details") or {}).get("zone")
        for _, typ, z, rc in self.recent:
            if typ == e["type"] and z == zone and (c is None or rc is None
                                                   or ((c[0] - rc[0]) ** 2 + (c[1] - rc[1]) ** 2) ** 0.5 <= self.dedupe_px):
                return "duplicate"
        if e.get("priority") != "critical" and len(self.sent_times) >= self.max_per_minute:
            return "rate_limit"
        return None

    def stats(self):
        return dict(self.suppressed)
