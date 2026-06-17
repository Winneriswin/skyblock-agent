$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "[skyblock-agent] Syncing SkyBlock item icons..."
Write-Host "Requires item catalog first (run sync-items.ps1 if needed)."
Write-Host "Icons are cached locally under data/processed/items/icons/"
Write-Host ""

$EnsurePy = if (Test-Path ".venv\Scripts\python.exe") {
    ".venv\Scripts\python.exe"
} else {
    "python"
}
& $EnsurePy scripts/ensure_env.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Downloading icons for catalog items..."
& ".venv\Scripts\skyblock-agent.exe" items icons import
$ExitCode = $LASTEXITCODE

Write-Host ""
if ($ExitCode -eq 0) {
    Write-Host "Item icons updated. Start the GUI with start.bat to see icons in Resources."
} else {
    Write-Host "Sync failed. Run sync-items.ps1 first, then try again."
}

exit $ExitCode
