# Sky-Guard GCS

Sky-Guard is an enterprise Ground Control Station (GCS) and airspace monitoring application built with PyQt5, OpenCV, and YOLOv8 object detection.

## Features
- **Real-Time Video Feeds**: Support for webcams and local video candidate streams (`droneflying.mp4`, `df2.mp4`, `df3.mp4`, `test_video.mp4`).
- **AI Target Detection & Tracking**: Powered by Ultralytics YOLOv8 for automated aerial target and threat detection.
- **HUD & Telemetry**: Live FPS, tracking counters, lock state, and alert siren.
- **Authentication**: Secure operator login window.
- **Dark/Light Mode**: Dynamic theme switching.
- **Reporting**: Event logging and report exporting to CSV.

## Quick Start

### 1. Requirements
- Python 3.9+ (Python 3.11 / 3.12 / 3.14 compatible)
- Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Launch the Application
You can launch the app in any of the following ways:

- **Using the batch launcher (Windows):**
  Double-click `run.bat`

- **Using the Python launcher:**
  ```bash
  python run_skyguard.py
  ```

- **Direct run:**
  ```bash
  python main.py
  ```

### 3. Default Operator Credentials
- **Username:** `admin`
- **Password:** `admin123`
