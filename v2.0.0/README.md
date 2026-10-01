# Guardia AI v2.0.0 — Autonomous Drone Surveillance & Rescue System

<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=26&pause=1000&color=FF6B35&center=true&vCenter=true&width=920&lines=Autonomous+Surveillance+%26+Rescue+Drone;Pixhawk+%2B+Raspberry+Pi+4B+%2B+Offline+AI;Track+%7C+Tail+%7C+Deliver+%7C+Rescue" alt="Guardia AI v2 banner" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Raspberry%20Pi%204B%20(8GB)-C51A4A?style=for-the-badge&logo=raspberry-pi" />
  <img src="https://img.shields.io/badge/Flight%20Controller-Pixhawk-0078D4?style=for-the-badge" />
  <img src="https://img.shields.io/badge/AI-Offline%20First-16a34a?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Telemetry-Disabled-ef4444?style=for-the-badge" />
  <img src="https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge" />
</p>

---

## What Is This?

Guardia AI v2 is a **fully autonomous drone system** designed for:
- **Surveillance** — patrol, monitor, detect threats autonomously
- **Rescue Missions** — locate and track people in disaster/emergency zones
- **Delivery** — deliver payloads to tracked targets
- **Person Tracking** — follow and tail specific individuals
- **Offline Operation** — all AI models run locally on Raspberry Pi 4B (8GB RAM)

### Key Principles
1. **No telemetry** — zero data leaves the drone unless explicitly commanded
2. **Offline AI** — YOLOv8-nano + ByteTrack + TFLite run entirely on-device
3. **Pixhawk integration** — MAVLink 2 over UART, custom GCS replaces QGC/Mission Planner
4. **8GB RAM budget** — every model and service tuned for Pi 4B constraints
5. **Custom GCS** — FastAPI + WebSocket backend, no dependency on QGroundControl for operations

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                    DRONE (Pi 4B)                     │
│                                                      │
│  ┌──────────┐  UART  ┌───────────┐  USB  ┌────────┐│
│  │ Pixhawk  │◄──────►│    Pi 4B  │◄─────►│4G Modem││
│  │ FC       │        │  Companion│       │(opt)   ││
│  └──────────┘        └───────────┘       └────────┘│
│       │                    │                         │
│  RC Receiver          Pi Camera                      │
│  (override)           + AI Stack                     │
│                                                      │
│  Services:                                           │
│  • mavlink-router     (MAVLink multiplexer)          │
│  • drone-agent        (flight controller + state)    │
│  • tracker-service    (YOLO + ByteTrack)             │
│  • video-service      (H.264 encode + stream)       │
│  • delivery-service   (payload management)           │
│  • nav-service        (path planning + geofence)     │
└─────────────────────────────────────────────────────┘
                         │ WireGuard (optional)
                         ▼
┌─────────────────────────────────────────────────────┐
│                  GCS (Ground Control)                 │
│                                                      │
│  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │ FastAPI Backend   │  │ Web Frontend (Next.js)   │ │
│  │ • MAVLink parser  │  │ • Live video + HUD       │ │
│  │ • Command API     │  │ • Map + waypoints        │ │
│  │ • WebSocket push  │  │ • Target selection       │ │
│  │ • Flight logging  │  │ • Mission planning       │ │
│  └──────────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
v2.0.0/
├── drone/                    # All onboard (Pi 4B) software
│   ├── core/                 # Core drone agent, state machine, config
│   ├── ai/                   # AI models, tracking, inference engine
│   │   ├── models/           # Model weights (.tflite, .onnx)
│   │   ├── tracking/         # ByteTrack, person re-ID
│   │   └── inference/        # TFLite/NCNN inference runners
│   ├── flight/               # Flight control, MAVLink, failsafes
│   │   ├── controllers/      # Follow, patrol, search controllers
│   │   ├── mavlink/          # MAVLink interface (MAVSDK/pymavlink)
│   │   └── failsafe/         # Failsafe manager, geofence
│   ├── video/                # Camera capture, encoding, streaming
│   ├── sensors/              # GPS, IMU, battery, signal monitoring
│   ├── navigation/           # Path planning, obstacle avoidance
│   ├── delivery/             # Payload drop and delivery logic
│   └── config/               # Hardware config, tuning parameters
├── gcs/                      # Ground Control Station
│   ├── backend/              # FastAPI backend
│   └── frontend/             # Next.js web frontend
├── colab/                    # Google Colab notebooks for model training
├── scripts/                  # Setup, deployment, calibration scripts
├── tests/                    # Test suites
└── docs/                     # Documentation
```

---

## Hardware Requirements

| Part | Role | Required |
|---|---|---|
| Pixhawk (2.4.8+) | Flight controller | ✅ |
| Raspberry Pi 4B (8GB) | Companion computer | ✅ |
| RC Transmitter/Receiver | Manual override | ✅ |
| Pi Camera Module v2/v3 | Vision + tracking | ✅ |
| GPS + Compass (M8N/M9N) | Navigation | ✅ |
| 5V 5A UBEC | Clean power for Pi | ✅ |
| 4G LTE Modem (optional) | Remote GCS link | Optional |

---

## Quick Start

```bash
# On Raspberry Pi 4B
cd v2.0.0/drone
pip install -r requirements.txt
python -m core.agent

# On GCS machine (laptop/PC)
cd v2.0.0/gcs/backend
pip install -r requirements.txt
python main.py

# For model training/export
# Open v2.0.0/colab/*.ipynb in Google Colab
```

---

## No Telemetry Policy

This system is built with **zero telemetry by default**:
- No analytics, crash reporting, or usage tracking
- No external API calls (all AI runs offline)
- Network communication only happens when explicitly enabled for GCS link
- All model inference is local on the Pi 4B
- Logs stay on-device unless manually exported

---

## Team — Tackle Studio
- **Aryan Bajpai** — System Architect, AI Lead
- **Tackle Studio** — Development

## License
MIT License — see LICENSE file.
