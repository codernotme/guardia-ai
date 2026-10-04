"""
Guardia AI v2.0.0 — Pixhawk 2.4.8 Configuration Script
======================================================
Sets essential ArduCopter parameters for Quad-X, FlySky FS-i6 RC,
HC-05 Bluetooth telemetry, and GCS Guided precision control.
"""

import sys
import time
from pymavlink import mavutil

DEFAULT_PARAMS = {
    # Frame definition
    "FRAME_CLASS": 1.0,        # 1 = Quadrotor
    "FRAME_TYPE": 1.0,         # 1 = X-frame
    
    # Telemetry Ports
    # SERIAL1 = TELEM1 (HC-05 Bluetooth transceiver)
    "SERIAL1_BAUD": 57.0,      # 57 = 57600 baud
    "SERIAL1_PROTOCOL": 2.0,   # 2 = MAVLink 2
    
    # SERIAL2 = TELEM2 (Future Raspberry Pi Companion Computer)
    "SERIAL2_BAUD": 921.0,     # 921 = 921600 baud high-speed companion link
    "SERIAL2_PROTOCOL": 2.0,   # 2 = MAVLink 2
    
    # Flight Modes for Channel 5 (FlySky FS-i6 SwC 3-pos switch / mixer)
    "FLTMODE_CH": 5.0,         # Channel 5 controls flight mode
    "FLTMODE1": 0.0,           # Position 1: STABILIZE (manual takeoff / baseline)
    "FLTMODE2": 2.0,           # Position 2: ALT_HOLD (smooth altitude hold)
    "FLTMODE3": 5.0,           # Position 3: LOITER (GPS position + alt hold)
    "FLTMODE4": 4.0,           # Position 4: GUIDED (Laptop GCS step/nudge control)
    "FLTMODE5": 6.0,           # Position 5: RTL (Return to Launch failsafe)
    "FLTMODE6": 9.0,           # Position 6: LAND
    
    # Battery Monitor (Standard 3DR Power Module)
    "BATT_MONITOR": 4.0,       # 4 = Analog Voltage and Current
    "BATT_VOLT_PIN": 2.0,      # Pixhawk A2 pin for voltage
    "BATT_CURR_PIN": 3.0,      # Pixhawk A3 pin for current
    
    # Safety & Failsafe
    "FS_THR_ENABLE": 1.0,      # 1 = RTL on RC signal loss
    "FS_GCS_ENABLE": 0.0,      # 0 = Disabled so Bluetooth short drop doesn't trigger RTL while RC active
    "BRD_SAFETY_DEFLT": 0.0,   # 0 = Safety switch disabled or enabled based on setup
}

def configure_pixhawk(port="COM5", baud=115200):
    print(f"Connecting to Pixhawk on {port} at {baud} baud...")
    try:
        mav = mavutil.mavlink_connection(port, baud=baud)
        msg = mav.wait_heartbeat(timeout=5)
        if not msg:
            print("Failed to receive heartbeat!")
            return False
        print(f"Connected: Autopilot {msg.autopilot}, Type {msg.type}")
    except Exception as e:
        print(f"Connection error: {e}")
        return False

    print("\nApplying recommended parameters...")
    for param_name, param_val in DEFAULT_PARAMS.items():
        print(f"  Setting {param_name} -> {param_val}...")
        mav.mav.param_set_send(
            mav.target_system,
            mav.target_component,
            param_name.encode("utf-8"),
            param_val,
            mavutil.mavlink.MAV_PARAM_TYPE_REAL32,
        )
        time.sleep(0.05)

    # Verify parameters
    print("\nVerifying written parameters...")
    verified = {}
    for param_name in DEFAULT_PARAMS.keys():
        mav.mav.param_request_read_send(
            mav.target_system,
            mav.target_component,
            param_name.encode("utf-8"),
            -1,
        )

    t0 = time.time()
    while time.time() - t0 < 4:
        msg = mav.recv_match(type="PARAM_VALUE", blocking=False)
        if msg:
            verified[msg.param_id] = msg.param_value
        time.sleep(0.01)

    print("\nVerification Results:")
    for k, v in DEFAULT_PARAMS.items():
        val = verified.get(k, "NOT_FOUND")
        status = "OK" if val == v else f"MISMATCH (read: {val})"
        print(f"  {k:18} = {val} [{status}]")

    mav.close()
    print("\nPixhawk parameter setup finished.")
    return True

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else "COM5"
    baud = int(sys.argv[2]) if len(sys.argv) > 2 else 115200
    configure_pixhawk(port, baud)
