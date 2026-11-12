"""Persisted notification contract on the disposable PostgreSQL/RLS test cluster."""

from sqlalchemy import select

from app.db import tenant_session
from app.models import Alert, NotificationEvent, Role
from app.services.notifications import record


def test_inbox_receipt_and_tenant_scope(world, login):
    alert_id = world.data["a"]["alerts"][0]
    with tenant_session(world.a.id) as db:
        alert = db.get(Alert, alert_id)
        record(db, alert, "candidate_created")
        db.commit()
        event_id = db.scalar(select(NotificationEvent.id).where(NotificationEvent.alert_id == alert_id))
    operator = login(world.a.operator)
    page = operator.get("/api/notifications")
    assert page.status_code == 200, page.text
    assert page.json()["unread"] == 1
    assert page.json()["items"][0]["incident_id"] == str(alert_id)
    assert page.json()["items"][0]["id"] == str(event_id)
    assert operator.post(f"/api/notifications/{event_id}/read").status_code == 200
    assert operator.post(f"/api/notifications/{event_id}/read").status_code == 200
    assert operator.get("/api/notifications").json()["unread"] == 0
    assert operator.post(f"/api/notifications/{event_id}/acknowledge").status_code == 200
    assert operator.get("/api/notifications").json()["items"][0]["acknowledged_at"]
    other = login(world.b.operator)
    assert other.get("/api/notifications").json()["unread"] == 0
    assert other.post(f"/api/notifications/{event_id}/read").status_code == 404
    patrol = login(world.a.patrol)
    assert patrol.get("/api/notifications").json()["unread"] == 0  # unassigned alert
    auditor = login(world.a.auditor)
    assert auditor.get("/api/notifications").status_code == 403


def test_synthetic_excluded_from_inbox(world):
    alert_id = world.data["a"]["alerts"][0]
    with tenant_session(world.a.id) as db:
        alert = db.get(Alert, alert_id)
        alert.details = {"origin": "local_replay", "synthetic": True}
        record(db, alert, "candidate_created")
        db.commit()
        assert db.scalar(select(NotificationEvent).where(NotificationEvent.alert_id == alert_id)) is None
        alert.details = {"scenario_type": "synthetic_test", "test_only": True}
        record(db, alert, "rejected")
        db.commit()
        assert db.scalar(select(NotificationEvent).where(NotificationEvent.alert_id == alert_id)) is None


def test_operator_contract_decision_emits_same_incident_revision(world, login):
    alert_id = world.data["a"]["alerts"][0]
    with tenant_session(world.a.id) as db:
        number = db.scalar(select(Alert.number).where(Alert.id == alert_id))
    operator = login(world.a.operator)
    decided = operator.post(f"/api/events/{number}/decision", {
        "decision": "reject", "note": "Controlled negative observation, not a traffic incident",
    })
    assert decided.status_code == 200, decided.text
    page = operator.get("/api/notifications").json()
    assert page["unread"] == 1
    assert page["items"][0]["incident_id"] == str(alert_id)
    assert page["items"][0]["kind"] == "rejected"
    repeated = operator.post(f"/api/events/{number}/decision", {
        "decision": "reject", "note": "Repeated stale decision",
    })
    assert repeated.status_code == 409
    assert operator.get("/api/notifications").json()["unread"] == 1


def test_sound_preference_persists_per_user_and_tenant(world, login):
    operator = login(world.a.operator)
    assert operator.get("/api/notifications/preferences").json() == {"sound_on_critical": False}
    assert operator.put("/api/notifications/preferences", {"sound_on_critical": True}).status_code == 200
    assert operator.get("/api/notifications/preferences").json() == {"sound_on_critical": True}
    assert login(world.a.operator).get("/api/notifications/preferences").json() == {"sound_on_critical": True}
    assert login(world.b.operator).get("/api/notifications/preferences").json() == {"sound_on_critical": False}
