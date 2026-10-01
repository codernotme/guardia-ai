# Status: Guardia AI v2.0.0 (Autonomous Drone System)

Type: app | drone robotics embedded
Budget: 45,000 INR hardware BOM | Deadline: Q4 2026 | Owner approvals needed: Aryan Bajpai (Tacklestudioz)

## Locked decisions
- D1 Version target: project version is strictly v2.0.0. All code, paths, docs, and configs use v2.0.0.
- D2 Flight controller hardware: Pixhawk 2.4.8 (STM32F427 Cortex-M4F, 2MB Flash, ArduPilot Copter fmuv3 / PX4 fmu-v3).
- D3 Companion computer: Raspberry Pi 4B (8GB RAM, Quad Cortex-A72 @ 1.8GHz, Raspberry Pi OS 64-bit Lite).
- D4 Zero telemetry mode: default flight mode is completely offline. No active 4G or cloud telemetry uplink during flight missions.
- D5 Perception runtime: local LiteRT (TFLite) CPU inference running YOLOv8n (320x320) + ByteTrack for person/vehicle tracking.
- D6 Flight link interface: MAVLink 2.0 via Pi 4B USB (/dev/ttyACM0) or TELEM2 UART (/dev/serial0) at 921600 baud.
- D7 Delivery mechanism: PWM servo drop mechanism on Pixhawk AUX1 or Pi 4B GPIO 18, actuated via MAVLink DO_SET_SERVO or local trigger.
- D8 Local GCS station: FastAPI backend + lightweight web HUD served locally over Pi 4B Wi-Fi Access Point (192.168.4.1).

## Assumptions (ASSUMED)
- A1 Pixhawk 2.4.8 uses ArduCopter 4.4+ fmuv3 firmware with Guided mode for companion control, raised by stack agent.
- A2 Offline blackbox logging stores telemetry and vision events to local SQLite and rotating MP4 video on Pi 4B microSD, raised by data agent.
- A3 User trains and exports INT8/FP16 quantized YOLOv8 models in Google Colab, then transfers weights via local SCP/USB, raised by brainstorm agent.

## Open blockers
- B1 Initial flight testing space: requires open field with no obstructions, default manual RC takeover enabled.

## Parking lot (not in scope)
- 4G cellular telemetry live streaming to AWS/GCP (deferred until zero telemetry validation passes).
- Dual camera thermal FLIR sensor fusion (v2.1 consideration).
- Swarm coordination mesh networking (v3.0 roadmap).

## Ledger files
| File | Agent | State | Summary (one line) |
| --- | --- | --- | --- |
| discovery.md | brainstorm | locked | Autonomous follow and rescue drone requirements, constraints, and pre-mortem. |
| blueprint.md | blueprint | locked | 6 core domains, mission state flows, component inventory, and vertical slices. |
| design.md | tsz-design-system | locked | Dark tactical HUD design system, tokens, SVG artificial horizon, and badges. |
| content.md | content | locked | Tactical HUD labels, telemetry keys, audio announcements, and pre-flight prompts. |
| logic.md | logic | locked | State machines for drone master, tracking loop, delivery drop, and failsafes. |
| data.md | data | locked | Blackbox SQLite schema, MAVLink message structures, and zero telemetry buffer. |
| responsive.md | responsive | locked | GCS field display layouts at 375px mobile, 768px tablet, 1440px ground monitor. |
| motion.md | tsz-motion | locked | Gyro attitude smoothing, target box acquisition pulse, and radar sweep specs. |
| stack.md | stack | locked | Pixhawk 2.4.8, Pi 4B 8GB, LiteRT, FastAPI, and complete 44,500 INR BOM. |
| structure.md | structure | locked | Domain first folder layout, file roles, and element ID naming standards. |
| antislop.md | tsz-antislop | locked | Clean developer audit, verification of realistic robotics code without AI fluff. |
| qa.md | tsz-qa-launch | locked | Pre-flight hardware checklist, failsafe verification matrix, and benchmarks. |
| release.md | release | locked | Atomic git commit plan, v2.0.0 changelog, and clean handover. |

## Slices
| Slice | Domain | State | Notes |
| --- | --- | --- | --- |
| S1 | flight | done | MAVLink connection to Pixhawk 2.4.8, heartbeat, telemetry parsing, mode switch. |
| S2 | perception | done | Video capture pipeline, YOLOv8n detector, ByteTrack tracker. |
| S3 | mission | done | Follow controller, search patterns (expanding square), waypoint patrol. |
| S4 | delivery | done | Servo drop mechanism, drop height check, verification logs. |
| S5 | storage | done | Zero telemetry blackbox SQLite logger and local MP4 recorder. |
| S6 | gcs | done | Local FastAPI GCS, offline HUD endpoints, MAVLink bridge. |
