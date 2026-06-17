<#
  Build a Windows .exe for a Raven desktop shell. RUN ON WINDOWS (PowerShell),
  not inside WSL — PyInstaller produces a binary for the OS it runs on.

  Prereqs (on Windows, in the repo):
    py -m venv .venv ; .\.venv\Scripts\Activate.ps1
    pip install -e ".[build]"
    pip install -e ".[desktop-webview]"   # for -Target webview
    pip install -e ".[desktop-qt]"        # for -Target qt

  Usage:
    .\scripts\build-exe.ps1 -Target webview          # Option A (pywebview)
    .\scripts\build-exe.ps1 -Target qt               # Option B (PySide6)
    .\scripts\build-exe.ps1 -Target webview -AllInOne  # bundle the server too

  By default the .exe is a THIN SHELL: it opens the UI and connects to a running
  daemon (RAVEN_URL or http://127.0.0.1:1802). Keep the daemon running. This keeps
  the binary small. -AllInOne bundles the full backend (large, heavier to build).
#>
param(
  [ValidateSet("webview", "qt")] [string]$Target = "webview",
  [switch]$AllInOne
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ($Target -eq "webview") {
  $entry = "raven\desktop\pywebview_app.py"
  $collect = @("--collect-all", "webview")
} else {
  $entry = "raven\desktop\qt_app.py"
  $collect = @("--collect-all", "PySide6")
}

$args = @(
  "--noconfirm", "--clean", "--windowed",
  "--name", "Raven",
  "--paths", ".",
  "--add-data", "raven\api\static;raven\api\static"
) + $collect

if ($AllInOne) {
  # Pull the backend stack into the binary (large). Add more --collect-all as needed.
  $args += @(
    "--collect-all", "chromadb",
    "--collect-all", "langchain",
    "--collect-all", "langgraph",
    "--collect-all", "tiktoken",
    "--hidden-import", "raven.api.app"
  )
}

# Optional icon: place an .ico at assets\raven.ico to brand the window/taskbar.
if (Test-Path "assets\raven.ico") { $args += @("--icon", "assets\raven.ico") }

$args += $entry

Write-Host "[build-exe] pyinstaller $($args -join ' ')"
pyinstaller @args

Write-Host "[build-exe] Done -> dist\Raven\Raven.exe"
