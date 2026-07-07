import re
from pathlib import Path
from app.config import get_state, update_state

BUILT_IN_AGENTS = [
    {
        "id": "claude-code",
        "name": "Claude Code",
        "config_file": "CLAUDE.md",
        "start_marker": "<!-- EntryBox -->",
        "end_marker": "<!-- /EntryBox -->",
        "template": "markdown",
        "built_in": True,
    },
    {
        "id": "cursor",
        "name": "Cursor",
        "config_file": ".cursorrules",
        "start_marker": "# EntryBox",
        "end_marker": "# /EntryBox",
        "template": "comment",
        "built_in": True,
    },
    {
        "id": "windsurf",
        "name": "Windsurf",
        "config_file": ".windsurfrules",
        "start_marker": "# EntryBox",
        "end_marker": "# /EntryBox",
        "template": "comment",
        "built_in": True,
    },
    {
        "id": "copilot",
        "name": "GitHub Copilot",
        "config_file": ".github/copilot-instructions.md",
        "start_marker": "<!-- EntryBox -->",
        "end_marker": "<!-- /EntryBox -->",
        "template": "markdown",
        "built_in": True,
    },
    {
        "id": "aider",
        "name": "Aider",
        "config_file": ".aider.conf.yml",
        "start_marker": "# EntryBox",
        "end_marker": "# /EntryBox",
        "template": "comment",
        "built_in": True,
    },
]


def get_all_agents() -> list[dict]:
    state = get_state()
    learned = state.get("learned_agents", [])
    return BUILT_IN_AGENTS + [dict(a, built_in=False) for a in learned]


def get_agent(agent_id: str) -> dict | None:
    return next((a for a in get_all_agents() if a["id"] == agent_id), None)


def add_learned_agent(name: str, config_file: str, template: str = "markdown") -> dict:
    import uuid
    agent_id = f"custom-{uuid.uuid4().hex[:8]}"
    if template == "comment":
        start_marker = "# EntryBox"
        end_marker = "# /EntryBox"
    else:
        start_marker = "<!-- EntryBox -->"
        end_marker = "<!-- /EntryBox -->"
    agent = {
        "id": agent_id,
        "name": name,
        "config_file": config_file,
        "start_marker": start_marker,
        "end_marker": end_marker,
        "template": template,
        "used_in_projects": [],
    }
    state = get_state()
    learned = state.get("learned_agents", [])
    learned.append(agent)
    update_state({"learned_agents": learned})
    return agent


def remove_learned_agent(agent_id: str) -> bool:
    state = get_state()
    learned = state.get("learned_agents", [])
    new_learned = [a for a in learned if a["id"] != agent_id]
    if len(new_learned) == len(learned):
        return False
    update_state({"learned_agents": new_learned})
    return True


def detect_agents_in_project(root_dir: Path) -> list[str]:
    found = []
    for agent in get_all_agents():
        cfg_path = root_dir / agent["config_file"]
        if cfg_path.exists():
            found.append(agent["id"])
    return found


def build_annotation(agent: dict, project: dict, host: str = "localhost", port: int = 3859) -> str:
    """The instruction block written into an agent's config file.

    It is a playbook, not just an API reference: it tells the agent how to
    behave when the user mentions an entry in plain language."""
    pid = project["id"]
    prefix = project["prefix"]
    name = project["name"]
    url = f"http://{host}:{port}"
    sm, em = agent["start_marker"], agent["end_marker"]
    eid = f"{prefix}-0039"
    cli = f"python <entrybox>/cli/entrybox.py update-state --project {pid} --id {eid} --state wip"

    if agent["template"] == "markdown":
        return (
            f"{sm}\n"
            f"## EntryBox\n\n"
            f"This project tracks ideas, fixes, and feedback in EntryBox.\n"
            f"Entries live in `.entrybox/entries.md` (plain markdown, read it directly).\n"
            f"Project: {name} | Prefix: {prefix} | Server: {url}\n\n"
            f"### When the user references an entry\n\n"
            f'If the user says "check EntryBox {eid}", "look at entry 39", or\n'
            f'"let\'s work on the entrybox idea about X":\n\n'
            f"1. Find it. Read `.entrybox/entries.md` and match the ID. A bare\n"
            f'   number like "39" means `{eid}` (zero-padded, with the prefix).\n'
            f"2. Set the state to `review` so the user sees you picked it up.\n"
            f"3. Read the title and body. Think through scope and approach.\n"
            f"4. Surface it back: a short summary of the entry and your proposed\n"
            f"   approach, then ask for a go-ahead. Do not start work yet.\n"
            f"5. Once the user confirms, set `wip` and do the work.\n"
            f"6. Set `done` when finished. If blocked, set `error` and say what\n"
            f"   blocks it.\n\n"
            f"### Setting state\n\n"
            f"CLI: {cli}\n"
            f'API: PATCH {url}/api/projects/{pid}/entries  {{"id": "{eid}", "state": "wip"}}\n\n'
            f"States: logged, review, wip, done, error.\n\n"
            f"### Optional entry fields\n\n"
            f"Entries can carry priority, due date, and recurrence. Read them from\n"
            f"`.entrybox/entries.md` — they appear in the header line as\n"
            f"`· pri:A · due:2026-06-15 · recur:weekly`.\n\n"
            f"| Field | Values | Meaning |\n"
            f"|-------|--------|---------|\n"
            f"| `priority` | A, B, C | A = urgent, C = low |\n"
            f"| `due` | YYYY-MM-DD | Due date |\n"
            f"| `recur` | daily / weekly / monthly / yearly | Auto-relogs on done |\n\n"
            f"Set or clear via API (pass `\"\"` to clear):\n"
            f'API: PATCH {url}/api/projects/{pid}/entries  {{"id": "{eid}", "priority": "A", "due": "2026-06-15"}}\n\n'
            f"When the user says things like \"mark this high priority\", \"set due date to\n"
            f"Friday\", or \"make this repeat weekly\" — update the relevant field.\n"
            f"When creating an entry you can include these fields in the POST body.\n"
            f"When a recurring entry is marked done, EntryBox auto-creates the next\n"
            f"occurrence — you don't need to do anything extra.\n"
            f"{em}\n"
        )
    else:
        return (
            f"{sm}\n"
            f"# Tracks ideas, fixes, feedback. Entries: .entrybox/entries.md (read directly).\n"
            f"# Project: {name} | Prefix: {prefix} | Server: {url}\n"
            f"#\n"
            f'# When the user references an entry (e.g. "check EntryBox {eid}"):\n'
            f'#  1. Find it in .entrybox/entries.md. "39" means {eid}.\n'
            f"#  2. Set state `review` so the user sees you picked it up.\n"
            f"#  3. Read it. Think through the approach.\n"
            f"#  4. Summarise it to the user and ask for a go-ahead. Do not start yet.\n"
            f"#  5. On confirmation set `wip`, do the work.\n"
            f"#  6. Set `done` when finished, or `error` if blocked.\n"
            f"# Set state: {cli}\n"
            f"#\n"
            f"# Optional fields: priority (A/B/C), due (YYYY-MM-DD), recur (daily/weekly/monthly/yearly).\n"
            f"# Read from header: ## ID · ts · type · state · pri:A · due:2026-06-15 · recur:weekly — title\n"
            f'# Set: PATCH {url}/api/projects/{pid}/entries  {{"id": "ID", "priority": "A", "due": "2026-06-15"}}\n'
            f"# If user says 'high priority' / 'due Friday' / 'repeat weekly' — update the field.\n"
            f"# Recurring entries auto-resubmit when marked done.\n"
            f"{em}\n"
        )


def _legacy_block_pattern(agent: dict) -> re.Pattern:
    """Matches a hand-written EntryBox block that has NO marker tags.

    Used to adopt instructions a user (or a past EntryBox version) wrote
    manually, so re-registering never appends a duplicate.
    """
    if agent.get("template") == "markdown":
        # Heading up to the next markdown heading or end of file.
        return re.compile(
            r"\n*#{2,} EntryBox Integration\b.*?(?=\n#{1,6} |\Z)", re.DOTALL
        )
    # Comment style: heading + contiguous comment lines (stops at blank/non-#).
    return re.compile(r"\n*#+ EntryBox Integration\b(?:\n#[^\n]*)*")


def annotation_status(agent: dict, config_file: Path) -> str:
    """Returns 'none', 'marked' (managed block present) or 'legacy'
    (EntryBox instructions present but with no marker tags)."""
    if not config_file.exists():
        return "none"
    text = config_file.read_text(encoding="utf-8", errors="replace")
    if agent["start_marker"] in text and agent["end_marker"] in text:
        return "marked"
    if _legacy_block_pattern(agent).search(text):
        return "legacy"
    return "none"


def write_annotation(agent: dict, project: dict, config_file: Path, annotation: str) -> None:
    sm = agent["start_marker"]
    em = agent["end_marker"]

    if not config_file.exists():
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(annotation, encoding="utf-8")
        return

    text = config_file.read_text(encoding="utf-8", errors="replace")

    if sm in text and em in text:
        # Re-register / re-assign: replace the managed block in place.
        pattern = re.compile(rf"{re.escape(sm)}.*?{re.escape(em)}\n?", re.DOTALL)
        new_text = pattern.sub(lambda _m: annotation, text, count=1)
    else:
        legacy = _legacy_block_pattern(agent).search(text)
        if legacy:
            # Adopt a hand-written block: replace it with a marked one.
            before = text[: legacy.start()].rstrip("\n")
            after = text[legacy.end():].lstrip("\n")
            parts = [p for p in (before, annotation.rstrip("\n"), after) if p]
            new_text = "\n\n".join(parts) + "\n"
        else:
            new_text = text.rstrip("\n") + "\n\n" + annotation

    config_file.write_text(new_text, encoding="utf-8")


def remove_annotation(agent: dict, config_file: Path) -> bool:
    if not config_file.exists():
        return False
    sm = agent["start_marker"]
    em = agent["end_marker"]
    text = config_file.read_text(encoding="utf-8", errors="replace")

    if sm in text and em in text:
        pattern = re.compile(rf"\n?{re.escape(sm)}.*?{re.escape(em)}\n?", re.DOTALL)
        new_text = pattern.sub("", text)
    else:
        # No markers: fall back to removing a hand-written block if present.
        new_text, n = _legacy_block_pattern(agent).subn("", text)
        if n == 0:
            return False

    config_file.write_text(new_text.rstrip("\n") + "\n", encoding="utf-8")
    return True
