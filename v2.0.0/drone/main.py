"""
Guardia AI v2.0.0 — Main Drone Entrypoint
===========================================
Boots all subsystems and runs the drone agent.
This is what you run on the Raspberry Pi 4B.

Usage:
    python -m core.main
    # or
    python main.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Setup logging first
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)-24s] %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/tmp/guardia_drone.log", mode="a"),
    ],
)
logger = logging.getLogger("guardia.main")


def print_banner():
    banner = """
    ╔══════════════════════════════════════════════════════╗
    ║                                                      ║
    ║     🚁  GUARDIA AI v2.0.0  —  AUTONOMOUS DRONE      ║
    ║                                                      ║
    ║     Surveillance • Rescue • Tracking • Delivery      ║
    ║     Tackle Studio — by Aryan Bajpai                  ║
    ║                                                      ║
    ║     ⚠️  NO TELEMETRY  •  ALL OFFLINE  •  NO CLOUD    ║
    ║                                                      ║
    ╚══════════════════════════════════════════════════════╝
    """
    print(banner)


async def main():
    print_banner()
    logger.info("=" * 60)
    logger.info("GUARDIA AI v2.0.0 — DRONE STARTUP")
    logger.info("=" * 60)

    # ------------------------------------------------------------------
    # 1. Load configuration
    # ------------------------------------------------------------------
    from config.settings import get_config
    config = get_config()

    logger.info("Configuration loaded:")
    logger.info("  Telemetry: DISABLED (global kill switch ON)")
    logger.info("  Detector: %s (%s)", config.ai.detector_model, config.ai.detector_format)
    logger.info("  Pixhawk: %s @ %d baud", config.hardware.pixhawk_serial_port, config.hardware.pixhawk_baud_rate)
    logger.info("  Camera: %s @ %dfps", config.hardware.camera_resolution, config.hardware.camera_fps)
    logger.info("  Modem: %s", "ENABLED" if config.hardware.modem_enabled else "DISABLED")
    logger.info("  Follow limits: max_speed=%.1fm/s altitude=%.1fm geofence=%.0fm",
                config.flight.follow_max_speed, config.flight.follow_default_altitude,
                config.flight.geofence_radius)

    # ------------------------------------------------------------------
    # 2. Initialize subsystems
    # ------------------------------------------------------------------
    logger.info("Initializing subsystems...")

    # AI Detector
    from ai.inference.detector import OfflineDetector
    detector = OfflineDetector(
        model_path=config.ai.detector_model_path,
        input_size=config.ai.detector_input_size,
        confidence_threshold=config.ai.detector_confidence,
        iou_threshold=config.ai.detector_iou_threshold,
        max_detections=config.ai.detector_max_detections,
        target_classes=config.ai.target_classes,
    )
    if detector.initialize():
        logger.info("✅ AI Detector ready")
    else:
        logger.warning("⚠️  AI Detector failed to initialize — tracking disabled")

    # Tracker
    from ai.tracking.byte_tracker import ByteTracker
    tracker = ByteTracker(
        max_age=config.ai.tracker_max_age,
        min_hits=config.ai.tracker_min_hits,
        iou_threshold=config.ai.tracker_iou_threshold,
    )
    logger.info("✅ ByteTracker ready")

    # Video Pipeline
    from video.capture.pipeline import VideoPipeline
    video = VideoPipeline(config=config)

    # Flight Controller (MAVLink)
    from flight.mavlink.interface import MAVLinkInterface
    mavlink = MAVLinkInterface(
        port=config.hardware.pixhawk_serial_port,
        baud=config.hardware.pixhawk_baud_rate,
        firmware="px4",  # Change to "ardupilot" if needed
    )

    # Follow Controller
    from flight.controllers.follow_controller import FollowController
    follow_ctrl = FollowController(
        max_speed=config.flight.follow_max_speed,
        min_distance=config.flight.follow_min_distance,
        target_altitude=config.flight.follow_default_altitude,
        max_yaw_rate=config.flight.max_yaw_rate,
    )

    # Failsafe Manager
    from flight.failsafe.manager import FailsafeManager
    failsafe = FailsafeManager()

    # Delivery Service
    from delivery.service import DeliveryService
    delivery = DeliveryService(
        servo_pin=config.delivery.servo_pin,
        drop_altitude=config.delivery.delivery_altitude,
    )

    # ------------------------------------------------------------------
    # 3. Initialize Drone Agent
    # ------------------------------------------------------------------
    from core.agent import DroneAgent
    agent = DroneAgent()
    agent.register_subsystems(
        flight_controller=mavlink,
        tracker=tracker,
        video_service=video,
        delivery_service=delivery,
        failsafe_manager=failsafe,
    )

    # ------------------------------------------------------------------
    # 4. Connect to Pixhawk
    # ------------------------------------------------------------------
    logger.info("Connecting to Pixhawk...")
    if await mavlink.connect():
        logger.info("✅ Pixhawk connected")
        agent.update_pixhawk_heartbeat()

        # Set up heartbeat callback
        mavlink.on_heartbeat(agent.update_pixhawk_heartbeat)
    else:
        logger.warning("⚠️  Pixhawk not connected — running in simulation mode")

    # ------------------------------------------------------------------
    # 5. Start Video Pipeline
    # ------------------------------------------------------------------
    logger.info("Starting video pipeline...")
    if video.start():
        logger.info("✅ Video pipeline running")
    else:
        logger.warning("⚠️  Video pipeline failed — AI tracking disabled")

    # ------------------------------------------------------------------
    # 6. Start Background Tasks
    # ------------------------------------------------------------------
    tasks = []

    # MAVLink receive loop
    if mavlink.is_connected:
        tasks.append(asyncio.create_task(
            mavlink.receive_loop(), name="mavlink_rx"
        ))

    # AI inference loop
    async def ai_loop():
        """Run detector + tracker on camera frames."""
        while True:
            try:
                frame = video.get_ai_frame(timeout=0.1)
                if frame is not None and detector.is_ready:
                    # Detect
                    det_result = detector.detect(frame)

                    # Track
                    tracker_result = tracker.update(det_result.detections, frame)

                    # Update agent status
                    agent.status.targets_detected = len(tracker_result.confirmed_tracks)

                    # If following, compute velocity commands
                    if agent.state.name == "FOLLOW" and agent.status.target_id is not None:
                        offset = tracker.get_target_offset(
                            agent.status.target_id,
                            frame.shape[1], frame.shape[0],
                        )
                        if offset:
                            agent.status.target_locked = True
                            vx, vy, vz, yaw_rate = follow_ctrl.compute(
                                offset[0], offset[1], offset[2],
                                dt=1.0 / max(1, config.ai.detector_fps_target),
                            )
                            if mavlink.is_connected:
                                await mavlink.send_velocity(vx, vy, vz, yaw_rate)
                        else:
                            agent.status.target_locked = False
                            vx, vy, vz, yaw_rate = follow_ctrl.compute_lost_target()
                            if mavlink.is_connected:
                                await mavlink.send_velocity(vx, vy, vz, yaw_rate)

                await asyncio.sleep(1.0 / config.ai.detector_fps_target)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("AI loop error: %s", e, exc_info=True)
                await asyncio.sleep(1.0)

    tasks.append(asyncio.create_task(ai_loop(), name="ai_loop"))

    # ------------------------------------------------------------------
    # 7. Run Main Agent
    # ------------------------------------------------------------------
    logger.info("=" * 60)
    logger.info("🚁 GUARDIA AI DRONE READY")
    logger.info("=" * 60)

    try:
        await agent.run()
    finally:
        # Cleanup
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        video.stop()
        await mavlink.disconnect()
        delivery.cleanup()
        logger.info("Guardia AI shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
