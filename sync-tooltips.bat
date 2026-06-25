@echo off
setlocal
cd /d "%~dp0"

echo [skyblock-agent] Syncing SkyBlock item tooltips (NEU + Wiki + Hypixel stats)...
echo This is NOT run automatically when starting the GUI.
echo First sync may download ~8000 NEU item files and take a few minutes.
echo.

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\ensure_env.py
) else (
  python scripts\ensure_env.py
)
if errorlevel 1 exit /b 1

".venv\Scripts\skyblock-agent.exe" items tooltips import
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE%==0 (
  echo Tooltip cache updated. Re-import items first if stats fallback looks outdated:
  echo   sync-items.bat
) else (
  echo Sync failed. Check your network connection and try again.
)

pause
exit /b %EXITCODE%
