@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>&1 || (echo Python not found. Install from python.org && pause && exit /b 1)

REM Use the project venv if present (it has tkinter from the base Python),
REM otherwise fall back to system python. Quick Drop is stdlib-only — no pip deps.
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" quickdrop.py
) else (
    start "" pythonw quickdrop.py
)
