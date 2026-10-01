# Data: Guardia AI v2.0.0 Blackbox & Schema

Locked summary: local zero telemetry persistence architecture. Stores all sensor frames, detection bounding boxes, mission events, and errors in an embedded SQLite database (`flight_blackbox.db`) and local rotating MP4 video files.

## 1. Local SQLite Blackbox Database Schema

### Table: `flight_sessions`
- `session_id`: TEXT PRIMARY KEY (e.g. `SES_20261001_133000`)
- `start_time`: REAL NOT NULL (Unix epoch seconds)
- `end_time`: REAL (Unix epoch seconds, null if active)
- `start_battery_v`: REAL NOT NULL
- `end_battery_v`: REAL
- `drone_id`: TEXT DEFAULT 'GUARDIA_PI4_PIXHAWK248'
- `firmware_version`: TEXT DEFAULT 'v2.0.0'
- `total_waypoints`: INTEGER DEFAULT 0
- `flight_mode`: TEXT DEFAULT 'STANDBY'

### Table: `telemetry_blackbox`
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `session_id`: TEXT NOT NULL REFERENCES flight_sessions(session_id)
- `timestamp`: REAL NOT NULL
- `lat`: REAL NOT NULL
- `lon`: REAL NOT NULL
- `alt_rel_m`: REAL NOT NULL
- `alt_msl_m`: REAL NOT NULL
- `vx_ms`: REAL NOT NULL
- `vy_ms`: REAL NOT NULL
- `vz_ms`: REAL NOT NULL
- `pitch_deg`: REAL NOT NULL
- `roll_deg`: REAL NOT NULL
- `yaw_deg`: REAL NOT NULL
- `battery_v`: REAL NOT NULL
- `battery_pct`: REAL NOT NULL
- `armed`: INTEGER NOT NULL (0 or 1)
- `flight_mode`: TEXT NOT NULL
- `gps_fix_type`: INTEGER NOT NULL
- `satellites_visible`: INTEGER NOT NULL
- Indexes: `idx_telem_session_time ON telemetry_blackbox(session_id, timestamp)`

### Table: `target_detections`
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `session_id`: TEXT NOT NULL REFERENCES flight_sessions(session_id)
- `timestamp`: REAL NOT NULL
- `track_id`: INTEGER NOT NULL
- `class_name`: TEXT NOT NULL (e.g. 'person', 'car')
- `confidence`: REAL NOT NULL
- `bbox_x`: REAL NOT NULL (normalized 0.0 to 1.0)
- `bbox_y`: REAL NOT NULL
- `bbox_w`: REAL NOT NULL
- `bbox_h`: REAL NOT NULL
- `estimated_distance_m`: REAL
- `is_locked_target`: INTEGER DEFAULT 0
- Indexes: `idx_target_session ON target_detections(session_id, track_id)`

### Table: `mission_events`
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `session_id`: TEXT NOT NULL REFERENCES flight_sessions(session_id)
- `timestamp`: REAL NOT NULL
- `event_type`: TEXT NOT NULL (e.g. 'TAKEOFF', 'WAYPOINT_REACHED', 'TARGET_LOCKED', 'DROP_RELEASED', 'FAILSAFE_TRIGGERED')
- `severity`: TEXT NOT NULL ('INFO', 'WARNING', 'CRITICAL')
- `lat`: REAL
- `lon`: REAL
- `alt_m`: REAL
- `details_json`: TEXT

## 2. In-Memory Ring Buffer for Real-Time Streaming
- When local GCS is connected over Wi-Fi AP, telemetry frames are broadcast via WebSocket at 10 Hz from a circular memory buffer (capacity: 600 frames = 60 seconds).
- If Wi-Fi disconnects or drone flies out of range, the ring buffer continues writing uninterrupted to the local SQLite database.
- When GCS reconnects, it queries `/api/blackbox/sync?since={last_timestamp}` to fill in missing telemetry points.

## 3. Video Recording Storage Strategy
- Directory: `/home/pi/guardia/recordings/`
- Segment duration: 5 minutes per file (`flight_{session_id}_seg{N}.mp4`).
- Max total storage cap: 16GB (auto-deletes oldest sessions when free disk space < 2GB).
- Codec: H.264 Baseline Profile via Pi 4B hardware encoder or OpenCV VideoWriter.
