"""
Guardia AI v2.0.0 — Video Pipeline
====================================
Camera capture, dual-stream (main + AI), hardware H.264 encoding,
and local recording. Streaming only enabled when modem is active.

Designed for Pi Camera Module v2/v3 via libcamera/Picamera2.
Falls back to OpenCV for USB cameras or testing.

Memory budget: ~150MB for camera + encoder + buffers
"""

import logging
import time
import threading
import queue
from typing import Optional, Tuple, Callable
from pathlib import Path
from datetime import datetime

import numpy as np

logger = logging.getLogger("guardia.video")


class VideoCapture:
    """
    Dual-stream camera capture for Pi Camera.

    Stream 1 (main): 1280x720 @ 30fps — for recording and streaming
    Stream 2 (low):  320x320 @ 10fps  — for AI inference

    Uses Picamera2 when available, falls back to OpenCV.
    """

    def __init__(
        self,
        resolution: Tuple[int, int] = (1280, 720),
        fps: int = 30,
        low_res: Tuple[int, int] = (320, 320),
        rotation: int = 0,
        hflip: bool = False,
        vflip: bool = False,
    ):
        self._resolution = resolution
        self._fps = fps
        self._low_res = low_res
        self._rotation = rotation
        self._hflip = hflip
        self._vflip = vflip

        self._camera = None
        self._backend = None  # "picamera2" or "opencv"
        self._running = False

        # Frame buffers (thread-safe)
        self._main_frame: Optional[np.ndarray] = None
        self._low_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._frame_count = 0
        self._fps_actual = 0.0
        self._fps_timer = time.monotonic()
        self._fps_count = 0

        # Callbacks
        self._on_frame: Optional[Callable] = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def fps_actual(self) -> float:
        return self._fps_actual

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def initialize(self) -> bool:
        """Initialize camera. Returns True on success."""
        # Try Picamera2 first (Pi Camera)
        try:
            from picamera2 import Picamera2

            self._camera = Picamera2()

            # Configure dual-stream
            config = self._camera.create_preview_configuration(
                main={"size": self._resolution, "format": "RGB888"},
                lores={"size": self._low_res, "format": "RGB888"},
            )
            self._camera.configure(config)

            if self._hflip or self._vflip:
                self._camera.set_controls({
                    "HFlip": self._hflip,
                    "VFlip": self._vflip,
                })

            self._backend = "picamera2"
            logger.info(
                "Camera initialized (Picamera2): main=%s lores=%s @ %dfps",
                self._resolution, self._low_res, self._fps,
            )
            return True

        except (ImportError, RuntimeError) as e:
            logger.warning("Picamera2 not available: %s. Trying OpenCV...", e)

        # Fallback to OpenCV
        try:
            import cv2

            self._camera = cv2.VideoCapture(0)
            if not self._camera.isOpened():
                self._camera = cv2.VideoCapture(-1)

            if self._camera.isOpened():
                self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, self._resolution[0])
                self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self._resolution[1])
                self._camera.set(cv2.CAP_PROP_FPS, self._fps)

                self._backend = "opencv"
                logger.info(
                    "Camera initialized (OpenCV): %s @ %dfps",
                    self._resolution, self._fps,
                )
                return True
            else:
                logger.error("No camera device found")
                return False

        except Exception as e:
            logger.error("Camera initialization failed: %s", e)
            return False

    def start(self):
        """Start camera capture in a background thread."""
        if self._running:
            return

        self._running = True

        if self._backend == "picamera2":
            self._camera.start()
            self._capture_thread = threading.Thread(
                target=self._capture_loop_picamera, daemon=True
            )
        else:
            self._capture_thread = threading.Thread(
                target=self._capture_loop_opencv, daemon=True
            )

        self._capture_thread.start()
        logger.info("Camera capture started")

    def stop(self):
        """Stop camera capture."""
        self._running = False
        if hasattr(self, "_capture_thread"):
            self._capture_thread.join(timeout=2.0)

        if self._camera:
            if self._backend == "picamera2":
                self._camera.stop()
                self._camera.close()
            else:
                self._camera.release()

        logger.info("Camera stopped")

    def get_main_frame(self) -> Optional[np.ndarray]:
        """Get latest main resolution frame."""
        with self._frame_lock:
            return self._main_frame.copy() if self._main_frame is not None else None

    def get_low_frame(self) -> Optional[np.ndarray]:
        """Get latest low-resolution frame for AI inference."""
        with self._frame_lock:
            return self._low_frame.copy() if self._low_frame is not None else None

    def on_frame(self, callback: Callable):
        """Register callback for each new frame."""
        self._on_frame = callback

    def _capture_loop_picamera(self):
        """Capture loop for Picamera2."""
        while self._running:
            try:
                arrays = self._camera.capture_arrays(["main", "lores"])
                main_frame = arrays[0]
                low_frame = arrays[1]

                with self._frame_lock:
                    self._main_frame = main_frame
                    self._low_frame = low_frame
                    self._frame_count += 1

                self._update_fps()

                if self._on_frame:
                    self._on_frame(main_frame, low_frame)

            except Exception as e:
                logger.error("Capture error: %s", e)
                time.sleep(0.1)

    def _capture_loop_opencv(self):
        """Capture loop for OpenCV."""
        import cv2

        while self._running:
            try:
                ret, frame = self._camera.read()
                if not ret:
                    time.sleep(0.01)
                    continue

                # Convert BGR to RGB
                main_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Create low-res version
                low_frame = cv2.resize(
                    main_frame, self._low_res,
                    interpolation=cv2.INTER_LINEAR,
                )

                with self._frame_lock:
                    self._main_frame = main_frame
                    self._low_frame = low_frame
                    self._frame_count += 1

                self._update_fps()

                if self._on_frame:
                    self._on_frame(main_frame, low_frame)

            except Exception as e:
                logger.error("Capture error: %s", e)
                time.sleep(0.1)

    def _update_fps(self):
        """Track actual FPS."""
        self._fps_count += 1
        now = time.monotonic()
        elapsed = now - self._fps_timer
        if elapsed >= 1.0:
            self._fps_actual = self._fps_count / elapsed
            self._fps_count = 0
            self._fps_timer = now


class VideoRecorder:
    """
    Local video recorder using hardware H.264 encoder.
    Records to MP4 files with auto-rotation.
    """

    def __init__(
        self,
        output_dir: str = "/home/pi/guardia/recordings",
        max_file_size_mb: int = 4096,
        resolution: Tuple[int, int] = (1280, 720),
        fps: int = 30,
        bitrate_kbps: int = 2000,
    ):
        self._output_dir = Path(output_dir)
        self._max_file_size = max_file_size_mb * 1024 * 1024
        self._resolution = resolution
        self._fps = fps
        self._bitrate = bitrate_kbps

        self._writer = None
        self._recording = False
        self._current_file: Optional[Path] = None
        self._bytes_written = 0

    def start(self) -> bool:
        """Start recording to a new file."""
        try:
            import cv2

            self._output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._current_file = self._output_dir / f"flight_{timestamp}.mp4"

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self._writer = cv2.VideoWriter(
                str(self._current_file),
                fourcc,
                self._fps,
                self._resolution,
            )

            if self._writer.isOpened():
                self._recording = True
                logger.info("Recording started: %s", self._current_file)
                return True
            else:
                logger.error("Failed to open video writer")
                return False

        except Exception as e:
            logger.error("Recording start failed: %s", e)
            return False

    def write_frame(self, frame: np.ndarray):
        """Write a frame to the recording."""
        if not self._recording or self._writer is None:
            return

        try:
            import cv2
            # Convert RGB to BGR for OpenCV
            bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            self._writer.write(bgr)
        except Exception as e:
            logger.error("Frame write error: %s", e)

    def stop(self):
        """Stop recording."""
        if self._writer:
            self._writer.release()
            self._writer = None
        self._recording = False
        if self._current_file:
            logger.info("Recording saved: %s", self._current_file)

    @property
    def is_recording(self) -> bool:
        return self._recording


class VideoPipeline:
    """
    Complete video pipeline: capture → AI feed → record → (optional stream).

    Coordinates VideoCapture and VideoRecorder.
    Provides frames to the tracker service.
    """

    def __init__(self, config=None):
        self._config = config
        self._capture = VideoCapture()
        self._recorder = VideoRecorder()
        self._running = False

        # AI frame queue (non-blocking, drops old frames)
        self._ai_queue: queue.Queue = queue.Queue(maxsize=3)

    @property
    def capture(self) -> VideoCapture:
        return self._capture

    @property
    def recorder(self) -> VideoRecorder:
        return self._recorder

    def start(self) -> bool:
        """Start the complete video pipeline."""
        if not self._capture.initialize():
            logger.error("Video pipeline failed: camera init error")
            return False

        self._capture.on_frame(self._on_new_frame)
        self._capture.start()

        # Start recording
        self._recorder.start()

        self._running = True
        logger.info("Video pipeline started")
        return True

    def stop(self):
        """Stop the video pipeline."""
        self._running = False
        self._capture.stop()
        self._recorder.stop()
        logger.info("Video pipeline stopped")

    def get_ai_frame(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """Get a low-res frame for AI inference (non-blocking)."""
        try:
            return self._ai_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_display_frame(self) -> Optional[np.ndarray]:
        """Get latest main frame for display/streaming."""
        return self._capture.get_main_frame()

    def _on_new_frame(self, main_frame: np.ndarray, low_frame: np.ndarray):
        """Callback from camera capture."""
        # Record main frame
        if self._recorder.is_recording:
            self._recorder.write_frame(main_frame)

        # Queue low-res for AI (drop old if full)
        try:
            self._ai_queue.put_nowait(low_frame)
        except queue.Full:
            try:
                self._ai_queue.get_nowait()
                self._ai_queue.put_nowait(low_frame)
            except queue.Empty:
                pass
