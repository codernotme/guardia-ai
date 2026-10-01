# Content: Guardia AI v2.0.0 Tactical Copy

Locked summary: exact string dictionary for telemetry readouts, flight status badges, emergency banners, pre-flight checklists, and voice/audio alert transcriptions.

## 1. Flight Status Badges
| State | Label Text | Color Token | Context |
|---|---|---|---|
| Connected | `FC CONNECTED [PIXHAWK 2.4.8]` | `--color-hud-success` | Valid heartbeat received |
| Disconnected | `NO FC HEARTBEAT` | `--color-hud-danger` | Serial link timeout > 1.0s |
| Armed | `PROPULSION ARMED` | `--color-hud-danger` | Motors active and spinning |
| Disarmed | `MOTORS SAFE [DISARMED]` | `--color-hud-dim` | Safety switch engaged or disarmed |
| Mode Offboard | `MODE: OFFBOARD / GUIDED` | `--color-hud-primary` | Companion AI controlling flight |
| Mode Loiter | `MODE: LOITER / HOLD` | `--color-hud-success` | GPS position hold active |
| Mode RTL | `MODE: RETURN TO LAUNCH` | `--color-hud-warning` | Returning to home point |
| Mode Manual | `MODE: MANUAL STABILIZE` | `--color-hud-dim` | Pilot manual RC control |

## 2. Target Acquisition Copy
- Unlocked: `SCANNING AIRSPACE: NO TARGET`
- Acquiring: `ACQUIRING CANDIDATE: {class} ({conf}%)`
- Locked: `TARGET LOCKED: ID #{track_id} | RANGE: {distance}m | BRG: {bearing}deg`
- Occluded: `TARGET OCCLUDED: HOLDING LAST KNOWN HEADING ({timer}s)`
- Lost: `TARGET LOST: SWITCHING TO LOITER SEARCH PATTERN`

## 3. Payload Delivery Copy
- Standby: `PAYLOAD LATCH: LOCKED [SAFETY ON]`
- Ready: `DELIVERY READY: ALTITUDE {alt}m WITHIN DROP ENVELOPE`
- Confirm prompt: `CONFIRM RELEASE: EMERGENCY MEDICAL CARGO`
- Deployed: `PAYLOAD DEPLOYED: LATCH OPEN CONFIRMED`
- Aborted: `DROP ABORTED: WIND / DRIFT SPEED EXCEEDS 0.5 M/S`

## 4. Pre-Flight Verification Checklist Strings
1. `CHECK 1: Pixhawk 2.4.8 MAVLink link established over /dev/serial0 or /dev/ttyACM0`
2. `CHECK 2: IMU sensors calibrated (MPU6000 + MS5611 Baro + External Magnetometer)`
3. `CHECK 3: 3D GPS satellite lock count >= 8 and HDOP < 1.5`
4. `CHECK 4: Battery voltage >= 14.8V (4S LiPo storage threshold)`
5. `CHECK 5: YOLOv8n TFLite neural model loaded on Pi 4B CPU`
6. `CHECK 6: Camera pipeline streaming at target 30 FPS`
7. `CHECK 7: Delivery servo mechanism responsive to test pulse`
8. `CHECK 8: RC transmitter link active with CH5 mode switch and CH6 kill switch`

## 5. Voice and Audio Alert Transcripts
- On lock: `"Target acquired. Tracking engaged."`
- On battery low: `"Warning. Battery at twenty percent. Plan recovery."`
- On critical failsafe: `"Alert. Failsafe triggered. Returning to launch."`
- On payload drop: `"Payload released. Confirm visual delivery."`
