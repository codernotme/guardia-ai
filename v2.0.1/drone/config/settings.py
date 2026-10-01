"""
Guardia AI v2.0.1 — Drone Configuration
========================================
All hardware, AI, flight, and system parameters.
Tuned for Raspberry Pi 4B (8GB RAM) with Pixhawk FC.

No telemetry. No external API calls. Everything offline.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path


@dataclass(frozen=False)
class HardwareConfig:
    """Physical hardware parameters."""
    # --- Pixhawk UART ---
    pixhawk_serial_port: str = "/dev/serial0"
    pixhawk_baud_rate: int = 921600
    mavlink_system_id: int = 1
    mavlink_component_id: int = 191  # MAV_COMP_ID_ONBOARD_COMPUTER

    # --- Camera ---
    camera_resolution: tuple = (1280, 720)
    camera_fps: int = 30
    camera_low_res: tuple = (320, 320)  # For AI inference
    camera_rotation: int = 0
    camera_hflip: bool = False
    camera_vflip: bool = False

    # --- GPS ---
    gps_port: str = ""  # Empty = Pixhawk handles GPS
    gps_baud: int = 38400

    # --- 4G Modem (disabled by default — no telemetry) ---
    modem_enabled: bool = False
    modem_device: str = "/dev/ttyUSB2"
    modem_apn: str = "jionet"

    # --- Power ---
    battery_cells: int = 4  # 4S LiPo
    battery_low_voltage: float = 3.5  # Per cell
    battery_critical_voltage: float = 3.3  # Per cell
    battery_capacity_mah: int = 5200


@dataclass(frozen=False)
class AIConfig:
    """AI model and inference parameters — all offline."""
    # --- Object Detection ---
    detector_model: str = "yolov8n"  # nano for Pi 4B
    detector_format: str = "tflite"  # tflite or ncnn
    detector_input_size: int = 320
    detector_confidence: float = 0.35
    detector_iou_threshold: float = 0.45
    detector_max_detections: int = 20
    detector_fps_target: int = 10  # Inference FPS cap

    # Model paths (relative to drone/ai/models/)
    detector_model_path: str = "yolov8n.tflite"
    person_reid_model_path: str = "osnet_x025.tflite"

    # --- Tracker ---
    tracker_type: str = "bytetrack"
    tracker_max_age: int = 30  # Frames before dropping lost track
    tracker_min_hits: int = 3  # Minimum detections to confirm track
    tracker_iou_threshold: float = 0.3

    # --- Person Re-ID (for tailing) ---
    reid_enabled: bool = True
    reid_similarity_threshold: float = 0.6
    reid_feature_dim: int = 256

    # --- Classes of interest ---
    target_classes: list = field(default_factory=lambda: [
        "person", "car", "truck", "bicycle", "motorcycle",
        "dog", "cat", "backpack", "suitcase"
    ])
    rescue_priority_classes: list = field(default_factory=lambda: [
        "person"
    ])

    # --- No telemetry ---
    telemetry_enabled: bool = False
    analytics_enabled: bool = False
    crash_reporting: bool = False
    usage_tracking: bool = False


@dataclass(frozen=False)
class FlightConfig:
    """Flight control parameters."""
    # --- Follow Mode ---
    follow_max_speed: float = 3.0  # m/s
    follow_min_distance: float = 5.0  # meters
    follow_default_altitude: float = 10.0  # meters
    follow_max_altitude: float = 50.0  # meters
    follow_yaw_p_gain: float = 0.8
    follow_forward_p_gain: float = 0.5
    follow_setpoint_rate_hz: int = 20

    # --- Patrol Mode ---
    patrol_speed: float = 2.0  # m/s
    patrol_altitude: float = 15.0  # meters
    patrol_waypoint_radius: float = 3.0  # meters, acceptance radius

    # --- Search Mode (rescue) ---
    search_pattern: str = "expanding_square"  # or "sector", "parallel"
    search_altitude: float = 20.0
    search_speed: float = 2.0
    search_grid_spacing: float = 15.0  # meters between passes

    # --- Geofence ---
    geofence_radius: float = 150.0  # meters from home
    geofence_max_altitude: float = 50.0
    geofence_action: str = "rtl"  # rtl, land, loiter

    # --- Failsafes ---
    rc_loss_action: str = "rtl"
    gcs_loss_action: str = "hover_then_rtl"
    gcs_loss_hover_time: float = 10.0  # seconds before RTL
    battery_low_action: str = "rtl"
    battery_critical_action: str = "land"
    offboard_loss_timeout: float = 0.5  # seconds before Pixhawk failsafe
    lost_target_hover_time: float = 5.0  # seconds before searching/RTL

    # --- Safety Limits ---
    max_speed: float = 5.0  # m/s absolute
    max_acceleration: float = 2.0  # m/s^2
    max_yaw_rate: float = 45.0  # deg/s
    min_altitude: float = 2.0  # meters


@dataclass(frozen=False)
class VideoConfig:
    """Video streaming and encoding config."""
    # --- Encoding ---
    codec: str = "h264"
    bitrate_kbps: int = 2000
    keyframe_interval: int = 30  # frames (1 second at 30fps)
    profile: str = "baseline"
    use_hw_encoder: bool = True  # Pi 4B hardware H.264

    # --- Streaming (only active if modem enabled) ---
    stream_enabled: bool = False  # Disabled by default — no telemetry
    stream_protocol: str = "srt"
    stream_port: int = 8554

    # --- Recording ---
    record_locally: bool = True
    record_path: str = "/home/pi/guardia/recordings"
    record_max_size_mb: int = 4096  # Auto-rotate at 4GB
    record_format: str = "mp4"


@dataclass(frozen=False)
class DeliveryConfig:
    """Payload delivery system config."""
    delivery_enabled: bool = False
    servo_pin: int = 18  # GPIO pin for servo
    servo_release_angle: int = 90
    servo_lock_angle: int = 0
    delivery_altitude: float = 3.0  # meters above target for drop
    max_payload_weight_g: int = 500  # grams


@dataclass(frozen=False)
class GCSConfig:
    """Ground Control Station config."""
    # --- Backend ---
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # --- Security ---
    secret_key: str = ""  # Generated on first run
    session_timeout_minutes: int = 30
    require_auth: bool = True

    # --- Database ---
    database_url: str = "sqlite:///./guardia_gcs.db"

    # --- MAVLink Connection ---
    mavlink_connection: str = "udpin:0.0.0.0:14550"

    # --- No telemetry ---
    telemetry_to_cloud: bool = False
    analytics_enabled: bool = False


@dataclass(frozen=False)
class SystemConfig:
    """Top-level system configuration."""
    hardware: HardwareConfig = field(default_factory=HardwareConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    flight: FlightConfig = field(default_factory=FlightConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    delivery: DeliveryConfig = field(default_factory=DeliveryConfig)
    gcs: GCSConfig = field(default_factory=GCSConfig)

    # --- System-wide ---
    debug: bool = False
    log_level: str = "INFO"
    log_file: str = "/home/pi/guardia/logs/drone.log"

    # --- Telemetry kill switch ---
    telemetry_global_disable: bool = True  # Master switch — kills ALL outbound data

    @classmethod
    def from_env(cls) -> "SystemConfig":
        """Load config with environment variable overrides."""
        config = cls()

        # Override from environment
        if os.getenv("GUARDIA_DEBUG"):
            config.debug = True
            config.log_level = "DEBUG"

        if os.getenv("GUARDIA_SERIAL_PORT"):
            config.hardware.pixhawk_serial_port = os.getenv("GUARDIA_SERIAL_PORT")

        if os.getenv("GUARDIA_BAUD_RATE"):
            config.hardware.pixhawk_baud_rate = int(os.getenv("GUARDIA_BAUD_RATE"))

        if os.getenv("GUARDIA_MODEM_ENABLED", "").lower() == "true":
            config.hardware.modem_enabled = True
            config.video.stream_enabled = True

        if os.getenv("GUARDIA_DETECTOR_MODEL"):
            config.ai.detector_model_path = os.getenv("GUARDIA_DETECTOR_MODEL")

        # Force no telemetry
        config.ai.telemetry_enabled = False
        config.ai.analytics_enabled = False
        config.ai.crash_reporting = False
        config.ai.usage_tracking = False
        config.gcs.telemetry_to_cloud = False
        config.gcs.analytics_enabled = False
        config.telemetry_global_disable = True

        return config


# Module-level singleton
_config: Optional[SystemConfig] = None


def get_config() -> SystemConfig:
    """Get or create the system configuration singleton."""
    global _config
    if _config is None:
        _config = SystemConfig.from_env()
    return _config


def reset_config() -> None:
    """Reset config (for testing)."""
    global _config
    _config = None
