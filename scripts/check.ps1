# Runs every automated check for the repository. Usage (from the repo root):
#   powershell -ExecutionPolicy Bypass -File scripts/check.ps1
# Requires the setup steps in README.md to have been done once, and the
# database container to be running:  docker compose up -d --wait
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "== Backend tests (pytest) =="
Push-Location "$root/backend"
& ".venv/Scripts/python.exe" -m pytest -q
$backend = $LASTEXITCODE
Pop-Location

Write-Host "== Frontend type-check and build =="
Push-Location "$root/frontend"
npm run build
$frontend = $LASTEXITCODE
Pop-Location

if ($backend -ne 0 -or $frontend -ne 0) {
    Write-Host "CHECKS FAILED (backend=$backend, frontend=$frontend)"
    exit 1
}
Write-Host "ALL CHECKS PASSED"
