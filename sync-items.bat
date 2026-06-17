@echo off
setlocal
cd /d "%~dp0"

echo [skyblock-agent] Syncing SkyBlock item catalog (static resources)...
echo This is NOT run automatically when starting the GUI.
echo.

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\ensure_env.py
) else (
  python scripts\ensure_env.py
)
if errorlevel 1 exit /b 1

echo Downloading v2/resources/skyblock/items from Hypixel...
".venv\Scripts\skyblock-agent.exe" items import
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE%==0 (
  echo Item catalog updated. You can now start the GUI with start.bat
) else (
  echo Sync failed. Check your network connection and try again.
)

pause
exit /b %EXITCODE%
