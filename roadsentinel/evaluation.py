"""Held-out evaluation of detector models (torch-free; the model is an injected `predictor`).

Why our own metric code: the SAME items and the SAME code evaluate the candidate and the base model,
per class, per camera and per condition tag, with sample sizes next to every number. AP is the
COCO-style 101-point interpolation averaged over IoU 0.50:0.05:0.95 (mAP50-95) and at 0.50 (mAP50);
it can differ slightly from Ultralytics' own val numbers, so quote only numbers from here.

Manifest (JSON):
  {"name": "...", "items": [{"image": "rel/path.jpg", "labels": "rel/path.txt", "camera": "iasi-piata-unirii",
                             "captured_at": "2026-10-20T19:06:00", "tags": ["night"]}]}
Paths are relative to the manifest. Labels are YOLO txt (class cx cy w h, normalised) using the COCO ids.
"""
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

from .models import PROJECT_CLASSES, sha256_file

IOU_THRESHOLDS = [round(0.5 + 0.05 * i, 2) for i in range(10)]
MIN_BOXES_FOR_A_CLAIM = 30      # below this a per-class number is flagged "low sample"
OPERATING_CONF = 0.25


class EvalError(Exception):
    pass


# ------------------------------------------------------------------ manifests and leakage
def load_manifest(path):
    path = Path(path)
    data = json.loads(path.read_text())
    items = []
    for it in data["items"]:
        items.append({**it, "image_path": (path.parent / it["image"]).resolve(),
                      "label_path": (path.parent / it["labels"]).resolve() if it.get("labels") else None,
                      "tags": list(it.get("tags", []))})
    return {"name": data.get("name", path.stem), "path": str(path), "sha256": sha256_file(path), "items": items}


def _item_hash(item):
    return sha256_file(item["image_path"])


def check_leakage(test, others, min_gap_s=600):
    """Problems (empty list = clean). Test items must not share bytes with train/val items and must be
    at least `min_gap_s` away in time from any train/val item of the same camera (neighbouring
    frames of one recording are near-duplicates). Items without `captured_at` cannot be verified."""
    problems = []
    seen = {}
    for m in others:
        for it in m["items"]:
            seen[_item_hash(it)] = (m["name"], it["image"])
    times = defaultdict(list)
    for m in others:
        for it in m["items"]:
            if it.get("captured_at"):
                times[it.get("camera")].append((datetime.fromisoformat(it["captured_at"]), m["name"], it["image"]))
    for it in test["items"]:
        h = _item_hash(it)
        if h in seen:
            problems.append(f"{it['image']}: identical image bytes in {seen[h][0]} ({seen[h][1]})")
        if not it.get("captured_at"):
            problems.append(f"{it['image']}: no captured_at, cannot verify the time gap to train/val")
            continue
        t = datetime.fromisoformat(it["captured_at"])
        for t2, name, img in times.get(it.get("camera"), []):
            if abs((t - t2).total_seconds()) < min_gap_s:
                problems.append(f"{it['image']}: only {abs((t - t2).total_seconds()):.0f} s from {name} item {img} "
                                f"(same camera, minimum {min_gap_s} s)")
                break
    return problems


# ------------------------------------------------------------------ metrics
def read_labels(label_path, width, height):
    """-> [(class_name, (x1, y1, x2, y2))] in pixels, project classes only."""
    out = []
    if not label_path or not Path(label_path).exists():
        return out
    for line in Path(label_path).read_text().splitlines():
        parts = line.split()
        if len(parts) < 5 or int(parts[0]) not in PROJECT_CLASSES:
            continue
        cx, cy, w, h = (float(v) for v in parts[1:5])
        out.append((PROJECT_CLASSES[int(parts[0])],
                    ((cx - w / 2) * width, (cy - h / 2) * height, (cx + w / 2) * width, (cy + h / 2) * height)))
    return out


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _match(preds, gts, thr):
    """Greedy by confidence. preds: [(conf, box)], gts: [box]. Returns list of (conf, is_tp)."""
    used, out = set(), []
    for conf, box in sorted(preds, key=lambda p: -p[0]):
        best, best_j = 0.0, -1
        for j, g in enumerate(gts):
            if j in used:
                continue
            v = iou(box, g)
            if v > best:
                best, best_j = v, j
        if best >= thr:
            used.add(best_j)
            out.append((conf, True))
        else:
            out.append((conf, False))
    return out


def average_precision(scored, n_gt):
    """101-point interpolated AP from [(conf, is_tp)] and the number of ground-truth boxes."""
    if n_gt == 0:
        return None
    if not scored:
        return 0.0
    scored = sorted(scored, key=lambda s: -s[0])
    tp = np.cumsum([1 if t else 0 for _, t in scored])
    fp = np.cumsum([0 if t else 1 for _, t in scored])
    recall = tp / n_gt
    precision = tp / np.maximum(tp + fp, 1e-12)
    for i in range(len(precision) - 2, -1, -1):
        precision[i] = max(precision[i], precision[i + 1])
    pts = np.linspace(0, 1, 101)
    idx = np.searchsorted(recall, pts, side="left")
    return float(np.mean([precision[i] if i < len(precision) else 0.0 for i in idx]))


def evaluate(items, predictor, read_size):
    """-> {"overall": block, "per_camera": {...}, "per_tag": {...}} with sample sizes.
    `predictor(image_path) -> [(class_name, conf, box)]`; `read_size(image_path) -> (w, h)`."""
    per_item = []
    for it in items:
        w, h = read_size(it["image_path"])
        gts = read_labels(it["label_path"], w, h)
        preds = [(c, conf, box) for c, conf, box in predictor(it["image_path"]) if c in PROJECT_CLASSES.values()]
        per_item.append((it, gts, preds))

    def block(subset):
        classes = sorted(PROJECT_CLASSES.values())
        scored = {c: {t: [] for t in IOU_THRESHOLDS} for c in classes}
        n_gt = defaultdict(int)
        tp = defaultdict(int)
        fp = defaultdict(int)
        fn = defaultdict(int)
        for _, gts, preds in subset:
            for c in classes:
                g = [b for k, b in gts if k == c]
                p = [(conf, b) for k, conf, b in preds if k == c]
                n_gt[c] += len(g)
                for thr in IOU_THRESHOLDS:
                    scored[c][thr] += _match(p, g, thr)
                op = [x for x in p if x[0] >= OPERATING_CONF]
                m = _match(op, g, 0.5)
                tp[c] += sum(1 for _, t in m if t)
                fp[c] += sum(1 for _, t in m if not t)
                fn[c] += len(g) - sum(1 for _, t in m if t)
        out_classes, ap50s, ap5095s = {}, [], []
        for c in classes:
            if n_gt[c] == 0:
                continue
            ap50 = average_precision(scored[c][0.5], n_gt[c])
            ap5095 = float(np.mean([average_precision(scored[c][t], n_gt[c]) for t in IOU_THRESHOLDS]))
            prec = tp[c] / (tp[c] + fp[c]) if tp[c] + fp[c] else None
            rec = tp[c] / n_gt[c]
            out_classes[c] = {"gt_boxes": n_gt[c], "ap50": round(ap50, 4), "ap50_95": round(ap5095, 4),
                              "precision": None if prec is None else round(prec, 4), "recall": round(rec, 4),
                              "false_positives": fp[c], "missed": fn[c],
                              "low_sample": n_gt[c] < MIN_BOXES_FOR_A_CLAIM}
            ap50s.append(ap50)
            ap5095s.append(ap5095)
        return {"images": len(subset), "gt_boxes": int(sum(n_gt.values())),
                "map50": round(float(np.mean(ap50s)), 4) if ap50s else None,
                "map50_95": round(float(np.mean(ap5095s)), 4) if ap5095s else None,
                "classes": out_classes, "operating_conf": OPERATING_CONF}

    cams, tags = defaultdict(list), defaultdict(list)
    for entry in per_item:
        cams[entry[0].get("camera") or "?"].append(entry)
        for tag in entry[0]["tags"] or ["untagged"]:
            tags[tag].append(entry)
    return {"overall": block(per_item), "per_camera": {k: block(v) for k, v in sorted(cams.items())},
            "per_tag": {k: block(v) for k, v in sorted(tags.items())}}


def compare(candidate, baseline):
    """Per-block deltas (candidate - baseline) on mAP50-95 and mAP50, computed on the same items."""
    def delta(a, b):
        return None if a is None or b is None else round(a - b, 4)

    out = {"overall": {"map50": delta(candidate["overall"]["map50"], baseline["overall"]["map50"]),
                       "map50_95": delta(candidate["overall"]["map50_95"], baseline["overall"]["map50_95"])},
           "per_class": {}, "per_camera": {}, "per_tag": {}}
    for c, v in candidate["overall"]["classes"].items():
        b = baseline["overall"]["classes"].get(c)
        out["per_class"][c] = delta(v["ap50_95"], b["ap50_95"] if b else None)
    for key in ("per_camera", "per_tag"):
        for k, v in candidate[key].items():
            b = baseline[key].get(k)
            out[key][k] = delta(v["map50_95"], b["map50_95"] if b else None)
    return out


# ------------------------------------------------------------------ alerts per hour on a long stream
def count_alerts(frames, tracker, camera_cfg, calib, zones, rules_cls, gate_cls):
    """Run tracker + rules + alert gate over (t, frame) pairs and count the alerts a human would
    have to review. `tracker(frame) -> [(track_id, cls, foot_xy, bbox)]` is injected.
    Returns {"alerts", "by_type", "hours", "alerts_per_hour", "items": [...]}; these are NOT yet
    false alarms: a person must label each item (see review_to_rate)."""
    engine = rules_cls(zones, camera_cfg["thresholds"], camera_cfg.get("rules"))
    gate = gate_cls(camera_cfg.get("alerts"))
    items, last_t, first_t = [], 0.0, None
    for t, frame in frames:
        first_t = t if first_t is None else first_t
        last_t = t
        for e in gate.filter(t, engine.update(t, tracker(frame), calib)):
            items.append({"index": len(items), "t": round(t, 2), "type": e["type"], "rule": e["rule"], "label": ""})
    hours = max((last_t - (first_t or 0.0)) / 3600.0, 1e-9)
    by_type = defaultdict(int)
    for i in items:
        by_type[i["type"]] += 1
    return {"alerts": len(items), "by_type": dict(by_type), "hours": round(hours, 4),
            "alerts_per_hour": round(len(items) / hours, 2), "suppressed_by_gate": gate.stats(), "items": items}


def review_to_rate(result, labels):
    """labels: {index: "true"|"false"} filled in by a human reviewer. Returns false alarms per hour
    and precision over the REVIEWED alerts only (unreviewed ones are reported, not guessed)."""
    reviewed = {i: v for i, v in labels.items() if v in ("true", "false")}
    false = sum(1 for v in reviewed.values() if v == "false")
    return {"reviewed": len(reviewed), "unreviewed": result["alerts"] - len(reviewed),
            "false_alarms": false, "false_alarms_per_hour": round(false / result["hours"], 2),
            "precision": round((len(reviewed) - false) / len(reviewed), 4) if reviewed else None}


def sha256_text(text):
    return hashlib.sha256(text.encode()).hexdigest()


# ------------------------------------------------------------------ report and registry
def build_report(model_entry, candidate, baseline, comparison, test, others, baseline_name, alerts=None, review=None,
                 versions=None):
    return {
        "model_id": model_entry["id"], "model_sha256": model_entry["sha256"], "baseline": baseline_name,
        "evaluated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "test_manifest": {"name": test["name"], "sha256": test["sha256"], "images": len(test["items"])},
        "excluded_from_training_checked_against": [{"name": m["name"], "sha256": m["sha256"]} for m in others],
        "leakage_check": "passed",
        "candidate": candidate, "baseline_result": baseline, "comparison": comparison,
        "stream_alerts": alerts, "review": review, "versions": versions or {},
        "caveats": [
            "Numbers are valid only for the test manifest named above (its cameras, days and conditions).",
            f"Per-class numbers with fewer than {MIN_BOXES_FOR_A_CLAIM} ground-truth boxes are marked low_sample: do not quote them.",
            "alerts_per_hour counts alerts a human must review; false alarms exist only after a human labelled them.",
        ],
    }


def render_markdown(report):
    c, o = report["candidate"]["overall"], report["comparison"]["overall"]
    lines = [f"# Evaluation: {report['model_id']}", "",
             f"* Evaluated: {report['evaluated_at']}  ·  baseline: `{report['baseline']}`",
             (f"* Test set: **{report['test_manifest']['name']}**, {report['test_manifest']['images']} images, "
              f"{c['gt_boxes']} ground-truth boxes (sha256 {report['test_manifest']['sha256'][:12]}…)"),
             f"* Leakage check against train/val: {report['leakage_check']}", "",
             (f"**Overall**: mAP50 {c['map50']}, mAP50-95 {c['map50_95']} "
              f"(Δ vs baseline: mAP50 {o['map50']}, mAP50-95 {o['map50_95']})"), "",
             "| class | GT boxes | AP50 | AP50-95 | precision | recall | Δ AP50-95 vs base | note |", "|---|---|---|---|---|---|---|---|"]
    for k, v in c["classes"].items():
        lines.append(f"| {k} | {v['gt_boxes']} | {v['ap50']} | {v['ap50_95']} | {v['precision']} | {v['recall']} | "
                     f"{report['comparison']['per_class'].get(k)} | {'LOW SAMPLE, do not quote' if v['low_sample'] else ''} |")
    for key, title in (("per_camera", "camera"), ("per_tag", "condition")):
        lines += ["", f"| {title} | images | GT boxes | mAP50 | mAP50-95 | Δ mAP50-95 |", "|---|---|---|---|---|---|"]
        for k, v in report["candidate"][key].items():
            lines.append(f"| {k} | {v['images']} | {v['gt_boxes']} | {v['map50']} | {v['map50_95']} | {report['comparison'][key].get(k)} |")
    if report.get("stream_alerts"):
        s = report["stream_alerts"]
        lines += ["", (f"**Long stream**: {s['alerts']} alerts in {s['hours']} h = {s['alerts_per_hour']} alerts/hour to review "
                       f"(by type {s['by_type']}; suppressed by the gate {s['suppressed_by_gate']})")]
        if report.get("review"):
            r = report["review"]
            lines.append(f"Human review: {r['reviewed']} reviewed, {r['false_alarms']} false = {r['false_alarms_per_hour']} false alarms/hour, "
                         f"precision {r['precision']} ({r['unreviewed']} unreviewed)")
    lines += ["", "## Caveats", *[f"* {x}" for x in report["caveats"]]]
    return "\n".join(lines) + "\n"


def record_in_registry(registry_path, report, report_path):
    """Write the evaluation summary into the model's registry entry. Only this function sets metrics."""
    from .models import find, load_registry, save_registry

    reg = load_registry(registry_path)
    entry = find(reg, report["model_id"])
    if entry is None:
        raise EvalError(f"{report['model_id']} is not registered")
    if entry["sha256"] != report["model_sha256"]:
        raise EvalError("the registered weights changed since the evaluation started")
    o = report["candidate"]["overall"]
    entry["metrics"] = {"source": "training/eval.py", "report": str(report_path), "evaluated_at": report["evaluated_at"],
                        "test_manifest": report["test_manifest"]["name"], "test_images": report["test_manifest"]["images"],
                        "gt_boxes": o["gt_boxes"], "map50": o["map50"], "map50_95": o["map50_95"],
                        "baseline": report["baseline"], "delta_map50_95": report["comparison"]["overall"]["map50_95"]}
    save_registry(reg, registry_path)
    return entry["metrics"]
