@echo off
setlocal
cd /d "%~dp0"

echo [skyblock-agent] Syncing SkyBlock item catalog (static resources)...
echo This is NOT run automatically when starting the GUI.
echo.

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
pip install -e . -q
if errorlevel 1 (
  echo Failed to install dependencies.
  exit /b 1
)

echo Downloading v2/resources/skyblock/items from Hypixel...
skyblock-agent items import
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE%==0 (
  echo Item catalog updated. You can now start the GUI with start.bat
) else (
  echo Sync failed. Check your network connection and try again.
)

pause
exit /b %EXITCODE%
