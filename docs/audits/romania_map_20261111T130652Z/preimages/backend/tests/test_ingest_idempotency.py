# ruff: noqa: F811, F401  (pytest fixtures imported from test_contract_ingest)
"""Idempotent ingestion, the new rule types and the heartbeat's rate status."""

from __future__ import annotations

import json
import uuid
from typing import Any

from roadsentinel.alerts import AlertGate
from roadsentinel.geometry import Calibration, Zone
from roadsentinel.rules import RuleEngine

from app.db import tenant_session
from app.models import Alert, AuditLog, Camera, Evidence
from tests.conftest import World
from tests.test_contract_ingest import (
    EVENT,
    alerts_of,
    highway,
    pipe,
    post_event,
    send,
)
from tests.test_ingest_auth import Pipeline

KEY = "iasi-piata-unirii:event_1792315896889_very_high_speed"


class TestIdempotentIngest:
    def test_retry_with_the_same_key_returns_the_same_alert(
        self, world: World, pipe: Pipeline
    ) -> None:
        first = post_event(pipe, {**EVENT, "event_key": KEY})
        second = post_event(pipe, {**EVENT, "event_key": KEY})
        assert first.status_code == 200 and second.status_code == 200
        assert first.json() == second.json()
        assert len(alerts_of(world.a.id)) == 1
        with tenant_session(world.a.id) as db:
            [alert] = alerts_of(world.a.id)
            assert db.query(Evidence).filter(Evidence.alert_id == alert.id).count() == 2

    def test_different_keys_or_no_key_create_separate_alerts(
        self, world: World, pipe: Pipeline
    ) -> None:
        post_event(pipe, {**EVENT, "event_key": KEY})
        post_event(pipe, {**EVENT, "event_key": KEY + "-2"})
        post_event(pipe)
        post_event(pipe)
        assert len(alerts_of(world.a.id)) == 4

    def test_malformed_keys_are_rejected(self, pipe: Pipeline) -> None:
        for bad in ("short", "has space in it!!", "x" * 81):
            assert post_event(pipe, {**EVENT, "event_key": bad}).status_code == 422


class TestNewRuleTypes:
    def test_near_miss_and_object_on_roadway_are_accepted_with_derived_priority(
        self, world: World, pipe: Pipeline
    ) -> None:
        near = {**EVENT, "type": "near_miss", "rule": "TTC 1.1 s", "details": {"ttc_s": 1.1}}
        obj = {**EVENT, "type": "object_on_roadway", "object_class": "object", "rule": "obiect"}
        assert post_event(pipe, near).status_code == 200
        assert post_event(pipe, obj).status_code == 200
        by_type = {a.event_type: a for a in alerts_of(world.a.id)}
        assert by_type["near_miss"].priority.value == "high"
        assert by_type["object_on_roadway"].priority.value == "critical"
        assert by_type["object_on_roadway"].object_class == "object"

    def test_synthetic_rule_candidate_ingest_persistence_and_operator_review(
        self, world: World, pipe: Pipeline, login: Any
    ) -> None:
        """Production RuleEngine -> signed ingest -> PostgreSQL -> operator review/audit."""
        thresholds = {
            "speed_limit_kmh": 130,
            "very_high_speed_kmh": 150,
            "stopped_speed_kmh": 5,
            "stopped_seconds": 4,
            "hard_brake_mps2": 4.5,
            "headway_seconds": 0.8,
            "headway_min_speed_kmh": 60,
            "lane_change_m": 3.0,
            "lane_change_window_s": 1.5,
            "wrong_way_min_px": 120,
            "congestion_vehicles": 3,
            "congestion_avg_speed_kmh": 30,
            "congestion_seconds": 2,
        }
        road = Zone({
            "id": "synthetic-road",
            "name": "Synthetic test roadway",
            "kind": "carriageway",
            "direction": [0, 1],
            "polygon": [[0, 0], [80, 0], [80, 1000], [0, 1000]],
        })
        calibration = Calibration([[0, 0], [100, 0], [100, 1000], [0, 1000]], 10, 100)
        rule_engine = RuleEngine([road], thresholds, ["wrong_way"])
        generated = []
        for frame in range(100):
            t = frame / 25
            y = 900 - (60 / 3.6 * 10) * t
            generated.extend(rule_engine.update(
                t,
                [(72, "car", (40, y), (30, y - 20, 50, y))],
                calibration,
            ))
        assert len(generated) == 1 and generated[0]["type"] == "wrong_way"
        gated = AlertGate().filter(4.0, generated)
        assert gated == generated
        rule_event = gated[0]
        candidate = {
            **EVENT,
            "type": rule_event["type"],
            "rule": f"SYNTHETIC TEST: {rule_event['rule']}",
            "track_id": rule_event["track_id"],
            "object_class": rule_event["object_class"],
            "speed_kmh": rule_event["speed_kmh"],
            "event_key": "synthetic-wrong-way-review-001",
            "details": {
                "scenario_type": "synthetic_test",
                "test_only": True,
                **rule_event["details"],
                "rule_version": "test-fixture-v1",
            },
        }
        ingested = post_event(pipe, candidate)
        assert ingested.status_code == 200
        alert_number = ingested.json()["id"]
        with tenant_session(world.a.id) as db:
            alert_id = db.query(Alert.id).filter(Alert.number == alert_number).scalar()
        assert alert_id is not None
        alert_id = str(alert_id)

        operator = login(world.a.operator)
        detail = operator.get(f"/api/alerts/{alert_id}")
        assert detail.status_code == 200
        alert = detail.json()
        assert alert["event_type"] == "wrong_way"

        reviewed = operator.post(
            f"/api/alerts/{alert_id}/reject",
            json={"note": "SYNTHETIC TEST: deterministic rule-path validation"},
        )
        assert reviewed.status_code == 200
        assert reviewed.json()["status"] == "rejected"

        archived = operator.post("/api/search", json={"q": "wrong way"})
        assert archived.status_code == 200
        assert any(item["id"] == alert_number for item in archived.json()["results"])

        with tenant_session(world.a.id) as db:
            saved = db.get(Alert, uuid.UUID(alert_id))
            assert saved is not None and saved.status.value == "rejected"
            assert saved.details["scenario_type"] == "synthetic_test"
            actions = db.query(AuditLog).filter(AuditLog.resource_id == str(saved.id)).all()
            assert any(row.action == "alert.rejected" for row in actions)


class TestHeartbeatStatus:
    def _beat(self, pipe: Pipeline, body: dict[str, Any]) -> Any:
        raw = json.dumps(body).encode()
        target = "/api/ingest/cameras/demo-highway/heartbeat"
        headers = pipe.headers("POST", target, raw)
        headers["Content-Type"] = "application/json"
        return pipe.http.request("POST", target, content=raw, headers=headers)

    def _status(self, world: World, camera_id: uuid.UUID) -> Any:
        with tenant_session(world.a.id) as db:
            cam = db.get(Camera, camera_id)
            assert cam is not None
            return cam.status_info

    def test_status_is_stored_and_replaced(
        self, world: World, pipe: Pipeline, highway: uuid.UUID
    ) -> None:
        body = {
            "fps": 0.5,
            "rules": {
                "very_high_speed": {"supported": False, "min_fps": 5.0, "reason": "necesită ≥ 5.0"},
                "pedestrian_on_road": {"supported": True, "min_fps": 0.0},
            },
        }
        assert self._beat(pipe, body).status_code == 204
        info = self._status(world, highway)
        assert info["fps"] == 0.5 and info["rules"]["very_high_speed"]["supported"] is False
        assert "reported_at" in info
        assert self._beat(pipe, {"fps": 12.0, "rules": {}}).status_code == 204
        assert self._status(world, highway)["fps"] == 12.0

    def test_pipeline_telemetry_is_tenant_scoped_and_visible_to_operator_api(
        self, world: World, pipe: Pipeline, highway: uuid.UUID, login: Any
    ) -> None:
        body = {
            "fps": 2.9,
            "processing_fps": 1.84,
            "inference_latency_ms_p50": 84.57,
            "inference_latency_ms_p95": 93.07,
            "detections": 1085,
            "unique_tracks": 67,
            "tracks_by_class": {"bus": 13, "car": 32, "truck": 16},
            "model": "YOLOX-S ONNX / Supervision ByteTrack",
            "model_sha256": "c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063",
            "source": {"kind": "file", "state": "healthy", "frames": 105, "replay": True},
            "traffic": {
                "total_crossings": 9,
                "counts_by_line_lane_class": [
                    {
                        "line": "horizontal-mid",
                        "lane": "unassigned",
                        "object_class": "car",
                        "count": 4,
                    }
                ],
                "rolling_flow_per_minute": {"window_seconds": 60, "total": 2.5},
            },
        }
        assert self._beat(pipe, body).status_code == 204
        info = self._status(world, highway)
        assert info["unique_tracks"] == 67 and info["source"]["replay"] is True
        assert info["traffic"]["total_crossings"] == 9
        cams = login(world.a.operator).get("/api/cameras").json()
        camera = next(row for row in cams if row["id"] == "demo-highway")
        assert camera["status_info"]["tracks_by_class"]["car"] == 32
        assert camera["status_info"]["model_sha256"].endswith("8063")

    def test_empty_heartbeat_still_works_and_keeps_old_status(
        self, world: World, pipe: Pipeline, highway: uuid.UUID
    ) -> None:
        self._beat(pipe, {"fps": 3.0, "rules": {}})
        assert send(pipe, "POST", "/api/ingest/cameras/demo-highway/heartbeat").status_code == 204
        assert self._status(world, highway)["fps"] == 3.0

    def test_unknown_or_oversized_fields_are_refused(self, pipe: Pipeline) -> None:
        assert self._beat(pipe, {"fps": 1, "evil": "x"}).status_code == 422
        assert self._beat(pipe, {"fps": -1}).status_code == 422
        assert (
            self._beat(
                pipe, {"rules": {"r": {"supported": True, "min_fps": 1, "reason": "x" * 300}}}
            ).status_code
            == 422
        )
