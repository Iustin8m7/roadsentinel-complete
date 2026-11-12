"""API flow: login gate, ingestion with token, operator decision, audit trail, search."""
import importlib
import json

import pytest
from fastapi.testclient import TestClient

EVENT = {"camera_id": "cam-test", "camera_name": "Cameră test", "location": "Iași", "type": "very_high_speed",
         "priority": "high", "occurred_at": "2026-10-16T14:05:16", "video_t": 16.5, "track_id": 72,
         "object_class": "car", "speed_kmh": 155.0, "rule": "Viteză 155 km/h > prag 150 km/h",
         "details": {"measured_kmh": 155.0}, "vlm_status": "skipped", "vlm_text": None}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/t.db")
    monkeypatch.setenv("DASHBOARD_PASSWORD", "legacy-test-pw")
    monkeypatch.setenv("INGEST_TOKEN", "tok")
    monkeypatch.setenv("COOKIE_SECURE", "0")
    monkeypatch.delenv("S3_BUCKET", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from roadsentinel import server
    importlib.reload(server)
    return TestClient(server.app)


def ingest(client, token="tok", event=EVENT):
    return client.post("/api/ingest/events", headers={"Authorization": f"Bearer {token}"},
                       data={"event": json.dumps(event)},
                       files={"keyframe": ("e1.jpg", b"jpg-bytes", "image/jpeg"),
                              "clip": ("e1.mp4", b"mp4-bytes", "video/mp4")})


def login(client, password="legacy-test-pw"):
    return client.post("/api/login", json={"operator": "ag. Popescu", "password": password})


def test_dashboard_requires_login(client):
    assert client.get("/api/events").status_code == 401
    assert login(client, "gresit").status_code == 401
    assert login(client).status_code == 200
    assert client.get("/api/events").status_code == 200


def test_ingest_requires_token(client):
    assert ingest(client, token="gresit").status_code == 401


def test_ingested_event_is_listed_with_media(client):
    event_id = ingest(client).json()["id"]
    login(client)
    [e] = client.get("/api/events").json()
    assert e["id"] == event_id and e["speed_kmh"] == 155.0
    assert client.get(e["clip_url"]).content == b"mp4-bytes"


def test_decision_is_attributed_to_logged_in_operator(client):
    event_id = ingest(client).json()["id"]
    login(client)
    client.post(f"/api/events/{event_id}/view", json={})
    bad = client.post(f"/api/events/{event_id}/decision", json={"decision": "confirm"})
    assert bad.status_code == 400  # confirming needs an action
    r = client.post(f"/api/events/{event_id}/decision", json={"decision": "confirm", "action": "dispatch_patrol"})
    assert r.json()["status"] == "confirmed"
    trail = [(a["actor"], a["action"]) for a in r.json()["audit"]]
    assert trail == [("system", "detected"), ("ag. Popescu", "viewed"), ("ag. Popescu", "confirmed")]


def test_search_by_speed(client):
    ingest(client)
    login(client)
    r = client.get("/api/search", params={"q": "viteză peste 140 km/h"}).json()
    assert len(r["results"]) == 1
    assert client.get("/api/search", params={"q": "viteză peste 160 km/h"}).json()["results"] == []


def test_reprocessing_a_camera_replaces_its_events(client):
    ingest(client)
    r = client.delete("/api/ingest/cameras/cam-test", headers={"Authorization": "Bearer tok"})
    assert r.status_code == 204
    login(client)
    assert client.get("/api/events").json() == []


# ---- review findings (PR #1) ----

@pytest.mark.parametrize("patch", [
    {"type": "ufo"},                              # unknown event type
    {"rule": None},                               # missing required field
    {"camera_id": "../../escaped"},               # path traversal
    {"occurred_at": "not-a-date"},
])
def test_invalid_ingest_is_rejected_and_stores_nothing(client, tmp_path, patch):
    r = ingest(client, event={**EVENT, **patch})
    assert r.status_code == 422
    assert not (tmp_path / "escaped").exists()
    login(client)
    assert client.get("/api/events").json() == []


def test_ingest_rejects_bad_json(client):
    r = client.post("/api/ingest/events", headers={"Authorization": "Bearer tok"}, data={"event": "{nope"},
                    files={"keyframe": ("a.jpg", b"x", "image/jpeg"), "clip": ("a.mp4", b"x", "video/mp4")})
    assert r.status_code == 422


def test_priority_comes_from_event_type(client):
    ingest(client, event={**EVENT, "priority": "info"})
    login(client)
    assert client.get("/api/events").json()[0]["priority"] == "high"


def test_camera_routes_reject_path_traversal(client):
    h = {"Authorization": "Bearer tok"}
    assert client.delete("/api/ingest/cameras/..", headers=h).status_code in (400, 404, 422)
    assert client.delete("/api/ingest/cameras/a.b", headers=h).status_code == 422


def test_media_does_not_serve_files_outside_media_root(client, tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("nu")
    login(client)
    for path in (f"/media/{secret}", f"/media//{secret}", "/media/../t.db"):
        assert client.get(path).status_code != 200


def test_non_ascii_password(tmp_path, monkeypatch, client):
    monkeypatch.setenv("DASHBOARD_PASSWORD", "parolă")
    from roadsentinel import server
    importlib.reload(server)
    c = TestClient(server.app)
    assert c.post("/api/login", json={"operator": "x", "password": "gresită"}).status_code == 401
    assert c.post("/api/login", json={"operator": "x", "password": "parolă"}).status_code == 200


def test_decided_event_cannot_be_decided_again(client):
    event_id = ingest(client).json()["id"]
    login(client)
    url = f"/api/events/{event_id}/decision"
    assert client.post(url, json={"decision": "reject", "action": "dispatch_patrol"}).status_code == 200
    assert client.post(url, json={"decision": "confirm", "action": "monitor"}).status_code == 409
    reject = client.get(f"/api/events/{event_id}").json()["audit"][-1]
    assert reject["action"] == "rejected" and reject["note"] is None  # no action label on reject


def test_audit_times_are_timezone_aware(client):
    ingest(client)
    login(client)
    assert client.get("/api/audit").json()[0]["at"].endswith(("Z", "+00:00"))


def test_stream_replays_events_missed_while_disconnected(client):
    first = ingest(client).json()["id"]
    second = ingest(client).json()["id"]
    login(client)
    from roadsentinel import server
    gen = server.stream_events(after_event=first, after_audit=10**9)
    chunk = next(gen)
    assert f"id: {second}" in chunk and "event: alert" in chunk
