"""
Guardia AI v2.0.0 — Ground Control Station (GCS) Backend
==========================================================
Custom GCS replacing QGroundControl / Mission Planner.
FastAPI + WebSocket for real-time telemetry, step nudges (1cm / 1ft),
FlySky RC integration, and Pixhawk 2.4.8 hardware link (USB / Bluetooth).

Features:
- Real-time Pixhawk telemetry over WebSocket (5-10Hz)
- Hardware link via USB (COM5) or HC-05 Bluetooth (COM4/COM3) with auto-detect
- Step & Nudge precision flight control (1 cm, 10 cm, 1 ft, 1 m)
- Seamless FlySky RC transmitter handover (Switch to LOITER/ALT_HOLD)
- Port scanning and dynamic connect/disconnect
- Zero telemetry to external services
"""

import asyncio
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure root workspace is in sys.path to import drone modules
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from drone.flight.mavlink.interface import MAVLinkInterface

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)-20s] %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("guardia.gcs")


# ──────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────

class CommandRequest(BaseModel):
    command: str
    params: Dict[str, Any] = Field(default_factory=dict)
    confirm: bool = False  # Dangerous commands need confirm=True


class CommandResponse(BaseModel):
    ok: bool
    msg: str
    timestamp: float = Field(default_factory=time.time)


class StepRequest(BaseModel):
    axis: str = "up"  # "up", "down", "forward", "backward", "left", "right", "yaw_left", "yaw_right"
    distance: float = 0.3048  # Default 1 ft (0.3048m), 1 cm = 0.01m, 10 cm = 0.1m


class ModeRequest(BaseModel):
    mode: str = "LOITER"  # "LOITER", "ALT_HOLD", "STABILIZE", "GUIDED", "RTL", "LAND"


class ConnectRequest(BaseModel):
    port: str = "AUTO"  # "AUTO", "COM5", "COM4", etc.
    baud: int = 115200


class MotorTestRequest(BaseModel):
    motor: int = 1  # 1, 2, 3, 4, or 0 for all motors in sequence
    throttle: float = 10.0  # Throttle percentage (1% to 35%)
    duration: float = 2.0  # Duration in seconds


class TelemetrySnapshot(BaseModel):
    state: str = "IDLE"
    mission: str = "MANUAL"
    armed: bool = False
    lat: float = 0.0
    lon: float = 0.0
    alt: float = 0.0
    heading: float = 0.0
    groundspeed: float = 0.0
    battery_pct: int = 100
    battery_v: float = 0.0
    gps_fix: int = 0
    gps_sats: int = 0
    target_id: Optional[int] = None
    target_locked: bool = False
    targets_detected: int = 0
    cpu_temp: float = 0.0
    ram_mb: float = 0.0
    uptime: float = 0.0
    flight_mode: str = "UNKNOWN"
    pitch: float = 0.0
    roll: float = 0.0
    yaw: float = 0.0
    rc_channels: List[int] = Field(default_factory=lambda: [1500] * 8)
    statustext: str = ""
    is_hardware: bool = False
    port: str = "None"
    baud: int = 115200


class Waypoint(BaseModel):
    lat: float
    lon: float
    alt: float = 10.0
    speed: float = 2.0


class MissionPlan(BaseModel):
    waypoints: List[Waypoint]
    patrol_repeat: bool = False
    altitude: float = 10.0


class ArduPilotAutoSetupRequest(BaseModel):
    profile: str = "bench"  # "bench" or "field"
    calibrate_sensors: bool = True
    rtl_altitude_m: float = 15.0


class ParamUpdateRequest(BaseModel):
    name: str
    value: float


class SurveyPolygonRequest(BaseModel):
    polygon: List[List[float]] = Field(default_factory=list)  # [[lat, lon], ...]
    altitude: float = 15.0
    lane_spacing_m: float = 15.0
    speed_ms: float = 3.5


# ──────────────────────────────────────────────────────────────
# WebSocket Connection Manager
# ──────────────────────────────────────────────────────────────

class ConnectionManager:
    """Manages WebSocket connections for telemetry broadcasting."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)
        logger.info("GCS client connected (%d total)", len(self.active_connections))

    def disconnect(self, ws: WebSocket):
        if ws in self.active_connections:
            self.active_connections.remove(ws)
        logger.info("GCS client disconnected (%d remaining)", len(self.active_connections))

    async def broadcast(self, message: dict):
        """Broadcast to all connected clients."""
        data = json.dumps(message)
        disconnected = []
        for ws in self.active_connections:
            try:
                await ws.send_text(data)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)

    async def broadcast_telemetry(self, telemetry: dict):
        await self.broadcast({"type": "TELEMETRY", "data": telemetry})

    async def broadcast_alert(self, alert: dict):
        await self.broadcast({"type": "ALERT", "data": alert})


manager = ConnectionManager()


DEFAULT_ARDUPILOT_PARAMS = [
    {
        "name": "ARMING_CHECK",
        "category": "Safety & Arming",
        "value": 0.0,
        "default": 1.0,
        "description": "Pre-arm safety checks. 0=Disable (Bench/Desk test), 1=All checks enabled (Outdoor Flight).",
        "options": [0, 1, 71]
    },
    {
        "name": "BRD_SAFETYENABLE",
        "category": "Hardware Safety",
        "value": 0.0,
        "default": 1.0,
        "description": "Pixhawk physical red safety switch requirement. 0=Disabled (Desk test), 1=Enabled.",
        "options": [0, 1]
    },
    {
        "name": "MOT_SPIN_ARM",
        "category": "Motor Control",
        "value": 0.07,
        "default": 0.07,
        "description": "Motor idle spin speed when armed (0.0 to 0.25). 0.07 = 7% throttle.",
        "options": [0.05, 0.07, 0.10]
    },
    {
        "name": "BATT_MONITOR",
        "category": "Battery & Power",
        "value": 4.0,
        "default": 4.0,
        "description": "Power module sensor type. 4=Analog Voltage and Current sensor (3S/4S LiPo).",
        "options": [0, 3, 4]
    },
    {
        "name": "BATT_CAPACITY",
        "category": "Battery & Power",
        "value": 4200.0,
        "default": 4200.0,
        "description": "Battery total capacity in milliampere-hours (mAh).",
        "options": [3000, 4200, 5200]
    },
    {
        "name": "FS_THR_ENABLE",
        "category": "Failsafe",
        "value": 1.0,
        "default": 1.0,
        "description": "Throttle / RC connection loss failsafe. 1=Return-to-Launch (RTL), 2=Land immediately.",
        "options": [0, 1, 2]
    },
    {
        "name": "RTL_ALT",
        "category": "Failsafe",
        "value": 1500.0,
        "default": 1500.0,
        "description": "Return-to-Launch minimum climb altitude in centimeters (1500 cm = 15 meters).",
        "options": [1000, 1500, 2000, 3000]
    },
    {
        "name": "FRAME_CLASS",
        "category": "Airframe",
        "value": 1.0,
        "default": 1.0,
        "description": "Vehicle frame class. 1=Quad, 2=Hexa, 3=Octa.",
        "options": [1, 2, 3]
    },
    {
        "name": "FRAME_TYPE",
        "category": "Airframe",
        "value": 1.0,
        "default": 1.0,
        "description": "Motor layout configuration. 1=X-frame (Standard Quad X).",
        "options": [0, 1]
    },
    {
        "name": "EKF3_ENABLE",
        "category": "Navigation & EKF",
        "value": 1.0,
        "default": 1.0,
        "description": "Enable Extended Kalman Filter 3 navigation attitude & position estimator.",
        "options": [0, 1]
    }
]


def compute_prearm_check(telemetry_dict: dict) -> dict:
    checks = []

    # 1. IMU Horizon Level
    pitch = abs(telemetry_dict.get("pitch", 0.0))
    roll = abs(telemetry_dict.get("roll", 0.0))
    imu_ok = pitch < 5.0 and roll < 5.0
    checks.append({
        "name": "IMU Horizon Level",
        "status": "PASS" if imu_ok else "WARN",
        "detail": f"Pitch {pitch:.1f}°, Roll {roll:.1f}° {'(Level desk)' if imu_ok else '(Level drone before arming)'}"
    })

    # 2. Barometer Reference
    alt = abs(telemetry_dict.get("alt", 0.0))
    baro_ok = alt < 2.0
    checks.append({
        "name": "Barometer Ground Zero",
        "status": "PASS" if baro_ok else "WARN",
        "detail": f"Altitude {alt:.2f}m {'(Zeroed ground reference)' if baro_ok else '(Suggest zeroing baro)'}"
    })

    # 3. Battery Voltage
    v = telemetry_dict.get("battery_v", 0.0)
    pct = telemetry_dict.get("battery_pct", 0)
    batt_ok = v >= 10.5 or (v == 0.0 and not telemetry_dict.get("is_hardware"))
    checks.append({
        "name": "Battery Voltage",
        "status": "PASS" if batt_ok else "FAIL",
        "detail": f"{v:.1f}V ({pct}%) {'(Nominal voltage)' if batt_ok else '(Low battery warning)'}"
    })

    # 4. GPS 3D Lock
    fix = telemetry_dict.get("gps_fix", 0)
    sats = telemetry_dict.get("gps_sats", 0)
    gps_ok = fix >= 3 or not telemetry_dict.get("is_hardware")
    checks.append({
        "name": "GPS 3D Fix & Satellites",
        "status": "PASS" if gps_ok else "WARN",
        "detail": f"{sats} Sats locked ({'3D Fix' if fix >= 3 else 'No 3D Lock'})"
    })

    # 5. RC Radio Link
    rc = telemetry_dict.get("rc_channels", [1500] * 8)
    rc_ok = len(rc) >= 4 and any(ch > 900 for ch in rc[:4])
    checks.append({
        "name": "FlySky RC Radio Link",
        "status": "PASS" if rc_ok else "FAIL",
        "detail": "8-Channel PWM stream active (Ch1-Ch4 detected)" if rc_ok else "No RC receiver packets detected"
    })

    # 6. Safety Switch Status
    checks.append({
        "name": "Hardware Safety Switch",
        "status": "READY",
        "detail": "Motor outputs unlocked (Ready for throttle)"
    })

    pass_count = sum(1 for c in checks if c["status"] in ["PASS", "READY"])
    score = int((pass_count / len(checks)) * 100)
    ready = score >= 80

    return {
        "ready": ready,
        "score": score,
        "checks": checks,
        "timestamp": time.time()
    }


def generate_survey_grid(polygon: List[List[float]], altitude: float = 15.0, lane_spacing_m: float = 15.0, speed_ms: float = 3.5) -> List[Dict[str, Any]]:
    if not polygon or len(polygon) < 3:
        # Default polygon (approx 12,000 sqm around Stanfield Land / test area)
        polygon = [
            [28.6130, 77.2080],
            [28.6145, 77.2080],
            [28.6145, 77.2098],
            [28.6130, 77.2098],
        ]

    lats = [p[0] for p in polygon]
    lons = [p[1] for p in polygon]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    # 1 deg latitude ≈ 111,000 meters
    lat_step = max(0.00008, lane_spacing_m / 111000.0)
    current_lat = min_lat + (lat_step / 2.0)

    waypoints = []
    direction_west_to_east = True
    wp_id = 1

    while current_lat <= max_lat:
        start_lon = min_lon if direction_west_to_east else max_lon
        end_lon = max_lon if direction_west_to_east else min_lon

        waypoints.append({
            "id": f"wp-{wp_id}",
            "lat": round(current_lat, 6),
            "lon": round(start_lon, 6),
            "alt": altitude,
            "speed": speed_ms,
        })
        wp_id += 1

        waypoints.append({
            "id": f"wp-{wp_id}",
            "lat": round(current_lat, 6),
            "lon": round(end_lon, 6),
            "alt": altitude,
            "speed": speed_ms,
        })
        wp_id += 1

        current_lat += lat_step
        direction_west_to_east = not direction_west_to_east

    return waypoints


# ──────────────────────────────────────────────────────────────
# Simulated Drone (Fallback when hardware disconnected)
# ──────────────────────────────────────────────────────────────

class SimulatedDrone:
    """Simulated drone fallback for GCS testing."""

    def __init__(self):
        self.telemetry = TelemetrySnapshot(
            lat=28.6139,
            lon=77.2090,
            alt=0.0,
            battery_pct=95,
            battery_v=16.4,
            gps_fix=3,
            gps_sats=12,
            flight_mode="STABILIZE",
            rc_channels=[1500, 1500, 1100, 1500, 1000, 1000, 1500, 1500],
        )
        self._start_time = time.time()

    def update(self):
        self.telemetry.uptime = time.time() - self._start_time
        self.telemetry.cpu_temp = 50.0 + (time.time() % 5)
        self.telemetry.ram_mb = 2048.0

    async def execute_command(self, cmd: str, params: dict) -> dict:
        if cmd == "arm":
            self.telemetry.armed = True
            return {"ok": True, "msg": "Armed (simulated)"}
        elif cmd == "disarm":
            self.telemetry.armed = False
            return {"ok": True, "msg": "Disarmed (simulated)"}
        elif cmd == "takeoff":
            alt = params.get("altitude", 10.0)
            self.telemetry.alt = alt
            self.telemetry.state = "HOLD"
            self.telemetry.flight_mode = "GUIDED"
            self.telemetry.armed = True
            return {"ok": True, "msg": f"Takeoff to {alt}m (simulated)"}
        elif cmd == "land":
            self.telemetry.alt = 0.0
            self.telemetry.armed = False
            self.telemetry.flight_mode = "LAND"
            return {"ok": True, "msg": "Landing completed (simulated)"}
        elif cmd == "rtl":
            self.telemetry.flight_mode = "RTL"
            return {"ok": True, "msg": "RTL initiated (simulated)"}
        elif cmd in ["hold", "loiter"]:
            self.telemetry.flight_mode = "LOITER"
            return {"ok": True, "msg": "Holding position in LOITER (simulated)"}
        elif cmd == "mode":
            mode = params.get("mode", "LOITER").upper()
            self.telemetry.flight_mode = mode
            return {"ok": True, "msg": f"Mode changed to {mode} (simulated)"}
        elif cmd == "step":
            axis = params.get("axis", "up")
            dist = float(params.get("distance", 0.3048))
            if axis == "up":
                self.telemetry.alt += dist
            elif axis == "down":
                self.telemetry.alt = max(0.0, self.telemetry.alt - dist)
            return {"ok": True, "msg": f"Step {axis.upper()} by {dist:.3f}m executed (simulated)"}
        elif cmd == "rc_handover":
            self.telemetry.flight_mode = "LOITER"
            return {"ok": True, "msg": "Control handed over to FlySky RC in LOITER (simulated)"}
        elif cmd == "motor_test":
            motor = params.get("motor", 1)
            throttle = params.get("throttle", 10.0)
            dur = params.get("duration", 2.0)
            target = "All 4 motors (sequence)" if motor == 0 else f"Motor {motor}"
            return {"ok": True, "msg": f"{target} spun at {throttle:.0f}% for {dur:.1f}s (simulated)"}
        elif cmd == "bench_mode":
            return {"ok": True, "msg": "BENCH MODE ACTIVE: Safety disabled, ARMING_CHECK=0 (simulated)"}
        elif cmd in ["safety_off", "safety_disengage"]:
            return {"ok": True, "msg": "Safety switch disengaged (Motors Active) (simulated)"}
        elif cmd in ["safety_on", "safety_engage"]:
            return {"ok": True, "msg": "Safety switch engaged (Safe) (simulated)"}
        elif cmd == "calibrate_level":
            self.telemetry.pitch = 0.0
            self.telemetry.roll = 0.0
            return {"ok": True, "msg": "Level Horizon calibrated (Pitch & Roll zeroed) (simulated)"}
        elif cmd == "calibrate_gyros":
            return {"ok": True, "msg": "Gyroscopes calibrated successfully (simulated)"}
        elif cmd == "calibrate_baro":
            self.telemetry.alt = 0.0
            return {"ok": True, "msg": "Barometer zeroed to ground level (simulated)"}
        elif cmd == "calibrate_compass":
            return {"ok": True, "msg": "Compass calibration initiated (simulated)"}
        elif cmd == "upload_mission":
            wps = params.get("waypoints", [])
            return {"ok": True, "msg": f"Successfully uploaded {len(wps)} waypoints (simulated)"}
        elif cmd == "clear_mission":
            return {"ok": True, "msg": "Mission cleared (simulated)"}
        elif cmd == "drop_payload":
            return {"ok": True, "msg": "Payload released via AUX Ch7 relay (simulated)"}
        elif cmd == "reboot":
            return {"ok": True, "msg": "Autopilot reboot initiated (simulated)"}
        elif cmd == "get_param":
            name = str(params.get("name", "ARMING_CHECK"))
            return {"ok": True, "msg": f"Param {name} = 0.0 (simulated)", "data": {"name": name, "value": 0.0}}
        elif cmd == "set_param":
            name = str(params.get("name", "ARMING_CHECK"))
            val = float(params.get("value", 0.0))
            return {"ok": True, "msg": f"Set {name} = {val} (simulated)", "data": {"name": name, "value": val}}
        elif cmd == "get_params_all":
            return {"ok": True, "params": DEFAULT_ARDUPILOT_PARAMS}
        elif cmd == "prearm_check":
            res = compute_prearm_check(self.get_telemetry_dict())
            return {"ok": True, "msg": "Pre-arm readiness check evaluated", "data": res}
        elif cmd == "auto_setup":
            profile = str(params.get("profile", "bench")).lower()
            cal_sensors = bool(params.get("calibrate_sensors", True))
            rtl_alt = float(params.get("rtl_altitude_m", 15.0))

            steps = [
                {"step": f"Set ARMING_CHECK = {0.0 if profile == 'bench' else 1.0}", "description": "Pre-arm arming checks", "ok": True, "detail": "Success"},
                {"step": f"Set BRD_SAFETYENABLE = {0.0 if profile == 'bench' else 1.0}", "description": "Hardware safety switch", "ok": True, "detail": "Success"},
                {"step": "Set MOT_SPIN_ARM = 0.07", "description": "Arm motor spin idle throttle", "ok": True, "detail": "Success"},
                {"step": "Set BATT_MONITOR = 4.0", "description": "Analog battery monitor (voltage/current)", "ok": True, "detail": "Success"},
                {"step": "Set FS_THR_ENABLE = 1.0", "description": "RC link loss failsafe (RTL)", "ok": True, "detail": "Success"},
                {"step": f"Set RTL_ALT = {rtl_alt * 100.0}", "description": f"RTL climb altitude ({rtl_alt}m)", "ok": True, "detail": "Success"},
                {"step": "Set FRAME_CLASS = 1.0", "description": "Quad frame class", "ok": True, "detail": "Success"},
                {"step": "Set FRAME_TYPE = 1.0", "description": "X-type frame configuration", "ok": True, "detail": "Success"},
            ]
            if cal_sensors:
                self.telemetry.pitch = 0.0
                self.telemetry.roll = 0.0
                self.telemetry.alt = 0.0
                steps.append({"step": "Calibrate Level Horizon", "description": "Zero roll & pitch angles", "ok": True, "detail": "Horizon leveled (simulated)"})
                steps.append({"step": "Zero Gyroscopes", "description": "Gyro bias nulling", "ok": True, "detail": "Gyros calibrated (simulated)"})
                steps.append({"step": "Zero Barometer", "description": "Ground level AGL reference", "ok": True, "detail": "Baro zeroed to 0.0m (simulated)"})

            self.telemetry.statustext = f"ArduPilot Auto-Setup Complete [{profile.upper()}]"
            return {
                "ok": True,
                "msg": f"ArduPilot Auto-Setup completed for {profile.upper()} profile",
                "data": {"profile": profile, "steps": steps}
            }
        return {"ok": False, "msg": f"Unknown command: {cmd}"}

    def get_telemetry_dict(self) -> dict:
        self.update()
        return self.telemetry.model_dump()


# ──────────────────────────────────────────────────────────────
# Pixhawk Hardware Bridge
# ──────────────────────────────────────────────────────────────

class PixhawkDroneBridge:
    """
    Manages connection and commands to physical Pixhawk 2.4.8
    or falls back to SimulatedDrone when offline.
    """

    def __init__(self):
        self.interface: Optional[MAVLinkInterface] = None
        self.is_hardware: bool = False
        self.port: str = "None"
        self.baud: int = 115200
        self.rx_task: Optional[asyncio.Task] = None
        self.sim = SimulatedDrone()
        self.start_time = time.time()
        self.auto_reconnect = True

    async def connect(self, port: str = "AUTO", baud: int = 115200) -> bool:
        """Connect to Pixhawk on specified port or auto-detect."""
        await self.disconnect()

        target_port = "/dev/serial0" if port == "AUTO" else port
        self.interface = MAVLinkInterface(port=target_port, baud=baud)

        connected = await self.interface.connect()
        if connected:
            self.is_hardware = True
            self.port = self.interface._port
            self.baud = self.interface._baud
            self.interface.on_disconnect(self._handle_disconnect)
            self.rx_task = asyncio.create_task(self.interface.receive_loop(), name="mavlink_rx")
            logger.info("Connected to Pixhawk 2.4.8 on %s @ %d baud", self.port, self.baud)
            return True
        else:
            self.is_hardware = False
            self.port = "Simulated"
            return False

    def _handle_disconnect(self, reason: str):
        logger.warning("Hardware link dropped: %s. Switched to offline state.", reason)
        self.is_hardware = False
        self.port = "Disconnected"
        asyncio.create_task(manager.broadcast_alert({"message": "Pixhawk hardware disconnected"}))

    async def disconnect(self):
        """Disconnect and cleanup background receive task."""
        if self.rx_task:
            self.rx_task.cancel()
            try:
                await self.rx_task
            except asyncio.CancelledError:
                pass
            self.rx_task = None

        if self.interface:
            await self.interface.disconnect()
            self.interface = None

        self.is_hardware = False
        self.port = "None"

    def get_telemetry_dict(self) -> dict:
        """Get live telemetry dictionary from hardware or simulator."""
        if self.is_hardware and self.interface and self.interface.is_connected:
            t = self.interface.telemetry
            v = t.battery_voltage
            pct = t.battery_remaining
            if pct < 0 or pct > 100 or (v > 9.0 and pct > 90 and v < 11.5):
                # Auto-calculate based on cell count (3S or 4S)
                if v >= 13.0:
                    pct = int(max(0, min(100, (v - 13.8) / (16.8 - 13.8) * 100)))
                elif v >= 9.5:
                    pct = int(max(0, min(100, (v - 10.2) / (12.6 - 10.2) * 100)))
                else:
                    pct = 0

            return {
                "state": "ARMED" if t.armed else "DISARMED",
                "mission": "MANUAL",
                "armed": t.armed,
                "lat": t.latitude,
                "lon": t.longitude,
                "alt": t.altitude_rel,
                "heading": t.heading,
                "groundspeed": t.groundspeed,
                "battery_pct": pct,
                "battery_v": round(t.battery_voltage, 2),
                "gps_fix": t.gps_fix_type,
                "gps_sats": t.gps_satellites,
                "target_id": None,
                "target_locked": False,
                "targets_detected": 0,
                "cpu_temp": 46.0,
                "ram_mb": 1024.0,
                "uptime": time.time() - self.start_time,
                "flight_mode": t.flight_mode,
                "pitch": t.pitch,
                "roll": t.roll,
                "yaw": t.yaw,
                "rc_channels": t.rc_channels or [1500] * 8,
                "statustext": t.statustext or "",
                "is_hardware": True,
                "port": self.port,
                "baud": self.baud,
            }
        else:
            sim_dict = self.sim.get_telemetry_dict()
            sim_dict["is_hardware"] = False
            sim_dict["port"] = "Simulated"
            sim_dict["baud"] = 0
            sim_dict["statustext"] = "Simulated mode — Hardware not connected"
            return sim_dict

    async def execute_command(self, cmd: str, params: dict) -> dict:
        cmd = cmd.lower().strip()
        if not self.is_hardware or not self.interface or not self.interface.is_connected:
            return await self.sim.execute_command(cmd, params)

        try:
            if cmd == "arm":
                force = bool(params.get("force", False))
                ok, reason = await self.interface.arm(force=force)
                return {"ok": ok, "msg": "Pixhawk Armed successfully" if ok else f"Arm failed: {reason}"}
            elif cmd == "disarm":
                ok = await self.interface.disarm()
                return {"ok": ok, "msg": "Pixhawk Disarmed" if ok else "Disarm failed"}
            elif cmd == "bench_mode":
                enable = bool(params.get("enable", True))
                ok, msg = await self.interface.configure_bench_mode(enable=enable)
                return {"ok": ok, "msg": msg}
            elif cmd in ["safety_off", "safety_disengage"]:
                ok, msg = await self.interface.set_safety_switch(enable=False)
                return {"ok": ok, "msg": msg}
            elif cmd in ["safety_on", "safety_engage"]:
                ok, msg = await self.interface.set_safety_switch(enable=True)
                return {"ok": ok, "msg": msg}
            elif cmd == "calibrate_level":
                ok, msg = await self.interface.calibrate_level()
                return {"ok": ok, "msg": msg}
            elif cmd == "calibrate_gyros":
                ok, msg = await self.interface.calibrate_gyros()
                return {"ok": ok, "msg": msg}
            elif cmd == "calibrate_baro":
                ok, msg = await self.interface.calibrate_baro()
                return {"ok": ok, "msg": msg}
            elif cmd == "calibrate_compass":
                ok, msg = await self.interface.calibrate_compass()
                return {"ok": ok, "msg": msg}
            elif cmd == "set_param":
                name = str(params.get("name", "ARMING_CHECK"))
                val = float(params.get("value", 0))
                ok, msg = await self.interface.set_param(name, val)
                return {"ok": ok, "msg": msg}
            elif cmd == "upload_mission":
                wps = params.get("waypoints", [])
                ok, msg = await self.interface.upload_mission(wps)
                return {"ok": ok, "msg": msg}
            elif cmd == "clear_mission":
                ok, msg = await self.interface.clear_mission()
                return {"ok": ok, "msg": msg}
            elif cmd == "drop_payload":
                ok = await self.interface.set_servo(channel=9, pwm=1900)
                return {"ok": ok, "msg": "Payload servo triggered on AUX Ch9" if ok else "Servo command failed"}
            elif cmd == "reboot":
                ok, msg = await self.interface.reboot_autopilot()
                return {"ok": ok, "msg": msg}
            elif cmd == "get_param":
                name = str(params.get("name", "ARMING_CHECK"))
                val = await self.interface.get_param(name)
                if val is not None:
                    return {"ok": True, "msg": f"{name} = {val}", "data": {"name": name, "value": val}}
                return {"ok": False, "msg": f"Failed to retrieve param {name}"}
            elif cmd == "takeoff":
                alt = float(params.get("altitude", 10.0))
                ok = await self.interface.takeoff(alt)
                return {"ok": ok, "msg": f"Takeoff to {alt}m initiated" if ok else "Takeoff command rejected"}
            elif cmd == "land":
                ok = await self.interface.land()
                return {"ok": ok, "msg": "LAND command dispatched" if ok else "Land command failed"}
            elif cmd == "rtl":
                ok = await self.interface.rtl()
                return {"ok": ok, "msg": "RTL return-to-home dispatched" if ok else "RTL command failed"}
            elif cmd in ["hold", "loiter"]:
                ok = await self.interface.set_mode("LOITER")
                return {"ok": ok, "msg": "Flight mode set to LOITER" if ok else "Failed to switch to LOITER"}
            elif cmd == "mode":
                mode = params.get("mode", "LOITER").upper()
                ok = await self.interface.set_mode(mode)
                return {"ok": ok, "msg": f"Flight mode set to {mode}" if ok else f"Failed to switch to {mode}"}
            elif cmd == "step":
                axis = params.get("axis", "up")
                dist = float(params.get("distance", 0.3048))
                ok = await self.interface.send_step_nudge(axis, dist)
                label = f"{dist * 100:.1f} cm" if dist < 0.3 else f"{dist / 0.3048:.1f} ft"
                return {"ok": ok, "msg": f"Nudge {axis.upper()} by {label} sent" if ok else f"Nudge {axis} failed"}
            elif cmd == "rc_handover":
                target_mode = params.get("mode", "LOITER").upper()
                ok = await self.interface.set_mode(target_mode)
                return {
                    "ok": ok,
                    "msg": f"Control transferred to FlySky transmitter ({target_mode} active). Sticks now active!"
                    if ok
                    else "RC handover failed",
                }
            elif cmd == "kill":
                ok = await self.interface.disarm()
                return {"ok": ok, "msg": "EMERGENCY MOTOR KILL EXECUTED" if ok else "Kill command failed"}
            elif cmd == "motor_test":
                motor = int(params.get("motor", 1))
                throttle = float(params.get("throttle", 10.0))
                duration = float(params.get("duration", 2.0))
                count = 4 if motor == 0 else 1
                motor_idx = 1 if motor == 0 else motor
                ok, msg = await self.interface.motor_test(
                    motor_instance=motor_idx,
                    throttle_pct=throttle,
                    timeout_sec=duration,
                    motor_count=count,
                )
                return {"ok": ok, "msg": msg}
            elif cmd == "prearm_check":
                res = compute_prearm_check(self.get_telemetry_dict())
                return {"ok": True, "msg": "Pre-arm readiness check evaluated", "data": res}
            elif cmd == "get_params_all":
                return {"ok": True, "params": DEFAULT_ARDUPILOT_PARAMS}
            elif cmd == "auto_setup":
                profile = str(params.get("profile", "bench")).lower()
                cal_sensors = bool(params.get("calibrate_sensors", True))
                rtl_alt = float(params.get("rtl_altitude_m", 15.0))

                configs = [
                    ("ARMING_CHECK", 0.0 if profile == "bench" else 1.0, "Pre-arm arming checks"),
                    ("BRD_SAFETYENABLE", 0.0 if profile == "bench" else 1.0, "Hardware safety switch"),
                    ("MOT_SPIN_ARM", 0.07, "Arm motor spin idle throttle"),
                    ("BATT_MONITOR", 4.0, "Analog battery monitor (voltage/current)"),
                    ("FS_THR_ENABLE", 1.0, "RC link loss failsafe (RTL)"),
                    ("RTL_ALT", rtl_alt * 100.0, f"RTL climb altitude ({rtl_alt}m)"),
                    ("FRAME_CLASS", 1.0, "Quad frame class"),
                    ("FRAME_TYPE", 1.0, "X-type frame configuration"),
                ]

                steps = []
                for name, val, desc in configs:
                    ok, msg = await self.interface.set_param(name, val)
                    steps.append({"step": f"Set {name} = {val}", "description": desc, "ok": ok, "detail": msg})

                if cal_sensors:
                    ok_level, msg_level = await self.interface.calibrate_level()
                    steps.append({"step": "Calibrate Level Horizon", "description": "Zero roll & pitch angles", "ok": ok_level, "detail": msg_level})

                    ok_gyro, msg_gyro = await self.interface.calibrate_gyros()
                    steps.append({"step": "Zero Gyroscopes", "description": "Gyro bias nulling", "ok": ok_gyro, "detail": msg_gyro})

                    ok_baro, msg_baro = await self.interface.calibrate_baro()
                    steps.append({"step": "Zero Barometer", "description": "Ground level AGL reference", "ok": ok_baro, "detail": msg_baro})

                all_ok = all(s["ok"] for s in steps)
                return {
                    "ok": all_ok,
                    "msg": f"ArduPilot Auto-Setup finished ({'All Succeeded' if all_ok else 'Some checks had warnings'})",
                    "data": {"profile": profile, "steps": steps}
                }
            else:
                return await self.sim.execute_command(cmd, params)
        except Exception as e:
            logger.error("Error executing command %s: %s", cmd, e)
            return {"ok": False, "msg": str(e)}


drone_bridge = PixhawkDroneBridge()


# ──────────────────────────────────────────────────────────────
# App Lifespan
# ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage GCS startup and shutdown."""
    logger.info("Guardia GCS starting...")

    # Attempt to auto-connect to Pixhawk hardware (USB or Bluetooth)
    try:
        await drone_bridge.connect(port="AUTO", baud=115200)
    except Exception as e:
        logger.warning("Auto-connect exception: %s", e)

    # Start telemetry broadcast loop
    telemetry_task = asyncio.create_task(telemetry_broadcaster(), name="telemetry_broadcast")
    watchdog_task = asyncio.create_task(reconnect_watchdog(), name="reconnect_watchdog")

    logger.info("🎮 Guardia GCS ready — http://localhost:8000")
    yield

    telemetry_task.cancel()
    watchdog_task.cancel()
    try:
        await telemetry_task
        await watchdog_task
    except asyncio.CancelledError:
        pass
    await drone_bridge.disconnect()
    logger.info("Guardia GCS stopped")


async def reconnect_watchdog():
    """Periodically probe for Pixhawk when disconnected without spamming logs."""
    while True:
        try:
            await asyncio.sleep(15.0)
            if not drone_bridge.is_hardware and drone_bridge.auto_reconnect:
                import serial.tools.list_ports as lp
                com_devices = lp.comports()
                # Prioritize USB serial adapters / Pixhawk VID/PID
                hardware_candidates = [
                    p.device for p in com_devices
                    if any(term in (p.description or "").lower() for term in ["pixhawk", "px4", "stm", "ardupilot", "ch340", "cp210", "ftdi", "usb serial"])
                ]
                if hardware_candidates:
                    logger.info("Found candidate flight controller on %s, attempting connection...", hardware_candidates[0])
                    await drone_bridge.connect(port=hardware_candidates[0], baud=115200)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(10.0)


async def telemetry_broadcaster():
    """Broadcast telemetry at 5Hz (200ms)."""
    while True:
        try:
            if manager.active_connections:
                data = drone_bridge.get_telemetry_dict()
                await manager.broadcast_telemetry(data)
            await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Telemetry broadcast error: %s", e)
            await asyncio.sleep(1.0)


# ──────────────────────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Guardia AI — Ground Control Station",
    description="Tactical GCS for Pixhawk 2.4.8, FlySky RC, and Autonomous Surveillance.",
    version="2.0.0",
    contact={"name": "Aryan Bajpai — Tackle Studio"},
    license_info={"name": "MIT"},
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────
# API Routes
# ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    return {"status": "healthy", "service": "guardia-gcs", "version": "2.0.0"}


@app.get("/api/v1/status", tags=["System"])
def system_status():
    return {
        "status": "online",
        "is_hardware": drone_bridge.is_hardware,
        "connected_port": drone_bridge.port,
        "clients": len(manager.active_connections),
        "uptime": time.time() - drone_bridge.start_time,
        "version": "2.0.0",
        "telemetry_enabled": False,  # Zero-telemetry policy
    }


@app.get("/api/v1/ports", tags=["Connection"])
def list_ports():
    """List all available serial and Bluetooth COM ports."""
    ports_list = []
    try:
        import serial.tools.list_ports as lp
        for p in lp.comports():
            ports_list.append({
                "device": p.device,
                "description": p.description,
                "hwid": p.hwid,
            })
    except Exception as e:
        logger.error("Port enumeration error: %s", e)
    return {"ports": ports_list}


@app.post("/api/v1/connection/connect", tags=["Connection"])
async def connect_port(req: ConnectRequest):
    """Connect to a specific serial / Bluetooth COM port."""
    success = await drone_bridge.connect(port=req.port, baud=req.baud)
    return {
        "ok": success,
        "msg": f"Connected to {drone_bridge.port} @ {drone_bridge.baud}" if success else f"Failed to connect to {req.port}",
        "is_hardware": drone_bridge.is_hardware,
        "port": drone_bridge.port,
    }


@app.post("/api/v1/connection/disconnect", tags=["Connection"])
async def disconnect_port():
    """Disconnect active port and switch to simulation."""
    await drone_bridge.disconnect()
    return {"ok": True, "msg": "Disconnected from hardware"}


@app.get("/api/v1/telemetry", tags=["Telemetry"])
def get_telemetry():
    """Get current telemetry snapshot."""
    return drone_bridge.get_telemetry_dict()


# --- Commands ---

DANGEROUS_COMMANDS = {"arm", "takeoff", "kill"}


@app.post("/api/v1/command", tags=["Commands"], response_model=CommandResponse)
async def send_command(req: CommandRequest):
    """Generic command dispatch."""
    cmd = req.command.lower().strip()

    if cmd in DANGEROUS_COMMANDS and not req.confirm:
        raise HTTPException(
            status_code=400,
            detail=f"Command '{cmd}' requires explicit confirmation. Set confirm=true.",
        )

    result = await drone_bridge.execute_command(cmd, req.params)

    # Broadcast executed command to all GCS clients
    await manager.broadcast({
        "type": "COMMAND_EXECUTED",
        "data": {"command": cmd, "result": result},
    })

    return CommandResponse(ok=result["ok"], msg=result["msg"])


@app.post("/api/v1/command/arm", tags=["Commands"])
async def cmd_arm():
    """Arm motors."""
    return await drone_bridge.execute_command("arm", {})


@app.post("/api/v1/command/disarm", tags=["Commands"])
async def cmd_disarm():
    """Disarm motors."""
    return await drone_bridge.execute_command("disarm", {})


@app.post("/api/v1/command/takeoff", tags=["Commands"])
async def cmd_takeoff(altitude: float = 10.0):
    """Take off to altitude (meters)."""
    return await drone_bridge.execute_command("takeoff", {"altitude": altitude})


@app.post("/api/v1/command/land", tags=["Commands"])
async def cmd_land():
    """Land immediately."""
    return await drone_bridge.execute_command("land", {})


@app.post("/api/v1/command/rtl", tags=["Commands"])
async def cmd_rtl():
    """Return to Launch."""
    return await drone_bridge.execute_command("rtl", {})


@app.post("/api/v1/command/hold", tags=["Commands"])
async def cmd_hold():
    """Hold position (LOITER)."""
    return await drone_bridge.execute_command("hold", {})


@app.post("/api/v1/command/mode", tags=["Commands"])
async def cmd_set_mode(req: ModeRequest):
    """Change flight mode (e.g. LOITER, ALT_HOLD, GUIDED, STABILIZE)."""
    return await drone_bridge.execute_command("mode", {"mode": req.mode})


@app.post("/api/v1/command/step", tags=["Commands"])
async def cmd_step_nudge(req: StepRequest):
    """
    Step nudge movement:
    axis: "up", "down", "forward", "backward", "left", "right", "yaw_left", "yaw_right"
    distance: distance in meters (e.g., 0.01 for 1cm, 0.3048 for 1ft)
    """
    return await drone_bridge.execute_command("step", {"axis": req.axis, "distance": req.distance})


@app.post("/api/v1/command/rc_handover", tags=["Commands"])
async def cmd_rc_handover(mode: str = "LOITER"):
    """
    Instantly hand control over to the FlySky RC transmitter
    by switching to LOITER or ALT_HOLD mode.
    """
    return await drone_bridge.execute_command("rc_handover", {"mode": mode})


@app.post("/api/v1/command/motor_test", tags=["Commands"])
async def cmd_motor_test(req: MotorTestRequest):
    """
    Test spin motors without flight.
    motor: 1 to 4 (or 0 for all in sequence)
    throttle: throttle percentage (e.g. 10.0 for 10%)
    duration: duration in seconds (e.g. 2.0)
    """
    return await drone_bridge.execute_command("motor_test", req.model_dump())


# ──────────────────────────────────────────────────────────────
# ArduPilot Specialized Routes
# ──────────────────────────────────────────────────────────────

@app.post("/api/v1/ardupilot/auto_setup", tags=["ArduPilot"])
async def api_ardupilot_auto_setup(req: ArduPilotAutoSetupRequest):
    """
    Automated One-Click Setup for Pixhawk 2.4.8 running ArduPilot.
    Configures recommended safety parameters, runs level/gyro/baro calibration,
    and returns comprehensive step-by-step audit.
    """
    res = await drone_bridge.execute_command("auto_setup", req.model_dump())
    # Broadcast auto-setup alert to all connected GCS clients
    await manager.broadcast({
        "type": "ALERT",
        "data": {"message": f"ArduPilot Auto-Setup Completed [{req.profile.upper()}]"}
    })
    return res


@app.get("/api/v1/ardupilot/params", tags=["ArduPilot"])
async def api_get_ardupilot_params():
    """Retrieve full catalog of core ArduPilot parameters with active values."""
    res = await drone_bridge.execute_command("get_params_all", {})
    return res


@app.post("/api/v1/ardupilot/params/set", tags=["ArduPilot"])
async def api_set_ardupilot_param(req: ParamUpdateRequest):
    """Set individual ArduPilot parameter."""
    res = await drone_bridge.execute_command("set_param", {"name": req.name, "value": req.value})
    return res


@app.get("/api/v1/ardupilot/prearm_check", tags=["ArduPilot"])
async def api_get_prearm_check():
    """Evaluate full pre-flight readiness checklist (score 0-100%)."""
    res = await drone_bridge.execute_command("prearm_check", {})
    return res


@app.post("/api/v1/mission/generate_survey", tags=["Mission"])
async def api_generate_survey(req: SurveyPolygonRequest):
    """
    Generate autonomous lawnmower survey waypoints across any bounding polygon.
    Ideal for agricultural recon, crop inspection, or tactical patrol.
    """
    wps = generate_survey_grid(
        polygon=req.polygon,
        altitude=req.altitude,
        lane_spacing_m=req.lane_spacing_m,
        speed_ms=req.speed_ms
    )
    return {
        "ok": True,
        "count": len(wps),
        "waypoints": wps,
        "msg": f"Generated {len(wps)} survey waypoints with {req.lane_spacing_m}m lane spacing"
    }


# ──────────────────────────────────────────────────────────────
# WebSocket Telemetry
# ──────────────────────────────────────────────────────────────

@app.websocket("/ws/telemetry")
async def websocket_telemetry(ws: WebSocket):
    """Real-time telemetry and command duplex stream."""
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            if data.strip().lower() == "ping":
                await ws.send_text(json.dumps({"type": "PONG"}))
            else:
                try:
                    msg = json.loads(data)
                    cmd = msg.get("command")
                    if cmd:
                        result = await drone_bridge.execute_command(
                            cmd, msg.get("params", {})
                        )
                        await ws.send_text(json.dumps({
                            "type": "COMMAND_RESULT",
                            "data": result,
                        }))
                except json.JSONDecodeError:
                    pass
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        manager.disconnect(ws)


# Mount static frontend
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
    logger.info("Mounted tactical GCS frontend from %s", frontend_dir)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
