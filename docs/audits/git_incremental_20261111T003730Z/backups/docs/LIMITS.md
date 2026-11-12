# Limits (what this system is not, today)

Written to be read by someone deciding whether to trust it. Items marked **measured** have a number from this repository's own tooling; everything else is a statement about what is *not* known.

## Product
* It alerts and prepares evidence; **a human decides**. It issues no fines. "Dispatch patrol / warning sign / enforcement" is a recorded decision label; only *patrol assignment with status* (assigned → en route → on scene → done) has a real workflow. Nothing is connected to signs or to an enforcement system.
* Not implemented: road-condition detection (fog/ice), tram class, automatic licence-plate reading, rules management and zone editing from the UI (zones, rules and thresholds are YAML per camera), camera creation from the UI (`register-camera` CLI), four-eyes approval of camera changes, saved searches/archive export.
* Natural-language search is a **keyword parser** (Romanian/English), not language understanding.
* The VLM check exists in code but is **off** (needs `RS_EXTERNAL_AI=frames` and an API key; frames then leave the server). No UI text claims an AI confirmation.

## Detection accuracy: nothing is validated
* No accuracy figure for any model on real footage exists in this repo. Earlier metrics in `training/RESULTS*.md` compare a student model with a teacher model's pseudo-labels (agreement, not accuracy) on frames from the same scenes.
* `training/eval.py` is the only sanctioned source of numbers; it has been tested with fake predictors, **never run on real weights here**. No false-alarm rate per hour exists.
* Rules are validated only on synthetic tracks. Night, rain, fog, dense traffic: **not evaluated**.
* Speed is **orientativ**: calibrations are unvalidated (`docs/CALIBRATION.md`), lens distortion is not corrected, and the demo thresholds are tuned to produce alerts. Video speed is for triage, never for fines.
* A camera processed at ~0.5 fps (the live Piața Unirii webcam on the dev laptop) can only run rules that work at that rate; the Cameras page lists what it cannot do. Alerts from sparse frames are marked lower confidence.
* `pipeline.py` was changed and wired to the new modules but was **not executed end to end** in this environment (no torch/ultralytics): live behaviour, stall recovery and upload spooling are tested through their parts with fakes only.

## Privacy and compliance (not legal advice)
* **No claim of GDPR / Directive 2016/680 compliance is made.** No DPIA, legal basis or retention schedule has been approved by anyone.
* Redaction is a **heuristic** (head = top third of a person box; plate = lower band of a vehicle box; windshield region for large vehicles). It misses small, distant, night and unusual cases. It can be switched off only with an explicit confirmation, and then the evidence is labelled FĂRĂ REDACTARE.
* Pipeline evidence has a single stored copy: there is no unredacted original to unblur (`has_original=false`).
* Retention deletes evidence files on a schedule you configure and run; it does not delete alerts, hashes or the audit log. The audit log keeps IP, user agent and operator notes for the life of the chain; erasing a person's data from it is not implemented.
* Training/test frames: licences and consent per source must be recorded in a data card (`docs/DATA_CARD_TEMPLATE.md`); the live Iași webcam is **off** until written permission is recorded in its camera file. Public availability is not permission.
* The repository has no LICENSE; `ultralytics` is AGPL-3.0.

## Security
* MFA mandatory (TOTP + recovery codes). Demo exemption exists, is off by default and refused in production.
* One API process: the rate limiter is in memory and SSE polls the database once per second per connected client. **Measured** (local, loopback, one uvicorn worker, PostgreSQL 18.6, dev laptop): ingest request p50 42 ms / p95 56 ms; event-to-screen over SSE p50 567 ms / p95 989 ms with 21 connected viewers, p50 512 / p95 930 ms with 51 (30 events each, 1.37 s apart); API process 113 MB RSS. These describe the poll interval (1 s) and this machine, not a production deployment, not WAN latency and not many events per second.
* Master keys come from the environment (no KMS); DEK rotation does not re-encrypt existing evidence files. The audit chain has no external anchor: someone with owner-level database access can rewrite it consistently.
* Pentest, dependency pinning policy review and a threat-model refresh have not been done. CI, Docker builds, the compose stack and Railway were **not run** for this branch.

## Process
* Bus factor: see docs/IMPLEMENTATION_PROGRESS.md and the audit report; weights, Railway access and prod credentials are held by individuals.
