$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "[skyblock-agent] Syncing SkyBlock item tooltips (NEU + Wiki + Hypixel stats)..."
Write-Host "This is NOT run automatically when starting the GUI."
Write-Host "First sync may download ~8000 NEU item files and take a few minutes."
Write-Host ""

$EnsurePy = if (Test-Path ".venv\Scripts\python.exe") {
    ".venv\Scripts\python.exe"
} else {
    "python"
}
& $EnsurePy scripts/ensure_env.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& ".venv\Scripts\skyblock-agent.exe" items tooltips import
$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "Tooltip cache updated."
    Write-Host "Re-run sync-items if Hypixel stats fallback looks outdated."
} else {
    Write-Host "Sync failed. Check your network connection and try again."
}

exit $exitCode
