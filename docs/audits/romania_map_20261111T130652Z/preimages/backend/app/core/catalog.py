"""Event types, operator actions and object classes of the API.md contract.

The detection pipeline (``roadsentinel/rules.py``) emits these event types; priority is always
derived here from the type, never accepted from a client. ``tests/test_catalog_sync.py`` at the
repository root keeps this table identical to the pipeline's.
"""

from __future__ import annotations

from app.models.operations import Priority

# type -> (priority, Romanian label)
EVENT_TYPES: dict[str, tuple[Priority, str]] = {
    "wrong_way": (Priority.critical, "Sens interzis"),
    "pedestrian_on_road": (Priority.critical, "Pieton pe carosabil"),
    "probable_crash": (Priority.critical, "Accident probabil"),
    "very_high_speed": (Priority.high, "Viteză foarte mare"),
    "stopped_emergency_lane": (Priority.high, "Vehicul oprit pe banda de urgență"),
    "stopped_on_road": (Priority.high, "Vehicul oprit pe carosabil"),
    "hard_braking": (Priority.medium, "Frânare bruscă"),
    "tailgating": (Priority.medium, "Distanță prea mică"),
    "dangerous_lane_change": (Priority.medium, "Schimbare de bandă periculoasă"),
    "congestion": (Priority.info, "Aglomerare"),
    "near_miss": (Priority.high, "Aproape de coliziune"),
    "object_on_roadway": (Priority.critical, "Obiect pe carosabil"),
}

# What an operator can do when confirming an alert (key -> Romanian label).
ACTIONS: dict[str, str] = {
    "dispatch_patrol": "Trimite patrulă",
    "warning_sign": "Activează panou de avertizare",
    "enforcement": "Transmite către procedura de constatare",
    "monitor": "Doar monitorizare",
}

OBJECT_CLASSES = ("car", "truck", "bus", "motorcycle", "bicycle", "person", "object")


def priority_for(event_type: str) -> Priority:
    return EVENT_TYPES[event_type][0]
