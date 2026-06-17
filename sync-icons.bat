@echo off
setlocal
cd /d "%~dp0"

echo [skyblock-agent] Syncing SkyBlock item icons...
echo Requires item catalog first (run sync-items.bat if needed).
echo Icons are cached locally under data/processed/items/icons/
echo.

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\ensure_env.py
) else (
  python scripts\ensure_env.py
)
if errorlevel 1 exit /b 1

echo Downloading icons for catalog items...
".venv\Scripts\skyblock-agent.exe" items icons import
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE%==0 (
  echo Item icons updated. Start the GUI with start.bat to see icons in Resources.
) else (
  echo Sync failed. Run sync-items.bat first, then try again.
)

pause
exit /b %EXITCODE%
