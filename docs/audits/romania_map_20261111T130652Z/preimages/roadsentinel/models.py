"""Model registry, installation, activation and rollback (torch-free; weights are loaded only
through an injectable `loader`, so everything here is tested without real weights).

Files (see docs/MODEL_INTEGRATION.md):
    models/registry.json     git-tracked metadata of every model (weights themselves are git-ignored)
    models/<file>.pt         the weights (git-ignored; never deleted by these tools)
    models/changes.jsonl     append-only, hash-chained record of installs / activations / rollbacks
    models/reports/<id>.*    written by training/eval.py ONLY; the only source of metrics
"""
import hashlib
import json
import os
import re
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"
REGISTRY = MODELS_DIR / "registry.json"
CHANGES = MODELS_DIR / "changes.jsonl"
CAMERAS_DIR = ROOT / "cameras"

# The detector must keep these COCO ids/names: the pipeline maps ids to classes with this table.
PROJECT_CLASSES = {0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
STATUSES = ("candidate", "active", "retired")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")


class ModelError(Exception):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def load_registry(path=REGISTRY):
    path = Path(path)
    if not path.exists():
        return {"schema_version": 1, "models": []}
    reg = json.loads(path.read_text())
    if reg.get("schema_version") != 1:
        raise ModelError("unsupported registry schema_version")
    return reg


def save_registry(reg, path=REGISTRY):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(reg, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(tmp, path)


def find(reg, model_id):
    return next((m for m in reg["models"] if m["id"] == model_id), None)


def by_path(reg, path):
    return next((m for m in reg["models"] if m["file"] == str(path)), None)


def check_class_map(names):
    """names: {id: name} as stored in the weights. Every project class id must carry its name."""
    names = {int(k): v for k, v in names.items()}
    return [f"class {i} should be '{n}' but the weights say '{names.get(i)}'"
            for i, n in PROJECT_CLASSES.items() if names.get(i) != n]


def default_loader(path):
    """Loads the weights with ultralytics (heavy import, only here)."""
    from ultralytics import YOLO

    model = YOLO(str(path))
    import ultralytics

    return {"names": dict(model.names), "framework": {"ultralytics": ultralytics.__version__}}


def _append_change(record, changes=CHANGES):
    """Append-only log; each line carries the hash of the previous one (tamper-evident)."""
    changes = Path(changes)
    changes.parent.mkdir(parents=True, exist_ok=True)
    prev = "0" * 64
    if changes.exists() and changes.stat().st_size:
        prev = json.loads(changes.read_text().splitlines()[-1])["hash"]
    body = {**record, "at": _now(), "prev_hash": prev}
    body["hash"] = hashlib.sha256((prev + json.dumps(body, sort_keys=True)).encode()).hexdigest()
    with open(changes, "a") as f:
        f.write(json.dumps(body, sort_keys=True, ensure_ascii=False) + "\n")
    return body


def verify_changes(changes=CHANGES):
    """True if the chain is intact."""
    prev = "0" * 64
    if not Path(changes).exists():
        return True
    for line in Path(changes).read_text().splitlines():
        rec = json.loads(line)
        h = rec.pop("hash")
        if rec["prev_hash"] != prev or hashlib.sha256((prev + json.dumps(rec, sort_keys=True)).encode()).hexdigest() != h:
            return False
        prev = h
    return True


def install(weights, model_id, *, base_model, training_data, trained_on, cameras=("*",), notes="",
            registry=REGISTRY, models_dir=MODELS_DIR, changes=CHANGES, loader=default_loader, operator=None):
    """Validate the weights and add a `candidate` entry. Never overwrites an `active` model."""
    weights = Path(weights)
    if not ID_RE.match(model_id):
        raise ModelError("model id must be lowercase letters, digits, . _ - (3-64 chars)")
    if not weights.is_file():
        raise ModelError(f"weights not found: {weights}")
    reg = load_registry(registry)
    existing = find(reg, model_id)
    if existing and existing["status"] == "active":
        raise ModelError(f"{model_id} is active and cannot be overwritten; install under a new id")
    digest = sha256_file(weights)
    clash = next((m for m in reg["models"] if m["sha256"] == digest and m["id"] != model_id), None)
    if clash:
        raise ModelError(f"these exact weights are already registered as {clash['id']}")
    try:
        info = loader(weights)
    except Exception as err:
        raise ModelError(f"weights do not load: {err}") from err
    problems = check_class_map(info["names"])
    if problems:
        raise ModelError("class map mismatch: " + "; ".join(problems))
    dest = Path(models_dir) / f"{model_id}{weights.suffix}"
    if dest.exists() and sha256_file(dest) != digest:
        raise ModelError(f"{dest} exists with different content; refusing to overwrite weights")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if weights.resolve() != dest.resolve():
        shutil.copy2(weights, dest)
    rel = os.path.relpath(dest, ROOT) if str(dest).startswith(str(ROOT)) else str(dest)
    entry = {
        "id": model_id, "file": rel, "sha256": digest, "status": "candidate", "base_model": base_model,
        "training_data": training_data, "trained_on": trained_on, "installed_at": _now(),
        "framework": info.get("framework", {}), "classes": sorted(PROJECT_CLASSES.values()),
        "cameras": list(cameras), "active_cameras": [],
        "metrics": None,   # filled by training/eval.py only; never by hand
        "notes": notes,
    }
    reg["models"] = [m for m in reg["models"] if m["id"] != model_id] + [entry]
    save_registry(reg, registry)
    _append_change({"action": "install", "model_id": model_id, "sha256": digest, "operator": operator or os.environ.get("USER", "?")}, changes)
    return entry


# ---------------------------------------------------------------- camera yaml
def _read_cam(camera_yaml):
    return Path(camera_yaml).read_text()


def current_model(camera_yaml):
    """(model path, model_id) currently configured in a camera yaml; (None, None) if absent."""
    text = _read_cam(camera_yaml)
    m = re.search(r"^model:\s*(\S+)", text, re.MULTILINE)
    i = re.search(r"^model_id:\s*(\S+)", text, re.MULTILINE)
    return (m.group(1) if m else None, i.group(1) if i else None)


def _set_yaml_model(camera_yaml, file, model_id):
    p = Path(camera_yaml)
    text = p.read_text()
    text = re.sub(r"^model_id:.*\n", "", text, flags=re.MULTILINE)
    if re.search(r"^model:", text, re.MULTILINE):
        text = re.sub(r"^model:.*$", f"model: {file}\nmodel_id: {model_id}", text, count=1, flags=re.MULTILINE)
    else:
        anchor = re.search(r"^(calibration:|zones:|rules:)", text, re.MULTILINE)
        pos = anchor.start() if anchor else len(text)
        text = text[:pos] + f"model: {file}\nmodel_id: {model_id}\n" + text[pos:]
    p.write_text(text)


def camera_id_of(camera_yaml):
    m = re.search(r"^id:\s*(\S+)", _read_cam(camera_yaml), re.MULTILINE)
    if not m:
        raise ModelError(f"{camera_yaml} has no id")
    return m.group(1)


def smoke_test(weights, frames, predictor=None):
    """Run the model on a few frames: it must load and produce no exception; returns the classes seen.
    `predictor(weights, frame_path) -> [class names]` is injectable for tests."""
    predictor = predictor or _default_predictor
    seen = set()
    for f in frames:
        seen.update(predictor(weights, f))
    return sorted(seen)


def _default_predictor(weights, frame):
    from ultralytics import YOLO

    model = YOLO(str(weights))
    res = model.predict(str(frame), verbose=False, conf=0.25, classes=list(PROJECT_CLASSES))[0]
    return [model.names[int(c)] for c in res.boxes.cls.tolist()]


def activate(model_id, camera_yaml, *, registry=REGISTRY, changes=CHANGES, frames=(), expect_classes=(),
             require_eval=True, predictor=None, operator=None, _action="activate"):
    reg = load_registry(registry)
    entry = find(reg, model_id)
    if entry is None:
        raise ModelError(f"unknown model {model_id}")
    cam = camera_id_of(camera_yaml)
    if entry["cameras"] != ["*"] and cam not in entry["cameras"]:
        raise ModelError(f"{model_id} is not registered for camera {cam} (applies to: {entry['cameras']})")
    weights = ROOT / entry["file"] if not Path(entry["file"]).is_absolute() else Path(entry["file"])
    if not weights.is_file():
        raise ModelError(f"weights file missing: {weights}")
    if sha256_file(weights) != entry["sha256"]:
        raise ModelError("weights file does not match the registered sha256 (modified or corrupted)")
    if require_eval and not entry.get("metrics"):
        raise ModelError(f"{model_id} has no evaluation (run training/eval.py); --allow-unevaluated overrides")
    if frames:
        seen = smoke_test(weights, frames, predictor)
        missing = [c for c in expect_classes if c not in seen]
        if missing:
            raise ModelError(f"smoke test: expected classes not detected: {missing} (saw {seen})")
    prev_file, prev_id = current_model(camera_yaml)
    _set_yaml_model(camera_yaml, entry["file"], model_id)
    for m in reg["models"]:
        if m["id"] == prev_id and cam in m["active_cameras"] and m["id"] != model_id:
            m["active_cameras"].remove(cam)
            if not m["active_cameras"]:
                m["status"] = "retired"
    if cam not in entry["active_cameras"]:
        entry["active_cameras"].append(cam)
    entry["status"] = "active"
    save_registry(reg, registry)
    _append_change({"action": _action, "model_id": model_id, "camera": cam, "previous": prev_id or prev_file,
                    "unevaluated": not entry.get("metrics"), "smoke_frames": len(list(frames)),
                    "operator": operator or os.environ.get("USER", "?")}, changes)
    return {"camera": cam, "model": model_id, "previous": prev_id or prev_file}


def rollback(camera_yaml, *, registry=REGISTRY, changes=CHANGES, operator=None):
    """Instantly return a camera to the model it used before the last activation. Weights are kept."""
    cam = camera_id_of(camera_yaml)
    last = None
    if Path(changes).exists():
        for line in Path(changes).read_text().splitlines():
            rec = json.loads(line)
            if rec["action"] in ("activate", "rollback") and rec.get("camera") == cam:
                last = rec
    if last is None or not last.get("previous"):
        raise ModelError(f"no previous model recorded for camera {cam}")
    reg = load_registry(registry)
    target = find(reg, last["previous"])
    if target is None:   # the previous model was a bare weights path (before the registry existed)
        cur_file, cur_id = current_model(camera_yaml)
        _set_yaml_model(camera_yaml, last["previous"], "unregistered")
        _append_change({"action": "rollback", "model_id": "unregistered", "camera": cam, "previous": cur_id or cur_file,
                        "operator": operator or os.environ.get("USER", "?")}, changes)
        return {"camera": cam, "model": last["previous"], "previous": cur_id or cur_file}
    return activate(target["id"], camera_yaml, registry=registry, changes=changes, require_eval=False,
                    operator=operator, _action="rollback")


def resolve_for_pipeline(cfg, override=None, env=None):
    """Which weights a camera run uses: (path, model_id, sha256). `--model` wins; else the camera's
    own model. A configured model that is missing is an ERROR (it used to fall back silently to the
    stock weights, which the camera's thresholds were not tuned for); set RS_ALLOW_MODEL_FALLBACK=1
    to accept the stock fallback explicitly."""
    env = os.environ if env is None else env
    if override:
        if Path(override).suffix.lower() != ".onnx":
            raise ModelError("the supported inference runtime accepts ONNX weights; Ultralytics .pt is not enabled")
        reg = load_registry()
        selected = Path(override).resolve()
        entry = next(
            (model for model in reg["models"] if Path(model["file"]).resolve() == selected), None
        )
        return override, entry["id"] if entry else "override", sha256_file(override) if Path(override).is_file() else None
    # Explicit deployment location for the registered stock artifact, never a model fallback.
    configured = env.get('RS_YOLOX_MODEL_PATH')
    if cfg.get('model') == 'models/yolox_s.onnx' and configured:
        root = Path(__file__).resolve().parents[1]
        registry = load_registry(root / 'models/registry.json')
        expected = next(m for m in registry['models'] if m['id'] == 'stock-yolox-s')['sha256']
        if not Path(configured).is_file() or sha256_file(configured) != expected:
            raise ModelError('Configured stock YOLOX model is missing or its checksum differs')
        return configured, 'stock-yolox-s', expected
    own = cfg.get("model")
    if own and Path(own).exists():
        if Path(own).suffix.lower() != ".onnx":
            raise ModelError(f"model {own} is not ONNX; the current inference runtime uses the permissive YOLOX ONNX path")
        reg = load_registry()
        entry = by_path(reg, own)
        return own, (entry["id"] if entry else cfg.get("model_id", "unregistered")), sha256_file(own)
    if own and env.get("RS_ALLOW_MODEL_FALLBACK") != "1":
        raise ModelError(f"model {own} for camera {cfg.get('id')} is missing on this machine; "
                         "install it (docs/MODEL_INTEGRATION.md) or explicitly select models/yolox_s.onnx")
    stock = "models/yolox_s.onnx"
    digest = sha256_file(stock) if Path(stock).is_file() else None
    return stock, "stock-yolox-s", digest
