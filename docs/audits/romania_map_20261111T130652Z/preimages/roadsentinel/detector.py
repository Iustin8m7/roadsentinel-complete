"""Permissive YOLOX ONNX detector and Supervision ByteTrack adapter.

Model output uses the standard YOLOX COCO ordering (80 classes). No weights are downloaded
implicitly: callers must provide a local, provenance-checked ONNX file.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

COCO = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck",
    24: "object", 26: "object", 28: "object",
}


@dataclass(frozen=True)
class Detections:
    xyxy: np.ndarray
    confidence: np.ndarray
    class_id: np.ndarray
    latency_ms: float


def _decode(raw: np.ndarray, input_size: tuple[int, int]) -> np.ndarray:
    """Decode raw YOLOX (cx,cy,w,h,obj,classes...) rows from grid offsets."""
    predictions = np.asarray(raw, dtype=np.float32)
    if predictions.ndim == 3:
        if predictions.shape[0] != 1:
            raise ValueError("YOLOX inference expects batch size 1")
        predictions = predictions[0]
    if predictions.ndim != 2 or predictions.shape[1] < 6:
        raise ValueError(f"unexpected YOLOX output shape: {predictions.shape}")
    height, width = input_size
    strides = (8, 16, 32)
    grids, expanded_strides = [], []
    for stride in strides:
        grid_h, grid_w = height // stride, width // stride
        yv, xv = np.meshgrid(np.arange(grid_h), np.arange(grid_w), indexing="ij")
        grids.append(np.stack((xv, yv), axis=-1).reshape(1, -1, 2))
        expanded_strides.append(np.full((1, grid_h * grid_w, 1), stride, dtype=np.float32))
    grid = np.concatenate(grids, axis=1)
    stride = np.concatenate(expanded_strides, axis=1)
    if len(predictions) != grid.shape[1]:
        raise ValueError(f"YOLOX output anchor count {len(predictions)} != expected {grid.shape[1]}")
    decoded = predictions.copy()
    decoded[:, :2] = (decoded[:, :2] + grid[0]) * stride[0]
    decoded[:, 2:4] = np.exp(np.clip(decoded[:, 2:4], -20, 20)) * stride[0]
    return decoded


def _nms(boxes: np.ndarray, scores: np.ndarray, threshold: float) -> list[int]:
    if len(boxes) == 0:
        return []
    x1, y1, x2, y2 = boxes.T
    areas = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
    order = np.argsort(scores, kind="stable")[::-1]
    keep: list[int] = []
    while order.size:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        rest = order[1:]
        xx1, yy1 = np.maximum(x1[i], x1[rest]), np.maximum(y1[i], y1[rest])
        xx2, yy2 = np.minimum(x2[i], x2[rest]), np.minimum(y2[i], y2[rest])
        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        union = areas[i] + areas[rest] - inter
        iou = inter / np.maximum(union, 1e-8)
        order = rest[iou <= threshold]
    return keep


def postprocess(
    raw: np.ndarray,
    *,
    frame_shape: tuple[int, int],
    input_size: tuple[int, int] = (640, 640),
    classes: set[int] | None = None,
    confidence_threshold: float = 0.3,
    iou_threshold: float = 0.45,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Map YOLOX output back to source-frame XYXY and perform class-aware NMS."""
    if not 0.01 <= confidence_threshold <= 0.99 or not 0.05 <= iou_threshold <= 0.95:
        raise ValueError("confidence/iou thresholds outside safe bounds")
    height, width = frame_shape
    ratio = min(input_size[0] / height, input_size[1] / width)
    pred = _decode(raw, input_size)
    obj = pred[:, 4]
    class_scores = pred[:, 5:]
    class_ids = class_scores.argmax(axis=1)
    scores = obj * class_scores[np.arange(len(class_scores)), class_ids]
    mask = (scores >= confidence_threshold) & np.isfinite(scores)
    if classes is not None:
        mask &= np.isin(class_ids, tuple(classes))
    pred, scores, class_ids = pred[mask], scores[mask], class_ids[mask]
    if len(pred) == 0:
        return np.empty((0, 4), dtype=np.float32), np.empty(0, dtype=np.float32), np.empty(0, dtype=np.int64)
    boxes = np.column_stack((pred[:, 0] - pred[:, 2] / 2, pred[:, 1] - pred[:, 3] / 2,
                             pred[:, 0] + pred[:, 2] / 2, pred[:, 1] + pred[:, 3] / 2)) / ratio
    boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, width)
    boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, height)
    keep: list[int] = []
    for class_id in np.unique(class_ids):
        ids = np.flatnonzero(class_ids == class_id)
        keep.extend(ids[i] for i in _nms(boxes[ids], scores[ids], iou_threshold))
    keep = sorted(keep, key=lambda i: (-float(scores[i]), int(class_ids[i])))
    return boxes[keep].astype(np.float32), scores[keep].astype(np.float32), class_ids[keep].astype(np.int64)


class YoloXOnnx:
    """YOLOX ONNX Runtime session with an explicit, observable CPU/CUDA selection."""

    def __init__(
        self,
        path: str | Path,
        *,
        input_size: int = 640,
        provider: str | None = None,
        session=None,
    ):
        self.path = Path(path)
        requested = (provider or os.environ.get("RS_ONNX_PROVIDER", "auto")).lower()
        if requested not in {"auto", "cpu", "cuda"}:
            raise ValueError("RS_ONNX_PROVIDER must be auto, cpu, or cuda")
        self.provider_fallback_reason = None
        if session is None:
            if not self.path.is_file():
                raise FileNotFoundError(f"YOLOX ONNX weights not found: {self.path}")
            try:
                import onnxruntime as ort
            except ImportError as err:
                raise RuntimeError("install onnxruntime into the project .venv") from err
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = min(4, max(1, os.cpu_count() or 1))
            available = ort.get_available_providers()
            wants_cuda = requested in {"auto", "cuda"}
            if wants_cuda and "CUDAExecutionProvider" not in available:
                self.provider_fallback_reason = "CUDAExecutionProvider is not installed in this ONNX Runtime"
            if wants_cuda and "CUDAExecutionProvider" in available:
                try:
                    session = ort.InferenceSession(
                        str(self.path),
                        sess_options=opts,
                        providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
                    )
                except Exception as exc:  # noqa: BLE001 - CPU fallback is the safe runtime path.
                    self.provider_fallback_reason = (
                        f"CUDA session initialization failed ({type(exc).__name__}); using CPU"
                    )
            if session is None:
                session = ort.InferenceSession(
                    str(self.path), sess_options=opts, providers=["CPUExecutionProvider"]
                )
        providers = session.get_providers() if hasattr(session, "get_providers") else []
        self.provider = next(
            (name for name in ("CUDAExecutionProvider", "CPUExecutionProvider") if name in providers),
            "UNKNOWN",
        )
        if requested == "cpu" and self.provider != "CPUExecutionProvider":
            self.provider_fallback_reason = "requested CPU provider was not active"
        elif requested == "cuda" and self.provider != "CUDAExecutionProvider":
            self.provider_fallback_reason = self.provider_fallback_reason or (
                "CUDA was requested but the session activated " + self.provider
            )
        elif requested == "auto" and self.provider == "CPUExecutionProvider":
            try:
                if "CUDAExecutionProvider" in ort.get_available_providers():
                    self.provider_fallback_reason = "CUDA was available but the session activated CPU"
            except (NameError, AttributeError):
                pass
        self.session = session
        self.input_size = (input_size, input_size)
        self.input_name = session.get_inputs()[0].name
        self.output_name = session.get_outputs()[0].name

    def predict(self, frame: np.ndarray, *, classes: set[int] | None = None,
                confidence_threshold: float = 0.3, iou_threshold: float = 0.45) -> Detections:
        if frame is None or frame.ndim != 3 or frame.shape[2] != 3 or frame.size == 0:
            raise ValueError("expected a non-empty BGR frame")
        started = time.perf_counter()
        height, width = frame.shape[:2]
        ratio = min(self.input_size[0] / height, self.input_size[1] / width)
        resized = cv2.resize(frame, (int(width * ratio), int(height * ratio)), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((*self.input_size, 3), 114, dtype=np.uint8)
        canvas[:resized.shape[0], :resized.shape[1]] = resized
        # Match Megvii's official preproc: BGR channel order, uint8-scale values, top-left pad.
        tensor = canvas.astype(np.float32)
        tensor = np.ascontiguousarray(tensor.transpose(2, 0, 1)[None])
        raw = self.session.run([self.output_name], {self.input_name: tensor})[0]
        boxes, confidence, class_id = postprocess(
            raw, frame_shape=(height, width), input_size=self.input_size, classes=classes,
            confidence_threshold=confidence_threshold, iou_threshold=iou_threshold,
        )
        return Detections(boxes, confidence, class_id, (time.perf_counter() - started) * 1000)


def create_tracker(frame_rate: float):
    try:
        import supervision as sv
    except ImportError as err:
        raise RuntimeError("install supervision==0.30.7 into the project .venv") from err
    return sv.ByteTrack(frame_rate=max(1, round(frame_rate)))


def to_supervision(detections: Detections):
    try:
        import supervision as sv
    except ImportError as err:
        raise RuntimeError("install supervision==0.30.7 into the project .venv") from err
    return sv.Detections(xyxy=detections.xyxy, confidence=detections.confidence, class_id=detections.class_id)
