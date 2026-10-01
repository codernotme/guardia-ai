"""
Unit tests for Guardia AI v2.0.0 configuration settings.
Verifies Pixhawk 2.4.8 hardware defaults and strict zero-telemetry policy.
"""

import unittest
import sys
import os

# Add drone to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "drone")))

from config.settings import get_config, reset_config, SystemConfig


class TestSettings(unittest.TestCase):
    def setUp(self):
        reset_config()

    def tearDown(self):
        reset_config()

    def test_pixhawk_248_defaults(self):
        """Verify Pixhawk 2.4.8 parameters."""
        config = get_config()
        hw = config.hardware
        self.assertEqual(hw.pixhawk_model, "pixhawk_2_4_8")
        self.assertEqual(hw.pixhawk_baud_rate, 921600)
        self.assertEqual(hw.pixhawk_servo_channel, 9)  # AUX1
        self.assertIn("/dev/ttyACM0", hw.pixhawk_fallback_ports)
        self.assertIn("/dev/serial0", hw.pixhawk_fallback_ports)

    def test_zero_telemetry_enforcement(self):
        """Ensure all cloud telemetry flags are strictly False."""
        config = get_config()
        self.assertTrue(config.telemetry_global_disable)
        self.assertFalse(config.ai.telemetry_enabled)
        self.assertFalse(config.ai.analytics_enabled)
        self.assertFalse(config.ai.crash_reporting)
        self.assertFalse(config.gcs.telemetry_to_cloud)
        self.assertFalse(config.hardware.modem_enabled)

    def test_battery_4s_thresholds(self):
        """Verify 4S LiPo power thresholds."""
        hw = get_config().hardware
        self.assertEqual(hw.battery_cells, 4)
        self.assertAlmostEqual(hw.battery_low_voltage * hw.battery_cells, 14.0)
        self.assertAlmostEqual(hw.battery_critical_voltage * hw.battery_cells, 13.2)


if __name__ == "__main__":
    unittest.main()
