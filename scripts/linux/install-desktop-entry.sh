#!/usr/bin/env bash
# EntryBox desktop entry installer (Linux).
# Adds an EntryBox launcher to the applications menu (and lets you pin it to
# the taskbar / favorites from there). The launcher starts the local server
# if it is down, then opens EntryBox as an app window when a Chromium-family
# browser is available.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor/512x512/apps"

mkdir -p "$APPS" "$ICONS"
cp "$REPO/assets/favicon.png" "$ICONS/entrybox.png"

cat > "$APPS/entrybox.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=EntryBox
Comment=The idea board that lives in your repo
Exec=$REPO/scripts/linux/entrybox-launcher.sh
Icon=entrybox
Terminal=false
Categories=Development;Utility;
DESKTOP

command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" || true

echo "installed: $APPS/entrybox.desktop"
echo "Find EntryBox in your app menu; pin it to the taskbar or favorites from there."
