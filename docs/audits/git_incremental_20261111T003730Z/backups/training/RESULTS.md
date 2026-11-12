# Training results: first fine-tune (rs-yolo11s-960px-e30-mps-b4)

> Newer: domain adaptation to the live Iași cameras, see [RESULTS-iasi.md](RESULTS-iasi.md).

## What was trained

Distillation-style self-training. A larger COCO model (`yolo11m.pt`, the teacher) pre-labelled
sampled frames at 1280 px, conf 0.35, keeping only the six pipeline classes (person, bicycle, car,
motorcycle, bus, truck). The student, `yolo11s.pt`, was fine-tuned on those pseudo-labels. Nobody
reviewed the labels by hand.

**This matters for how to read the numbers.** The test labels are teacher labels as well. The
metrics below measure how closely each `yolo11s` matches `yolo11m` on unseen frames. They do
not measure accuracy against ground truth. A score of 1.0 would mean "behaves exactly like
yolo11m". It would not mean "detects every vehicle".

## Data split

Frames were sampled every 2nd frame and resized to 1280 px wide (`extract_frames.py`).

| Split | Source | Frames | Boxes (person / car / bus / truck) |
|---|---|---|---|
| train | first 80% (in time) of `vehicles.mp4` (215) and of `vehicles-2.mp4` 0-30 s (360) | 575 | 38 / 9559 / 418 / 1419 |
| val | last 20% (in time) of each of the same segments (54 + 90) | 144 | 29 / 2366 / 2 / 368 |
| test | `vehicles-2.mp4` 30.0-42.5 s (frames 899-1273), extracted separately, never trained on | 188 | 13 / 4785 / 55 / 783 |

Train and val are split in time rather than at random, because a random split would put
near-identical neighbouring frames into val. The test segment is held out from the same urban clip,
so it is close to the training distribution: same camera, same scene, a different 12 seconds.
Bicycle and motorcycle never appear in any split.

## Config

```
model yolo11s.pt (COCO pretrained), 80 COCO names kept so the weights are a drop-in replacement
imgsz 960, batch 4, epochs 30, patience 10, optimizer auto (AdamW lr 0.000119), amp off (MPS)
hsv_s 0.6, hsv_v 0.5, fliplr 0.5, mosaic 1.0, close_mosaic 10, workers 2
device mps (Apple M2, 16 GB), PYTORCH_ENABLE_MPS_FALLBACK=1, ultralytics 8.4
```

Early stopping ended the run after epoch 14 (0.81 h). The best epoch was 4, with val mAP50-95
0.544 (epoch 1: 0.512). Val mAP plateaued at about 0.52-0.53 after epoch 4.

- W&B run: https://forge.coreweave.com/wandb/cristiangavrilean-universitatea-alexandru-ioan-cuza-din-ia-i/RoadSentinel/runs/zdwwgbo2
- Weights (git-ignored, local only):
  `training/runs/detect/rs-yolo11s-960px-e30-mps-b4/weights/best.pt`. On the machine that trained it:
  `/Users/cristi/token-training/training/runs/detect/rs-yolo11s-960px-e30-mps-b4/weights/best.pt`.

## Test-split metrics (agreement with the yolo11m teacher)

`python training/evaluate.py yolo11s.pt training/runs/detect/rs-yolo11s-960px-e30-mps-b4/weights/best.pt --imgsz <N>`

| imgsz | model | all mAP50 | all mAP50-95 | person (13) | car (4785) | bus (55) | truck (783) |
|---|---|---|---|---|---|---|---|
| 960 | stock yolo11s | 0.581 | 0.500 | 0.349 / 0.256 | 0.912 / 0.786 | 0.135 / 0.116 | 0.930 / 0.841 |
| 960 | fine-tuned | **0.696** | **0.613** | 0.712 / 0.549 | 0.952 / 0.882 | 0.156 / 0.129 | 0.962 / 0.893 |
| 1280 | stock yolo11s | **0.800** | **0.718** | 0.899 / 0.754 | 0.942 / 0.864 | 0.411 / 0.368 | 0.949 / 0.887 |
| 1280 | fine-tuned | 0.727 | 0.653 | 0.887 / 0.706 | 0.953 / 0.897 | 0.105 / 0.097 | 0.965 / 0.914 |

Per-class cells are mAP50 / mAP50-95. Instance counts are in parentheses.

How to read it:

- At 1280 px, the size the pipeline runs at, the fine-tuned model is better on car (+0.033
  mAP50-95) and truck (+0.027). Those two classes are 99% of the boxes.
- The overall mean drops at 1280 because of **bus**. The fine-tuned model scores 0.097 there, against
  0.368 for stock. Training had 418 bus boxes but val had only 2, so early stopping effectively
  ignored bus, and bus recall on test fell from 0.088 (stock) to 0.036.
- Person (13 test boxes) and bus (55) are too small to support firm conclusions.
- At 960 px the fine-tuned model wins on every class, which is expected because it was trained at 960.

## Drop-in check

`DATABASE_URL=sqlite:////tmp/rs-train-eval.db python -m roadsentinel.pipeline cameras/demo-highway.yaml --no-wandb --max-seconds 10 --model <best.pt>`
ran from the repo root (no `RS_API_URL`) and exited 0. Over 250 frames it produced 543 detections, 6 tracks
(5 car, 1 truck) and a median speed of 124.7 km/h. Stock `yolo11s.pt` on the same 10 s gave 545
detections, 6 tracks (5 car, 1 truck) and 124.4 km/h. `demo-highway` plays `vehicles.mp4`, which is
part of the training data, so this checks compatibility, not quality.

## Incident: batch 8 thrashed

The first attempt (`batch 8`, 960 px; log `training/runs/train-b8-thrash.log`, local run dir
`rs-yolo11s-960px-e30-mps`) used about 10.7 GB of MPS memory on a 16 GB M2. macOS started swapping, and
the first batches took up to 77 s each, so after almost 5 min only 5 of the 72 batches in epoch 1 were done
(the progress bar projected about 1.5 h per epoch). The run was stopped in epoch 1 and restarted at batch 4,
which fit in memory and took about 3.5-5 min per epoch (train plus val).

## Verdict

Do **not** replace `yolo11s.pt` in the pipeline yet. At the pipeline's 1280 px, the fine-tune agrees
more closely with the teacher on cars and trucks but loses buses badly, and the overall test mAP50-95
falls from 0.718 to 0.653. All of these labels also come from the teacher, so even the car/truck gain
only shows that yolo11s moved closer to yolo11m, not that it is more correct. For a real replacement:

1. hand-review at least the val and test labels, so the metric measures accuracy against ground truth;
2. make sure val holds enough buses (and people) for early stopping to see them;
3. train and evaluate at 1280 px, the inference size, with longer patience;
4. if teacher agreement is the goal, running `yolo11m.pt` directly at 1280 is the simpler option
   wherever the throughput is acceptable.

The weights are still useful as a 960 px model. At that size they beat stock yolo11s on every class,
which matters if the pipeline is ever run at `--imgsz 960` for speed.
