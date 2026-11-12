# Local YOLO live-replay runbook

This runbook uses licensed recorded traffic served as a loopback MJPEG stream. The dashboard must
label it `REPLAY`; it is not a Romanian external camera. The repeatable acceptance harness starts
the replay server, FastAPI, disposable PostgreSQL, pipeline and Chromium browser together:

```bash
cd backend
RS_RUN_REAL_YOLO_E2E=1 \
RS_TEST_ADMIN_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:55438/postgres \
../.venv/bin/python -m pytest tests/test_real_yolo_e2e.py -q -s
```

This fixture drops/recreates only `rs_test`. Point it only at the disposable local test cluster.
The test requires local `models/yolox_s.onnx`, `/tmp/Street_traffic.webm`, Node 22, and the installed
Playwright Chromium. It uses a random loopback port for FastAPI and Vite's backend proxy. Shutdown
is bounded; processes are terminated and force-killed on timeout.

## Manual components

1. Install pinned dependencies into the project virtual environment and verify the local model hash
   against `models/registry.json`; never download at service startup.
2. Start the existing local FastAPI/PostgreSQL stack according to [SETUP](SETUP.md). Create a camera
   slug and a camera-scoped HMAC service account with the backend CLI. Keep the key in a local
   ignored environment file; do not put it in the camera YAML or logs.
3. Serve the approved local recording only on loopback:

   ```bash
   .venv/bin/python -m roadsentinel.replay --video /tmp/Street_traffic.webm \
     --host 127.0.0.1 --port 8091 --fps 10
   ```

   Health endpoint: `http://127.0.0.1:8091/health`; stream: `http://127.0.0.1:8091/stream.mjpg`.
   The relay rejects non-loopback bind addresses and loops the file at a bounded frame rate.
4. Use a camera configuration whose `id` matches the backend camera slug and whose `video` points
   to the loopback URL. Set `source_replay: true`, `enabled: true`, `source_fps: 10`, and document
   the local replay basis in `source_consent` (recording source, license, scope, date and evidence
   URL). The source adapter rejects a replay label on non-loopback network hosts.
5. Start the detector with local API and service-account variables, e.g.:

   ```bash
   RS_API_URL=http://127.0.0.1:8000 \
   RS_INGEST_KEY_ID="$LOCAL_PIPELINE_KEY_ID" \
   RS_INGEST_SECRET="$LOCAL_PIPELINE_SECRET" \
   .venv/bin/python -m roadsentinel.pipeline cameras/local-replay.yaml \
     --model models/yolox_s.onnx --no-wandb --live --loop --imgsz 640
   ```

6. Start the operator UI with `RS_API_ORIGIN=http://127.0.0.1:8000 npm run dev` from `frontend/`,
   sign in with an MFA-enrolled local operator, open **Camere**, and select **Detalii live**. The UI
   refreshes camera summaries every three seconds. The replay label remains visible.
7. Stop the pipeline, relay, API and UI. The camera becomes stale after heartbeat expiry. The local
   replay itself writes no raw recording or detection JSONL by default. Set `RS_SAVE_DETECTIONS=1`
   only when the optional local bbox log is needed; it is sensitive local output and must be handled
   under the source license and local retention policy.

The current measurement and exact observed counts/latencies are in
[YOLO_REAL_INFERENCE_REPORT](YOLO_REAL_INFERENCE_REPORT.md). External sources stay disabled until
documented machine-processing permission and a documented transport are approved.
