@echo off
setlocal
cd /d "%~dp0"

echo [skyblock-agent] Preparing environment...

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo Failed to create venv. Install Python 3.9+ and try again.
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip >nul
pip install -e ".[gui]" -q
if errorlevel 1 (
  echo Failed to install dependencies.
  exit /b 1
)

if not exist ".env" (
  echo Creating .env from .env.example...
  copy /Y ".env.example" ".env" >nul
)

findstr /C:"your-api-key-here" ".env" >nul
if not errorlevel 1 (
  echo.
  echo ============================================================
  echo  HYPIXEL_API_KEY is not configured yet.
  echo  1. Join Hypixel and run: /api new
  echo  2. Edit .env in this folder and paste your key
  echo ============================================================
  echo.
  pause
)

set HOST=127.0.0.1
set PORT=8765
echo [skyblock-agent] Starting GUI at http://%HOST%:%PORT%
start "" "http://%HOST%:%PORT%"
skyblock-agent gui --host %HOST% --port %PORT%
