@echo off
cd /d "%~dp0"
echo Starting Sky-Guard GCS...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application stopped or encountered an error.
    pause
)
