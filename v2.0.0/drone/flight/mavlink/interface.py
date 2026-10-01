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

        # Callbacks
        self._heartbeat_callback: Optional[Callable] = None
        self._telemetry_callback: Optional[Callable] = None

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

    async def connect(self) -> bool:
        """Connect to Pixhawk via serial port with auto-probe fallbacks."""
        try:
            from pymavlink import mavutil
            import os

            # Candidate ports for Pixhawk 2.4.8
            candidate_ports = [self._port]
            for p in ["/dev/ttyACM0", "/dev/serial0", "/dev/ttyAMA0", "/dev/ttyUSB0"]:
                if p not in candidate_ports and os.path.exists(p):
                    candidate_ports.append(p)

            for port in candidate_ports:
                logger.info("Attempting Pixhawk 2.4.8 connection on: %s @ %d baud", port, self._baud)
                try:
                    self._connection = mavutil.mavlink_connection(
                        port,
                        baud=self._baud,
                        source_system=self._source_system,
                        source_component=self._source_component,
                    )

                    # Wait for heartbeat
                    logger.info("Waiting for Pixhawk heartbeat on %s...", port)
                    msg = self._connection.wait_heartbeat(timeout=3)

                    if msg:
                        self._port = port
                        self._connected = True
                        self._telemetry.last_heartbeat = time.monotonic()
                        logger.info(
                            "✅ Pixhawk 2.4.8 connected on %s | system=%d component=%d | firmware=%s",
                            port,
                            self._connection.target_system,
                            self._connection.target_component,
                            self._firmware,
                        )

                        # Request data streams
                        self._request_data_streams()
                        return True
                    else:
                        logger.warning("No heartbeat on %s within 3s", port)
                        if self._connection:
                            self._connection.close()
                except Exception as port_err:
                    logger.warning("Failed connecting on %s: %s", port, port_err)

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
            except Exception as e:
                logger.error("MAVLink receive error: %s", e)
                await asyncio.sleep(0.1)

    def _process_message(self, msg):
        """Process incoming MAVLink message."""
        msg_type = msg.get_type()

        if msg_type == "HEARTBEAT":
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

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def arm(self) -> bool:
        """Arm the vehicle."""
        if not self._connected:
            return False

        from pymavlink import mavutil

        self._connection.mav.command_long_send(
            self._connection.target_system,
            self._connection.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,    # confirmation
            1,    # arm
            0, 0, 0, 0, 0, 0,
        )

        # Wait for ACK
        ack = self._connection.recv_match(type="COMMAND_ACK", blocking=True, timeout=5)
        if ack and ack.result == 0:
            logger.info("✅ Armed")
            return True
        logger.warning("❌ Arm failed: %s", ack)
        return False

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

        ack = self._connection.recv_match(type="COMMAND_ACK", blocking=True, timeout=5)
        if ack and ack.result == 0:
            logger.info("✅ Disarmed")
            return True
        logger.warning("❌ Disarm failed")
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

        ack = self._connection.recv_match(type="COMMAND_ACK", blocking=True, timeout=5)
        if ack and ack.result == 0:
            logger.info("✅ Takeoff to %.1fm", altitude)
            return True
        logger.warning("❌ Takeoff failed")
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

        ack = self._connection.recv_match(type="COMMAND_ACK", blocking=True, timeout=5)
        success = ack and ack.result == 0
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
        return True

    async def disconnect(self):
        """Close the MAVLink connection."""
        self._running = False
        self._connected = False
        if self._connection:
            self._connection.close()
        logger.info("MAVLink disconnected")
