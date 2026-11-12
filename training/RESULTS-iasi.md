# Training results: domain adaptation to the live Iași cameras (2026-10-20)

**Verdict: use `models/rs-yolo11s-iasi.pt` (fine-tuned yolo11s, 1280 px) for the live Piața Unirii
pipeline instead of stock `yolo11s.pt`.** On the held-out Iași test recording it agrees with the
yolo11x teacher much more closely than stock does: mAP50-95 0.727 against 0.525, and every class
improves. It also stays roughly level with stock on the old stock clips (0.733 against 0.750). It
has the same architecture and speed as stock and keeps all 80 COCO names, so it drops straight in:
`--model models/rs-yolo11s-iasi.pt`.

Read the caveats below before treating these numbers as accuracy. In particular, **all footage was
recorded after dark**, so daytime performance was not measured.

## Data

Recorded with `ffmpeg -rw_timeout 20000000 -i <url> -map 0:v:0 -c copy -an -t 180` (no re-encode),
one connection per stream. Each stream got four 3-minute segments, started about 15 minutes apart
(19:06, 19:20, 19:35, 19:50 EEST), into `data/iasi_live/` (476 MB, git-ignored).

| Stream | Source | Format | Use |
|---|---|---|---|
| `unirii` Piața Unirii (main target) | `w1.webcamromania.ro/piatauniriiiasi` | 1920x1080, 20 fps | s1+s2 train, s3 val, s4 test |
| `pascani` Gara Pașcani | `w2.webcamromania.ro/isgarapascani` | 1920x1080, 30 fps | s1+s2 train, s3 val, s4 test |
| `palat` Palace of Culture | `digilive.rcs-rds.ro/.../iasi_desktop.stream` | 1280x800, 30 fps | never trained; s4 in test |

Frames were sampled every 1.5 s at 1280 px wide and pseudo-labelled by **yolo11x.pt at 1280 px,
conf 0.35**, keeping the six pipeline classes. For **replay**, frames from the four stock clips
(`data/videos/vehicles*.mp4`, `data/mixkit/*.mp4`) were sampled every 0.5 s. The first 80% of
each clip went to train and the last 20% to val. Older training frames were not on disk, so the
replay set was rebuilt this way.

| Split | Frames | Boxes (person / bicycle / car / bus / truck) |
|---|---|---|
| train (Iași s1+s2: 482, replay: 151) | 633 | 1486 / 262 / 11374 / 684 / 773 |
| val (Iași s3: 241, replay tail: 40) | 281 | 298 / 125 / 4796 / 258 / 227 |
| test (s4 of each stream) | 360 | 218 / 121 / 4499 / 24 / 132 |
| of which unirii s4 | 120 | 210 / 0 / 3232 / 24 / 113 |
| of which pascani s4 | 121 | 8 / 121 / 1266 / 0 / 19 |
| of which palat s4 | 119 | 0 / 0 / 1 / 0 / 0 |

There were no motorcycles. Bus has only 24 test boxes, all at Unirii, and the 121 Pașcani bicycles
are one parked bike seen in every frame.

**The Palace of Culture hold-out did not work.** That camera is almost black at night, and the
teacher found only 7 cars in all 476 Palace frames. A pseudo-label metric for it would be
meaningless, so the unseen-camera generalisation check was not possible. The only signal is
detection counts on those 476 frames at conf 0.35: yolo11x found 7, stock yolo11s 4, fine-tuned
1280 75 and fine-tuned 960 162. In a spot check, the frame with the most fine-tuned detections had
two plausible real cars (one parked, one with lit tail lights). Nobody measured how many of the
extra detections are false positives.

## Commands

```bash
P=.venv/bin/python; export PYTORCH_ENABLE_MPS_FALLBACK=1
# frames (repeat per segment; palat → frames-iasi-unseen, s3 → frames-iasi-val, s4 → frames-iasi-test)
$P training/extract_frames.py data/iasi_live/unirii_s1_*.mp4 --every 1.5 --out training/frames-iasi-train
$P training/extract_frames.py data/videos/vehicles.mp4 --every 0.5 --end 17.2 --out training/frames-iasi-train/replay
$P training/extract_frames.py data/videos/vehicles.mp4 --every 0.5 --start 17.2 --out training/frames-iasi-val/replay
# (vehicles-2 cut at 34 s, busy-city-street at 10.7 s, suspended-bridge at 12.2 s)
$P training/prelabel.py --frames training/frames-iasi-train --model yolo11x.pt --device mps --batch 2
# split: everything under --frames is train; val and test are whole later recordings
$P training/split.py --frames training/frames-iasi-train --val 0 --val-frames training/frames-iasi-val \
    --test-frames training/frames-iasi-test --out training/datasets/iasi
# train (backbone frozen; see "Training" below)
$P training/train.py --data training/dataset-iasi.yaml --imgsz 1280 --batch 2 --epochs 10 --patience 4 \
    --freeze 10 --name rs-yolo11s-iasi-1280
$P training/train.py --data training/dataset-iasi.yaml --imgsz 960 --batch 4 --epochs 10 --patience 4 \
    --freeze 10 --name rs-yolo11s-iasi-960
# evaluate (run from training/); per-camera yamls point `test:` at a list file in datasets/iasi/
$P evaluate.py ../yolo11s.pt runs/detect/rs-yolo11s-iasi-1280/weights/best.pt --data dataset-iasi.yaml --imgsz 1280
$P evaluate.py ... --data datasets/iasi/test-unirii.yaml --imgsz 1280   # also test-pascani, test-replay
```

`test-replay` is the 40 replay val frames: stock daytime clips, never trained on, but used for
early stopping.

## Training

Both runs started from COCO `yolo11s.pt`, used the `train.py` augmentations, and froze layers 0-9
(the backbone) with `--freeze 10`. Ten epochs were run. Since `close_mosaic=10` ≥ epochs, mosaic
was off throughout.

| Run | Time | Best val mAP50 / mAP50-95 |
|---|---|---|
| `rs-yolo11s-iasi-1280` (batch 2) | 68 min, ~6.8 min/epoch | 0.871 / 0.801 (epoch 9) |
| `rs-yolo11s-iasi-960` (batch 4) | 39 min, ~3.9 min/epoch | 0.848 / 0.757 (epoch 10) |

Val was still rising slowly at epoch 10, so a longer run might gain a little.

**Why the backbone was frozen.** A full fine-tune was tried first (1280 px, batch 4). With another
desktop process using about 16 GB, it pushed the 16 GB M2 deep into swap, the trainer stalled, and
the live pipeline's processing rate dropped. It was stopped within minutes. A full-model batch-2 run
then took 36 min for one epoch (log `training/runs/train-iasi-1280-full-aborted.log`, epoch-1 val
mAP50-95 0.738). That would have meant more than 13 h for 25 epochs, so it was stopped too.
Freezing the backbone cut memory to about 3.4 GB and the epoch time to about 7 min. It also limits
forgetting, which is what broke bus in the earlier run. Pausing the trainer for about 4 minutes
left the live pipeline at the same ~0.4-0.5 fps, so its slowdown came from system memory pressure,
not this training.

## Test results (pseudo-labels from yolo11x: agreement with the teacher, not ground truth)

Cells are mAP50 / mAP50-95.

**Full Iași test split (360 frames: s4 of all three streams)**

| imgsz | Model | all | person | bicycle | car | bus | truck |
|---|---|---|---|---|---|---|---|
| 1280 | stock yolo11s | 0.642 / 0.525 | 0.585 / 0.446 | 0.950 / 0.782 | 0.782 / 0.633 | 0.782 / 0.677 | 0.112 / 0.086 |
| 1280 | **ft-1280** | **0.816 / 0.727** | 0.649 / 0.491 | 0.994 / 0.967 | 0.927 / 0.822 | 0.916 / 0.824 | 0.591 / 0.529 |
| 1280 | ft-960 | 0.793 / 0.684 | 0.628 / 0.465 | 0.988 / 0.907 | 0.923 / 0.805 | 0.880 / 0.775 | 0.546 / 0.467 |
| 960 | stock yolo11s | 0.576 / 0.377 | 0.388 / 0.236 | 0.989 / 0.485 | 0.726 / 0.562 | 0.651 / 0.502 | 0.124 / 0.101 |
| 960 | **ft-960** | **0.765 / 0.652** | 0.543 / 0.337 | 0.993 / 0.938 | 0.922 / 0.805 | 0.818 / 0.669 | 0.549 / 0.511 |
| 960 | ft-1280 | 0.763 / 0.646 | 0.493 / 0.307 | 0.994 / 0.887 | 0.922 / 0.808 | 0.837 / 0.693 | 0.570 / 0.535 |

**Per camera and old-domain check (mAP50-95, "all")**

| Test set | stock @1280 | ft-1280 @1280 | ft-960 @1280 | stock @960 | ft-960 @960 |
|---|---|---|---|---|---|
| Unirii s4 (120 frames, main target) | 0.477 | **0.697** | 0.661 | 0.356 | 0.608 |
| Pașcani s4 (121) | 0.403 | **0.545** | 0.488 | 0.349 | 0.578 |
| Stock clips, replay tail (40, daytime) | **0.750** | 0.733 | 0.738 | 0.646 | 0.706 |

On the stock clips the fine-tuned 1280 model loses 0.017 overall. Most of that is bus (0.635 to
0.526), and there are only 8 bus boxes, so this is weak evidence either way. Car (+0.05) and truck
(+0.01) improve.

## Speed (this Mac: M2, 16 GB, MPS)

The benchmark runs `predict` one frame at a time on 60 test JPEGs, after a 5-frame warm-up. Each
timing covers JPEG decode, pre- and post-processing. It ran while the live pipeline was using the
GPU and memory was under pressure, so treat the numbers as relative.

| Model | 1280 px | 960 px |
|---|---|---|
| stock yolo11s | 14.7 fps (68 ms) | 18.6 fps (54 ms) |
| ft-1280 | 15.7 fps (64 ms) | 18.8 fps (53 ms) |
| ft-960 | 13.3 fps (75 ms) | 21.5 fps (47 ms) |

The architecture is identical, so the differences are noise. 960 px is about 1.3x faster than
1280 here.

## Drop-in check

`DATABASE_URL=sqlite:///<tmp>.db python -m roadsentinel.pipeline cameras/demo-highway.yaml --no-wandb
--max-seconds 10 --model training/runs/detect/rs-yolo11s-iasi-1280/weights/best.pt` exited 0. It
gave 250 frames, 565 detections, 6 tracks (5 car, 1 truck) and a median speed of 124.1 km/h. Stock
gave 545 detections, 6 tracks and 124.4 km/h (RESULTS.md). That clip's first 17 s are in the replay
training data, so this checks compatibility only.

## Caveats

1. **These are teacher-agreement scores.** Labels are unreviewed yolo11x pseudo-labels, so they show
   that yolo11s moved closer to yolo11x on these cameras, not that it is more correct. yolo11x
   misses dark vehicles (see Palace) and those misses were learned as background.
2. **Night only.** Every Iași frame was recorded between 19:06 and 19:53 EEST, after dark.
   Daylight on these cameras is untested. The stock-clip check suggests little daytime forgetting
   in general, but it is not the same scene.
3. **The test set is the same scene 30 minutes later.** Parked cars, the parked bike at Pașcani and
   the static layout appear in both train and test, so part of the gain is learning the scene.
   That is acceptable for a fixed live camera, but it overstates performance on a new camera.
4. **There was no unseen-camera measurement** (Palace too dark for the teacher). Small classes
   (bus 24 test boxes, no motorcycles) are not conclusive.

## Recommendation

- **Live Piața Unirii at 1280 px:** switch to `models/rs-yolo11s-iasi.pt` (a copy of
  `training/runs/detect/rs-yolo11s-iasi-1280/weights/best.pt`). It wins on every class at Unirii
  and Pașcani at the same speed. Re-check after a daytime recording.
- **If live mode needs 960 px to run at stride 1:** use `models/rs-yolo11s-iasi-960.pt` at
  `--imgsz 960`. At 960 it scores 0.652 on the test split, above stock yolo11s at 1280 (0.525), and
  it runs about 1.3x faster than 1280.
- **Next:** record a daytime session (same procedure) and add it to train/val. Hand-review the
  Unirii test labels so the metric measures accuracy. If memory allows, try an unfrozen fine-tune.
