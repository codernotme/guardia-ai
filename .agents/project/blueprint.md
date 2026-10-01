# Blueprint: Guardia AI v2.0.0

Locked summary: defines 6 core domains (flight, perception, mission, delivery, storage, gcs), user and autonomous mission flows, component inventory, local SQLite entities, and ordered vertical slices for the autonomous drone system.

## 1. Domains
1. `flight`: Pixhawk 2.4.8 MAVLink 2.0 communication, arming, attitude/velocity setpoints, failsafe monitor.
2. `perception`: Camera capture, YOLOv8n object detection, ByteTrack person tracking, target re-identification.
3. `mission`: High-level autonomous coordinator: state machine, follow controller, waypoint patrol, search patterns.
4. `delivery`: Payload latch servo control, drop altitude validation, release confirmation.
5. `storage`: Local zero-telemetry blackbox logger, SQLite flight telemetry, local MP4 video recorder.
6. `gcs`: Local offline Ground Control Station, FastAPI REST/WebSocket server, telemetry visualizer.

## 2. Sitemap and Views (Local GCS Web UI)
- `/`: Primary Tactical HUD. Shows live local video, target lock reticle, artificial horizon, battery, flight mode.
- `/missions`: Mission Planner. Waypoint upload, patrol route builder, search grid generator, geofence radius.
- `/delivery`: Payload Release Panel. Cargo status, armed indicator, altitude check, manual drop override button.
- `/blackbox`: Local Flight Log Browser. Historical flight sessions, telemetry charts, exportable CSV/JSON, video clips.
- `/settings`: Hardware and Parameters. Pixhawk connection status, serial port selection, AI confidence thresholds.

## 3. Mission Flows
- Follow Mission:
  `Select target in camera view > Arm drone > Takeoff to 10m > Lock track ID > Compute lateral/range velocity > Stream MAVLink setpoints > Maintain 6m distance > Target lost 5s timeout > Hold position > Operator command`
- Search and Rescue Patrol:
  `Define search polygon > Generate expanding square grid > Auto takeoff > Fly waypoints at 15m > Run person detector > Target spotted > Switch to loiter over target > Log GPS coordinates to blackbox > Notify operator`
- Emergency Payload Delivery:
  `Navigate above target GPS > Descend to 3.0m drop altitude > Check hover stability (<0.2 m/s drift) > Arm delivery servo > Actuate PWM drop latch > Confirm payload release via sensor > Climb to 15m safe altitude > Return to launch`
- RC Override Failsafe:
  `Autonomous mode active > Operator flips RC CH5 switch to Manual/Stabilize > Pixhawk cuts offboard control > Manual pilot controls drone`

## 4. Component Inventory
- `flight/mavlink-client`: MAVLink connection manager, heartbeat daemon, message sender.
- `flight/telemetry-parser`: Decodes GLOBAL_POSITION_INT, ATTITUDE, SYS_STATUS, BATTERY_STATUS.
- `flight/failsafe-guard`: Watches heartbeat latency, battery thresholds, geofence limits.
- `perception/frame-grabber`: OpenCV / Picamera2 video capture thread at 30 FPS.
- `perception/yolo-detector`: TFLite INT8 inference runner for 320x320 frames.
- `perception/track-manager`: ByteTrack multi-object association and Kalman filter tracker.
- `mission/state-engine`: Core autonomous state machine (IDLE, TAKEOFF, PATROL, FOLLOW, DROP, RTL).
- `mission/follow-pid`: Proportional derivative controller generating forward velocity and yaw rate.
- `mission/search-grid`: Geometric waypoint generator for expanding square and parallel swath searches.
- `delivery/servo-actuator`: PWM pulse generator on Pixhawk AUX1 or Pi GPIO 18.
- `delivery/drop-validator`: Altitude and velocity gate keeper before releasing cargo.
- `storage/blackbox-db`: SQLite time-series recorder for flight data, alerts, and target detections.
- `storage/video-writer`: Local rotating H.264 MP4 file saver on Pi microSD card.
- `gcs/hud-overlay`: Front-end tactical heads up display with artificial horizon and target lock boxes.
- `gcs/mavlink-bridge`: Local WebSocket broadcasting telemetry frames at 10 Hz to connected browsers.

## 5. Entities
- `FlightSession`: session_id, start_time, end_time, initial_battery, drone_id.
- `TelemetryFrame`: timestamp, session_id, lat, lon, alt_rel, vx, vy, vz, pitch, roll, yaw, battery_v, armed, mode.
- `TargetDetection`: detection_id, session_id, timestamp, class_name, confidence, bbox_x, bbox_y, bbox_w, bbox_h, track_id.
- `DeliveryEvent`: event_id, session_id, timestamp, target_lat, target_lon, drop_altitude, status.
- `FailsafeIncident`: incident_id, session_id, timestamp, trigger_type, action_taken.

## 6. Integrations
- Pixhawk 2.4.8: MAVLink 2.0 protocol over serial (USB /dev/ttyACM0 or UART /dev/serial0).
- Pi Camera Module 3 / v2: CSI ribbon cable via libcamera/Picamera2.
- Local GCS: FastAPI WebSocket + REST on Pi Wi-Fi AP (192.168.4.1:8000).

## 7. Vertical Slices (Ordered by Risk)
- S1 Flight Link: Pixhawk 2.4.8 MAVLink handshake, heartbeat, telemetry stream, mode commanding.
- S2 Perception Engine: Video capture + TFLite YOLOv8n + ByteTrack running on Pi 4B CPU.
- S3 Follow Controller: Visual tracking feedback to MAVLink velocity setpoints in closed loop.
- S4 Delivery Subsystem: Servo release mechanism, altitude interlocks, drop logs.
- S5 Zero Telemetry Storage: SQLite blackbox logging, MP4 recording, offline data export.
- S6 Local GCS Station: Web HUD, map plotting, mission dispatch, telemetry streaming.
