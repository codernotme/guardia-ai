"""
Guardia AI v2.0.1 — Navigation & Path Planning
================================================
Search patterns for rescue missions, waypoint navigation,
and basic obstacle avoidance via altitude.

Patterns:
- Expanding Square (default for rescue)
- Sector Search
- Parallel Track (grid search)
- Creeping Line
"""

import logging
import math
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum, auto

logger = logging.getLogger("guardia.nav")


@dataclass
class Waypoint:
    """A navigation waypoint."""
    latitude: float
    longitude: float
    altitude: float = 10.0
    speed: float = 2.0
    hover_time: float = 0.0  # seconds to hover at waypoint
    label: str = ""


class SearchPattern(Enum):
    """Available search patterns."""
    EXPANDING_SQUARE = auto()
    SECTOR = auto()
    PARALLEL_TRACK = auto()
    CREEPING_LINE = auto()


class NavigationPlanner:
    """
    Path planning for autonomous missions.

    Handles:
    - Search pattern generation for rescue
    - Waypoint mission management
    - Distance and bearing calculations
    """

    def __init__(self):
        self._waypoints: List[Waypoint] = []
        self._current_wp_index: int = 0
        self._mission_complete: bool = False
        self._acceptance_radius: float = 3.0  # meters

    @property
    def current_waypoint(self) -> Optional[Waypoint]:
        if 0 <= self._current_wp_index < len(self._waypoints):
            return self._waypoints[self._current_wp_index]
        return None

    @property
    def waypoints(self) -> List[Waypoint]:
        return self._waypoints

    @property
    def progress(self) -> float:
        if not self._waypoints:
            return 0.0
        return self._current_wp_index / len(self._waypoints)

    @property
    def is_complete(self) -> bool:
        return self._mission_complete

    def set_waypoints(self, waypoints: List[Waypoint]):
        """Set waypoint mission."""
        self._waypoints = waypoints
        self._current_wp_index = 0
        self._mission_complete = False
        logger.info("Mission set: %d waypoints", len(waypoints))

    def update(self, current_lat: float, current_lon: float) -> Optional[Waypoint]:
        """
        Update navigation state with current position.
        Returns next waypoint to fly to, or None if mission complete.
        """
        if self._mission_complete or not self._waypoints:
            return None

        wp = self._waypoints[self._current_wp_index]
        distance = self._haversine(current_lat, current_lon, wp.latitude, wp.longitude)

        if distance <= self._acceptance_radius:
            logger.info(
                "Waypoint %d/%d reached (%.1fm from target)",
                self._current_wp_index + 1, len(self._waypoints), distance,
            )
            self._current_wp_index += 1

            if self._current_wp_index >= len(self._waypoints):
                self._mission_complete = True
                logger.info("Mission complete!")
                return None

        return self._waypoints[self._current_wp_index]

    def generate_search_pattern(
        self,
        center_lat: float,
        center_lon: float,
        radius: float = 100.0,
        altitude: float = 20.0,
        spacing: float = 15.0,
        pattern: SearchPattern = SearchPattern.EXPANDING_SQUARE,
        speed: float = 2.0,
    ) -> List[Waypoint]:
        """
        Generate a search pattern around a center point.

        Args:
            center_lat, center_lon: Center of search area
            radius: Maximum search radius (meters)
            altitude: Search altitude (meters)
            spacing: Distance between search legs (meters)
            pattern: Type of search pattern
            speed: Search speed (m/s)

        Returns:
            List of waypoints forming the search pattern
        """
        if pattern == SearchPattern.EXPANDING_SQUARE:
            waypoints = self._expanding_square(
                center_lat, center_lon, radius, spacing, altitude, speed,
            )
        elif pattern == SearchPattern.PARALLEL_TRACK:
            waypoints = self._parallel_track(
                center_lat, center_lon, radius, spacing, altitude, speed,
            )
        elif pattern == SearchPattern.SECTOR:
            waypoints = self._sector_search(
                center_lat, center_lon, radius, altitude, speed,
            )
        else:
            waypoints = self._expanding_square(
                center_lat, center_lon, radius, spacing, altitude, speed,
            )

        self.set_waypoints(waypoints)
        logger.info(
            "Search pattern generated: %s, %d waypoints, radius=%.0fm",
            pattern.name, len(waypoints), radius,
        )
        return waypoints

    def _expanding_square(
        self,
        center_lat: float,
        center_lon: float,
        radius: float,
        spacing: float,
        altitude: float,
        speed: float,
    ) -> List[Waypoint]:
        """
        Expanding square search pattern.
        Starts at center and spirals outward in a square pattern.
        Best for: Known last position (rescue).
        """
        waypoints = []
        waypoints.append(Waypoint(
            center_lat, center_lon, altitude, speed, label="center"
        ))

        leg = spacing
        directions = [
            (0, 1),   # North
            (1, 0),   # East
            (0, -1),  # South
            (-1, 0),  # West
        ]

        current_lat = center_lat
        current_lon = center_lon
        dir_idx = 0
        legs_in_direction = 1

        while leg <= radius * 2:
            for _ in range(2):  # Two legs of same length before increasing
                dx, dy = directions[dir_idx % 4]
                new_lat, new_lon = self._offset_position(
                    current_lat, current_lon,
                    dx * leg, dy * leg,
                )

                # Check radius
                dist = self._haversine(new_lat, new_lon, center_lat, center_lon)
                if dist > radius:
                    return waypoints

                waypoints.append(Waypoint(
                    new_lat, new_lon, altitude, speed,
                    label=f"sq_{len(waypoints)}",
                ))
                current_lat, current_lon = new_lat, new_lon
                dir_idx += 1

            leg += spacing

        return waypoints

    def _parallel_track(
        self,
        center_lat: float,
        center_lon: float,
        radius: float,
        spacing: float,
        altitude: float,
        speed: float,
    ) -> List[Waypoint]:
        """
        Parallel track (lawn mower) search pattern.
        Best for: Large area coverage.
        """
        waypoints = []
        num_tracks = int(2 * radius / spacing)
        direction = 1  # Alternates

        for i in range(num_tracks + 1):
            offset_x = -radius + i * spacing
            y_extent = radius * direction

            start_lat, start_lon = self._offset_position(
                center_lat, center_lon, offset_x, -y_extent,
            )
            end_lat, end_lon = self._offset_position(
                center_lat, center_lon, offset_x, y_extent,
            )

            waypoints.append(Waypoint(
                start_lat, start_lon, altitude, speed,
                label=f"track_{i}_start",
            ))
            waypoints.append(Waypoint(
                end_lat, end_lon, altitude, speed,
                label=f"track_{i}_end",
            ))

            direction *= -1

        return waypoints

    def _sector_search(
        self,
        center_lat: float,
        center_lon: float,
        radius: float,
        altitude: float,
        speed: float,
        sectors: int = 6,
    ) -> List[Waypoint]:
        """
        Sector search pattern.
        Divides area into pie slices and covers each.
        Best for: High probability of detection near center.
        """
        waypoints = []
        angle_step = 360.0 / sectors

        for i in range(sectors):
            angle = math.radians(i * angle_step)

            # Go to edge
            edge_x = radius * math.cos(angle)
            edge_y = radius * math.sin(angle)
            edge_lat, edge_lon = self._offset_position(
                center_lat, center_lon, edge_x, edge_y,
            )
            waypoints.append(Waypoint(
                edge_lat, edge_lon, altitude, speed,
                label=f"sector_{i}_edge",
            ))

            # Return to center
            waypoints.append(Waypoint(
                center_lat, center_lon, altitude, speed,
                label=f"sector_{i}_return",
            ))

        return waypoints

    def reset(self):
        """Reset navigation state."""
        self._waypoints.clear()
        self._current_wp_index = 0
        self._mission_complete = False

    # ------------------------------------------------------------------
    # Geo utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Distance between two GPS coords in meters."""
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    @staticmethod
    def _offset_position(
        lat: float, lon: float, dx_meters: float, dy_meters: float,
    ) -> Tuple[float, float]:
        """Offset a GPS position by meters (flat earth approximation, fine for <10km)."""
        new_lat = lat + (dy_meters / 111320.0)
        new_lon = lon + (dx_meters / (111320.0 * math.cos(math.radians(lat))))
        return (new_lat, new_lon)

    @staticmethod
    def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Bearing from point 1 to point 2 in degrees."""
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dlam = math.radians(lon2 - lon1)
        x = math.sin(dlam) * math.cos(phi2)
        y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
        return (math.degrees(math.atan2(x, y)) + 360) % 360
