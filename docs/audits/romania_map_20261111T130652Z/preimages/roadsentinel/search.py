"""Natural-language archive search.

The query is turned into a structured filter (by Claude when an API key is set, otherwise
by a small Romanian/English keyword parser), then run against the event store.
"""
import re
from datetime import date, datetime, timedelta
from typing import Literal

from pydantic import BaseModel

from . import store, vlm
from .rules import EVENT_TYPES

EventType = Literal[tuple(EVENT_TYPES)]  # type: ignore[valid-type]


class Filter(BaseModel):
    event_types: list[EventType] = []
    object_classes: list[Literal["car", "truck", "bus", "motorcycle", "person"]] = []
    priorities: list[Literal["critical", "high", "medium", "info"]] = []
    date_from: str | None = None   # ISO datetime
    date_to: str | None = None
    hour_from: int | None = None   # time-of-day window on any date, e.g. "seara" = 18..23
    hour_to: int | None = None
    min_speed_kmh: float | None = None
    status: Literal["new", "confirmed", "rejected"] | None = None
    text: str | None = None        # free text to match in descriptions/locations
    explanation: str = ""             # how the query was understood (shown to the user)


TYPE_WORDS = {
    "wrong_way": ["sens interzis", "contrasens", "sens opus", "wrong way", "wrong-way"],
    "pedestrian_on_road": ["pieton", "pietoni", "pedestrian", "persoan"],
    "very_high_speed": ["viteză", "viteza", "vitez", "speed", "rapid", "speeding"],
    "stopped_emergency_lane": ["banda de urgență", "banda de urgenta", "acostament", "urgență", "shoulder", "emergency lane"],
    "stopped_on_road": ["oprit", "oprite", "staționat", "stationat", "stopped", "stalled"],
    "hard_braking": ["frân", "fran", "brak"],
    "tailgating": ["distanță", "distanta", "tailgat", "prea aproape"],
    "dangerous_lane_change": ["schimb", "bandă", "lane change"],
    "congestion": ["aglomer", "ambuteiaj", "coloan", "congest", "traffic jam"],
}
CLASS_WORDS = {"truck": ["camion", "camioan", "tir", "truck"], "bus": ["autobuz", "bus"],
               "car": ["mașin", "masin", "autoturism", "car "], "motorcycle": ["motociclet", "moto"],
               "person": ["pieton", "persoan", "pedestrian"]}
PRIORITY_WORDS = {"critical": ["critic"], "high": ["ridicat", "grav"], "medium": ["medi"], "info": ["informativ"]}
DAY_PARTS = {"dimineaț": (6, 12), "dimineat": (6, 12), "morning": (6, 12), "prânz": (11, 14), "după-amiaz": (12, 18),
             "dupa-amiaz": (12, 18), "afternoon": (12, 18), "seară": (18, 23), "seara": (18, 23), "evening": (18, 23),
             "noapte": (0, 6), "night": (0, 6)}
WEEKDAYS = {"luni": 0, "marți": 1, "marti": 1, "miercuri": 2, "joi": 3, "vineri": 4, "sâmbătă": 5, "sambata": 5,
            "duminică": 6, "duminica": 6, "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4}


def parse_keywords(q, today=None):
    today = today or date.today()
    s = q.lower()
    f = Filter()
    f.event_types = [t for t, words in TYPE_WORDS.items() if any(w in s for w in words)]
    # "oprit pe banda de urgență" should not also match every stopped vehicle.
    if "stopped_emergency_lane" in f.event_types:
        f.event_types = [t for t in f.event_types if t not in ("stopped_on_road", "dangerous_lane_change")]
    f.object_classes = [c for c, words in CLASS_WORDS.items() if any(w in s for w in words)]
    f.priorities = [p for p, words in PRIORITY_WORDS.items() if any(w in s for w in words)]

    day = None
    if "alaltăieri" in s or "alaltaieri" in s:
        day = today - timedelta(days=2)
    elif "ieri" in s or "yesterday" in s:
        day = today - timedelta(days=1)
    elif "azi" in s or "astăzi" in s or "astazi" in s or "today" in s:
        day = today
    else:
        for w, wd in WEEKDAYS.items():
            if re.search(rf"\b{w}\b", s):
                day = today - timedelta(days=(today.weekday() - wd) % 7 or 7)
                break
    hours = None
    m = re.search(r"(?:între|intre|between|de la)\s*(?:ora\s*)?(\d{1,2})(?::\d\d)?\s*(?:și|si|and|-|până la|pana la)\s*(\d{1,2})", s)
    if m:
        hours = (int(m.group(1)), int(m.group(2)))
    else:
        hours = next((h for w, h in DAY_PARTS.items() if w in s), None)
    if day or hours:
        d = day or today
        h0, h1 = hours or (0, 24)
        f.date_from = datetime(d.year, d.month, d.day, h0).isoformat()
        f.date_to = (datetime(d.year, d.month, d.day) + timedelta(hours=h1)).isoformat()
        if not day:  # only a time of day: search that window on every day
            f.date_from, f.date_to = None, None
            f.hour_from, f.hour_to = h0, h1

    m = re.search(r"(?:peste|over|>)\s*(\d{2,3})\s*km", s)
    if m:
        f.min_speed_kmh = float(m.group(1))
        f.event_types = f.event_types or ["very_high_speed"]
    if "confirmat" in s:
        f.status = "confirmed"
    elif "respins" in s:
        f.status = "rejected"
    f.explanation = "Interpretare după cuvinte cheie"
    return f


def parse_llm(q, today=None):
    import anthropic

    today = today or date.today()
    types = "\n".join(f"- {t}: {label} ({prio})" for t, (prio, label) in EVENT_TYPES.items())
    prompt = f"""Transformă cererea unui anchetator într-un filtru pentru arhiva de evenimente rutiere.
Data de azi: {today.isoformat()} ({today.strftime('%A')}). Ora locală (Europe/Bucharest), fără fus orar în valori.
Tipuri de evenimente:
{types}
Lasă listele goale dacă cererea nu restrânge acel câmp. „explanation” = o propoziție în română despre cum ai înțeles cererea.

Cererea: {q}"""
    resp = anthropic.Anthropic().messages.parse(model=vlm.MODEL, max_tokens=4000,
                                                messages=[{"role": "user", "content": prompt}], output_format=Filter)
    return resp.parsed_output


def parse(q, today=None):
    if vlm.available():
        try:
            f = parse_llm(q, today)
            if f is not None:
                return f
        except Exception as err:  # noqa: BLE001 - any LLM failure falls back to keywords, never fails the search
            print("LLM parse failed:", err)
    return parse_keywords(q, today)


def run(db, q, today=None):
    f = parse(q, today)
    hours = (f.hour_from, f.hour_to) if f.hour_from is not None and f.hour_to is not None else None
    return f, store.query_events(db, types=f.event_types, classes=f.object_classes, priorities=f.priorities,
                                 status=f.status, date_from=f.date_from, date_to=f.date_to, hours=hours,
                                 min_speed=f.min_speed_kmh, text=f.text)
