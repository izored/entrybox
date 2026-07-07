# Changelog

All notable changes to EntryBox are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.5.1] - 2026-06-04

> _Status: in active development (updated 2026-06-14)._

### Also queued for this session (after 1.5.1)

- **N6** file-tree UI + file-scoped entries (backend already built in v1.5.0)
- **N4** Chrome extension (MV3: popup, context-menu, screenshot→attachment)
- **N5** companion app + quick.html refresh (paste attach, undo, capture-contract parity)
- **N2** per-project custom types + broadened positioning / copy
- **P3** search / filter bar
- **P4** resurfacing / snooze (stale-badge + saved filter)
- **P6** resolution link on done (commit / PR / file ref)

### Added

- Priority, due date, and recurrence fields on entries. The header stores
  optional `· pri:A · due:2026-06-10 · recur:weekly` segments; all three fields
  are optional and backward-compatible (old entries parse with `null` values).
  Priority is A/B/C (A = urgent). Recurrence values: `daily`, `weekly`,
  `monthly`, `yearly`.
- Priority and due date badges on entry cards. Priority uses urgency colors
  (A = red, B = orange, C = green). Due badge adapts: overdue shows a ⚠ prefix
  in red, today shows "due today", tomorrow shows "due tomorrow", future shows
  the date string in a dimmed style. All colors come from existing theme CSS vars
  — no hardcoded values added.
- Recurrence indicator (↺) on cards with a tooltip naming the recur interval.
- Priority, due date, and recur controls in the log form and inline edit form.
- Auto-re-log on done: when a recurring entry is marked `done`, EntryBox creates
  the next occurrence immediately with the computed next due date (daily = +1 d,
  weekly = +7 d, monthly = +30 d, yearly = +365 d) and returns it as
  `recur_entry` in the PATCH response. The UI unshifts the new entry without a
  reload and fires the `entry_created` webhook.
- Done entries hidden section: `done`-state entries are separated into a
  collapsible section below the main list. A ▼ / ▲ toggle shows the count and
  expands/collapses. Open entries stay in the main list.
- `?` help overlay: pressing `?` (or the `?` button in the topbar) toggles a
  modal showing all keyboard shortcuts, entry types, state machine, and a
  priority/due/recur quick reference. `Escape` closes it.
- `/api/network` endpoint: returns the server's LAN IP addresses and port number
  for local-network clients.
- `ENTRYBOX_MAX_UPLOAD_MB` environment variable (default `25`). Sets the
  attachment size limit for both upload and serving — raise it for larger files.
- Attachment upload feedback. A client-side size pre-check rejects an oversize
  file instantly (toast naming the file size and the limit) instead of failing
  after a wasted round-trip; a success toast confirms each attach with its size;
  and an image that fails to load (missing, oversize, or server down) now shows a
  clickable "⚠ couldn't load — open file" fallback link instead of a silent
  broken image.

### Changed

- Agent annotation blocks (written into `CLAUDE.md`, `.cursorrules`, etc.) now
  include an optional-fields section instructing the agent to use `priority`,
  `due`, and `recur` when the user asks for them (e.g. "mark this high
  priority", "set due date to Friday", "make this repeat weekly"). The JS mirror
  of `build_annotation()` in `index.html` matches.
- REST API: POST `/api/projects/{id}/entries` and PATCH
  `/api/projects/{id}/entries` both accept `priority`, `due`, and `recur`
  fields. PATCH returns `recur_entry` in the response body when a recurring
  entry is marked done.
- Due date input replaced with a custom branded datepicker. The native
  `<input type="date">` browser popup has been removed; an Alpine.js calendar
  component now renders the picker using the active theme's CSS variables
  (`--surface`, `--surface2`, `--border`, `--accent`, `--text`, `--text2`,
  `--radius`). Selection, clear, and "Today" shortcut work in the log form and
  both inline edit forms. The picker is 222 px wide and does not stretch to fill
  the form row.
- highlight.js and Alpine.js are now vendored locally under `app/static/vendor/`
  instead of loading from `cdn.jsdelivr.net`. EntryBox boots fully offline and
  the script bytes are pinned in-repo — Alpine moved off the floating `3.x.x`
  range to a fixed `3.15.12`. There are now no third-party script origins.

### Fixed

- Attachments larger than 512 KB uploaded successfully but returned **413
  Request Entity Too Large** when the page tried to display them: the `/file`
  serve route reused the small text-preview cap (`MAX_READ_BYTES`, 512 KB) for
  attachment serving while uploads allowed far more. Attachments now serve up to
  the upload limit (default 25 MB); generic file previews keep the smaller cap.
- Deleting an entry no longer removes attachments that another entry still
  references. A shared image survives until its last referrer is deleted; a
  solo attachment is still reaped with its only entry.

### Security

- Served `.svg` attachments can no longer execute scripts in the app origin.
  The `/file` route now sends `X-Content-Type-Options: nosniff` on every served
  file and forces `Content-Disposition: attachment` for SVG, so opening an
  attached SVG downloads it instead of running it as a same-origin document with
  access to every EntryBox API. Inline `<img>` preview is unaffected.
- Vendoring the frontend scripts (see Changed) removes the supply-chain exposure
  of loading executable JavaScript — including a floating Alpine version — from a
  third-party CDN into a tool that reads local project files and writes into
  agent config files.

### Removed

- QR code mobile access (the 📱 topbar button and modal). The qrcode CDN build
  it depended on is no longer published, and mobile access will be reapproached.
  The `/api/network` endpoint it used is retained for future local-network
  clients.

---

## [1.5.0] - 2026-06-03

### Added

- Code syntax highlighting in entry bodies. Fenced code blocks are highlighted
  with highlight.js (loaded from CDN, no build step); the fence info-string
  (e.g. ` ```python `) sets the language, otherwise it is auto-detected. Colors
  come from new `--code-*` theme variables that reference each theme's existing
  palette, so highlighting adapts to the active theme and `style.css` keeps its
  zero-hardcoded-color rule.
- Attachments. Screenshots and files can be attached to an entry by pasting,
  drag-and-drop, or a file picker in both the log form and the inline edit form.
  Files are stored in `.entrybox/attachments/` and referenced from the entry
  body as standard markdown (`![name](attachments/…)` for images,
  `[name](attachments/…)` for other files), so the entry stays plain readable
  markdown and an AI agent can open the artifact directly. Image refs render
  inline; deleting an entry reaps its attachments. The attachments directory is
  git-ignored by default (debug context that stays on the machine).
- Undo-after-log. After logging an entry a transient "✓ logged ID · undo"
  control appears for 8 seconds; undo removes the just-created entry and
  restores its title, body, and type to the log form — the fix for accidental
  early submits.
- Sandboxed project file surface: `GET /api/projects/{id}/file` (preview /
  attachment serving), `GET /api/projects/{id}/tree` (directory tree, skipping
  VCS/dependency/dot directories), and `POST /api/projects/{id}/attachments`
  (base64 JSON upload — no new server dependency). All resolve paths through a
  single sandbox (`app/files.py`) that rejects `..`, absolute, drive-qualified,
  and symlink escapes.
- `ENTRYBOX_TOKEN` environment variable. When set, the file/tree/attachment
  routes require a matching `X-EntryBox-Token` header (recommended if you bind
  off-loopback).
- Test suite (`tests/`, stdlib `unittest`, no dependency): 23 cases covering the
  markdown parser (all header formats, the date-only regression, round-trip
  idempotence, edit isolation, duplicate-ID repair) and the path sandbox
  (escape attempts, ignore rules).

### Changed

- `/health` now reports the real application version from a single source
  (`app/__init__.py`) instead of a hardcoded `1.0.0`.
- CORS is locked to loopback and browser-extension origins (was `allow_origins
  ["*"]`). A website you visit can no longer read responses from
  `localhost:3859` — important now that file-read routes exist. Requests with no
  Origin (CLI, Quick Drop, server-to-server) are unaffected.
- All entries-file rewrites are now atomic (temp file + rename); the automatic
  legacy-format migration also snapshots the prior contents to `entries.md.bak`
  first.

### Fixed

- Duplicate entry IDs are detected and repaired on load: when two blocks share
  an ID the earliest keeps the number and later collisions are reassigned fresh
  IDs, so the UI never renders colliding keys and state/delete operations can't
  target the wrong block.
- A non-loopback `ENTRYBOX_BIND` now logs a clear unauthenticated-exposure
  warning at startup.

---

## [1.4.0] - 2026-06-02

### Added

- Entry editing: title, body, and type can now be edited after creation. In the
  UI, a ✎ button appears on each entry card; clicking it opens an inline form
  pre-populated with the current values. Save with the button or Enter (from the
  title field), cancel with Escape. Optimistic update — the card refreshes
  immediately without a full reload.
- `update_entry()` in `app/entries.py`: edits the target block in place while
  leaving all sibling blocks byte-for-byte untouched. ID, timestamp, state, and
  done_at are preserved; only the fields sent in the request are changed.
- `edit` sub-command in the CLI: `python cli/entrybox.py edit --project <id>
  --id PREFIX-NNNN [--title "..."] [--body "..."] [--type fix|improve|...]`.
  Pass any combination of the three content fields; unchanged fields are left as-is.
- PATCH `/api/projects/{id}/entries` now accepts `title`, `body`, and/or `type`
  fields for content edits. State change and content edit can be sent in the same
  request (each runs its own logic). New webhook event: `entry_updated`.

### Fixed

- **Duplicate-ID bug**: entries with a date-only timestamp (`2026-06-01`, no
  `HH:MM`) were silently dropped by all four `_parse_block` regex variants in
  `app/entries.py`. Dropped entries were invisible to `list`, `update-state`,
  and every other operation. Worse, `_next_id` computed `max+1` over only the
  surviving entries, so the dropped entry's number was handed out again to the
  next `add_entry` call, creating a duplicate ID.
  - Fixed by replacing the hardcoded `\d{4}-\d{2}-\d{2} \d{2}:\d{2}` fragment
    with `\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?` in all four parsers (for both
    created-timestamp and done_at), and in the `update_entry_state` state-change
    regex.
  - `add_entry` and the migration path in `load_entries` now derive the next ID
    from a raw `re.findall(PREFIX-\d+)` scan over the whole file, not just the
    parsed entries, so a malformed block can never cause its number to be recycled.
  - `_parse_file` now logs a `WARNING` for each dropped block (file path + first
    line) instead of silently discarding it.
  - The rewrite path (`load_entries` migration) pads any surviving date-only
    stamps to `YYYY-MM-DD 00:00` to prevent re-occurrence on hand-edited files.
  - Root cause: `add_entry` always writes a full `HH:MM` stamp, so API-created
    entries were never affected; only hand-written or externally edited entries
    with abbreviated timestamps hit the bug.

---

## [1.3.0] - 2026-05-28

### Added

- Quick Drop desktop window (`quickdrop.py`, launched via `quickdrop.bat`): a
  compact native window for dropping entries without opening the full UI. Pick a
  project, type a title, hit Enter — the entry is posted to the running EntryBox
  server. Drop several in a row; Esc or the close button shuts the window, and
  re-running the shortcut reopens it. Built with Tkinter (stdlib only, no pip
  deps) so it renders reliably over Remote Desktop — no browser engine, no GPU.
  The last-used project is remembered per machine.
- Server-down handling in Quick Drop: if the EntryBox server isn't reachable,
  the window shows a "Start server" button that launches `run.bat` in a new
  console, polls `/health`, and loads the project list once the server is up.
- `/quick` route and `app/templates/quick.html`: a minimal, dependency-free
  (vanilla JS, no Alpine) browser quick-entry page — project + type selectors,
  title, optional note. Fetches active theme vars on load. `Enter` submits,
  `Ctrl/Cmd+Enter` submits from the note field.

### Changed

- `requirements.txt` unchanged for the desktop app — Quick Drop is stdlib-only.
  The server's dependencies are untouched.

---

## [1.2.0] - 2026-05-23

### Added

- Entry body rich rendering: fenced code blocks (` ``` `) render as `<pre><code>`
  blocks; inline backtick code renders with a pill background; `**text**` renders
  bold; `http(s)://` URLs render in accent blue (non-clickable); filesystem paths
  (`src/foo/`, `./bar`, `/usr/local`, `C:\path`) render in accent blue monospace.
  Implemented as a dependency-free `renderBody()` function in the Alpine component;
  XSS-safe (all text HTML-escaped before injection).
- Copy-body button: a double-rectangle clipboard icon appears on hover in the
  top-right corner of each entry body. Clicking copies the raw body text to the
  clipboard and shows a `✓` checkmark for 1.5 s.
- Collapsible long entries: bodies longer than 5 lines are collapsed by default
  (100 px max-height with a bottom fade mask). A `↓ show more` / `↑ show less`
  toggle appears below each collapsible entry.

---

## [1.1.0] - 2026-05-23

### Added

- Pagination for the entries API: `GET /api/projects/{id}/entries` now accepts
  `?limit=50&offset=0` and returns `total`, `offset`, and `limit` alongside the
  page. Default page size is 50.
- "Load more" button in the UI: the first 50 entries render immediately; older
  entries are fetched on demand with a remaining-count label.

### Changed

- Embed mode init is now faster: logo SVG and agents list are skipped entirely
  (neither is rendered in embed), and the theme and config fetches run in
  parallel instead of sequentially.
- All entry mutations (add, state change, delete) are now optimistic: the UI
  updates instantly and the server write happens in the background. The array
  rolls back automatically if the request fails.
- `update_entry_state` now returns `(entry, old_state)` as a tuple, eliminating
  a redundant `load_entries` call that `patch_entry` previously made to retrieve
  the old state before writing.

### Performance

- Added a per-process mtime cache in `entries.py`: the entries file is parsed
  once and cached in memory keyed by modification time. Repeated reads (health
  poll, embed reload, state changes) hit the cache and skip all file I/O and
  regex work until the file actually changes. At 500 entries this reduces a
  full-parse-per-request to a single parse per write.

### Fixed

- Iframe embed patterns in the README now defer setting `src` until after the
  health check succeeds, preventing the browser from opening a connection to
  `localhost:3859` while the offline state is displayed.

---

## [1.0.0] - 2026-05-22

First public release.

### Added

- FastAPI server on port 3859, bound to `127.0.0.1` by default.
- Markdown-first storage: one `.entrybox/entries.md` per project, human-readable
  and git-friendly.
- 5 entry types: `fix`, `improve`, `docs`, `idea`, `roadmap`.
- 5-state workflow: `logged` → `review` → `wip` → `done`, plus `error`.
  `done` entries are auto-timestamped.
- Multi-project model: one EntryBox instance manages any number of codebases;
  each project's entries travel with the project, not with EntryBox.
- Project registry stored in `data/entrybox.json`.
- AI agent integration: a marker-tracked instruction block written into the
  agent's config file, fully editable and optional before writing.
- Built-in agent library: Claude Code (`CLAUDE.md`), Cursor (`.cursorrules`),
  Windsurf (`.windsurfrules`), GitHub Copilot
  (`.github/copilot-instructions.md`), Aider (`.aider.conf.yml`).
- Learned (custom) agents: point EntryBox at an unknown agent's instruction
  file; it is remembered and offered for all future projects.
- Legacy block adoption: a hand-written EntryBox block with no marker tags is
  detected and replaced in place on registration, never duplicated.
- Per-project and global agent toggles in settings.
- Theme system: all colors and fonts are CSS variables defined in theme JSON;
  `style.css` carries zero color values.
- 4 built-in themes: `default` (light), `dark`, `minimal`, `ocean`. Community
  themes are auto-discovered from `themes/*.json`. Live switching, no reload.
- Boot animation slot: a clearly marked HTML/CSS zone with a CSS placeholder,
  ready to be replaced with custom motion.
- 9-slide first-run onboarding, including an AI-tool selector and an editable
  agent-integration preview. Replayable from settings.
- Iframe embed mode: `?embed=1&project=<id>` renders a single project with no
  chrome.
- Webhooks: POST on entry create and state change, global or per-project URL.
- REST API for entries, projects, agents, themes, and config.
- Dependency-free CLI (`cli/entrybox.py`): `list`, `add`, `update-state`,
  `projects`, `add-project`, `themes`, `set-theme`.
- File locking (`filelock`) around all `entries.md` reads and writes to prevent
  races between the UI and the CLI.
- Docker support (single-project mode) and Python standalone (multi-project).
- One-click start scripts: `run.bat` (Windows) and `run.sh` (macOS/Linux).

---

[1.0.0]: https://github.com/<your-org>/entrybox/releases/tag/v1.0.0
