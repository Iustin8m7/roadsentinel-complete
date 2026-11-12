"""Regression tests for the permissive YOLOX ONNX inference adapter."""

from types import SimpleNamespace

import numpy as np
import pytest

from roadsentinel.detector import YoloXOnnx, create_tracker, postprocess, to_supervision


def raw_with(*rows):
    raw = np.zeros((1, 8400, 85), dtype=np.float32)
    for index, cx, cy, width, height, score, class_id in rows:
        raw[0, index, :5] = [cx, cy, width, height, score]
        raw[0, index, 5 + class_id] = 0.9
    return raw


def test_postprocess_decodes_source_coordinates_and_filters_classes():
    # At the 8px stride, flattened grid cell 3240 is (x=40, y=40).
    raw = raw_with((3240, 0, 0, 0, 0, 0.9, 2), (3241, -1, 0, 0, 0, 0.8, 2))
    boxes, scores, classes = postprocess(
        raw, frame_shape=(640, 1280), classes={2}, confidence_threshold=0.3,
    )
    assert boxes.shape == (1, 4)
    np.testing.assert_allclose(boxes[0], [632, 632, 648, 640], atol=1)
    assert scores[0] == pytest.approx(0.81)
    assert classes.tolist() == [2]


def test_postprocess_keeps_overlapping_different_classes():
    raw = raw_with((3240, 0, 0, 0, 0, 0.9, 2), (3241, -1, 0, 0, 0, 0.8, 7))
    boxes, _, classes = postprocess(raw, frame_shape=(640, 640), confidence_threshold=0.3)
    assert len(boxes) == 2
    assert classes.tolist() == [2, 7]


@pytest.mark.parametrize(
    ("confidence", "iou"), [(0, 0.4), (1.1, 0.4), (0.3, 0.01), (0.3, 1.0)],
)
def test_postprocess_rejects_unsafe_thresholds(confidence, iou):
    with pytest.raises(ValueError, match="safe bounds"):
        postprocess(np.zeros((1, 8400, 85), np.float32), frame_shape=(640, 640),
                    confidence_threshold=confidence, iou_threshold=iou)


class FakeSession:
    def get_inputs(self):
        return [type("Node", (), {"name": "images"})()]

    def get_outputs(self):
        return [type("Node", (), {"name": "output"})()]

    def get_providers(self):
        return ["CPUExecutionProvider"]

    def run(self, names, feed):
        self.tensor = feed["images"]
        return [np.zeros((1, 8400, 85), dtype=np.float32)]


def test_adapter_uses_megvii_bgr_255_scale_and_validates_frames():
    session = FakeSession()
    model = YoloXOnnx("ignored.onnx", session=session)
    frame = np.zeros((320, 640, 3), dtype=np.uint8)
    frame[:, :, 0] = 17
    model.predict(frame)
    assert session.tensor.shape == (1, 3, 640, 640)
    assert session.tensor.dtype == np.float32
    assert session.tensor[0, 0, 20, 20] == 17
    assert session.tensor[0, 2, 20, 20] == 0
    assert session.tensor[0, 0, 400, 20] == 114
    with pytest.raises(ValueError, match="non-empty BGR"):
        model.predict(None)


@pytest.mark.parametrize("requested", ["auto", "cuda"])
def test_detector_discloses_cpu_fallback_when_cuda_provider_is_unavailable(
    requested, monkeypatch, tmp_path
):
    import sys

    weights = tmp_path / "yolox.onnx"
    weights.write_bytes(b"fixture")
    runtime = SimpleNamespace(
        SessionOptions=lambda: type("Options", (), {})(),
        get_available_providers=lambda: ["CPUExecutionProvider"],
        InferenceSession=lambda *_args, **_kwargs: FakeSession(),
    )
    monkeypatch.setitem(sys.modules, "onnxruntime", runtime)
    detector = YoloXOnnx(weights, provider=requested)
    assert detector.provider == "CPUExecutionProvider"
    assert "not installed" in detector.provider_fallback_reason


def test_detector_selects_cuda_only_when_the_session_reports_cuda(monkeypatch, tmp_path):
    import sys

    weights = tmp_path / "yolox.onnx"
    weights.write_bytes(b"fixture")
    requested_provider_lists = []

    class CudaSession(FakeSession):
        def get_providers(self):
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]

    runtime = SimpleNamespace(
        SessionOptions=lambda: type("Options", (), {})(),
        get_available_providers=lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"],
        InferenceSession=lambda *_args, providers, **_kwargs: (
            requested_provider_lists.append(providers) or CudaSession()
        ),
    )
    monkeypatch.setitem(sys.modules, "onnxruntime", runtime)
    detector = YoloXOnnx(weights, provider="cuda")
    assert detector.provider == "CUDAExecutionProvider"
    assert requested_provider_lists == [["CUDAExecutionProvider", "CPUExecutionProvider"]]


def test_supervision_bytetrack_keeps_ids_for_a_moving_detection():
    tracker = create_tracker(10)
    tracked_ids = []
    for x in (100, 105, 110, 115):
        detections = type("FrameDetections", (), {
            "xyxy": np.array([[x, 100, x + 80, 180]], dtype=np.float32),
            "confidence": np.array([0.9], dtype=np.float32),
            "class_id": np.array([2], dtype=np.int64),
        })()
        tracked = tracker.update_with_detections(to_supervision(detections))
        if tracked.tracker_id is not None:
            tracked_ids.extend(tracked.tracker_id.tolist())
    assert tracked_ids
    assert len(set(tracked_ids)) == 1

