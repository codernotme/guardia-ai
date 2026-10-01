# Guardia AI v2.0.1 — MASTER PLAN
## Autonomous Drone: Surveillance, Rescue, Tracking, Delivery
### Tackle Studio — Aryan Bajpai

> **This project is 100% AI-built.** Every module, every line, every integration.
> This document is the single source of truth for the entire build.

---

## Table of Contents

1. [Vision & Scope](#1-vision--scope)
2. [System Overview](#2-system-overview)
3. [Architecture Deep Dive](#3-architecture-deep-dive)
4. [Module Breakdown](#4-module-breakdown)
5. [Build Phases & Sprint Plan](#5-build-phases--sprint-plan)
6. [AI Model Strategy](#6-ai-model-strategy)
7. [Hardware Wiring Guide](#7-hardware-wiring-guide)
8. [Software Stack & Dependencies](#8-software-stack--dependencies)
9. [Testing Strategy](#9-testing-strategy)
10. [Safety & Legal](#10-safety--legal)
11. [No-Telemetry Implementation](#11-no-telemetry-implementation)
12. [Runbooks & SOPs](#12-runbooks--sops)
13. [Risk Register](#13-risk-register)
14. [Decision Log](#14-decision-log)
15. [Cost Breakdown](#15-cost-breakdown)

---

## 1. Vision & Scope

### What We're Building
A **fully autonomous drone system** that runs on a Raspberry Pi 4B (8GB RAM) with a Pixhawk flight controller. It can:

| Capability | Description | Priority |
|---|---|---|
| **Surveillance Patrol** | Fly autonomous waypoint routes, detect anomalies | P0 |
| **Person Follow** | Lock onto a person and follow them at safe distance | P0 |
| **Person Tail** | Covert follow at greater distance, smoother movements | P1 |
| **Rescue Search** | Fly search patterns (expanding square, grid, sector) to find people | P0 |
| **Delivery** | Carry and drop payload to GPS coordinates or tracked person | P2 |
| **Custom GCS** | Web-based ground control replacing QGroundControl | P0 |

### What We're NOT Building (Scope Guards)
- ❌ No obstacle avoidance via LiDAR/sonar (altitude-only avoidance for now)
- ❌ No multi-drone coordination (single drone first)
- ❌ No voice commands
- ❌ No autonomous takeoff/landing from moving platforms
- ❌ No night vision (camera hardware dependent)
- ❌ No weaponized features

### Hard Constraints
| Constraint | Value | Reason |
|---|---|---|
| RAM | 8GB | Raspberry Pi 4B |
| CPU | 4x Cortex-A72 1.8GHz | Pi 4B |
| GPU | VideoCore VI | H.264 encode only |
| AI inference | <150ms per frame | Usable tracking at 8-12 FPS |
| Total power | <20W for Pi + modem | Battery budget |
| Telemetry | ZERO | Privacy, offline-first |
| Network | Optional 4G | Not required for core operation |

---

## 2. System Overview

### Two-Machine Architecture

```
┌──────────────────────────────────┐     ┌──────────────────────────────┐
│          DRONE (Air)             │     │         GCS (Ground)          │
│                                  │     │                               │
│  Raspberry Pi 4B (8GB)          │     │  Any laptop/PC/phone          │
│  ├── AI Detector (YOLOv8n)      │     │  ├── FastAPI Backend          │
│  ├── ByteTrack Tracker          │     │  ├── Next.js Frontend         │
│  ├── Follow Controller (PID)    │     │  ├── Video Viewer (WebRTC)    │
│  ├── Video Pipeline             │     │  ├── Map (MapLibre)           │
│  ├── Failsafe Manager           │     │  └── Command Interface        │
│  ├── Navigation Planner         │     │                               │
│  ├── Delivery Service           │     │  Connected via:               │
│  └── MAVLink Interface          │     │  • USB (bench testing)        │
│                                  │     │  • WiFi (close range)         │
│  Pixhawk Flight Controller      │     │  • 4G/WireGuard (long range)  │
│  (connected via UART)           │     │                               │
└──────────────────────────────────┘     └──────────────────────────────┘
```

### Data Flow Architecture

```
Camera 30fps ──┬── Main Stream (720p) ──── Record to SD / Stream to GCS
               │
               └── Low-Res Stream (320x320) ──── YOLOv8n Detector
                                                      │
                                                      ▼
                                               ByteTrack Tracker
                                                      │
                                                      ▼
                                               Follow Controller
                                                      │
                                              ┌───────┴───────┐
                                              │  PID Output   │
                                              │  vx, vy, yaw  │
                                              └───────┬───────┘
                                                      │
                                                      ▼
                                               MAVLink Interface
                                                      │
                                                      ▼
                                                  Pixhawk FC
                                                      │
                                                      ▼
                                                  Motors/ESCs
```

### State Machine

```
                        ┌────────────────────────────┐
                        │                            │
    ┌──────┐       ┌────▼────┐       ┌───────┐      │
    │ IDLE │──────►│PREFLIGHT│──────►│ ARMED │      │
    └──┬───┘       └─────────┘       └───┬───┘      │
       │                                 │           │
       │                            ┌────▼────┐      │
       │                            │ TAKEOFF │      │
       │                            └────┬────┘      │
       │                                 │           │
       │                            ┌────▼────┐      │
       │            ┌───────────────┤  HOLD   ├──────┤
       │            │               └────┬────┘      │
       │            │                    │           │
       │     ┌──────┼──────────┬─────────┼──────┐   │
       │     │      │          │         │      │   │
       │  ┌──▼──┐ ┌─▼────┐ ┌──▼───┐ ┌───▼───┐  │   │
       │  │PATROL│ │FOLLOW│ │SEARCH│ │DELIVER│  │   │
       │  └──┬───┘ └──┬───┘ └──┬───┘ └───┬───┘  │   │
       │     │        │        │         │      │   │
       │     └────────┴────────┴─────────┘      │   │
       │                    │                    │   │
       │               ┌────▼────┐               │   │
       │               │  RTL    │───────────────┘   │
       │               └────┬────┘                   │
       │                    │                        │
       │               ┌────▼────┐                   │
       │               │ LANDING │                   │
       │               └────┬────┘                   │
       │                    │                        │
       │               ┌────▼────┐                   │
       └───────────────┤ LANDED  │                   │
                       └─────────┘                   │
                                                     │
        ANY STATE ──────► EMERGENCY ─────────────────┘
```

---

## 3. Architecture Deep Dive

### 3.1 Memory Budget (8GB)

| Component | RAM (MB) | Notes |
|---|---|---|
| Raspberry Pi OS Lite | 300-400 | Headless, no desktop |
| Python runtime | 80-100 | Interpreter + standard lib |
| YOLOv8n TFLite (INT8) | 8-12 | Quantized, tiny |
| YOLOv8n TFLite (FP32) | 25-30 | More accurate alternative |
| TFLite inference buffers | 40-60 | Input/output tensors |
| ByteTracker state | 10-20 | Track objects, history |
| Camera buffers (dual stream) | 100-150 | 720p + 320x320 |
| H.264 encoder (hardware) | 50-80 | VideoCore VI |
| Video recording buffer | 50-100 | Ring buffer |
| MAVLink/pymavlink | 20-30 | Serial I/O |
| Follow controller | 5-10 | PID state |
| Failsafe manager | 5-10 | Monitoring state |
| Navigation planner | 10-20 | Waypoint lists |
| OS page cache & buffers | 200-500 | Disk I/O caching |
| **Total estimated** | **~900-1500** | |
| **Available** | **8192** | |
| **Headroom** | **~6500-7200** | Plenty of room |

### 3.2 CPU Budget (4 cores @ 1.8GHz)

| Task | Core Affinity | CPU % | Frequency |
|---|---|---|---|
| AI inference (detector) | Core 0-1 | 60-80% | 8-12 FPS |
| Camera capture | Core 2 | 10-15% | 30 FPS |
| MAVLink RX/TX | Core 3 | 5-10% | 50 Hz |
| Agent main loop | Core 3 | 5-10% | 50 Hz |
| Follow controller | Core 3 | 2-5% | 20 Hz |
| Video encoding (hardware) | VideoCore | 0% CPU | 30 FPS |
| Failsafe checks | Any | <1% | 50 Hz |

### 3.3 Latency Budget (tracking loop)

| Step | Time (ms) | Notes |
|---|---|---|
| Camera capture | 0-5 | Zero-copy from CSI |
| Resize to 320x320 | 1-3 | OpenCV or Picamera2 lores |
| YOLOv8n inference | 80-120 | TFLite, 4 threads |
| ByteTrack update | 1-3 | Pure numpy |
| PID compute | <1 | Simple math |
| MAVLink send | <1 | Serial write |
| **Total tracking loop** | **~85-135** | **7-12 Hz** |

This is the on-device loop. It never touches the network. The drone tracks smoothly regardless of GCS connection.

---

## 4. Module Breakdown

### 4.1 Drone Modules (Pi 4B)

| Module | File(s) | Status | Description |
|---|---|---|---|
| **Config** | `drone/config/settings.py` | ✅ Done | All hardware, AI, flight, video, delivery parameters |
| **Core Agent** | `drone/core/agent.py` | ✅ Done | State machine, subsystem coordinator, safety enforcer |
| **Main Entry** | `drone/main.py` | ✅ Done | Boot sequence, subsystem initialization |
| **AI Detector** | `drone/ai/inference/detector.py` | ✅ Done | YOLOv8n TFLite offline detector |
| **ByteTracker** | `drone/ai/tracking/byte_tracker.py` | ✅ Done | Multi-object tracking with Re-ID support |
| **MAVLink** | `drone/flight/mavlink/interface.py` | ✅ Done | Pixhawk communication (PX4 + ArduPilot) |
| **Follow Ctrl** | `drone/flight/controllers/follow_controller.py` | ✅ Done | PID follow/tail/orbit controller |
| **Failsafe** | `drone/flight/failsafe/manager.py` | ✅ Done | Battery, GPS, heartbeat, geofence monitoring |
| **Video** | `drone/video/capture/pipeline.py` | ✅ Done | Dual-stream capture, recording, AI frame queue |
| **Navigation** | `drone/navigation/planner.py` | ✅ Done | Search patterns, waypoint management |
| **Delivery** | `drone/delivery/service.py` | ✅ Done | Servo-controlled payload release |
| **Sensors** | `drone/sensors/` | 🔲 TODO | Battery monitor, signal strength, IMU |
| **Patrol Ctrl** | `drone/flight/controllers/patrol_controller.py` | 🔲 TODO | Waypoint patrol logic |
| **Search Ctrl** | `drone/flight/controllers/search_controller.py` | 🔲 TODO | Rescue search logic |

### 4.2 GCS Modules (Laptop/PC)

| Module | File(s) | Status | Description |
|---|---|---|---|
| **GCS Backend** | `gcs/backend/main.py` | ✅ Done | FastAPI + WebSocket + command API |
| **GCS Frontend** | `gcs/frontend/` | 🔲 TODO | Next.js web dashboard |
| **Video Relay** | `gcs/backend/video/` | 🔲 TODO | MediaMTX WebRTC relay |
| **Flight Logger** | `gcs/backend/models/` | 🔲 TODO | SQLite flight log storage |
| **Map Service** | Part of frontend | 🔲 TODO | MapLibre GL with drone position |

### 4.3 Supporting

| Module | File(s) | Status | Description |
|---|---|---|---|
| **Model Export** | `colab/model_export.ipynb` | ✅ Done | YOLOv8n → TFLite export notebook |
| **Pi Setup** | `scripts/setup_pi.sh` | ✅ Done | Full Pi 4B setup with telemetry blocking |
| **Requirements** | `drone/requirements.txt` | ✅ Done | Pi dependencies |
| **GCS Requirements** | `gcs/backend/requirements.txt` | ✅ Done | GCS dependencies |

---

## 5. Build Phases & Sprint Plan

### Phase 0 — Simulation & GCS Shell (Week 1-2)
**Goal:** GCS talks to a simulated drone. No hardware needed.

| Task | Description | Hours | Deps |
|---|---|---|---|
| 0.1 | Install PX4 SITL on dev machine | 2 | None |
| 0.2 | Connect GCS backend to SITL via MAVLink UDP | 4 | 0.1 |
| 0.3 | Build GCS frontend shell (Next.js) | 8 | None |
| 0.4 | Add telemetry WebSocket to frontend | 4 | 0.2, 0.3 |
| 0.5 | Add map with simulated drone position | 4 | 0.4 |
| 0.6 | Add command buttons (arm, takeoff, land, RTL) | 4 | 0.4 |
| 0.7 | Test full loop: GCS → SITL → GCS | 2 | All |

**Pass criteria:** GCS shows live telemetry from SITL, can arm/takeoff/land.

### Phase 1 — Bench Test: Pi + Pixhawk (Week 2-3)
**Goal:** Pi reads Pixhawk heartbeat over UART. Props OFF.

| Task | Description | Hours | Deps |
|---|---|---|---|
| 1.1 | Flash Pixhawk firmware (PX4 or ArduPilot) | 2 | None |
| 1.2 | Calibrate sensors via QGroundControl (one time) | 2 | 1.1 |
| 1.3 | Configure TELEM2 for MAVLink 2 @ 921600 | 1 | 1.1 |
| 1.4 | Setup Pi OS Lite, run setup_pi.sh | 2 | None |
| 1.5 | Wire Pixhawk TELEM2 → Pi UART | 1 | 1.3, 1.4 |
| 1.6 | Run drone agent, verify heartbeat | 2 | 1.5 |
| 1.7 | Test MAVLink commands (arm attempt, mode set) | 2 | 1.6 |
| 1.8 | Connect GCS to Pi via USB/WiFi | 2 | 1.6, Phase 0 |

**Pass criteria:** Pi reads heartbeat, attitude, GPS from Pixhawk. GCS shows it.

### Phase 2 — Camera & AI (Week 3-4)
**Goal:** Detector + tracker running on Pi with live camera.

| Task | Description | Hours | Deps |
|---|---|---|---|
| 2.1 | Export YOLOv8n to TFLite (Colab notebook) | 2 | None |
| 2.2 | Copy model to Pi, test inference speed | 2 | 2.1, Phase 1 |
| 2.3 | Run detector on live camera feed | 4 | 2.2 |
| 2.4 | Add ByteTracker, verify stable IDs | 4 | 2.3 |
| 2.5 | Test detection on recorded video first | 2 | 2.1 |
| 2.6 | Measure end-to-end FPS and latency | 2 | 2.4 |
| 2.7 | Test with Pi handheld, walking around people | 2 | 2.4 |

**Pass criteria:** 8+ FPS detection with stable track IDs on live camera.

### Phase 3 — Video Streaming (Week 4-5)
**Goal:** Live video from Pi to GCS browser.

| Task | Description | Hours | Deps |
|---|---|---|---|
| 3.1 | Setup local streaming (Pi → laptop via WiFi) | 4 | Phase 2 |
| 3.2 | Add detection overlay metadata to stream | 4 | 3.1 |
| 3.3 | Integrate video player in GCS frontend | 4 | 3.1, Phase 0 |
| 3.4 | Add target selection (click to follow in GCS) | 4 | 3.2, 3.3 |
| 3.5 | Measure latency (glass-to-glass) | 2 | 3.3 |

**Pass criteria:** Operator sees live video with detection boxes in browser.

### Phase 4 — Follow Mode (Week 5-7)
**Goal:** Drone follows a person. Start on ground, then fly.

| Task | Description | Hours | Deps |
|---|---|---|---|
| 4.1 | Test follow controller with recorded video | 4 | Phase 2 |
| 4.2 | Test on Pi handheld: walk, verify velocity output | 4 | 4.1 |
| 4.3 | Test on Pi mounted on car/bike (no drone yet) | 4 | 4.2 |
| 4.4 | Wire follow controller to MAVLink velocity commands | 4 | 4.3, Phase 1 |
| 4.5 | TETHERED hover + follow test | 4 | 4.4, hardware ready |
| 4.6 | Free flight follow at low speed (3m/s max) | 4 | 4.5 |
| 4.7 | Tune PID gains based on flight data | 4 | 4.6 |
| 4.8 | Test lost-target recovery (hover → search → RTL) | 4 | 4.6 |

**Pass criteria:** Drone follows a walking person at 10m altitude, recovers when target lost.

### Phase 5 — Patrol & Search (Week 7-8)
**Goal:** Autonomous waypoint patrol and rescue search patterns.

| Task | Description | Hours | Deps |
|---|---|---|---|
| 5.1 | Build patrol controller (waypoint navigation) | 4 | Phase 1 |
| 5.2 | Add waypoint drawing to GCS map | 4 | Phase 3 |
| 5.3 | Test patrol in SITL first | 2 | 5.1, 5.2 |
| 5.4 | Test patrol on real drone | 4 | 5.3, Phase 4 |
| 5.5 | Test search patterns (expanding square) | 4 | 5.1 |
| 5.6 | Integrate search + detection (auto-lock on found person) | 4 | 5.5, Phase 2 |

**Pass criteria:** Drone patrols waypoints, auto-detects and follows found people.

### Phase 6 — Delivery (Week 8-9)
**Goal:** Drop payload at GPS coordinates.

| Task | Description | Hours | Deps |
|---|---|---|---|
| 6.1 | Wire and test servo mechanism | 2 | None |
| 6.2 | Implement delivery state machine | 4 | Phase 4 |
| 6.3 | Test GPS-targeted delivery | 4 | 6.2 |
| 6.4 | Test person-targeted delivery | 4 | 6.3, Phase 4 |

**Pass criteria:** Drone flies to location, drops payload, returns.

### Phase 7 — Hardening (Week 9-10)
**Goal:** Production-ready safety and reliability.

| Task | Description | Hours | Deps |
|---|---|---|---|
| 7.1 | Failsafe testing: deliberate RC loss | 2 | Phase 4 |
| 7.2 | Failsafe testing: deliberate link loss | 2 | Phase 4 |
| 7.3 | Failsafe testing: low battery simulation | 2 | Phase 4 |
| 7.4 | Geofence breach testing | 2 | Phase 4 |
| 7.5 | Security audit: GCS authentication | 4 | Phase 3 |
| 7.6 | Flight logging and replay | 4 | Phase 3 |
| 7.7 | Stress test: 30+ minute flight | 4 | All |

---

## 6. AI Model Strategy

### 6.1 Detection Model Selection

| Model | Size | FPS on Pi 4B | mAP | RAM | Decision |
|---|---|---|---|---|---|
| YOLOv8n (FP32 TFLite) | 12MB | 8-10 | 37.3 | ~50MB | ✅ **Default** |
| YOLOv8n (INT8 TFLite) | 4MB | 12-15 | 34-35 | ~25MB | ✅ **Speed option** |
| YOLOv8s | 42MB | 3-5 | 44.9 | ~100MB | ❌ Too slow |
| MobileNet SSD v2 | 6MB | 15-20 | 22.1 | ~30MB | Backup if YOLO fails |
| YOLOv5n | 7MB | 10-12 | 28.0 | ~40MB | Alternative |

### 6.2 Tracker Selection

| Tracker | Speed | Accuracy | RAM | Decision |
|---|---|---|---|---|
| ByteTrack | <3ms | High | ~10MB | ✅ **Selected** |
| DeepSORT | ~15ms | Higher | ~100MB | ❌ Too heavy for Pi |
| BoT-SORT | ~10ms | Highest | ~80MB | ❌ GPU needed |
| Simple IoU | <1ms | Low | ~1MB | Fallback |

### 6.3 Model Training (Google Colab)

The Colab notebook (`colab/model_export.ipynb`) handles:

1. **Download** YOLOv8-nano pretrained weights (COCO 80 classes)
2. **Export** to TFLite (INT8 and FP32 variants)
3. **Benchmark** inference speed
4. **Optional fine-tune** on custom surveillance/rescue dataset
5. **Memory budget** verification

Custom training data needed for:
- Person detection in aerial view (top-down perspective)
- Person in distress poses (lying down, waving)
- Rescue scenarios (flood, fire, forest)

### 6.4 Future Model Upgrades

| Upgrade | When | Benefit |
|---|---|---|
| Coral USB Accelerator | Phase 7+ | 4x inference speed |
| Person Re-ID model | Phase 4+ | Better tailing with occlusion |
| Pose estimation | Phase 7+ | Detect distress signals |
| Thermal camera | Phase 7+ | Night/smoke detection |

---

## 7. Hardware Wiring Guide

### 7.1 Pixhawk TELEM2 → Pi UART

```
Pixhawk TELEM2          Raspberry Pi 4B
┌──────────┐            ┌──────────┐
│ TX  ─────┼────────────┼─► RXD    │ (GPIO15, Pin 10)
│ RX  ◄────┼────────────┼── TXD    │ (GPIO14, Pin 8)
│ GND ─────┼────────────┼── GND    │ (Pin 6)
│ 5V  ─────┼── DO NOT ──┼── CONNECT│
└──────────┘            └──────────┘

⚠️  TX↔RX crossed (Pixhawk TX → Pi RX, Pi TX → Pixhawk RX)
⚠️  Both are 3.3V logic — NO level shifter needed
⚠️  Do NOT connect Pixhawk 5V to Pi — use separate power
```

### 7.2 Power Distribution

```
Battery (4S LiPo)
├── Power Module → Pixhawk (battery sensing + FC power)
├── 5V 5A UBEC → Raspberry Pi 4B (USB-C or GPIO 5V)
│                └── 4G Modem (if used)
└── ESC → Motors

⚠️  Pi needs clean, stable 5V 3A minimum
⚠️  Add 470-1000µF capacitor near modem
⚠️  Never power Pi from Pixhawk servo rail
```

### 7.3 Camera Connection

```
Pi Camera Module v2/v3
└── CSI ribbon cable → Pi Camera Port (lift tab, insert, press)

⚠️  Keep cable short and away from modem/ESC wires
⚠️  Cable is fragile — secure with tape
```

### 7.4 Servo (Delivery)

```
Delivery Servo
├── Signal → GPIO18 (Pin 12)
├── VCC → 5V from UBEC (NOT from Pi GPIO)
└── GND → Common ground

⚠️  Servo can draw 1A+ — never power from Pi 3.3V/5V pins
```

---

## 8. Software Stack & Dependencies

### 8.1 Drone (Pi 4B)

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| OS | Raspberry Pi OS Lite 64-bit | Latest | Headless Linux |
| Runtime | Python 3.11+ | 3.11 | All services |
| AI inference | tflite-runtime | 2.14+ | YOLOv8n detector |
| Computer vision | OpenCV | 4.8+ | Frame processing |
| MAVLink | pymavlink | 2.4+ | Pixhawk communication |
| Camera | Picamera2 | 0.3+ | Pi camera interface |
| Video encode | GStreamer (hardware) | 1.22+ | H.264 encoding |
| Tracking | Custom ByteTrack | - | Pure numpy |
| Monitoring | psutil | 5.9+ | System metrics |

### 8.2 GCS Backend

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Framework | FastAPI | 0.104+ | REST + WebSocket API |
| Server | Uvicorn | 0.24+ | ASGI server |
| MAVLink | pymavlink | 2.4+ | Drone communication |
| Database | SQLAlchemy + SQLite | 2.0+ | Flight logs |
| Validation | Pydantic | 2.5+ | Request/response schemas |

### 8.3 GCS Frontend (TODO)

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Framework | Next.js | 14+ | React SSR/SPA |
| Language | TypeScript | 5+ | Type safety |
| Map | MapLibre GL | 4+ | Drone position map |
| Video | WebRTC / WHEP | - | Live video player |
| Charts | Recharts | 2+ | Telemetry graphs |
| Styling | CSS / Tailwind | - | UI styling |

---

## 9. Testing Strategy

### 9.1 Test Progression (NEVER skip steps)

```
1. Simulation (SITL)     — No hardware risk
   ↓
2. Bench test (props OFF) — Verify wiring and comms
   ↓
3. Recorded video         — Test AI on pre-recorded footage
   ↓
4. Handheld Pi           — Walk around with Pi + camera
   ↓
5. Car/bike mounted      — Test at speed
   ↓
6. Tethered hover        — Drone constrained by rope
   ↓
7. Low & slow flight     — 2m altitude, 1m/s, open field
   ↓
8. Normal flight         — Full parameters, controlled area
```

### 9.2 Test Matrix

| Test | Method | Pass Criteria |
|---|---|---|
| Heartbeat | `drone/main.py` | Pi prints Pixhawk heartbeat within 3s |
| Telemetry | GCS WebSocket | Lat/lon/alt/battery update at 5Hz |
| Detection | Record video, run detector | 8+ FPS, persons detected |
| Tracking | Walk in front of camera | Stable ID for 30+ seconds |
| Follow sim | Handheld Pi, walk | Velocity output tracks person offset |
| Follow flight | Tethered drone | Drone follows at set distance |
| RTL | Cut RC | Drone returns to launch point |
| Battery FS | Lower threshold | Drone RTL on low battery |
| Geofence | Fly towards boundary | Drone stops / returns |
| GCS commands | Send via API | Drone responds to arm/takeoff/land |

### 9.3 SITL Testing Commands

```bash
# Install PX4 SITL (Ubuntu/WSL)
git clone https://github.com/PX4/PX4-Autopilot.git --recursive
cd PX4-Autopilot
make px4_sitl jmavsim

# Or ArduPilot SITL
sim_vehicle.py -v ArduCopter -f quad --map --console

# Connect GCS backend to SITL
# SITL broadcasts MAVLink on UDP 14550
# Set in GCS config: mavlink_connection = "udpin:0.0.0.0:14550"
```

---

## 10. Safety & Legal

### 10.1 Safety Hierarchy

```
Layer 1: RC manual override (hardware, always works)
Layer 2: Pixhawk firmware failsafes (works even if Pi crashes)
Layer 3: Guardia failsafe manager (smarter, faster software response)
Layer 4: GCS operator commands (requires link)
```

### 10.2 Failsafe Matrix

| Condition | Detection | Action | Implemented By |
|---|---|---|---|
| RC signal lost | No RC heartbeat for 3s | RTL | Pixhawk firmware |
| Pi crashes | No setpoints for 0.5s | Exit offboard → failsafe | Pixhawk firmware |
| Battery low (15%) | Voltage monitoring | RTL | Guardia failsafe + Pixhawk |
| Battery critical (5%) | Voltage monitoring | LAND immediately | Guardia failsafe + Pixhawk |
| GPS lost | Fix type < 3 | HOVER (hold position) | Guardia failsafe |
| Geofence breach | Distance > radius | RTL | Guardia failsafe + Pixhawk |
| GCS link lost | No GCS heartbeat 10s | HOVER → RTL | Guardia failsafe |
| Target lost (follow) | No detection 5s | HOVER → search/RTL | Guardia agent |
| CPU overheat | temp > 82°C | WARN → throttle AI | Guardia failsafe |

### 10.3 India Legal (Drone Rules 2021)

| Requirement | Action |
|---|---|
| Registration | Register on Digital Sky (digitalsky.dgca.gov.in) |
| Category | Nano (<250g) exempt from most rules. Micro (250g-2kg) needs registration |
| No-fly zones | Check Digital Sky map. No airports, military, national parks |
| BVLOS | Special permission required for beyond visual line of sight |
| Altitude | Max 400ft (120m) for micro/small |
| Insurance | Required for small/medium |
| Tracking | Only if > 2kg |

### 10.4 Ethical Guidelines

- Only track consenting people during testing
- No surveillance of private property without permission
- Rescue use requires coordination with authorities
- No autonomous weapon capability — delivery is for supplies only

---

## 11. No-Telemetry Implementation

### What we disable:

| Vector | How | File |
|---|---|---|
| Pi OS telemetry | Block domains in /etc/hosts | `scripts/setup_pi.sh` |
| Pi auto-updates | Disable apt timers | `scripts/setup_pi.sh` |
| Python packages | No analytics dependencies | `drone/requirements.txt` |
| AI model | TFLite inference, no cloud API | `drone/ai/inference/detector.py` |
| Config flags | `telemetry_enabled = False` | `drone/config/settings.py` |
| Global kill switch | `telemetry_global_disable = True` | `drone/config/settings.py` |
| GCS backend | `telemetry_to_cloud = False` | `drone/config/settings.py` |
| Network | Modem disabled by default | `drone/config/settings.py` |
| DNS blocking | Telemetry domains → 0.0.0.0 | `scripts/setup_pi.sh` |

### Blocked domains:
```
0.0.0.0 telemetry.raspberrypi.com
0.0.0.0 metrics.raspberrypi.com
0.0.0.0 analytics.google.com
0.0.0.0 crashlyticsreports-pa.googleapis.com
0.0.0.0 firebase-settings.crashlytics.com
```

### Verification:
```bash
# On the Pi, after setup:
cat /etc/hosts | grep "0.0.0.0"
systemctl list-timers | grep -i apt
ss -tulnp  # Should show NO outbound connections
tcpdump -i any -c 100  # Verify no unexpected traffic
```

---

## 12. Runbooks & SOPs

### 12.1 How to: First Boot (Day 1)

```bash
# 1. Flash Raspberry Pi OS Lite 64-bit to SD card (Raspberry Pi Imager)
#    - Set hostname: guardia
#    - Enable SSH, add your public key
#    - Set WiFi credentials (for initial setup)

# 2. Boot Pi, SSH in
ssh pi@guardia.local

# 3. Run setup script
cd ~/
git clone <your-repo> guardia
cd guardia/v2.0.1/scripts
chmod +x setup_pi.sh
sudo ./setup_pi.sh

# 4. Reboot (required for UART changes)
sudo reboot

# 5. After reboot, verify UART
ls -la /dev/serial0  # Should exist
# Wire Pixhawk TELEM2 to Pi GPIO 14/15

# 6. Copy AI model
scp yolov8n.tflite pi@guardia.local:~/guardia/v2.0.1/drone/ai/models/

# 7. Test
cd ~/guardia/v2.0.1/drone
source ~/guardia/venv/bin/activate
python main.py
```

### 12.2 How to: Run the GCS

```bash
# On your laptop/PC
cd v2.0.1/gcs/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py

# Open browser: http://localhost:8000/docs
# WebSocket: ws://localhost:8000/ws/telemetry
```

### 12.3 How to: Export AI Models (Colab)

```
1. Open v2.0.1/colab/model_export.ipynb in Google Colab
2. Run all cells
3. Download guardia_models.zip
4. Extract and copy yolov8n.tflite to Pi:
   scp yolov8n_float32.tflite pi@guardia.local:~/guardia/v2.0.1/drone/ai/models/yolov8n.tflite
```

### 12.4 How to: Pre-Flight Checklist

```
□ Battery fully charged (>90%)
□ Props secure, no damage
□ Camera lens clean
□ SD card has space for recording
□ GPS has 3D fix (>6 satellites)
□ RC transmitter on, bound, and tested
□ Failsafe switch tested (flip and verify)
□ Geofence set for the flying area
□ Weather: wind < 20km/h, no rain
□ Area clear of people not involved in test
□ Emergency landing zone identified
□ Pi running, heartbeat confirmed
□ GCS connected (if using)
```

### 12.5 How to: Emergency Procedures

```
SITUATION: Drone not responding
  1. Flip RC failsafe switch → drone should RTL or LAND
  2. If no response: switch to manual mode on RC
  3. If still no response: cut throttle on RC
  4. If RC lost: wait for Pixhawk auto-RTL timeout

SITUATION: Drone flying away
  1. Flip RTL switch on RC
  2. If no response: flip kill switch
  3. If no RC: Pixhawk geofence should catch it
  4. Call the number on the drone label

SITUATION: Crash
  1. Disconnect battery IMMEDIATELY
  2. Check for fire or smoke
  3. Retrieve and inspect for damage
  4. Check flight logs for cause
```

---

## 13. Risk Register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Pi overheats in flight | Medium | Medium | Heatsink + fan, throttle AI if hot |
| GPS loss at altitude | Low | High | Pixhawk holds position on IMU |
| Camera cable disconnect (vibration) | Medium | Medium | Secure cable, use tape |
| 4G modem resets from power ripple | High | Low | Capacitor, dedicated UBEC |
| Wind exceeds drone capability | Medium | High | Pre-flight weather check, geofence |
| TFLite model too slow | Low | Medium | INT8 model or lower resolution |
| Pixhawk UART baud mismatch | Medium | Low | Test at 921600 first, fall back to 115200 |
| Battery sag under load | Medium | High | Conservative voltage thresholds |
| SD card corruption | Low | Medium | Use quality card, minimize writes |
| Servo fails (delivery) | Low | Medium | Test mechanism before flight |

---

## 14. Decision Log

| # | Decision | Options Considered | Chosen | Reason |
|---|---|---|---|---|
| D1 | Flight firmware | PX4, ArduPilot | **PX4** (default), ArduPilot (supported) | Both supported. PX4 has cleaner offboard API |
| D2 | AI model | YOLOv8n, YOLOv5n, MobileNet | **YOLOv8n** | Best speed/accuracy tradeoff on Pi |
| D3 | Inference runtime | TFLite, NCNN, OpenVINO | **TFLite** | Best Pi support, official YOLO export |
| D4 | Tracker | ByteTrack, DeepSORT, BoT-SORT | **ByteTrack** | Lightweight, no GPU needed |
| D5 | MAVLink library | pymavlink, MAVSDK | **pymavlink** | More control, lower overhead |
| D6 | GCS backend | FastAPI, Flask, Django | **FastAPI** | WebSocket native, async, fast |
| D7 | GCS frontend | Next.js, Vue, plain HTML | **Next.js** | React ecosystem, SSR |
| D8 | Video transport | SRT, RTSP, WebRTC | **SRT→WebRTC** | SRT for reliability, WebRTC for browser |
| D9 | No telemetry | Opt-in, opt-out, blocked | **Hard blocked** | Privacy first, can enable later |
| D10 | Comms link | WiFi, 4G, LoRa | **WiFi → 4G** | WiFi for dev, 4G for deployment |

---

## 15. Cost Breakdown (INR)

### Already Owned
- Pixhawk flight controller
- Raspberry Pi 4B (8GB RAM)
- RC transmitter + receiver

### To Purchase

| Item | Min Cost (₹) | Max Cost (₹) | Priority |
|---|---|---|---|
| Pi Camera Module v2/v3 | 2,500 | 3,500 | P0 |
| GPS + Compass (M8N/M9N) | 1,500 | 4,000 | P0 |
| 5V 5A UBEC | 400 | 800 | P0 |
| Heatsink + fan for Pi | 200 | 500 | P0 |
| Cables, connectors, tape | 300 | 600 | P0 |
| **Subtotal (minimum viable)** | **4,900** | **9,400** | |
| 4G LTE Modem (SIM7600) | 4,000 | 8,000 | P1 |
| LTE Antennas (2x) | 500 | 1,200 | P1 |
| Data SIM (Jio/Airtel) | 300/mo | 700/mo | P1 |
| Delivery servo | 200 | 500 | P2 |
| Coral USB Accelerator | 6,000 | 8,000 | P3 |

### Recurring

| Item | Monthly (₹) |
|---|---|
| Data SIM | 300-700 |
| VPS (if needed) | 400-1,000 |

---

> **This document is alive. Update it as decisions change and phases complete.**
>
> Last updated: 2026-10-01
> Author: AI Agent (Tackle Studio)
