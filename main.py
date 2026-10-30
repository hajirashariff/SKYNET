#!/usr/bin/env python3
"""Sky-Guard GCS — enterprise PyQt5 ground control station."""

from __future__ import annotations

import csv
import ctypes
import math
import os
import platform
import sqlite3
import sys
import time
import uuid
from collections import defaultdict, deque
from contextlib import closing
from datetime import datetime
from importlib.util import find_spec
from pathlib import Path

# Windows: load torch before PyQt5 to avoid c10.dll initialization failure.
if platform.system() == "Windows":
    try:
        spec = find_spec("torch")
        if spec and spec.origin:
            dll_path = os.path.join(os.path.dirname(spec.origin), "lib", "c10.dll")
            if os.path.exists(dll_path):
                ctypes.CDLL(os.path.normpath(dll_path))
    except Exception:
        pass
    try:
        import torch  # noqa: F401
    except Exception:
        pass

import cv2
import numpy as np
from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, QThread, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

APP_DIR = Path(__file__).resolve().parent
ICON_FILE = APP_DIR / "icon.png"
MODEL_WEIGHTS = "yolov8n.pt"
VIDEO_CANDIDATES = ("test_video.mp4", "droneflying.mp4", "df2.mp4", "df3.mp4")
AUTH_USER = "admin"
AUTH_PASS = "admin123"

CYAN_BGR = (255, 255, 0)
CRIMSON_BGR = (60, 20, 220)
LABEL_BG = (0, 0, 0)
NO_FLY_ZONE = ((0.66, 0.22), (0.94, 0.22), (0.94, 0.78), (0.66, 0.78))
FORENSIC_CONFIDENCE = 0.85

DARK = {
    "bg": "#121212",
    "surface": "#1e1e1e",
    "accent": "#007acc",
    "text": "#ffffff",
    "muted": "#9aa0a6",
    "border": "#2a2a2a",
    "danger": "#d13438",
    "input": "#252525",
}
LIGHT = {
    "bg": "#f3f3f3",
    "surface": "#ffffff",
    "accent": "#007acc",
    "text": "#1a1a1a",
    "muted": "#5f6368",
    "border": "#d6d6d6",
    "danger": "#c42b1c",
    "input": "#ffffff",
}


def app_icon() -> QIcon:
    return QIcon("icon.png") if Path("icon.png").exists() else QIcon(str(ICON_FILE))


def stylesheet(theme: dict) -> str:
    return f"""
    QWidget {{
        background: {theme['bg']};
        color: {theme['text']};
        font-family: 'Segoe UI', sans-serif;
        font-size: 13px;
    }}
    QMainWindow, QDialog {{ background: {theme['bg']}; }}
    QFrame#surface, QFrame#card {{
        background: {theme['surface']};
        border: 1px solid {theme['border']};
        border-radius: 6px;
    }}
    QLabel#title {{
        color: {theme['text']};
        font-size: 22px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }}
    QLabel#subtitle {{
        color: {theme['muted']};
        font-size: 12px;
    }}
    QLabel#section {{
        color: {theme['accent']};
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1.4px;
    }}
    QLineEdit, QComboBox {{
        background: {theme['input']};
        color: {theme['text']};
        border: 1px solid {theme['border']};
        border-radius: 4px;
        padding: 8px 10px;
        min-height: 20px;
    }}
    QLineEdit:focus, QComboBox:focus {{ border: 1px solid {theme['accent']}; }}
    QComboBox QAbstractItemView {{
        background: {theme['surface']};
        color: {theme['text']};
        selection-background-color: {theme['accent']};
        border: 1px solid {theme['border']};
    }}
    QPushButton {{
        background: {theme['surface']};
        color: {theme['text']};
        border: 1px solid {theme['border']};
        border-radius: 4px;
        padding: 8px 14px;
        font-weight: 600;
    }}
    QPushButton:hover {{ border-color: {theme['accent']}; color: {theme['accent']}; }}
    QPushButton:pressed {{ background: {theme['input']}; }}
    QPushButton#primary {{
        background: {theme['accent']};
        color: #ffffff;
        border: 1px solid {theme['accent']};
    }}
    QPushButton#primary:hover {{ background: #1b8bd4; }}
    QPushButton:checked {{
        background: {theme['accent']};
        color: #ffffff;
        border: 1px solid {theme['accent']};
    }}
    QPushButton#danger:checked {{
        background: {theme['danger']};
        border: 1px solid {theme['danger']};
        color: #ffffff;
    }}
    QTabWidget::pane {{
        background: {theme['surface']};
        border: 1px solid {theme['border']};
    }}
    QTabBar::tab {{
        background: {theme['bg']};
        color: {theme['muted']};
        padding: 8px 16px;
        border: 1px solid {theme['border']};
    }}
    QTabBar::tab:selected {{
        color: {theme['text']};
        background: {theme['surface']};
        border-bottom: 2px solid {theme['accent']};
    }}
    QTableWidget {{
        background: {theme['surface']};
        color: {theme['text']};
        gridline-color: {theme['border']};
        border: 1px solid {theme['border']};
    }}
    QHeaderView::section {{
        background: {theme['bg']};
        color: {theme['muted']};
        border: none;
        padding: 8px;
        font-weight: 600;
    }}
    QListWidget {{
        background: {theme['bg']};
        color: {theme['text']};
        border: 1px solid {theme['border']};
        font-family: Consolas, 'Cascadia Mono', monospace;
        font-size: 12px;
        padding: 6px;
    }}
    QSlider::groove:horizontal {{
        height: 4px;
        background: {theme['border']};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {theme['accent']};
        width: 14px;
        margin: -6px 0;
        border-radius: 7px;
    }}
    QSlider::sub-page:horizontal {{ background: {theme['accent']}; }}
    QScrollBar:vertical {{ background: {theme['bg']}; width: 10px; }}
    QScrollBar::handle:vertical {{ background: {theme['border']}; border-radius: 4px; }}
    """


def discover_videos(base_dir: Path):
    items = []
    seen = set()
    for folder in (base_dir, base_dir / "video_logs"):
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.mp4")):
            key = str(path.resolve())
            if key not in seen:
                seen.add(key)
                items.append(path)
    for name in VIDEO_CANDIDATES:
        path = base_dir / name
        if path.is_file():
            key = str(path.resolve())
            if key not in seen:
                seen.add(key)
                items.append(path)
    return items


def default_source(base_dir: Path):
    videos = discover_videos(base_dir)
    if videos:
        return ("file", str(videos[0]))
    return ("cam", 0)


def open_capture(source):
    kind, value = source
    if kind == "file":
        cap = cv2.VideoCapture(str(value))
        return cap, Path(value).name, False
    cap = cv2.VideoCapture(int(value))
    return cap, f"WEBCAM-{value}", True


def draw_corner_brackets(frame, x1, y1, x2, y2, color, thickness=3):
    h, w = frame.shape[:2]
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = min(w - 1, int(x2)), min(h - 1, int(y2))
    length = max(18, int(min(x2 - x1, y2 - y1) * 0.28))
    cv2.line(frame, (x1, y1), (x1 + length, y1), color, thickness, cv2.LINE_AA)
    cv2.line(frame, (x1, y1), (x1, y1 + length), color, thickness, cv2.LINE_AA)
    cv2.line(frame, (x2, y1), (x2 - length, y1), color, thickness, cv2.LINE_AA)
    cv2.line(frame, (x2, y1), (x2, y1 + length), color, thickness, cv2.LINE_AA)
    cv2.line(frame, (x1, y2), (x1 + length, y2), color, thickness, cv2.LINE_AA)
    cv2.line(frame, (x1, y2), (x1, y2 - length), color, thickness, cv2.LINE_AA)
    cv2.line(frame, (x2, y2), (x2 - length, y2), color, thickness, cv2.LINE_AA)
    cv2.line(frame, (x2, y2), (x2, y2 - length), color, thickness, cv2.LINE_AA)


def draw_target_label(frame, text, x, y, color):
    font = cv2.FONT_HERSHEY_DUPLEX
    scale, thick = 1.2, 2
    (tw, th), _ = cv2.getTextSize(text, font, scale, thick)
    x, y = int(x), int(max(th + 8, y))
    cv2.rectangle(frame, (x - 4, y - th - 8), (x + tw + 4, y + 6), LABEL_BG, -1)
    cv2.putText(frame, text, (x, y), font, scale, color, thick, cv2.LINE_AA)


def apply_ptz(frame, pan: int, tilt: int, zoom: int):
    scale = 1.0 + (zoom / 100.0) * 2.5
    if scale <= 1.01:
        return frame
    h, w = frame.shape[:2]
    crop_w = max(32, int(w / scale))
    crop_h = max(32, int(h / scale))
    x = int((pan / 100.0) * (w - crop_w))
    y = int((tilt / 100.0) * (h - crop_h))
    return cv2.resize(frame[y : y + crop_h, x : x + crop_w], (w, h), interpolation=cv2.INTER_LINEAR)


def bgr_to_qimage(frame) -> QImage:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    return QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()


def apply_display_mode(frame, mode: str):
    if mode == "night":
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        lut = np.clip((np.arange(256, dtype=np.float32) - 48) * 1.65, 0, 255).astype(np.uint8)
        green = cv2.LUT(gray, lut)
        blue = (green.astype(np.float32) * 0.08).astype(np.uint8)
        red = (green.astype(np.float32) * 0.025).astype(np.uint8)
        return cv2.merge((blue, green, red))
    if mode == "thermal":
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.applyColorMap(gray, cv2.COLORMAP_JET)
    return frame.copy()


def crop_target(frame, track):
    _tid, _label, _conf, x1, y1, x2, y2 = track
    h, w = frame.shape[:2]
    box_w, box_h = max(1, x2 - x1), max(1, y2 - y1)
    pad_x, pad_y = box_w * 0.25, box_h * 0.25
    left = max(0, int(x1 - pad_x))
    top = max(0, int(y1 - pad_y))
    right = min(w, int(x2 + pad_x))
    bottom = min(h, int(y2 + pad_y))
    if right <= left or bottom <= top:
        return None
    return frame[top:bottom, left:right]


class ForensicStore:
    """SQLite metadata and image storage for high-confidence detections."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.directory = base_dir / "forensics"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.database_path = self.directory / "threats.sqlite3"
        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS detections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        target_id INTEGER NOT NULL,
                        target_class TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        image_path TEXT NOT NULL
                    )
                    """
                )

    def save(self, frame, track):
        target_id, label, confidence, *_box = track
        crop = crop_target(frame, track)
        if crop is None or crop.size == 0:
            raise ValueError(f"Cannot crop target {target_id}: its bounding box is empty")
        filename = f"threat_{uuid.uuid4().hex}.jpg"
        image_path = self.directory / filename
        if not cv2.imwrite(str(image_path), crop):
            raise OSError(f"Could not write forensic snapshot: {image_path}")
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        relative_path = image_path.relative_to(self.base_dir).as_posix()
        try:
            with closing(sqlite3.connect(self.database_path)) as connection:
                with connection:
                    cursor = connection.execute(
                        """
                        INSERT INTO detections
                            (timestamp, target_id, target_class, confidence, image_path)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (timestamp, int(target_id), str(label), float(confidence), relative_path),
                    )
                    entry_id = cursor.lastrowid
        except sqlite3.Error:
            image_path.unlink(missing_ok=True)
            raise
        return {
            "id": entry_id,
            "timestamp": timestamp,
            "target_id": int(target_id),
            "target_class": str(label),
            "confidence": float(confidence),
            "image_path": relative_path,
        }

    def entries(self):
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT id, timestamp, target_id, target_class, confidence, image_path
                FROM detections
                ORDER BY id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]


def write_fallback_icon(path: Path) -> None:
    img = np.zeros((256, 256, 3), dtype=np.uint8)
    img[:] = (18, 18, 18)
    cv2.circle(img, (128, 128), 96, (204, 122, 0), 3)
    cv2.circle(img, (128, 128), 58, (204, 122, 0), 2)
    cv2.ellipse(img, (128, 128), (96, 96), 0, -20, 70, (255, 255, 0), 4)
    cv2.circle(img, (128, 128), 6, (255, 255, 255), -1)
    pts = np.array([[128, 78], [148, 150], [128, 138], [108, 150]], np.int32)
    cv2.fillPoly(img, [pts], (220, 220, 220))
    cv2.imwrite(str(path), img)


class InferenceWorker(QThread):
    """Vision pipeline. YOLO is constructed once; only VideoCapture is hot-swapped."""

    frame_ready = pyqtSignal(object)
    detection_event = pyqtSignal(str)
    status_event = pyqtSignal(str)
    tracks_updated = pyqtSignal(list)
    telemetry = pyqtSignal(dict)
    pip_frame_ready = pyqtSignal(object)
    geofence_alert = pyqtSignal(bool, str)
    forensic_saved = pyqtSignal(dict)

    def __init__(self, base_dir: Path, forensic_store=None, parent=None):
        super().__init__(parent)
        self.base_dir = base_dir
        self.forensic_store = forensic_store
        self._running = True
        self.pan = 50
        self.tilt = 50
        self.zoom = 0
        self.locked_id = None
        self.siren_on = False
        self.flash = False
        self.conf_min = 0.25
        self.paused = False
        self.tracking_enabled = True
        self.pending_source = default_source(base_dir)
        self.click_norm = None
        self.model = None
        self._model_ready = False
        self.display_mode = "normal"
        self.trajectories = defaultdict(lambda: deque(maxlen=30))
        self.geofence_inside = set()
        self.forensic_saved_ids = set()
        self.forensic_retry_after = {}

    def stop(self):
        self._running = False

    def hot_swap_source(self, source):
        """Release/reopen cv2.VideoCapture only. Do not reload YOLO."""
        self.pending_source = source

    def request_click(self, nx: float, ny: float):
        self.click_norm = (nx, ny)

    def _init_model_once(self):
        if self._model_ready:
            return
        try:
            from ultralytics import YOLO

            self.model = YOLO(MODEL_WEIGHTS)
            self._model_ready = True
            self.detection_event.emit("> AI ENGINE READY  yolov8n.pt (loaded once)")
        except Exception as exc:
            self.model = None
            self._model_ready = True
            self.detection_event.emit(f"> AI ENGINE OFFLINE  {exc}")

    def _swap_capture(self, current_cap, source):
        if current_cap is not None:
            current_cap.release()
        cap, name, is_camera = open_capture(source)
        if cap is None or not cap.isOpened():
            self.status_event.emit(f"NO SIGNAL  |  {source}")
            return None, "NO-SOURCE", False
        self.status_event.emit(f"FEED ONLINE  |  {name}")
        self.detection_event.emit(f"> FEED HOT-SWAP  {name}")
        return cap, name, is_camera

    def run(self):
        self._init_model_once()

        cap = None
        source_name = "NO-SOURCE"
        is_camera = False
        seen_ids = set()
        persist = False
        t_prev = time.perf_counter()
        fps_smooth = 0.0

        while self._running:
            if self.pending_source is not None:
                source = self.pending_source
                self.pending_source = None
                cap, source_name, is_camera = self._swap_capture(cap, source)
                seen_ids.clear()
                persist = False
                self.locked_id = None
                self.trajectories.clear()
                self.geofence_inside.clear()
                self.forensic_saved_ids.clear()
                self.forensic_retry_after.clear()
                self.geofence_alert.emit(False, "")
                continue

            if cap is None:
                blank = np.zeros((720, 1280, 3), dtype=np.uint8)
                cv2.putText(blank, "NO SIGNAL", (400, 370), cv2.FONT_HERSHEY_DUPLEX, 1.6, CRIMSON_BGR, 2)
                self.frame_ready.emit(bgr_to_qimage(blank))
                self.pip_frame_ready.emit(None)
                self.msleep(80)
                continue

            if self.paused:
                self.msleep(30)
                continue

            ok, frame = cap.read()
            if not ok:
                if is_camera:
                    self.msleep(20)
                    continue
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                persist = False
                self.trajectories.clear()
                self.geofence_inside.clear()
                self.geofence_alert.emit(False, "")
                continue

            tracks = []
            if self.tracking_enabled and self.model is not None:
                try:
                    results = self.model.track(
                        frame,
                        persist=persist,
                        verbose=False,
                        conf=self.conf_min,
                    )
                    persist = True
                    result = results[0]
                    boxes = result.boxes
                    names = result.names or {}
                    if boxes is not None and len(boxes):
                        xyxy = boxes.xyxy.cpu().numpy()
                        confs = boxes.conf.cpu().numpy() if boxes.conf is not None else np.ones(len(xyxy))
                        clss = boxes.cls.cpu().numpy() if boxes.cls is not None else np.zeros(len(xyxy))
                        ids = boxes.id.cpu().numpy().astype(int) if boxes.id is not None else None
                        for i, box in enumerate(xyxy):
                            x1, y1, x2, y2 = box
                            label = names.get(int(clss[i]), str(int(clss[i])))
                            conf = float(confs[i])
                            if ids is not None:
                                tid = int(ids[i])
                                log_key = tid
                            else:
                                tid = hash((label, int((x1 + x2) / 2) // 80)) & 0x7FFFFFFF
                                log_key = ("cls", label)
                            tracks.append((tid, label, conf, x1, y1, x2, y2))
                            if log_key not in seen_ids:
                                seen_ids.add(log_key)
                                self.detection_event.emit(
                                    f"> TARGET ACQUIRED  id={tid}  {label}  {conf * 100:.0f}%"
                                )
                except Exception as exc:
                    self.detection_event.emit(f"> INFERENCE FAULT  {exc}")

            h, w = frame.shape[:2]
            zone = np.array(
                [[int(x * w), int(y * h)] for x, y in NO_FLY_ZONE],
                dtype=np.int32,
            )
            previous_inside = self.geofence_inside
            current_inside = set()
            for track in tracks:
                tid, label, _conf, x1, y1, x2, y2 = track
                center = ((x1 + x2) / 2, (y1 + y2) / 2)
                if cv2.pointPolygonTest(zone, center, False) >= 0:
                    current_inside.add(tid)
                    if tid not in previous_inside:
                        self.detection_event.emit(
                            f"> NO-FLY ZONE BREACH  id={tid}  {label}"
                        )
                        self.geofence_alert.emit(
                            True,
                            f"NO-FLY ZONE BREACH  |  ID {tid}  {label.upper()}",
                        )
            for tid in previous_inside - current_inside:
                self.detection_event.emit(f"> NO-FLY ZONE CLEAR  id={tid}")
            if previous_inside and not current_inside:
                self.geofence_alert.emit(False, "")
            self.geofence_inside = current_inside

            active_ids = {track[0] for track in tracks}
            for tid in tuple(self.trajectories):
                if tid not in active_ids:
                    del self.trajectories[tid]
            for track in tracks:
                tid, _label, confidence, x1, y1, x2, y2 = track
                self.trajectories[tid].append(
                    (int((x1 + x2) / 2), int((y1 + y2) / 2))
                )
                if (
                    confidence > FORENSIC_CONFIDENCE
                    and self.forensic_store is not None
                    and tid not in self.forensic_saved_ids
                    and time.monotonic() >= self.forensic_retry_after.get(tid, 0)
                ):
                    try:
                        entry = self.forensic_store.save(frame, track)
                    except (OSError, sqlite3.Error, ValueError, cv2.error) as exc:
                        self.forensic_retry_after[tid] = time.monotonic() + 5
                        self.detection_event.emit(
                            f"> FORENSIC SNAPSHOT FAILED  id={tid}  {exc}"
                        )
                    else:
                        self.forensic_saved_ids.add(tid)
                        self.forensic_retry_after.pop(tid, None)
                        self.forensic_saved.emit(entry)
                        self.detection_event.emit(
                            f"> FORENSIC SNAPSHOT SAVED  id={tid}  {confidence * 100:.0f}%"
                        )

            if self.click_norm is not None and tracks:
                nx, ny = self.click_norm
                self.click_norm = None
                h, w = frame.shape[:2]
                px, py = nx * w, ny * h
                chosen = None
                for t in tracks:
                    tid, _lab, _c, x1, y1, x2, y2 = t
                    if x1 <= px <= x2 and y1 <= py <= y2:
                        chosen = t
                        break
                if chosen is None:
                    chosen = min(
                        tracks,
                        key=lambda t: ((t[3] + t[5]) / 2 - px) ** 2 + ((t[4] + t[6]) / 2 - py) ** 2,
                    )
                self.locked_id = chosen[0]
                self.detection_event.emit(f"> LOCK  id={chosen[0]}  {chosen[1]}")

            live = {t[0] for t in tracks}
            if self.locked_id is not None and self.locked_id not in live:
                self.locked_id = None

            vis = apply_display_mode(frame, self.display_mode)
            overlay = vis.copy()
            cv2.fillPoly(overlay, [zone], CRIMSON_BGR)
            alpha = (
                0.14 + 0.16 * (0.5 + 0.5 * math.sin(time.perf_counter() * 6))
                if current_inside
                else 0.12
            )
            vis = cv2.addWeighted(overlay, alpha, vis, 1 - alpha, 0)
            cv2.polylines(vis, [zone], True, CRIMSON_BGR, 2, cv2.LINE_AA)
            zone_x, zone_y = zone[0]
            cv2.putText(
                vis,
                "NO-FLY ZONE",
                (int(zone_x), max(20, int(zone_y) - 8)),
                cv2.FONT_HERSHEY_DUPLEX,
                0.6,
                CRIMSON_BGR,
                2,
                cv2.LINE_AA,
            )

            for points in self.trajectories.values():
                if len(points) < 2:
                    continue
                path = list(points)
                for index in range(1, len(path)):
                    brightness = 0.25 + 0.75 * index / (len(path) - 1)
                    color = tuple(int(channel * brightness) for channel in CYAN_BGR)
                    cv2.polylines(
                        vis,
                        [np.array(path[index - 1:index + 1], dtype=np.int32)],
                        False,
                        color,
                        2,
                        cv2.LINE_AA,
                    )

            for t in tracks:
                tid, label, conf, x1, y1, x2, y2 = t
                color = CRIMSON_BGR if tid == self.locked_id else CYAN_BGR
                draw_corner_brackets(vis, x1, y1, x2, y2, color, thickness=3)
                draw_target_label(
                    vis,
                    f"ID {tid}  {label.upper()}  {conf * 100:.0f}%",
                    x1,
                    y1 - 12,
                    color,
                )

            if tracks:
                pip_crop = crop_target(frame, max(tracks, key=lambda track: track[2]))
                self.pip_frame_ready.emit(
                    bgr_to_qimage(apply_display_mode(pip_crop, self.display_mode))
                    if pip_crop is not None
                    else None
                )
            else:
                self.pip_frame_ready.emit(None)

            vis = apply_ptz(vis, self.pan, self.tilt, self.zoom)
            now = time.perf_counter()
            inst = 1.0 / max(now - t_prev, 1e-6)
            t_prev = now
            fps_smooth = 0.85 * fps_smooth + 0.15 * inst if fps_smooth else inst
            self._hud(vis, source_name, len(tracks), fps_smooth)
            if self.siren_on and self.flash:
                overlay = vis.copy()
                cv2.rectangle(overlay, (0, 0), (vis.shape[1] - 1, vis.shape[0] - 1), CRIMSON_BGR, 20)
                vis = cv2.addWeighted(overlay, 0.28, vis, 0.72, 0)

            self.tracks_updated.emit(tracks)
            self.frame_ready.emit(bgr_to_qimage(vis))
            self.telemetry.emit(
                {
                    "fps": fps_smooth,
                    "source": source_name,
                    "tracks": len(tracks),
                    "locked": self.locked_id,
                    "camera": is_camera,
                }
            )
            self.msleep(8)

        if cap is not None:
            cap.release()
        self.status_event.emit("FEED OFFLINE")

    def _hud(self, frame, source_name, n_tracks, fps):
        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2
        cv2.line(frame, (cx - 22, cy), (cx + 22, cy), (230, 230, 230), 1, cv2.LINE_AA)
        cv2.line(frame, (cx, cy - 22), (cx, cy + 22), (230, 230, 230), 1, cv2.LINE_AA)
        line = f"SKY-GUARD   {datetime.now().strftime('%H:%M:%S')}   {source_name}   FPS {fps:.0f}   TRACKS {n_tracks}"
        cv2.putText(frame, line, (18, 36), cv2.FONT_HERSHEY_DUPLEX, 0.7, CYAN_BGR, 2, cv2.LINE_AA)
        if self.locked_id is not None:
            cv2.putText(
                frame,
                f"LOCK  ID {self.locked_id}",
                (18, 72),
                cv2.FONT_HERSHEY_DUPLEX,
                0.8,
                CRIMSON_BGR,
                2,
                cv2.LINE_AA,
            )


class VideoView(QLabel):
    clicked = pyqtSignal(float, float)

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(720, 405)
        self._pixmap = QPixmap()
        self._draw_rect = (0, 0, 0, 0)
        self.setText("INITIALIZING SENSOR FEED")

    def set_frame(self, image: QImage):
        self._pixmap = QPixmap.fromImage(image)
        self._rescale()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton or self._pixmap.isNull():
            return
        x, y, w, h = self._draw_rect
        if w <= 0 or h <= 0:
            return
        px, py = event.pos().x(), event.pos().y()
        if x <= px <= x + w and y <= py <= y + h:
            self.clicked.emit((px - x) / w, (py - y) / h)

    def _rescale(self):
        if self._pixmap.isNull():
            return
        scaled = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        canvas = QPixmap(self.size())
        canvas.fill(QColor("#000000"))
        painter = QPainter(canvas)
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        self._draw_rect = (x, y, scaled.width(), scaled.height())
        painter.drawPixmap(x, y, scaled)
        painter.end()
        super().setPixmap(canvas)


class LoginWindow(QWidget):
    authenticated = pyqtSignal()

    def __init__(self, theme: dict):
        super().__init__()
        self.theme = theme
        self.setWindowTitle("Sky-Guard  |  Secure Access")
        self.setWindowFlags(Qt.Window)
        self.setWindowIcon(QIcon("icon.png"))
        self.setFixedSize(440, 520)
        self.setStyleSheet(stylesheet(theme))
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 36, 36, 36)
        root.addStretch()

        card = QFrame()
        card.setObjectName("card")
        col = QVBoxLayout(card)
        col.setContentsMargins(28, 28, 28, 28)
        col.setSpacing(12)

        icon = QLabel()
        pix = QPixmap("icon.png")
        if pix.isNull():
            pix = QPixmap(str(ICON_FILE))
        icon.setPixmap(pix.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon.setAlignment(Qt.AlignCenter)

        title = QLabel("SKY-GUARD")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        sub = QLabel("Ground Control Station  ·  Authorized personnel only")
        sub.setObjectName("subtitle")
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)

        self.user = QLineEdit()
        self.user.setPlaceholderText("Username")
        self.user.setText("admin")
        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.returnPressed.connect(self.try_login)

        self.error = QLabel("")
        self.error.setAlignment(Qt.AlignCenter)
        self.error.setStyleSheet("color: #d13438;")

        submit = QPushButton("SIGN IN")
        submit.setObjectName("primary")
        submit.setCursor(Qt.PointingHandCursor)
        submit.clicked.connect(self.try_login)

        col.addWidget(icon)
        col.addWidget(title)
        col.addWidget(sub)
        col.addSpacing(8)
        col.addWidget(self.user)
        col.addWidget(self.password)
        col.addWidget(self.error)
        col.addWidget(submit)

        root.addWidget(card)
        root.addStretch()
        self.user.setFocus()

    def try_login(self):
        user = self.user.text().strip()
        password = self.password.text()
        if user == AUTH_USER and password == AUTH_PASS:
            self.error.setText("")
            self.authenticated.emit()
            return
        self.error.setText("Access denied. Check credentials.")
        self.password.selectAll()
        self.password.setFocus()


class MainWindow(QMainWindow):
    def __init__(self, theme_name: str = "dark"):
        super().__init__()
        self.theme_name = theme_name
        self.theme = DARK if theme_name == "dark" else LIGHT
        self.base_dir = APP_DIR
        self.latest_tracks = []
        self.event_rows = []
        self.custom_files = []
        self._block_source = False
        self.forensic_store = None
        self.forensic_storage_error = None
        try:
            self.forensic_store = ForensicStore(self.base_dir)
        except (OSError, sqlite3.Error) as exc:
            self.forensic_storage_error = str(exc)

        self.setWindowTitle("Sky-Guard  |  Airspace Monitoring GCS")
        self.setWindowIcon(QIcon("icon.png"))
        self.resize(1560, 900)

        self.worker = InferenceWorker(self.base_dir, self.forensic_store)
        self.worker.frame_ready.connect(self.on_frame)
        self.worker.detection_event.connect(self.append_log)
        self.worker.status_event.connect(self.on_status)
        self.worker.tracks_updated.connect(self.on_tracks)
        self.worker.telemetry.connect(self.on_telemetry)
        self.worker.pip_frame_ready.connect(self.on_pip_frame)
        self.worker.geofence_alert.connect(self.on_geofence_alert)
        self.worker.forensic_saved.connect(self.on_forensic_saved)

        self.siren_timer = QTimer(self)
        self.siren_timer.setInterval(400)
        self.siren_timer.timeout.connect(self._pulse_siren)

        self._build_ui()
        self.apply_theme()
        self.populate_sources()
        self.append_log("> SESSION  operator authenticated")
        if self.forensic_storage_error:
            self.append_log(f"> FORENSIC STORAGE OFFLINE  {self.forensic_storage_error}")
            QMessageBox.warning(
                self,
                "Forensic storage unavailable",
                f"Threat snapshots cannot be saved:\n{self.forensic_storage_error}",
            )
        elif self.forensic_store is not None:
            self.load_gallery()
        self.worker.start()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        top = QHBoxLayout()
        brand = QLabel("SKY-GUARD")
        brand.setObjectName("title")
        self.status_label = QLabel("INITIALIZING")
        self.status_label.setObjectName("subtitle")
        self.stats_label = QLabel("FPS --")
        self.stats_label.setObjectName("subtitle")
        self.theme_btn = QPushButton("LIGHT MODE")
        self.theme_btn.clicked.connect(self.toggle_theme)
        top.addWidget(brand)
        top.addSpacing(16)
        top.addWidget(self.status_label, 1)
        top.addWidget(self.stats_label)
        top.addWidget(self.theme_btn)
        layout.addLayout(top)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter, 1)

        left = QFrame()
        left.setObjectName("surface")
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(10, 10, 10, 10)
        left_l.setSpacing(8)

        self.video = VideoView()
        self.video.clicked.connect(self.worker.request_click)
        left_l.addWidget(self.video, 1)
        left_l.addWidget(self._media_bar())
        left_l.addWidget(self._gimbal_bar())

        right = QFrame()
        right.setObjectName("surface")
        right.setMinimumWidth(360)
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(12, 12, 12, 12)
        head = QLabel("COMMAND")
        head.setObjectName("section")
        self.lock_state = QLabel("LOCK  STANDBY")
        self.lock_state.setObjectName("subtitle")
        right_l.addWidget(head)
        right_l.addWidget(self.lock_state)

        optics = QHBoxLayout()
        self.night_btn = QPushButton("🟢 NIGHT VISION")
        self.night_btn.setCheckable(True)
        self.night_btn.toggled.connect(self.toggle_night_vision)
        self.thermal_btn = QPushButton("🔥 THERMAL FLIR")
        self.thermal_btn.setCheckable(True)
        self.thermal_btn.toggled.connect(self.toggle_thermal)
        optics.addWidget(self.night_btn)
        optics.addWidget(self.thermal_btn)
        right_l.addLayout(optics)

        pip_title = QLabel("AUTO-ZOOM  |  HIGHEST CONFIDENCE")
        pip_title.setObjectName("section")
        self.pip_view = QLabel("NO ACTIVE TARGET")
        self.pip_view.setAlignment(Qt.AlignCenter)
        self.pip_view.setMinimumHeight(150)
        self.pip_view.setMaximumHeight(210)
        self.pip_view.setStyleSheet("background:#000; color:#9aa0a6;")
        self.warning_label = QLabel("GEOFENCE CLEAR")
        self.warning_label.setAlignment(Qt.AlignCenter)
        self.warning_label.setStyleSheet(
            "background:#18351f; color:#83d58e; padding:7px; font-weight:700;"
        )
        right_l.addWidget(pip_title)
        right_l.addWidget(self.pip_view)
        right_l.addWidget(self.warning_label)

        tabs = QTabWidget()
        tabs.addTab(self._ops_tab(), "Operations")
        tabs.addTab(self._tracks_tab(), "Tracks")
        tabs.addTab(self._log_tab(), "Event Log")
        tabs.addTab(self._gallery_tab(), "Threat Gallery")
        right_l.addWidget(tabs, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)

    def _media_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("surface")
        row = QHBoxLayout(bar)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(8)

        label = QLabel("SOURCE")
        label.setObjectName("section")
        self.source_combo = QComboBox()
        self.source_combo.currentIndexChanged.connect(self.on_source_changed)

        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse_video)
        webcam = QPushButton("Webcam")
        webcam.clicked.connect(self.use_webcam)

        self.play_btn = QPushButton("Pause")
        self.play_btn.setCheckable(True)
        self.play_btn.toggled.connect(self.toggle_pause)

        self.track_btn = QPushButton("Tracking On")
        self.track_btn.setCheckable(True)
        self.track_btn.setChecked(True)
        self.track_btn.toggled.connect(self.toggle_tracking)

        row.addWidget(label)
        row.addWidget(self.source_combo, 1)
        row.addWidget(browse)
        row.addWidget(webcam)
        row.addWidget(self.play_btn)
        row.addWidget(self.track_btn)
        return bar

    def _gimbal_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("surface")
        row = QHBoxLayout(bar)
        row.setContentsMargins(10, 8, 10, 8)
        self.pan = self._slider("PAN", 50)
        self.tilt = self._slider("TILT", 50)
        self.zoom = self._slider("ZOOM", 0)
        self.conf = self._slider("CONF", 25)
        for w in (self.pan, self.tilt, self.zoom, self.conf):
            row.addWidget(w)
        return bar

    def _slider(self, name: str, value: int) -> QWidget:
        box = QWidget()
        col = QVBoxLayout(box)
        col.setContentsMargins(4, 0, 4, 0)
        header = QHBoxLayout()
        lab = QLabel(name)
        lab.setObjectName("section")
        val = QLabel(str(value))
        val.setObjectName("subtitle")
        header.addWidget(lab)
        header.addStretch()
        header.addWidget(val)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(value)
        slider.valueChanged.connect(lambda v, n=name, lab=val: self.on_slider(n, v, lab))
        col.addLayout(header)
        col.addWidget(slider)
        box.slider = slider
        return box

    def _ops_tab(self) -> QWidget:
        page = QWidget()
        col = QVBoxLayout(page)
        col.setSpacing(8)
        self.siren_btn = QPushButton("Alert Siren")
        self.siren_btn.setObjectName("danger")
        self.siren_btn.setCheckable(True)
        self.siren_btn.toggled.connect(self.toggle_siren)
        lock_btn = QPushButton("Manual Lock")
        lock_btn.clicked.connect(self.manual_lock)
        dismiss_btn = QPushButton("Dismiss Threat")
        dismiss_btn.clicked.connect(self.dismiss_threat)
        export_btn = QPushButton("Export Report")
        export_btn.clicked.connect(self.export_report)
        hint = QLabel("Click a tracked object in the video to lock.\nVideos loop automatically at end of tape.")
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)
        for w in (self.siren_btn, lock_btn, dismiss_btn, export_btn, hint):
            col.addWidget(w)
        col.addStretch()
        return page

    def _tracks_tab(self) -> QWidget:
        page = QWidget()
        col = QVBoxLayout(page)
        self.track_table = QTableWidget(0, 4)
        self.track_table.setHorizontalHeaderLabels(["ID", "Class", "Conf", "Position"])
        self.track_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.track_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.track_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.track_table.cellClicked.connect(self.lock_from_table)
        col.addWidget(self.track_table)
        return page

    def _log_tab(self) -> QWidget:
        page = QWidget()
        col = QVBoxLayout(page)
        self.log = QListWidget()
        clear = QPushButton("Clear Log")
        clear.clicked.connect(self.clear_logs)
        col.addWidget(self.log, 1)
        col.addWidget(clear)
        return page

    def _gallery_tab(self) -> QWidget:
        page = QWidget()
        col = QVBoxLayout(page)
        self.gallery = QListWidget()
        self.gallery.setIconSize(QSize(128, 72))
        self.gallery.setSpacing(6)
        col.addWidget(self.gallery)
        return page

    def apply_theme(self):
        self.theme = DARK if self.theme_name == "dark" else LIGHT
        self.setStyleSheet(stylesheet(self.theme))
        self.theme_btn.setText("LIGHT MODE" if self.theme_name == "dark" else "DARK MODE")
        self.video.setStyleSheet(f"background:#000; color:{self.theme['muted']};")

    def toggle_theme(self):
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.apply_theme()
        self.append_log(f"> DISPLAY  {self.theme_name} mode")

    def populate_sources(self, retain=None):
        self._block_source = True
        self.source_combo.clear()
        self.source_combo.addItem("Webcam 0", ("cam", 0))
        self.source_combo.addItem("Webcam 1", ("cam", 1))
        for path in discover_videos(self.base_dir):
            self.source_combo.addItem(path.name, ("file", str(path)))
        for path in self.custom_files:
            self.source_combo.addItem(Path(path).name, ("file", path))
        if retain:
            idx = self.source_combo.findData(retain)
            if idx >= 0:
                self.source_combo.setCurrentIndex(idx)
        elif self.source_combo.count() > 2:
            self.source_combo.setCurrentIndex(2)
        self._block_source = False

    def on_source_changed(self, _index: int):
        if self._block_source:
            return
        data = self.source_combo.currentData()
        if data:
            self.worker.hot_swap_source(data)

    def browse_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select video source",
            str(self.base_dir),
            "Video Files (*.mp4 *.avi *.mkv *.mov *.webm);;All Files (*.*)",
        )
        if not path:
            return
        if path not in self.custom_files:
            self.custom_files.append(path)
        payload = ("file", path)
        self.populate_sources(retain=payload)
        self.worker.hot_swap_source(payload)

    def use_webcam(self):
        self.source_combo.setCurrentIndex(0)

    def toggle_pause(self, paused: bool):
        self.worker.paused = paused
        self.play_btn.setText("Play" if paused else "Pause")
        self.append_log("> HOLD" if paused else "> LIVE")

    def toggle_tracking(self, on: bool):
        self.worker.tracking_enabled = on
        self.track_btn.setText("Tracking On" if on else "Tracking Off")
        self.append_log("> TRACKING  " + ("enabled" if on else "disabled"))

    def toggle_night_vision(self, on: bool):
        if on:
            self.thermal_btn.setChecked(False)
            self.worker.display_mode = "night"
            self.append_log("> OPTICS  night vision enabled")
        elif not self.thermal_btn.isChecked():
            self.worker.display_mode = "normal"
            self.append_log("> OPTICS  normal display")

    def toggle_thermal(self, on: bool):
        if on:
            self.night_btn.setChecked(False)
            self.worker.display_mode = "thermal"
            self.append_log("> OPTICS  thermal FLIR enabled")
        elif not self.night_btn.isChecked():
            self.worker.display_mode = "normal"
            self.append_log("> OPTICS  normal display")

    def on_slider(self, name: str, value: int, label: QLabel):
        label.setText(str(value))
        self.worker.pan = self.pan.slider.value()
        self.worker.tilt = self.tilt.slider.value()
        self.worker.zoom = self.zoom.slider.value()
        self.worker.conf_min = max(0.05, self.conf.slider.value() / 100.0)

    @pyqtSlot(object)
    def on_frame(self, image: QImage):
        self.video.set_frame(image)

    @pyqtSlot(object)
    def on_pip_frame(self, image):
        if image is None or image.isNull():
            self.pip_view.clear()
            self.pip_view.setText("NO ACTIVE TARGET")
            return
        pixmap = QPixmap.fromImage(image).scaled(
            self.pip_view.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.pip_view.setPixmap(pixmap)

    @pyqtSlot(bool, str)
    def on_geofence_alert(self, active: bool, message: str):
        if active:
            self.warning_label.setText(message)
            self.warning_label.setStyleSheet(
                "background:#7f1d1d; color:#ffffff; padding:7px; font-weight:700;"
            )
        else:
            self.warning_label.setText("GEOFENCE CLEAR")
            self.warning_label.setStyleSheet(
                "background:#18351f; color:#83d58e; padding:7px; font-weight:700;"
            )

    @pyqtSlot(dict)
    def on_forensic_saved(self, entry: dict):
        self.add_gallery_entry(entry)

    def load_gallery(self):
        if self.forensic_store is None:
            return
        try:
            entries = self.forensic_store.entries()
        except sqlite3.Error as exc:
            self.append_log(f"> THREAT GALLERY LOAD FAILED  {exc}")
            return
        for entry in reversed(entries):
            self.add_gallery_entry(entry)

    def add_gallery_entry(self, entry: dict):
        image_path = self.base_dir / entry["image_path"]
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            self.append_log(f"> THREAT GALLERY IMAGE MISSING  {image_path}")
        details = (
            f"{entry['timestamp']}  |  ID {entry['target_id']}  |  "
            f"{entry['target_class']}  |  {entry['confidence'] * 100:.0f}%"
        )
        item = QListWidgetItem(QIcon(pixmap), details)
        self.gallery.insertItem(0, item)

    @pyqtSlot(str)
    def on_status(self, text: str):
        self.status_label.setText(text)
        self.append_log(f"> STATUS  {text}")

    @pyqtSlot(list)
    def on_tracks(self, tracks):
        self.latest_tracks = tracks
        locked = self.worker.locked_id
        if locked is None:
            self.lock_state.setText("LOCK  STANDBY")
        else:
            match = next((t for t in tracks if t[0] == locked), None)
            if match:
                self.lock_state.setText(f"LOCK  ID {match[0]}  {match[1].upper()}  {match[2]*100:.0f}%")
        self.track_table.setRowCount(len(tracks))
        for i, t in enumerate(tracks):
            tid, label, conf, x1, y1, x2, y2 = t
            vals = [str(tid), label, f"{conf*100:.0f}%", f"{int((x1+x2)/2)}, {int((y1+y2)/2)}"]
            for c, val in enumerate(vals):
                self.track_table.setItem(i, c, QTableWidgetItem(val))

    @pyqtSlot(dict)
    def on_telemetry(self, tel: dict):
        lock = f"LOCK {tel['locked']}" if tel["locked"] is not None else "NO LOCK"
        self.stats_label.setText(f"FPS {tel['fps']:.0f}   TRACKS {tel['tracks']}   {lock}")

    def lock_from_table(self, row: int, _col: int):
        item = self.track_table.item(row, 0)
        if item:
            self.worker.locked_id = int(item.text())
            self.append_log(f"> LOCK  id={item.text()}")

    def append_log(self, message: str):
        line = f"{datetime.now().strftime('%H:%M:%S')}  {message}"
        self.event_rows.append(line)
        if hasattr(self, "log"):
            self.log.addItem(QListWidgetItem(line))
            self.log.scrollToBottom()

    def clear_logs(self):
        self.log.clear()
        self.event_rows.clear()
        self.append_log("> LOG  cleared")

    def toggle_siren(self, on: bool):
        self.worker.siren_on = on
        if on:
            self.siren_timer.start()
            self.append_log("> ALERT  siren armed")
        else:
            self.siren_timer.stop()
            self.worker.flash = False
            self.append_log("> ALERT  siren silenced")

    def _pulse_siren(self):
        self.worker.flash = not self.worker.flash

    def manual_lock(self):
        if not self.latest_tracks:
            self.append_log("> LOCK  no targets")
            return
        best = max(self.latest_tracks, key=lambda t: t[2])
        self.worker.locked_id = best[0]
        self.append_log(f"> LOCK  id={best[0]}  {best[1]}")

    def dismiss_threat(self):
        self.append_log(f"> DISMISS  id={self.worker.locked_id}")
        self.worker.locked_id = None
        self.lock_state.setText("LOCK  STANDBY")

    def export_report(self):
        default = self.base_dir / f"skyguard_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Export report", str(default), "CSV (*.csv);;Text (*.txt)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["entry"])
                for row in self.event_rows:
                    writer.writerow([row])
            QMessageBox.information(self, "Sky-Guard", f"Report saved:\n{path}")
        except OSError as exc:
            QMessageBox.critical(self, "Sky-Guard", str(exc))

    def closeEvent(self, event):
        self.siren_timer.stop()
        self.worker.stop()
        self.worker.wait(2500)
        event.accept()


def main():
    os.chdir(APP_DIR)
    if not Path("icon.png").exists():
        write_fallback_icon(Path("icon.png"))

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    app.setApplicationName("Sky-Guard")
    app.setWindowIcon(QIcon("icon.png"))

    login = LoginWindow(DARK)
    main_window = {"win": None}

    def open_main():
        win = MainWindow("dark")
        win.setWindowIcon(QIcon("icon.png"))
        main_window["win"] = win
        effect = QGraphicsOpacityEffect(win)
        win.setGraphicsEffect(effect)
        win.show()
        win.raise_()
        win.activateWindow()
        anim = QPropertyAnimation(effect, b"opacity", win)
        anim.setDuration(280)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        login.close()

    login.authenticated.connect(open_main)
    login.show()
    login.raise_()
    login.activateWindow()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
