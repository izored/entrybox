# Contributing to EntryBox

Thanks for considering a contribution. EntryBox is small on purpose, and the
goal is to keep it that way. Themes, agent definitions, bug fixes, and focused
features are all welcome.

By contributing you agree your work is licensed under the project's
[AGPL-3.0](LICENSE).

---

## Development setup

EntryBox needs Python 3.10 or newer.

```bash
git clone https://github.com/izored/EntryBox.git
cd entrybox
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 3859 --reload
```

`--reload` restarts the server on file changes. Open http://localhost:3859.

There is **no automated test suite**. Verify changes against the running server:
exercise the affected flow in the browser, check the browser console and the
server log, and confirm `data/entrybox.json` and any `.entrybox/entries.md` are
still valid.

---

## Submitting a theme

A theme is a single JSON file. The fastest contribution there is.

1. Copy an existing file from `themes/` (e.g. `themes/ocean.json`).
2. Change `name`, set `author`, and adjust the values under `vars`. Every key
   that exists in the built-in themes should be present.
3. Save it as `themes/<your-theme>.json`. It is auto-discovered on next load.
4. Switch to it in the top bar and confirm every entry type and state is
   legible, in both compact and expanded entries.
5. Open a PR with a screenshot.

Prefer not to open a PR? Publish the JSON as a gist or repo and tag it
`entrybox-theme` on GitHub so others can find it.

---

## Adding a built-in agent

Built-in agents live in `BUILT_IN_AGENTS` in `app/agents.py`. Each entry needs:

```python
{
    "id": "my-agent",
    "name": "My Agent",
    "config_file": "path/relative/to/project/root",
    "start_marker": "<!-- EntryBox -->",   # or "# EntryBox" for comment files
    "end_marker": "<!-- /EntryBox -->",    # or "# /EntryBox"
    "template": "markdown",                 # or "comment"
    "built_in": True,
}
```

Use the `markdown` template for Markdown config files and `comment` for files
where every line is a `#` comment. Add the agent to the table in `README.md`
and to `CHANGELOG.md` in the same PR.

---

## Code changes

- Keep it minimal. EntryBox favors a small, readable codebase over features.
- Match the existing style. No new dependencies without a clear reason. The
  runtime set is intentionally tiny.
- One logical change per PR.
- Describe what you changed, why, and how you verified it. Screenshots help for
  any UI change.

---

## Reporting bugs and requesting features

Use the issue templates. For bugs, include your OS, Python version, and the
relevant browser-console and server-log output. For security issues, do **not**
open a public issue. See [SECURITY.md](SECURITY.md).

---

## Questions

Open a discussion, or reach **dev@izo.red**.
