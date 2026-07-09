<div align="center">

<img src="assets/logo.svg" alt="EntryBox" width="240">

**The idea board that lives in your repo.**

Lightweight idea, feedback, and fix tracking for any project. Markdown-native, multi-project, agent-aware, no SaaS.

[![License: AGPL v3](https://img.shields.io/badge/license-AGPL%20v3-3b9eff?style=flat-square)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3b9eff?style=flat-square)](https://www.python.org/)
[![Local-first](https://img.shields.io/badge/local--first-no%20account-6bcb77?style=flat-square)](#security)
[![Release](https://img.shields.io/badge/release-v1.5.2-6bcb77?style=flat-square)](CHANGELOG.md)
[![Tests](https://github.com/izored/entrybox/actions/workflows/tests.yml/badge.svg)](https://github.com/izored/entrybox/actions/workflows/tests.yml)

</div>

---

<!-- screenshot-main.png pending, see assets/SHOTLIST.md. Uncomment when captured:
<div align="center">
<img src="assets/screenshot-main.png" alt="EntryBox main interface" width="800">
</div>
-->

## Why I built this

My ideas kept dying in chat. Feedback got buried in threads. GitHub Issues felt too formal for a 2am shower thought, Notion wanted an account and a tab, Linear wanted money and a habit.

I just wanted to write the thing down, track it, and have my AI agent know about it.

So EntryBox is a tiny local server. One markdown file per project. A five-state workflow. A UI you understand in three seconds. CLI and REST for your coding agent.

```
logged → review → wip → done
                      ↘ error
```

Everything lives in `.entrybox/entries.md` inside each project: plain text, git-friendly, grep-able, portable as `cp`. No database. No binary format. No account. No telemetry.

> **Not a task manager.** EntryBox doesn't track progress, maintain history, or remember agent conversations. It's a drop box. Capture ideas and problems when they surface, work on them when you're ready.

|  | EntryBox | GitHub Issues | Notion | Linear |
|--|----------|---------------|--------|--------|
| Lives in your repo | ✅ `.entrybox/entries.md` | ❌ on GitHub | ❌ in the cloud | ❌ in the cloud |
| Account required | No | Yes | Yes | Yes |
| Readable by your AI agent as a plain file | ✅ | API only | API only | API only |
| Cost | Free (AGPL) | Free | Freemium | Paid |
| Formality of a 2am idea | One line | A form | A page | A ticket |

---

## Quickstart

EntryBox runs on **port 3859**.

```bash
git clone https://github.com/izored/entrybox.git
cd entrybox
```

**Windows:** double-click `run.bat`
**macOS / Linux:**

```bash
./run.sh
```

The script creates a virtual environment, installs dependencies, and starts the server. Then open **http://localhost:3859**.

Manual start, if you prefer:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 3859
```

### First run

On first launch EntryBox plays a short boot animation, then a 9-slide onboarding. It asks which AI coding agent you use and shows the exact integration block before anything is written. Replay it any time from **Settings → Show intro again**.

### Quick Drop (desktop window)

For dropping entries without opening the full UI, run `quickdrop.bat` (Windows). A small native window opens: pick a project, type a title, hit **Enter**, and it's logged. Drop several in a row. **Esc** or the close button shuts the window. Run the shortcut again to reopen it.

```bash
quickdrop.bat        # opens the Quick Drop window
```

It's a native Tkinter window (stdlib only, no extra dependencies) and talks to the same local server. If the server isn't running, the window shows a **Start server** button that launches `run.bat` for you. Pin `quickdrop.bat` to your taskbar or make a desktop shortcut for one-click access.

Full design, architecture, and rebuild notes: [docs/QUICKDROP.md](docs/QUICKDROP.md).

---

## Features

- **Markdown-first storage.** Entries live in `.entrybox/entries.md` per project. Human-readable, git-friendly, no tooling required.
- **Multi-project.** One EntryBox instance, any number of codebases, switchable from the sidebar.
- **5 entry types, 5 states.** A visual vocabulary that fits on one screen.
- **AI agent integration.** Writes a small, marker-tracked instruction block into your agent's config file (`CLAUDE.md`, `.cursorrules`, `AGENTS.md`, and others). Editable, optional, removable.
- **Skinnable.** Every colour and font is a CSS variable defined in a JSON theme. 4 built-in themes, community themes are a single JSON drop-in.
- **Embeddable.** `?embed=1&project=<id>` renders one project, no chrome, for iframing into another dashboard.
- **REST + CLI.** Drive everything headlessly. Ideal for AI agents.
- **Webhooks.** POST on entry create and state change.
- **Local-first.** Binds to `127.0.0.1` by default. Nothing leaves the machine.

---

## Entry types & states

| Type | Meaning | Colour |
|------|---------|--------|
| `fix` | Something is broken | Red |
| `improve` | Make an existing thing better | Green |
| `docs` | Documentation work | Blue |
| `idea` | A new thought, unscoped | Orange |
| `roadmap` | Larger planned direction | Purple |

| State | Meaning |
|-------|---------|
| `logged` | Just captured, not triaged |
| `review` | Being looked at |
| `wip` | In progress |
| `done` | Complete (auto-timestamped) |
| `error` | Blocked, needs a decision |

---

## Multi-project model

EntryBox itself stores only a registry in `data/entrybox.json` (theme, project list, learned agents, onboarding flags). **Each project's entries live with the project**, not with EntryBox:

```
your-project/
└── .entrybox/
    └── entries.md      ← travels with the repo, commit it or .gitignore it
```

Registering a project creates the `.entrybox/` folder, creates (or migrates into) `entries.md`, and, if you allow it, writes the agent integration block. A confirmation modal shows every file EntryBox will touch before it touches it.

---

## AI agent integration

EntryBox writes a small instruction block into your agent's config file so the agent knows the API address, the project prefix, and how to update states.

The block is wrapped in **markers** so EntryBox can find, update, or remove it cleanly later:

```markdown
<!-- EntryBox -->
## EntryBox

Entries live in `.entrybox/entries.md` (plain markdown, read it directly).
Project: My Project | Prefix: MY | Server: http://localhost:3859

When the user references an entry, the block tells the agent to find it,
set the state to `review`, think through scope, summarise it back and ask
for a go-ahead, then set `wip` and do the work. `done` on finish, or
`error` with an explanation if blocked.
...
<!-- /EntryBox -->
```

The block is **fully editable** before it is written (what you edit is what gets written, as long as the markers stay intact), and writing it is **optional** (choose "Copy, I'll paste manually"). If you hand-write the block yourself without markers, EntryBox detects it on registration and adopts it in place. It never appends a duplicate.

### Your config files stay yours

Files like `CLAUDE.md` get edited by you *and* by your agents. EntryBox plans for that: the managed block is only replaced when its marker pair is intact. If markers ever end up orphaned, duplicated, or out of order, EntryBox refuses to touch the file, tells you why, and leaves your content byte-for-byte as it was. Every rewrite keeps your file's line endings and drops a `<file>.bak` snapshot first. Files that aren't valid UTF-8 are never rewritten.

### Built-in agents

| Agent | Config file | Marker style |
|-------|-------------|--------------|
| Claude Code | `CLAUDE.md` | `<!-- EntryBox -->` |
| Cursor | `.cursorrules` | `# EntryBox` |
| Windsurf | `.windsurfrules` | `# EntryBox` |
| GitHub Copilot | `.github/copilot-instructions.md` | `<!-- EntryBox -->` |
| Aider | `.aider.conf.yml` | `# EntryBox` |
| AGENTS.md standard (Codex, Kimi, Amp, Jules, Zed…) | `AGENTS.md` | `<!-- EntryBox -->` |
| Gemini CLI | `GEMINI.md` | `<!-- EntryBox -->` |

### Custom or unknown agents

Use an agent EntryBox doesn't know? Point it at your instruction file in **Settings → Add custom agent**. EntryBox suggests a marker template from the file extension, learns the agent, and offers it for every future project.

---

## Theming

`style.css` is structural only, with **zero colour values**. Every colour and font is a CSS custom property defined in a theme JSON file under `themes/`.

Built-in themes: `default` (light), `dark`, `minimal`, `ocean`. Switch live from the top bar, no reload.

A theme is one file:

```json
{
  "name": "ocean",
  "author": "community",
  "vars": {
    "--bg": "#0f1e2e",
    "--surface": "#1a2f42",
    "--text": "#d0e8f5",
    "--accent": "#3b9eff",
    "--type-fix": "#ff6b6b",
    "--state-done": "#6bcb77"
  }
}
```

Drop a `themes/mytheme.json` in and it is auto-discovered on next load. To share one, open a PR or tag your gist `entrybox-theme` on GitHub. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## REST API

Base URL: `http://localhost:3859`. All bodies are JSON.

### Entries

| Method | Endpoint | Body | Purpose |
|--------|----------|------|---------|
| `GET` | `/api/projects/{id}/entries` | none | List entries |
| `POST` | `/api/projects/{id}/entries` | `{title, type?, body?, priority?, due?, recur?}` | Create an entry |
| `PATCH` | `/api/projects/{id}/entries` | `{id, state?, title?, body?, type?, priority?, due?, recur?}` | Update state and/or content |
| `DELETE` | `/api/projects/{id}/entries` | `{id}` | Delete an entry |

Optional entry fields:

| Field | Values | Behaviour |
|-------|--------|-----------|
| `priority` | `A` `B` `C` | A = high urgency, C = low |
| `due` | `YYYY-MM-DD` | Due date; urgency-coloured in the UI |
| `recur` | `daily` `weekly` `monthly` `yearly` | When marked `done`, a fresh entry is auto-created with the next due date |

Pass an empty string to clear a field (`"priority": ""`).

```bash
# Log an entry with priority and due date
curl -X POST http://localhost:3859/api/projects/myproject/entries \
  -H 'Content-Type: application/json' \
  -d '{"title": "Ship the release", "type": "roadmap", "priority": "A", "due": "2026-06-10"}'

# Log a recurring weekly entry
curl -X POST http://localhost:3859/api/projects/myproject/entries \
  -H 'Content-Type: application/json' \
  -d '{"title": "Review deps", "type": "improve", "recur": "weekly", "due": "2026-06-07"}'

# Mark it done (auto-creates the next recurrence)
curl -X PATCH http://localhost:3859/api/projects/myproject/entries \
  -H 'Content-Type: application/json' \
  -d '{"id": "MY-0001", "state": "done"}'

# Set priority and due on an existing entry
curl -X PATCH http://localhost:3859/api/projects/myproject/entries \
  -H 'Content-Type: application/json' \
  -d '{"id": "MY-0002", "priority": "B", "due": "2026-06-15"}'
```

### Projects

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/projects` | List registered projects |
| `POST` | `/api/projects` | Register a project |
| `GET` | `/api/projects/{id}` | One project |
| `DELETE` | `/api/projects/{id}` | Unregister (optionally strip annotations) |
| `GET` | `/api/projects/{id}/scan-agents` | Detect agent config files in a registered project |
| `POST` | `/api/projects/scan-dir` | Detect agent config files in any directory |
| `POST` | `/api/projects/{id}/agents` | Set the project's active agents |
| `POST` | `/api/projects/{id}/preview-annotation` | Render the annotation block for an agent |

### Agents, themes, config

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/agents` | List built-in and learned agents |
| `POST` | `/api/agents` | Add a learned agent |
| `POST` | `/api/agents/preview` | Preview the annotation block for any agent (no project needed) |
| `DELETE` | `/api/agents/{id}` | Remove a learned agent |
| `GET` | `/api/themes` | List themes and active id |
| `GET` | `/api/themes/active` | Active theme and vars |
| `POST` | `/api/themes/active` | Set active theme `{id}` |
| `GET` | `/api/themes/{id}` | One theme and vars |
| `GET` | `/api/config` | App config (booted, onboarded, theme, and more) |
| `PATCH` | `/api/config` | Update app config |
| `GET` | `/api/network` | LAN IP addresses and port (for local-network clients) |

### Webhooks

Set `ENTRYBOX_WEBHOOK_URL` (or a per-project `webhook_url`). EntryBox POSTs on entry create and state change:

```json
{
  "event": "state_changed",
  "project": "myproject",
  "old_state": "wip",
  "entry": { "id": "MY-0001", "state": "done", "...": "..." }
}
```

---

## CLI

`cli/entrybox.py` is pure standard library, no dependencies. It talks to a running EntryBox server.

```bash
# Global flags: --host (default http://localhost:3859), --project / -p

python cli/entrybox.py projects                       # list projects
python cli/entrybox.py -p myproject list              # list entries
python cli/entrybox.py -p myproject add "New idea" --type idea --body "details"
python cli/entrybox.py -p myproject update-state --id MY-0001 --state done
python cli/entrybox.py themes                         # list themes
python cli/entrybox.py set-theme ocean                # switch theme

# Register a project from the terminal (shows a confirmation prompt)
python cli/entrybox.py add-project \
  --name "My Project" --root-dir /path/to/project --prefix MY \
  --agents claude-code,cursor
```

`add-project` flags: `--id`, `--color`, `--migrate-from <entries.md>`, `--skip-agent-config`, `--yes/-y` (skip the confirmation prompt).

---

## Embed mode

EntryBox can be embedded as a single-project panel inside any local app or dashboard: no sidebar, no chrome, just the entry form and cards for one project.

### URL structure

```
http://localhost:3859/?embed=1&project=<project-id>
```

| Param | Required | Description |
|-------|----------|-------------|
| `embed` | yes | Hides topbar and sidebar |
| `project` | yes | Project ID, the slug you set at registration (e.g. `my-app`, `izo`) |

The **project ID is the isolation slug.** Each registered project has its own URL; two projects never share a view. Find yours in the EntryBox sidebar, or via `GET /api/projects`.

### Minimal iframe

```html
<iframe
  src="http://localhost:3859/?embed=1&project=my-project"
  style="width:100%;height:100%;border:none;"
  title="EntryBox">
</iframe>
```

### Recommended: health-aware wrapper

If EntryBox is not running when the parent app loads, a raw `<iframe>` shows a browser connection-refused error. Wrap it with a health check instead so users see a clear offline state with the launch command.

**Health endpoint:**

```
GET http://localhost:3859/health
→ 200  { "status": "ok", "version": "1.5.2" }
```

**Alpine.js pattern** (drop into any Alpine component):

```html
<div x-data="entryBoxEmbed()" x-init="check()"
     style="height:100%;position:relative">

  <!-- offline -->
  <div x-show="status==='offline'"
       style="display:flex;flex-direction:column;align-items:center;
              justify-content:center;height:100%;gap:16px;text-align:center">
    <strong>EntryBox server is not running</strong>
    <code>python -m uvicorn app.main:app --host 127.0.0.1 --port 3859 --reload</code>
    <button @click="check()">↻ Retry</button>
  </div>

  <!-- checking -->
  <div x-show="status==='checking'"
       style="display:flex;align-items:center;justify-content:center;height:100%">
    Connecting to EntryBox…
  </div>

  <!-- online: src set only after health check to avoid wasted load -->
  <iframe x-show="status==='online'"
          :src="status==='online' ? 'http://localhost:3859/?embed=1&project=my-project' : ''"
          style="width:100%;height:100%;border:none;display:block"
          title="EntryBox">
  </iframe>
</div>

<script>
function entryBoxEmbed() {
  return {
    status: 'checking',
    async check() {
      this.status = 'checking'
      try {
        const ctrl = new AbortController()
        setTimeout(() => ctrl.abort(), 2000)
        await fetch('http://localhost:3859/health', { signal: ctrl.signal })
        this.status = 'online'
      } catch {
        this.status = 'offline'
      }
    }
  }
}
</script>
```

**Vanilla JS pattern** (no framework):

```html
<div id="eb-wrapper" style="height:100%;position:relative">
  <div id="eb-offline" style="display:none;flex-direction:column;
       align-items:center;justify-content:center;height:100%;gap:16px">
    <strong>EntryBox server is not running</strong>
    <code>python -m uvicorn app.main:app --host 127.0.0.1 --port 3859 --reload</code>
    <button onclick="checkEntryBox()">↻ Retry</button>
  </div>
  <!-- src left blank until health check passes to avoid wasted load -->
  <iframe id="eb-frame"
          style="width:100%;height:100%;border:none;display:none"
          title="EntryBox">
  </iframe>
</div>

<script>
async function checkEntryBox() {
  document.getElementById('eb-offline').style.display = 'none'
  document.getElementById('eb-frame').style.display = 'none'
  try {
    const ctrl = new AbortController()
    setTimeout(() => ctrl.abort(), 2000)
    await fetch('http://localhost:3859/health', { signal: ctrl.signal })
    document.getElementById('eb-frame').src = 'http://localhost:3859/?embed=1&project=my-project'
    document.getElementById('eb-frame').style.display = 'block'
  } catch {
    document.getElementById('eb-offline').style.display = 'flex'
  }
}
checkEntryBox()
</script>
```

### Notes

- EntryBox binds to `127.0.0.1`. Embed works when both apps run on the same machine and the browser accesses them via `localhost`.
- **Loading HTML in an `<iframe>` has no CORS restriction.** The iframe itself works without any CORS config.
- **JavaScript `fetch()` from a host app to `localhost:3859` IS cross-origin** (different port). EntryBox allows cross-origin reads only from `localhost` / `127.0.0.1` origins (any port) and browser extensions. A host app served from localhost works out of the box; arbitrary websites cannot read your entries. If your host page is not on a localhost origin, use the iframe (not subject to CORS) or a zero-read health check with `mode: 'no-cors'`: the fetch rejects only on connection refused (server down), resolves on any HTTP response (server up).
- Updates to EntryBox (new features, theme changes) propagate automatically to every embed. The iframe always fetches the latest HTML from the running server. No changes needed in host apps.

---

## Configuration

Copy `.env.example` to `.env` and adjust:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ENTRYBOX_BIND` | `127.0.0.1` | Server bind address (keep local) |
| `ENTRYBOX_PORT` | `3859` | Server port |
| `ENTRYBOX_DATA_DIR` | `./data` | Where `entrybox.json` is stored |
| `ENTRYBOX_WEBHOOK_URL` | _(unset)_ | Global webhook endpoint |
| `ENTRYBOX_MAX_UPLOAD_MB` | `25` | Max attachment size (MB), upload + serving |
| `ENTRYBOX_TOKEN` | _(unset)_ | Shared secret; gates file/tree/attachment routes via `X-EntryBox-Token` |

---

## Security

EntryBox has **no authentication**. It is designed to run on `localhost` for a single user.

- It binds to `127.0.0.1` by default, reachable only from your own machine.
- Document and entry content stays on the machine. No telemetry, no cloud.
- **Do not** change `ENTRYBOX_BIND` to `0.0.0.0` or expose port 3859 on a LAN or the internet without putting a reverse proxy with authentication in front of it. Anyone who can reach the port can read and edit every entry.

Found a vulnerability? See [SECURITY.md](SECURITY.md).

---

## Roadmap

v1.0 shipped the full core described above. Next: a file-tree UI, a search / filter bar, a Chrome extension, richer webhooks, and a community themes gallery. See the **Unreleased / Planned** section of [CHANGELOG.md](CHANGELOG.md) for the live queue.

---

## Built with AI

I built EntryBox alongside AI coding agents, mostly Claude Code. That is not a footnote, it is the point: EntryBox exists because tracking ideas next to the code, where the agent can see them, is a workflow worth having. I keep the codebase small and readable on purpose so anyone can audit it.

---

## Contributing

Themes, agent definitions, bug fixes, and features are all welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Support

EntryBox is free and AGPL-licensed. If it saves you time and you want to help it keep going:

<!-- TODO: donation method not finalized yet. Replace with the real link
     (GitHub Sponsors / Ko-fi / etc.) once chosen. -->

- Star the repo. It genuinely helps.
- Share a theme, file a bug, or send a PR.
- Follow along at **[dev.izo.red](https://dev.izo.red)**.
- A donation link is coming. Until then, a kind word to **dev@izo.red** works.

---

## License

[GNU AGPL-3.0](LICENSE). You may use, modify, and redistribute EntryBox freely. If you run a modified version as a network service, you must make your modified source available to its users.

---

## Credits

Built by **Reda Izo** under **DIR (dev.izo.red)**, the developer identity behind the creative studio izo.red. Born from a growing obsession with building software alongside AI coding agents.

Contact: **dev@izo.red**
