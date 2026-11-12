"""The API.md contract served by the secure backend (ported from the prototype's tests/test_api.py,
adapted to per-user MFA logins), plus tenant isolation and patrol scoping of the new routes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.api import contract as contract_api
from app.db import tenant_session
from app.deps import Principal
from app.models import SavedSearch, User, UserSession
from tests.conftest import ApiClient, World, admin_conn, audit_actions
from tests.test_contract_ingest import EVENT, MP4, add_camera, post_event
from tests.test_ingest_auth import Pipeline, make_pipeline


@pytest.fixture
def pipe(world: World) -> Pipeline:
    add_camera(world.a.id, "demo-highway")
    return make_pipeline(world.a.id)[0]


@pytest.fixture
def event_no(pipe: Pipeline) -> int:
    r = post_event(pipe)
    assert r.status_code == 200, r.text
    return int(r.json()["id"])


def operator(login: Any, world: World) -> ApiClient:
    return login(world.a.operator)


class TestLogin:
    def test_dashboard_requires_login(self, client: ApiClient) -> None:
        assert client.get("/api/events").status_code == 401
        assert client.get("/api/me").json() == {
            "operator": None,
            "auth_required": True,
            "mfa_required": False,
            "mfa_enrollment": False,
        }

    def test_password_then_mfa(self, client: ApiClient, world: World) -> None:
        user = world.a.operator
        r = client.post("/api/login", {"operator": user.email, "password": user.password})
        assert r.status_code == 200, r.text
        assert r.json()["mfa_required"] is True and r.json()["operator"] is None
        assert client.get("/api/events").status_code == 401  # password alone is not enough
        assert client.post("/api/auth/mfa/verify", {"code": user.totp()}).status_code == 204
        assert client.get("/api/me").json()["operator"] == "operator.a"
        assert client.get("/api/events").status_code == 200

    def test_wrong_password(self, client: ApiClient, world: World) -> None:
        r = client.post("/api/login", {"operator": world.a.operator.email, "password": "nope"})
        assert r.status_code == 401

    def test_logout_ends_the_session(self, login: Any, world: World) -> None:
        api = operator(login, world)
        assert api.post("/api/logout").json()["operator"] is None
        assert api.get("/api/events").status_code == 401


class TestEvents:
    def test_ingested_event_is_listed_with_media(
        self, login: Any, world: World, event_no: int
    ) -> None:
        api = operator(login, world)
        [e] = [e for e in api.get("/api/events").json() if e["id"] == event_no]
        assert e["camera_id"] == "demo-highway" and e["priority"] == "high"
        assert e["occurred_at"] == "2026-10-16T14:05:16"  # back in camera-local time
        assert e["redaction"] == "unknown"
        clip = api.get(e["clip_url"])
        assert clip.status_code == 200 and clip.content == MP4  # decrypted on the fly
        assert clip.headers["cache-control"] == "no-store"

    def test_queue_order_undecided_then_priority(
        self, login: Any, world: World, pipe: Pipeline
    ) -> None:
        post_event(pipe, {**EVENT, "type": "congestion"})
        post_event(pipe, {**EVENT, "type": "wrong_way"})
        listed = operator(login, world).get("/api/events").json()
        types = [e["type"] for e in listed if e["type"] != "test_event"]  # skip fixture alerts
        assert types == ["wrong_way", "congestion"]

    def test_meta_and_stats(self, login: Any, world: World, event_no: int) -> None:
        api = operator(login, world)
        meta = api.get("/api/meta").json()
        assert meta["event_types"]["wrong_way"]["priority"] == "critical"
        assert "dispatch_patrol" in meta["actions"]
        stats = api.get("/api/stats").json()
        assert stats["by_type"]["very_high_speed"] == 1

    def test_stats_aggregate_in_database_and_respect_patrol_scope(
        self, login: Any, world: World
    ) -> None:
        operator_stats = login(world.a.operator).get("/api/stats").json()
        patrol_stats = login(world.a.patrol).get("/api/stats").json()
        assert operator_stats["total"] == 3
        assert patrol_stats["total"] == 1
        assert patrol_stats["by_priority"] == {"critical": 1}
        assert patrol_stats["by_type"] == {"test_event": 1}

    def test_decision_is_attributed_to_the_logged_in_user(
        self, login: Any, world: World, event_no: int
    ) -> None:
        api = operator(login, world)
        assert api.post(f"/api/events/{event_no}/view", {}).status_code == 204
        bad = api.post(f"/api/events/{event_no}/decision", {"decision": "confirm"})
        assert bad.status_code == 400
        r = api.post(
            f"/api/events/{event_no}/decision", {"decision": "confirm", "action": "dispatch_patrol"}
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "confirmed" and body["action"] == "dispatch_patrol"
        trail = [(a["actor"], a["action"]) for a in body["audit"]]
        assert trail == [
            ("system", "detected"),
            ("operator.a", "viewed"),
            ("operator.a", "confirmed"),
        ]

    def test_decided_event_cannot_be_decided_again(
        self, login: Any, world: World, event_no: int
    ) -> None:
        api = operator(login, world)
        url = f"/api/events/{event_no}/decision"
        r = api.post(url, {"decision": "reject", "action": "dispatch_patrol"})
        assert r.status_code == 200
        assert r.json()["action"] is None  # no action stored on reject
        assert api.post(url, {"decision": "confirm", "action": "monitor"}).status_code == 409

    def test_search_by_speed(self, login: Any, world: World, event_no: int) -> None:
        api = operator(login, world)
        found = api.get("/api/search", params={"q": "viteză peste 140 km/h"}).json()
        assert [e["id"] for e in found["results"]] == [event_no]
        assert found["filter"]["min_speed_kmh"] == 140
        posted = api.post("/api/search", {"q": "viteză peste 140 km/h"}).json()
        assert [e["id"] for e in posted["results"]] == [event_no]
        none = api.get("/api/search", params={"q": "viteză peste 160 km/h"}).json()
        assert none["results"] == []
        assert "alert.search" in audit_actions(world.a.id)

    def test_search_cursor_pages_are_stable_and_filter_bound(
        self, login: Any, world: World, pipe: Pipeline
    ) -> None:
        for offset, track in ((2, 82), (1, 81), (0, 80)):
            event = {
                **EVENT,
                "occurred_at": (
                    datetime.fromisoformat(EVENT["occurred_at"]) + timedelta(minutes=offset)
                ).isoformat(),
                "track_id": track,
            }
            assert post_event(pipe, event).status_code == 200

        api = operator(login, world)
        body = {"q": "viteză peste 140 km/h", "limit": 1}
        first = api.post("/api/search", body)
        assert first.status_code == 200, first.text
        page1 = first.json()
        assert len(page1["results"]) == 1 and page1["next_cursor"]

        second = api.post("/api/search", {**body, "cursor": page1["next_cursor"]})
        assert second.status_code == 200, second.text
        page2 = second.json()
        assert len(page2["results"]) == 1 and page2["next_cursor"]

        third = api.post("/api/search", {**body, "cursor": page2["next_cursor"]})
        assert third.status_code == 200, third.text
        page3 = third.json()
        assert len(page3["results"]) == 1 and page3["next_cursor"] is None
        ids = [page["results"][0]["id"] for page in (page1, page2, page3)]
        assert len(set(ids)) == 3

        changed_filter = api.post(
            "/api/search",
            {"q": "viteză peste 160 km/h", "cursor": page1["next_cursor"], "limit": 1},
        )
        assert changed_filter.status_code == 400
        tampered = page1["next_cursor"][:-1] + ("A" if page1["next_cursor"][-1] != "A" else "B")
        assert api.post("/api/search", {**body, "cursor": tampered}).status_code == 400
        other_tenant = login(world.b.operator)
        foreign_cursor = {**body, "cursor": page1["next_cursor"]}
        assert other_tenant.post("/api/search", foreign_cursor).status_code == 400

        saved = api.post(
            "/api/saved-searches", {"name": "Paged archive", "query": body["q"]}
        ).json()
        saved_first = api.post(f"/api/saved-searches/{saved['id']}/run", {"limit": 1}).json()
        assert saved_first["next_cursor"]
        saved_second = api.post(
            f"/api/saved-searches/{saved['id']}/run",
            {"cursor": saved_first["next_cursor"], "limit": 1},
        ).json()
        assert saved_second["results"]
        assert saved_second["results"][0]["id"] != saved_first["results"][0]["id"]

    def test_saved_searches_are_owner_scoped_audited_and_store_only_filters(
        self, login: Any, world: World, event_no: int
    ) -> None:
        api = operator(login, world)
        payload = {"name": "Fast traffic", "query": "viteză peste 140 km/h SECRET-PLATE-123"}
        created = api.post("/api/saved-searches", payload)
        assert created.status_code == 201, created.text
        saved = created.json()
        assert saved["filters"]["min_speed_kmh"] == 140
        assert "SECRET-PLATE-123" not in created.text
        with tenant_session(world.a.id) as db:
            stored = db.get(SavedSearch, uuid.UUID(saved["id"]))
            assert stored is not None and "SECRET-PLATE-123" not in str(stored.filters)

        assert api.post("/api/saved-searches", payload).status_code == 409
        assert len(api.get("/api/saved-searches").json()) == 1
        assert login(world.a.admin).get("/api/saved-searches").json() == []
        assert login(world.a.auditor).get("/api/saved-searches").status_code == 403
        other = login(world.b.operator)
        assert other.get(f"/api/saved-searches/{saved['id']}/run").status_code == 405
        assert other.post(f"/api/saved-searches/{saved['id']}/run").status_code == 404

        run = api.post(f"/api/saved-searches/{saved['id']}/run")
        assert run.status_code == 200, run.text
        assert [event["id"] for event in run.json()["results"]] == [event_no]
        assert "SECRET-PLATE-123" not in run.text

        updated = api.put(
            f"/api/saved-searches/{saved['id']}",
            {"name": "Very fast traffic", "query": "viteză peste 160 km/h"},
        )
        assert updated.status_code == 200, updated.text
        assert api.post(f"/api/saved-searches/{saved['id']}/run").json()["results"] == []
        assert api.delete(f"/api/saved-searches/{saved['id']}").status_code == 204
        assert api.delete(f"/api/saved-searches/{saved['id']}").status_code == 404
        assert {
            "alert.saved_search.created",
            "alert.saved_search.updated",
            "alert.saved_search.deleted",
        } <= set(audit_actions(world.a.id))

    def test_audit_view_is_timezone_aware_and_alert_only(
        self, login: Any, world: World, event_no: int
    ) -> None:
        entries = operator(login, world).get("/api/audit").json()
        assert entries and all(e["at"].endswith(("Z", "+00:00")) for e in entries)
        assert {e["action"] for e in entries} <= {
            "login",
            "detected",
            "viewed",
            "confirmed",
            "rejected",
            "vlm_confirmed",
            "vlm_rejected",
            "vlm_uncertain",
        }

    def test_superseded_events_disappear(
        self, login: Any, world: World, pipe: Pipeline, event_no: int
    ) -> None:
        from tests.test_contract_ingest import send

        send(pipe, "DELETE", "/api/ingest/cameras/demo-highway")
        api = operator(login, world)
        assert all(e["id"] != event_no for e in api.get("/api/events").json())
        assert api.get(f"/api/events/{event_no}").status_code == 404


class TestCameras:
    def test_cameras_use_slugs_and_link_the_recording(
        self, login: Any, world: World, pipe: Pipeline
    ) -> None:
        from tests.test_contract_ingest import send

        send(
            pipe,
            "PUT",
            "/api/ingest/cameras/demo-highway/video",
            files={"video": ("a.mp4", MP4, "video/mp4")},
        )
        api = operator(login, world)
        cams = {c["id"]: c for c in api.get("/api/cameras").json()}
        assert cams["demo-highway"]["uuid"]
        assert cams["demo-highway"]["timezone"] == "Europe/Bucharest"
        assert cams["demo-highway"]["video_url"]
        assert api.get(cams["demo-highway"]["video_url"]).content == MP4
        assert "last_seen_at" in cams["demo-highway"]


class TestIsolation:
    def test_unit_b_cannot_see_unit_a_events_or_media(
        self, login: Any, world: World, event_no: int
    ) -> None:
        a_event = operator(login, world).get(f"/api/events/{event_no}").json()
        b = login(world.b.operator)
        assert all(e["camera_id"] != "demo-highway" for e in b.get("/api/events").json())
        # Unit B has no event with that number: same 404 as any missing id.
        assert b.get(f"/api/events/{event_no}").status_code == 404
        # A's media link does not work for B (signature is bound to A's user, RLS hides it).
        assert b.get(a_event["clip_url"]).status_code in (403, 404)

    def test_media_link_is_bound_to_the_user(self, login: Any, world: World, event_no: int) -> None:
        url = operator(login, world).get(f"/api/events/{event_no}").json()["clip_url"]
        assert login(world.a.admin).get(url).status_code == 403
        assert operator(login, world).get(url.replace("sig=", "sig=x")).status_code == 403

    def test_patrol_sees_only_assigned_alerts(
        self, login: Any, world: World, event_no: int
    ) -> None:
        patrol = login(world.a.patrol)
        assert patrol.get(f"/api/events/{event_no}").status_code == 404
        assert all(e["id"] != event_no for e in patrol.get("/api/events").json())
        decision = patrol.post(f"/api/events/{event_no}/decision", {"decision": "reject"})
        assert decision.status_code == 403

    def test_auditor_cannot_read_alerts(self, login: Any, world: World) -> None:
        auditor = login(world.a.auditor)
        assert auditor.get("/api/events").status_code == 403
        assert auditor.get("/api/stream").status_code == 403


def _principal(world: World) -> Principal:
    """A live session for the operator, as get_principal would load it."""
    now = datetime.now(UTC)
    with tenant_session(world.a.id) as db:
        user = db.get(User, world.a.operator.id)
        session = UserSession(
            tenant_id=world.a.id,
            user_id=world.a.operator.id,
            expires_at=now + timedelta(hours=1),
            last_seen_at=now,
            mfa_verified_at=now,
        )
        db.add(session)
        db.commit()
        assert user is not None
        return Principal(user=user, session=session, db=db)


class TestStream:
    def test_replays_alerts_after_last_event_id(
        self, world: World, pipe: Pipeline, event_no: int
    ) -> None:
        second = post_event(pipe).json()["id"]
        principal = _principal(world)
        after_event, after_audit = contract_api.cursors(principal, str(event_no))
        chunk, cursor, _ = contract_api.poll(principal, after_event, after_audit)
        assert chunk is not None
        assert f"id: {second}\nevent: alert" in chunk and f"id: {event_no}\n" not in chunk
        assert cursor == second

    def test_poll_works_after_the_request_session_is_released(
        self, world: World, pipe: Pipeline, event_no: int
    ) -> None:
        from app.db import get_sessionmaker, set_tenant

        stored = _principal(world)
        db = get_sessionmaker()()  # open, like the request's session in get_principal
        set_tenant(db, world.a.id)
        user, session = db.get(User, stored.user.id), db.get(UserSession, stored.session.id)
        assert user is not None and session is not None
        principal = Principal(user=user, session=session, db=db)
        after_event, after_audit = contract_api.cursors(principal, str(event_no - 1))
        contract_api.release_request_session(principal)
        chunk, cursor, _ = contract_api.poll(principal, after_event, after_audit)
        assert chunk is not None and cursor == event_no

    def test_revoked_session_ends_the_stream(self, world: World, event_no: int) -> None:
        principal = _principal(world)
        with tenant_session(world.a.id) as db:
            row = db.get(UserSession, principal.session.id)
            assert row is not None
            row.revoked_at = datetime.now(UTC)
            db.commit()
        chunk, _, _ = contract_api.poll(principal, 0, 0)
        assert chunk is None

    def test_requires_login(self, client: ApiClient) -> None:
        assert client.get("/api/stream").status_code == 401


class TestReviewFindings:
    """PR #12 review: regressions that must not come back."""

    def test_long_vlm_text_is_truncated_not_rejected(self, world: World, pipe: Pipeline) -> None:
        from tests.test_contract_ingest import alerts_of

        r = post_event(pipe, {**EVENT, "vlm_status": "confirmed", "vlm_text": "x" * 400})
        assert r.status_code == 200, r.text
        assert len(alerts_of(world.a.id)[0].vlm_text or "") == 300

    @pytest.mark.parametrize(
        ("sent", "stored"), [("full", "full"), (None, "unknown"), ("off", "off")]
    )
    def test_redaction_level_reported_by_the_pipeline_is_kept(
        self, world: World, pipe: Pipeline, sent: str | None, stored: str
    ) -> None:
        from app.models import Evidence

        details = {"redaction": sent} if sent else {}
        assert post_event(pipe, {**EVENT, "details": details}).status_code == 200
        with tenant_session(world.a.id) as db:
            levels = {
                e.redaction for e in db.query(Evidence).filter(Evidence.alert_id.is_not(None))
            }
        assert stored in levels

    def test_unknown_redaction_value_is_rejected(self, world: World, pipe: Pipeline) -> None:
        assert post_event(pipe, {**EVENT, "details": {"redaction": "none"}}).status_code == 422

    def test_queue_limit_keeps_the_most_urgent(
        self, login: Any, world: World, pipe: Pipeline, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(contract_api, "MAX_EVENTS", 2)
        post_event(pipe, {**EVENT, "type": "congestion"})
        post_event(pipe, {**EVENT, "type": "congestion"})
        post_event(pipe, {**EVENT, "type": "wrong_way"})
        listed = operator(login, world).get("/api/events").json()
        assert listed[0]["type"] == "wrong_way" or listed[0]["priority"] == "critical"

    def test_concurrent_decisions_cannot_both_win(
        self, login: Any, world: World, event_no: int
    ) -> None:
        a, b = operator(login, world), login(world.a.admin)
        url = f"/api/events/{event_no}/decision"
        first = a.post(url, {"decision": "reject"})
        second = b.post(url, {"decision": "confirm", "action": "monitor"})
        assert first.status_code == 200 and second.status_code == 409
        assert audit_actions(world.a.id).count("alert.rejected") == 1
        assert "alert.confirmed" not in audit_actions(world.a.id)


class TestStreamScoping:
    """PR #12 review round 2."""

    def test_patrol_stream_carries_no_history_of_unassigned_alerts(
        self, login: Any, world: World, event_no: int
    ) -> None:
        operator(login, world).post(
            f"/api/events/{event_no}/decision",
            {"decision": "confirm", "action": "monitor", "note": "SECRET-NOTE"},
        )
        now = datetime.now(UTC)
        with tenant_session(world.a.id) as db:
            user = db.get(User, world.a.patrol.id)
            session = UserSession(
                tenant_id=world.a.id,
                user_id=world.a.patrol.id,
                expires_at=now + timedelta(hours=1),
                last_seen_at=now,
                mfa_verified_at=now,
            )
            db.add(session)
            db.commit()
            assert user is not None
            patrol = Principal(user=user, session=session, db=db)
        chunk, _, _ = contract_api.poll(patrol, 0, 0)
        assert chunk is not None
        assert "SECRET-NOTE" not in chunk and '"action":"login"' not in chunk

    def test_stream_releases_the_request_db_session(self, world: World) -> None:
        principal = _principal(world)
        principal.db.begin()
        contract_api.release_request_session(principal)
        assert not principal.db.in_transaction()


def test_register_camera_rejects_unknown_timezone(world: World) -> None:
    from app.cli import main

    with pytest.raises(SystemExit):
        main(
            [
                "register-camera",
                "--tenant",
                "unit-a",
                "--slug",
                "x1",
                "--name",
                "X",
                "--location",
                "Y",
                "--timezone",
                "Europe/Bucurest",
            ]
        )


class TestMfaExemption:
    """The exemption is a demo switch: off by default, enabled here explicitly."""

    @pytest.fixture(autouse=True)
    def _enable_exemption(self, monkeypatch: pytest.MonkeyPatch) -> Any:
        from app.config import get_settings

        monkeypatch.setenv("RS_MFA_EXEMPTION_ENABLED", "true")
        get_settings.cache_clear()
        yield
        monkeypatch.undo()
        get_settings.cache_clear()

    def _exempt(self, world: World, user: Any) -> None:
        from app.cli import main

        tenant = "unit-a" if user.tenant_id == world.a.id else "unit-b"
        main(["set-mfa-exempt", "--tenant", tenant, "--email", user.email])

    def test_exempt_account_logs_in_with_password_only(
        self, client: ApiClient, world: World
    ) -> None:
        user = world.a.operator
        self._exempt(world, user)
        r = client.post("/api/login", {"operator": user.email, "password": user.password})
        assert r.status_code == 200, r.text
        assert r.json()["mfa_required"] is False and r.json()["operator"] == "operator.a"
        assert client.get("/api/events").status_code == 200
        with admin_conn() as conn:
            details = conn.execute(
                "SELECT details FROM audit_log WHERE tenant_id = %s AND action = %s "
                "ORDER BY seq DESC LIMIT 1",
                (world.a.id, "auth.login.success"),
            ).fetchone()[0]
        assert details == {"mfa": "exempt"}

    def test_exempt_account_still_needs_the_right_password(
        self, client: ApiClient, world: World
    ) -> None:
        self._exempt(world, world.a.operator)
        r = client.post("/api/login", {"operator": world.a.operator.email, "password": "wrong"})
        assert r.status_code == 401

    def test_other_accounts_still_need_mfa(self, client: ApiClient, world: World) -> None:
        self._exempt(world, world.a.operator)
        admin = world.a.admin
        r = client.post("/api/login", {"operator": admin.email, "password": admin.password})
        assert r.json()["mfa_required"] is True
        assert client.get("/api/events").status_code == 401

    def test_auth_route_and_revocation(self, client: ApiClient, world: World) -> None:
        from app.cli import main

        user = world.a.operator
        self._exempt(world, user)
        r = client.post("/api/auth/login", {"email": user.email, "password": user.password})
        assert r.json() == {"mfa_required": False, "enrollment_required": False}
        main(["set-mfa-exempt", "--tenant", "unit-a", "--email", user.email, "--off"])
        fresh = ApiClient()
        r = fresh.post("/api/login", {"operator": user.email, "password": user.password})
        assert r.json()["mfa_required"] is True


class TestMfaIsMandatoryByDefault:
    def test_flag_is_off_by_default(self) -> None:
        from app.config import Settings

        assert Settings().mfa_exemption_enabled is False  # type: ignore[call-arg]

    @pytest.mark.parametrize(
        "path,field", [("/api/login", "operator"), ("/api/auth/login", "email")]
    )
    def test_password_alone_never_opens_a_session(
        self, client: ApiClient, world: World, path: str, field: str
    ) -> None:
        user = world.a.operator
        r = client.post(path, {field: user.email, "password": user.password})
        assert r.status_code == 200
        assert r.json()["mfa_required"] is True
        assert client.get("/api/events").status_code == 401
        assert client.get("/api/auth/me").status_code == 401

    def test_flagged_account_still_needs_mfa_while_switch_is_off(
        self, client: ApiClient, world: World
    ) -> None:
        from app.cli import main

        user = world.a.operator
        main(["set-mfa-exempt", "--tenant", "unit-a", "--email", user.email])
        r = client.post("/api/login", {"operator": user.email, "password": user.password})
        assert r.json()["mfa_required"] is True
        assert client.get("/api/events").status_code == 401

    def test_short_usernames_are_not_mapped_to_a_demo_domain(
        self, client: ApiClient, world: World
    ) -> None:
        r = client.post(
            "/api/login", {"operator": "operator", "password": world.a.operator.password}
        )
        assert r.status_code == 401

    def test_exemption_ignored_in_production(
        self, client: ApiClient, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.cli import main
        from app.config import get_settings

        user = world.a.operator
        main(["set-mfa-exempt", "--tenant", "unit-a", "--email", user.email])
        monkeypatch.setenv("RS_MFA_EXEMPTION_ENABLED", "true")
        monkeypatch.setenv("RS_ENV", "production")
        get_settings.cache_clear()
        try:
            r = client.post("/api/login", {"operator": user.email, "password": user.password})
            assert r.json()["mfa_required"] is True
        finally:
            monkeypatch.undo()
            get_settings.cache_clear()
