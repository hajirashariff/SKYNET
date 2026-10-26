#!/usr/bin/env python3
"""Sky-Guard launcher: install dependencies, then start the GCS."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PACKAGES = ["pyqt5", "opencv-python", "ultralytics", "numpy"]


def install_dependencies() -> None:
    cmd = [sys.executable, "-m", "pip", "install", *PACKAGES]
    print("Installing Sky-Guard dependencies:")
    print(" ", " ".join(cmd))
    subprocess.check_call(cmd)
    print("Dependency installation confirmed.")


def launch_app() -> None:
    app_path = Path(__file__).resolve().parent / "main.py"
    if not app_path.is_file():
        raise FileNotFoundError(f"Could not find application file: {app_path}")
    print(f"Launching Sky-Guard GCS: {app_path}")
    subprocess.check_call([sys.executable, str(app_path)])


def main() -> int:
    try:
        install_dependencies()
        launch_app()
    except subprocess.CalledProcessError as exc:
        print(f"Launcher failed (exit {exc.returncode}).", file=sys.stderr)
        return exc.returncode or 1
    except Exception as exc:
        print(f"Launcher failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
