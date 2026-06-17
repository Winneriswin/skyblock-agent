@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

title Skyblock Agent
echo.
echo ============================================================
echo  Skyblock Agent - GUI startup
echo ============================================================
echo [debug] Batch file : %~f0
echo [debug] Project dir: %CD%
echo.

set "HOST=127.0.0.1"
set "PORT=8765"
set "PY=.venv\Scripts\python.exe"
set "CLI=.venv\Scripts\skyblock-agent.exe"

echo [debug] Step 1/5 - Check environment
echo ------------------------------------------------------------
if not exist "%PY%" (
  echo [debug] No venv yet - using system Python
  where python >nul 2>&1
  if errorlevel 1 (
    echo [FAIL] Python not found. Install Python 3.9+ first.
    goto :fail
  )
  set "PY=python"
  set "CLI=skyblock-agent"
) else (
  echo [debug] Using venv Python: %PY%
)

"%PY%" --version
if errorlevel 1 (
  echo [FAIL] Python failed to run.
  goto :fail
)

echo.
echo [debug] Step 2/5 - Ensure dependencies
echo ------------------------------------------------------------
"%PY%" scripts\ensure_env.py --gui --verbose
if errorlevel 1 (
  echo [FAIL] ensure_env.py failed.
  goto :fail
)

if not exist "%CLI%" (
  echo [FAIL] CLI not found: %CLI%
  goto :fail
)
echo [debug] CLI ready: %CLI%

echo.
echo [debug] Step 3/5 - GUI diagnostics
echo ------------------------------------------------------------
"%PY%" scripts\diagnose_gui.py %PORT%
set "DIAG=!ERRORLEVEL!"
if not "!DIAG!"=="0" (
  echo [WARN] Diagnostics exit code: !DIAG! - continuing anyway.
) else (
  echo [debug] Diagnostics passed.
)

echo.
echo [debug] Step 4/5 - .env / API key
echo ------------------------------------------------------------
if not exist ".env" (
  echo [debug] Creating .env from .env.example...
  copy /Y ".env.example" ".env" >nul
) else (
  echo [debug] .env exists.
)

findstr /C:"your-api-key-here" ".env" >nul
if not errorlevel 1 (
  echo [WARN] HYPIXEL_API_KEY is still the placeholder in .env
  echo        Profile lookup will fail until you add a real key.
  echo        Get one in-game with: /api new
  echo.
) else (
  echo [debug] HYPIXEL_API_KEY appears configured.
)

echo.
echo [debug] Step 5/5 - Start web server
echo ------------------------------------------------------------
echo [debug] URL  : http://%HOST%:%PORT%/
echo [debug] Health: http://%HOST%:%PORT%/api/health
echo [debug] Keep this window open. Press Ctrl+C to stop the server.
echo ============================================================
echo.

"%CLI%" gui --host %HOST% --port %PORT% --log-level info
set "EXITCODE=!ERRORLEVEL!"

echo.
echo ============================================================
if "!EXITCODE!"=="0" (
  echo [debug] Server exited normally.
) else (
  echo [FAIL] Server exited with code !EXITCODE!
)
echo ============================================================
goto :end

:fail
set "EXITCODE=1"
echo.
echo [FAIL] Startup aborted. See messages above.

:end
echo.
echo Press any key to close this window...
pause >nul
exit /b !EXITCODE!
