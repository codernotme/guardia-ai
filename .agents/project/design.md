# Design System: Guardia AI v2.0.0 Tactical HUD

Locked summary: tactical dark mode interface tailored for field readability under outdoor sunlight and night surveillance. Monospaced instrumentation, high contrast HUD symbology, military inspired telemetry badges, and zero generic aesthetic slop.

## 1. Design Tokens
- Canvas:
  - `--color-bg-base`: #090B0E (deep radar void)
  - `--color-bg-surface`: #11151B (panel backing)
  - `--color-bg-elevated`: #1B222C (interactive card)
  - `--color-border-subtle`: #222B38 (subtle grid divider)
  - `--color-border-active`: #3A475C (focused border)
- Tactical Signal Accents:
  - `--color-hud-primary`: #00F0FF (cyan: aircraft orientation, primary reticle)
  - `--color-hud-success`: #00E676 (green: locked target, armed status, healthy GPS)
  - `--color-hud-warning`: #FFD600 (amber: battery warning, track lost, degraded fix)
  - `--color-hud-danger`: #FF1744 (crimson: failsafe active, emergency kill, critical battery)
  - `--color-hud-text`: #EDF2F7 (primary telemetry readout)
  - `--color-hud-dim`: #718096 (labels and secondary metadata)
- Typography:
  - Font families: `ui-monospace, 'JetBrains Mono', 'Roboto Mono', monospace` for all telemetry readouts and coordinates.
  - Heading font: `'Inter', -apple-system, BlinkMacSystemFont, sans-serif` with tabular numerals enabled (`font-feature-settings: 'tnum'`).
  - Font scale:
    - Micro: 10px / line-height 12px (sub-labels, GPS HDOP)
    - Caption: 12px / line-height 14px (status tags, coordinates)
    - Body: 14px / line-height 18px (system logs, control buttons)
    - Metric: 22px / line-height 26px (speed, altitude, distance readouts)
    - Hero Metric: 32px / line-height 36px (altitude tape, battery percentage)
- Spacing:
  - Base unit: 4px.
  - Scale: 4px, 8px, 12px, 16px, 24px, 32px.
- Radii:
  - Sharp tactical corners: 2px for HUD boxes, 4px for buttons and panels. Never pill buttons or round cards.

## 2. Key UI Components
1. Artificial Horizon:
   - Centered pitch ladder (-30 deg to +30 deg) in cyan (#00F0FF).
   - Roll pointer on top circular arc with bank angle graduation tick marks.
   - Zero-pitch waterline aircraft symbol fixed at screen center.
2. Target Tracking Reticle:
   - Candidate box: dashed amber 1px border with corner tick brackets.
   - Locked target: solid neon green 2px border with corner bracket crosshairs and track ID label: `TRK-01 [PERSON 94%] DIST: 6.2M`.
   - Lost target: blinking amber border with countdown ticker: `LOST: 3.2s`.
3. Status and Telemetry Bar:
   - Top banner containing: Flight Mode pill (`GUIDED` / `OFFBOARD`), Arm status (`ARMED` / `DISARMED`), Battery Voltage and % remaining with warning color thresholds, GPS satellites and Fix Type (`3D FIX (14 SATS)`), Link health ping (`12ms`).
4. Action Controls:
   - Primary action buttons: Takeoff, Hold, Follow Target, Release Payload, Return to Launch.
   - Emergency Kill button: striped diagonal hazard background with prominent confirmation guard.
