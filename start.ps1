$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "[skyblock-agent] Preparing environment..."

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

& ".venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip | Out-Null
pip install -e ".[gui]" -q

if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..."
    Copy-Item ".env.example" ".env"
    Write-Host "Add your HYPIXEL_API_KEY to .env (in-game: /api new)"
}

$HostAddress = "127.0.0.1"
$Port = 8765
Write-Host "[skyblock-agent] Starting GUI at http://${HostAddress}:${Port}"
Start-Process "http://${HostAddress}:${Port}"
skyblock-agent gui --host $HostAddress --port $Port
