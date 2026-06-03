# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the server

```bash
# Windows
run.bat

# macOS / Linux
./run.sh

# Manual
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 3859 --reload
```

Server binds to `http://localhost:3859` by default. The `--reload` flag is for development only.

## Environment

Copy `.env.example` to `.env`. Key vars:

| Var | Default | Purpose |
|-----|---------|---------|
| `ENTRYBOX_BIND` | `127.0.0.1` | Bind address |
| `ENTRYBOX_PORT` | `3859` | Port |
| `ENTRYBOX_DATA_DIR` | `./data` | Where `entrybox.json` lives |
| `ENTRYBOX_THEME` | `dark` | Active theme ID |
| `ENTRYBOX_WEBHOOK_URL` | _(none)_ | Global webhook for state-change events |

## Architecture

EntryBox is a local-only FastAPI SPA. No database — all state lives in flat files.

### Data model

**Global state** (`data/entrybox.json`): theme, onboarding flags, registered projects list, learned agents list. Read/written by `app/config.py`.

**Per-project entries** (`.entrybox/entries.md` inside each registered project root): plain markdown, one `## ID · timestamp · type · state — title` heading per entry, followed by optional body. Parsed/written by `app/entries.py` using regex — no markdown library. File uses `filelock` for concurrent write safety.

Entry IDs are `PREFIX-NNNN` (zero-padded). On load, old-format entries (no ID / no state field) are auto-migrated in place.

### State machine

```
logged → review → wip → done
                      ↘ error
```

Valid types: `fix`, `improve`, `docs`, `idea`, `roadmap`  
Valid states: `logged`, `review`, `wip`, `done`, `error`

### Module layout

```
app/
  config.py     — env vars, entrybox.json read/write
  entries.py    — markdown parse/write for entries files
  projects.py   — project CRUD; calls agents.py on register/unregister
  agents.py     — built-in + learned agent registry; annotation read/write
  theme.py      — theme load; vars injected into UI at runtime
  main.py       — FastAPI app; mounts routes + static; /quick route; SPA fallback
  routes/       — one router per resource (entries, projects, agents, themes, config)
  templates/    — index.html (Alpine.js SPA), quick.html (vanilla-JS quick-entry page)
  static/       — style.css
themes/         — *.json theme files (name, author, vars dict of CSS custom props)
cli/            — entrybox.py (stdlib-only CLI; talks to the REST API)
quickdrop.py    — native Tkinter quick-entry window (stdlib only); posts to the REST API
quickdrop.bat   — launcher: runs quickdrop.py via pythonw (uses .venv python if present)
docs/QUICKDROP.md — Quick Drop design, architecture, attempt history & rebuild notes
assets/         — logo.svg
```

### Agent annotation system

When a project is registered with one or more agents, `agents.py` writes a block into that agent's config file (e.g. `CLAUDE.md`, `.cursorrules`). The block is delimited by 
` (markdown) or `# EntryBox` / `# /EntryBox` (comment style).

`annotation_status()` returns `"none"`, `"marked"` (managed block present), or `"legacy"` (hand-written EntryBox block without markers). `write_annotation()` handles all three cases without producing duplicates.

Built-in agents: `claude-code`, `cursor`, `windsurf`, `copilot`, `aider`. Custom agents can be added via the UI or API and are persisted in `entrybox.json` as `learned_agents`.

```markdown
<!-- EntryBox -->
## EntryBox

This project tracks ideas, fixes, and feedback in EntryBox.
Entries live in `.entrybox/entries.md` (plain markdown, read it directly).
Project: EntryBox | Prefix: EBX | Server: http://localhost:3859

### When the user references an entry

If the user says "check EntryBox EBX-0039", "look at entry 39", or
"let's work on the entrybox idea about X":

1. Find it. Read `.entrybox/entries.md` and match the ID. A bare
   number like "39" means `EBX-0039` (zero-padded, with the prefix).
2. Set the state to `review` so the user sees you picked it up.
3. Read the title and body. Think through scope and approach.
4. Surface it back: a short summary of the entry and your proposed
   approach, then ask for a go-ahead. Do not start work yet.
5. Once the user confirms, set `wip` and do the work.
6. Set `done` when finished. If blocked, set `error` and say what
   blocks it.

### Setting state

CLI: python <entrybox>/cli/entrybox.py update-state --project ebx --id EBX-0039 --state wip
API: PATCH http://localhost:3859/api/projects/ebx/entries  {"id": "EBX-0039", "state": "wip"}

States: logged, review, wip, done, error.
<!-- /EntryBox -->
```



### Frontend

Single Alpine.js component (`entrybox()`) in `index.html`. Theme CSS vars are fetched from `/api/themes/active` on boot and injected into `<style id="eb-theme">`. No build step — the HTML file is served directly.

### Webhook

On `entry_created` and `state_changed` events, a POST is fired to the project-level `webhook_url` or the global `ENTRYBOX_WEBHOOK_URL`. Failures are silently swallowed.

## CLI usage

```bash
python cli/entrybox.py --project <id> list
python cli/entrybox.py --project <id> add "My idea" --type idea
python cli/entrybox.py --project <id> update-state --id PREFIX-0001 --state done
python cli/entrybox.py projects
python cli/entrybox.py add-project --name "My App" --root-dir /path/to/app --prefix APP --agents claude-code
```

The CLI is stdlib-only (`urllib`, `argparse`, `json`) — no pip install needed.

## Custom themes

Add a JSON file to `themes/` with this shape:

```json
{
  "name": "My Theme",
  "author": "You",
  "vars": {
    "--bg": "#...",
    "--surface": "#...",
    "...": "..."
  }
}
```

The filename (without `.json`) becomes the theme ID.
