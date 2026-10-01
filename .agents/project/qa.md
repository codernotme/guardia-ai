# QA & Launch: Guardia AI v2.0.0 Verification Matrix

Locked summary: systematic verification protocol covering benchtop hardware testing, sensor calibration, software-in-the-loop validation, and field flight readiness checks.

## 1. Benchtop Hardware Verification Matrix (Props OFF)

| Test ID | Subsystem | Procedure | Expected Result | Pass Criteria |
|---|---|---|---|---|
| HW-01 | Pixhawk Handshake | Connect Pi 4B to Pixhawk 2.4.8 via USB or TELEM2, run `interface.py` | Heartbeat received within 500ms, firmware identified as ArduCopter/PX4 | MAVLink packets > 10 Hz |
| HW-02 | Telemetry Streams | Query ATTITUDE, GLOBAL_POSITION_INT, SYS_STATUS | Real-time roll/pitch values reflect physical board tilt | Zero packet drops in 60s |
| HW-03 | RC Override Priority | Switch to GUIDED mode, then toggle RC CH5 switch to STABILIZE | Offboard loop terminates immediately, RC control restored | < 50ms takeover time |
| HW-04 | Servo Payload Drop | Send `MAV_CMD_DO_SET_SERVO` to AUX1 or toggle GPIO 18 | Servo sweeps from 1000us (lock) to 2000us (release) | Physical latch opens |
| HW-05 | Battery Monitor | Measure battery with multimeter vs GCS voltage readout | Voltage matches within 0.1V | Multimeter delta <= 0.1V |
| HW-06 | Motor Spin Direction | Arm via Mission Planner test utility (PROPS OFF) | Motors 1-4 spin in Quad-X configuration (CW/CCW correct) | Visual verification |

## 2. AI Perception & Vision Benchmarks (Pi 4B 8GB)

| Test ID | Benchmark | Input Format | Target Metric | Minimum Acceptable |
|---|---|---|---|---|
| AI-01 | YOLOv8n Inference Time | 320x320 INT8 TFLite, 4 CPU threads | 65 ms to 80 ms | < 100 ms (>= 10 FPS) |
| AI-02 | ByteTrack Association | 10 active tracks in frame | < 5 ms per frame | < 10 ms |
| AI-03 | Video Capture Pipeline | Pi Camera Module 3 via libcamera | 30 FPS @ 1280x720 | >= 28 FPS |
| AI-04 | Target Re-ID Recovery | Person walks behind obstacle for 2s | Re-acquires same track ID | Recovery in <= 3 frames |

## 3. Failsafe Verification Protocol

1. Companion Disconnect Test:
   - Disconnect USB cable between Pi 4B and Pixhawk 2.4.8 while in GUIDED/OFFBOARD mode.
   - Verify Pixhawk enters LOITER/HOLD within 500ms (`COM_OF_LOSS_T = 0.5s`).
2. Battery Critical Failsafe Test:
   - Simulate 13.1V input using variable bench power supply.
   - Verify Pixhawk triggers Land failsafe (`BATT_FS_CRT_ACT = 1`).
3. Zero Telemetry Offline Leak Test:
   - Run network sniffer (`tcpdump -i eth0 -i wlan0`) during simulated mission.
   - Verify zero outbound packets to external WAN IPs (only local broadcast on 192.168.4.x).
