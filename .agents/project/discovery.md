# Discovery: Guardia AI v2.0.0

Locked summary: autonomous surveillance, person tracking, and emergency delivery drone powered by a Pixhawk 2.4.8 flight controller and a Raspberry Pi 4B (8GB RAM). Runs completely offline with zero telemetry dependencies, storing logs locally for retrieval.

## 1. Goal and Success Metric
- Primary goal: build an autonomous UAV system capable of person tailing, search and rescue patrol, and payload drop without relying on active cloud connectivity.
- Success metrics:
  - 10 to 15 FPS real-time person detection on Pi 4B CPU.
  - Zero telemetry data leak: 100% of flight control and decision logic runs on the edge.
  - Target tracking recovery within 3 seconds of occlusion.
  - Safe payload drop trigger within 1.5 meters lateral error at 3m altitude.

## 2. Audience and Context
- Operator: solo field technician, rescue worker, or developer using a laptop, tablet, or phone near the drone launch site.
- Flight environment: outdoors, open fields, variable lighting, zero internet or cellular connectivity.

## 3. Scope
- In scope:
  - Full flight controller integration with Pixhawk 2.4.8 (ArduPilot/PX4).
  - High-speed MAVLink companion computer link over USB or TELEM2 serial.
  - Edge object detection (YOLOv8n TFLite) and multi-object tracking (ByteTrack).
  - Autonomous follow controller maintaining stand-off distance and heading.
  - Autonomous payload release mechanism on PWM servo.
  - Local zero-telemetry blackbox flight logger (SQLite + MP4).
  - Local ad-hoc Wi-Fi GCS web interface.
  - Google Colab pipeline for training and exporting quantized models.
- Out of scope:
  - Remote cloud telemetry servers and cellular modems.
  - Dual thermal optical sensor fusion.
  - Swarm multi-drone coordination.

## 4. Constraints
- Hardware budget: ~44,500 INR total component BOM.
- Flight controller: Pixhawk 2.4.8 with STM32F427 microcontroller (2MB flash).
- Onboard computer: Raspberry Pi 4B with 8GB RAM, passive/active heatsink cooling.
- Power: 4S LiPo battery (14.8V nominal, 5200mAh) with 5.3V 3A UBEC for Pi.
- Safety: dedicated hardware RC kill switch and geofence RTL must always take priority over autonomous code.

## 5. Proposed Directions
1. Cloud-tethered 4G stream: high latency, data cost, cellular dead-zone risk.
2. Fully offline edge autonomous (Chosen): all inference, flight control, and blackbox recording happen on Pi 4B + Pixhawk 2.4.8. Zero dependency on external networks.
3. Micro-controller only without companion computer: unable to run modern computer vision or deep learning models.

## 6. Pre-Mortem: 5 Failure Modes and Guards
1. Companion computer crashes or hangs mid-flight:
   - Guard: Pixhawk heartbeat timeout failsafe (COM_OF_LOSS_T = 0.5s) immediately switches flight mode to Loiter or Return to Launch (RTL).
2. Pi 4B thermal throttling drops inference framerate:
   - Guard: aluminum armor case with dual fans; inference capped at 320x320 resolution and 10 to 12 FPS target rate.
3. Target lost due to rapid motion or visual occlusion:
   - Guard: follow controller enters 5-second loiter search mode; if target is not re-acquired, drone climbs 5m and holds position or returns home.
4. Payload servo jams or drops prematurely:
   - Guard: two-stage software arming command (ARM_DELIVERY + CONFIRM_DROP) with altitude interlock (>2m and <5m).
5. Pixhawk clone flash or sensor inconsistency:
   - Guard: explicit ArduCopter fmuv3 firmware pin with calibrated MPU6000 and external compass on mast.

## 7. Assumptions and Blockers
- ASSUMED: Operator has standard 2.4GHz RC transmitter (FlySky FS-i6X or Radiomaster) for manual safety override.
- Blocker: None blocking architecture and code execution.
