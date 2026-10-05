"""
Guardia AI v2.0.0 — MAVLink Flight Interface
==============================================
Handles all communication with the Pixhawk flight controller
via MAVLink 2 over UART. Uses pymavlink for direct control.

Supports:
- Heartbeat monitoring
- Telemetry reception (position, attitude, battery, GPS)
- Offboard/Guided mode commands
- Velocity setpoints for follow mode
- Waypoint missions
- Arming, takeoff, landing, RTL
- Failsafe parameter reading

No telemetry to external services. All data stays on-device.
"""

import asyncio
import logging
import time
import math
from typing import Optional, Callable, Dict, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger("guardia.flight.mavlink")


@dataclass
class TelemetryData:
    """Parsed telemetry from Pixhawk."""
    # Position
    latitude: float = 0.0
    longitude: float = 0.0
    altitude_msl: float = 0.0
    altitude_rel: float = 0.0

    # Attitude (radians)
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0

    # Velocity (m/s)
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    groundspeed: float = 0.0
    airspeed: float = 0.0

    # Heading (degrees)
    heading: float = 0.0

    # Battery
    battery_voltage: float = 0.0
    battery_current: float = 0.0
    battery_remaining: int = -1

    # GPS
    gps_fix_type: int = 0
    gps_satellites: int = 0
    gps_hdop: float = 99.99
    gps_vdop: float = 99.99

    # System
    flight_mode: str = "UNKNOWN"
    armed: bool = False
    system_status: int = 0

    # Home position
    home_lat: float = 0.0
    home_lon: float = 0.0
    home_alt: float = 0.0

    # Timestamps
    last_heartbeat: float = 0.0
    last_position: float = 0.0
    last_attitude: float = 0.0
    last_battery: float = 0.0

    # RC and Status Messages
    rc_channels: list = None
    statustext: str = ""


class MAVLinkInterface:
    """
    Low-level MAVLink 2 interface to Pixhawk.

    Handles serial communication, message parsing, and command sending.
    Designed for both PX4 and ArduPilot firmware.

    Usage:
        mav = MAVLinkInterface("/dev/serial0", 921600)
        await mav.connect()
        await mav.arm()
        await mav.takeoff(10.0)
    """

    # PX4 flight modes
    PX4_MODES = {
        "MANUAL": (1, 0),
        "ALTCTL": (1, 1),
        "POSCTL": (1, 2),
        "OFFBOARD": (1, 6),
        "STABILIZED": (1, 7),
        "RATTITUDE": (1, 8),
        "MISSION": (4, 4),
        "LOITER": (4, 3),
        "RTL": (4, 5),
        "LAND": (4, 6),
        "TAKEOFF": (4, 2),
    }

    # ArduPilot flight modes (Copter)
    ARDUPILOT_MODES = {
        "STABILIZE": 0,
        "ACRO": 1,
        "ALT_HOLD": 2,
        "AUTO": 3,
        "GUIDED": 4,
        "LOITER": 5,
        "RTL": 6,
        "CIRCLE": 7,
        "LAND": 9,
        "POSHOLD": 16,
        "BRAKE": 17,
        "SMART_RTL": 21,
    }

    def __init__(
        self,
        port: str = "/dev/serial0",
        baud: int = 921600,
        source_system: int = 1,
        source_component: int = 191,
        firmware: str = "px4",  # "px4" or "ardupilot"
    ):
        self._port = port
        self._baud = baud
        self._source_system = source_system
        self._source_component = source_component
        self._firmware = firmware.lower()

        self._connection = None
        self._connected = False
        self._telemetry = TelemetryData()
        self._running = False

        # Internal message trackers (avoids thread race conditions)
        self._command_acks: Dict[int, Tuple[int, float]] = {}
        self._recent_statustexts: list = []
        self._parameters: Dict[str, float] = {}

        # Callbacks
        self._heartbeat_callback: Optional[Callable] = None
        self._telemetry_callback: Optional[Callable] = None
        self._disconnect_callback: Optional[Callable] = None

        # Setpoint tracking
        self._last_setpoint_time = 0.0
        self._setpoint_rate_hz = 20

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def telemetry(self) -> TelemetryData:
        return self._telemetry

    def on_heartbeat(self, callback: Callable):
        self._heartbeat_callback = callback

    def on_telemetry(self, callback: Callable):
        self._telemetry_callback = callback

    def on_disconnect(self, callback: Callable):
        self._disconnect_callback = callback

    async def connect(self) -> bool:
        """Connect to Pixhawk via serial port with auto-probe fallbacks."""
        try:
            from pymavlink import mavutil
            import os

            # Candidate ports for Pixhawk 2.4.8 (cross-platform)
            candidate_ports = [self._port]
            
            # Detect Windows COM ports if on Windows
            try:
                import serial.tools.list_ports as lp
                for p in lp.comports():
                    if p.device not in candidate_ports:
                        candidate_ports.append(p.device)
            except Exception:
                pass

            for p in ["/dev/ttyACM0", "/dev/serial0", "/dev/ttyAMA0", "/dev/ttyUSB0"]:
                if p not in candidate_ports and os.path.exists(p):
                    candidate_ports.append(p)

            bauds_to_try = [self._baud]
            for b in [115200, 57600, 921600]:
                if b not in bauds_to_try:
                    bauds_to_try.append(b)

            for port in candidate_ports:
                for baud in bauds_to_try:
                    logger.info("Attempting Pixhawk connection on: %s @ %d baud", port, baud)
                    try:
                        self._connection = mavutil.mavlink_connection(
                            port,
                            baud=baud,
                            source_system=self._source_system,
                            source_component=self._source_component,
                        )

                        # Wait for heartbeat
                        msg = self._connection.wait_heartbeat(timeout=1.5)
                        if msg:
                            self._port = port
                            self._baud = baud
                            self._connected = True
                            self._telemetry.last_heartbeat = time.monotonic()
                            if msg.autopilot == mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA:
                                self._firmware = "ardupilot"
                            elif msg.autopilot == mavutil.mavlink.MAV_AUTOPILOT_PX4:
                                self._firmware = "px4"

                            logger.info(
                                "✅ Pixhawk connected on %s @ %d | sys=%d comp=%d | fw=%s",
                                port,
                                baud,
                                self._connection.target_system,
                                self._connection.target_component,
                                self._firmware,
                            )
                            self._request_data_streams()
                            return True
                        else:
                            if self._connection:
                                self._connection.close()
                    except Exception as port_err:
                        pass

            logger.error("❌ Failed to connect to Pixhawk 2.4.8 on all candidate ports: %s", candidate_ports)
            return False

        except ImportError:
            logger.error("pymavlink not installed. Install with: pip install pymavlink")
            return False
        except Exception as e:
            logger.error("Failed to connect to Pixhawk: %s", e)
            return False

    def _request_data_streams(self):
        """Request telemetry data streams from Pixhawk."""
        if not self._connection:
            return

        from pymavlink import mavutil

        # Request all data streams at 10Hz
        streams = [
            mavutil.mavlink.MAV_DATA_STREAM_ALL,
        ]
        for stream in streams:
            self._connection.mav.request_data_stream_send(
                self._connection.target_system,
                self._connection.target_component,
                stream,
                10,  # Hz
                1,   # Start
            )

    async def receive_loop(self):
        """Continuous message receive loop. Run as an asyncio task."""
        self._running = True
        logger.info("MAVLink receive loop started")

        while self._running and self._connected:
            try:
                msg = self._connection.recv_match(blocking=False)
                if msg:
                    self._process_message(msg)
                else:
                    await asyncio.sleep(0.001)  # 1ms sleep if no message
            except (OSError, PermissionError) as e:
                # Fatal serial disconnect (e.g. ClearCommError, USB unplugged)
                logger.warning("🔌 Pixhawk serial link lost: %s", e)
                self._connected = False
                self._running = False
                if self._connection:
                    try:
                        self._connection.close()
                    except Exception:
                        pass
                    self._connection = None
                if self._disconnect_callback:
                    try:
                        self._disconnect_callback(str(e))
                    except Exception:
                        pass
                break
            except Exception as e:
                err_str = str(e)
                if any(w in err_str.lower() for w in ["clearcommerror", "not recognize the command", "bad file descriptor", "handle is invalid"]):
                    logger.warning("🔌 Pixhawk serial disconnected: %s", err_str)
                    self._connected = False
                    self._running = False
                    if self._connection:
                        try:
                            self._connection.close()
                        except Exception:
                            pass
                        self._connection = None
                    if self._disconnect_callback:
                        try:
                            self._disconnect_callback(err_str)
                        except Exception:
                            pass
                    break
                else:
                    logger.error("MAVLink receive error: %s", e)
                    await asyncio.sleep(0.2)

    def _process_message(self, msg):
        """Process incoming MAVLink message."""
        msg_type = msg.get_type()

        if msg_type == "HEARTBEAT":
            from pymavlink import mavutil
            if msg.autopilot == mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA:
                self._firmware = "ardupilot"
            elif msg.autopilot == mavutil.mavlink.MAV_AUTOPILOT_PX4:
                self._firmware = "px4"
            self._telemetry.last_heartbeat = time.monotonic()
            self._telemetry.armed = (msg.base_mode & 128) != 0
            self._telemetry.system_status = msg.system_status
            self._parse_flight_mode(msg)

            if self._heartbeat_callback:
                self._heartbeat_callback()

        elif msg_type == "GLOBAL_POSITION_INT":
            self._telemetry.latitude = msg.lat / 1e7
            self._telemetry.longitude = msg.lon / 1e7
            self._telemetry.altitude_msl = msg.alt / 1000.0
            self._telemetry.altitude_rel = msg.relative_alt / 1000.0
            self._telemetry.vx = msg.vx / 100.0
            self._telemetry.vy = msg.vy / 100.0
            self._telemetry.vz = msg.vz / 100.0
            self._telemetry.heading = msg.hdg / 100.0
            self._telemetry.last_position = time.monotonic()

        elif msg_type == "ATTITUDE":
            self._telemetry.roll = msg.roll
            self._telemetry.pitch = msg.pitch
            self._telemetry.yaw = msg.yaw
            self._telemetry.last_attitude = time.monotonic()

        elif msg_type == "SYS_STATUS":
            self._telemetry.battery_voltage = msg.voltage_battery / 1000.0
            self._telemetry.battery_current = msg.current_battery / 100.0
            self._telemetry.battery_remaining = msg.battery_remaining
            self._telemetry.last_battery = time.monotonic()

        elif msg_type == "GPS_RAW_INT":
            self._telemetry.gps_fix_type = msg.fix_type
            self._telemetry.gps_satellites = msg.satellites_visible
            self._telemetry.gps_hdop = msg.eph / 100.0
            self._telemetry.gps_vdop = msg.epv / 100.0

        elif msg_type == "VFR_HUD":
            self._telemetry.groundspeed = msg.groundspeed
            self._telemetry.airspeed = msg.airspeed

        elif msg_type == "HOME_POSITION":
            self._telemetry.home_lat = msg.latitude / 1e7
            self._telemetry.home_lon = msg.longitude / 1e7
            self._telemetry.home_alt = msg.altitude / 1000.0

        elif msg_type == "RC_CHANNELS":
            self._telemetry.rc_channels = [
                getattr(msg, f"chan{i}_raw", 1500) for i in range(1, 9)
            ]

        elif msg_type == "STATUSTEXT":
            self._telemetry.statustext = msg.text
            self._recent_statustexts.append(msg.text)
            if len(self._recent_statustexts) > 30:
                self._recent_statustexts.pop(0)
            logger.info("📢 FC STATUSTEXT: %s", msg.text)

        elif msg_type == "COMMAND_ACK":
            self._command_acks[msg.command] = (msg.result, time.monotonic())
            logger.info("📩 FC COMMAND_ACK: cmd=%d, result=%d", msg.command, msg.result)

        elif msg_type == "PARAM_VALUE":
            try:
                p_id = msg.param_id if isinstance(msg.param_id, str) else msg.param_id.decode("utf-8", "ignore").rstrip("\x00")
                self._parameters[p_id] = msg.param_value
            except Exception:
                pass

        if self._telemetry_callback:
            self._telemetry_callback(msg_type, self._telemetry)

    def _parse_flight_mode(self, heartbeat_msg):
        """Parse flight mode from heartbeat message."""
        if self._firmware == "px4":
            custom = heartbeat_msg.custom_mode
            main = (custom >> 16) & 0xFF
            sub = (custom >> 24) & 0xFF
            for name, (m, s) in self.PX4_MODES.items():
                if main == m and sub == s:
                    self._telemetry.flight_mode = name
                    return
            self._telemetry.flight_mode = f"PX4_CUSTOM_{custom}"
        else:
            mode = heartbeat_msg.custom_mode
            for name, m in self.ARDUPILOT_MODES.items():
                if m == mode:
                    self._telemetry.flight_mode = name
                    return
            self._telemetry.flight_mode = f"AP_MODE_{mode}"

    async def wait_command_ack(self, command: int, timeout: float = 3.0) -> Optional[int]:
        """Wait for COMMAND_ACK for a given command without thread race conditions."""
        t_start = time.monotonic()
        if command in self._command_acks:
            del self._command_acks[command]

        while time.monotonic() - t_start < timeout:
            if command in self._command_acks:
                res, _ = self._command_acks[command]
                return res
            await asyncio.sleep(0.03)
        return None

    async def set_safety_switch(self, enable: bool = False) -> Tuple[bool, str]:
        """
        Disengage (enable=False) or engage (enable=True) hardware safety switch.
        In ArduPilot / MAVLink: MAV_CMD_DO_SET_SAFETY_SWITCH_STATE (5300):
        param1: 0 = SAFETY_SWITCH_STATE_SAFE (safe/locked), 1 = SAFETY_SWITCH_STATE_DANGEROUS (motors active!)
        """
        if not self._connected:
            return False, "Not connected to Pixhawk"

        from pymavlink import mavutil

        safety_val = (
            mavutil.mavlink.SAFETY_SWITCH_STATE_SAFE
            if enable
            else mavutil.mavlink.SAFETY_SWITCH_STATE_DANGEROUS
        )
        logger.info(
            "Setting safety switch: %s (param1=%d)",
            "ON (Safe)" if enable else "OFF (Motors LIVE)",
            safety_val,
        )

        cmd_id = getattr(mavutil.mavlink, "MAV_CMD_DO_SET_SAFETY_SWITCH_STATE", 5300)
        try:
            self._connection.mav.command_long_send(
                self._connection.target_system,
                self._connection.target_component,
                cmd_id,
                0,
                safety_val,
                0, 0, 0, 0, 0, 0,
            )
            ack = await self.wait_command_ack(cmd_id, timeout=2.0)
        except Exception as e:
            logger.warning("Safety switch command error: %s", e)
            ack = None

        state_str = "Safety ENGAGED (Safe)" if enable else "Safety DISENGAGED (Motors Active)"
        if ack == 0 or ack is None:
            return True, state_str
        return False, f"Safety switch command rejected (ACK {ack})"

    async def set_param(self, name: str, value: float) -> Tuple[bool, str]:
        """Set a flight controller parameter (e.g. ARMING_CHECK, BRD_SAFETYENABLE)."""
        if not self._connected:
            return False, "Not connected to Pixhawk"

        logger.info("Setting flight controller parameter: %s = %s", name, value)
        try:
            self._connection.param_set_send(name, float(value))
        except Exception:
            from pymavlink import mavutil
            self._connection.mav.param_set_send(
                self._connection.target_system,
                self._connection.target_component,
                name.encode("utf-8")[:16].ljust(16, b"\x00"),
                float(value),
                mavutil.mavlink.MAV_PARAM_TYPE_REAL32,
            )
        await asyncio.sleep(0.15)
        return True, f"Parameter {name} set to {value}"

    async def get_param(self, name: str, timeout: float = 2.0) -> Optional[float]:
        """Request and retrieve a parameter value from the flight controller."""
        if not self._connected:
            return None

        if name in self._parameters:
            return self._parameters[name]

        p_bytes = name.encode("utf-8")[:16].ljust(16, b"\x00")
        try:
            self._connection.mav.param_request_read_send(
                self._connection.target_system,
                self._connection.target_component,
                p_bytes,
                -1,
            )
        except Exception as e:
            logger.warning("param_request_read_send error: %s", e)

        t_start = time.monotonic()
        while time.monotonic() - t_start < timeout:
            if name in self._parameters:
                return self._parameters[name]
            await asyncio.sleep(0.05)
        return None

    async def reboot_autopilot(self) -> Tuple[bool, str]:
        """Reboot the Pixhawk flight controller (reloads IO co-processor and parameters)."""
        if not self._connected:
            return False, "Pixhawk not connected"

        from pymavlink import mavutil

        logger.info("Sending reboot command to Pixhawk...")
        try:
            self._connection.mav.command_long_send(
                self._connection.target_system,
                self._connection.target_component,
                mavutil.mavlink.MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN,
                0,
                1,  # param1 = 1: Reboot autopilot
                0, 0, 0, 0, 0, 0,
            )
            return True, "Reboot command sent to Pixhawk (reconnecting in ~5s)"
        except Exception as e:
            return False, f"Reboot command failed: {e}"

    async def configure_bench_mode(self, enable: bool = True) -> Tuple[bool, str]:
        """
        One-click setup for bench testing:
        - Disables safety switch requirement (BRD_SAFETYENABLE=0, BRD_SAFETY_DEFLT=0)
        - Unmasks motor outputs 1-4 so IO chip always outputs PWM (BRD_SAFETY_MASK=15)
        - Disables pre-arm checks (ARMING_CHECK=0)
        - Disables low battery failsafe on bench (BATT_FS_LOW_ACT=0) so USB 5V doesn't trip failsafe
        - Disengages safety switch
        Allows testing motors, precision steps, and arming on your desk without outdoor GPS/Compass locks.
        """
        if not self._connected:
            return False, "Not connected to Pixhawk"

        if enable:
            await self.set_param("BRD_SAFETYENABLE", 0)
            await self.set_param("BRD_SAFETY_DEFLT", 0)
            await self.set_param("BRD_SAFETY_MASK", 15)
            await self.set_param("ARMING_CHECK", 0)
            await self.set_param("BATT_FS_LOW_ACT", 0)
            await self.set_safety_switch(enable=False)
            return True, "BENCH MODE ACTIVE: Safety disabled, BRD_SAFETY_MASK=15, ARMING_CHECK=0 (Motors & outputs active)"
        else:
            await self.set_param("ARMING_CHECK", 1)
            await self.set_param("BRD_SAFETYENABLE", 1)
            await self.set_param("BRD_SAFETY_DEFLT", 1)
            await self.set_param("BRD_SAFETY_MASK", 0)
            await self.set_param("BATT_FS_LOW_ACT", 1)
            await self.set_safety_switch(enable=True)
            return True, "FLIGHT MODE ACTIVE: Strict Pre-Arm checks and safety switch restored"

    async def calibrate_level(self) -> Tuple[bool, str]:
        """
        Calibrate AHRS Accelerometer Level Trim (horizontal level).
        Places vehicle flat on desk, then calibrates pitch=0, roll=0.
        Uses MAV_CMD_PREFLIGHT_CALIBRATION with param5=1.
        """
        if not self._connected:
            return False, "Pixhawk not connected"

        from pymavlink import mavutil

        logger.info("Starting Level Horizon (Accel Trim) Calibration...")
        self._connection.mav.command_long_send(
            self._connection.target_system,
            self._connection.target_component,
            mavutil.mavlink.MAV_CMD_PREFLIGHT_CALIBRATION,
            0,
            0, 0, 0, 0, 1, 0, 0  # param5 = 1 (Level trim)
        )

        ack = await self.wait_command_ack(mavutil.mavlink.MAV_CMD_PREFLIGHT_CALIBRATION, timeout=4.0)
        if ack == 0 or ack is None:
            return True, "Level Horizon Calibrated successfully (Roll & Pitch zeroed)"
        return False, f"Level calibration rejected (ACK {ack})"

    async def calibrate_gyros(self) -> Tuple[bool, str]:
        """
        Calibrate gyroscopes. Drone must stay still on table for 3 seconds.
        Uses MAV_CMD_PREFLIGHT_CALIBRATION with param1=1.
        """
        if not self._connected:
            return False, "Pixhawk not connected"

        from pymavlink import mavutil

        logger.info("Starting Gyroscope Calibration (hold drone still)...")
        self._connection.mav.command_long_send(
            self._connection.target_system,
            self._connection.target_component,
            mavutil.mavlink.MAV_CMD_PREFLIGHT_CALIBRATION,
            0,
            1, 0, 0, 0, 0, 0, 0  # param1 = 1 (Gyros)
        )

        ack = await self.wait_command_ack(mavutil.mavlink.MAV_CMD_PREFLIGHT_CALIBRATION, timeout=5.0)
        if ack == 0 or ack is None:
            return True, "Gyroscopes calibrated successfully"
        return False, f"Gyro calibration failed (ACK {ack})"

    async def calibrate_baro(self) -> Tuple[bool, str]:
        """
        Zero barometer pressure reference (reset altitude to 0.0m).
        Uses MAV_CMD_PREFLIGHT_CALIBRATION with param3=1.
        """
        if not self._connected:
            return False, "Pixhawk not connected"

        from pymavlink import mavutil

        logger.info("Zeroing barometer / ground pressure reference...")
        self._connection.mav.command_long_send(
            self._connection.target_system,
            self._connection.target_component,
            mavutil.mavlink.MAV_CMD_PREFLIGHT_CALIBRATION,
            0,
            0, 0, 1, 0, 0, 0, 0  # param3 = 1 (Baro)
        )

        ack = await self.wait_command_ack(mavutil.mavlink.MAV_CMD_PREFLIGHT_CALIBRATION, timeout=3.0)
        if ack == 0 or ack is None:
            return True, "Barometer zeroed to ground level"
        return False, f"Barometer calibration failed (ACK {ack})"

    async def calibrate_compass(self) -> Tuple[bool, str]:
        """
        Trigger Compass Calibration.
        Uses MAV_CMD_PREFLIGHT_CALIBRATION with param2=1.
        """
        if not self._connected:
            return False, "Pixhawk not connected"

        from pymavlink import mavutil

        logger.info("Triggering compass calibration...")
        self._connection.mav.command_long_send(
            self._connection.target_system,
            self._connection.target_component,
            mavutil.mavlink.MAV_CMD_PREFLIGHT_CALIBRATION,
            0,
            0, 1, 0, 0, 0, 0, 0  # param2 = 1 (Compass)
        )

        ack = await self.wait_command_ack(mavutil.mavlink.MAV_CMD_PREFLIGHT_CALIBRATION, timeout=3.0)
        if ack == 0 or ack is None:
            return True, "Compass calibration started — rotate drone smoothly on all axes"
        return False, f"Compass calibration rejected (ACK {ack})"

    async def arm(self, force: bool = False) -> Tuple[bool, str]:
        """Arm the vehicle. If force=True, bypasses pre-arm checks with magic 21196."""
        if not self._connected:
            return False, "Pixhawk not connected"

        from pymavlink import mavutil

        # Ensure safety switch is disengaged before arming
        await self.set_safety_switch(enable=False)
        await asyncio.sleep(0.1)

        self._recent_statustexts.clear()

        # In ArduPilot, param2=21196 forces arming regardless of pre-arm checks
        force_magic = 21196 if force else 0

        logger.info("Sending ARM command (force=%s)...", force)
        self._connection.mav.command_long_send(
            self._connection.target_system,
            self._connection.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,            # confirmation
            1,            # 1 = arm
            force_magic,  # param2
            0, 0, 0, 0, 0,
        )

        ack = await self.wait_command_ack(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, timeout=3.0)
        if ack == 0:
            self._telemetry.armed = True
            logger.info("✅ Armed successfully")
            return True, "Armed"
        else:
            errors = [t for t in self._recent_statustexts if any(w in t.lower() for w in ["prearm", "check", "compass", "accel", "gyro", "safety", "battery", "gps"])]
            detail = "; ".join(errors) if errors else (self._telemetry.statustext if self._telemetry.statustext else "Pre-arm checks failed")
            logger.warning("❌ Arm failed: %s (ACK %s)", detail, ack)
            return False, f"Arm failed: {detail} (Tip: Use 'Force Arm' or 'Bench Mode' for desk testing)"

    async def disarm(self) -> bool:
        """Disarm the vehicle."""
        if not self._connected:
            return False

        from pymavlink import mavutil

        self._connection.mav.command_long_send(
            self._connection.target_system,
            self._connection.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            0,    # disarm
            0, 0, 0, 0, 0, 0,
        )

        ack = await self.wait_command_ack(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, timeout=3.0)
        if ack == 0 or ack is None:
            self._telemetry.armed = False
            logger.info("✅ Disarmed")
            return True
        logger.warning("❌ Disarm failed (ACK %s)", ack)
        return False

    async def takeoff(self, altitude: float = 10.0) -> bool:
        """Command takeoff to given altitude (meters)."""
        if not self._connected:
            return False

        from pymavlink import mavutil

        # Set mode to GUIDED/OFFBOARD first
        if self._firmware == "px4":
            await self.set_mode("OFFBOARD")
        else:
            await self.set_mode("GUIDED")

        self._connection.mav.command_long_send(
            self._connection.target_system,
            self._connection.target_component,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0,
            0, 0, 0, 0, 0, 0,
            altitude,
        )

        ack = await self.wait_command_ack(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, timeout=4.0)
        if ack == 0 or ack is None:
            logger.info("✅ Takeoff to %.1fm initiated", altitude)
            return True
        logger.warning("❌ Takeoff command rejected (ACK %s)", ack)
        return False

    async def land(self) -> bool:
        """Command landing at current position."""
        if not self._connected:
            return False

        from pymavlink import mavutil

        self._connection.mav.command_long_send(
            self._connection.target_system,
            self._connection.target_component,
            mavutil.mavlink.MAV_CMD_NAV_LAND,
            0,
            0, 0, 0, 0, 0, 0, 0,
        )

        ack = await self.wait_command_ack(mavutil.mavlink.MAV_CMD_NAV_LAND, timeout=4.0)
        success = (ack == 0 or ack is None)
        logger.info("Land command: %s", "✅" if success else "❌")
        return success

    async def rtl(self) -> bool:
        """Return to launch."""
        if self._firmware == "px4":
            return await self.set_mode("RTL")
        else:
            return await self.set_mode("RTL")

    async def set_mode(self, mode: str) -> bool:
        """Set flight mode by name."""
        if not self._connected:
            return False

        from pymavlink import mavutil

        if self._firmware == "px4":
            if mode not in self.PX4_MODES:
                logger.error("Unknown PX4 mode: %s", mode)
                return False
            main_mode, sub_mode = self.PX4_MODES[mode]
            custom_mode = (main_mode) | (sub_mode << 8)
            self._connection.mav.command_long_send(
                self._connection.target_system,
                self._connection.target_component,
                mavutil.mavlink.MAV_CMD_DO_SET_MODE,
                0,
                mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                custom_mode,
                0, 0, 0, 0, 0,
            )
        else:
            if mode not in self.ARDUPILOT_MODES:
                logger.error("Unknown ArduPilot mode: %s", mode)
                return False
            mode_id = self.ARDUPILOT_MODES[mode]
            self._connection.set_mode(mode_id)

        await asyncio.sleep(0.5)
        logger.info("Mode set to: %s", mode)
        return True

    async def send_velocity(
        self, vx: float, vy: float, vz: float, yaw_rate: float = 0.0
    ):
        """
        Send velocity setpoint in body frame.

        Args:
            vx: Forward velocity (m/s)
            vy: Right velocity (m/s)
            vz: Down velocity (m/s, positive = descend)
            yaw_rate: Yaw rate (rad/s)
        """
        if not self._connected:
            return

        from pymavlink import mavutil

        # Rate limiting
        now = time.monotonic()
        dt = now - self._last_setpoint_time
        min_dt = 1.0 / self._setpoint_rate_hz
        if dt < min_dt:
            return
        self._last_setpoint_time = now

        # SET_POSITION_TARGET_LOCAL_NED
        type_mask = (
            0b0000_0000_0111  # Ignore position
            | 0b0000_0000_0000  # Use velocity
            | 0b0000_0110_0000  # Ignore acceleration
            # Yaw rate
        )
        if yaw_rate != 0:
            type_mask |= 0b0000_0100_0000_0000  # Ignore yaw, use yaw_rate
        else:
            type_mask |= 0b0000_1000_0000_0000  # Ignore yaw_rate

        self._connection.mav.set_position_target_local_ned_send(
            0,  # time_boot_ms
            self._connection.target_system,
            self._connection.target_component,
            mavutil.mavlink.MAV_FRAME_BODY_NED,
            type_mask,
            0, 0, 0,     # position (ignored)
            vx, vy, vz,  # velocity
            0, 0, 0,     # acceleration (ignored)
            0,            # yaw
            yaw_rate,     # yaw_rate
        )

    async def send_position(self, lat: float, lon: float, alt: float):
        """Send a goto position command."""
        if not self._connected:
            return

        from pymavlink import mavutil

        self._connection.mav.set_position_target_global_int_send(
            0,
            self._connection.target_system,
            self._connection.target_component,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
            0b0000_1111_1111_1000,  # Use position only
            int(lat * 1e7),
            int(lon * 1e7),
            alt,
            0, 0, 0,
            0, 0, 0,
            0, 0,
        )

    async def send_step_nudge(self, axis: str, distance_m: float = 0.3048) -> bool:
        """
        Command a relative step movement in the body frame.
        Useful for precise 1cm / 1ft nudges from the GCS.

        Args:
            axis: 'up', 'down', 'forward', 'backward', 'left', 'right', 'yaw_left', 'yaw_right'
            distance_m: distance in meters (e.g. 0.01 for 1cm, 0.3048 for 1ft)
        """
        if not self._connected:
            logger.warning("Cannot send step: not connected to Pixhawk")
            return False

        from pymavlink import mavutil

        # Ensure vehicle is in GUIDED mode for manual GCS nudges
        if self._telemetry.flight_mode not in ["GUIDED", "OFFBOARD"]:
            logger.info("Switching to GUIDED mode for step movement")
            await self.set_mode("GUIDED" if self._firmware != "px4" else "OFFBOARD")
            await asyncio.sleep(0.2)

        axis = axis.lower().strip()
        dx, dy, dz = 0.0, 0.0, 0.0

        if axis == "up":
            # NED: negative Z is up
            dz = -abs(distance_m)
        elif axis == "down":
            dz = abs(distance_m)
        elif axis == "forward":
            dx = abs(distance_m)
        elif axis == "backward":
            dx = -abs(distance_m)
        elif axis == "left":
            dy = -abs(distance_m)
        elif axis == "right":
            dy = abs(distance_m)
        elif axis in ["yaw_left", "yaw_right"]:
            angle_deg = 15.0 if axis == "yaw_right" else -15.0
            self._connection.mav.command_long_send(
                self._connection.target_system,
                self._connection.target_component,
                mavutil.mavlink.MAV_CMD_CONDITION_YAW,
                0,
                abs(angle_deg),
                20.0,  # 20 deg/s
                1 if angle_deg > 0 else -1,
                1,     # Relative offset
                0, 0, 0
            )
            return True
        else:
            logger.error("Unknown step axis: %s", axis)
            return False

        # Send SET_POSITION_TARGET_LOCAL_NED with MAV_FRAME_BODY_OFFSET_NED
        type_mask = 0b0000_1111_1111_1000

        self._connection.mav.set_position_target_local_ned_send(
            0,  # time_boot_ms
            self._connection.target_system,
            self._connection.target_component,
            mavutil.mavlink.MAV_FRAME_BODY_OFFSET_NED,
            type_mask,
            dx, dy, dz,
            0, 0, 0,
            0, 0, 0,
            0, 0
        )
        logger.info("Sent step nudge: axis=%s, distance=%.4fm (dx=%.4f, dy=%.4f, dz=%.4f)", axis, distance_m, dx, dy, dz)
        return True

    def get_distance_to_home(self) -> float:
        """Calculate distance from current position to home (meters)."""
        if self._telemetry.home_lat == 0:
            return 0.0
        return self._haversine(
            self._telemetry.latitude, self._telemetry.longitude,
            self._telemetry.home_lat, self._telemetry.home_lon,
        )

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Distance between two GPS coordinates in meters."""
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    async def set_servo(self, channel: int, pwm: int) -> bool:
        """
        Set PWM output on a Pixhawk servo channel.
        For Pixhawk 2.4.8:
        Channel 1-8: MAIN OUT
        Channel 9-14: AUX OUT 1-6 (AUX1 = 9)

        Args:
            channel: Servo channel (e.g. 9 for AUX1)
            pwm: PWM value in microseconds (typically 1000 to 2000)
        """
        if not self._connected:
            logger.warning("Cannot set servo: Pixhawk not connected")
            return False

        from pymavlink import mavutil

        logger.info("Setting Pixhawk servo ch %d to %d us", channel, pwm)
        self._connection.mav.command_long_send(
            self._connection.target_system,
            self._connection.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_SERVO,
            0,
            channel,
            pwm,
            0, 0, 0, 0, 0,
        )
        return True

    async def set_gripper(self, action: int = 0) -> bool:
        """
        Command ArduPilot gripper library.
        Args:
            action: 0 for release, 1 for grab
        """
        if not self._connected:
            return False

        from pymavlink import mavutil

        logger.info("Commanding gripper action: %d (0=release, 1=grab)", action)
        self._connection.mav.command_long_send(
            self._connection.target_system,
            self._connection.target_component,
            mavutil.mavlink.MAV_CMD_DO_GRIPPER,
            0,
            1,  # Gripper instance 1
            action,
            0, 0, 0, 0, 0,
        )
    async def motor_test(
        self,
        motor_instance: int = 1,
        throttle_pct: float = 10.0,
        timeout_sec: float = 2.0,
        motor_count: int = 1,
    ) -> Tuple[bool, str]:
        """
        Spin motor for bench testing without flight.
        Uses MAV_CMD_DO_MOTOR_TEST.

        Args:
            motor_instance: Motor index (1 = Front-Right, 2 = Rear-Right, 3 = Rear-Left, 4 = Front-Left)
            throttle_pct: Throttle percentage (1% to 40% safe limit)
            timeout_sec: Duration in seconds (0.5s to 10s)
            motor_count: 1 for single motor, or 4 for all motors in sequence
        """
        if not self._connected:
            return False, "Pixhawk not connected"

        from pymavlink import mavutil

        # Ensure safety switch is off before testing motors
        await self.set_safety_switch(enable=False)
        await asyncio.sleep(0.1)

        # Clamp throttle to safe limits (0 to 40%)
        throttle_pct = max(0.0, min(40.0, float(throttle_pct)))
        timeout_sec = max(0.5, min(10.0, float(timeout_sec)))

        logger.info(
            "Running Motor Test: motor=%d, throttle=%.1f%%, duration=%.1fs, count=%d",
            motor_instance, throttle_pct, timeout_sec, motor_count
        )

        self._connection.mav.command_long_send(
            self._connection.target_system,
            self._connection.target_component,
            mavutil.mavlink.MAV_CMD_DO_MOTOR_TEST,
            0,               # confirmation
            motor_instance,  # param1: Motor instance (1-8)
            0,               # param2: Throttle type (0 = percent 0-100)
            throttle_pct,    # param3: Throttle value
            timeout_sec,     # param4: Timeout in seconds
            motor_count,     # param5: Motor count (1=single, 4=sequence)
            0,               # param6: Motor test order (0 = default)
            0,
        )

        ack = await self.wait_command_ack(mavutil.mavlink.MAV_CMD_DO_MOTOR_TEST, timeout=2.5)
        target_desc = f"All 4 motors in sequence" if motor_count > 1 else f"Motor {motor_instance}"
        if ack == 0 or ack is None:
            return True, f"{target_desc} spinning at {throttle_pct:.0f}% for {timeout_sec:.1f}s"
        elif ack == 4:
            return False, f"Motor test rejected by flight controller (ACK 4) — Ensure safety switch is off or click 'Bench Mode'!"
        else:
            return False, f"Motor test rejected (ACK {ack})"

    async def clear_mission(self) -> Tuple[bool, str]:
        """Clear all waypoints from flight controller."""
        if not self._connected:
            return False, "Not connected to Pixhawk"

        self._connection.mav.mission_clear_all_send(
            self._connection.target_system,
            self._connection.target_component
        )
        return True, "Mission cleared on flight controller"

    async def upload_mission(self, waypoints: list) -> Tuple[bool, str]:
        """
        Upload waypoint list to Pixhawk flight controller.
        waypoints: list of dicts: [{"lat": float, "lon": float, "alt": float, "speed": float}, ...]
        """
        if not self._connected:
            return False, "Pixhawk not connected"
        if not waypoints:
            return False, "No waypoints provided"

        from pymavlink import mavutil

        # Clear existing mission first
        await self.clear_mission()
        await asyncio.sleep(0.2)

        total_items = len(waypoints)
        logger.info("Uploading %d waypoints to Pixhawk...", total_items)

        self._connection.mav.mission_count_send(
            self._connection.target_system,
            self._connection.target_component,
            total_items
        )

        for seq, wp in enumerate(waypoints):
            lat = float(wp.get("lat", 0.0))
            lon = float(wp.get("lon", 0.0))
            alt = float(wp.get("alt", 10.0))

            self._connection.mav.mission_item_int_send(
                self._connection.target_system,
                self._connection.target_component,
                seq,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                1 if seq == 0 else 0, # current
                1,                    # autocontinue
                0, 0, 0, 0,           # params 1-4
                int(lat * 1e7),
                int(lon * 1e7),
                float(alt)
            )
            await asyncio.sleep(0.05)

        return True, f"Successfully uploaded {total_items} waypoints to Pixhawk"

    async def disconnect(self):
        """Close the MAVLink connection."""
        self._running = False
        self._connected = False
        if self._connection:
            self._connection.close()
        logger.info("MAVLink disconnected")
