#!/usr/bin/env bash
# EntryBox Dock app installer (macOS).
# Builds ~/Applications/EntryBox.app: a tiny native bundle that starts the
# local server if it is down, then opens EntryBox as an app window (Chrome /
# Edge --app mode when available, default browser otherwise).
#
#   bash scripts/macos/install-dock-app.sh          # build the app
#   bash scripts/macos/install-dock-app.sh --pin    # build + pin to the Dock
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
APP="$HOME/Applications/EntryBox.app"

mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>EntryBox</string>
  <key>CFBundleDisplayName</key><string>EntryBox</string>
  <key>CFBundleIdentifier</key><string>red.izo.entrybox</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>entrybox</string>
  <key>CFBundleIconFile</key><string>entrybox</string>
</dict>
</plist>
PLIST

cat > "$APP/Contents/MacOS/entrybox" <<LAUNCH
#!/usr/bin/env bash
REPO="$REPO"
healthy() { curl -sf -m 2 http://127.0.0.1:3859/health >/dev/null 2>&1; }

if ! healthy; then
  if [ -x "\$REPO/.venv/bin/python" ]; then
    (cd "\$REPO" && nohup "\$REPO/.venv/bin/python" -m uvicorn app.main:app \
      --host 127.0.0.1 --port 3859 >/dev/null 2>&1 &)
  else
    # First run: no venv yet. Bootstrap visibly in Terminal so errors show.
    open -a Terminal "\$REPO/run.sh"
  fi
  for _ in \$(seq 1 60); do healthy && break; sleep 0.5; done
fi

if [ -d "/Applications/Google Chrome.app" ]; then
  open -na "Google Chrome" --args --app=http://localhost:3859
elif [ -d "/Applications/Microsoft Edge.app" ]; then
  open -na "Microsoft Edge" --args --app=http://localhost:3859
else
  open http://localhost:3859
fi
LAUNCH
chmod +x "$APP/Contents/MacOS/entrybox"

# Icon: build an .icns from the repo PNG with stock macOS tools.
if command -v sips >/dev/null && command -v iconutil >/dev/null; then
  ICONSET="$(mktemp -d)/entrybox.iconset"
  mkdir -p "$ICONSET"
  SRC="$REPO/assets/favicon.png"
  for s in 16 32 128 256 512; do
    sips -z $s $s "$SRC" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
    sips -z $((s*2)) $((s*2)) "$SRC" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
  done
  iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/entrybox.icns" || true
fi

touch "$APP"
echo "built: $APP"

if [ "${1:-}" = "--pin" ]; then
  defaults write com.apple.dock persistent-apps -array-add \
    "<dict><key>tile-data</key><dict><key>file-data</key><dict><key>_CFURLString</key><string>$APP</string><key>_CFURLStringType</key><integer>0</integer></dict></dict></dict>"
  killall Dock
  echo "pinned to Dock."
else
  echo "To pin: drag $APP to the Dock, or re-run with --pin."
fi
