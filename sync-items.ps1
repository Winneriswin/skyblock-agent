$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "[skyblock-agent] Syncing SkyBlock item catalog (static resources)..."
Write-Host "This is NOT run automatically when starting the GUI."
Write-Host ""

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

& ".venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip | Out-Null
pip install -e . -q

Write-Host "Downloading v2/resources/skyblock/items from Hypixel..."
skyblock-agent items import
$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "Item catalog updated. You can now start the GUI with start.ps1"
} else {
    Write-Host "Sync failed. Check your network connection and try again."
}

exit $exitCode
