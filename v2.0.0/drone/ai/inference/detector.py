"""
Guardia AI v2.0.1 — Offline Object Detector
=============================================
Runs YOLOv8-nano via TFLite or NCNN on Raspberry Pi 4B.
Zero network calls. Zero telemetry. Pure on-device inference.

Memory budget: ~200MB for model + inference buffers
Target: 8-15 FPS on Pi 4B at 320x320 input
"""

import logging
import time
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

logger = logging.getLogger("guardia.ai.detector")


@dataclass
class Detection:
    """A single object detection."""
    class_id: int
    class_name: str
    confidence: float
    bbox_xyxy: Tuple[float, float, float, float]  # x1, y1, x2, y2 (pixel coords)
    bbox_xywh: Tuple[float, float, float, float]  # center_x, center_y, w, h (normalized)

    @property
    def center(self) -> Tuple[float, float]:
        """Center of bounding box in pixel coordinates."""
        x1, y1, x2, y2 = self.bbox_xyxy
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    @property
    def area(self) -> float:
        x1, y1, x2, y2 = self.bbox_xyxy
        return (x2 - x1) * (y2 - y1)


@dataclass
class DetectionResult:
    """Result of running detection on a single frame."""
    detections: List[Detection] = field(default_factory=list)
    inference_time_ms: float = 0.0
    frame_shape: Tuple[int, int] = (0, 0)
    timestamp: float = 0.0

    @property
    def person_count(self) -> int:
        return sum(1 for d in self.detections if d.class_name == "person")

    @property
    def has_people(self) -> bool:
        return self.person_count > 0

    def get_by_class(self, class_name: str) -> List[Detection]:
        return [d for d in self.detections if d.class_name == class_name]

    def get_persons(self) -> List[Detection]:
        return self.get_by_class("person")


# COCO class names (80 classes)
COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep",
    "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
    "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
    "sports ball", "kite", "baseball bat", "baseball glove", "skateboard",
    "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork",
    "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv",
    "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave",
    "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush"
]


class OfflineDetector:
    """
    YOLOv8-nano detector running on TFLite or NCNN.
    Designed for Pi 4B with 8GB RAM.

    Usage:
        detector = OfflineDetector(model_path="yolov8n.tflite")
        detector.initialize()
        result = detector.detect(frame_bgr)
    """

    def __init__(
        self,
        model_path: str = "yolov8n.tflite",
        input_size: int = 320,
        confidence_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        max_detections: int = 20,
        target_classes: Optional[List[str]] = None,
    ):
        self._model_path = model_path
        self._input_size = input_size
        self._conf_threshold = confidence_threshold
        self._iou_threshold = iou_threshold
        self._max_detections = max_detections
        self._target_classes = target_classes or ["person"]
        self._target_class_ids = set()

        self._interpreter = None
        self._input_details = None
        self._output_details = None
        self._initialized = False

        # Performance tracking
        self._frame_count = 0
        self._total_inference_ms = 0.0

    def initialize(self) -> bool:
        """Load the TFLite model. Returns True on success."""
        try:
            import tflite_runtime.interpreter as tflite
            logger.info("Using tflite_runtime")
        except ImportError:
            try:
                import tensorflow.lite as tflite
                logger.info("Using tensorflow.lite")
            except ImportError:
                logger.error(
                    "Neither tflite_runtime nor tensorflow found. "
                    "Install with: pip install tflite-runtime"
                )
                return False

        model_file = Path(self._model_path)
        if not model_file.exists():
            # Try relative to this file's directory
            model_file = Path(__file__).parent.parent / "ai" / "models" / self._model_path
        if not model_file.exists():
            logger.error("Model file not found: %s", self._model_path)
            return False

        try:
            self._interpreter = tflite.Interpreter(
                model_path=str(model_file),
                num_threads=4,  # Use all 4 Pi cores
            )
            self._interpreter.allocate_tensors()
            self._input_details = self._interpreter.get_input_details()
            self._output_details = self._interpreter.get_output_details()

            # Resolve target class IDs
            self._target_class_ids = {
                i for i, name in enumerate(COCO_CLASSES)
                if name in self._target_classes
            }

            self._initialized = True
            logger.info(
                "Detector initialized: %s | input=%dx%d | classes=%s",
                model_file.name, self._input_size, self._input_size,
                self._target_classes
            )
            return True

        except Exception as e:
            logger.error("Failed to load model: %s", e)
            self._initialized = False
            return False

    @property
    def is_ready(self) -> bool:
        return self._initialized

    @property
    def avg_inference_ms(self) -> float:
        if self._frame_count == 0:
            return 0.0
        return self._total_inference_ms / self._frame_count

    def detect(self, frame: np.ndarray) -> DetectionResult:
        """
        Run detection on a BGR frame.

        Args:
            frame: BGR uint8 numpy array (H, W, 3)

        Returns:
            DetectionResult with detections and timing info
        """
        if not self._initialized:
            return DetectionResult()

        h, w = frame.shape[:2]
        start_time = time.monotonic()

        # Preprocess: resize and normalize
        input_tensor = self._preprocess(frame)

        # Run inference
        self._interpreter.set_tensor(
            self._input_details[0]["index"], input_tensor
        )
        self._interpreter.invoke()

        # Get output
        output = self._interpreter.get_tensor(
            self._output_details[0]["index"]
        )

        # Post-process: NMS and filtering
        detections = self._postprocess(output, w, h)

        inference_ms = (time.monotonic() - start_time) * 1000
        self._frame_count += 1
        self._total_inference_ms += inference_ms

        return DetectionResult(
            detections=detections,
            inference_time_ms=round(inference_ms, 1),
            frame_shape=(h, w),
            timestamp=time.time(),
        )

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Resize, pad, and normalize frame for model input."""
        import cv2

        # Letterbox resize
        h, w = frame.shape[:2]
        scale = min(self._input_size / h, self._input_size / w)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Pad to square
        padded = np.full(
            (self._input_size, self._input_size, 3), 114, dtype=np.uint8
        )
        dw, dh = (self._input_size - new_w) // 2, (self._input_size - new_h) // 2
        padded[dh:dh + new_h, dw:dw + new_w] = resized

        # BGR to RGB, normalize to [0, 1], add batch dim
        rgb = padded[:, :, ::-1].astype(np.float32) / 255.0
        return np.expand_dims(rgb, axis=0)

    def _postprocess(
        self, output: np.ndarray, orig_w: int, orig_h: int
    ) -> List[Detection]:
        """Apply NMS and convert to Detection objects."""
        # YOLOv8 TFLite output shape: (1, num_classes+4, num_boxes)
        # Transpose to (num_boxes, num_classes+4)
        if output.ndim == 3:
            output = output[0]
        if output.shape[0] < output.shape[1]:
            output = output.T

        detections = []
        scale = min(self._input_size / orig_h, self._input_size / orig_w)
        dw = (self._input_size - orig_w * scale) / 2
        dh = (self._input_size - orig_h * scale) / 2

        for row in output:
            # row = [cx, cy, w, h, class_scores...]
            cx, cy, bw, bh = row[:4]
            class_scores = row[4:]

            max_score_idx = np.argmax(class_scores)
            max_score = class_scores[max_score_idx]

            if max_score < self._conf_threshold:
                continue

            # Filter by target classes if specified
            if self._target_class_ids and max_score_idx not in self._target_class_ids:
                # Still detect if confidence is very high (security-relevant)
                if max_score < 0.7:
                    continue

            # Convert from model coords to original image coords
            x1 = (cx - bw / 2 - dw) / scale
            y1 = (cy - bh / 2 - dh) / scale
            x2 = (cx + bw / 2 - dw) / scale
            y2 = (cy + bh / 2 - dh) / scale

            # Clamp to image bounds
            x1 = max(0, min(x1, orig_w))
            y1 = max(0, min(y1, orig_h))
            x2 = max(0, min(x2, orig_w))
            y2 = max(0, min(y2, orig_h))

            class_name = COCO_CLASSES[max_score_idx] if max_score_idx < len(COCO_CLASSES) else f"class_{max_score_idx}"

            detections.append(Detection(
                class_id=int(max_score_idx),
                class_name=class_name,
                confidence=float(max_score),
                bbox_xyxy=(x1, y1, x2, y2),
                bbox_xywh=(
                    (x1 + x2) / 2 / orig_w,
                    (y1 + y2) / 2 / orig_h,
                    (x2 - x1) / orig_w,
                    (y2 - y1) / orig_h,
                ),
            ))

        # NMS
        if detections:
            detections = self._nms(detections)

        # Cap at max detections
        detections.sort(key=lambda d: d.confidence, reverse=True)
        return detections[:self._max_detections]

    def _nms(self, detections: List[Detection]) -> List[Detection]:
        """Simple non-maximum suppression."""
        if not detections:
            return []

        detections.sort(key=lambda d: d.confidence, reverse=True)
        keep = []

        while detections:
            best = detections.pop(0)
            keep.append(best)
            detections = [
                d for d in detections
                if self._iou(best.bbox_xyxy, d.bbox_xyxy) < self._iou_threshold
            ]

        return keep

    @staticmethod
    def _iou(
        box1: Tuple[float, float, float, float],
        box2: Tuple[float, float, float, float],
    ) -> float:
        """Compute IoU between two boxes."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - inter

        return inter / union if union > 0 else 0.0
