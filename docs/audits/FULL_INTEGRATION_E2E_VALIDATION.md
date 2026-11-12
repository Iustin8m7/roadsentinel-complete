> Current browser verification (2026-11-10T23:48:23.554678+00:00): see [FINAL_BROWSER_HANDOFF.md](FINAL_BROWSER_HANDOFF.md), [fresh ledger](TEST_EXECUTION_LEDGER_UPDATED.md) and the two REAL_BROWSER_E2E reports. Earlier counts, zero-camera-event/API-only/CLI-only claims below are historical checkpoints, not the current verdict.

# Full integration E2E validation — observed scope

Existing login: **PASS on A**. Feature 1 selected fixture journey: **PASS on B; broader feature PARTIAL**. Feature 2 selected controlled camera journey: **PASS on B; broader feature PARTIAL**. No external-live/accuracy/production acceptance claim.

## Inputs and runtime

- Model: Megvii YOLOX-S COCO ONNX; SHA-256 `c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063`; CPUExecutionProvider; actual ONNX Runtime detections and Supervision ByteTrack, no detector mock.
- Model location: original `models/yolox_s.onnx`, read only through explicitly configured `RS_YOLOX_MODEL_PATH`; stock checksum is enforced. No model download, copy, move or unknown-model fallback.
- Media: Editor's Wikimedia Commons Street traffic.webm, CC BY 3.0; local `/tmp/Street_traffic.webm`; SHA-256 `e5facb24baf755f0c1193999d823e99f6032661ad2bdef5cc28cc1cbbfde03e2`.
- B1 full suite: rsmission_final_regression, 127.0.0.1:55481, rslogin_testroot. B2 independent repeat: [database identity](runtime_verification/runs/20261110T130556Z-dbe51341/database.json). Each starts at base and migrates to 0022 with role/RLS prerequisites. Neither is the existing integration DB.

## Feature 1 — actual HTTP + Chromium + encrypted persistence

`backend/tests/test_mission_vertical.py::test_real_inference_recorded_candidate_to_encrypted_review` constructs a 36-second frozen derivative of a licensed frame, explicitly **SYNTHETIC TEST**. Actual model/tracker processes 60 samples; the focused run observed 8 candidates (an earlier run observed 9). The cause of the difference between retained8/9-candidate runs was not isolated. The test asserts actual nonempty inference/candidates; exact candidate-count reproducibility remains a limitation, not an accuracy figure. This is artificial stationary dwell, not a real obstruction incident.

Observed sequence:

1. Actual password/TOTP HTTP authentication; POST `/api/recordings` 201; crop confirmation 200; POST analysis 202; polling completed with real nonempty model tracks.
2. GET owned candidates; explicit POST candidate promotion 200; duplicate request returns the same alert. Recorded origin, run/track/model/media-position details persist. No automatic live alert or dispatch.
3. Authenticated redacted keyframe and bounded MP4 retrieval; encrypted storage metadata and RSE1 payload asserted. Chromium plays the protected MP4 with nonzero dimensions and duration.
4. Chromium password/TOTP login → `/app/analiza-video` → candidate duplicate submission → canonical alert → actual Respinge dialog/confirmation → case observation added through the real UI. Subsequent HTTP decision receives 409, proving UI performed the persisted transition.
5. Real HTTP case note, admin-recorded explicit fixture license grant, export request with not-ready 409, self-approval rejection, independent administrator approval, package generation and protected download. `verify_package` independently checks manifest SHA-256 and member hashes, with at least two files checked.
6. Other tenant receives 404; patrol/auditor receive 403 on promotion; other-tenant media denied. Complete backend suites cover ingest HMAC/replay/idempotency, approvals/evidence and tenant rules as separate negative tests.

[Executed focused log](runtime_verification/full-feature-journeys.log), [fresh repeat](runtime_verification/runs/20261110T130556Z-dbe51341/flows.log), [real browser screenshot](screenshots/recorded-review.png). Test-owned recording, ciphertext and export were not copied into the existing user's database.

Limits: initial upload/analysis/first promotion and final approval/export used HTTP rather than every step in Chromium. No abrupt service crash during an evidence write, complete archive UI retrieval after restart, original-media retention soak, or real incident precision/recall was proved. Manifest integrity is not a cryptographic signature or external custody anchor. The standalone case-export authorization/tamper/unit suites passed, but do not substitute for every browser scenario.

## Feature 2 — actual registration → approval → worker → preview → recovery

`test_managed_live_runtime.py::test_managed_replay_ack_preview_and_revocation` now creates camera state through actual authenticated operations rather than injected preapproved rows:

1. Tenant administrator logs in with real MFA in Chromium, adds LOCAL RECORDED REPLAY via `/app/camere`, receives camera POST201 and opens its control panel.
2. Authenticated camera-control APIs record source `recorded_replay`, local replay reference and explicit CC BY processing grant. Author creates/validates/submits a config; self approval is 403; a distinct tenant admin approves; activation succeeds.
3. Actual `roadsentinel.pipeline` subprocess obtains HMAC lease before source open, validates model hash/frame dimensions, applies approved config and ACKs revision 1. Signed heartbeats and authenticated preview show actual detections/track IDs and changing decoded JPEG content/timestamps.
4. A competing actual worker exits without opening the controlled source; lease ownership is not duplicated.
5. Operator Chromium login opens live detail; decoded preview updates; LOCAL RECORDED REPLAY provenance is asserted. [Registration screenshot](runtime_verification/screenshots/camera-register.png), [preview screenshot](runtime_verification/screenshots/camera-preview.png).
6. Independent config approval and activation of revision 2 causes old worker to exit cleanly. Fresh worker acquires a new lease and ACKs revision 2; subsequent telemetry is stamped accordingly.
7. Only test server sockets are interrupted. Authoritative state becomes reconnecting; stale preview returns404. Restored source yields real frames and healthy state. No hidden sample fallback is used.
8. Actual disable API stops processing. Self re-enable is403; independent reviewer re-enables; new lease/ACK/real frames succeed. Final pause stops worker cleanly. Best-effort stopped heartbeat now releases the lease immediately on orderly worker exit; expiry remains the failure fallback.

The captured worker measured CPU inference p50 approximately83–92ms, p95 approximately95–117ms and peak RSS approximately344–345MB in one short run. These are observed test measurements, not throughput/accuracy/service guarantees. Source dimensions1920×1080; actual processing roughly1–2.35fps in this resource-limited run, despite10fps source delivery. Calibration-dependent rules remain gated. Moving replay produced **zero eligible incident events**; this is reported honestly. Model-derived positive rule/evidence is demonstrated separately by Feature1's explicit synthetic recorded fixture. Live-camera event-to-case/export as a single positive managed run is still unverified.

Configuration edits/approval were through real MFA-authenticated APIs; registration and preview were through Chromium. The entire configuration editor/approval flow in two browser windows is not yet automated. No externally authorized camera, physical UVC camera, two-camera capacity run, long soak, or live incident ground truth was exercised. External camera processing remains blocked by documentary rights, not silently replaced by a live claim.

## Reproduce safely

```bash
cd /home/justin7m8/Documents/roadsentinel-integration
.venv.integration/bin/python scripts/verify-integration.py flows
```

This creates a unique loopback PostgreSQL cluster and database, verifies guarded fixture identity, runs auth/seed plus both actual-model/browser journeys, records UTC start/end/exit/duration and exact commands, and stops only that owned cluster. No existing service/DB is reset. Model and licensed fixture must already be present; no external fetch is attempted. The executed independent run passed **44 tests**, no skips, and shut down its own test cluster: [commands](runtime_verification/runs/20261110T130556Z-dbe51341/commands.json).
