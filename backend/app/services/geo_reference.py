"""Versioned public cartographic reference. No network/geocoding/device GPS at runtime."""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


@lru_cache(maxsize=8)
def layer(name: str):
    if name not in {"boundary", "counties", "places", "roads"}:
        raise ValueError("Unknown reference layer")
    return json.loads((DATA / f"romania-{name}.geojson").read_text())


def rings(geometry):
    return (
        geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    )


def in_ring(x, y, ring):
    inside = False
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
            inside = not inside
    return inside


def contains(x, y, geometry):
    return any(
        in_ring(x, y, p[0]) and not any(in_ring(x, y, hole) for hole in p[1:])
        for p in rings(geometry)
    )


def distance_to_boundary_m(x, y, geometry):
    scale_x = 111_320 * math.cos(math.radians(y))
    scale_y = 111_320
    best = math.inf
    for polygon in rings(geometry):
        for ring in polygon:
            for a, b in zip(ring, ring[1:]):
                ax, ay = (a[0] - x) * scale_x, (a[1] - y) * scale_y
                dx, dy = (b[0] - a[0]) * scale_x, (b[1] - a[1]) * scale_y
                q = (
                    max(0, min(1, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
                    if dx * dx + dy * dy
                    else 0
                )
                best = min(best, math.hypot(ax + q * dx, ay + q * dy))
    return best


@lru_cache(maxsize=4096)
def classify(latitude: float, longitude: float):
    geometry = layer("boundary")["features"][0]["geometry"]
    # This band is cartographic uncertainty, never a legal border claim or coordinate clamp.
    if 19.8 <= longitude <= 30 and 43.4 <= latitude <= 48.6:
        if distance_to_boundary_m(longitude, latitude, geometry) <= 2000:
            region = "border_uncertain"
        else:
            region = "romania" if contains(longitude, latitude, geometry) else "outside"
    else:
        region = "outside"
    counties = (
        [
            f["properties"]["code"]
            for f in layer("counties")["features"]
            if contains(longitude, latitude, f["geometry"])
        ]
        if region != "outside"
        else []
    )
    return region, counties[0] if len(counties) == 1 else None


def reference():
    boundary = layer("boundary")
    points = [
        point
        for polygon in rings(boundary["features"][0]["geometry"])
        for ring in polygon
        for point in ring
    ]
    return dict(
        boundary=boundary,
        counties=layer("counties"),
        places=layer("places"),
        roads=layer("roads"),
        bounds=[
            min(p[0] for p in points),
            min(p[1] for p in points),
            max(p[0] for p in points),
            max(p[1] for p in points),
        ],
        attribution="Made with Natural Earth · Public domain · 5.1.2 · cartographic, not cadastral",
        provenance=json.loads((DATA / "geodata-provenance.json").read_text()),
    )
