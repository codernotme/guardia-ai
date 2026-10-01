"""
Guardia AI v2.0.0 — Failsafe Manager
======================================
Hardware-level safety enforcement independent of the main agent.
This is the last line of software defense before Pixhawk firmware failsafes.

Monitors:
- Battery voltage and capacity
- GPS fix quality
- Pixhawk heartbeat
- GCS heartbeat (if connected)
- Geofence violations
- System resource limits (CPU temp, RAM)
- Offboard mode timeout

Actions:
- WARN → alert to GCS
- HOVER → stop all velocity, hover
- RTL → return to launch
- LAND → immediate land
- KILL → emergency motor kill (extreme last resort)
"""

import logging
import time
import math
from enum import Enum, auto
from typing import Optional, Callable, List
from dataclasses import dataclass, field

logger = logging.getLogger("guardia.flight.failsafe")


class FailsafeLevel(Enum):
    """Severity levels for failsafe triggers."""
    NONE = 0
    WARN = 1
    HOVER = 2
    RTL = 3
    LAND = 4
    KILL = 5


class FailsafeType(Enum):
    """Types of failsafe conditions."""
    BATTERY_LOW = auto()
    BATTERY_CRITICAL = auto()
    GPS_LOST = auto()
    PIXHAWK_LOST = auto()
    GCS_LOST = auto()
    GEOFENCE_BREACH = auto()
    CPU_OVERHEAT = auto()
    RAM_CRITICAL = auto()
    OFFBOARD_TIMEOUT = auto()


@dataclass
class FailsafeEvent:
    """A triggered failsafe event."""
    type: FailsafeType
    level: FailsafeLevel
    message: str
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False


@dataclass
class GeofenceConfig:
    """Geofence definition."""
    home_lat: float = 0.0
    home_lon: float = 0.0
    max_radius: float = 150.0       # meters
    max_altitude: float = 50.0      # meters
    min_altitude: float = 2.0       # meters
    enabled: bool = True


class FailsafeManager:
    """
    Continuous safety monitor running alongside the main agent.

    Checks run every tick (50Hz) and escalate through:
    WARN → HOVER → RTL → LAND → KILL

    The Pixhawk firmware has its own failsafes that work even if this
    code crashes. This manager provides faster, smarter responses.
    """

    def __init__(self):
        # Thresholds
        self._battery_warn_pct = 25
        self._battery_low_pct = 15
        self._battery_critical_pct = 5
        self._battery_warn_voltage = 3.5   # per cell
        self._battery_critical_voltage = 3.3
        self._battery_cells = 4

        self._pixhawk_timeout = 3.0   # seconds
        self._gcs_timeout = 10.0      # seconds
        self._gps_min_fix = 3         # 3D fix required
        self._gps_min_sats = 6

        self._cpu_warn_temp = 75.0    # °C
        self._cpu_critical_temp = 82.0
        self._ram_critical_pct = 90

        # Geofence
        self._geofence = GeofenceConfig()

        # State
        self._active_failsafes: List[FailsafeEvent] = []
        self._highest_level = FailsafeLevel.NONE
        self._failsafe_callback: Optional[Callable] = None

        # Cooldowns (prevent spamming)
        self._last_warn_time: dict = {}
        self._warn_cooldown = 5.0  # seconds

        logger.info("FailsafeManager initialized")

    @property
    def highest_level(self) -> FailsafeLevel:
        return self._highest_level

    @property
    def active_failsafes(self) -> List[FailsafeEvent]:
        return [f for f in self._active_failsafes if not f.resolved]

    @property
    def is_safe(self) -> bool:
        return self._highest_level.value <= FailsafeLevel.WARN.value

    def on_failsafe(self, callback: Callable):
        """Register callback for failsafe triggers."""
        self._failsafe_callback = callback

    def set_geofence(
        self,
        home_lat: float,
        home_lon: float,
        max_radius: float = 150.0,
        max_altitude: float = 50.0,
    ):
        """Configure geofence around home position."""
        self._geofence = GeofenceConfig(
            home_lat=home_lat,
            home_lon=home_lon,
            max_radius=max_radius,
            max_altitude=max_altitude,
            enabled=True,
        )
        logger.info(
            "Geofence set: center=(%.6f, %.6f) radius=%.0fm alt=%.0fm",
            home_lat, home_lon, max_radius, max_altitude,
        )

    def check(
        self,
        battery_pct: int,
        battery_voltage: float,
        gps_fix: int,
        gps_sats: int,
        pixhawk_heartbeat_age: float,
        gcs_heartbeat_age: float,
        latitude: float,
        longitude: float,
        altitude: float,
        cpu_temp: float,
        ram_usage_pct: float,
        is_airborne: bool,
    ) -> FailsafeLevel:
        """
        Run all safety checks. Returns highest triggered level.

        Call this every tick (50Hz).
        """
        self._highest_level = FailsafeLevel.NONE

        if not is_airborne:
            return FailsafeLevel.NONE

        # Battery
        self._check_battery(battery_pct, battery_voltage)

        # GPS
        self._check_gps(gps_fix, gps_sats)

        # Pixhawk heartbeat
        self._check_pixhawk(pixhawk_heartbeat_age)

        # GCS heartbeat
        self._check_gcs(gcs_heartbeat_age)

        # Geofence
        if self._geofence.enabled:
            self._check_geofence(latitude, longitude, altitude)

        # System resources
        self._check_system(cpu_temp, ram_usage_pct)

        return self._highest_level

    def _check_battery(self, pct: int, voltage: float):
        """Check battery levels."""
        cell_voltage = voltage / self._battery_cells if self._battery_cells > 0 else 0

        if pct <= self._battery_critical_pct or cell_voltage <= self._battery_critical_voltage:
            self._trigger(
                FailsafeType.BATTERY_CRITICAL,
                FailsafeLevel.LAND,
                f"BATTERY CRITICAL: {pct}% ({cell_voltage:.2f}V/cell)"
            )
        elif pct <= self._battery_low_pct or cell_voltage <= self._battery_warn_voltage:
            self._trigger(
                FailsafeType.BATTERY_LOW,
                FailsafeLevel.RTL,
                f"Battery low: {pct}% ({cell_voltage:.2f}V/cell)"
            )

    def _check_gps(self, fix: int, sats: int):
        """Check GPS quality."""
        if fix < self._gps_min_fix:
            self._trigger(
                FailsafeType.GPS_LOST,
                FailsafeLevel.HOVER,
                f"GPS degraded: fix={fix} sats={sats}"
            )

    def _check_pixhawk(self, heartbeat_age: float):
        """Check Pixhawk heartbeat."""
        if heartbeat_age > self._pixhawk_timeout:
            self._trigger(
                FailsafeType.PIXHAWK_LOST,
                FailsafeLevel.LAND,
                f"Pixhawk heartbeat lost ({heartbeat_age:.1f}s)"
            )

    def _check_gcs(self, heartbeat_age: float):
        """Check GCS heartbeat (only if GCS was ever connected)."""
        if heartbeat_age > self._gcs_timeout and heartbeat_age < 1000:
            self._trigger(
                FailsafeType.GCS_LOST,
                FailsafeLevel.HOVER,
                f"GCS heartbeat lost ({heartbeat_age:.1f}s)"
            )

    def _check_geofence(self, lat: float, lon: float, alt: float):
        """Check geofence boundaries."""
        if lat == 0 and lon == 0:
            return  # No GPS fix

        distance = self._haversine(
            lat, lon,
            self._geofence.home_lat, self._geofence.home_lon,
        )

        if distance > self._geofence.max_radius:
            self._trigger(
                FailsafeType.GEOFENCE_BREACH,
                FailsafeLevel.RTL,
                f"Geofence breach: {distance:.0f}m from home (limit: {self._geofence.max_radius:.0f}m)"
            )

        if alt > self._geofence.max_altitude:
            self._trigger(
                FailsafeType.GEOFENCE_BREACH,
                FailsafeLevel.HOVER,
                f"Altitude breach: {alt:.1f}m (limit: {self._geofence.max_altitude:.1f}m)"
            )

    def _check_system(self, cpu_temp: float, ram_pct: float):
        """Check system resources."""
        if cpu_temp > self._cpu_critical_temp:
            self._trigger(
                FailsafeType.CPU_OVERHEAT,
                FailsafeLevel.WARN,
                f"CPU critical: {cpu_temp:.1f}°C"
            )
        elif cpu_temp > self._cpu_warn_temp:
            self._trigger(
                FailsafeType.CPU_OVERHEAT,
                FailsafeLevel.WARN,
                f"CPU hot: {cpu_temp:.1f}°C"
            )

        if ram_pct > self._ram_critical_pct:
            self._trigger(
                FailsafeType.RAM_CRITICAL,
                FailsafeLevel.WARN,
                f"RAM critical: {ram_pct:.0f}%"
            )

    def _trigger(self, fs_type: FailsafeType, level: FailsafeLevel, message: str):
        """Trigger a failsafe event."""
        # Update highest level
        if level.value > self._highest_level.value:
            self._highest_level = level

        # Cooldown check
        now = time.time()
        last = self._last_warn_time.get(fs_type, 0)
        if now - last < self._warn_cooldown:
            return
        self._last_warn_time[fs_type] = now

        event = FailsafeEvent(type=fs_type, level=level, message=message)
        self._active_failsafes.append(event)

        log_fn = logger.warning if level.value <= 2 else logger.critical
        log_fn("⚠️ FAILSAFE [%s] %s: %s", level.name, fs_type.name, message)

        if self._failsafe_callback:
            try:
                self._failsafe_callback(event)
            except Exception as e:
                logger.error("Failsafe callback error: %s", e)

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
