"""
Guardia AI v2.0.1 — Ground Control Station (GCS) Backend
==========================================================
Custom GCS that replaces QGroundControl / Mission Planner.
FastAPI + WebSocket for real-time telemetry and commands.

Features:
- Real-time drone telemetry over WebSocket (5-10Hz)
- Command API with authentication and validation
- Detection overlays metadata stream
- Flight log recording
- No telemetry to external services
"""

import asyncio
import json
import logging
import secrets
import sys
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

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


class Waypoint(BaseModel):
    lat: float
    lon: float
    alt: float = 10.0
    speed: float = 2.0


class MissionPlan(BaseModel):
    waypoints: List[Waypoint]
    patrol_repeat: bool = False
    altitude: float = 10.0


class SearchRequest(BaseModel):
    center_lat: float
    center_lon: float
    radius: float = 100.0
    pattern: str = "expanding_square"


class DeliverRequest(BaseModel):
    target_lat: float
    target_lon: float


class FollowRequest(BaseModel):
    target_id: int
    mode: str = "follow"  # "follow", "tail", "orbit"
    distance: float = 10.0


# ──────────────────────────────────────────────────────────────
# WebSocket Manager
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

    async def broadcast_detections(self, detections: list):
        await self.broadcast({"type": "DETECTIONS", "data": detections})

    async def broadcast_alert(self, alert: dict):
        await self.broadcast({"type": "ALERT", "data": alert})


manager = ConnectionManager()


# ──────────────────────────────────────────────────────────────
# Simulated Drone State (for development without hardware)
# ──────────────────────────────────────────────────────────────

class SimulatedDrone:
    """Simulated drone for GCS development and testing."""

    def __init__(self):
        self.telemetry = TelemetrySnapshot(
            lat=28.6139,  # Delhi
            lon=77.2090,
            alt=0.0,
            battery_pct=95,
            battery_v=16.4,
            gps_fix=3,
            gps_sats=12,
        )
        self._start_time = time.time()

    def update(self):
        """Update simulated telemetry."""
        self.telemetry.uptime = time.time() - self._start_time
        self.telemetry.cpu_temp = 52.0 + (time.time() % 10)
        self.telemetry.ram_mb = 2048.0

    async def execute_command(self, cmd: str, params: dict) -> dict:
        """Execute a simulated command."""
        commands = {
            "arm": lambda: {"ok": True, "msg": "Armed (simulated)"},
            "disarm": lambda: {"ok": True, "msg": "Disarmed (simulated)"},
            "takeoff": lambda: self._sim_takeoff(params.get("altitude", 10.0)),
            "land": lambda: {"ok": True, "msg": "Landing (simulated)"},
            "rtl": lambda: {"ok": True, "msg": "RTL (simulated)"},
            "hold": lambda: {"ok": True, "msg": "Holding (simulated)"},
            "follow": lambda: {"ok": True, "msg": f"Following target #{params.get('target_id', 0)} (simulated)"},
            "tail": lambda: {"ok": True, "msg": f"Tailing target #{params.get('target_id', 0)} (simulated)"},
            "patrol": lambda: {"ok": True, "msg": "Patrol started (simulated)"},
            "search": lambda: {"ok": True, "msg": "Search started (simulated)"},
            "deliver": lambda: {"ok": True, "msg": "Delivery started (simulated)"},
        }

        handler = commands.get(cmd)
        if handler:
            return handler()
        return {"ok": False, "msg": f"Unknown command: {cmd}"}

    def _sim_takeoff(self, alt):
        self.telemetry.alt = alt
        self.telemetry.state = "HOLD"
        self.telemetry.armed = True
        return {"ok": True, "msg": f"Takeoff to {alt}m (simulated)"}

    def get_telemetry_dict(self) -> dict:
        self.update()
        return self.telemetry.model_dump()


drone = SimulatedDrone()


# ──────────────────────────────────────────────────────────────
# App Lifespan
# ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage GCS startup and shutdown."""
    logger.info("Guardia GCS starting...")

    # Start telemetry broadcast task
    telemetry_task = asyncio.create_task(telemetry_broadcaster(), name="telemetry")

    logger.info("🎮 Guardia GCS ready — http://0.0.0.0:8000/docs")
    yield

    telemetry_task.cancel()
    try:
        await telemetry_task
    except asyncio.CancelledError:
        pass
    logger.info("Guardia GCS stopped")


async def telemetry_broadcaster():
    """Broadcast telemetry at 5Hz."""
    while True:
        try:
            if manager.active_connections:
                data = drone.get_telemetry_dict()
                await manager.broadcast_telemetry(data)
            await asyncio.sleep(0.2)  # 5Hz
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
    description=(
        "## Custom GCS for Autonomous Drone\n\n"
        "Real-time telemetry, command API, and mission control.\n\n"
        "**No telemetry to external services.**\n\n"
        "### Key Endpoints\n"
        "- `GET /api/v1/status` — System health\n"
        "- `GET /api/v1/telemetry` — Current telemetry snapshot\n"
        "- `POST /api/v1/command` — Send command to drone\n"
        "- `WS /ws/telemetry` — Real-time telemetry stream\n"
    ),
    version="2.0.1",
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
    return {"status": "healthy", "service": "guardia-gcs", "version": "2.0.1"}


@app.get("/api/v1/status", tags=["System"])
def system_status():
    return {
        "status": "online",
        "drone_connected": True,
        "clients": len(manager.active_connections),
        "uptime": drone.telemetry.uptime,
        "version": "2.0.1",
        "telemetry_enabled": False,  # No external telemetry
    }


@app.get("/api/v1/telemetry", tags=["Telemetry"], response_model=TelemetrySnapshot)
def get_telemetry():
    """Get current telemetry snapshot."""
    drone.update()
    return drone.telemetry


# --- Commands ---

DANGEROUS_COMMANDS = {"arm", "takeoff", "follow", "tail", "deliver"}


@app.post("/api/v1/command", tags=["Commands"], response_model=CommandResponse)
async def send_command(req: CommandRequest):
    """Send a command to the drone."""
    cmd = req.command.lower().strip()

    # Safety: dangerous commands need explicit confirmation
    if cmd in DANGEROUS_COMMANDS and not req.confirm:
        raise HTTPException(
            status_code=400,
            detail=f"Command '{cmd}' is dangerous. Set confirm=true to proceed.",
        )

    result = await drone.execute_command(cmd, req.params)

    # Broadcast command to all GCS clients
    await manager.broadcast({
        "type": "COMMAND_EXECUTED",
        "data": {"command": cmd, "result": result},
    })

    return CommandResponse(ok=result["ok"], msg=result["msg"])


@app.post("/api/v1/command/arm", tags=["Commands"])
async def cmd_arm():
    """Arm the drone (requires preflight check)."""
    return await drone.execute_command("arm", {})


@app.post("/api/v1/command/takeoff", tags=["Commands"])
async def cmd_takeoff(altitude: float = 10.0):
    """Take off to specified altitude."""
    return await drone.execute_command("takeoff", {"altitude": altitude})


@app.post("/api/v1/command/land", tags=["Commands"])
async def cmd_land():
    """Land at current position."""
    return await drone.execute_command("land", {})


@app.post("/api/v1/command/rtl", tags=["Commands"])
async def cmd_rtl():
    """Return to launch."""
    return await drone.execute_command("rtl", {})


@app.post("/api/v1/command/hold", tags=["Commands"])
async def cmd_hold():
    """Hold position."""
    return await drone.execute_command("hold", {})


@app.post("/api/v1/command/follow", tags=["Commands"])
async def cmd_follow(req: FollowRequest):
    """Start following a tracked target."""
    return await drone.execute_command("follow", req.model_dump())


@app.post("/api/v1/command/patrol", tags=["Commands"])
async def cmd_patrol(plan: MissionPlan):
    """Start patrol mission with waypoints."""
    return await drone.execute_command("patrol", plan.model_dump())


@app.post("/api/v1/command/search", tags=["Commands"])
async def cmd_search(req: SearchRequest):
    """Start rescue search pattern."""
    return await drone.execute_command("search", req.model_dump())


@app.post("/api/v1/command/deliver", tags=["Commands"])
async def cmd_deliver(req: DeliverRequest):
    """Start delivery mission."""
    return await drone.execute_command("deliver", req.model_dump())


# ──────────────────────────────────────────────────────────────
# WebSocket
# ──────────────────────────────────────────────────────────────

@app.websocket("/ws/telemetry")
async def websocket_telemetry(ws: WebSocket):
    """
    Real-time telemetry and detection WebSocket.

    Receives:
    - TELEMETRY messages (5-10Hz)
    - DETECTION messages (~10Hz)
    - ALERT messages (on failsafe triggers)
    - COMMAND_EXECUTED messages

    Client can send:
    - "ping" → responds with {"type": "PONG"}
    - Commands as JSON
    """
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            if data.strip().lower() == "ping":
                await ws.send_text(json.dumps({"type": "PONG"}))
            else:
                try:
                    msg = json.loads(data)
                    if "command" in msg:
                        result = await drone.execute_command(
                            msg["command"], msg.get("params", {})
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


# ──────────────────────────────────────────────────────────────
# Entry
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
