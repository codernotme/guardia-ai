# Guardia AI v2.0.1 — Pixhawk Setup Guide
## Complete Flight Controller Configuration

---

## 1. Identify Your Pixhawk

Before anything else, identify your exact board:

| Board | Processor | Flash | Supported FW | Notes |
|---|---|---|---|---|
| Pixhawk 1 (3DR) | STM32F427 | 2MB | PX4, ArduPilot | Original |
| Pixhawk 2.4.8 (clone) | STM32F427 | 2MB | PX4, ArduPilot | Most common cheap clone |
| Pixhawk 4 | STM32F765 | 2MB | PX4, ArduPilot | Recommended |
| Pixhawk 4 Mini | STM32F765 | 2MB | PX4, ArduPilot | Compact |
| Cube Orange | STM32H743 | 2MB | ArduPilot (mainly) | Premium |
| mRo Pixhawk | STM32F427 | 2MB | PX4, ArduPilot | Quality clone |

**⚠️ If your board has only 1MB flash, recent firmware may not fit. Check the PX4/ArduPilot supported hardware list.**

---

## 2. Flash Firmware (One-Time)

### 2.1 Using QGroundControl

> QGroundControl is ONLY used for initial setup. After this, our custom GCS handles everything.

1. Download QGroundControl: http://qgroundcontrol.com
2. Connect Pixhawk via USB
3. Go to **Vehicle Setup → Firmware**
4. Select firmware:
   - **PX4** (recommended for offboard/follow mode)
   - **ArduPilot** (alternative, mature guided mode)
5. Click "OK" to flash
6. Wait for completion

### 2.2 Choose PX4 vs ArduPilot

| Feature | PX4 | ArduPilot |
|---|---|---|
| Offboard mode | First-class, clean API | "Guided" mode, slightly different |
| MAVSDK support | Full | Partial |
| pymavlink support | Full | Full |
| Community | Growing | Massive, more tutorials |
| Failsafes | Good | Very mature |
| Our code support | ✅ Both supported | ✅ Both supported |

**Default: PX4.** Switch to ArduPilot if your board doesn't support recent PX4.

---

## 3. Sensor Calibration

### In QGroundControl → Vehicle Setup:

1. **Accelerometer** — Follow the rotation prompts (6 positions)
2. **Gyroscope** — Place on flat surface, don't touch
3. **Compass** — Rotate in all orientations
4. **Level Horizon** — Place level, click calibrate
5. **Radio Setup** — Bind RC transmitter, calibrate sticks

### Important:
- Calibrate compass AWAY from motors and metal
- GPS/compass should be on a mast, not near the battery
- Re-calibrate if you change the physical setup

---

## 4. Configure TELEM2 for Companion Computer

### PX4 Parameters (set in QGC → Parameters)

```
MAV_1_CONFIG = TELEM 2
MAV_1_MODE = Onboard
MAV_1_RATE = 0             (maximum rate)
MAV_1_FORWARD = 1          (forward to other MAVLink instances)
SER_TEL2_BAUD = 921600     (match Pi serial config)
```

### ArduPilot Parameters

```
SERIAL2_PROTOCOL = 2       (MAVLink2)
SERIAL2_BAUD = 921          (921600 baud)
```

### Verify
After setting parameters, reboot the Pixhawk and check the TELEM2 LED blinks.

---

## 5. Failsafe Configuration

### PX4 Failsafes

```
# RC Loss
NAV_RCL_ACT = 2            (Return to launch)
COM_RC_LOSS_T = 3.0         (3 second timeout)

# Data Link (GCS) Loss
NAV_DLL_ACT = 0            (Disabled — we handle this in software)
COM_DL_LOSS_T = 10          (10 second timeout)

# Low Battery
COM_LOW_BAT_ACT = 3         (Return to launch)
BAT_LOW_THR = 0.15          (15% remaining)
BAT_CRIT_THR = 0.05         (5% remaining)
BAT_EMERGEN_THR = 0.03      (3% — emergency land)

# Geofence
GF_ACTION = 3               (Return to launch)
GF_MAX_HOR_DIST = 150       (150m radius)
GF_MAX_VER_DIST = 50        (50m altitude)

# Offboard mode loss
COM_OF_LOSS_T = 0.5          (0.5s before exiting offboard)
COM_OBL_ACT = 1              (Hold position on offboard loss)
COM_OBL_RC_ACT = 1           (Position mode on offboard loss if RC available)
```

### ArduPilot Failsafes

```
# RC Loss
FS_THR_ENABLE = 1           (Enabled, RTL)
FS_THR_VALUE = 975           (PWM threshold)

# GCS Loss
FS_GCS_ENABLE = 1           (Enabled, RTL)

# Battery
BATT_FS_LOW_ACT = 2         (RTL on low)
BATT_LOW_VOLT = 14.0        (14V for 4S = 3.5V/cell)
BATT_FS_CRT_ACT = 1         (Land on critical)
BATT_CRT_VOLT = 13.2        (13.2V for 4S = 3.3V/cell)

# Geofence
FENCE_ENABLE = 1
FENCE_TYPE = 7               (Circle + altitude + floor)
FENCE_RADIUS = 150           (150m)
FENCE_ALT_MAX = 50           (50m)
FENCE_ACTION = 1             (RTL)
```

---

## 6. RC Setup

### Required Switches

| Switch | Function | Channel |
|---|---|---|
| Flight mode | MANUAL ↔ STABILIZE ↔ OFFBOARD | CH5 |
| Kill switch | Emergency motor kill | CH6 |
| RTL switch | Return to launch | CH7 (or combine with mode) |

### PX4 Flight Mode Mapping
```
RC_MAP_FLTMODE = 5           (Channel 5 for flight mode)
COM_FLTMODE1 = Manual
COM_FLTMODE4 = Position
COM_FLTMODE6 = Offboard      (for autonomous)
```

### ArduPilot Flight Mode Mapping
```
FLTMODE_CH = 5
FLTMODE1 = 0                 (Stabilize)
FLTMODE4 = 5                 (Loiter)
FLTMODE6 = 4                 (Guided — for autonomous)
```

---

## 7. Frame Configuration

### ESC Protocol
```
# PX4
PWM_MAIN_RATE = 400          (400Hz for most ESCs)

# ArduPilot
MOT_PWM_TYPE = 0             (Normal)
MOT_PWM_MIN = 1000
MOT_PWM_MAX = 2000
```

### Motor Order
- Check PX4 or ArduPilot docs for your frame type
- Verify motor spin direction
- Test with props OFF first

---

## 8. Pre-Flight Verification

After all configuration, with Pixhawk connected to Pi:

```bash
# On the Pi
cd ~/guardia/v2.0.1/drone
source ~/guardia/venv/bin/activate
python3 -c "
import asyncio
from flight.mavlink.interface import MAVLinkInterface

async def test():
    mav = MAVLinkInterface('/dev/serial0', 921600)
    if await mav.connect():
        print('✅ Pixhawk connected!')
        print(f'  Flight mode: {mav.telemetry.flight_mode}')
        print(f'  Armed: {mav.telemetry.armed}')
        print(f'  GPS fix: {mav.telemetry.gps_fix_type}')
        print(f'  Battery: {mav.telemetry.battery_voltage:.1f}V')
    else:
        print('❌ Connection failed')
    await mav.disconnect()

asyncio.run(test())
"
```

Expected output:
```
✅ Pixhawk connected!
  Flight mode: MANUAL
  Armed: False
  GPS fix: 3
  Battery: 16.4V
```

---

## 9. Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| No heartbeat | UART not configured | Check `dtoverlay=disable-bt` in /boot/config.txt |
| No heartbeat | Wrong baud rate | Try 115200, 57600, 921600 |
| No heartbeat | TX/RX not crossed | Swap TX and RX wires |
| No heartbeat | Serial console active | Run `sudo raspi-config` → Interface → Serial → disable console |
| "Permission denied" on /dev/serial0 | User not in dialout group | `sudo usermod -aG dialout pi` |
| GPS no fix | Antenna obstructed | Move GPS to open sky, away from metal |
| Compass errors | Interference | Mount compass on mast, away from motors/battery |
| ESC beeping | Not calibrated | Calibrate ESCs in QGC |
| Motor wrong direction | Motor wire order | Swap any 2 of the 3 motor wires |
