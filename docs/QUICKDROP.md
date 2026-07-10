# Quick Drop — design & reference

Everything about EntryBox **Quick Drop**: what it is, how it's built, why it's
built that way, and what to do if you ever rebuild it as a "real" app. Written so
a future version (or a from-scratch rewrite) starts with full context and doesn't
repeat the mistakes we already hit.

Status: shipped in **v1.3.0** (2026-05-29). Since **v1.5.3** (2026-07-10) the
"Start server" path works on macOS and Linux too; the `quickdrop.bat` launcher
itself is still Windows (run `python3 quickdrop.py` elsewhere).

---

## 1. What it is

A small native window for dropping entries into EntryBox without opening the full
web UI. Launch it → pick a project → type a title (+ optional note) → Enter →
the entry is posted to the running EntryBox server. Drop several in a row; `Esc`
or the close button shuts the window. Re-launch to reopen.

Goal (user's words): *"a shortcut, EntryBox opens, we select the project to add
an entry, then we add one — a small window to drop in quick entries."*

It is **not** a second app or a second data store. It is a thin client over the
existing EntryBox REST API. All the rules (entry IDs, types, states, markdown
storage in `.entrybox/entries.md`) live in the server, unchanged.

---

## 2. Files

| File | Role |
|------|------|
| `quickdrop.py` | The whole desktop app — native Tkinter window, stdlib only. |
| `quickdrop.bat` | Launcher: runs `quickdrop.py` via `pythonw` (uses `.venv` python if present). |
| `app/templates/quick.html` | Browser quick-entry page served at `/quick`. Independent of the desktop app — usable in a normal browser/iframe. Vanilla JS, no Alpine. |
| `app/main.py` | Registers the `/quick` route (before the SPA catch-all). |
| `.quickdrop_state.json` | Tiny per-machine state file next to `quickdrop.py`; remembers last-used project. Safe to delete. |
| `quickdrop.log` | Runtime log written by `quickdrop.py` (startup, server launch, errors). |
| Desktop `.lnk` | `EntryBox Quick Drop.lnk` → `pythonw.exe quickdrop.py` (working dir = repo). Created on the user's Desktop. |

---

## 3. How it works (current build)

```
[ quickdrop.bat / .lnk ]
        │  launches
        ▼
[ quickdrop.py — Tkinter window ]
        │  on open: GET /health, GET /api/projects
        │  on submit: POST /api/projects/{id}/entries
        ▼
[ EntryBox server :3859 ]  ──writes──>  <project>/.entrybox/entries.md
```

- **Networking:** stdlib `urllib.request` + `json`. No `requests`, no `httpx`.
- **Threading:** all HTTP runs on a daemon thread (`_bg`); results marshal back to
  the Tk main thread via `root.after(0, …)`. Tk is single-threaded — never touch
  widgets off the main thread.
- **Server config:** reads `ENTRYBOX_BIND` / `ENTRYBOX_PORT` env vars (defaults
  `127.0.0.1:3859`), same as the server. `0.0.0.0` is normalised to `127.0.0.1`
  for the client.
- **Server-down path:** if `/health` fails on open, the window swaps the "Drop it"
  button for a **Start server** button that runs `run.bat` in a new console, then
  polls `/health` once per second (≤40 tries) and loads the project list when up.
- **Last project:** persisted in `.quickdrop_state.json` (`{"last_project": "<id>"}`)
  and preselected next launch.

### REST endpoints used

| Call | Endpoint | Notes |
|------|----------|-------|
| Health check | `GET /health` | `{"status":"ok",...}`, 200 = up. |
| List projects | `GET /api/projects` | Filters out `status == "unreachable"`. |
| Create entry | `POST /api/projects/{id}/entries` | Body `{title, body, type}`. Returns `{ok, id, ...}`. |

Valid types: `idea`, `fix`, `improve`, `docs`, `roadmap` (server defaults unknown
types to `idea`). New entries land in state `logged`.

### UI layout

Header (title + key hints) · Project dropdown + Type dropdown · Title entry ·
Note textarea · Footer (status label + Drop it / Start server button).
Palette matches the EntryBox dark theme: bg `#0f1117`, surface `#1e222b`, border
`#2a2f3a`, accent `#3b9eff`, text `#e6e8ec`. `ttk` uses the `clam` theme so colors
actually apply to the comboboxes.

Key bindings: `Enter` (title) submits · `Ctrl+Enter` (note) submits · `Esc` closes.

---

## 4. Design history & decisions (read before rebuilding)

We tried two shells before landing on Tkinter. The dead ends matter — don't repeat
them.

### Attempt 1 — pywebview + system tray + global hotkey  ❌
Stack: `pywebview` (renders the `/quick` page in a WebView2 window) + `pystray`
(tray icon) + `pynput` (global `Ctrl+Shift+E` hotkey). Failures, in order:

1. **Freeze on "Start server".** We called `window.load_url()` from a worker
   thread. The WebView2 backend deadlocks on cross-thread navigation. → Fix was to
   never navigate from Python; let the page poll `/health` in JS and navigate
   itself. (Lesson kept even after dropping pywebview.)
2. **Dead tray icon.** `pystray`'s message loop didn't reliably pump under
   pywebview's main loop; clicks/menu did nothing. Force-killing frozen runs also
   left **ghost tray icons** (Windows keeps drawing them until hovered), which
   confused debugging.
3. **Global hotkey is useless over Remote Desktop.** `pynput`'s global hotkey
   doesn't receive keystrokes in an RDP session — and the user works over RDP. A
   keyboard hotkey was the wrong trigger anyway; "a shortcut" meant a clickable
   launcher, not a hotkey.

### Attempt 2 — pywebview window only (no tray/hotkey)  ❌
Dropped tray + hotkey; just a WebView2 window opened by the launcher.

4. **Window froze on any click over RDP.** WebView2 uses GPU/hardware
   compositing; RDP sessions have no GPU, so input handling deadlocks. Tried
   `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--disable-gpu …` — unverifiable and
   still fragile. WebView2 over RDP is a known problem class.

### Attempt 3 — native Tkinter window  ✅ (current)
No browser engine, no GPU, no JS bridge, no extra processes. Tkinter renders with
GDI and is rock-solid over RDP. Stdlib-only — matches EntryBox's stdlib-CLI ethos.
Trade-off accepted: the window's look is hand-styled rather than reusing the web
theme CSS, and there's no tray/hotkey. Worth it for reliability.

### Decisions locked in
- **Trigger = click a launcher** (`.bat` / desktop `.lnk`), not a keyboard hotkey.
- **Window-only**, no system tray.
- **Stdlib only** for the desktop client (no pip deps).
- **Thin client** over the REST API — never read/write `entries.md` directly.
- All HTTP off the UI thread; widget updates only via `root.after`.

---

## 5. Known limitations (current build)

- **Launcher is Windows-only.** `quickdrop.bat` uses `pythonw.exe` and a
  Windows `.lnk`. The window itself and the Start-server button are
  cross-platform since v1.5.3 (macOS opens Terminal with `run.sh`; Linux
  spawns it detached). macOS/Linux users run `python3 quickdrop.py`.
- **No single-instance guard.** Launching twice opens two windows. (A prior
  socket-bind guard was removed with the rewrite; re-add if it matters.)
- **No global hotkey / no tray.** Intentional, but it means the window isn't
  "always one keypress away."
- **No live entry list / edit / state changes.** Drop-only. View/manage entries in
  the full UI.
- **Start-server polling is best-effort** (40 s) and the spawned server console is
  a separate window the user must not close.
- ~~Shortcut has the generic Python icon~~ Fixed in v1.5.3:
  `assets/entrybox.ico` exists and `scripts/windows/install-shortcut.ps1` uses
  it (that shortcut launches the main app, not Quick Drop; a Quick Drop `.lnk`
  can point at the same icon).

---

## 6. If you build a "real" app (future)

Pick the path by how much you want to invest. All of these keep the same contract:
**thin client over the EntryBox REST API.**

### Option A — polish the Tkinter app (cheap, stays stdlib)
- Add a single-instance guard (bind a localhost socket; if taken, exit or focus).
- ~~Generate a real window/taskbar icon~~ Done in v1.5.3: interim
  `assets/entrybox.ico` + `assets/favicon.png` (replace when the diamond mark
  is derived, see `assets/SHOTLIST.md`).
- Cross-platform launchers: `quickdrop.sh` + a `.desktop` entry (Linux) / `.app`
  wrapper (macOS); replace `run.bat` calls with the existing `run.sh`.
- Optional global hotkey **only for local (non-RDP) use** — and make it OS-level
  (a Windows shortcut "Shortcut key" on the `.lnk` survives RDP better than
  `pynput`).

### Option B — system-tray resident (if you really want a tray)
- Use a tray lib that owns the **main** thread and runs Tk on a child, or vice
  versa — the pywebview+pystray main-loop conflict is what killed it before.
- Test under RDP early; that's where tray + GPU UIs break.

### Option C — proper native/desktop framework
- **Tauri** (Rust + web frontend): small binary, can reuse the `/quick` page, but
  it's also WebView-based — **verify RDP behavior before committing** (same GPU
  risk as WebView2).
- **Electron**: heaviest, contradicts the lean/no-SaaS ethos; avoid unless there's
  a strong reason.
- **Qt (PySide6)**: native rendering, reliable over RDP, richer UI than Tkinter,
  but adds a heavy dependency.
- Recommendation: if leaving stdlib, prefer a **native-rendering** toolkit (Qt)
  over a **WebView-based** one (Tauri/Electron) specifically because of the RDP
  freeze we hit.

### Things the server already gives you (don't reinvent)
- Entry IDs, zero-padding, type/state validation, markdown storage, file locking,
  per-project + global webhooks — all server-side. A new client just calls the
  same endpoints.
- The `/quick` browser page is a working reference implementation of the same
  flow in HTML/JS; reuse its logic if you go WebView-based.

### Nice-to-haves not yet built
- Recent entries list / quick state toggle (logged→done) from the drop window.
- Multi-line / paste-image support, attachments.
- Configurable hotkey + global registration that survives RDP.
- macOS / Linux parity.
- Auto-start on login (Startup folder copy or a service).
- Bundling as a single executable (PyInstaller) so no Python install is needed.

---

## 7. Operational notes

- **Logs:** `quickdrop.log` (next to `quickdrop.py`). Startup line records the base
  URL and whether the server was up.
- **Reset last project:** delete `.quickdrop_state.json`.
- **Recreate the desktop shortcut** (PowerShell):
  ```powershell
  $ws = New-Object -ComObject WScript.Shell
  $lnk = $ws.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'EntryBox Quick Drop.lnk'))
  $lnk.TargetPath = '<repo>\.venv\Scripts\pythonw.exe'
  $lnk.Arguments = 'quickdrop.py'
  $lnk.WorkingDirectory = '<repo>'
  $lnk.Save()
  ```
- **Port/bind:** set `ENTRYBOX_PORT` / `ENTRYBOX_BIND` in the environment before
  launching if the server isn't on the `127.0.0.1:3859` default.
