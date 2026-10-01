# Release Plan: Guardia AI v2.0.0

Locked summary: proposed release plan, commit structure, and changelog for Guardia AI v2.0.0. Awaiting user approval prior to running git commit operations.

## 1. Changelog Draft

### v2.0.0: Autonomous Follow & Rescue Drone (Pixhawk 2.4.8 + Pi 4B)
- Flight Controller Support:
  - Added full hardware configuration and tuning for Pixhawk 2.4.8 (STM32F427 2MB flash, FMUv3 target).
  - Added dual serial connectivity: auto-detects USB Micro-B (`/dev/ttyACM0`) or TELEM2 UART (`/dev/serial0`) at 921600 baud.
  - Implemented ArduPilot Guided mode and PX4 Offboard mode MAVLink 2.0 command loop.
- Offline Vision & Tracking:
  - Integrated local YOLOv8n INT8 TFLite object detector running at 10-12 FPS on Pi 4B 8GB CPU.
  - Implemented ByteTrack multi-object tracker with Kalman filter and visual Re-ID.
  - Added autonomous visual follow controller maintaining safe stand-off distance and target centering.
- Emergency Delivery Subsystem:
  - Implemented payload drop mechanism with dual actuation paths: Pixhawk AUX1 servo (`MAV_CMD_DO_SET_SERVO`) and Pi 4B GPIO 18.
  - Added safety interlocks enforcing stable hover drift (<0.3 m/s) and altitude bounds (2.5m to 4.0m) before release.
- Zero-Telemetry Blackbox Storage:
  - Implemented on-device SQLite blackbox database recording all telemetry frames, target coordinates, and mission events.
  - Added local rotating H.264 MP4 flight video recorder with storage cap auto-management.
  - Completely isolated flight logic from cloud and external networks.
- Local Offline Ground Control Station:
  - Added FastAPI backend with local WebSocket telemetry broadcaster and REST mission control.
  - Created standalone offline tactical HUD for field laptops, tablets, and smartphones over local Wi-Fi AP.
- Tacklestudioz Agent Architecture:
  - Established `.agents/project/` ledger system containing complete design, logic, data, stack, and verification plans.

## 2. Proposed Atomic Commit Plan
1. `chore(ledger): initialize Tacklestudioz agent pack ledgers for v2.0.0`
2. `refactor(v2.0.0): migrate codebase versioning from v2.0.1 to v2.0.0`
3. `feat(hardware): tune Pixhawk 2.4.8 parameters, pinouts, and dual serial links`
4. `feat(delivery): support Pixhawk AUX servo MAVLink actuation and safety interlocks`
5. `feat(storage): implement offline SQLite blackbox logger and local GCS web HUD`
6. `docs(guides): update Master Plan, Pixhawk 2.4.8 setup guide, and GCS manuals`

Note: Git commits will only be executed after user review and explicit approval.
