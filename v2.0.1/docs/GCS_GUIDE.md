# Guardia AI v2.0.1 — GCS Development Guide
## Custom Ground Control Station Build Plan

---

## Overview

The GCS replaces QGroundControl / Mission Planner for daily operations.
It's a web app: FastAPI backend + Next.js frontend.

```
┌─────────────────────────────────────────────────────┐
│                    GCS ARCHITECTURE                  │
│                                                      │
│  Browser (Next.js)                                   │
│  ├── Live Video (WebRTC)                            │
│  ├── Telemetry HUD (WebSocket)                      │
│  ├── Map + Drone Position (MapLibre)                │
│  ├── Detection Overlays                              │
│  ├── Command Buttons                                 │
│  └── Mission Planner                                 │
│       │                                              │
│       │ WebSocket (telemetry, detections, commands)  │
│       │ HTTPS (REST API)                             │
│       ▼                                              │
│  FastAPI Backend                                     │
│  ├── MAVLink Parser (pymavlink)                     │
│  ├── WebSocket Manager (broadcast)                   │
│  ├── Command Validator (safety checks)               │
│  ├── Flight Logger (SQLite)                          │
│  └── Video Relay (MediaMTX)                          │
│       │                                              │
│       │ MAVLink over UDP/Serial/WireGuard            │
│       ▼                                              │
│  Drone (Pi 4B)                                       │
└─────────────────────────────────────────────────────┘
```

---

## Backend (Already Built)

File: `gcs/backend/main.py`

### Current Features
- ✅ FastAPI with CORS
- ✅ WebSocket telemetry broadcast at 5Hz
- ✅ Command API with safety confirmations
- ✅ Simulated drone for development
- ✅ Health check endpoints
- ✅ Pydantic models for all data

### API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/v1/status` | System status |
| GET | `/api/v1/telemetry` | Current telemetry snapshot |
| POST | `/api/v1/command` | Generic command (needs confirm for dangerous ones) |
| POST | `/api/v1/command/arm` | Arm drone |
| POST | `/api/v1/command/takeoff?altitude=10` | Take off |
| POST | `/api/v1/command/land` | Land |
| POST | `/api/v1/command/rtl` | Return to launch |
| POST | `/api/v1/command/hold` | Hold position |
| POST | `/api/v1/command/follow` | Follow target |
| POST | `/api/v1/command/patrol` | Start patrol |
| POST | `/api/v1/command/search` | Start rescue search |
| POST | `/api/v1/command/deliver` | Start delivery |
| WS | `/ws/telemetry` | Real-time telemetry + commands |

### Running the Backend
```bash
cd v2.0.1/gcs/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
# → http://localhost:8000/docs (Swagger UI)
```

### Connecting to Real Drone
Change the simulated drone to a real MAVLink connection:
```python
# In main.py, replace SimulatedDrone with real MAVLink:
from pymavlink import mavutil
connection = mavutil.mavlink_connection("udpin:0.0.0.0:14550")
```

---

## Frontend (To Build)

### Technology Stack
- **Next.js 14+** with App Router
- **TypeScript**
- **MapLibre GL** for map
- **WebSocket** for real-time telemetry
- **WebRTC** for live video

### Page Layout

```
┌─────────────────────────────────────────────────────┐
│ [Logo] Guardia GCS    [Status: CONNECTED]  [User]   │
├────────┬────────────────────────────────────────────┤
│        │                                             │
│  HUD   │            MAP                              │
│        │        (drone position,                     │
│ Speed  │         waypoints,                          │
│ Alt    │         geofence)                           │
│ Batt   │                                             │
│ GPS    │                                             │
│ Mode   │                                             │
│        │                                             │
├────────┼────────────────────────────────────────────┤
│        │                                             │
│ VIDEO  │     CONTROLS                                │
│ (live  │   [ARM] [TAKEOFF] [LAND] [RTL] [HOLD]     │
│  feed) │   [FOLLOW] [PATROL] [SEARCH] [DELIVER]    │
│        │                                             │
│        │     DETECTIONS                              │
│        │   Target #1: person (0.87)                  │
│        │   Target #2: person (0.72)                  │
│        │   [Click to follow]                         │
│        │                                             │
├────────┴────────────────────────────────────────────┤
│ Link: 45ms │ Loss: 0.1% │ Signal: -65dBm │ FPS: 28 │
└─────────────────────────────────────────────────────┘
```

### Frontend Init Commands
```bash
cd v2.0.1/gcs/frontend
npx -y create-next-app@latest ./ --typescript --app --src-dir --no-tailwind --eslint --no-import-alias
npm install maplibre-gl recharts
```

### Key Components to Build

| Component | Priority | Description |
|---|---|---|
| `TelemetryHUD` | P0 | Speed, altitude, battery, GPS, mode |
| `DroneMap` | P0 | MapLibre with drone marker and heading |
| `CommandPanel` | P0 | Buttons for arm, takeoff, land, RTL |
| `VideoPlayer` | P1 | WebRTC/WHEP live video |
| `DetectionList` | P1 | List of tracked targets with "follow" button |
| `MissionPlanner` | P2 | Draw waypoints on map |
| `FlightLog` | P2 | Historical telemetry viewer |
| `GeofenceDrawer` | P2 | Draw geofence on map |
| `LinkHealth` | P0 | RTT, packet loss, signal strength |
| `PreflightChecklist` | P1 | Interactive checklist before flight |

---

## WebSocket Protocol

### Messages FROM Server to Client

```jsonc
// Telemetry (5Hz)
{
  "type": "TELEMETRY",
  "data": {
    "state": "FOLLOW",
    "mission": "PERSON_FOLLOW",
    "armed": true,
    "lat": 28.6139,
    "lon": 77.2090,
    "alt": 10.5,
    "heading": 142.3,
    "groundspeed": 2.8,
    "battery_pct": 72,
    "battery_v": 15.2,
    "gps_fix": 3,
    "gps_sats": 14,
    "target_id": 3,
    "target_locked": true,
    "targets_detected": 5,
    "cpu_temp": 58.2,
    "ram_mb": 1200.0,
    "uptime": 342.5,
    "flight_mode": "OFFBOARD"
  }
}

// Detections (~10Hz)
{
  "type": "DETECTIONS",
  "data": [
    {"id": 3, "class": "person", "conf": 0.87, "bbox": [120, 80, 200, 280]},
    {"id": 5, "class": "person", "conf": 0.72, "bbox": [400, 150, 460, 350]}
  ]
}

// Alerts (on event)
{
  "type": "ALERT",
  "data": {
    "level": "WARNING",
    "type": "BATTERY_LOW",
    "message": "Battery at 15%, initiating RTL"
  }
}

// Command result (after command)
{
  "type": "COMMAND_RESULT",
  "data": {"ok": true, "msg": "Following target #3"}
}
```

### Messages FROM Client to Server

```jsonc
// Ping (keepalive)
"ping"

// Command via WebSocket
{"command": "follow", "params": {"target_id": 3, "mode": "follow"}}
{"command": "rtl", "params": {}}
{"command": "takeoff", "params": {"altitude": 15.0}}
```

---

## Development Workflow

### Phase 1: Backend + Swagger (Current)
```bash
# Already working
python main.py
# Test at http://localhost:8000/docs
```

### Phase 2: Frontend Shell
```bash
# Initialize Next.js project
cd gcs/frontend
npx -y create-next-app@latest ./ --typescript --app --eslint
npm run dev
```

### Phase 3: Connect Frontend to Backend
```typescript
// WebSocket hook
const ws = new WebSocket('ws://localhost:8000/ws/telemetry');
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === 'TELEMETRY') {
    setTelemetry(msg.data);
  }
};
```

### Phase 4: SITL Integration
```bash
# Run PX4 SITL
make px4_sitl jmavsim

# Connect GCS backend to SITL
# SITL broadcasts on UDP 14550
# Backend listens on udpin:0.0.0.0:14550
```

---

## Security Checklist

- [ ] Authentication on all command endpoints
- [ ] Rate limiting on commands (max 10/second)
- [ ] Double confirmation for dangerous commands (arm, takeoff, follow)
- [ ] HTTPS only in production
- [ ] WebSocket authentication
- [ ] Audit log for all commands
- [ ] Session timeout (30 minutes)
- [ ] Server-side speed/altitude/geofence validation
- [ ] No telemetry to external services
