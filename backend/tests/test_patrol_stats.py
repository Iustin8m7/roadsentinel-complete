"""Patrol workflow and response-time statistics from real timestamps."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.db import tenant_session
from app.models import Alert
from tests.conftest import World, audit_actions


def alert_ids(world: World) -> list[str]:
    return [str(i) for i in world.data["a"]["alerts"]]


class TestPatrolWorkflow:
    def test_assign_then_patrol_walks_the_statuses_forward(self, world: World, login: Any) -> None:
        op, patrol = login(world.a.operator), login(world.a.patrol)
        target = alert_ids(world)[0]
        r = op.post(f"/api/alerts/{target}/assign", {"user_id": str(world.a.patrol.id)})
        assert r.status_code == 200 and r.json()["patrol_status"] == "assigned"
        assert r.json()["assigned_to_name"]
        for step in ("en_route", "on_scene", "done"):
            r = patrol.post(f"/api/alerts/{target}/patrol-status", {"status": step})
            assert r.status_code == 200 and r.json()["patrol_status"] == step
        # the operator sees the real status
        assert op.get(f"/api/alerts/{target}").json()["patrol_status"] == "done"
        assert audit_actions(world.a.id).count("alert.patrol_status") == 3

    def test_status_cannot_go_backwards_or_skip_to_the_same_state(
        self, world: World, login: Any
    ) -> None:
        op, patrol = login(world.a.operator), login(world.a.patrol)
        target = alert_ids(world)[0]
        op.post(f"/api/alerts/{target}/assign", {"user_id": str(world.a.patrol.id)})
        assert (
            patrol.post(f"/api/alerts/{target}/patrol-status", {"status": "on_scene"}).status_code
            == 200
        )
        assert (
            patrol.post(f"/api/alerts/{target}/patrol-status", {"status": "en_route"}).status_code
            == 409
        )
        assert (
            patrol.post(f"/api/alerts/{target}/patrol-status", {"status": "on_scene"}).status_code
            == 409
        )
        assert (
            patrol.post(f"/api/alerts/{target}/patrol-status", {"status": "bogus"}).status_code
            == 422
        )

    def test_only_the_assignee_can_update_and_only_patrols(self, world: World, login: Any) -> None:
        op = login(world.a.operator)
        target = alert_ids(world)[0]
        op.post(f"/api/alerts/{target}/assign", {"user_id": str(world.a.patrol.id)})
        assert (
            op.post(f"/api/alerts/{target}/patrol-status", {"status": "en_route"}).status_code
            == 403
        )
        assert (
            login(world.a.admin)
            .post(f"/api/alerts/{target}/patrol-status", {"status": "en_route"})
            .status_code
            == 403
        )
        other_patrol = __import__("tests.conftest", fromlist=["x"]).make_user(
            world.a.id,
            __import__("app.models", fromlist=["Role"]).Role.patrol,
            "patrol2.a@test.local",
        )
        # not assigned to patrol2 -> not even visible to them
        assert login(other_patrol).post(
            f"/api/alerts/{target}/patrol-status", {"status": "en_route"}
        ).status_code in (403, 404)
        assert (
            login(world.b.patrol)
            .post(f"/api/alerts/{target}/patrol-status", {"status": "en_route"})
            .status_code
            == 404
        )

    def test_patrol_list_shows_real_accounts_and_open_assignments(
        self, world: World, login: Any
    ) -> None:
        op = login(world.a.operator)
        listing = op.get("/api/patrols").json()
        assert [p["id"] for p in listing] == [str(world.a.patrol.id)] and listing[0][
            "open_assignments"
        ] >= 1
        assert set(listing[0]) == {
            "id",
            "display_name",
            "open_assignments",
        }  # no invented positions / ETA
        assert login(world.a.patrol).get("/api/patrols").status_code == 403
        assert login(world.a.auditor).get("/api/patrols").status_code == 403
        assert [p["id"] for p in login(world.b.operator).get("/api/patrols").json()] == [
            str(world.b.patrol.id)
        ]

    def test_assigning_a_non_patrol_is_refused(self, world: World, login: Any) -> None:
        op = login(world.a.operator)
        r = op.post(
            f"/api/alerts/{alert_ids(world)[0]}/assign", {"user_id": str(world.a.operator.id)}
        )
        assert r.status_code == 422


class TestResponseStats:
    def _age(
        self,
        world: World,
        view_after: int | None,
        decide_after: int | None,
        status: str = "confirmed",
    ) -> None:
        """Rewrite timestamps of the first alert: created 10 min ago."""
        with tenant_session(world.a.id) as db:
            a = db.get(Alert, world.data["a"]["alerts"][0])
            a.created_at = datetime.now(UTC) - timedelta(minutes=10)
            a.first_viewed_at = (
                a.created_at + timedelta(seconds=view_after) if view_after is not None else None
            )
            if decide_after is not None:
                a.decided_at = a.created_at + timedelta(seconds=decide_after)
                a.status = __import__("app.models", fromlist=["AlertStatus"]).AlertStatus(status)
            db.commit()

    def test_times_come_from_timestamps_and_report_their_sample_size(
        self, world: World, login: Any
    ) -> None:
        self._age(world, view_after=20, decide_after=95)
        s = login(world.a.operator).get("/api/stats/response?since_hours=2").json()
        assert s["alerts"] == 3 and s["confirmed"] == 1 and s["undecided"] == 2
        assert s["time_to_first_view"] == {"n": 1, "median_s": 20.0, "p90_s": 20.0}
        assert s["time_to_decision"]["median_s"] == 95.0 and s["time_to_decision"]["n"] == 1
        assert s["never_viewed"] == 2 and s["rejection_rate"] == 0.0 and s["rejection_rate_n"] == 1
        assert sum(s["by_type"].values()) == 3 and sum(s["by_hour_local"].values()) == 3

    def test_no_data_means_null_not_zero(self, world: World, login: Any) -> None:
        s = login(world.a.operator).get("/api/stats/response?since_hours=1").json()
        assert s["time_to_first_view"]["median_s"] is None and s["rejection_rate"] is None

    def test_rejection_rate_and_window(self, world: World, login: Any) -> None:
        self._age(world, 5, 30, "rejected")
        s = login(world.a.admin).get("/api/stats/response?since_hours=2").json()
        assert s["rejected"] == 1 and s["rejection_rate"] == 1.0
        assert login(world.a.admin).get("/api/stats/response?since_hours=0").status_code == 422
        assert login(world.a.admin).get("/api/stats/response?tz=Mars/Base").status_code == 422

    def test_viewing_by_deciders_sets_first_view_but_patrol_viewing_does_not(
        self, world: World, login: Any
    ) -> None:
        target = alert_ids(world)[1]
        login(world.a.patrol).get(f"/api/alerts/{target}")
        with tenant_session(world.a.id) as db:
            assert db.get(Alert, world.data["a"]["alerts"][1]).first_viewed_at is None
        login(world.a.operator).get(f"/api/alerts/{target}")
        with tenant_session(world.a.id) as db:
            first = db.get(Alert, world.data["a"]["alerts"][1]).first_viewed_at
            assert first is not None
        login(world.a.admin).get(f"/api/alerts/{target}")  # a later view does not move it
        with tenant_session(world.a.id) as db:
            assert db.get(Alert, world.data["a"]["alerts"][1]).first_viewed_at == first

    def test_roles_and_tenants(self, world: World, login: Any) -> None:
        for user in (world.a.patrol, world.a.auditor):
            assert login(user).get("/api/stats/response").status_code == 403
        a = login(world.a.operator).get("/api/stats/response?since_hours=2").json()["alerts"]
        b = login(world.b.operator).get("/api/stats/response?since_hours=2").json()["alerts"]
        assert a == 3 and b == 3


class TestCameraManagement:
    def test_edit_and_disable_are_audited_with_before_and_after(
        self, world: World, login: Any
    ) -> None:
        admin = login(world.a.admin)
        cam = world.data["a"]["camera"]
        r = admin.patch(
            f"/api/cameras/{cam}", {"name": "Podul Roș", "latitude": 47.1, "longitude": 27.6}
        )
        assert r.status_code == 200 and r.json()["name"] == "Podul Roș"
        assert admin.patch(f"/api/cameras/{cam}", {"is_active": False}).json()["is_active"] is False
        assert audit_actions(world.a.id).count("camera.updated") == 2

    def test_validation_and_roles_and_tenants(self, world: World, login: Any) -> None:
        admin, cam = login(world.a.admin), world.data["a"]["camera"]
        assert admin.patch(f"/api/cameras/{cam}", {}).status_code == 422
        assert admin.patch(f"/api/cameras/{cam}", {"timezone": "Mars/Base"}).status_code == 422
        assert admin.patch(f"/api/cameras/{cam}", {"latitude": 200}).status_code == 422
        assert (
            admin.patch(f"/api/cameras/{cam}", {"slug": "x-1"}).status_code == 422
        )  # identity is immutable
        assert (
            admin.patch(f"/api/cameras/{cam}", {"timezone": "Europe/Bucharest"}).status_code == 200
        )
        for user in (world.a.operator, world.a.patrol, world.a.auditor):
            assert login(user).patch(f"/api/cameras/{cam}", {"name": "nope"}).status_code == 403
        assert (
            login(world.b.admin).patch(f"/api/cameras/{cam}", {"name": "nope"}).status_code == 404
        )
