# models/

* `registry.json` – git-tracked model metadata (id, SHA-256, source, format, license/provenance notes, status, metrics).
* `*.pt`, `*.onnx` – local weights; **git-ignored**. Verify the hash and license/provenance (see docs/MODEL_INTEGRATION.md).
* `changes.jsonl` – append-only, hash-chained log of installs / activations / rollbacks.
* `manifests/` – train / val / test manifests used by `training/eval.py` (leakage-checked).
* `reports/` – evaluation reports (`<model_id>.json|md`); the only allowed source of any number shown in docs or UI.

Runbook: `docs/MODEL_INTEGRATION.md`. The official YOLOX-S ONNX artifact is registered as a candidate; it is not activated and has no evaluation metrics. The Ultralytics `.pt` installer does not manage this ONNX model.
