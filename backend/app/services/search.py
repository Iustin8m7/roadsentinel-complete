"""Archive search for the API.md ``GET /api/search``: a Romanian/English keyword parser turns
the query into a bounded filter, which feeds a SQLAlchemy query under RLS. The query text is
never sent to a third party and never becomes SQL text.

Ported from ``roadsentinel/search.py`` (same vocabulary, same ``Filter`` fields)."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Select, extract, func

from app.core.catalog import EVENT_TYPES
from app.models import Alert, AlertStatus, Camera, Priority

SEARCH_TZ = "Europe/Bucharest"
MAX_SPAN = timedelta(days=92)


class Filter(BaseModel):
    event_types: list[str] = []  # keys of EVENT_TYPES (validated below)
    object_classes: list[str] = []
    priorities: list[str] = []
    date_from: str | None = None  # local ISO datetime
    date_to: str | None = None
    hour_from: int | None = Field(default=None, ge=0, le=24)
    hour_to: int | None = Field(default=None, ge=0, le=24)
    min_speed_kmh: float | None = Field(default=None, ge=0, le=400)
    status: Literal["new", "confirmed", "rejected"] | None = None
    text: str | None = Field(default=None, max_length=100)
    explanation: str = ""

    @field_validator("event_types")
    @classmethod
    def _types(cls, v: list[str]) -> list[str]:
        if any(t not in EVENT_TYPES for t in v):
            raise ValueError("unknown event type")
        return v


TYPE_WORDS = {
    "wrong_way": ["sens interzis", "contrasens", "sens opus", "wrong way", "wrong-way"],
    "pedestrian_on_road": ["pieton", "pietoni", "pedestrian", "persoan"],
    "very_high_speed": ["viteză", "viteza", "vitez", "speed", "rapid", "speeding"],
    "stopped_emergency_lane": [
        "banda de urgență",
        "banda de urgenta",
        "acostament",
        "urgență",
        "shoulder",
        "emergency lane",
    ],
    "stopped_on_road": ["oprit", "oprite", "staționat", "stationat", "stopped", "stalled"],
    "hard_braking": ["frân", "fran", "brak"],
    "tailgating": ["distanță", "distanta", "tailgat", "prea aproape"],
    "dangerous_lane_change": ["schimb", "bandă", "lane change"],
    "congestion": ["aglomer", "ambuteiaj", "coloan", "congest", "traffic jam"],
}
CLASS_WORDS = {
    "truck": ["camion", "camioan", "tir ", "truck"],
    "bus": ["autobuz", "bus"],
    "car": ["mașin", "masin", "autoturism", "car "],
    "motorcycle": ["motociclet", "moto"],
    "person": ["pieton", "persoan", "pedestrian"],
}
PRIORITY_WORDS = {
    "critical": ["critic"],
    "high": ["ridicat", "grav"],
    "medium": ["medi"],
    "info": ["informativ"],
}
DAY_PARTS = {
    "dimineaț": (6, 12),
    "dimineat": (6, 12),
    "morning": (6, 12),
    "prânz": (11, 14),
    "după-amiaz": (12, 18),
    "dupa-amiaz": (12, 18),
    "afternoon": (12, 18),
    "seară": (18, 23),
    "seara": (18, 23),
    "evening": (18, 23),
    "noapte": (0, 6),
    "night": (0, 6),
}
WEEKDAYS = {
    "luni": 0,
    "marți": 1,
    "marti": 1,
    "miercuri": 2,
    "joi": 3,
    "vineri": 4,
    "sâmbătă": 5,
    "sambata": 5,
    "duminică": 6,
    "duminica": 6,
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
}
RANGE_RE = re.compile(
    r"(?:între|intre|between|de la)\s*(?:ora\s*)?(\d{1,2})(?::\d\d)?\s*"
    r"(?:și|si|and|-|până la|pana la)\s*(\d{1,2})"
)
SPEED_RE = re.compile(r"(?:peste|over|>)\s*(\d{2,3})\s*km")


def _day(s: str, today: date) -> date | None:
    if "alaltăieri" in s or "alaltaieri" in s:
        return today - timedelta(days=2)
    if "ieri" in s or "yesterday" in s:
        return today - timedelta(days=1)
    if any(w in s for w in ("azi", "astăzi", "astazi", "today")):
        return today
    for word, wd in WEEKDAYS.items():
        if re.search(rf"\b{word}\b", s):
            return today - timedelta(days=(today.weekday() - wd) % 7 or 7)
    return None


def parse_keywords(q: str, today: date | None = None) -> Filter:
    today = today or datetime.now(ZoneInfo(SEARCH_TZ)).date()
    s = q.lower()[:500]
    f = Filter()
    f.event_types = [t for t, words in TYPE_WORDS.items() if any(w in s for w in words)]
    # "oprit pe banda de urgență" should not also match every stopped vehicle.
    if "stopped_emergency_lane" in f.event_types:
        f.event_types = [
            t for t in f.event_types if t not in ("stopped_on_road", "dangerous_lane_change")
        ]
    f.object_classes = [c for c, words in CLASS_WORDS.items() if any(w in s for w in words)]
    f.priorities = [p for p, words in PRIORITY_WORDS.items() if any(w in s for w in words)]

    day = _day(s, today)
    m = RANGE_RE.search(s)
    hours = (
        (min(int(m.group(1)), 24), min(int(m.group(2)), 24))
        if m
        else next((h for w, h in DAY_PARTS.items() if w in s), None)
    )
    if day or hours:
        h0, h1 = hours or (0, 24)
        if day:
            f.date_from = datetime(day.year, day.month, day.day, h0 % 24).isoformat()
            f.date_to = (datetime(day.year, day.month, day.day) + timedelta(hours=h1)).isoformat()
        else:  # only a time of day: search that window on every day
            f.hour_from, f.hour_to = h0, h1

    m = SPEED_RE.search(s)
    if m:
        f.min_speed_kmh = min(float(m.group(1)), 400)
        f.event_types = f.event_types or ["very_high_speed"]
    if "confirmat" in s:
        f.status = "confirmed"
    elif "respins" in s:
        f.status = "rejected"
    f.explanation = "Interpretare după cuvinte cheie"
    return f


def _utc(local_iso: str) -> datetime:
    return datetime.fromisoformat(local_iso).replace(tzinfo=ZoneInfo(SEARCH_TZ)).astimezone(UTC)


def apply(stmt: Select[Alert, Camera], f: Filter) -> Select[Alert, Camera]:
    if f.event_types:
        stmt = stmt.where(Alert.event_type.in_(f.event_types))
    if f.object_classes:
        stmt = stmt.where(Alert.object_class.in_(f.object_classes))
    if f.priorities:
        stmt = stmt.where(Alert.priority.in_([Priority(p) for p in f.priorities]))
    if f.status:
        stmt = stmt.where(Alert.status == AlertStatus(f.status))
    if f.date_from and f.date_to:
        start, end = _utc(f.date_from), _utc(f.date_to)
        end = min(end, start + MAX_SPAN)
        stmt = stmt.where(Alert.detected_at >= start, Alert.detected_at < end)
    if f.hour_from is not None and f.hour_to is not None:
        hour = extract("hour", func.timezone(SEARCH_TZ, Alert.detected_at))
        stmt = stmt.where(hour >= f.hour_from, hour < f.hour_to)
    if f.min_speed_kmh is not None:
        stmt = stmt.where(Alert.speed_kmh >= f.min_speed_kmh)
    if f.text:
        like = f"%{f.text}%"
        stmt = stmt.where(
            Alert.vlm_text.ilike(like) | Camera.location.ilike(like) | Camera.name.ilike(like)
        )
    return stmt  # the caller orders and applies its bounded page size
