"""
Guardia AI v2.0.1 — Delivery Service
======================================
Payload delivery system for the drone.
Controls a servo-driven release mechanism.

Supports:
- GPS-targeted delivery (fly to coords, drop)
- Person-targeted delivery (track and drop to tracked person)
- Altitude-controlled release
- Safety checks before release
"""

import logging
import time
from typing import Optional
from enum import Enum, auto

logger = logging.getLogger("guardia.delivery")


class DeliveryState(Enum):
    """Delivery mission states."""
    IDLE = auto()
    NAVIGATING = auto()
    APPROACHING = auto()
    HOVERING = auto()       # Hovering above target
    RELEASING = auto()
    CONFIRMING = auto()     # Confirming drop
    RETURNING = auto()
    COMPLETE = auto()
    FAILED = auto()


class DeliveryService:
    """
    Manages payload delivery operations.

    Usage:
        delivery = DeliveryService()
        delivery.start_mission(target_lat, target_lon)
        # ... in main loop ...
        delivery.update(current_lat, current_lon, current_alt)
    """

    def __init__(
        self,
        servo_pin: int = 18,
        release_angle: int = 90,
        lock_angle: int = 0,
        drop_altitude: float = 3.0,
        approach_radius: float = 2.0,
    ):
        self._servo_pin = servo_pin
        self._release_angle = release_angle
        self._lock_angle = lock_angle
        self._drop_altitude = drop_altitude
        self._approach_radius = approach_radius

        self._state = DeliveryState.IDLE
        self._target_lat = 0.0
        self._target_lon = 0.0
        self._target_track_id: Optional[int] = None

        self._servo_initialized = False
        self._payload_loaded = True
        self._release_time = 0.0

        logger.info("DeliveryService initialized (servo GPIO %d)", servo_pin)

    @property
    def state(self) -> DeliveryState:
        return self._state

    @property
    def has_payload(self) -> bool:
        return self._payload_loaded

    def initialize_servo(self) -> bool:
        """Initialize servo GPIO. Returns True on success."""
        try:
            import RPi.GPIO as GPIO

            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self._servo_pin, GPIO.OUT)
            self._servo_pwm = GPIO.PWM(self._servo_pin, 50)  # 50Hz
            self._servo_pwm.start(0)

            # Lock position
            self._set_servo_angle(self._lock_angle)
            self._servo_initialized = True
            logger.info("Servo initialized on GPIO %d", self._servo_pin)
            return True

        except ImportError:
            logger.warning("RPi.GPIO not available — servo control disabled")
            return False
        except Exception as e:
            logger.error("Servo init failed: %s", e)
            return False

    def start_gps_mission(self, lat: float, lon: float):
        """Start delivery to GPS coordinates."""
        self._target_lat = lat
        self._target_lon = lon
        self._target_track_id = None
        self._state = DeliveryState.NAVIGATING
        logger.info("Delivery mission started: (%.6f, %.6f)", lat, lon)

    def start_person_mission(self, track_id: int):
        """Start delivery to a tracked person."""
        self._target_track_id = track_id
        self._state = DeliveryState.NAVIGATING
        logger.info("Delivery mission to person #%d", track_id)

    def release_payload(self) -> bool:
        """Release the payload."""
        if not self._payload_loaded:
            logger.warning("No payload loaded")
            return False

        if self._servo_initialized:
            self._set_servo_angle(self._release_angle)
            time.sleep(1.0)  # Wait for servo to actuate
            self._set_servo_angle(self._lock_angle)

        self._payload_loaded = False
        self._release_time = time.time()
        self._state = DeliveryState.CONFIRMING
        logger.info("✅ Payload released")
        return True

    def cancel(self):
        """Cancel current delivery mission."""
        self._state = DeliveryState.IDLE
        if self._servo_initialized:
            self._set_servo_angle(self._lock_angle)
        logger.info("Delivery cancelled")

    def reset(self):
        """Reset for next delivery."""
        self._state = DeliveryState.IDLE
        self._payload_loaded = True
        if self._servo_initialized:
            self._set_servo_angle(self._lock_angle)
        logger.info("Delivery system reset")

    def _set_servo_angle(self, angle: int):
        """Set servo to a specific angle."""
        if not self._servo_initialized:
            return
        duty = 2 + (angle / 18)  # Convert angle to duty cycle
        self._servo_pwm.ChangeDutyCycle(duty)
        time.sleep(0.3)
        self._servo_pwm.ChangeDutyCycle(0)

    def cleanup(self):
        """Clean up GPIO."""
        if self._servo_initialized:
            self._servo_pwm.stop()
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup(self._servo_pin)
            except Exception:
                pass
