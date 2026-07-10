# How to pin EntryBox to your taskbar, Dock, or app menu

EntryBox is a browser UI on purpose. There is no installer and nothing to
sign. The app feel comes from your browser's app mode (a chromeless window
with its own icon) plus a small launcher per OS that starts the server when
it is down. This guide is the long version of the README's "Pin it like an
app" section, with troubleshooting.

Every launcher does the same three steps:

1. Check `http://127.0.0.1:3859/health`.
2. If the server is down, start it quietly (or bootstrap visibly on first
   run, so errors are seen).
3. Open `http://localhost:3859` as an app window via Chrome, Edge, or
   Chromium. Without a Chromium-family browser you get a normal tab.

---

## Windows 11 / 10

From the repo folder:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\install-shortcut.ps1
```

This creates two shortcuts (Start Menu and Desktop) with the EntryBox icon,
pointing at `scripts\windows\entrybox-launcher.vbs`.

Then pin it, two clicks: open the **Start menu**, find **EntryBox**,
right-click, **Pin to taskbar**. Windows does not allow scripts to pin for
you; there is no supported API for it.

**Troubleshooting**

- *PowerShell refuses to run the script*: the `-ExecutionPolicy Bypass` flag
  in the command above handles the default policy. If your machine enforces
  policy via GPO, create the shortcut by hand: target
  `wscript.exe "<repo>\scripts\windows\entrybox-launcher.vbs"`, icon
  `<repo>\assets\entrybox.ico`.
- *Window opens but shows a connection error*: first run without a venv
  bootstraps in a visible console via `run.bat`; give it a minute, then
  reopen from the shortcut.
- *For contributors*: the launcher runs `python.exe` with a hidden window,
  never `pythonw.exe`. pythonw has no stdout/stderr and uvicorn's logging
  crashes instantly without them.

## macOS

From the repo folder:

```bash
bash scripts/macos/install-dock-app.sh          # builds ~/Applications/EntryBox.app
bash scripts/macos/install-dock-app.sh --pin    # same, and pins it to the Dock
```

The script builds a plain `.app` bundle (Info.plist, a shell executable, and
an `.icns` icon generated on the spot with the stock `sips` and `iconutil`
tools). No signing is needed: bundles you build locally carry no quarantine
attribute, so Gatekeeper does not block them.

Prefer dragging? Skip `--pin` and drag `~/Applications/EntryBox.app` onto
the Dock.

**Troubleshooting**

- *"Permission denied" running `run.sh`*: fixed in v1.5.3 (the executable
  bit now ships in git). On an older checkout: `chmod +x run.sh`.
- *App bounces once and nothing opens*: the server is bootstrapping in
  Terminal on first run. Wait for "EntryBox running", then click the Dock
  icon again.
- *Rebuilding after moving the repo*: the repo path is baked into the bundle
  at install time. Re-run the script after moving the folder.

## Linux

From the repo folder:

```bash
bash scripts/linux/install-desktop-entry.sh
```

This installs `~/.local/share/applications/entrybox.desktop` plus the icon,
so EntryBox appears in your app menu. Pin it to the taskbar, panel, or
favorites the way your desktop environment does it (GNOME: right-click in
the app grid, **Pin to Dash**).

**Troubleshooting**

- *Menu entry doesn't appear*: some environments cache aggressively; log out
  and in, or run `update-desktop-database ~/.local/share/applications`.
- *Opens a plain tab instead of an app window*: install any Chromium-family
  browser (`google-chrome`, `chromium`, `microsoft-edge`, `brave-browser`);
  the launcher picks the first one it finds.
- *First run*: the launcher opens a terminal running `run.sh` so you can see
  the bootstrap. After that it starts the server silently.

---

## Quick Drop is separate

These shortcuts open the full EntryBox UI. The Quick Drop mini window
(`quickdrop.bat` on Windows, `python3 quickdrop.py` elsewhere) is its own
thing: see [QUICKDROP.md](QUICKDROP.md).
