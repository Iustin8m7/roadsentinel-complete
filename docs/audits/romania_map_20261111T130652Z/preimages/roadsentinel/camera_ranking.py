"""Explainable camera suitability scoring; permission is a hard eligibility gate."""

from __future__ import annotations

from typing import Any

WEIGHTS = {
    "vehicle_visibility": 0.18,
    "traffic_volume": 0.16,
    "camera_angle": 0.12,
    "resolution": 0.10,
    "reliability": 0.10,
    "road_coverage": 0.10,
    "low_occlusion": 0.10,
    "lighting": 0.08,
    "authorization": 0.06,
}


def assess_camera(candidate: dict[str, Any]) -> dict[str, Any]:
    """Return a normalized, explainable score without manufacturing missing observations.

    Scores are assessor inputs in [0, 5], with evidence notes. A candidate without an explicit
    processing permission remains ineligible regardless of the technical score.
    """
    ratings = candidate.get("ratings", {})
    invalid = [
        key
        for key, value in ratings.items()
        if key not in WEIGHTS or not isinstance(value, (int, float)) or not 0 <= value <= 5
    ]
    if invalid:
        raise ValueError(f"invalid camera rating fields: {', '.join(sorted(invalid))}")
    missing = [key for key in WEIGHTS if key not in ratings]
    score = None
    if not missing:
        score = round(sum(float(ratings[key]) * weight for key, weight in WEIGHTS.items()) * 20, 1)
    authorized = candidate.get("permission_status") == "granted"
    return {
        "id": str(candidate.get("id", "")),
        "eligible": authorized and score is not None,
        "permission_status": candidate.get("permission_status", "unknown"),
        "score_0_to_100": score,
        "missing_criteria": missing,
        "exclusion_reason": None if authorized else "processing permission is not confirmed",
        "ratings": {key: ratings[key] for key in WEIGHTS if key in ratings},
        "evidence": candidate.get("evidence", {}),
    }


def rank_cameras(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank only eligible, fully assessed candidates; others remain visible but unranked."""
    assessed = [assess_camera(candidate) for candidate in candidates]
    assessed.sort(key=lambda item: (not item["eligible"], -(item["score_0_to_100"] or 0), item["id"]))
    return assessed
