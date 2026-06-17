$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "[skyblock-agent] Syncing SkyBlock item catalog (static resources)..."
Write-Host "This is NOT run automatically when starting the GUI."
Write-Host ""

$EnsurePy = if (Test-Path ".venv\Scripts\python.exe") {
    ".venv\Scripts\python.exe"
} else {
    "python"
}
& $EnsurePy scripts/ensure_env.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Downloading v2/resources/skyblock/items from Hypixel..."
& ".venv\Scripts\skyblock-agent.exe" items import
$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "Item catalog updated. You can now start the GUI with start.ps1"
} else {
    Write-Host "Sync failed. Check your network connection and try again."
}

exit $exitCode
