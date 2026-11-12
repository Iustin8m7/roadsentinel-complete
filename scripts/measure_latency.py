#!/usr/bin/env python3
"""Measure ingest -> operator-screen latency of a RUNNING API over real HTTP (loopback or network).

It signs events exactly like the pipeline (roadsentinel/sink.py), listens on the SSE stream
(/api/stream) as an operator and, for every event, records
  ingest_ms   time the ingest request took (multipart upload, encryption, DB, audit)
  e2e_ms      from just before the ingest request until the `alert` event arrives on the stream
Optional --clients N opens N extra SSE connections (same session) to see how a crowd of viewers affects it.
Needs an operator that can log in with a password only: use a LOCAL dev API with
RS_MFA_EXEMPTION_ENABLED=true and `python -m app.cli demo-accounts --exempt-mfa` (never production).

    RS_MEASURE_PASSWORD=... RS_INGEST_SECRET=... python scripts/measure_latency.py \
        --url http://127.0.0.1:8099 --operator operator@roadsentinel.local \
        --key-id <id> --camera lat-cam --n 40 --clients 20

Results are per-method numbers for THIS setup (hardware, network, database); say so when quoting them.
"""
import argparse
import json
import os
import statistics
import sys
import tempfile
import threading
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from roadsentinel.sink import RemoteSink  # noqa: E402

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 600 + b"\xff\xd9"
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 1000


def login(base, operator, password, origin):
    c = httpx.Client(base_url=base, timeout=30, headers={"Origin": origin})
    token = c.get("/api/auth/csrf").json()["csrf_token"]
    c.headers["X-CSRF-Token"] = token
    r = c.post("/api/login", json={"operator": operator, "password": password})
    r.raise_for_status()
    if r.json().get("mfa_required"):
        sys.exit("this operator needs MFA; use a local dev API with the demo MFA exemption (see --help)")
    return c


def sse_listener(client, arrivals, stop, ready):
    with client.stream("GET", "/api/stream", timeout=None) as r:
        ready.set()
        event = None
        for line in r.iter_lines():
            if stop.is_set():
                return
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and event == "alert":
                try:
                    arrivals.setdefault(json.loads(line[5:])["id"], time.perf_counter())
                except (ValueError, KeyError, TypeError):
                    pass
            elif not line:
                event = None


def pct(values, p):
    v = sorted(values)
    k = (len(v) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True)
    ap.add_argument("--origin")
    ap.add_argument("--operator", required=True)
    ap.add_argument("--key-id", required=True)
    ap.add_argument("--camera", required=True)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--clients", type=int, default=0, help="extra SSE connections (other operators)")
    ap.add_argument("--gap", type=float, default=1.37, help="seconds between events (not a multiple of the poll interval)")
    a = ap.parse_args(argv)
    password, secret = os.environ["RS_MEASURE_PASSWORD"], os.environ["RS_INGEST_SECRET"]
    origin = a.origin or a.url
    stop = threading.Event()
    arrivals, extras = {}, []
    me = login(a.url, a.operator, password, origin)
    ready = threading.Event()
    threading.Thread(target=sse_listener, args=(me, arrivals, stop, ready), daemon=True).start()
    for _ in range(a.clients):
        # Extra viewers reuse the logged-in session on separate connections: the login rate limit
        # (correctly) refuses dozens of logins per minute from one address.
        c = httpx.Client(base_url=a.url, timeout=30, cookies=me.cookies, headers=dict(me.headers))
        extras.append(c)
        threading.Thread(target=sse_listener, args=(c, {}, stop, threading.Event()), daemon=True).start()
    ready.wait(10)
    time.sleep(2)
    sink = RemoteSink(a.url, a.key_id, secret)
    tmp = Path(tempfile.mkdtemp())
    (tmp / "k.jpg").write_bytes(JPEG)
    (tmp / "c.mp4").write_bytes(MP4)
    sent, ingest_ms = {}, []
    for i in range(a.n):
        t0 = time.perf_counter()
        eid = sink.add_event(
            {"camera_id": a.camera, "type": "very_high_speed", "occurred_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
             "video_t": 1.0, "track_id": i, "object_class": "car", "speed_kmh": 150.0, "rule": "latency probe",
             "details": {"redaction": "full"}, "event_key": f"latency-probe-{time.time_ns()}", "vlm_status": "skipped"},
            tmp / "k.jpg", tmp / "c.mp4")
        t1 = time.perf_counter()
        sent[eid] = t0
        ingest_ms.append((t1 - t0) * 1000)
        time.sleep(a.gap)
    time.sleep(3)
    stop.set()
    e2e = [(arrivals[e] - t0) * 1000 for e, t0 in sent.items() if e in arrivals]
    missed = len(sent) - len(e2e)

    def line(name, v):
        return (f"{name:10} n={len(v):3}  p50={pct(v, .5):7.0f}  p95={pct(v, .95):7.0f}  max={max(v):7.0f}  "
                f"mean={statistics.fmean(v):7.0f} ms") if v else f"{name}: no data"

    print(f"target {a.url}  events {a.n}  extra SSE clients {a.clients}  missed on the stream: {missed}")
    print(line("ingest_ms", ingest_ms))
    print(line("e2e_ms", e2e))
    return 0 if not missed else 1


if __name__ == "__main__":
    sys.exit(main())
