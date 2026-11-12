"""Process-level metrics in the Prometheus text format (no external dependency).

Counters and histograms are per process and reset on restart. Tenant data (alerts per type, camera
heartbeat age) is NOT in here: it lives behind row-level security and is served, per tenant, by
GET /api/ops/status. /api/metrics itself is off unless RS_METRICS_TOKEN is set.
"""

from __future__ import annotations

import threading
import time
import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from collections import defaultdict

BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


class Registry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self.hist: dict[tuple[str, tuple[tuple[str, str], ...]], list[float]] = {}
        self.gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}

    @staticmethod
    def _key(name: str, labels: dict[str, str]) -> tuple[str, tuple[tuple[str, str], ...]]:
        return name, tuple(sorted(labels.items()))

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        with self._lock:
            self.counters[self._key(name, labels)] += value

    def set_gauge(self, name: str, value: float, **labels: str) -> None:
        with self._lock:
            self.gauges[self._key(name, labels)] = value

    def observe(self, name: str, seconds: float, **labels: str) -> None:
        with self._lock:
            h = self.hist.setdefault(self._key(name, labels), [0.0] * (len(BUCKETS) + 2))
            for i, b in enumerate(BUCKETS):
                if seconds <= b:
                    h[i] += 1
            h[len(BUCKETS)] += 1  # +Inf bucket == count
            h[len(BUCKETS) + 1] += seconds  # sum

    def render(self) -> str:
        def fmt(labels: tuple[tuple[str, str], ...], extra: str = "") -> str:
            parts = [f'{k}="{v}"' for k, v in labels] + ([extra] if extra else [])
            return "{" + ",".join(parts) + "}" if parts else ""

        lines: list[str] = []
        with self._lock:
            for (name, labels), v in sorted(self.counters.items()):
                lines.append(f"{name}{fmt(labels)} {v:g}")
            for (name, labels), v in sorted(self.gauges.items()):
                lines.append(f"{name}{fmt(labels)} {v:g}")
            for (name, labels), h in sorted(self.hist.items()):
                for i, b in enumerate(BUCKETS):
                    lines.append(f"{name}_bucket{fmt(labels, f'le=\"{b:g}\"')} {h[i]:g}")
                lines.append(f"{name}_bucket{fmt(labels, 'le=\"+Inf\"')} {h[len(BUCKETS)]:g}")
                lines.append(f"{name}_count{fmt(labels)} {h[len(BUCKETS)]:g}")
                lines.append(f"{name}_sum{fmt(labels)} {h[len(BUCKETS) + 1]:.6f}")
        return "\n".join(lines) + "\n"


metrics = Registry()


# Bounded-cardinality reliability metrics API merged from the camera/casework workstream.
STARTED_AT = time.time()
# Seconds. Covers a fast DB read up to a slow storage call; everything above lands in +Inf.
REMOTE_REMOTE_BUCKETS: tuple[float, ...] = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
MAX_SERIES = 200

_NAME = re.compile(r"^rs_[a-z][a-z0-9_]{0,62}$")
_LABEL_KEY = re.compile(r"^[a-z][a-z0-9_]{0,30}$")
# Route templates ("/api/media/{evidence_id}"), methods, status classes, outcome codes.
_LABEL_VALUE = re.compile(r"^[A-Za-z0-9_./{}-]{1,96}$")


@dataclass
class _Series:
    buckets: list[int]
    count: int = 0
    total: float = 0.0


@dataclass
class _Histogram:
    help: str
    labels: tuple[str, ...]
    series: dict[tuple[str, ...], _Series] = field(default_factory=dict)


_lock = threading.Lock()
_metrics: dict[str, _Histogram] = {}
_dropped: dict[str, int] = {}


def register(name: str, help_text: str, labels: tuple[str, ...]) -> None:
    """Declare a duration histogram. Re-registering with the same labels is a no-op."""
    if not _NAME.match(name) or not all(_LABEL_KEY.match(k) for k in labels):
        raise ValueError(f"invalid metric or label name: {name}")
    if len(set(labels)) != len(labels):
        raise ValueError(f"duplicate label key in {name}")
    with _lock:
        existing = _metrics.get(name)
        if existing is not None:
            if existing.labels != tuple(labels):
                raise ValueError(f"metric {name} already registered with other labels")
            return
        _metrics[name] = _Histogram(help_text.replace("\n", " "), tuple(labels))


def observe(name: str, seconds: float, **labels: str) -> None:
    """Record one duration. Refuses unknown metrics, label keys and free-text label values."""
    metric = _metrics.get(name)
    if metric is None:
        raise ValueError(f"unknown metric {name}")
    if set(labels) != set(metric.labels):
        raise ValueError(f"{name} takes exactly the labels {metric.labels}")
    key = tuple(str(labels[k]) for k in metric.labels)
    for value in key:
        if not _LABEL_VALUE.match(value):
            raise ValueError(f"label value not allowed for {name}")
    seconds = max(0.0, float(seconds))
    with _lock:
        series = metric.series.get(key)
        if series is None:
            if len(metric.series) >= MAX_SERIES:
                _dropped[name] = _dropped.get(name, 0) + 1
                return
            series = metric.series[key] = _Series([0] * len(REMOTE_BUCKETS))
        series.count += 1
        series.total += seconds
        for i, bound in enumerate(REMOTE_BUCKETS):
            if seconds <= bound:
                series.buckets[i] += 1


@contextmanager
def timed(name: str, **labels: str) -> Iterator[dict[str, str]]:
    """Time a block. The yielded dict can change label values (e.g. ``outcome``) before exit;
    an exception that escapes without setting ``outcome`` is recorded as ``error``."""
    current = dict(labels)
    started = time.perf_counter()
    try:
        yield current
    except BaseException:
        if current.get("outcome") == labels.get("outcome") and "outcome" in current:
            current["outcome"] = "error"
        raise
    finally:
        observe(name, time.perf_counter() - started, **current)


def series_count(name: str) -> int:
    with _lock:
        return len(_metrics[name].series)


def reset() -> None:
    """Forget all observations (tests). Registrations stay."""
    with _lock:
        for metric in _metrics.values():
            metric.series.clear()
        _dropped.clear()


def _fmt_labels(keys: tuple[str, ...], values: tuple[str, ...], extra: str = "") -> str:
    parts = [f'{k}="{v}"' for k, v in zip(keys, values, strict=True)]
    if extra:
        parts.append(extra)
    return "{" + ",".join(parts) + "}" if parts else ""


def _pool_stats() -> dict[str, int]:
    from app.db import get_engine

    pool = get_engine().pool
    out: dict[str, int] = {}
    for stat in ("size", "checkedin", "checkedout", "overflow"):
        fn = getattr(pool, stat, None)
        if callable(fn):
            out[stat] = int(fn())
    return out


def render_prometheus() -> str:
    """Prometheus text exposition format 0.0.4."""
    lines = [
        "# HELP rs_process_uptime_seconds Seconds since this API process started.",
        "# TYPE rs_process_uptime_seconds gauge",
        f"rs_process_uptime_seconds {time.time() - STARTED_AT:.3f}",
        "# HELP rs_db_pool_connections Runtime database pool (this process).",
        "# TYPE rs_db_pool_connections gauge",
    ]
    for stat, value in _pool_stats().items():
        lines.append(f'rs_db_pool_connections{{state="{stat}"}} {value}')
    with _lock:
        for name, metric in sorted(_metrics.items()):
            lines += [f"# HELP {name} {metric.help}", f"# TYPE {name} histogram"]
            for key, s in sorted(metric.series.items()):
                plain = _fmt_labels(metric.labels, key)
                bounds = [*(str(b) for b in REMOTE_BUCKETS), "+Inf"]
                for bound, n in zip(bounds, [*s.buckets, s.count], strict=True):
                    le = _fmt_labels(metric.labels, key, 'le="' + bound + '"')
                    lines.append(f"{name}_bucket{le} {n}")
                lines.append(f"{name}_sum{plain} {s.total:.6f}")
                lines.append(f"{name}_count{plain} {s.count}")
        lines += [
            "# HELP rs_metrics_dropped_total Observations dropped by the per-metric series cap.",
            "# TYPE rs_metrics_dropped_total counter",
        ]
        for name, n in sorted(_dropped.items()):
            lines.append(f'rs_metrics_dropped_total{{metric="{name}"}} {n}')
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- platform metrics

HTTP_DURATION = "rs_http_request_duration_seconds"
EVIDENCE_READ = "rs_evidence_read_seconds"

register(
    HTTP_DURATION,
    "Time from request receipt to response headers, by route template (not raw path).",
    ("route", "method", "status_class"),
)
register(
    EVIDENCE_READ,
    "Time to open stored evidence and decrypt its first chunk (storage read + key unwrap), "
    "for the media and content endpoints.",
    ("variant", "outcome"),
)
