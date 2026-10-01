# Structure: Guardia AI v2.0.0 Architecture & Directory Tree

Locked summary: domain-first architecture and naming scheme for v2.0.0. Aligns embedded flight logic, edge vision, delivery actuation, local blackbox storage, and local offline GCS.

## 1. Directory Tree

```
guardia-ai/
├── .agents/
│   └── project/                  # Tacklestudioz ledger files
│       ├── status.md             # Master index ledger
│       ├── discovery.md          # Brief & requirements
│       ├── blueprint.md          # Domains, flows, slices
│       ├── design.md             # Design tokens & tactical HUD
│       ├── content.md            # Telemetry copy & alerts
│       ├── logic.md              # State machines & PID loops
│       ├── data.md               # SQLite blackbox schema
│       ├── responsive.md         # 375, 768, 1440 layout specs
│       ├── motion.md             # Attitude smoothing & HUD motion
│       ├── stack.md              # Pixhawk 2.4.8 & Pi 4B BOM
│       ├── structure.md          # Architecture & file mapping
│       ├── antislop.md           # Engineering audit
│       ├── qa.md                 # Pre-flight check & verification
│       └── release.md            # Commit plan & changelog
├── v1.0.0/                       # Archived initial webcam prototype
├── v2.0.0/                       # Active autonomous drone system
│   ├── docs/                     # Guides and manuals
│   │   ├── MASTER_PLAN.md        # Full system blueprint
│   │   ├── PIXHAWK_SETUP.md      # Pixhawk 2.4.8 wiring & calibration
│   │   ├── AI_WORKFLOW.md        # Colab to edge TFLite pipeline
│   │   └── GCS_GUIDE.md          # Local offline GCS station manual
│   ├── colab/                    # Cloud training and export
│   │   └── model_export.ipynb    # YOLOv8n to INT8 TFLite export
│   ├── drone/                    # Onboard companion computer software (Pi 4B)
│   │   ├── main.py               # Main runtime daemon entrypoint
│   │   ├── requirements.txt      # Pi 4B Python dependencies
│   │   ├── config/               # System configuration
│   │   │   └── settings.py       # Hardware, AI, and flight parameters
│   │   ├── flight/               # Domain: flight link
│   │   │   ├── mavlink/interface.py    # Pixhawk 2.4.8 MAVLink link
│   │   │   ├── failsafe/manager.py     # Heartbeat & battery watchdog
│   │   │   └── controllers/follow_controller.py # Visual PID controller
│   │   ├── ai/                   # Domain: perception
│   │   │   ├── inference/detector.py   # YOLOv8n TFLite offline detector
│   │   │   ├── tracking/byte_tracker.py # ByteTrack multi-object tracker
│   │   │   └── models/                 # Local .tflite weights
│   │   ├── navigation/           # Domain: mission
│   │   │   └── planner.py        # Waypoint & search pattern generator
│   │   ├── delivery/             # Domain: delivery
│   │   │   └── service.py        # Servo drop mechanism controller
│   │   ├── video/                # Domain: video pipeline
│   │   │   └── capture/pipeline.py     # Pi camera grabber & recorder
│   │   └── core/                 # Mission coordinator
│   │       └── agent.py          # Master autonomous state coordinator
│   ├── gcs/                      # Domain: local ground control station
│   │   ├── backend/              # FastAPI local backend
│   │   │   ├── main.py           # REST & WebSocket server
│   │   │   └── requirements.txt  # GCS dependencies
│   │   └── frontend/             # Local offline web HUD
│   │       ├── index.html        # Single-page tactical HUD
│   │       ├── css/style.css     # Vanilla tactical CSS
│   │       └── js/app.js         # WebSocket telemetry & HUD renderer
│   ├── scripts/                  # Deployment & configuration
│   │   └── setup_pi.sh           # Automated Pi 4B setup script
│   └── tests/                    # Unit & hardware integration tests
├── LICENSE
└── README.md
```

## 2. Naming Standards
- File naming: kebab-case for documents, snake_case for Python modules.
- Roles in use: `interface` (hardware link), `detector` (model runner), `tracker` (state estimator), `service` (actuator), `pipeline` (media stream), `manager` (daemon).
- Element IDs: `<domain>-<unit>-<element>` (e.g. `hud-horizon-pitch`, `hud-target-reticle`, `ctl-btn-takeoff`, `ctl-btn-drop`).
- Environment variables: `GUARDIA_<DOMAIN>_<KEY>` (e.g. `GUARDIA_SERIAL_PORT=/dev/ttyACM0`, `GUARDIA_BAUD_RATE=921600`, `GUARDIA_DETECTOR_MODEL=yolov8n.tflite`).
