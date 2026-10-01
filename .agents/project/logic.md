# Logic: Guardia AI v2.0.0 State Machines & Controllers

Locked summary: deterministic state machines for the master flight coordinator, target visual tracking loop, payload release safety interlocks, and failsafe execution hierarchy.

## 1. Master Drone State Machine
States: `UNCONNECTED > DISARMED_STANDBY > PREFLIGHT_CHECK > ARMED > TAKEOFF > MISSION_RUNNING > RTL > LANDING > DISARMED`
- `UNCONNECTED`: waiting for Pixhawk 2.4.8 heartbeat. Event: `HEARTBEAT_RECV` -> `DISARMED_STANDBY`.
- `DISARMED_STANDBY`: motors idle. Operator triggers `CMD_PREFLIGHT` -> `PREFLIGHT_CHECK`.
- `PREFLIGHT_CHECK`: runs 8 sensor & model health checks. If all PASS -> `ARMED`. If FAIL -> `DISARMED_STANDBY` with error.
- `ARMED`: motors spinning at min throttle. Event `CMD_TAKEOFF(alt=10m)` -> `TAKEOFF`.
- `TAKEOFF`: climbing vertically at 1.0 m/s until alt >= 9.5m. Event `ALT_REACHED` -> `MISSION_RUNNING`.
- `MISSION_RUNNING`: sub-states:
  - `SUB_PATROL`: following waypoint route at 15m.
  - `SUB_SEARCH`: flying expanding square search pattern.
  - `SUB_FOLLOW`: visual person tracking.
  - `SUB_DELIVERY`: descending and releasing cargo.
- `RTL`: climbs to RTL altitude (15m) if below, flies straight to home coordinates, loiters 5s, descends -> `LANDING`.
- `LANDING`: descending at 0.5 m/s. Ground contact detected via baro/accel -> disarm motors -> `DISARMED`.

## 2. Visual Follow State Machine
States: `IDLE > SEARCHING > ACQUIRING > LOCKED_TRACKING > OCCLUDED > LOST_HOLD`
- `IDLE`: video streaming, detector dormant. Event: `CMD_ENGAGE_FOLLOW` -> `SEARCHING`.
- `SEARCHING`: detector runs on 320x320 frames at 10 FPS. When person detected with confidence >= 0.40 -> `ACQUIRING`.
- `ACQUIRING`: ByteTrack tracks person across 3 consecutive frames. If track ID matches or user selects -> `LOCKED_TRACKING`.
- `LOCKED_TRACKING`: PID loop computes error:
  - Yaw error = (target_center_x - frame_center_x) / frame_width -> yaw_rate = Kp_yaw * error.
  - Range error = (target_box_height - desired_box_height) -> forward_vel = Kp_range * error.
  - Generates MAVLink `SET_POSITION_TARGET_LOCAL_NED` (type_mask 0b0000111111000111: velocity + yaw rate).
  - Streamed at 20 Hz to Pixhawk 2.4.8.
- `OCCLUDED`: target disappears from frame. Drone holds last known velocity for 1.0s, then stops and hovers. Timer starts (0 to 5s).
  - If re-detected with Re-ID score > 0.60 within 5s -> `LOCKED_TRACKING`.
  - If timeout 5.0s expires -> `LOST_HOLD`.
- `LOST_HOLD`: drone hovers in place at 10m, rotates 360 degrees slowly (10 deg/s) to search area. If no target found -> notify operator and hold position.

## 3. Payload Delivery Safety Interlock State Machine
States: `LOCKED > PRE_DROP_HOVER > ALTITUDE_CHECK > ARMED_FOR_DROP > RELEASING > CONFIRMED_DEPLOYED > POST_DROP_CLIMB`
- Interlocks:
  - Altitude must be between 2.5m and 4.0m above target ground level.
  - Horizontal drift velocity must be < 0.3 m/s.
  - Battery voltage must be > 14.0V (sufficient margin to climb out).
  - Software confirmation flag required (`ARM_PAYLOAD` sent within 5 seconds before `EXECUTE_DROP`).
- Actuation:
  - Pulse Pixhawk AUX1 servo pin to 2000 us (release angle) for 1500 ms, then return to 1000 us.
- Outcome:
  - Immediately command vertical climb back to safe transit altitude (15m) at 1.5 m/s.

## 4. Failsafe Priority Hierarchy (Higher overrides lower)
1. Hardware RC Manual Switch (CH5): absolute highest priority. Instantly cuts offboard mode in Pixhawk silicon.
2. Battery Critical (Voltage <= 13.2V / 3.3V per cell): triggers immediate auto-land wherever the drone is.
3. Battery Low (Voltage <= 14.0V / 3.5V per cell): aborts current mission, triggers auto-RTL to home coordinates.
4. MAVLink Companion Heartbeat Loss (timeout > 0.5s): Pixhawk auto-switches from OFFBOARD to LOITER/HOLD.
5. Geofence Breach (radius > 150m or alt > 50m): triggers immediate RTL back inside fence.
6. Target Lost Timeout (5.0s): stops following, holds position, notifies operator.
