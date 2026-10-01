# Guardia AI v2.0.0 — Pixhawk 2.4.8 Hardware & Setup Guide

Autonomous flight controller configuration for Guardia AI v2.0.0. Specifically tailored for the Pixhawk 2.4.8 flight controller interfaced with a Raspberry Pi 4B (8GB RAM) companion computer.

---

## 1. Pixhawk 2.4.8 Architecture & Specifications

The Pixhawk 2.4.8 is an open-hardware flight controller based on the 3DR Pixhawk FMUv3 design.

| Specification | Value | Notes |
|---|---|---|
| Main Processor | STM32F427VI ARM Cortex-M4F @ 168 MHz | Hardware FPU, 256 KB RAM, 2 MB Flash |
| Failsafe Co-processor | STM32F100 32-bit Cortex-M0 | Handles manual RC pass-through and failsafes |
| Primary IMU | InvenSense MPU6000 3-axis accel/gyro | High vibration tolerance over internal SPI bus |
| Secondary IMU | ST Micro LSM303D (accel/mag) + L3GD20 (gyro) | Redundant sensor suite over SPI |
| Barometer | Measurement Specialties MS5611 | High precision altitude estimation |
| Compass | External HMC5883L / QMC5883L | Mounted on GPS mast via I2C |
| Operating Voltage | 4.8V to 5.4V DC | Must be powered via 3DR Power Module BEC |
| MicroSD Card | FAT32 formatted, up to 32GB | Stores high-rate DataFlash binary logs (.bin) |

> [!IMPORTANT]
> Firmware target: Select **FMUv3** (NOT FMUv2) when flashing ArduPilot or PX4. The STM32F427 on Pixhawk 2.4.8 features the revision 3 silicon with the full 2MB flash, which avoids the 1MB flash allocation bug of legacy boards and supports all autonomous features.

---

## 2. Port Pinouts and Connector Reference

Pixhawk 2.4.8 uses DF13 / Molex PicoBlade style 1.25mm pitch locking connectors.

```
       PIXHAWK 2.4.8 TOP VIEW CONNECTOR MAP
+---------------------------------------------------+
|  [TELEM1]   [TELEM2]    [GPS]     [I2C]    [CAN]  |
|   6-pin      6-pin      6-pin     4-pin    4-pin  |
|                                                   |
|  [POWER]                                          |
|   6-pin                    [SAFETY SWITCH] 2-pin  |
|                            [PIEZO BUZZER]  2-pin  |
|                                                   |
|  [RC IN] === 3-pin (SBUS/PPM Inverter built-in)   |
|                                                   |
|  MAIN OUT 1-8  [ - + S ] (ESCs: CH 1-4)           |
|  AUX OUT  1-6  [ - + S ] (Payload Servo: AUX1=CH9)|
+---------------------------------------------------+
```

### TELEM2 Pinout (Companion Computer Serial Link)
| Pin # | Wire Name | Voltage Level | Destination on Raspberry Pi 4B |
|---|---|---|---|
| 1 | VCC | +5V DC | DO NOT CONNECT (Power Pi via dedicated UBEC) |
| 2 | TXD (Out) | 3.3V TTL | Pi 4B Pin 10 (GPIO 15 / RXD0) |
| 3 | RXD (In) | 3.3V TTL | Pi 4B Pin 8 (GPIO 14 / TXD0) |
| 4 | CTS | 3.3V TTL | Optional (Leave unconnected) |
| 5 | RTS | 3.3V TTL | Optional (Leave unconnected) |
| 6 | GND | 0V Ground | Pi 4B Pin 6 or 9 (Ground) |

### POWER Port Pinout (From 3DR Power Module)
| Pin # | Description | Notes |
|---|---|---|
| 1, 2 | VCC (+5.3V) | Clean regulated power to Pixhawk |
| 3 | Current Sense | Analog 0V to 3.3V (17.0 Amps per Volt) |
| 4 | Voltage Sense | Analog 0V to 3.3V (10.1 Voltage Divider) |
| 5, 6 | GND (Ground) | System common ground |

### AUX OUT Pinout (Payload Delivery Servo)
| Channel | Function | Parameter Setting | Description |
|---|---|---|---|
| AUX 1 (Pin 9) | Payload Drop Servo | `SERVO9_FUNCTION = 0` (or `28`) | Actuated via MAVLink `MAV_CMD_DO_SET_SERVO` |
| AUX 2 (Pin 10) | Secondary Release | `SERVO10_FUNCTION = 0` | Optional auxiliary release latch |

> [!WARNING]
> Servo Rail Power: The + (center) pin on the AUX and MAIN rail does NOT output 5V power from the Pixhawk power module. To power a delivery servo on AUX1, connect a 5V BEC or powered ESC 5V wire to the center pin of any unused servo slot on the rail.

---

## 3. Connecting Raspberry Pi 4B to Pixhawk 2.4.8

Guardia AI v2.0.0 supports two connection methods. Option 1 is recommended for initial assembly and testing.

### Option 1: Direct USB Cable (Recommended)
Connect a high-quality shielded USB-A to Micro-USB cable from any USB 2.0 / 3.0 port on the Raspberry Pi 4B directly to the Micro-USB port on the side of the Pixhawk 2.4.8.
- Device node: `/dev/ttyACM0` (or symlinked by udev rule).
- Baud rate: 921600 or 115200.
- Advantages: built-in hardware flow control, high noise immunity, no jumper wire soldering.

### Option 2: TELEM2 UART Serial
Connect Pixhawk TELEM2 to Pi 4B GPIO 14/15:
- Device node: `/dev/serial0` (UART0).
- Baud rate: 921600 baud.
- Pi OS configuration required in `/boot/firmware/config.txt` (or `/boot/config.txt`):
  ```ini
  enable_uart=1
  dtoverlay=disable-bt
  ```
  Disable Linux serial console in `/boot/firmware/cmdline.txt` (remove `console=serial0,115200`).

---

## 4. Firmware Installation

Use Mission Planner (Windows) or QGroundControl (Linux / macOS / Windows) to flash the latest stable firmware:

1. Connect Pixhawk 2.4.8 via USB to your workstation computer.
2. In Mission Planner, go to **Setup → Install Firmware**.
3. Select **ArduCopter v4.4+ (fmuv3)**.
4. Wait for the audio beeps confirming successful flashing.

---

## 5. Critical Parameters Configuration

Connect to Pixhawk in Mission Planner, open **Config → Full Parameter Tree**, and configure the following parameters:

### 5.1 Serial Companion Computer Link
```ini
SERIAL2_PROTOCOL = 2       # MAVLink 2.0 protocol on TELEM2
SERIAL2_BAUD = 921          # 921600 baud rate (or 115 for 115200)
```
If using USB connection (`/dev/ttyACM0`), Pixhawk auto-detects MAVLink 2 on the USB virtual serial port.

### 5.2 Battery Monitor Calibration (3DR Power Module)
```ini
BATT_MONITOR = 4           # Analog voltage and current
BATT_VOLT_PIN = 2          # Pixhawk voltage ADC pin
BATT_CURR_PIN = 3          # Pixhawk current ADC pin
BATT_VOLT_MULT = 10.1      # Standard 3DR voltage divider ratio
BATT_AMP_PERVLT = 17.0     # Amperes per volt calibration factor
```

### 5.3 Zero-Telemetry & Failsafe Parameters (Offline Missions)
In zero-telemetry mode, the drone operates autonomously without an active internet link. Setting these parameters prevents unexpected failsafe RTL triggers during autonomous follow missions:

```ini
FS_GCS_ENABLE = 0          # Disabled. Prevents RTL when outside local GCS range!
FS_THR_ENABLE = 1          # RC Throttle Failsafe: Enabled (RTL on RC transmitter loss)
FS_THR_VALUE = 975         # PWM threshold for RC loss detection
BATT_FS_LOW_ACT = 2        # Return to Launch (RTL) when battery hits low voltage
BATT_LOW_VOLT = 14.0       # 14.0V threshold for 4S LiPo (3.5V per cell)
BATT_FS_CRT_ACT = 1        # Emergency Land immediately on critical battery
BATT_CRT_VOLT = 13.2       # 13.2V threshold for 4S LiPo (3.3V per cell)
FENCE_ENABLE = 1           # Hardware geofence active
FENCE_TYPE = 7             # Circle radius + maximum altitude
FENCE_RADIUS = 150         # 150 meters maximum horizontal distance
FENCE_ALT_MAX = 50         # 50 meters maximum vertical altitude
FENCE_ACTION = 1           # Return to Launch if geofence breached
ARMING_CHECK = 1           # All pre-arm safety checks enabled
```

### 5.4 Payload Drop Servo Configuration (AUX1)
```ini
SERVO9_FUNCTION = 0        # Manual / MAVLink DO_SET_SERVO control
SERVO9_MIN = 1000          # 1000 us (locked position)
SERVO9_MAX = 2000          # 2000 us (open release position)
SERVO9_TRIM = 1000         # Default resting state
```

### 5.5 RC Transmitter Mapping (FlySky FS-i6X)
Configure your 6 to 10 channel RC transmitter with SBUS receiver connected to Pixhawk `RC IN`:
```ini
FLTMODE_CH = 5             # Channel 5 controls primary flight modes
FLTMODE1 = 0               # STABILIZE (Manual pilot recovery)
FLTMODE4 = 5               # LOITER (GPS position hold)
FLTMODE6 = 4               # GUIDED (Companion computer autonomous control)
RC6_OPTION = 32            # Channel 6 switch: Emergency Motor Interlock / Kill switch
```

---

## 6. Sensor Calibration Workflow

Before arming or testing autonomous modes, complete these calibrations in Mission Planner under **Setup → Mandatory Hardware**:

1. **Accelerometer Calibration**: Place Pixhawk level, then follow prompts to place on left side, right side, nose down, nose up, and back.
2. **Compass Calibration**: Rotate the drone on all 3 axes outdoors, away from metal structures and high-voltage power lines, until the calibration bar fills green.
3. **Radio Calibration**: Move transmitter sticks and switches to all extreme limits to record PWM ranges (1000 to 2000 us).
4. **ESC Calibration**:
   - REMOVE ALL PROPELLERS.
   - Push throttle to maximum, power on drone, power cycle, push throttle to zero. Listen for confirmation beeps.

---

## 7. Companion Verification Script

Run this verification script on the Raspberry Pi 4B to confirm full communication with the Pixhawk 2.4.8:

```bash
cd ~/guardia/v2.0.0/drone
source ~/guardia/venv/bin/activate
python3 -c "
import asyncio
from flight.mavlink.interface import MAVLinkInterface

async def verify():
    print('Testing Pixhawk 2.4.8 communication...')
    mav = MAVLinkInterface(port='/dev/ttyACM0', baud=921600, firmware='ardupilot')
    connected = await mav.connect()
    if not connected:
        print('Retrying on UART serial port /dev/serial0...')
        mav = MAVLinkInterface(port='/dev/serial0', baud=921600, firmware='ardupilot')
        connected = await mav.connect()

    if connected:
        print('=========================================')
        print('✅ PIXHAWK 2.4.8 HANDSHAKE SUCCESSFUL')
        print('=========================================')
        await asyncio.sleep(1.0)
        t = mav.telemetry
        print(f'Flight Mode    : {t.flight_mode}')
        print(f'Arm Status     : {\"ARMED\" if t.armed else \"DISARMED\"}')
        print(f'Battery        : {t.battery_voltage:.2f}V ({t.battery_remaining}%)')
        print(f'GPS Satellites : {t.gps_satellites} (Fix Type: {t.gps_fix_type})')
        print(f'Heading        : {t.heading:.1f} deg')
        print(f'Roll / Pitch   : {t.roll:.2f} rad / {t.pitch:.2f} rad')
        
        # Test servo channel 9 (AUX1)
        print('Testing AUX1 payload servo command...')
        await mav.set_servo(9, 1000)
        print('✅ AUX1 locked at 1000 us')
    else:
        print('❌ Failed to establish communication with Pixhawk 2.4.8')
    await mav.disconnect()

asyncio.run(verify())
"
```

Expected terminal output:
```
Testing Pixhawk 2.4.8 communication...
Attempting Pixhawk 2.4.8 connection on: /dev/ttyACM0 @ 921600 baud
Waiting for Pixhawk heartbeat on /dev/ttyACM0...
✅ Pixhawk 2.4.8 connected on /dev/ttyACM0 | system=1 component=1 | firmware=ardupilot
=========================================
✅ PIXHAWK 2.4.8 HANDSHAKE SUCCESSFUL
=========================================
Flight Mode    : STABILIZE
Arm Status     : DISARMED
Battery        : 15.20V (85%)
GPS Satellites : 12 (Fix Type: 3)
Heading        : 142.5 deg
Roll / Pitch   : 0.01 rad / -0.02 rad
Testing AUX1 payload servo command...
Setting Pixhawk servo ch 9 to 1000 us
✅ AUX1 locked at 1000 us
```

---

## 8. Pixhawk 2.4.8 Troubleshooting

| Symptom | Cause | Solution |
|---|---|---|
| Main LED flashes yellow (double beep) | Pre-arm check failure | Connect GCS to read pre-arm error (e.g. compass uncalibrated or no GPS lock). |
| No heartbeat on `/dev/ttyACM0` | USB cable is power-only or permissions issue | Use data-capable micro-USB cable. Add user to dialout: `sudo usermod -aG dialout pi`. |
| No heartbeat on `/dev/serial0` | Serial console active or baud mismatch | Disable serial console in `raspi-config`. Set `SERIAL2_BAUD = 921` in Pixhawk. |
| Voltage reading inaccurate | Divider ratio uncalibrated | Measure LiPo with digital multimeter, adjust `BATT_VOLT_MULT` in Mission Planner. |
| Bad Compass Health | Magnetometer near power wires | Raise GPS/compass puck on 14cm mast away from battery and motor ESC lines. |
| Offboard control rejected | No 3D GPS lock or arming required | Ensure GPS has >= 8 satellites (`gps_fix_type >= 3`) before entering Guided mode. |
| Servo doesn't move on AUX1 | No 5V power on servo rail | Connect 5V BEC power to the center pin of the Pixhawk servo output rail. |
