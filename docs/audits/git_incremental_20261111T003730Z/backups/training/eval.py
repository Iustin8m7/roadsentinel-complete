"""Evaluate a registered model on a held-out test manifest, compared with the base model.

    python training/eval.py --model rs-yolo11s-iasi-v2 \
        --test models/manifests/test.json --train models/manifests/train.json --val models/manifests/val.json \
        [--baseline yolo11s.pt] [--stream recording.mp4 --camera cameras/iasi-piata-unirii.yaml [--review review.csv]]

* Refuses to run if a test item also appears in train/val (identical bytes, or same camera within --min-gap-s).
* Same items, same code for the candidate and the baseline; per class, per camera, per condition tag,
  with sample sizes. Writes models/reports/<model_id>.json and .md and fills the registry metrics.
* --stream: runs tracking + rules + alert gate over a long unlabeled recording and counts the alerts a
  human must review (written to models/reports/<id>-alerts.csv with an empty `label` column). Fill the
  column with true/false and re-run with --review to get false alarms per hour.
No number may be written into docs or the UI unless it came from this script.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from roadsentinel import evaluation as ev
from roadsentinel import models


def ultralytics_predictor(weights, conf=0.001, imgsz=960, device=None):
    from ultralytics import YOLO

    model = YOLO(str(weights))

    def predict(path):
        res = model.predict(str(path), conf=conf, iou=0.6, imgsz=imgsz, device=device, verbose=False)[0]
        return [(model.names[int(c)], float(s), tuple(float(v) for v in b))
                for b, s, c in zip(res.boxes.xyxy.tolist(), res.boxes.conf.tolist(), res.boxes.cls.tolist())]

    return predict


def image_size(path):
    import cv2

    h, w = cv2.imread(str(path)).shape[:2]
    return w, h


def stream_frames(video, stride=1):
    import cv2

    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            return
        if i % stride == 0:
            yield i / fps, frame
        i += 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, help="registered model id")
    ap.add_argument("--test", required=True)
    ap.add_argument("--train", nargs="*", default=[])
    ap.add_argument("--val", nargs="*", default=[])
    ap.add_argument("--baseline", help="base weights (default: the model's base_model)")
    ap.add_argument("--min-gap-s", type=int, default=600)
    ap.add_argument("--imgsz", type=int, default=960)
    ap.add_argument("--device")
    ap.add_argument("--stream")
    ap.add_argument("--camera")
    ap.add_argument("--stride", type=int, default=1, help="process every Nth frame of --stream")
    ap.add_argument("--review", help="CSV from a previous --stream run with the `label` column filled (true/false)")
    ap.add_argument("--registry", default=str(models.REGISTRY))
    ap.add_argument("--reports", default=str(models.MODELS_DIR / "reports"))
    a = ap.parse_args(argv)

    reg = models.load_registry(a.registry)
    entry = models.find(reg, a.model)
    if entry is None:
        print(f"unknown model {a.model}", file=sys.stderr)
        return 2
    weights = ROOT / entry["file"]
    if models.sha256_file(weights) != entry["sha256"]:
        print("weights do not match the registered sha256", file=sys.stderr)
        return 2

    test = ev.load_manifest(a.test)
    others = [ev.load_manifest(p) for p in [*a.train, *a.val]]
    if not others:
        print("REFUSED: pass --train and/or --val manifests so leakage can be checked", file=sys.stderr)
        return 2
    problems = ev.check_leakage(test, others, a.min_gap_s)
    if problems:
        print("REFUSED: the test set overlaps training/validation data:", file=sys.stderr)
        for p in problems[:20]:
            print("  -", p, file=sys.stderr)
        print(f"  ({len(problems)} problem(s))", file=sys.stderr)
        return 3

    baseline_name = a.baseline or entry["base_model"]
    cand = ev.evaluate(test["items"], ultralytics_predictor(weights, imgsz=a.imgsz, device=a.device), image_size)
    base = ev.evaluate(test["items"], ultralytics_predictor(baseline_name, imgsz=a.imgsz, device=a.device), image_size)
    comparison = ev.compare(cand, base)

    alerts = review = None
    out_dir = Path(a.reports)
    out_dir.mkdir(parents=True, exist_ok=True)
    if a.stream:
        if not a.camera:
            print("--stream needs --camera", file=sys.stderr)
            return 2
        from ultralytics import YOLO

        from roadsentinel.alerts import AlertGate
        from roadsentinel.pipeline import COCO, drop_occupants, load_camera
        from roadsentinel.rules import RuleEngine

        cfg, calib, zones = load_camera(a.camera)
        model = YOLO(str(weights))

        def tracker(frame):
            res = model.track(frame, persist=True, tracker="bytetrack.yaml", classes=list(COCO), imgsz=a.imgsz, verbose=False, conf=0.3)[0]
            if res.boxes.id is None:
                return []
            objs = [(tid, COCO[c], ((b[0] + b[2]) / 2, b[3]), tuple(b))
                    for b, tid, c in zip(res.boxes.xyxy.tolist(), res.boxes.id.int().tolist(), res.boxes.cls.int().tolist())]
            return drop_occupants(objs)

        alerts = ev.count_alerts(stream_frames(a.stream, a.stride), tracker, cfg, calib, zones, RuleEngine, AlertGate)
        csv_path = out_dir / f"{a.model}-alerts.csv"
        if a.review:
            with open(a.review, newline="") as fh:
                labels = {int(r["index"]): r["label"].strip().lower() for r in csv.DictReader(fh)}
            review = ev.review_to_rate(alerts, labels)
        with open(csv_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["index", "t", "type", "rule", "label"])
            w.writeheader()
            w.writerows(alerts.pop("items"))
        print(f"alerts to review: {csv_path}")

    import platform
    versions = {"python": platform.python_version(), **entry.get("framework", {})}
    report = ev.build_report(entry, cand, base, comparison, test, others, baseline_name, alerts, review, versions)
    jp, mp = out_dir / f"{a.model}.json", out_dir / f"{a.model}.md"
    jp.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    mp.write_text(ev.render_markdown(report))
    ev.record_in_registry(a.registry, report, jp.relative_to(ROOT) if jp.is_relative_to(ROOT) else jp)
    print(mp.read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
