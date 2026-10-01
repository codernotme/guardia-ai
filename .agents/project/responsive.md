# Responsive: Guardia AI v2.0.0 GCS Layouts

Locked summary: screen layout specifications for local GCS across three field device tiers: handheld phone (375px), rugged field tablet (768px), and command laptop (1440px+).

## 1. 375px Viewport (Technician Handheld Mobile)
- Header: compact 40px bar with battery icon + %, GPS satellite pill, and flight mode tag.
- Main area: 16:9 live video feed with overlaid minimal HUD (crosshair, speed tape on left, altitude tape on right).
- Bottom sheet: collapsible drawer for action buttons:
  - Large touch targets (minimum 48px height).
  - Quick action grid: Takeoff, Hold, Follow, Drop, RTL.
  - Emergency Kill button floating at top right with slide-to-confirm gesture.
- Hidden on mobile: full mission waypoint map editor, raw MAVLink packet log.

## 2. 768px Viewport (Rugged Field Tablet)
- Split view layout:
  - Left 60%: full resolution video HUD with artificial horizon, target bounding box overlay, and target metadata card.
  - Right 40%: vertical telemetry dashboard and mini GPS satellite map showing real-time drone track and home point.
- Bottom docked bar:
  - Flight mode selector buttons.
  - Delivery servo status and two-stage drop confirmation modal.
  - Blackbox recording indicator with live storage usage gauge.

## 3. 1440px+ Viewport (Base Station Desktop / Laptop)
- Triple pane tactical layout:
  - Left pane (360px): telemetry instrument cluster, motor RPM / current draw, IMU orientation 3D cube, battery cell voltages.
  - Center pane (flex): large primary video feed with synthetic HUD symbology, artificial horizon, target velocity vector.
  - Right pane (400px): interactive Leaflet/MapLibre offline cached map with waypoint path editor, geofence boundary editor, and blackbox mission timeline.
- Bottom pane (180px): live system event log stream, MAVLink message health monitor, and blackbox log exporter.
