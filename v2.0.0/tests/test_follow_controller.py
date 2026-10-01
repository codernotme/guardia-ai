"""
Unit tests for Guardia AI v2.0.0 FollowController.
Verifies PID response, body-frame velocity outputs, and mode switching.
"""

import unittest
import math
import sys
import os

# Add drone to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "drone")))

from flight.controllers.follow_controller import PIDState, FollowController


class TestPIDState(unittest.TestCase):
    def test_proportional_response(self):
        pid = PIDState(kp=1.0, ki=0.0, kd=0.0, output_limit=5.0)
        out = pid.update(error=2.0, dt=0.1)
        self.assertEqual(out, 2.0)

    def test_output_clamping(self):
        pid = PIDState(kp=10.0, ki=0.0, kd=0.0, output_limit=1.0)
        out = pid.update(error=5.0, dt=0.1)
        self.assertEqual(out, 1.0)

    def test_reset(self):
        pid = PIDState(kp=1.0, ki=1.0, kd=1.0)
        pid.update(error=1.0, dt=0.1)
        pid.reset()
        self.assertEqual(pid.integral, 0.0)
        self.assertEqual(pid.prev_error, 0.0)
        self.assertEqual(pid.output, 0.0)


class TestFollowController(unittest.TestCase):
    def setUp(self):
        self.controller = FollowController(
            max_speed=3.0,
            min_distance=5.0,
            target_altitude=10.0,
            max_yaw_rate=45.0,
        )

    def test_mode_switching(self):
        self.controller.set_mode("tail", distance=25.0)
        self.assertEqual(self.controller._mode, "tail")
        self.assertEqual(self.controller._tail_distance, 25.0)

        self.controller.set_mode("orbit", radius=12.0, speed=1.5)
        self.assertEqual(self.controller._mode, "orbit")
        self.assertEqual(self.controller._orbit_radius, 12.0)

    def test_centered_target_low_velocity(self):
        # Target in deadband center: offset_x=0.0, offset_y=0.0, size=0.30, dt=0.05
        cmd = self.controller.compute(
            offset_x=0.0,
            offset_y=0.0,
            target_size=0.30,
            dt=0.05,
        )
        self.assertIsNotNone(cmd)
        vx, vy, vz, yaw_rate = cmd
        # Yaw and lateral should be near zero for centered target
        self.assertAlmostEqual(yaw_rate, 0.0, delta=0.1)
        self.assertAlmostEqual(vy, 0.0, delta=0.1)

    def test_target_lost_detection(self):
        cmd = self.controller.compute_lost_target()
        self.assertIsNotNone(cmd)
        vx, vy, vz, yaw_rate = cmd
        # Should command hover/stop
        self.assertEqual(vx, 0.0)
        self.assertEqual(vy, 0.0)
        self.assertEqual(vz, 0.0)


if __name__ == "__main__":
    unittest.main()
