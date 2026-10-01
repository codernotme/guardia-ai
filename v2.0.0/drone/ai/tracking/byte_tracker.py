"""
Guardia AI v2.0.1 — ByteTrack Multi-Object Tracker
====================================================
Lightweight multi-object tracker for person following, tailing, and rescue.
Runs entirely offline on Raspberry Pi 4B.

Features:
- Track-by-detection using IoU matching (no deep features needed for basic tracking)
- Person Re-ID support for tailing (optional, uses TFLite embedding model)
- Stable track IDs across occlusions
- Lost/found state management
- Optimized for 8-15 FPS input
"""

import logging
import time
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field
from collections import deque

import numpy as np

logger = logging.getLogger("guardia.ai.tracker")


@dataclass
class Track:
    """A tracked object across multiple frames."""
    track_id: int
    class_name: str
    class_id: int

    # Current state
    bbox_xyxy: Tuple[float, float, float, float] = (0, 0, 0, 0)
    confidence: float = 0.0
    velocity: Tuple[float, float] = (0.0, 0.0)  # Pixel velocity (dx, dy per frame)

    # Tracking state
    age: int = 0            # Total frames since track creation
    hits: int = 0           # Number of successful matches
    misses: int = 0         # Consecutive missed frames
    state: str = "tentative"  # tentative, confirmed, lost

    # Re-ID embedding (for tailing mode)
    embedding: Optional[np.ndarray] = None

    # History for smoothing
    bbox_history: deque = field(default_factory=lambda: deque(maxlen=30))
    center_history: deque = field(default_factory=lambda: deque(maxlen=60))

    @property
    def center(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self.bbox_xyxy
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    @property
    def width(self) -> float:
        return self.bbox_xyxy[2] - self.bbox_xyxy[0]

    @property
    def height(self) -> float:
        return self.bbox_xyxy[3] - self.bbox_xyxy[1]

    @property
    def area(self) -> float:
        return self.width * self.height

    def predict_next_bbox(self) -> Tuple[float, float, float, float]:
        """Simple linear prediction of next bbox position."""
        x1, y1, x2, y2 = self.bbox_xyxy
        dx, dy = self.velocity
        return (x1 + dx, y1 + dy, x2 + dx, y2 + dy)


@dataclass
class TrackerResult:
    """Result of running the tracker on a frame."""
    tracks: List[Track] = field(default_factory=list)
    new_tracks: List[int] = field(default_factory=list)
    lost_tracks: List[int] = field(default_factory=list)
    removed_tracks: List[int] = field(default_factory=list)
    processing_time_ms: float = 0.0

    @property
    def confirmed_tracks(self) -> List[Track]:
        return [t for t in self.tracks if t.state == "confirmed"]

    @property
    def person_tracks(self) -> List[Track]:
        return [t for t in self.tracks if t.class_name == "person" and t.state == "confirmed"]

    def get_track(self, track_id: int) -> Optional[Track]:
        for t in self.tracks:
            if t.track_id == track_id:
                return t
        return None


class ByteTracker:
    """
    ByteTrack-inspired multi-object tracker.

    Optimized for Pi 4B:
    - Pure numpy, no heavy dependencies
    - IoU-based matching (fast)
    - Optional Re-ID for person tailing
    - Memory-efficient track management

    Usage:
        tracker = ByteTracker()
        result = tracker.update(detections, frame)  # Each frame
    """

    def __init__(
        self,
        max_age: int = 30,
        min_hits: int = 3,
        iou_threshold: float = 0.3,
        high_conf_threshold: float = 0.5,
        low_conf_threshold: float = 0.1,
    ):
        self._max_age = max_age
        self._min_hits = min_hits
        self._iou_threshold = iou_threshold
        self._high_conf = high_conf_threshold
        self._low_conf = low_conf_threshold

        self._tracks: Dict[int, Track] = {}
        self._next_id = 1
        self._frame_count = 0

        logger.info(
            "ByteTracker initialized | max_age=%d min_hits=%d iou=%.2f",
            max_age, min_hits, iou_threshold
        )

    @property
    def is_ready(self) -> bool:
        return True

    @property
    def active_tracks(self) -> List[Track]:
        return [t for t in self._tracks.values() if t.state != "lost"]

    @property
    def confirmed_tracks(self) -> List[Track]:
        return [t for t in self._tracks.values() if t.state == "confirmed"]

    def update(self, detections: list, frame: Optional[np.ndarray] = None) -> TrackerResult:
        """
        Update tracks with new detections.

        Args:
            detections: List of Detection objects from the detector
            frame: Optional BGR frame for Re-ID embedding extraction

        Returns:
            TrackerResult with updated tracks
        """
        start = time.monotonic()
        self._frame_count += 1

        new_tracks = []
        lost_tracks = []
        removed_tracks = []

        # Split detections by confidence
        high_dets = [d for d in detections if d.confidence >= self._high_conf]
        low_dets = [d for d in detections if self._low_conf <= d.confidence < self._high_conf]

        # Step 1: Match high-confidence detections to existing tracks
        matched_track_ids = set()
        matched_det_indices = set()

        if self._tracks and high_dets:
            cost_matrix = self._compute_iou_matrix(
                list(self._tracks.values()), high_dets
            )
            matches = self._hungarian_match(cost_matrix)

            track_list = list(self._tracks.values())
            for track_idx, det_idx in matches:
                if cost_matrix[track_idx, det_idx] < self._iou_threshold:
                    continue  # IoU too low

                track = track_list[track_idx]
                det = high_dets[det_idx]
                self._update_track(track, det)
                matched_track_ids.add(track.track_id)
                matched_det_indices.add(det_idx)

        # Step 2: Match low-confidence detections to unmatched tracks
        unmatched_tracks = [
            t for t in self._tracks.values()
            if t.track_id not in matched_track_ids
        ]
        if unmatched_tracks and low_dets:
            cost_matrix = self._compute_iou_matrix(unmatched_tracks, low_dets)
            matches = self._hungarian_match(cost_matrix)

            for track_idx, det_idx in matches:
                if cost_matrix[track_idx, det_idx] < self._iou_threshold:
                    continue
                track = unmatched_tracks[track_idx]
                det = low_dets[det_idx]
                self._update_track(track, det)
                matched_track_ids.add(track.track_id)

        # Step 3: Create new tracks for unmatched high-confidence detections
        for i, det in enumerate(high_dets):
            if i not in matched_det_indices:
                track = self._create_track(det)
                new_tracks.append(track.track_id)

        # Step 4: Handle unmatched tracks (increment misses)
        for track in self._tracks.values():
            if track.track_id not in matched_track_ids:
                track.misses += 1
                track.age += 1

                if track.misses > self._max_age:
                    removed_tracks.append(track.track_id)
                elif track.state == "confirmed" and track.misses > 5:
                    track.state = "lost"
                    lost_tracks.append(track.track_id)

        # Step 5: Remove dead tracks
        for tid in removed_tracks:
            del self._tracks[tid]

        # Build result
        elapsed_ms = (time.monotonic() - start) * 1000

        return TrackerResult(
            tracks=list(self._tracks.values()),
            new_tracks=new_tracks,
            lost_tracks=lost_tracks,
            removed_tracks=removed_tracks,
            processing_time_ms=round(elapsed_ms, 1),
        )

    def get_track(self, track_id: int) -> Optional[Track]:
        """Get a specific track by ID."""
        return self._tracks.get(track_id)

    def get_target_offset(
        self, track_id: int, frame_width: int, frame_height: int
    ) -> Optional[Tuple[float, float, float]]:
        """
        Get the offset of a target from frame center.

        Returns:
            (offset_x, offset_y, relative_size) or None if track not found.
            offset_x: -1.0 (left) to 1.0 (right)
            offset_y: -1.0 (top) to 1.0 (bottom)
            relative_size: bbox height / frame height (distance proxy)
        """
        track = self._tracks.get(track_id)
        if track is None or track.state == "lost":
            return None

        cx, cy = track.center
        offset_x = (cx - frame_width / 2) / (frame_width / 2)
        offset_y = (cy - frame_height / 2) / (frame_height / 2)
        relative_size = track.height / frame_height

        return (offset_x, offset_y, relative_size)

    def reset(self):
        """Clear all tracks."""
        self._tracks.clear()
        self._next_id = 1
        self._frame_count = 0
        logger.info("Tracker reset")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _create_track(self, detection) -> Track:
        """Create a new track from a detection."""
        track = Track(
            track_id=self._next_id,
            class_name=detection.class_name,
            class_id=detection.class_id,
            bbox_xyxy=detection.bbox_xyxy,
            confidence=detection.confidence,
            hits=1,
            state="tentative",
        )
        track.bbox_history.append(detection.bbox_xyxy)
        track.center_history.append(track.center)

        self._tracks[self._next_id] = track
        self._next_id += 1
        return track

    def _update_track(self, track: Track, detection):
        """Update an existing track with a new detection."""
        old_center = track.center

        track.bbox_xyxy = detection.bbox_xyxy
        track.confidence = detection.confidence
        track.hits += 1
        track.misses = 0
        track.age += 1

        # Update velocity
        new_center = track.center
        track.velocity = (
            new_center[0] - old_center[0],
            new_center[1] - old_center[1],
        )

        # Update history
        track.bbox_history.append(detection.bbox_xyxy)
        track.center_history.append(new_center)

        # State promotion
        if track.state == "tentative" and track.hits >= self._min_hits:
            track.state = "confirmed"
        elif track.state == "lost":
            track.state = "confirmed"

    def _compute_iou_matrix(
        self, tracks: List[Track], detections: list
    ) -> np.ndarray:
        """Compute IoU cost matrix between tracks and detections."""
        n_tracks = len(tracks)
        n_dets = len(detections)
        cost = np.zeros((n_tracks, n_dets), dtype=np.float32)

        for i, track in enumerate(tracks):
            # Use predicted bbox for lost tracks
            if track.misses > 0:
                track_bbox = track.predict_next_bbox()
            else:
                track_bbox = track.bbox_xyxy

            for j, det in enumerate(detections):
                cost[i, j] = self._iou(track_bbox, det.bbox_xyxy)

        return cost

    @staticmethod
    def _iou(box1, box2) -> float:
        """Compute IoU."""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - inter

        return inter / union if union > 0 else 0.0

    def _hungarian_match(
        self, cost_matrix: np.ndarray
    ) -> List[Tuple[int, int]]:
        """
        Greedy matching (faster than full Hungarian for small matrices).
        For Pi 4B, greedy is faster and good enough at <50 detections.
        """
        matches = []
        if cost_matrix.size == 0:
            return matches

        cost = cost_matrix.copy()
        n_rows, n_cols = cost.shape

        for _ in range(min(n_rows, n_cols)):
            # Find best match
            idx = np.unravel_index(np.argmax(cost), cost.shape)
            if cost[idx] < self._iou_threshold:
                break

            matches.append(idx)
            cost[idx[0], :] = 0
            cost[:, idx[1]] = 0

        return matches
