$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$EnsurePy = if (Test-Path ".venv\Scripts\python.exe") {
    ".venv\Scripts\python.exe"
} else {
    "python"
}
& $EnsurePy scripts/ensure_env.py --gui
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..."
    Copy-Item ".env.example" ".env"
    Write-Host "Add your HYPIXEL_API_KEY to .env (in-game: /api new)"
}

$HostAddress = "127.0.0.1"
$Port = 8765
Write-Host "[skyblock-agent] Starting GUI at http://${HostAddress}:${Port}"
Write-Host "Browser opens after the server is ready. Use Ctrl+C to stop."
& ".venv\Scripts\skyblock-agent.exe" gui --host $HostAddress --port $Port
