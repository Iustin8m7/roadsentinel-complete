"""Statistics computed from real alert timestamps only (no placeholders, no trends).

Time-to-first-view: alert creation -> the first time someone who can decide opened it.
Time-to-decision: alert creation -> confirm / reject. Both only count alerts where the event
happened; alerts never viewed or decided are reported as such, not guessed.
"""

from __future__ import annotations

import math
from collections import Counter
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.policy import Permission, scope_alerts
from app.deps import Principal, require
from app.models import Alert, AlertStatus, Camera
from app.services import contract as view

router = APIRouter(tags=["stats"])


class Dist(BaseModel):
    n: int
    median_s: float | None
    p90_s: float | None


class ResponseStats(BaseModel):
    window_from: datetime
    window_to: datetime
    timezone: str
    alerts: int
    by_type: dict[str, int]
    by_camera: dict[str, int]
    by_hour_local: dict[int, int]
    confirmed: int
    rejected: int
    undecided: int
    rejection_rate: float | None
    rejection_rate_n: int
    never_viewed: int
    time_to_first_view: Dist
    time_to_decision: Dist


def _dist(values: list[float]) -> Dist:
    if not values:
        return Dist(n=0, median_s=None, p90_s=None)
    v = sorted(values)

    def pct(p: float) -> float:
        k = (len(v) - 1) * p
        lo, hi = math.floor(k), math.ceil(k)
        return v[lo] + (v[hi] - v[lo]) * (k - lo)

    return Dist(n=len(v), median_s=round(pct(0.5), 1), p90_s=round(pct(0.9), 1))


@router.get("/api/stats/response", response_model=ResponseStats)
def response_stats(
    since_hours: int = Query(default=24, ge=1, le=24 * 90),
    tz: str = Query(default="Europe/Bucharest", max_length=64),
    principal: Principal = Depends(require(Permission.stats_read)),
) -> ResponseStats:
    try:
        zone = ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(422, "unknown time zone") from None
    now = datetime.now(UTC)
    start = now - timedelta(hours=since_hours)
    stmt = scope_alerts(view.visible_alerts(), principal).where(Alert.created_at >= start)
    rows = [(a, c) for a, c in principal.db.execute(stmt.limit(20000))]
    cams: Counter[str] = Counter()
    types: Counter[str] = Counter()
    hours: Counter[int] = Counter()
    first_view, decision = [], []
    confirmed = rejected = never = 0
    for alert, cam in rows:
        types[alert.event_type] += 1
        cams[(cam.name if isinstance(cam, Camera) else str(alert.camera_id))] += 1
        hours[alert.detected_at.astimezone(zone).hour] += 1
        if alert.first_viewed_at is not None:
            first_view.append(max(0.0, (alert.first_viewed_at - alert.created_at).total_seconds()))
        else:
            never += 1
        if alert.status == AlertStatus.confirmed:
            confirmed += 1
        elif alert.status == AlertStatus.rejected:
            rejected += 1
        if alert.decided_at is not None:
            decision.append(max(0.0, (alert.decided_at - alert.created_at).total_seconds()))
    decided = confirmed + rejected
    return ResponseStats(
        window_from=start,
        window_to=now,
        timezone=tz,
        alerts=len(rows),
        by_type=dict(types),
        by_camera=dict(cams),
        by_hour_local=dict(sorted(hours.items())),
        confirmed=confirmed,
        rejected=rejected,
        undecided=len(rows) - decided,
        rejection_rate=round(rejected / decided, 4) if decided else None,
        rejection_rate_n=decided,
        never_viewed=never,
        time_to_first_view=_dist(first_view),
        time_to_decision=_dist(decision),
    )
