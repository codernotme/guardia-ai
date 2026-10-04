"""
Guardia AI v2.0.0 — Flight Safety Mode Switcher
===============================================
Sets ARMING_CHECK = 1 to re-enable all pre-arm safety checks
before taking the drone outside for real flights.
"""

import sys
import time
from pymavlink import mavutil

def set_flight_mode(port="COM5", baud=115200):
    print(f"Connecting to Pixhawk on {port} at {baud}...")
    try:
        mav = mavutil.mavlink_connection(port, baud=baud)
        msg = mav.wait_heartbeat(timeout=4)
        if not msg:
            print("No heartbeat received!")
            return False
    except Exception as e:
        print(f"Connection error: {e}")
        return False

    print("Setting ARMING_CHECK -> 1 (Full Pre-Flight Safety Checks Enabled)...")
    mav.mav.param_set_send(
        mav.target_system,
        mav.target_component,
        b"ARMING_CHECK",
        1.0,
        mavutil.mavlink.MAV_PARAM_TYPE_REAL32,
    )
    time.sleep(0.5)

    # Verify
    mav.mav.param_request_read_send(
        mav.target_system,
        mav.target_component,
        b"ARMING_CHECK",
        -1,
    )
    t0 = time.time()
    while time.time() - t0 < 3:
        msg = mav.recv_match(type="PARAM_VALUE", blocking=False)
        if msg and msg.param_id == "ARMING_CHECK":
            print(f"✅ Verified: ARMING_CHECK is now {msg.param_value}")
            break
        time.sleep(0.01)

    mav.close()
    print("\nFlight safety mode active. All sensors must pass checks before arming.")
    return True

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else "COM5"
    baud = int(sys.argv[2]) if len(sys.argv) > 2 else 115200
    set_flight_mode(port, baud)
