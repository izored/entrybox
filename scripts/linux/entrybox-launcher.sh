#!/usr/bin/env bash
# EntryBox launcher (Linux). Ensures the local server is running, then opens
# EntryBox as an app window (Chromium family) or in the default browser.
set -u

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
healthy() { curl -sf -m 2 http://127.0.0.1:3859/health >/dev/null 2>&1; }

if ! healthy; then
  if [ -x "$REPO/.venv/bin/python" ]; then
    (cd "$REPO" && nohup "$REPO/.venv/bin/python" -m uvicorn app.main:app \
      --host 127.0.0.1 --port 3859 >/dev/null 2>&1 &)
  else
    # First run: bootstrap in a terminal so errors are visible.
    for term in x-terminal-emulator gnome-terminal konsole xterm; do
      if command -v "$term" >/dev/null; then
        "$term" -e "bash '$REPO/run.sh'" & break
      fi
    done
  fi
  for _ in $(seq 1 60); do healthy && break; sleep 0.5; done
fi

for browser in google-chrome chromium chromium-browser microsoft-edge brave-browser; do
  if command -v "$browser" >/dev/null; then
    exec "$browser" --app=http://localhost:3859
  fi
done
exec xdg-open http://localhost:3859
