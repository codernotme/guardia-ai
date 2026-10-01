"""
Guardia AI v2.0.1 — Follow Controller
=======================================
Converts target tracking offsets into velocity commands for the Pixhawk.
Handles follow mode, tail mode, and orbit mode.

PID-controlled with hard safety limits.
Works at 20Hz to keep Pixhawk offboard mode alive.
"""

import logging
import math
import time
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger("guardia.flight.follow")


@dataclass
class PIDState:
    """PID controller state."""
    kp: float = 0.0
    ki: float = 0.0
    kd: float = 0.0
    integral: float = 0.0
    prev_error: float = 0.0
    output: float = 0.0

    # Anti-windup
    integral_limit: float = 1.0
    output_limit: float = 1.0

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0
        self.output = 0.0

    def update(self, error: float, dt: float) -> float:
        """Compute PID output."""
        if dt <= 0:
            return 0.0

        # Proportional
        p = self.kp * error

        # Integral with anti-windup
        self.integral += error * dt
        self.integral = max(-self.integral_limit, min(self.integral_limit, self.integral))
        i = self.ki * self.integral

        # Derivative
        derivative = (error - self.prev_error) / dt
        d = self.kd * derivative
        self.prev_error = error

        # Output with clamping
        self.output = max(-self.output_limit, min(self.output_limit, p + i + d))
        return self.output


class FollowController:
    """
    Converts target tracking data into velocity commands.

    Follow modes:
    1. FOLLOW — standard follow at set distance
    2. TAIL — covert follow at larger distance, smoother movements
    3. ORBIT — circle the target at fixed distance

    Input: target offset from frame center (from tracker)
    Output: velocity commands for Pixhawk (vx, vy, vz, yaw_rate)
    """

    def __init__(
        self,
        max_speed: float = 3.0,
        min_distance: float = 5.0,
        target_altitude: float = 10.0,
        max_yaw_rate: float = 45.0,  # deg/s
        max_acceleration: float = 2.0,
    ):
        self._max_speed = max_speed
        self._min_distance = min_distance
        self._target_altitude = target_altitude
        self._max_yaw_rate = math.radians(max_yaw_rate)
        self._max_accel = max_acceleration

        self._mode = "follow"  # "follow", "tail", "orbit"
        self._tail_distance = 20.0
        self._orbit_radius = 15.0
        self._orbit_speed = 1.0

        # Target size reference (for distance estimation)
        # A person standing is roughly 1.7m tall
        # At 10m altitude and 10m distance, they appear as ~30% of frame height
        self._reference_target_size = 0.30  # Relative height when at desired distance

        # PID controllers
        self._yaw_pid = PIDState(
            kp=0.8, ki=0.05, kd=0.15,
            integral_limit=0.5, output_limit=1.0,
        )
        self._forward_pid = PIDState(
            kp=0.5, ki=0.03, kd=0.1,
            integral_limit=0.5, output_limit=1.0,
        )
        self._lateral_pid = PIDState(
            kp=0.3, ki=0.02, kd=0.08,
            integral_limit=0.3, output_limit=0.5,
        )

        # Smoothing
        self._prev_vx = 0.0
        self._prev_vy = 0.0
        self._prev_yaw_rate = 0.0
        self._last_update_time = 0.0

        # Lost target
        self._target_lost = False
        self._target_lost_time = 0.0

        logger.info(
            "FollowController initialized | max_speed=%.1f min_dist=%.1f alt=%.1f",
            max_speed, min_distance, target_altitude,
        )

    def set_mode(self, mode: str, **kwargs):
        """Set follow mode: follow, tail, or orbit."""
        self._mode = mode
        if mode == "tail":
            self._tail_distance = kwargs.get("distance", 20.0)
            self._reference_target_size = 0.15  # Smaller = farther
            logger.info("Tail mode: distance=%.1fm", self._tail_distance)
        elif mode == "orbit":
            self._orbit_radius = kwargs.get("radius", 15.0)
            self._orbit_speed = kwargs.get("speed", 1.0)
            logger.info("Orbit mode: radius=%.1fm speed=%.1f", self._orbit_radius, self._orbit_speed)
        else:
            self._reference_target_size = 0.30
            logger.info("Follow mode")

        self.reset()

    def reset(self):
        """Reset PID states."""
        self._yaw_pid.reset()
        self._forward_pid.reset()
        self._lateral_pid.reset()
        self._prev_vx = 0.0
        self._prev_vy = 0.0
        self._prev_yaw_rate = 0.0
        self._target_lost = False

    def compute(
        self,
        offset_x: float,
        offset_y: float,
        target_size: float,
        dt: float,
    ) -> Tuple[float, float, float, float]:
        """
        Compute velocity commands from target offset.

        Args:
            offset_x: Horizontal offset from frame center (-1.0 to 1.0)
            offset_y: Vertical offset from frame center (-1.0 to 1.0)
            target_size: Relative size of target bbox (0.0 to 1.0)
            dt: Time since last update (seconds)

        Returns:
            (vx, vy, vz, yaw_rate) velocity commands
            vx: forward (m/s, positive = forward)
            vy: lateral (m/s, positive = right)
            vz: vertical (m/s, positive = down)
            yaw_rate: yaw rate (rad/s, positive = clockwise)
        """
        if dt <= 0:
            return (0, 0, 0, 0)

        self._target_lost = False
        self._target_lost_time = 0.0

        if self._mode == "orbit":
            return self._compute_orbit(offset_x, offset_y, target_size, dt)

        # --- YAW: Turn to keep target centered horizontally ---
        yaw_error = -offset_x  # Negative because we yaw opposite to offset
        yaw_rate = self._yaw_pid.update(yaw_error, dt) * self._max_yaw_rate

        # --- FORWARD/BACK: Adjust distance based on target size ---
        # Larger target = too close, smaller = too far
        size_error = self._reference_target_size - target_size
        forward_speed = self._forward_pid.update(size_error, dt) * self._max_speed

        # --- LATERAL: Small lateral correction ---
        lateral_speed = self._lateral_pid.update(-offset_x, dt) * self._max_speed * 0.3

        # --- VERTICAL: Keep altitude constant (handled by Pixhawk mostly) ---
        vz = 0.0

        # --- Smoothing (prevent jerky movements) ---
        alpha = min(1.0, dt * 5.0)  # Smooth factor
        vx = self._prev_vx + alpha * (forward_speed - self._prev_vx)
        vy = self._prev_vy + alpha * (lateral_speed - self._prev_vy)
        yaw_rate = self._prev_yaw_rate + alpha * (yaw_rate - self._prev_yaw_rate)

        # --- Acceleration limiting ---
        max_dv = self._max_accel * dt
        vx = self._clamp_change(vx, self._prev_vx, max_dv)
        vy = self._clamp_change(vy, self._prev_vy, max_dv)

        # --- Speed clamping ---
        speed = math.sqrt(vx ** 2 + vy ** 2)
        if speed > self._max_speed:
            scale = self._max_speed / speed
            vx *= scale
            vy *= scale

        # Tail mode: reduce speed and smoothness
        if self._mode == "tail":
            vx *= 0.6
            vy *= 0.4
            yaw_rate *= 0.5

        # Save for next iteration
        self._prev_vx = vx
        self._prev_vy = vy
        self._prev_yaw_rate = yaw_rate

        return (vx, vy, vz, yaw_rate)

    def compute_lost_target(self) -> Tuple[float, float, float, float]:
        """Return safe velocity when target is lost (hover/slow down)."""
        if not self._target_lost:
            self._target_lost = True
            self._target_lost_time = time.monotonic()
            logger.warning("Target lost — decelerating")

        # Gradually slow down
        decay = 0.9
        self._prev_vx *= decay
        self._prev_vy *= decay
        self._prev_yaw_rate *= decay

        # Below threshold, stop completely
        if abs(self._prev_vx) < 0.05:
            self._prev_vx = 0.0
        if abs(self._prev_vy) < 0.05:
            self._prev_vy = 0.0
        if abs(self._prev_yaw_rate) < 0.01:
            self._prev_yaw_rate = 0.0

        return (self._prev_vx, self._prev_vy, 0.0, self._prev_yaw_rate)

    @property
    def target_lost_duration(self) -> float:
        """How long the target has been lost (seconds)."""
        if not self._target_lost:
            return 0.0
        return time.monotonic() - self._target_lost_time

    def _compute_orbit(
        self, offset_x: float, offset_y: float, target_size: float, dt: float
    ) -> Tuple[float, float, float, float]:
        """Orbit mode: circle the target."""
        # Keep target to the side while moving forward
        yaw_rate = self._orbit_speed / self._orbit_radius  # rad/s
        vx = self._orbit_speed  # Forward along circle
        vy = 0.0
        vz = 0.0

        # Adjust orbit radius based on target size
        size_error = self._reference_target_size - target_size
        vx += self._forward_pid.update(size_error, dt) * 0.5

        return (vx, vy, vz, yaw_rate)

    @staticmethod
    def _clamp_change(new_val: float, old_val: float, max_change: float) -> float:
        """Limit rate of change."""
        diff = new_val - old_val
        if abs(diff) > max_change:
            return old_val + max_change * (1 if diff > 0 else -1)
        return new_val
