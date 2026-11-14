# Launches Langflow locally.
#
# Two things this handles that a bare `langflow run` does not, on this machine:
#   1. Windows Smart App Control blocks uuid_utils' native DLL, so Langflow/
#      pyshim (a pure-Python stand-in) is put on PYTHONPATH ahead of the venv.
#   2. This Langflow version requires superuser credentials; AUTO_LOGIN restores
#      the old open-on-localhost behaviour.
#
# Run it with:  powershell -ExecutionPolicy Bypass -File Langflow\start.ps1
# Stop the server with Ctrl+C.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

$env:PYTHONPATH = Join-Path $root "pyshim"
$env:LANGFLOW_AUTO_LOGIN = "true"

$langflow = Join-Path $root "venv\Scripts\langflow.exe"
if (-not (Test-Path $langflow)) {
    Write-Error "langflow.exe not found at $langflow"
    exit 1
}

Set-Location $root
& $langflow run --open-browser
