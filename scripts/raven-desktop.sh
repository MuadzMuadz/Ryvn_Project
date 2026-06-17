#!/usr/bin/env bash
# Launch Raven as a desktop app window (Jarvis-style, chromeless).
# Zero extra deps: opens the running daemon's UI in a Chromium "--app" window
# (no tabs, no address bar, own taskbar entry). Works from WSL via Windows Chrome/Edge.
#
# Usage: ./scripts/raven-desktop.sh   (daemon must be running, see start.sh)
set -uo pipefail

URL="${RAVEN_URL:-http://localhost:1802}"
PROFILE="${HOME}/.raven-desktop"   # isolated profile so it feels like its own app

CANDIDATES=(
  "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
  "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe"
  "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
  "google-chrome" "google-chrome-stable" "chromium" "chromium-browser" "microsoft-edge"
)

BROWSER=""
for b in "${CANDIDATES[@]}"; do
  if [ -x "$b" ] || command -v "$b" >/dev/null 2>&1; then BROWSER="$b"; break; fi
done

if [ -z "$BROWSER" ]; then
  echo "[raven-desktop] No Chromium-based browser found. Just open $URL in any browser." >&2
  exit 1
fi

# Wait briefly for the daemon to answer.
for _ in $(seq 1 20); do curl -sf -o /dev/null "$URL/health" 2>/dev/null && break; sleep 0.3; done

echo "[raven-desktop] launching $URL"
exec "$BROWSER" \
  --app="$URL" \
  --user-data-dir="$PROFILE" \
  --window-size=1120,800 \
  --class=Raven --name=Raven \
  >/dev/null 2>&1
