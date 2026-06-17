<#
  Run the Raven BACKEND (headless API daemon) as a Windows service.

  Why the backend, not the desktop app: Windows services run in a non-interactive
  session and cannot show a GUI. So the always-on piece is the daemon; the desktop
  .exe is a normal app (autostart at login, lives in the tray) that connects to it.

  This uses NSSM (https://nssm.cc) — the simplest way to service-wrap any process.
  Install NSSM first (e.g. `winget install NSSM` or `choco install nssm`).

  Usage (PowerShell as Administrator, on Windows with the project installed):
    .\scripts\windows-service.ps1 -Action install
    .\scripts\windows-service.ps1 -Action start
    .\scripts\windows-service.ps1 -Action stop
    .\scripts\windows-service.ps1 -Action remove
#>
param(
  [ValidateSet("install", "start", "stop", "remove")] [string]$Action = "install",
  [int]$Port = 1802
)

$ErrorActionPreference = "Stop"
$svc = "RavenDaemon"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

switch ($Action) {
  "install" {
    if (-not (Test-Path $python)) { throw "Expected venv python at $python. Create it and `pip install -e .` first." }
    nssm install $svc $python "-m" "uvicorn" "raven.api.app:app" "--host" "127.0.0.1" "--port" "$Port"
    nssm set $svc AppDirectory $root
    nssm set $svc AppStdout (Join-Path $root "data\daemon.out.log")
    nssm set $svc AppStderr (Join-Path $root "data\daemon.err.log")
    nssm set $svc Start SERVICE_AUTO_START
    Write-Host "[service] installed '$svc' -> http://127.0.0.1:$Port"
  }
  "start"  { nssm start  $svc }
  "stop"   { nssm stop   $svc }
  "remove" { nssm stop   $svc; nssm remove $svc confirm }
}
