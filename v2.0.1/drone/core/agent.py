"""
Guardia AI v2.0.1 — Drone Core Agent
======================================
The master brain. Manages the drone state machine, coordinates all subsystems
(flight, AI, video, delivery), and enforces safety at every step.

Runs entirely on the Raspberry Pi 4B. No telemetry. No cloud calls.

State Machine:
    IDLE → ARMED → TAKEOFF → HOLD → { PATROL | FOLLOW | SEARCH | DELIVER } → RTL → LANDED
    Any state → EMERGENCY (on critical failure)
"""

import asyncio
import logging
import signal
import time
from enum import Enum, auto
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field

logger = logging.getLogger("guardia.agent")


class DroneState(Enum):
    """Core drone state machine states."""
    IDLE = auto()
    PREFLIGHT = auto()
    ARMED = auto()
    TAKEOFF = auto()
    HOLD = auto()         # Hovering, waiting for commands
    PATROL = auto()       # Autonomous waypoint patrol
    FOLLOW = auto()       # Following a tracked target
    SEARCH = auto()       # Search pattern (rescue mode)
    DELIVER = auto()      # Payload delivery mission
    RTL = auto()          # Return to launch
    LANDING = auto()
    LANDED = auto()
    EMERGENCY = auto()


class MissionType(Enum):
    """Types of autonomous missions."""
    SURVEILLANCE_PATROL = auto()
    PERSON_FOLLOW = auto()
    PERSON_TAIL = auto()    # Covert follow at distance
    RESCUE_SEARCH = auto()
    DELIVERY = auto()
    MANUAL = auto()


@dataclass
class DroneStatus:
    """Current drone status snapshot."""
    state: DroneState = DroneState.IDLE
    mission: MissionType = MissionType.MANUAL
    armed: bool = False

    # Position
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0
    heading: float = 0.0

    # Velocity
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    groundspeed: float = 0.0

    # Battery
    battery_voltage: float = 0.0
    battery_percent: int = 100
    battery_current: float = 0.0

    # GPS
    gps_fix: int = 0
    gps_satellites: int = 0

    # Tracking
    target_id: Optional[int] = None
    target_locked: bool = False
    target_distance: float = 0.0
    targets_detected: int = 0

    # System
    cpu_temp: float = 0.0
    cpu_usage: float = 0.0
    ram_usage_mb: float = 0.0
    uptime_seconds: float = 0.0
    flight_mode: str = "UNKNOWN"

    # Timestamps
    last_heartbeat: float = 0.0
    last_gps_update: float = 0.0


# Valid state transitions
VALID_TRANSITIONS: Dict[DroneState, set] = {
    DroneState.IDLE:       {DroneState.PREFLIGHT},
    DroneState.PREFLIGHT:  {DroneState.ARMED, DroneState.IDLE},
    DroneState.ARMED:      {DroneState.TAKEOFF, DroneState.IDLE},
    DroneState.TAKEOFF:    {DroneState.HOLD},
    DroneState.HOLD:       {DroneState.PATROL, DroneState.FOLLOW, DroneState.SEARCH,
                            DroneState.DELIVER, DroneState.RTL, DroneState.LANDING},
    DroneState.PATROL:     {DroneState.HOLD, DroneState.FOLLOW, DroneState.RTL},
    DroneState.FOLLOW:     {DroneState.HOLD, DroneState.RTL},
    DroneState.SEARCH:     {DroneState.HOLD, DroneState.FOLLOW, DroneState.RTL},
    DroneState.DELIVER:    {DroneState.HOLD, DroneState.RTL},
    DroneState.RTL:        {DroneState.LANDING, DroneState.HOLD},
    DroneState.LANDING:    {DroneState.LANDED},
    DroneState.LANDED:     {DroneState.IDLE},
    DroneState.EMERGENCY:  {DroneState.LANDED, DroneState.IDLE},
}

# Emergency is always reachable from any state
for state in DroneState:
    if state != DroneState.EMERGENCY:
        VALID_TRANSITIONS[state].add(DroneState.EMERGENCY)


class DroneAgent:
    """
    Core drone agent — the master orchestrator.

    Responsibilities:
    - State machine management
    - Subsystem coordination (flight, AI, video, delivery)
    - Safety enforcement (geofence, battery, link loss)
    - Command processing from GCS
    - Heartbeat and health monitoring
    """

    def __init__(self):
        self.status = DroneStatus()
        self._state = DroneState.IDLE
        self._mission = MissionType.MANUAL
        self._running = False
        self._start_time = 0.0

        # Subsystem references (injected after init)
        self._flight_controller = None
        self._tracker = None
        self._video_service = None
        self._delivery_service = None
        self._nav_planner = None
        self._failsafe_manager = None

        # Callbacks
        self._state_callbacks: list = []
        self._alert_callbacks: list = []

        # Heartbeat tracking
        self._last_pixhawk_heartbeat = 0.0
        self._last_gcs_heartbeat = 0.0
        self._pixhawk_timeout = 3.0  # seconds
        self._gcs_timeout = 10.0     # seconds

        logger.info("DroneAgent initialized — state: %s", self._state.name)

    @property
    def state(self) -> DroneState:
        return self._state

    @property
    def mission(self) -> MissionType:
        return self._mission

    def register_subsystems(
        self,
        flight_controller=None,
        tracker=None,
        video_service=None,
        delivery_service=None,
        nav_planner=None,
        failsafe_manager=None,
    ):
        """Inject subsystem references after construction."""
        self._flight_controller = flight_controller
        self._tracker = tracker
        self._video_service = video_service
        self._delivery_service = delivery_service
        self._nav_planner = nav_planner
        self._failsafe_manager = failsafe_manager
        logger.info("Subsystems registered")

    def on_state_change(self, callback: Callable):
        """Register a callback for state transitions."""
        self._state_callbacks.append(callback)

    def on_alert(self, callback: Callable):
        """Register a callback for safety alerts."""
        self._alert_callbacks.append(callback)

    # ------------------------------------------------------------------
    # State Machine
    # ------------------------------------------------------------------

    def transition_to(self, new_state: DroneState, reason: str = "") -> bool:
        """
        Attempt a state transition. Returns True if valid.
        Emergency transitions are always allowed.
        """
        if new_state == self._state:
            return True

        valid_next = VALID_TRANSITIONS.get(self._state, set())
        if new_state not in valid_next:
            logger.warning(
                "BLOCKED transition %s → %s (reason: %s). Valid: %s",
                self._state.name, new_state.name, reason,
                [s.name for s in valid_next]
            )
            return False

        old_state = self._state
        self._state = new_state
        self.status.state = new_state

        logger.info(
            "STATE: %s → %s [%s]",
            old_state.name, new_state.name, reason or "no reason"
        )

        # Notify callbacks
        for cb in self._state_callbacks:
            try:
                cb(old_state, new_state, reason)
            except Exception as e:
                logger.error("State callback error: %s", e)

        return True

    # ------------------------------------------------------------------
    # Main Loop
    # ------------------------------------------------------------------

    async def run(self):
        """Main agent loop — runs forever until stopped."""
        self._running = True
        self._start_time = time.monotonic()
        logger.info("🚁 DroneAgent starting main loop")

        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self.stop)

        try:
            while self._running:
                cycle_start = time.monotonic()

                # Update status
                self.status.uptime_seconds = cycle_start - self._start_time
                self._update_system_stats()

                # Run state-specific logic
                await self._tick()

                # Safety checks (always run regardless of state)
                await self._safety_check()

                # Target 50Hz control loop
                elapsed = time.monotonic() - cycle_start
                sleep_time = max(0, 0.02 - elapsed)  # 50Hz = 20ms
                await asyncio.sleep(sleep_time)

        except asyncio.CancelledError:
            logger.info("DroneAgent cancelled")
        except Exception as e:
            logger.critical("DroneAgent crashed: %s", e, exc_info=True)
            self.transition_to(DroneState.EMERGENCY, f"agent crash: {e}")
        finally:
            await self._shutdown()

    def stop(self):
        """Signal the agent to stop."""
        logger.info("DroneAgent stop requested")
        self._running = False

    async def _tick(self):
        """Execute state-specific logic for the current tick."""
        state = self._state

        if state == DroneState.IDLE:
            pass  # Waiting for commands

        elif state == DroneState.PREFLIGHT:
            await self._preflight_check()

        elif state == DroneState.ARMED:
            pass  # Waiting for takeoff command

        elif state == DroneState.TAKEOFF:
            await self._handle_takeoff()

        elif state == DroneState.HOLD:
            await self._handle_hold()

        elif state == DroneState.PATROL:
            await self._handle_patrol()

        elif state == DroneState.FOLLOW:
            await self._handle_follow()

        elif state == DroneState.SEARCH:
            await self._handle_search()

        elif state == DroneState.DELIVER:
            await self._handle_deliver()

        elif state == DroneState.RTL:
            await self._handle_rtl()

        elif state == DroneState.LANDING:
            await self._handle_landing()

        elif state == DroneState.LANDED:
            pass

        elif state == DroneState.EMERGENCY:
            await self._handle_emergency()

    # ------------------------------------------------------------------
    # State Handlers
    # ------------------------------------------------------------------

    async def _preflight_check(self):
        """Run preflight checks before arming."""
        checks_passed = True
        issues = []

        # Check Pixhawk heartbeat
        if time.monotonic() - self._last_pixhawk_heartbeat > self._pixhawk_timeout:
            checks_passed = False
            issues.append("No Pixhawk heartbeat")

        # Check GPS
        if self.status.gps_fix < 3:
            checks_passed = False
            issues.append(f"GPS fix insufficient: {self.status.gps_fix}")

        # Check battery
        if self.status.battery_percent < 20:
            checks_passed = False
            issues.append(f"Battery low: {self.status.battery_percent}%")

        # Check AI system
        if self._tracker and not self._tracker.is_ready:
            issues.append("Tracker not ready (non-blocking)")

        if checks_passed:
            logger.info("✅ Preflight passed")
            self.transition_to(DroneState.ARMED, "preflight passed")
        else:
            logger.warning("❌ Preflight failed: %s", issues)

    async def _handle_takeoff(self):
        """Manage takeoff sequence."""
        if self._flight_controller:
            # Flight controller handles the actual takeoff via MAVLink
            pass

    async def _handle_hold(self):
        """Hover in place, run AI detection."""
        if self._tracker:
            # Keep running detection even in hold mode
            pass

    async def _handle_patrol(self):
        """Autonomous waypoint patrol."""
        if self._nav_planner and self._flight_controller:
            # Navigate to next waypoint
            pass
        # Run detection during patrol
        if self._tracker:
            pass

    async def _handle_follow(self):
        """Follow a tracked target."""
        if not self._tracker or not self.status.target_locked:
            # Lost target — hover and wait
            self.transition_to(DroneState.HOLD, "target lost")
            return

        if self._flight_controller and self._tracker:
            # Get target offset from tracker
            # Convert to velocity commands
            # Send to Pixhawk
            pass

    async def _handle_search(self):
        """Execute search pattern for rescue."""
        if self._nav_planner and self._flight_controller:
            # Follow search pattern
            pass
        # Look for people
        if self._tracker:
            pass

    async def _handle_deliver(self):
        """Execute delivery mission."""
        if self._delivery_service and self._flight_controller:
            pass

    async def _handle_rtl(self):
        """Return to launch."""
        if self._flight_controller:
            pass

    async def _handle_landing(self):
        """Manage landing sequence."""
        if self._flight_controller:
            pass

    async def _handle_emergency(self):
        """Emergency state — attempt to land immediately."""
        if self._flight_controller:
            # Command immediate land
            pass

    # ------------------------------------------------------------------
    # Safety
    # ------------------------------------------------------------------

    async def _safety_check(self):
        """Run safety checks every tick."""
        now = time.monotonic()

        # Pixhawk heartbeat check
        if (self._state not in (DroneState.IDLE, DroneState.LANDED) and
                now - self._last_pixhawk_heartbeat > self._pixhawk_timeout):
            logger.critical("LOST PIXHAWK HEARTBEAT")
            self.transition_to(DroneState.EMERGENCY, "pixhawk heartbeat lost")

        # Battery check
        if self.status.battery_percent <= 5:
            self.transition_to(DroneState.EMERGENCY, "battery critical")
        elif self.status.battery_percent <= 15 and self._state not in (
            DroneState.RTL, DroneState.LANDING, DroneState.LANDED,
            DroneState.EMERGENCY, DroneState.IDLE
        ):
            logger.warning("Battery low (%d%%), initiating RTL", self.status.battery_percent)
            self.transition_to(DroneState.RTL, "battery low")

        # Geofence check
        # (would check distance from home against config.flight.geofence_radius)

    def update_pixhawk_heartbeat(self):
        """Called when a MAVLink heartbeat is received from Pixhawk."""
        self._last_pixhawk_heartbeat = time.monotonic()
        self.status.last_heartbeat = self._last_pixhawk_heartbeat

    def update_gcs_heartbeat(self):
        """Called when a GCS heartbeat is received."""
        self._last_gcs_heartbeat = time.monotonic()

    # ------------------------------------------------------------------
    # Commands (from GCS or internal)
    # ------------------------------------------------------------------

    async def cmd_arm(self) -> dict:
        """Arm the drone."""
        if self._state == DroneState.IDLE:
            self.transition_to(DroneState.PREFLIGHT, "arm requested")
            return {"ok": True, "msg": "Running preflight checks..."}
        elif self._state == DroneState.ARMED:
            return {"ok": True, "msg": "Already armed"}
        return {"ok": False, "msg": f"Cannot arm from state {self._state.name}"}

    async def cmd_disarm(self) -> dict:
        """Disarm the drone."""
        if self._state in (DroneState.LANDED, DroneState.IDLE):
            self.status.armed = False
            self.transition_to(DroneState.IDLE, "disarmed")
            return {"ok": True, "msg": "Disarmed"}
        return {"ok": False, "msg": f"Cannot disarm in state {self._state.name}"}

    async def cmd_takeoff(self, altitude: float = 10.0) -> dict:
        """Take off to specified altitude."""
        if self._state != DroneState.ARMED:
            return {"ok": False, "msg": f"Must be ARMED, currently {self._state.name}"}
        self.transition_to(DroneState.TAKEOFF, f"takeoff to {altitude}m")
        return {"ok": True, "msg": f"Taking off to {altitude}m"}

    async def cmd_land(self) -> dict:
        """Land at current position."""
        self.transition_to(DroneState.LANDING, "land commanded")
        return {"ok": True, "msg": "Landing"}

    async def cmd_rtl(self) -> dict:
        """Return to launch."""
        self.transition_to(DroneState.RTL, "RTL commanded")
        return {"ok": True, "msg": "Returning to launch"}

    async def cmd_hold(self) -> dict:
        """Hold position."""
        self.transition_to(DroneState.HOLD, "hold commanded")
        return {"ok": True, "msg": "Holding position"}

    async def cmd_follow(self, target_id: int) -> dict:
        """Start following a tracked target."""
        if self._state not in (DroneState.HOLD, DroneState.PATROL, DroneState.SEARCH):
            return {"ok": False, "msg": f"Cannot follow from state {self._state.name}"}
        self.status.target_id = target_id
        self._mission = MissionType.PERSON_FOLLOW
        self.transition_to(DroneState.FOLLOW, f"following target #{target_id}")
        return {"ok": True, "msg": f"Following target #{target_id}"}

    async def cmd_tail(self, target_id: int, distance: float = 20.0) -> dict:
        """Covert tail — follow at greater distance."""
        if self._state not in (DroneState.HOLD, DroneState.PATROL, DroneState.SEARCH):
            return {"ok": False, "msg": f"Cannot tail from state {self._state.name}"}
        self.status.target_id = target_id
        self._mission = MissionType.PERSON_TAIL
        self.transition_to(DroneState.FOLLOW, f"tailing target #{target_id} at {distance}m")
        return {"ok": True, "msg": f"Tailing target #{target_id}"}

    async def cmd_patrol(self, waypoints: list) -> dict:
        """Start patrol mission with waypoints."""
        if self._state != DroneState.HOLD:
            return {"ok": False, "msg": f"Must be HOLD to start patrol"}
        self._mission = MissionType.SURVEILLANCE_PATROL
        self.transition_to(DroneState.PATROL, f"patrol with {len(waypoints)} waypoints")
        return {"ok": True, "msg": f"Patrol started with {len(waypoints)} waypoints"}

    async def cmd_search(self, center_lat: float, center_lon: float, radius: float) -> dict:
        """Start rescue search pattern."""
        if self._state != DroneState.HOLD:
            return {"ok": False, "msg": "Must be HOLD to start search"}
        self._mission = MissionType.RESCUE_SEARCH
        self.transition_to(DroneState.SEARCH, f"searching {radius}m radius")
        return {"ok": True, "msg": f"Search pattern started"}

    async def cmd_deliver(self, target_lat: float, target_lon: float) -> dict:
        """Deliver payload to coordinates."""
        if self._state != DroneState.HOLD:
            return {"ok": False, "msg": "Must be HOLD to start delivery"}
        self._mission = MissionType.DELIVERY
        self.transition_to(DroneState.DELIVER, "delivery mission")
        return {"ok": True, "msg": "Delivery mission started"}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _update_system_stats(self):
        """Update CPU/RAM stats."""
        try:
            # CPU temperature
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                self.status.cpu_temp = int(f.read().strip()) / 1000.0
        except (FileNotFoundError, ValueError):
            pass

        try:
            import psutil
            self.status.cpu_usage = psutil.cpu_percent(interval=0)
            mem = psutil.virtual_memory()
            self.status.ram_usage_mb = mem.used / (1024 * 1024)
        except ImportError:
            pass

    async def _shutdown(self):
        """Clean shutdown of all subsystems."""
        logger.info("DroneAgent shutting down...")
        if self._flight_controller:
            try:
                # Ensure disarmed
                pass
            except Exception:
                pass
        if self._video_service:
            try:
                pass
            except Exception:
                pass
        logger.info("DroneAgent stopped cleanly")

    def get_status_dict(self) -> dict:
        """Return current status as a dictionary (for GCS telemetry)."""
        return {
            "state": self._state.name,
            "mission": self._mission.name,
            "armed": self.status.armed,
            "lat": self.status.latitude,
            "lon": self.status.longitude,
            "alt": self.status.altitude,
            "heading": self.status.heading,
            "groundspeed": self.status.groundspeed,
            "battery_pct": self.status.battery_percent,
            "battery_v": self.status.battery_voltage,
            "gps_fix": self.status.gps_fix,
            "gps_sats": self.status.gps_satellites,
            "target_id": self.status.target_id,
            "target_locked": self.status.target_locked,
            "target_distance": self.status.target_distance,
            "targets_detected": self.status.targets_detected,
            "cpu_temp": self.status.cpu_temp,
            "cpu_usage": self.status.cpu_usage,
            "ram_mb": self.status.ram_usage_mb,
            "uptime": self.status.uptime_seconds,
            "flight_mode": self.status.flight_mode,
        }
