@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>&1 || (echo Python not found. Install from python.org && pause && exit /b 1)

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

python -c "import fastapi" 2>nul || (
    echo Installing dependencies...
    pip install -r requirements.txt
)

echo.
echo EntryBox running at http://localhost:3859
echo Press Ctrl+C to stop.
echo.

python -m uvicorn app.main:app --host 127.0.0.1 --port 3859 --reload
