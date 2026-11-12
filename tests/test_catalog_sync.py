"""The secure backend keeps its own copy of the event catalog (it ships without the pipeline).
This test fails if the two drift apart."""
import ast
from pathlib import Path

from roadsentinel.rules import EVENT_TYPES

CATALOG = Path(__file__).resolve().parent.parent / "backend" / "app" / "core" / "catalog.py"


def _backend_event_types():
    tree = ast.parse(CATALOG.read_text())
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "EVENT_TYPES":
            out = {}
            for key, value in zip(node.value.keys, node.value.values, strict=True):
                priority, label = value.elts
                out[key.value] = (priority.attr, label.value)
            return out
    raise AssertionError("EVENT_TYPES not found in backend catalog")


def test_backend_catalog_matches_pipeline_rules():
    assert _backend_event_types() == EVENT_TYPES
