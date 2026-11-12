"""Model registry kit with a fake loader: no real weights, torch or ultralytics involved."""
import json

import pytest

from roadsentinel import models
from roadsentinel.models import ModelError

GOOD_NAMES = {0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane", 5: "bus", 7: "truck"}


def loader_for(names):
    return lambda path: {"names": names, "framework": {"ultralytics": "0.0-test"}}


@pytest.fixture
def env(tmp_path):
    cam = tmp_path / "cam.yaml"
    cam.write_text("id: cam-a\nname: A\nvideo: x.m3u8\nmodel: models/old.pt\nmodel_id: old-model\n"
                   "calibration:\n  source: []\nrules: [very_high_speed]\n")
    (tmp_path / "w1.pt").write_bytes(b"weights-one")
    (tmp_path / "w2.pt").write_bytes(b"weights-two")
    return {"tmp": tmp_path, "cam": cam, "registry": tmp_path / "reg.json", "models_dir": tmp_path / "m",
            "changes": tmp_path / "changes.jsonl"}


def kw(env, **extra):
    return dict(base_model="yolo11s.pt", training_data="test data", trained_on="2026-11-02",
                registry=env["registry"], models_dir=env["models_dir"], changes=env["changes"],
                loader=loader_for(GOOD_NAMES), **extra)


def install(env, name="w1.pt", model_id="rs-a-v1", **extra):
    return models.install(env["tmp"] / name, model_id, **kw(env, **extra))


def test_install_registers_a_candidate_copy_with_hash_and_no_metrics(env):
    e = install(env)
    assert e["status"] == "candidate" and e["metrics"] is None and len(e["sha256"]) == 64
    assert (env["models_dir"] / "rs-a-v1.pt").read_bytes() == b"weights-one"
    reg = models.load_registry(env["registry"])
    assert models.find(reg, "rs-a-v1")["sha256"] == e["sha256"]
    assert models.verify_changes(env["changes"])


def test_install_refuses_a_wrong_class_map_bad_id_and_duplicate_weights(env):
    bad = {**GOOD_NAMES, 2: "truck"}
    with pytest.raises(ModelError, match="class map"):
        models.install(env["tmp"] / "w1.pt", "rs-a-v1", **{**kw(env), "loader": loader_for(bad)})
    with pytest.raises(ModelError, match="id"):
        install(env, model_id="Bad Id!")
    install(env)
    with pytest.raises(ModelError, match="already registered"):
        install(env, model_id="rs-a-copy")          # same bytes under another id
    with pytest.raises(ModelError, match="do not load"):
        models.install(env["tmp"] / "w2.pt", "rs-b-v1", **{**kw(env), "loader": lambda p: 1 / 0})


def test_install_never_overwrites_an_active_model(env):
    install(env)
    models.activate("rs-a-v1", env["cam"], registry=env["registry"], changes=env["changes"], require_eval=False)
    with pytest.raises(ModelError, match="active"):
        install(env, name="w2.pt")                  # same id, different weights


def test_activation_needs_an_evaluation_unless_overridden(env):
    install(env)
    with pytest.raises(ModelError, match="no evaluation"):
        models.activate("rs-a-v1", env["cam"], registry=env["registry"], changes=env["changes"])
    r = models.activate("rs-a-v1", env["cam"], registry=env["registry"], changes=env["changes"], require_eval=False)
    assert r == {"camera": "cam-a", "model": "rs-a-v1", "previous": "old-model"}
    assert models.current_model(env["cam"]) == (str(env["models_dir"] / "rs-a-v1.pt"), "rs-a-v1")
    last = json.loads(env["changes"].read_text().splitlines()[-1])
    assert last["unevaluated"] is True and last["previous"] == "old-model"


def test_activation_checks_sha_applicability_and_smoke_test(env):
    e = install(env, cameras=["other-cam"])
    with pytest.raises(ModelError, match="not registered for camera"):
        models.activate("rs-a-v1", env["cam"], registry=env["registry"], changes=env["changes"], require_eval=False)
    reg = models.load_registry(env["registry"])
    models.find(reg, "rs-a-v1")["cameras"] = ["*"]
    models.save_registry(reg, env["registry"])
    (env["models_dir"] / "rs-a-v1.pt").write_bytes(b"tampered")
    with pytest.raises(ModelError, match="sha256"):
        models.activate("rs-a-v1", env["cam"], registry=env["registry"], changes=env["changes"], require_eval=False)
    (env["models_dir"] / "rs-a-v1.pt").write_bytes(b"weights-one")
    assert e["sha256"] == models.sha256_file(env["models_dir"] / "rs-a-v1.pt")
    with pytest.raises(ModelError, match="smoke test"):
        models.activate("rs-a-v1", env["cam"], registry=env["registry"], changes=env["changes"], require_eval=False,
                        frames=["f.jpg"], expect_classes=["truck"], predictor=lambda w, f: ["car"])
    assert models.current_model(env["cam"])[1] == "old-model"      # a refused activation changes nothing
    models.activate("rs-a-v1", env["cam"], registry=env["registry"], changes=env["changes"], require_eval=False,
                    frames=["f.jpg"], expect_classes=["car"], predictor=lambda w, f: ["car"])


def test_rollback_restores_the_previous_model_and_keeps_all_weights(env):
    install(env)
    install(env, name="w2.pt", model_id="rs-a-v2")
    for mid in ("rs-a-v1", "rs-a-v2"):
        models.activate(mid, env["cam"], registry=env["registry"], changes=env["changes"], require_eval=False)
    assert models.current_model(env["cam"])[1] == "rs-a-v2"
    r = models.rollback(env["cam"], registry=env["registry"], changes=env["changes"])
    assert r["model"] == "rs-a-v1" and models.current_model(env["cam"])[1] == "rs-a-v1"
    reg = models.load_registry(env["registry"])
    assert models.find(reg, "rs-a-v1")["status"] == "active" and models.find(reg, "rs-a-v2")["status"] == "retired"
    assert (env["models_dir"] / "rs-a-v2.pt").exists() and (env["models_dir"] / "rs-a-v1.pt").exists()
    assert models.verify_changes(env["changes"])


def test_rollback_without_history_is_refused(env):
    with pytest.raises(ModelError, match="no previous"):
        models.rollback(env["cam"], registry=env["registry"], changes=env["changes"])


def test_change_log_detects_tampering(env):
    install(env)
    models.activate("rs-a-v1", env["cam"], registry=env["registry"], changes=env["changes"], require_eval=False)
    assert models.verify_changes(env["changes"])
    lines = env["changes"].read_text().splitlines()
    rec = json.loads(lines[0])
    rec["operator"] = "someone-else"
    lines[0] = json.dumps(rec, sort_keys=True)
    env["changes"].write_text("\n".join(lines) + "\n")
    assert not models.verify_changes(env["changes"])


def test_camera_yaml_without_model_gets_one_inserted_before_calibration(env):
    env["cam"].write_text("id: cam-b\nname: B\ncalibration:\n  source: []\nrules: []\n")
    install(env)
    models.activate("rs-a-v1", env["cam"], registry=env["registry"], changes=env["changes"], require_eval=False)
    text = env["cam"].read_text()
    assert text.index("model:") < text.index("calibration:") and "model_id: rs-a-v1" in text


def test_pipeline_fails_loudly_when_the_configured_model_is_missing(tmp_path):
    cfg = {"id": "cam", "model": str(tmp_path / "missing.pt")}
    with pytest.raises(ModelError, match="missing"):
        models.resolve_for_pipeline(cfg, env={})
    assert models.resolve_for_pipeline(cfg, env={"RS_ALLOW_MODEL_FALLBACK": "1"})[0] == "models/yolox_s.onnx"
    with pytest.raises(ModelError, match="ONNX"):
        models.resolve_for_pipeline(cfg, "my.pt", env={})
    assert models.resolve_for_pipeline(cfg, "my.onnx", env={})[0] == "my.onnx"  # explicit ONNX override wins
    own = tmp_path / "own.onnx"
    own.write_bytes(b"x")
    path, mid, sha = models.resolve_for_pipeline({"id": "cam", "model": str(own), "model_id": "x-1"}, env={})
    assert path == str(own) and mid == "x-1" and sha == models.sha256_file(own)
    assert models.resolve_for_pipeline({"id": "cam"}, env={})[0] == "models/yolox_s.onnx"   # no model configured: stock


def test_the_shipped_registry_is_valid_and_empty_of_fake_metrics():
    reg = models.load_registry()
    assert reg["schema_version"] == 1
    assert all(m["metrics"] is None or "report" in m["metrics"] for m in reg["models"])
