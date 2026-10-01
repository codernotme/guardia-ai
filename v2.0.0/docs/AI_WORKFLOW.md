# Guardia AI v2.0.0 — AI Workflow Guide
## How to Run AI Models: Training, Export, Deployment

> This project is 100% AI-operated. This guide covers every step
> from model selection to deployment on Raspberry Pi 4B.

---

## Overview

```
Google Colab (Training/Export)
    │
    │  Download .tflite
    ▼
Raspberry Pi 4B (Inference)
    │
    │  Detection results
    ▼
ByteTrack (Tracking)
    │
    │  Target offsets
    ▼
Follow Controller (PID)
    │
    │  Velocity commands
    ▼
Pixhawk (Flight)
```

---

## Step 1: Model Export (Google Colab)

### 1.1 Open the Notebook
```
File: v2.0.0/colab/model_export.ipynb
Open in: Google Colab (colab.research.google.com)
Runtime: GPU (free tier is fine)
```

### 1.2 What the Notebook Does
1. Installs `ultralytics` and `tflite-support`
2. Downloads YOLOv8-nano pretrained weights (COCO 80 classes)
3. Exports to TFLite format:
   - **FP32** (12MB, more accurate, ~8-10 FPS on Pi)
   - **INT8** (4MB, faster, ~12-15 FPS on Pi)
4. Runs benchmark tests
5. Packages models for download

### 1.3 Run All Cells
Just click "Run All" — the notebook is non-interactive.

### 1.4 Download Models
The notebook creates `guardia_models.zip` containing:
```
guardia_models/
├── yolov8n.pt                    # PyTorch weights (reference)
├── yolov8n_float32.tflite        # FP32 TFLite (recommended start)
└── yolov8n_integer_quant.tflite  # INT8 TFLite (speed option)
```

---

## Step 2: Deploy to Raspberry Pi

### 2.1 Copy Model
```bash
# From your laptop
scp yolov8n_float32.tflite pi@guardia.local:~/guardia/v2.0.0/drone/ai/models/yolov8n.tflite
```

### 2.2 Verify on Pi
```bash
# SSH into Pi
ssh pi@guardia.local
cd ~/guardia/v2.0.0/drone

# Activate virtual environment
source ~/guardia/venv/bin/activate

# Quick test
python3 -c "
from ai.inference.detector import OfflineDetector
d = OfflineDetector(model_path='ai/models/yolov8n.tflite')
print('Init:', d.initialize())
print('Ready:', d.is_ready)
"
```

### 2.3 Benchmark on Pi
```bash
python3 -c "
import numpy as np
import time
from ai.inference.detector import OfflineDetector

d = OfflineDetector(model_path='ai/models/yolov8n.tflite', input_size=320)
d.initialize()

# Warm up
dummy = np.random.randint(0, 255, (320, 320, 3), dtype=np.uint8)
for _ in range(5):
    d.detect(dummy)

# Benchmark
times = []
for _ in range(50):
    start = time.monotonic()
    d.detect(dummy)
    times.append((time.monotonic() - start) * 1000)

print(f'Mean:   {np.mean(times):.1f} ms')
print(f'Median: {np.median(times):.1f} ms')
print(f'FPS:    {1000/np.mean(times):.1f}')
"
```

Expected output:
```
Mean:   90-120 ms
Median: 85-110 ms
FPS:    8-12
```

---

## Step 3: Custom Training (Optional)

### 3.1 When to Fine-Tune
- Default COCO model works well for people, cars, bikes
- Fine-tune if you need:
  - Better aerial (top-down) detection
  - Specific rescue scenarios
  - Custom objects

### 3.2 Dataset Preparation
```
dataset/
├── images/
│   ├── train/
│   │   ├── img001.jpg
│   │   └── ...
│   └── val/
│       ├── img050.jpg
│       └── ...
├── labels/
│   ├── train/
│   │   ├── img001.txt  # YOLO format: class cx cy w h
│   │   └── ...
│   └── val/
│       └── ...
└── data.yaml
```

### 3.3 data.yaml
```yaml
path: /content/dataset
train: images/train
val: images/val

nc: 5  # number of classes
names:
  0: person
  1: vehicle
  2: bicycle
  3: backpack
  4: distress_person
```

### 3.4 Training (in Colab)
```python
from ultralytics import YOLO

model = YOLO('yolov8n.pt')  # Start from pretrained
model.train(
    data='/content/dataset/data.yaml',
    epochs=50,
    imgsz=320,
    batch=16,
    device=0,
    name='guardia_custom',
    patience=10,        # Early stopping
    augment=True,       # Data augmentation
    mosaic=1.0,         # Mosaic augmentation
    flipud=0.5,         # Vertical flip (useful for aerial)
)

# Export
model.export(format='tflite', imgsz=320, int8=True)
```

### 3.5 Aerial Dataset Sources
- [VisDrone](https://github.com/VisDrone/VisDrone-Dataset) — drone perspective
- [DOTA](https://captain-whu.github.io/DOTA/) — aerial object detection
- [HERIDAL](https://github.com/MagdalenaPakworska/HERIDAL) — rescue/search
- Record your own from drone footage

---

## Step 4: Tracker Configuration

### 4.1 ByteTrack Parameters

| Parameter | Default | Range | Effect |
|---|---|---|---|
| `max_age` | 30 | 10-60 | Frames before dropping lost track |
| `min_hits` | 3 | 1-5 | Detections needed to confirm track |
| `iou_threshold` | 0.3 | 0.1-0.5 | Minimum IoU for matching |

### 4.2 Tuning Tips

**For Follow mode:**
```python
# Tight tracking, fast response
tracker = ByteTracker(max_age=15, min_hits=2, iou_threshold=0.3)
```

**For Rescue search:**
```python
# Keep tracks longer, tolerate occlusion
tracker = ByteTracker(max_age=60, min_hits=3, iou_threshold=0.2)
```

**For Tail mode:**
```python
# Long-distance, handle partial occlusion
tracker = ByteTracker(max_age=45, min_hits=3, iou_threshold=0.25)
```

---

## Step 5: Follow Controller Tuning

### 5.1 PID Gains

| Parameter | Default | Tune When |
|---|---|---|
| `yaw_pid.kp = 0.8` | Good start | Drone oscillates → decrease. Slow response → increase |
| `yaw_pid.ki = 0.05` | Low intentionally | Persistent offset → increase slightly |
| `yaw_pid.kd = 0.15` | Dampens oscillation | Jerky → increase. Sluggish → decrease |
| `forward_pid.kp = 0.5` | Conservative | Too cautious → increase to 0.7 |
| `max_speed = 3.0` | Safety limit | Increase only after extensive testing |

### 5.2 Tuning Process
1. Start with defaults
2. Record a follow test flight
3. Plot target offset vs velocity commands
4. Adjust one gain at a time
5. Repeat until smooth tracking

---

## Memory Management

### RAM Usage Monitoring
```bash
# On the Pi during flight
watch -n 1 'free -m && echo "---" && ps aux --sort=-%mem | head -5'
```

### If RAM is tight:
1. Use INT8 model instead of FP32 (saves ~20MB)
2. Reduce camera resolution to 640x480
3. Reduce tracker history length
4. Disable recording during AI-heavy missions
5. Limit concurrent tracks to 10

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| "Model file not found" | Wrong path | Check `drone/ai/models/` contains the .tflite file |
| "Neither tflite_runtime nor tensorflow found" | Missing package | `pip install tflite-runtime` |
| "0 FPS" | Model loading failed | Check model format matches (TFLite, not ONNX) |
| Low FPS (<5) | Input too large | Reduce `detector_input_size` to 256 |
| Many false detections | Confidence too low | Increase `detector_confidence` to 0.45 |
| Tracker loses target fast | `max_age` too low | Increase to 45-60 |
| Jerky following | PID gains too high | Decrease `kp`, increase `kd` |
