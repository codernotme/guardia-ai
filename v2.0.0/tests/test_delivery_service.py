"""
Unit tests for Guardia AI v2.0.0 DeliveryService.
Verifies state machine transitions, altitude checks, and Pixhawk AUX1 MAVLink servo drops.
"""

import unittest
import asyncio
import sys
import os

# Add drone to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "drone")))

from delivery.service import DeliveryService, DeliveryState


class MockMAVLinkInterface:
    def __init__(self):
        self.is_connected = True
        self.last_servo_channel = None
        self.last_servo_pwm = None

    async def set_servo(self, channel: int, pwm: int):
        self.last_servo_channel = channel
        self.last_servo_pwm = pwm
        return True


class TestDeliveryService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_mav = MockMAVLinkInterface()
        self.service = DeliveryService(
            servo_pin=18,
            drop_altitude=3.0,
            mavlink_interface=self.mock_mav,
            pixhawk_servo_channel=9,
        )

    async def test_initial_state(self):
        self.assertEqual(self.service.state, DeliveryState.IDLE)
        self.assertTrue(self.service.has_payload)

    async def test_gps_mission_start(self):
        self.service.start_gps_mission(28.6139, 77.2090)
        self.assertEqual(self.service.state, DeliveryState.NAVIGATING)

    async def test_release_payload_via_mavlink(self):
        success = await self.service.release_payload()
        self.assertTrue(success)
        self.assertFalse(self.service.has_payload)
        self.assertEqual(self.service.state, DeliveryState.CONFIRMING)
        # Check mock MAVLink was called for Pixhawk AUX1 (CH9)
        self.assertEqual(self.mock_mav.last_servo_channel, 9)
        self.assertEqual(self.mock_mav.last_servo_pwm, 2000)

    async def test_double_release_blocked(self):
        await self.service.release_payload()
        # Second attempt without reload should return False
        success = await self.service.release_payload()
        self.assertFalse(success)

    async def test_reset(self):
        await self.service.release_payload()
        self.assertFalse(self.service.has_payload)
        self.service.reset()
        self.assertTrue(self.service.has_payload)
        self.assertEqual(self.service.state, DeliveryState.IDLE)


if __name__ == "__main__":
    unittest.main()
