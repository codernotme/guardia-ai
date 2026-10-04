# Status: Guardia AI v2.0.0

Type: app
Budget: N/A | Deadline: Ongoing | Owner approvals needed: Aryan Bajpai

## Locked decisions
- D1 GCS frontend stack: Next.js 16 (App Router) + HeroUI 3.2.6 + TailwindCSS v4.
- D2 Theme & typography: Custom HeroUI OKLCH color tokens and Bricolage Grotesque font loaded.
- D3 Map & attitude display: Integrated Leaflet (CartoDB Dark + Esri Satellite Hybrid) with rotating tactical quadcopter icon, breadcrumb flight trail, and Primary Flight Display (Artificial Horizon, pitch ladder, 360° compass ribbon).
- D4 Flight controls & diagnostics: Precision Step & Nudge (1cm/10cm/1ft/1m), FlySky RC 8-channel PWM visualizer, serial port switcher, bench motor test, and autonomous mission planner with payload drop servo trigger.
- D5 Real-time bridge: Reconnecting WebSocket to FastAPI backend on `ws://localhost:8000/ws/telemetry`.

## Assumptions (ASSUMED)
- A1 Local dev flow: Next.js frontend runs on `http://localhost:3000` communicating with FastAPI backend on `http://localhost:8000`.

## Open blockers
- None

## Parking lot (not in scope)
- Multi-drone coordination
- Obstacle LiDAR pointcloud rendering

## Ledger files
| File | Agent | State | Summary (one line) |
| --- | --- | --- | --- |
| status.md | orchestrator | locked | Project status and wave index |

## Slices
| Slice | Domain | State | Notes |
| --- | --- | --- | --- |
| S1 | gcs-frontend-init | done | Next.js HeroUI app initialized, themed, and verified |
| S2 | gcs-map-pfd-controls | done | Tactical Map, 360° Compass, Artificial Horizon, Step Controls, RC Monitor, Analytics, and Mission Planner integrated |
| S3 | drone-hardware-bench-flight | next | Bench test with Pixhawk 2.4.8, FlySky FS-i6, and HC-05 Bluetooth |
