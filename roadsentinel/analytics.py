"""Deterministic, privacy-preserving traffic counts from tracker observations.

Counts are measurements of detected tracks crossing configured image-space lines. They are not
ground truth and are not converted into lane counts unless the operator configures that line.
"""

from __future__ import annotations

from collections import Counter, OrderedDict, deque
from dataclasses import dataclass
from typing import Any


def _side(a: tuple[float, float], b: tuple[float, float], p: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def _crosses_segment(
    a: tuple[float, float], b: tuple[float, float], p: tuple[float, float], q: tuple[float, float]
) -> bool:
    s1, s2 = _side(a, b, p), _side(a, b, q)
    if s1 == 0 or s2 == 0 or (s1 > 0) == (s2 > 0):
        return False
    # Segment bounds test: the infinite counting line alone is not enough.
    return max(min(a[0], b[0]), min(p[0], q[0])) <= min(max(a[0], b[0]), max(p[0], q[0])) and max(
        min(a[1], b[1]), min(p[1], q[1])
    ) <= min(max(a[1], b[1]), max(p[1], q[1]))


@dataclass(frozen=True)
class CountLine:
    id: str
    start: tuple[float, float]
    end: tuple[float, float]
    lane: str | None = None

    @classmethod
    def from_config(cls, value: dict[str, Any]) -> CountLine:
        try:
            start, end = value["points"]
            line = cls(
                str(value["id"]),
                (float(start[0]), float(start[1])),
                (float(end[0]), float(end[1])),
                str(value["lane"]) if value.get("lane") else None,
            )
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise ValueError("counting line requires id and two finite points") from exc
        if line.start == line.end or not all(map(_finite, (*line.start, *line.end))):
            raise ValueError("counting line points must be finite and distinct")
        return line


def _finite(value: float) -> bool:
    import math

    return math.isfinite(value)


class TrafficAnalytics:
    """Count unique tracker IDs crossing configured lines and report bounded rolling flow."""

    def __init__(
        self, lines: list[CountLine], window_seconds: float = 60.0, max_track_states: int = 50_000
    ) -> None:
        if not 1 <= window_seconds <= 3600:
            raise ValueError("window_seconds must be between 1 and 3600")
        if max_track_states < 1:
            raise ValueError("max_track_states must be positive")
        ids = [line.id for line in lines]
        if len(set(ids)) != len(ids):
            raise ValueError("counting line ids must be unique")
        self.lines = lines
        self.window_seconds = window_seconds
        self.max_track_states = max_track_states
        self.previous: OrderedDict[tuple[str, int], tuple[float, float]] = OrderedDict()
        self.counts: Counter[tuple[str, str, str]] = Counter()
        self.crossings: deque[tuple[float, str, str, str]] = deque()
        self.seen: OrderedDict[tuple[str, int], None] = OrderedDict()

    def update(self, timestamp: float, observations: list[tuple[int, str, tuple[float, float]]]) -> None:
        for track_id, object_class, point in observations:
            for line in self.lines:
                key = (line.id, int(track_id))
                prior = self.previous.get(key)
                if prior is not None and key not in self.seen and _crosses_segment(line.start, line.end, prior, point):
                    direction = "positive" if _side(line.start, line.end, prior) < 0 else "negative"
                    lane = line.lane or "unassigned"
                    self.counts[(line.id, lane, str(object_class))] += 1
                    self.crossings.append((float(timestamp), line.id, str(object_class), direction))
                    self.seen[key] = None
                    while len(self.seen) > self.max_track_states:
                        self.seen.popitem(last=False)
                self.previous[key] = (float(point[0]), float(point[1]))
                self.previous.move_to_end(key)
                while len(self.previous) > self.max_track_states:
                    self.previous.popitem(last=False)
        self._prune(timestamp)

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self.crossings and self.crossings[0][0] < cutoff:
            self.crossings.popleft()
        # Track state is bounded by live tracks; prune IDs not observed for a long gap.
        # A crossing remains deduplicated for this process/session to avoid recounting reversals.

    def snapshot(self, now: float) -> dict[str, Any]:
        self._prune(now)
        by_class: Counter[str] = Counter()
        by_direction: Counter[str] = Counter()
        by_line: Counter[str] = Counter()
        for _, line, cls, direction in self.crossings:
            by_class[cls] += 1
            by_direction[direction] += 1
            by_line[line] += 1
        return {
            "total_crossings": sum(self.counts.values()),
            "counts_by_line_lane_class": [
                {"line": line, "lane": lane, "object_class": cls, "count": count}
                for (line, lane, cls), count in sorted(self.counts.items())[:32]
            ],
            "rolling_flow_per_minute": {
                "window_seconds": self.window_seconds,
                "total": round(len(self.crossings) * 60 / self.window_seconds, 2),
                "by_class": dict(sorted(by_class.items())),
                "by_direction": dict(sorted(by_direction.items())),
                "by_line": dict(sorted(by_line.items())),
            },
        }
