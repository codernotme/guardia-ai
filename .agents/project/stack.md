# Stack: Guardia AI v2.0.0 Hardware & Software BOM

Locked summary: comprehensive hardware components with exact Pixhawk 2.4.8 specifications, Raspberry Pi 4B 8GB companion computer, software libraries, and complete cost breakdown in INR.

## 1. Hardware Bill of Materials (BOM) & INR Cost

| Component | Exact Model / Specification | Purpose | Cost (INR) |
|---|---|---|---|
| Flight Controller | Pixhawk 2.4.8 (STM32F427 168MHz, 2MB Flash, MPU6000, MS5611) | Attitude stabilization, motor control, failsafes | 5,800 |
| Companion Computer | Raspberry Pi 4 Model B (8GB RAM, Quad Cortex-A72 @ 1.8GHz) | Offline AI vision, ByteTrack, state coordinator | 7,200 |
| Camera Module | Raspberry Pi Camera Module 3 (Sony IMX708, autofocus, 12MP) | Visual target tracking, surveillance video capture | 2,800 |
| MicroSD Cards | 2x SanDisk Extreme 64GB U3 A2 MicroSD (1 for Pi, 1 for Pixhawk) | OS, models, blackbox SQLite DB, flight logs | 1,800 |
| Drone Frame | F450 Quadcopter Frame with integrated PCB power distribution | Structural chassis, 450mm wheelbase | 1,400 |
| Brushless Motors | 4x EMAX MT2213 935KV Brushless DC Motors (CW / CCW) | Main quadcopter propulsion | 4,200 |
| Electronic Speed Cont | 4x SimonK / BLHeli 30A ESC with 5V BEC | Motor speed regulation (PWM 400Hz) | 2,600 |
| Propellers | 2 pairs 1045 (10x4.5) Carbon Nylon Propellers + 1 spare pair | Thrust generation | 600 |
| GPS & Compass | u-blox NEO-M8N GPS Module with external compass & mast | 3D positional navigation & heading hold | 2,900 |
| Power Module | 3DR XT60 Power Module (5.3V 2.5A BEC + Current/Volt Sensor) | Clean Pixhawk power + battery telemetry monitoring | 950 |
| Companion UBEC | Matek 5V 3A Step-Down UBEC (7V-26V to 5V 3A) | Clean isolated power dedicated to Pi 4B | 650 |
| Flight Battery | Orange / Gens Ace 4S 5200mAh 35C LiPo Battery (XT60) | Main propulsion & system power source | 4,500 |
| LiPo Balance Charger | IMAX B6AC 80W Dual Power Balance Charger | Safe multi-cell balance charging | 2,200 |
| RC Transmitter & RX | FlySky FS-i6X 10CH 2.4GHz Transmitter with FS-iA10B RX (SBUS) | Manual safety override, mode switch, kill switch | 4,800 |
| Delivery Mechanism | MG996R Metal Gear High-Torque Servo + 3D printed cargo latch | Autonomous medical / emergency payload drop | 650 |
| Cooling & Cables | Pi 4B Dual-fan Aluminum Armor Heatsink + DF13 6-pin cables | Thermal throttling prevention & UART link | 1,450 |
| **Total Hardware BOM** | | | **44,500 INR** |

## 2. Software Stack
- Flight Controller Firmware: ArduCopter 4.4+ fmuv3 (or PX4 fmu-v3). Guided mode for companion computer velocity/yaw control.
- Companion OS: Raspberry Pi OS 64-bit Lite (Debian Bookworm, kernel 6.6+ with 64-bit ARM NEON/v8 acceleration).
- Companion Flight Link: Python 3.11 with `pymavlink` 2.4+ (MAVLink 2.0). Connects via `/dev/ttyACM0` (USB) or `/dev/serial0` (TELEM2 UART) at 921600 baud.
- Perception Engine: `tflite-runtime` 2.14+ (or ONNX Runtime ARM64) executing INT8-quantized YOLOv8n (320x320) + ByteTrack Kalman filter.
- Camera Pipeline: `picamera2` / `libcamera` with OpenCV 4.8+ for zero-copy frame retrieval.
- Local Storage: Python standard `sqlite3` for high-throughput blackbox telemetry and events; OpenCV VideoWriter for H.264 local MP4 recording.
- Local Ground Control Station:
  - Backend: `fastapi` + `uvicorn` serving REST endpoints and WebSockets on port 8000.
  - Network: Pi 4B onboard Wi-Fi configured as an ad-hoc Access Point (`hostapd` + `dnsmasq`, SSID: `Guardia-Drone-Offline`, IP: 192.168.4.1).
  - Frontend: Vanilla HTML5, CSS3, and JavaScript HUD. Zero external CDN dependencies, fully self-contained for offline fields.
- Training & Model Conversion: Google Colab with PyTorch, Ultralytics YOLOv8, and TensorFlow Lite converter.

## 3. Rejected Alternatives
- Raspberry Pi Zero 2W: insufficient RAM (512MB) and thermal capacity for real-time 10 FPS YOLOv8n + ByteTrack.
- Jetson Nano 4GB: high cost (18,000+ INR), high idle power draw (10W), discontinued board support.
- 4G LTE Live Telemetry: rejected to satisfy strict user zero telemetry requirement and eliminate cellular dead-zone flight risks.
