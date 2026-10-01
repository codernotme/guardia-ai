# Antislop: Guardia AI v2.0.0 Engineering Audit

Locked summary: full-scope antislop review confirming genuine robotics engineering rigor, realistic embedded performance limits, absence of AI fluff copy, and strict elimination of em dashes across all code and documentation.

## 1. Audit Scope & Lens Results
- Mode: full
- Result: clean (0 tells, 0 smells)

| # | Lens | Where | Finding | Status |
|---|---|---|---|---|
| 1 | Visual | `gcs/frontend/` | High contrast tactical dark mode with monospaced data readouts. No generic gradients or purple SaaS cards. | Pass |
| 2 | Copy | `docs/` & `copy` | Direct developer tone. All claims backed by physical hardware specs (STM32F427 168MHz, 2MB flash, 8GB Pi 4B). Zero buzzwords like "hyper-smart" or "revolutionary". | Pass |
| 3 | Code | `drone/` | Real MAVLink message IDs (SET_POSITION_TARGET_LOCAL_NED, COMMAND_LONG, HEARTBEAT), real baud rates (921600), explicit zero-division guards on PID calculations. | Pass |
| 4 | Repo | `.agents/` | No em dashes in prose or comments. Strict file naming convention following domain-first architecture. | Pass |

## 2. Signature Decisions
1. Pixhawk 2.4.8 hardware distinction: explicitly accounts for FMUv3 target firmware and 2MB flash silicon revision, avoiding the 1MB flash limitation of older FMUv2 boards.
2. Dual connection support: auto-detects USB Micro-B connection (`/dev/ttyACM0`) or TELEM2 UART (`/dev/serial0`) at 921600 baud.
3. Offline silent architecture: completely disables remote cloud telemetry and handles local GCS via an ad-hoc Wi-Fi Access Point on the Pi 4B, with blackbox persistence in embedded SQLite.
4. Two-stage delivery release interlock: requires altitude check (2.5m - 4.0m) and stability gate (<0.3 m/s drift) before allowing payload servo trigger.
