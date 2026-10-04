# Status: Guardia AI v2.0.0

Type: app
Budget: N/A | Deadline: Ongoing | Owner approvals needed: Aryan Bajpai

## Locked decisions
- D1 GCS frontend stack: Migrated to Next.js 16 (App Router) + HeroUI 3.2.6 + TailwindCSS v4.
- D2 Theme & typography: Custom HeroUI OKLCH color tokens and Bricolage Grotesque font loaded.
- D3 Legacy preservation: Prior prototype backed up at `gcs/frontend_legacy` for API/state parity.

## Assumptions (ASSUMED)
- A1 Local dev flow: Next.js frontend connects to FastAPI backend at `localhost:8000` via REST and `/ws/telemetry`.

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
| S2 | gcs-telemetry-hud | next | Integrate Pixhawk telemetry HUD, Step controls, and RC status |
