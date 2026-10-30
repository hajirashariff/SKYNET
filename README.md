# Sky-Guard GCS

Sky-Guard is an enterprise Ground Control Station (GCS) and airspace monitoring application built with PyQt5, OpenCV, and YOLOv8 object detection.

## Features
- **Real-Time Video Feeds**: Support for webcams and local video candidate streams (`droneflying.mp4`, `df2.mp4`, `df3.mp4`, `test_video.mp4`).
- **AI Target Detection & Tracking**: Powered by Ultralytics YOLOv8 for automated aerial target and threat detection.
- **Enhanced Optics**: Selectable night-vision phosphor-green and thermal color-map displays.
- **Trajectory & Geofence Overlay**: Recent motion trails and a normalized no-fly zone with entry alerts.
- **Editable Geofence**: Toggle zone monitoring on/off, or draw and save a custom polygon by clicking feed locations.
- **Auto-Zoom PiP**: A live crop of the highest-confidence detection in the command panel.
- **Forensic Threat Gallery**: Saves one snapshot per track ID and source when confidence exceeds 85%, with timestamp, ID, class, and confidence metadata in `forensics/threats.sqlite3`.
- **HUD & Telemetry**: Live FPS, tracking counters, lock state, and alert siren.
- **Voice Alerts**: Speech-synthesized target acquisition and geofence breach alerts, handled on a dedicated thread.
- **Swarm Warning**: Flashing on-feed warning and event-log entry when three or more targets are tracked.
- **Simulated Motion Metrics**: Per-target approximate distance and centroid-based speed, clearly labeled as simulated.
- **Authentication**: Secure operator login window.
- **Dark/Light Mode**: Dynamic theme switching.
- **Reporting**: Event logging and report exporting to CSV.
- **Accessible, Responsive Controls**: Resizable command layout, high-visibility keyboard focus, adjustable text size, keyboard shortcuts, and a shortcut guide.

### Keyboard and accessibility controls
- `Ctrl+Shift+P`: Pause or resume the feed.
- `Ctrl+Shift+T`: Toggle tracking.
- `Ctrl+Shift+D`: Switch dark/light theme.
- `Ctrl+=` / `Ctrl+-`: Increase/decrease interface text size.
- `F11`: Toggle full screen.

The `A−` and `A+` buttons adjust text size, and the **SHORTCUTS** button shows
the complete keyboard guide. Controls remain available on screen for mouse and
keyboard users.

The default no-fly zone is a polygon in normalized frame coordinates near the right
side of the feed. Its vertices can be adjusted in `main.py` (`NO_FLY_ZONE`) to match
the monitored scene. Snapshots are stored in `forensics/`; the gallery can also show
records from earlier launches as long as their image files remain available.

To draw a custom fence, select **DRAW FENCE**, click at least three locations on
the video, then choose **FINISH FENCE**. Use **UNDO POINT** to correct the last
vertex, or toggle drawing off to cancel and restore the previous fence. Geofence
detection is paused while drawing; the saved polygon and on/off setting persist
between launches.

Voice alerts use `pyttsx3` on a dedicated thread; if the speech engine is unavailable,
the app logs that status while video and tracking continue. The on-feed swarm warning
appears when at least three detections are active and is logged once per swarm event.
Distance is estimated as `100000 / box area` meters and speed from centroid motion
using an illustrative `0.05 m/pixel` scale. These are demo-only values, not calibrated
measurements or real-world telemetry.

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
