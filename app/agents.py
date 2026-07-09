import logging
import re
from pathlib import Path
from app.config import PORT, get_state, update_state

logger = logging.getLogger("entrybox")

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
    {
        # The emerging cross-vendor standard: OpenAI Codex, Kimi, Amp, Jules,
        # Zed, Factory and others all read AGENTS.md.
        "id": "agents-md",
        "name": "AGENTS.md (Codex, Kimi & others)",
        "config_file": "AGENTS.md",
        "start_marker": "<!-- EntryBox -->",
        "end_marker": "<!-- /EntryBox -->",
        "template": "markdown",
        "built_in": True,
    },
    {
        "id": "gemini-cli",
        "name": "Gemini CLI",
        "config_file": "GEMINI.md",
        "start_marker": "<!-- EntryBox -->",
        "end_marker": "<!-- /EntryBox -->",
        "template": "markdown",
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


def build_annotation(agent: dict, project: dict, host: str = "localhost", port: int | None = None) -> str:
    """The instruction block written into an agent's config file.

    It is a playbook, not just an API reference: it tells the agent how to
    behave when the user mentions an entry in plain language."""
    pid = project["id"]
    prefix = project["prefix"]
    name = project["name"]
    url = f"http://{host}:{port or PORT}"
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


# ── Managed-block plumbing ────────────────────────────────────────────────────
# The config files this module writes into (CLAUDE.md, .cursorrules, …) are
# living files, edited by the user AND by the agents themselves. Marker
# integrity can never be assumed. The rule everything below follows:
#
#   Exactly one well-formed marker pair  → replace the block in place.
#   No markers                           → adopt a legacy block, or append.
#   Anything else (orphan / reversed /
#   duplicated markers, undecodable)     → touch NOTHING, report it.


def _marker_line_re(marker: str) -> re.Pattern:
    # Line-anchored: "# EntryBox" must not match inside "# EntryBox rules".
    return re.compile(rf"^[ \t]*{re.escape(marker)}[ \t]*$", re.MULTILINE)


def marker_state(agent: dict, text: str) -> str:
    """'ok' (exactly one well-ordered pair), 'none', or 'broken'."""
    sms = list(_marker_line_re(agent["start_marker"]).finditer(text))
    ems = list(_marker_line_re(agent["end_marker"]).finditer(text))
    if not sms and not ems:
        return "none"
    if len(sms) == 1 and len(ems) == 1 and sms[0].start() < ems[0].start():
        return "ok"
    return "broken"


def _block_span(agent: dict, text: str) -> tuple[int, int]:
    """Span of the managed block (marker_state must be 'ok'). End includes the
    trailing newline of the end-marker line when present."""
    sm = _marker_line_re(agent["start_marker"]).search(text)
    em = _marker_line_re(agent["end_marker"]).search(text)
    end = em.end()
    if text[end:end + 1] == "\n":
        end += 1
    return sm.start(), end


def _find_legacy_span(agent: dict, text: str) -> tuple[int, int] | None:
    """Span of a hand-written, marker-less EntryBox block, or None.

    Markdown: a heading line that is exactly 'EntryBox' or starts with
    'EntryBox Integration', ending at the next heading of the SAME OR HIGHER
    level (standard section semantics — an inner '###' no longer truncates
    the match and leaves fragments behind).
    Comment style: the heading line plus contiguous '#' comment lines.
    """
    head = r"EntryBox(?: Integration\b[^\n]*)?"
    if agent.get("template") == "markdown":
        m = re.search(rf"^(#{{1,6}}) {head}[ \t]*$", text, re.MULTILINE)
        if not m:
            return None
        level = len(m.group(1))
        nxt = re.compile(rf"^#{{1,{level}}} ", re.MULTILINE).search(text, m.end())
        return m.start(), (nxt.start() if nxt else len(text))
    m = re.search(rf"^#+ {head}[ \t]*$(?:\n#[^\n]*)*", text, re.MULTILINE)
    return (m.start(), m.end()) if m else None


def _read_config(config_file: Path) -> tuple[str, bool] | None:
    """Decode strictly and normalize line endings for processing.

    Returns (text_with_LF, had_crlf), or None when the file is not valid
    UTF-8 — in that case we must never rewrite it (errors='replace' would
    permanently mojibake every non-UTF-8 byte in the user's file)."""
    try:
        text = config_file.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return None
    crlf = "\r\n" in text
    if crlf:
        text = text.replace("\r\n", "\n")
    return text, crlf


def _write_config(config_file: Path, text: str, crlf: bool) -> None:
    """Atomic replace with a .bak snapshot, preserving the file's own line
    endings (newline='' disables translation — a user's LF file must not come
    back CRLF just because the server runs on Windows)."""
    from app.entries import _write_atomic
    out = text.replace("\n", "\r\n") if crlf else text
    _write_atomic(config_file, out, backup=True, newline="")


def valid_custom_annotation(agent: dict, text: str) -> bool:
    """True when user-edited annotation text still carries exactly one
    well-formed marker pair (so future updates/removal keep working)."""
    return marker_state(agent, text.replace("\r\n", "\n")) == "ok"


def annotation_status(agent: dict, config_file: Path) -> str:
    """'none' | 'marked' | 'broken' (damaged markers — EntryBox will not
    touch the file) | 'legacy' (marker-less hand-written block) |
    'unreadable' (not UTF-8)."""
    if not config_file.exists():
        return "none"
    loaded = _read_config(config_file)
    if loaded is None:
        return "unreadable"
    text, _ = loaded
    state = marker_state(agent, text)
    if state == "ok":
        return "marked"
    if state == "broken":
        return "broken"
    if _find_legacy_span(agent, text):
        return "legacy"
    return "none"


def write_annotation(agent: dict, project: dict, config_file: Path, annotation: str) -> str:
    """Write/refresh the managed block. Never destroys user content: with
    damaged markers or a non-UTF-8 file the file is left byte-identical.

    Returns: 'created' | 'replaced' | 'replaced_other' (replaced a block that
    belonged to a different project — same root registered twice) |
    'adopted' | 'appended' | 'skipped_broken' | 'skipped_unreadable'.
    """
    annotation = annotation.replace("\r\n", "\n").rstrip("\n") + "\n"

    if not config_file.exists():
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(annotation, encoding="utf-8", newline="")
        return "created"

    loaded = _read_config(config_file)
    if loaded is None:
        logger.warning("%s is not valid UTF-8 — annotation not written", config_file)
        return "skipped_unreadable"
    text, crlf = loaded

    state = marker_state(agent, text)
    if state == "broken":
        logger.warning("%s has damaged EntryBox markers — annotation not written "
                       "(fix or delete the stray marker lines)", config_file)
        return "skipped_broken"

    if state == "ok":
        start, end = _block_span(agent, text)
        old_block = text[start:end]
        _write_config(config_file, text[:start] + annotation + text[end:], crlf)
        m = re.search(r"Prefix: (\S+)", old_block)
        if m and m.group(1) != project.get("prefix"):
            return "replaced_other"
        return "replaced"

    legacy = _find_legacy_span(agent, text)
    if legacy:
        before = text[:legacy[0]].rstrip("\n")
        after = text[legacy[1]:].lstrip("\n")
        parts = [p for p in (before, annotation.rstrip("\n"), after) if p]
        _write_config(config_file, "\n\n".join(parts) + "\n", crlf)
        return "adopted"

    _write_config(config_file, text.rstrip("\n") + "\n\n" + annotation, crlf)
    return "appended"


def remove_annotation(agent: dict, config_file: Path) -> bool:
    if not config_file.exists():
        return False
    loaded = _read_config(config_file)
    if loaded is None:
        logger.warning("%s is not valid UTF-8 — annotation not removed", config_file)
        return False
    text, crlf = loaded

    state = marker_state(agent, text)
    if state == "broken":
        logger.warning("%s has damaged EntryBox markers — annotation not removed", config_file)
        return False

    if state == "ok":
        start, end = _block_span(agent, text)
        new_text = text[:start].rstrip("\n") + "\n\n" + text[end:].lstrip("\n")
        new_text = new_text.strip("\n")
        _write_config(config_file, (new_text + "\n") if new_text else "", crlf)
        return True

    legacy = _find_legacy_span(agent, text)
    if legacy is None:
        return False
    new_text = (text[:legacy[0]].rstrip("\n") + "\n\n" + text[legacy[1]:].lstrip("\n")).strip("\n")
    _write_config(config_file, (new_text + "\n") if new_text else "", crlf)
    return True
