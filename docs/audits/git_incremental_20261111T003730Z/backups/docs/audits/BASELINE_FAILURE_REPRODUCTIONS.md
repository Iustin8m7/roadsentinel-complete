# Baseline reproductions

1. Read `backend/app/api/offline_analytics.py:388`: candidates are returned as offline_recording/pending_review; route search shows no promotion action. Missing capability, not an HTTP failure claim.
2. `rg "config/ack|/config" roadsentinel/pipeline.py`: no control-plane handshake. Config API exists in backend/app/api/camera_worker.py.
3. Current proxy: curl direct 8003 and proxied 5175 /api/health/live returned alive. Historical wrong proxy is not reproduced.
4. Prior owner-role failure is documented in the preceding authentication repair; this mission has not independently reproduced its database query yet. No blind seeding performed.
5. Model registry references models/yolox_s.onnx, which is absent in integration. No silent download performed.
