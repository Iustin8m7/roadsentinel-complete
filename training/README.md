# Training — fine-tuning the detector

Goal: fine-tune YOLO11 (the model `roadsentinel/pipeline.py` uses) on our own traffic-camera footage
so detection holds up at night, in rain, and on Romanian roads.

## Data on disk (gitignored, under `data/`)

| Folder | Content | Source | License |
|---|---|---|---|
| `data/videos/vehicles.mp4` | Highway, 4K | Roboflow Supervision examples | free demo |
| `data/videos/vehicles-2.mp4` | Dense urban, 1080p | Roboflow Supervision examples | free demo |
| `data/romania/bucuresti_tramvaie_iarna.webm` | Bucharest, winter | Wikimedia Commons | see file page |
| `data/romania/cluj_tramvaie_2012.webm` | Cluj-Napoca | Wikimedia Commons | see file page |

Re-download the demo clips with `bash scripts/download_data.sh`.

## Gated datasets (need a human to request access)

These require registration or an access request by a team member; download them into the listed folder.

| Dataset | Use | Request at | Put in |
|---|---|---|---|
| TU-DAT (~210 accident videos, research only) | crashes, anomalies | https://github.com/pavana27/TU-DAT | `data/tu-dat/` |
| TSBOW (198 CCTV videos, all weather, CC BY-NC-ND 4.0) | night, rain, fog | https://huggingface.co/datasets/SKKUAutoLab/TSBOW | `data/tsbow/` |
| AAU RainSnow (RGB + thermal) | rain, snow, night | https://vbn.aau.dk/en/datasets/aau-rainsnow-traffic-surveillance-dataset | `data/aau-rainsnow/` |
| AI City Challenge | crashes, stopped vehicles | https://www.aicitychallenge.org/ | `data/aicity/` |
| BrnoCompSpeed (~200 GB, email authors) | speed validation | https://github.com/JakubSochor/BrnoCompSpeed | `data/brnocompspeed/` |
| UA-DETRAC | labeled boxes, accuracy numbers | https://arxiv.org/abs/1511.04136 | `data/ua-detrac/` |

Start with **TU-DAT** and **TSBOW**: both need an access request, so send those first.
Check each license before using footage outside research/demo.

## Workflow (macOS, Apple Silicon / MPS)

All commands run from the repo root with the project venv (`.venv/bin/python`; ultralytics,
torch with MPS, opencv, wandb). `train.py` picks `mps`, then CUDA, then CPU automatically.

```bash
# 0. Environment
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -c "import torch; print(torch.backends.mps.is_available())"   # expect True

# 1. Sample frames from raw clips (every 2nd frame, 1280 px wide). Pipeline output under
#    data/media/ or named annotated*/event_* is skipped. --start/--end hold a segment out.
.venv/bin/python training/extract_frames.py data/videos/vehicles.mp4 --step 2
.venv/bin/python training/extract_frames.py data/videos/vehicles-2.mp4 --step 2 --end 30
.venv/bin/python training/extract_frames.py data/videos/vehicles-2.mp4 --step 2 --start 30 \
    --out training/frames-test

# 2. Pre-label with a larger teacher so annotators only fix boxes
.venv/bin/python training/prelabel.py --model yolo11m.pt --device mps
.venv/bin/python training/prelabel.py --frames training/frames-test --model yolo11m.pt --device mps

# 3. Review/fix labels (CVAT, Label Studio or Roboflow, YOLO format), then split: the last 20%
#    of each video (in time) goes to val, the held-out frames go to test
.venv/bin/python training/split.py --val 0.2 --test-frames training/frames-test

# 4. Fine-tune on MPS in the background (logs to W&B project RoadSentinel). batch 8 at 960 px
#    swaps heavily on a 16 GB M2; batch 4 fits.
PYTORCH_ENABLE_MPS_FALLBACK=1 nohup .venv/bin/python training/train.py \
    --imgsz 960 --batch 4 --epochs 30 --patience 10 > training/runs/train.log 2>&1 &

# 5. Compare stock vs fine-tuned on the held-out test split
.venv/bin/python training/evaluate.py yolo11s.pt training/runs/detect/<name>/weights/best.pt
```

Weights land in `training/runs/detect/<name>/weights/best.pt` (git-ignored, like frames and
datasets). Use them in the pipeline with
`python -m roadsentinel.pipeline cameras/demo-highway.yaml --model training/runs/detect/<name>/weights/best.pt`.
See `RESULTS.md` for the first run.

## Classes

`dataset.yaml` keeps all 80 COCO names and IDs so the fine-tuned weights are a drop-in replacement
for `yolo11s.pt`; only ids 0, 1, 2, 3, 5, 7 (person, bicycle, car, motorcycle, bus, truck) carry labels,
matching the classes the pipeline filters to.

There is no `80: road_object` class in this run. Pre-labels come from a COCO-trained teacher, which
never predicts debris, tyres or cargo, so the class would have zero positive boxes and the model would
learn that such objects are background. Add it back only once frames containing road objects have
been labeled by hand.
