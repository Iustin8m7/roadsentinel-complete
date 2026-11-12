import json

from tests.test_contract_ingest import add_camera
from tests.test_ingest_auth import make_pipeline


def test_signed_heartbeat_owns_lease_and_duplicate_worker_stops(world):
    camera = add_camera(world.a.id, "lease-camera")
    pipe, _ = make_pipeline(world.a.id, camera_ids=[camera])
    path = "/api/ingest/cameras/lease-camera/heartbeat"

    def send(epoch, seq):
        return pipe.post(
            path, json.dumps(dict(worker_epoch=epoch, seq=seq, health="starting")).encode()
        )

    first = send("mission_worker_a", 1)
    assert first.status_code == 200, first.text
    assert first.json()["lease"] == "holder"
    second = send("mission_worker_b", 1)
    assert second.status_code == 200, second.text
    assert second.json()["directive"] == "stop"
    assert send("mission_worker_a", 2).json()["lease"] == "holder"
    assert pipe.post(path, b"not-json").status_code == 422
