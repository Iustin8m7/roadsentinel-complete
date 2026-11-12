"""One pass of the real worker config client against a local API: fetch the camera's desired
config, verify it (fingerprint, schema, frame size, frame rate), acknowledge it, send one
heartbeat and stop gracefully (which releases the lease). Prints {"applied_revision": n}.
Used by browser checks to show the difference between a revision that was activated and one a
worker has applied.

usage: E2E_PASSWORD=... worker_once.py --api http://localhost:8441 --origin http://localhost:5441
       --video CLIP [--slug e2e-replay]

The detector is not run here (scripts/e2e/camera_detector_e2e.py does that); only the worker's
config handshake is, with the same code the pipeline uses (roadsentinel/remote_config.py).
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import cv2
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
from camera_control_e2e import Session

from roadsentinel import remote_config, sink

ap = argparse.ArgumentParser()
ap.add_argument("--api", required=True)
ap.add_argument("--origin", required=True)
ap.add_argument("--password", default=os.environ.get("E2E_PASSWORD"), help="default: $E2E_PASSWORD")
ap.add_argument("--video", required=True)
ap.add_argument("--slug", default="e2e-replay")
a = ap.parse_args()
assert a.password, "set E2E_PASSWORD or pass --password"

admin = Session(a.api, a.origin, "admin", a.password)
account = next(x for x in admin.ok("GET", "/api/service-accounts") if x["name"] == "e2e-worker")
for old in account["keys"]:
    if not old["revoked_at"]:
        admin.call("DELETE", f"/api/service-accounts/{account['id']}/keys/{old['key_id']}")
key = admin.ok("POST", f"/api/service-accounts/{account['id']}/keys", expect=(201,))

cap = cv2.VideoCapture(a.video)
width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = float(cap.get(cv2.CAP_PROP_FPS))
cap.release()
assert width and height and fps, "fixture video unreadable"

out = sink.RemoteSink(a.api, key["key_id"], key["secret"])
base_cfg = yaml.safe_load((ROOT / "cameras/demo-urban.yaml").read_text())
deadline = time.time() + 150
while True:  # an earlier worker's lease (90 s) fences this one out until it expires or is released
    client = remote_config.RemoteConfigClient(out.request_json, a.slug, frame_size=(width, height),
                                              source_fps=fps, source_is_stream=False)
    try:
        client.initial(base_cfg)
        answer = client.heartbeat(source_fps=round(fps, 2), frame_width=width, frame_height=height,
                                  last_frame_at=remote_config.utc_iso(time.time()))
        break
    except remote_config.RemoteConfigError as err:
        if err.reason != "duplicate_worker" or time.time() > deadline:
            raise
        time.sleep(5)
assert answer["lease"] == "holder", answer
client.heartbeat(health="stopped")  # graceful stop: releases the lease for the next pass
print(json.dumps({"applied_revision": client.applied[0]}))
