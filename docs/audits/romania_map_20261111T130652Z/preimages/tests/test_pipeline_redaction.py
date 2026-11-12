"""Privacy regions must change without altering unrelated pixels."""
from pathlib import Path

import numpy as np
import pytest

from roadsentinel import redaction as pipeline


def frame():
    return np.random.default_rng(42).integers(0, 256, (200, 240, 3), dtype=np.uint8)


def test_full_redacts_plate_windshield_and_person(monkeypatch):
    monkeypatch.delenv('RS_REDACTION', raising=False)
    before = frame()
    after = before.copy()
    pipeline.redact_frame(after, [('car', (20, 20, 120, 120)), ('person', (150, 30, 180, 120))])
    assert not np.array_equal(after[85:120, 20:120], before[85:120, 20:120])
    assert not np.array_equal(after[20:70, 20:120], before[20:70, 20:120])
    assert not np.array_equal(after[30:60, 150:180], before[30:60, 150:180])
    mask = np.ones(before.shape[:2], dtype=bool)
    mask[85:120, 20:120] = False
    mask[20:70, 20:120] = False
    mask[30:60, 150:180] = False
    np.testing.assert_array_equal(after[mask], before[mask])


def test_heads_only_keeps_vehicle_pixels(monkeypatch):
    monkeypatch.setenv('RS_REDACTION', 'heads_only')
    before = frame()
    after = before.copy()
    pipeline.redact_frame(after, [('car', (20, 20, 120, 120)), ('person', (40, 30, 60, 90))])
    assert not np.array_equal(after[30:50, 40:60], before[30:50, 40:60])
    mask = np.ones(before.shape[:2], dtype=bool)
    mask[30:50, 40:60] = False
    np.testing.assert_array_equal(after[mask], before[mask])


def test_distant_vehicle_plate_but_no_windshield():
    before = frame()
    after = before.copy()
    pipeline.redact_frame(after, [('car', (10, 10, 22, 22))], mode='full')
    np.testing.assert_array_equal(after[10:16, 10:22], before[10:16, 10:22])
    assert not np.array_equal(after[18:22, 10:22], before[18:22, 10:22])


def test_outside_and_invalid_boxes_do_not_wrap():
    before = frame()
    after = before.copy()
    pipeline.redact_frame(after, [('car', (-50, -50, -10, -10)), ('person', (40, 40, 20, 20))], mode='full')
    np.testing.assert_array_equal(after, before)


def test_invalid_mode_fails_closed(monkeypatch):
    monkeypatch.setenv('RS_REDACTION', 'none')
    with pytest.raises(ValueError, match='RS_REDACTION'):
        pipeline.redact_frame(frame(), [])


@pytest.mark.parametrize('kind', ['car', 'truck', 'bus', 'motorcycle'])
def test_every_motor_vehicle_has_plate_band(kind):
    before = frame()
    after = before.copy()
    pipeline.redact_frame(after, [(kind, (20, 20, 120, 120))], mode='full')
    assert not np.array_equal(after[85:120, 20:120], before[85:120, 20:120])
    if kind == 'motorcycle':
        np.testing.assert_array_equal(after[20:70, 20:120], before[20:70, 20:120])
    else:
        assert not np.array_equal(after[20:70, 20:120], before[20:70, 20:120])


def test_partial_boxes_clip_at_image_boundary():
    before = frame()
    after = before.copy()
    pipeline.redact_frame(after, [('car', (-20, 100, 30, 220))], mode='full')
    assert not np.array_equal(after[178:200, :30], before[178:200, :30])
    np.testing.assert_array_equal(after[:, 30:], before[:, 30:])


def test_clip_fps_follows_the_stream_times_of_dropped_frames():
    from roadsentinel.pipeline import clip_fps

    assert clip_fps([0.0, 0.25, 0.5, 0.75, 1.0], 20) == 4
    assert clip_fps([3.0], 20) == 20


def test_pick_model_uses_only_the_supported_onnx_runtime(tmp_path, monkeypatch):
    from roadsentinel.models import ModelError
    from roadsentinel.pipeline import pick_model

    monkeypatch.delenv('RS_ALLOW_MODEL_FALLBACK', raising=False)
    weights = tmp_path / 'cam.onnx'
    weights.write_bytes(b'x')
    other = tmp_path / 'other.onnx'
    other.write_bytes(b'y')
    assert pick_model({'model': str(weights)}, str(other)) == str(other)
    assert pick_model({'model': str(weights)}) == str(weights)
    with pytest.raises(ModelError):
        pick_model({'model': str(tmp_path / 'missing.onnx')})
    assert pick_model({}) == 'models/yolox_s.onnx'


def test_pipeline_reports_detector_startup_failure_before_opening_source(monkeypatch, tmp_path):
    from roadsentinel import pipeline

    config = tmp_path / "camera.yaml"
    config.write_text("id: probe\nname: Probe\nvideo: device:0\nstart_time: '2026-11-07T00:00:00'\nrules: []\nzones: []\nthresholds: {}\n")
    monkeypatch.setattr(pipeline, "YoloXOnnx", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("install onnxruntime")))
    with pytest.raises(RuntimeError, match="install onnxruntime"):
        pipeline.run(str(config), live=True)


def test_redaction_is_on_by_default(monkeypatch):
    monkeypatch.delenv('RS_REDACTION', raising=False)
    assert pipeline.redaction_mode() == 'full'


def test_off_needs_an_explicit_confirmation(monkeypatch):
    monkeypatch.setenv('RS_REDACTION', 'off')
    monkeypatch.delenv('RS_ALLOW_UNREDACTED', raising=False)
    with pytest.raises(ValueError, match='RS_ALLOW_UNREDACTED'):
        pipeline.redaction_mode()
    monkeypatch.setenv('RS_ALLOW_UNREDACTED', '1')
    assert pipeline.redaction_mode() == 'off'


def test_pipeline_reports_the_real_mode():
    """The mode must reach the backend unchanged (it used to relabel off as heads_only)."""
    src = Path('roadsentinel/pipeline.py').read_text()
    assert 'e["redaction"] = redaction' in src
    assert 'heads_only" if redaction == "off"' not in src
