"""Retention: policy, dry-run, legal hold, audited purge, access to purged evidence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.db import tenant_session
from app.models import Alert, AlertStatus, Evidence
from app.services import evidence as evidence_service
from app.services import retention
from app.services.keys import load_keyring
from app.services.seed import make_png
from tests.conftest import World, admin_conn, audit_actions


def add_evidence(
    world: World, kind: str, age_days: int, *, alert: str = "assigned", status: str | None = None
) -> uuid.UUID:
    with tenant_session(world.a.id) as db:
        kr = load_keyring(db, world.a.id)
        alert_id = {
            "assigned": world.data["a"]["assigned_alert"],
            "other": world.data["a"]["alerts"][0],
            "third": world.data["a"]["alerts"][2],
        }[alert]
        a = db.get(Alert, alert_id)
        if status:
            a.status = AlertStatus(status)
        ev = evidence_service.ingest(
            db,
            kr,
            a,
            original=None,
            redacted=make_png(16, 12, redacted=True, seed=age_days),
            content_type="image/png",
            kind=kind,
        )
        ev.created_at = datetime.now(UTC) - timedelta(days=age_days)
        db.commit()
        return ev.id


def stored_path(world: World, eid: uuid.UUID) -> Any:
    from app.config import get_settings

    with tenant_session(world.a.id) as db:
        ev = db.get(Evidence, eid)
        return get_settings().evidence_dir / ev.redacted_path


class TestPolicy:
    def test_defaults_and_update_with_audit(self, world: World, login: Any) -> None:
        admin = login(world.a.admin)
        assert admin.get("/api/retention").json()["days"] == retention.DEFAULT_DAYS
        r = admin.put("/api/retention", {"days": {"clip": 10, "keyframe": 14}})
        assert (
            r.status_code == 200
            and r.json()["days"]["clip"] == 10
            and r.json()["days"]["camera_video"] == 7
        )
        assert "retention.policy_changed" in audit_actions(world.a.id)

    def test_bounds_and_roles(self, world: World, login: Any) -> None:
        admin = login(world.a.admin)
        assert admin.put("/api/retention", {"days": {"clip": 0}}).status_code == 422
        assert admin.put("/api/retention", {"days": {"clip": 9999}}).status_code == 422
        assert admin.put("/api/retention", {"days": {"surprise": 5}}).status_code == 422
        for user in (world.a.operator, world.a.patrol, world.a.auditor):
            assert login(user).get("/api/retention").status_code == 403
            assert login(user).post("/api/retention/purge", {"dry_run": True}).status_code == 403

    def test_policy_is_per_tenant(self, world: World, login: Any) -> None:
        login(world.a.admin).put("/api/retention", {"days": {"clip": 3}})
        assert login(world.b.admin).get("/api/retention").json()["days"]["clip"] == 30


class TestPurge:
    def test_dry_run_changes_nothing_but_is_audited(self, world: World, login: Any) -> None:
        old = add_evidence(world, "clip", 40)
        admin = login(world.a.admin)
        r = admin.post("/api/retention/purge", {"dry_run": True}).json()
        assert r["candidates"] == 1 and r["purged"] == 0 and r["by_kind"] == {"clip": 1}
        assert stored_path(world, old).exists()
        assert "retention.purged" in audit_actions(world.a.id)

    def test_real_purge_needs_confirmation_and_deletes_files_but_keeps_the_row(
        self, world: World, login: Any
    ) -> None:
        old = add_evidence(world, "clip", 40)
        fresh = add_evidence(world, "clip", 2)
        path = stored_path(world, old)
        admin = login(world.a.admin)
        assert admin.post("/api/retention/purge", {"dry_run": False}).status_code == 422
        assert (
            admin.post("/api/retention/purge", {"dry_run": False, "confirm": "yes"}).status_code
            == 422
        )
        assert path.exists()
        r = admin.post("/api/retention/purge", {"dry_run": False, "confirm": "PURGE"}).json()
        assert r["purged"] == 1 and not path.exists() and stored_path(world, fresh).exists()
        with tenant_session(world.a.id) as db:
            ev = db.get(Evidence, old)
            assert (
                ev.purged_at is not None and len(ev.sha256) == 64
            )  # chain-of-custody metadata stays
        # idempotent: a second run finds nothing
        assert (
            admin.post("/api/retention/purge", {"dry_run": False, "confirm": "PURGE"}).json()[
                "purged"
            ]
            == 0
        )
        with admin_conn() as conn:
            details = conn.execute(
                "SELECT details FROM audit_log WHERE tenant_id = %s "
                "AND action = 'retention.purged' ORDER BY seq DESC OFFSET 1 LIMIT 1",
                (world.a.id,),
            ).fetchone()[0]
        assert details["purged"] == 1 and str(old) in details["ids"] and details["dry_run"] is False

    def test_per_kind_days_and_confirmed_cases_are_kept_longer(
        self, world: World, login: Any
    ) -> None:
        keyframe = add_evidence(world, "keyframe", 20)  # default 30 days: kept
        confirmed = add_evidence(
            world, "clip", 100, alert="third", status="confirmed"
        )  # confirmed_case 365: kept
        plain = add_evidence(world, "clip", 100, alert="other")  # 30 days: due
        admin = login(world.a.admin)
        put = admin.put("/api/retention", {"days": {"keyframe": 10}})
        assert put.status_code == 200, put.text
        assert admin.get("/api/retention").json()["due_now"] == 2
        r = admin.post("/api/retention/purge", {"dry_run": False, "confirm": "PURGE"}).json()
        assert r["purged"] == 2  # keyframe (now 10 d) and the plain old clip
        assert stored_path(world, confirmed).exists()
        assert not stored_path(world, keyframe).exists() and not stored_path(world, plain).exists()

    def test_legal_hold_blocks_the_purge_until_released(self, world: World, login: Any) -> None:
        old = add_evidence(world, "clip", 400)
        admin = login(world.a.admin)
        alert = world.data["a"]["assigned_alert"]
        assert admin.post(f"/api/retention/holds/{alert}", {"reason": "short"}).status_code == 422
        assert (
            admin.post(
                f"/api/retention/holds/{alert}", {"reason": "Court order 123/2026, keep everything"}
            ).status_code
            == 204
        )
        r = admin.post("/api/retention/purge", {"dry_run": False, "confirm": "PURGE"}).json()
        assert r["purged"] == 0 and r["held_skipped"] >= 1 and stored_path(world, old).exists()
        assert admin.delete(f"/api/retention/holds/{alert}").status_code == 204
        assert (
            admin.post("/api/retention/purge", {"dry_run": False, "confirm": "PURGE"}).json()[
                "purged"
            ]
            >= 1
        )
        acts = audit_actions(world.a.id)
        assert "alert.legal_hold_set" in acts and "alert.legal_hold_released" in acts

    def test_hold_on_another_tenants_alert_is_invisible(self, world: World, login: Any) -> None:
        other = world.data["b"]["assigned_alert"]
        assert (
            login(world.a.admin)
            .post(f"/api/retention/holds/{other}", {"reason": "x" * 20})
            .status_code
            == 404
        )

    def test_purge_of_one_tenant_never_touches_another(self, world: World, login: Any) -> None:
        with tenant_session(world.b.id) as db:
            b_ev = db.query(Evidence).first()
            b_ev.created_at = datetime.now(UTC) - timedelta(days=900)
            db.commit()
            b_id = b_ev.id
        add_evidence(world, "clip", 400)
        login(world.a.admin).post("/api/retention/purge", {"dry_run": False, "confirm": "PURGE"})
        with tenant_session(world.b.id) as db:
            assert db.get(Evidence, b_id).purged_at is None


class TestAccessToPurgedEvidence:
    def test_metadata_says_purged_and_content_is_gone(self, world: World, login: Any) -> None:
        old = add_evidence(world, "keyframe", 400)
        op, admin = login(world.a.operator), login(world.a.admin)
        url = op.post(f"/api/evidence/{old}/access", {"variant": "redacted"}).json()["url"]
        assert op.get(url).status_code == 200
        admin.post("/api/retention/purge", {"dry_run": False, "confirm": "PURGE"})
        assert op.post(f"/api/evidence/{old}/access", {"variant": "redacted"}).status_code == 410
        assert op.get(url).status_code == 410
        assert op.post(f"/api/evidence/{old}/export").status_code in (409, 410)


def test_cli_job_dry_run_and_real(world: World, capsys: Any) -> None:
    from app.cli import main

    old = add_evidence(world, "clip", 400)
    main(["purge-evidence", "--tenant", "unit-a", "--dry-run"])
    assert "DRY RUN candidates=1" in capsys.readouterr().out and stored_path(world, old).exists()
    main(["purge-evidence", "--tenant", "unit-a", "unit-b"])
    out = capsys.readouterr().out
    assert "PURGED candidates=1 purged=1" in out
    assert not stored_path(world, old).exists()
