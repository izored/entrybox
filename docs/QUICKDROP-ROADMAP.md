# Quick Drop — roadmap

Planned evolution of EntryBox **Quick Drop**, from the shipped v1.3.0 window to a
polished cross-platform drop tool. Each item keeps the core contract: **thin
client over the EntryBox REST API** — no second data store, server owns all rules.

Background, architecture, and the dead-end attempts (WebView2/RDP freeze, dead
tray, RDP hotkey) live in [QUICKDROP.md](QUICKDROP.md). Read that before picking
up any item here.

Legend: ⬜ todo · 🔄 doing · ✅ done · 💡 idea
Effort: S (hours) · M (a day) · L (multi-day)

---

## Shipped — v1.3.0 (2026-05-29)

- ✅ Native Tkinter drop window (stdlib only, RDP-solid)
- ✅ Project + type selectors, title, optional note
- ✅ `POST /api/projects/{id}/entries` submit; drop several in a row
- ✅ Server-down detection + "Start server" button (runs `run.bat`, polls `/health`)
- ✅ Remembers last-used project (`.quickdrop_state.json`)
- ✅ Launcher `quickdrop.bat` + desktop `.lnk`
- ✅ Docs: design + architecture reference

---

## Phase 1 — polish current Windows app (cheap, stays stdlib)

Goal: make the existing window feel finished. No new heavy deps.

| | Item | Effort | Notes |
|--|------|--------|-------|
| ⬜ | **Single-instance guard** | S | Bind a localhost socket on launch; if taken, focus the existing window (or exit). Prevents stacked windows. |
| ⬜ | **Real app icon** | S | Generate `.ico` from `assets/logo.svg` as a one-time build step (Pillow in build env, *not* a runtime dep). Set on window + `.lnk`. |
| ⬜ | **Taskbar pin + Startup option** | S | Document/script pinning; optional copy of `.lnk` to the Startup folder for auto-availability. |
| ⬜ | **Keyboard polish** | S | Tab order, `Ctrl+Enter` everywhere, dropdown type-ahead, focus title on open. |
| ⬜ | **Inline validation + nicer toasts** | S | Clearer error/success states; auto-clear status after N seconds. |
| ⬜ | **Window position memory** | S | Persist last window x/y in the state file. |

---

## Phase 2 — feature depth (still Tkinter)

Goal: reduce trips to the full UI for common quick actions.

| | Item | Effort | Notes |
|--|------|--------|-------|
| ⬜ | **Recent entries strip** | M | Show last ~5 entries for the selected project (`GET …/entries?limit=5`); read-only. |
| ⬜ | **Quick state toggle** | M | Flip an entry `logged→done` (or pick state) from the recent strip via `PATCH …/entries`. |
| ⬜ | **Project quick-switch** | S | Keyboard shortcut to cycle projects; remember per-project last type. |
| ⬜ | **Paste / attach** | M | Multi-line paste cleanup; later, image/file attach if the server grows support. |
| ⬜ | **Theme sync** | M | Pull active theme vars from `/api/themes/active` and map the key colors onto the Tk palette so the window matches the web UI. |

---

## Phase 3 — cross-platform

Goal: leave Windows-only behind. Tkinter is already portable; the launcher and
server-start path are not.

| | Item | Effort | Notes |
|--|------|--------|-------|
| ⬜ | **macOS + Linux launchers** | M | `quickdrop.sh`, a `.desktop` entry (Linux), `.app` wrapper (macOS). Replace `run.bat`/`cmd /k` with `run.sh` for server start. |
| ⬜ | **OS-agnostic server-start** | S | Detect platform; spawn the right run script + console. |
| ⬜ | **Path/port config UI** | S | Small settings affordance for `ENTRYBOX_BIND`/`ENTRYBOX_PORT` instead of env-only. |

---

## Phase 4 — "real app" (only if demand justifies leaving stdlib)

Goal: richer UX and/or distribution as a standalone binary. **Decision gate** —
don't start without a real need; current app already meets the original goal.

| | Item | Effort | Notes |
|--|------|--------|-------|
| 💡 | **Single-binary bundle** | M | PyInstaller-package the Tkinter app so no Python install is needed. Lowest-risk "real app" step. |
| 💡 | **Qt (PySide6) rewrite** | L | Native rendering, RDP-safe, richer UI than Tkinter. Heavy dep. Preferred over WebView frameworks **because of the RDP freeze we hit**. |
| 💡 | **Tauri rewrite** | L | Reuses the `/quick` web page; small binary — **but WebView-based**, so *verify RDP behavior first* (same GPU risk as WebView2). |
| 💡 | **Global hotkey (local only)** | M | OS-level hotkey via the `.lnk` "Shortcut key" property (survives RDP better than `pynput`). Don't ship a `pynput`-style global hotkey — it's dead over RDP. |
| 💡 | **System tray, done right** | M | Only if a resident tray is genuinely wanted. Must resolve the main-loop ownership conflict that killed pystray before; test under RDP early. |

---

## Explicitly out of scope

- A second data store or local DB — entries always live in `.entrybox/entries.md`
  via the server.
- Reading/writing entry files directly from the client.
- Electron (contradicts the lean / no-SaaS ethos unless a strong reason appears).
- A `pynput` global hotkey or a pywebview/WebView2 window (both failed over RDP —
  see [QUICKDROP.md](QUICKDROP.md) §4).

---

## Guiding principles

1. **Thin client.** All rules stay server-side; the client only calls the API.
2. **Reliability over flash.** Native rendering beat a prettier WebView because it
   survives Remote Desktop. Keep that bias.
3. **Stdlib until proven necessary.** Add a heavy dep only when a phase-4 need
   clearly justifies it.
4. **Trigger = a click.** Launcher/shortcut, not a fragile global hotkey.
5. **Verify under RDP** for any UI-framework change — that's where past attempts broke.
