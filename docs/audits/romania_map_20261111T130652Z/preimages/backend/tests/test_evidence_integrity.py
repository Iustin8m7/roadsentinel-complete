"""Evidence without a distinct original (everything the pipeline sends) cannot be 'unblurred'
or exported as an original, and the UI is told so."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.db import tenant_session
from app.models import Alert, Evidence
from app.services import evidence as evidence_service
from app.services.keys import load_keyring
from app.services.seed import make_png
from tests.conftest import ApiClient, World, audit_actions


@pytest.fixture
def single_copy(world: World) -> uuid.UUID:
    """Evidence stored the way the ingestion API stores pipeline files: one copy."""
    with tenant_session(world.a.id) as db:
        kr = load_keyring(db, world.a.id)
        alert = db.get(Alert, world.data["a"]["assigned_alert"])
        ev = evidence_service.ingest(
            db,
            kr,
            alert,
            original=None,
            redacted=make_png(16, 12, redacted=True, seed=7),
            content_type="image/png",
            redaction="off",
        )
        db.commit()
        return ev.id


def test_flags_are_recorded(world: World, single_copy: uuid.UUID) -> None:
    with tenant_session(world.a.id) as db:
        single = db.get(Evidence, single_copy)
        distinct = db.get(Evidence, world.data["a"]["evidence"])
        assert single is not None and distinct is not None
        assert single.has_original is False and single.redaction == "off"
        assert distinct.has_original is True


def test_identical_bytes_are_not_a_distinct_original(world: World) -> None:
    png = make_png(16, 12, redacted=True, seed=3)
    with tenant_session(world.a.id) as db:
        kr = load_keyring(db, world.a.id)
        alert = db.get(Alert, world.data["a"]["assigned_alert"])
        ev = evidence_service.ingest(
            db, kr, alert, original=png, redacted=png, content_type="image/png"
        )
        assert ev.has_original is False


def test_metadata_exposes_has_original(world: World, login: Any, single_copy: uuid.UUID) -> None:
    op = login(world.a.operator)
    body = op.get(f"/api/evidence/{single_copy}").json()
    assert body["has_original"] is False and body["redaction"] == "off"
    assert op.get(f"/api/evidence/{world.data['a']['evidence']}").json()["has_original"] is True


def test_unblur_and_export_requests_are_refused(
    world: World, login: Any, single_copy: uuid.UUID
) -> None:
    op: ApiClient = login(world.a.operator)
    for kind in ("unblur", "export"):
        r = op.post(
            "/api/approvals",
            {
                "kind": kind,
                "evidence_id": str(single_copy),
                "justification": "Needed for the case report",
                "case_reference": "CASE-1",
            },
        )
        assert r.status_code == 409 and "no_original" in r.text


def test_original_access_is_refused_but_the_stored_copy_stays_viewable(
    world: World, login: Any, single_copy: uuid.UUID
) -> None:
    op = login(world.a.operator)
    assert (
        op.post(f"/api/evidence/{single_copy}/access", {"variant": "original"}).status_code == 409
    )
    assert op.post(f"/api/evidence/{single_copy}/export").status_code == 409
    # the stored (processed) copy stays viewable
    r = op.post(f"/api/evidence/{single_copy}/access", {"variant": "redacted"})
    assert r.status_code == 200 and op.get(r.json()["url"]).status_code == 200
    assert "security.access_denied" in audit_actions(world.a.id)
