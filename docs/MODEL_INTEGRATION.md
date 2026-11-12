# Detector model integration

## Runtime choice and licenses

The supported local inference path is Megvii YOLOX-S in ONNX format, ONNX Runtime's CPU
execution provider, and Supervision ByteTrack. Ultralytics and its weights are excluded from
the default runtime because the official terms describe AGPL-3.0 obligations for private R&D;
RoadSentinel remains private and the owner has not authorized publication. The alternate YOLOX
repository is Apache-2.0. Its official release publishes the YOLOX-S ONNX artifact in the
project model zoo. The checkpoint was trained for COCO; retain the source, hash and any applicable
dataset/model notices. This is provenance documentation, not a legal opinion.

No automatic download occurs at application startup. The expected local weight file is
`models/yolox_s.onnx` (git-ignored); its SHA-256 is recorded in `models/registry.json`.

## Current local artifact

| Item | Value |
|---|---|
| Model | Megvii YOLOX-S, COCO, ONNX |
| Source | [Official Megvii release](https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_s.onnx) |
| Local path | `models/yolox_s.onnx` (not committed) |
| SHA-256 | `c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063` |
| Model input/output | `1×3×640×640` BGR, 0–255; output `1×8400×85` |
| Runtime | ONNX Runtime 1.23.2, `CPUExecutionProvider` |
| Tracker | Supervision 0.30.7 `ByteTrack` (`update_with_detections`) |
| Inference target | CPU; no functioning NVIDIA driver was detected |
| Activation/evaluation | Candidate only; no labeled-set metrics and no camera activation |

Supervision 0.30.7 is pinned because 0.31 removed `sv.ByteTrack`. PyTorch and Ultralytics are not
needed for this ONNX inference path. Training and model-kit scripts that import Ultralytics remain
unavailable unless their separate license and dependency path is explicitly approved.

## Install

The dependencies are pinned in root `requirements.txt`. To install into this repository's venv:

```bash
uv pip install --python .venv/bin/python -r requirements.txt
```

For another machine, acquire the ONNX file from the official release URL above, verify that its
SHA-256 matches the registry entry, and place it at `models/yolox_s.onnx`. Do not silently fetch
weights from arbitrary mirrors or use fallback downloads during a camera run.

## Run an authorized local video

```bash
RS_SAVE_DETECTIONS=1 .venv/bin/python -m roadsentinel.pipeline \
  cameras/<local-camera>.yaml --model models/yolox_s.onnx --no-wandb --imgsz 640
```

The pipeline emits annotated video, optional JSONL detection records, per-class track counts,
line-crossing counts, incident candidates, p50/p95/p99 inference latency, process peak RSS and
the model hash. The camera source and its video license/authorization must be recorded before
processing. These values describe that run; they are not accuracy measurements.

For secure ingestion, set `RS_API_URL`, `RS_INGEST_KEY_ID` and `RS_INGEST_SECRET` for a local
RoadSentinel backend service account scoped to the camera. The sender signs the exact multipart
body and uploads redacted keyframes/clips. A model inference alone is not end-to-end acceptance:
verify the event in PostgreSQL and the supported operator client.

## Registry and training status

`models/registry.json` records the stock YOLOX-S checksum and provenance as a `candidate`.
It is not active for any camera. Existing `model_install.py`, `model_activate.py`, rollback and
training evaluation scripts were written for Ultralytics `.pt` files. Do not use those commands
for ONNX until the registry loader, ONNX class-map validation, smoke test and evaluator are
extended. This does not prevent local inference through the explicit ONNX adapter.

No mAP, precision/recall, false-alert/hour or count-accuracy metric should be reported until an
authorized, labeled evaluation split with leakage checks has been run. Incident rules are
candidate generators that require human review; the sample traffic video does not validate rule
accuracy or legal conclusions.
