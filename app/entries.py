import logging
import os
import re
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    from filelock import FileLock
    def _lock(path: Path):
        return FileLock(str(path) + ".lock")
except ImportError:
    import contextlib
    @contextlib.contextmanager
    def _lock(path):
        yield

logger = logging.getLogger(__name__)

# path → (mtime, entries_chronological)
_cache: dict[str, tuple[float, list[dict]]] = {}

VALID_TYPES = {"fix", "improve", "docs", "idea", "roadmap"}
VALID_STATES = {"logged", "review", "wip", "done", "error"}
VALID_PRIORITIES = {"A", "B", "C"}
VALID_RECURS = {"daily", "weekly", "monthly", "yearly"}

# Timestamp fragment: a date with an OPTIONAL " HH:MM". Tolerating a missing
# time keeps hand-written, date-only stamps from being silently dropped — a drop
# made the entry invisible and let its ID number get recycled into a duplicate.
_TS = r"\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?"

# Optional ` · key:value` segments appended after state (or done_at).
# key = word chars only; value = anything except whitespace, middle-dot, em-dash.
# This pattern captures the whole segment including leading space·space.
_EXTRAS_RE = r"((?:\s+·\s+\w+:[^\s·—]+)*)"


def _extras(raw: str) -> dict:
    """Extract key:value pairs from a ` · key:val · ...` extras segment."""
    result = {}
    for m in re.finditer(r'(\w+):([^\s·—]+)', raw or ''):
        result[m.group(1)] = m.group(2)
    return result


def _header(project_name: str, prefix: str) -> str:
    return f"# {prefix} — EntryBox\n\nEntry tracking for {project_name}. Managed by EntryBox.\n"


def ensure_file(entries_file: Path, project_name: str, prefix: str) -> None:
    entries_file.parent.mkdir(parents=True, exist_ok=True)
    if not entries_file.exists():
        entries_file.write_text(_header(project_name, prefix) + "\n", encoding="utf-8")


def _next_id(existing_ids: list[str], prefix: str) -> str:
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    nums = [int(m.group(1)) for eid in existing_ids if (m := pattern.match(eid))]
    return f"{prefix}-{(max(nums) + 1 if nums else 1):04d}"


def _pad_ts(ts: str | None) -> str | None:
    """Pad a date-only stamp (YYYY-MM-DD) to YYYY-MM-DD 00:00 for consistency."""
    if ts and re.fullmatch(r"\d{4}-\d{2}-\d{2}", ts.strip()):
        return ts.strip() + " 00:00"
    return ts


# A body line that would match the block separator in _parse_file would split
# the entry in two on the next load (a phantom entry gets fabricated and the
# original body is truncated — silent data mangling from an ordinary markdown
# paste). Neutralize on write with a leading backslash; strip it on parse.
# Only separator-shaped lines are touched, so normal bodies round-trip
# byte-identically and stay human-readable.
def _danger_line(prefix: str) -> str:
    return rf"## (?:{re.escape(prefix)}-\d+|\d{{4}}-\d{{2}}-\d{{2}})"


def _escape_body(body: str, prefix: str) -> str:
    return re.sub(rf"^(\\*{_danger_line(prefix)})", r"\\\1", body, flags=re.MULTILINE)


def _unescape_body(body: str, prefix: str) -> str:
    return re.sub(rf"^\\(\\*{_danger_line(prefix)})", r"\1", body, flags=re.MULTILINE)


def _write_atomic(path: Path, text: str, backup: bool = False,
                  newline: str | None = None) -> None:
    """Write via temp-file + atomic rename so a crash mid-write can't truncate
    the entries file. With backup=True, snapshot the prior contents to
    `<file>.bak` first (used for the automatic, unattended migration rewrite).
    newline="" disables newline translation (caller controls line endings —
    used when rewriting files EntryBox does not own)."""
    if backup and path.exists():
        try:
            shutil.copy2(path, path.with_name(path.name + ".bak"))
        except OSError:
            pass
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline=newline)
    os.replace(tmp, path)


def _parse_block(block: str, prefix: str) -> dict | None:
    block = block.strip()
    pre = re.escape(prefix)

    def body(raw: str) -> str:
        return _unescape_body(raw.strip(), prefix)

    # With done_at: ## PREFIX-NNNN · ts · type · state · done_at [extras] — title
    m = re.match(
        rf"## ({pre}-\d+) · ({_TS}) · (\w+) · (\w+) · ({_TS}){_EXTRAS_RE} — (.+)\n?([\s\S]*)",
        block,
    )
    if m:
        ex = _extras(m.group(6))
        return {"id": m.group(1), "timestamp": m.group(2), "type": m.group(3),
                "state": m.group(4), "done_at": m.group(5), "title": m.group(7).strip(),
                "body": body(m.group(8)),
                "priority": ex.get("pri"), "due": ex.get("due"), "recur": ex.get("recur")}

    # Without done_at: ## PREFIX-NNNN · ts · type · state [extras] — title
    m = re.match(
        rf"## ({pre}-\d+) · ({_TS}) · (\w+) · (\w+){_EXTRAS_RE} — (.+)\n?([\s\S]*)",
        block,
    )
    if m:
        ex = _extras(m.group(5))
        return {"id": m.group(1), "timestamp": m.group(2), "type": m.group(3),
                "state": m.group(4), "done_at": None, "title": m.group(6).strip(),
                "body": body(m.group(7)),
                "priority": ex.get("pri"), "due": ex.get("due"), "recur": ex.get("recur")}

    # Transitional (no state): ## PREFIX-NNNN · ts · type — title
    m = re.match(
        rf"## ({pre}-\d+) · ({_TS}) · (\w+) — (.+)\n?([\s\S]*)",
        block,
    )
    if m:
        return {"id": m.group(1), "timestamp": m.group(2), "type": m.group(3),
                "state": "logged", "done_at": None, "title": m.group(4).strip(),
                "body": body(m.group(5)),
                "priority": None, "due": None, "recur": None}

    # Old format: ## YYYY-MM-DD HH:MM — title
    m = re.match(rf"## ({_TS}) — (.+)\n?([\s\S]*)", block)
    if m:
        return {"id": None, "timestamp": m.group(1), "type": "idea",
                "state": "logged", "done_at": None, "title": m.group(2).strip(),
                "body": body(m.group(3)),
                "priority": None, "due": None, "recur": None}

    return None


def _entry_text(entry: dict, prefix: str) -> str:
    body = _escape_body(entry.get("body") or "", prefix)
    state = entry.get("state") or "logged"
    done_at = entry.get("done_at")
    priority = entry.get("priority")
    due = entry.get("due")
    recur = entry.get("recur")

    if state == "done" and done_at:
        header = f"## {entry['id']} · {entry['timestamp']} · {entry['type']} · {state} · {done_at}"
    else:
        header = f"## {entry['id']} · {entry['timestamp']} · {entry['type']} · {state}"

    if priority:
        header += f" · pri:{priority}"
    if due:
        header += f" · due:{due}"
    if recur:
        header += f" · recur:{recur}"

    header += f" — {entry['title']}"
    return f"{header}\n\n{body}\n" if body else f"{header}\n\n"


def _parse_file(entries_file: Path, prefix: str) -> tuple[str, list[dict]]:
    text = entries_file.read_text(encoding="utf-8", errors="replace")
    sep = rf"\n(?=## (?:{re.escape(prefix)}-\d+|\d{{4}}-\d{{2}}-\d{{2}}))"
    blocks = re.split(sep, text)
    preamble = blocks[0]
    entries = []
    for b in blocks[1:]:
        parsed = _parse_block(b, prefix)
        if parsed is None:
            snippet = b.strip().splitlines()[0] if b.strip() else "<empty>"
            logger.warning("entrybox: dropping unparseable entry block in %s: %r", entries_file, snippet)
            continue
        entries.append(parsed)
    return preamble, entries


def load_entries(entries_file: Path, prefix: str) -> list[dict]:
    if not entries_file.exists():
        return []

    key = str(entries_file)
    mtime = entries_file.stat().st_mtime
    if key in _cache and _cache[key][0] == mtime:
        return list(reversed(_cache[key][1]))

    preamble, entries = _parse_file(entries_file, prefix)

    # Duplicate-ID detection: two blocks sharing an ID must be repaired, else the
    # UI sees colliding keys and update/delete can target the wrong block.
    seen_ids: set[str] = set()
    has_dupes = False
    for e in entries:
        if e["id"] is not None:
            if e["id"] in seen_ids:
                has_dupes = True
            seen_ids.add(e["id"])

    needs_rewrite = has_dupes or any(e["id"] is None for e in entries)
    if not needs_rewrite:
        text = entries_file.read_text(encoding="utf-8", errors="replace")
        needs_rewrite = not re.search(rf"## {re.escape(prefix)}-\d+ · .+ · \w+ · \w+ — ", text)

    if needs_rewrite:
        # Derive next IDs from every PREFIX-NNNN token in the raw file, not just
        # the parsed entries, so a malformed/dropped block can't recycle a number.
        raw = entries_file.read_text(encoding="utf-8", errors="replace")
        existing_ids = re.findall(rf"{re.escape(prefix)}-\d+", raw)
        assigned: set[str] = set()
        for entry in entries:
            eid = entry["id"]
            if eid is None or eid in assigned:
                if eid is not None:
                    logger.warning("entrybox: duplicate id %s in %s — reassigning", eid, entries_file)
                entry["id"] = _next_id(existing_ids, prefix)
                existing_ids.append(entry["id"])
            assigned.add(entry["id"])
            entry["timestamp"] = _pad_ts(entry["timestamp"])
            entry["done_at"] = _pad_ts(entry["done_at"])
        body_text = "\n".join(_entry_text(e, prefix) for e in entries)
        _write_atomic(entries_file, preamble.rstrip("\n") + "\n\n" + body_text, backup=True)
        mtime = entries_file.stat().st_mtime

    _cache[key] = (mtime, entries)
    return list(reversed(entries))


def add_entry(entries_file: Path, prefix: str, project_name: str, title: str, body: str,
              entry_type: str, priority: str | None = None, due: str | None = None,
              recur: str | None = None) -> dict:
    ensure_file(entries_file, project_name, prefix)
    with _lock(entries_file):
        load_entries(entries_file, prefix)
        raw = entries_file.read_text(encoding="utf-8", errors="replace")
        existing_ids = re.findall(rf"{re.escape(prefix)}-\d+", raw)
        new_id = _next_id(existing_ids, prefix)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = {"id": new_id, "timestamp": ts, "type": entry_type, "state": "logged",
                 "done_at": None, "title": title, "body": body,
                 "priority": priority or None, "due": due or None, "recur": recur or None}
        with open(entries_file, "a", encoding="utf-8") as f:
            f.write("\n" + _entry_text(entry, prefix))
    return entry


def next_due(due: str | None, recur: str) -> str | None:
    """Compute the next due date for a recurring entry after completion."""
    if not due:
        return None
    try:
        d = date.fromisoformat(due)
        deltas = {"daily": timedelta(1), "weekly": timedelta(7),
                  "monthly": timedelta(30), "yearly": timedelta(365)}
        delta = deltas.get(recur)
        if delta is None:
            return None
        return (d + delta).isoformat()
    except (ValueError, TypeError):
        return None


def update_entry_state(entries_file: Path, prefix: str, entry_id: str,
                       new_state: str) -> tuple[dict | None, str | None]:
    if not entries_file.exists():
        return None, None
    with _lock(entries_file):
        entries = load_entries(entries_file, prefix)
        entry = next((e for e in entries if e["id"] == entry_id), None)
        if not entry:
            return None, None
        old_state = entry["state"]
        text = entries_file.read_text(encoding="utf-8", errors="replace")
        # Capture extras (pri:/due:/recur: fields) to preserve them through the state change.
        pattern = rf"(## {re.escape(entry_id)} · [^·]+ · \w+) · \w+(?: · {_TS})?{_EXTRAS_RE} —"
        # Verify the header actually matches BEFORE mutating the (cached) entry
        # dict — otherwise a manually mangled header would return success while
        # the file stays unchanged and cache and disk disagree.
        if re.search(pattern, text) is None:
            logger.warning("entrybox: header for %s in %s did not match — state not changed",
                           entry_id, entries_file)
            return None, None
        entry["state"] = new_state
        if new_state == "done":
            done_at = datetime.now().strftime("%Y-%m-%d %H:%M")
            entry["done_at"] = done_at
            replacement = rf"\1 · {new_state} · {done_at}\2 —"
        else:
            entry["done_at"] = None
            replacement = rf"\1 · {new_state}\2 —"
        new_text = re.sub(pattern, replacement, text)
        _write_atomic(entries_file, new_text)
    return entry, old_state


def update_entry(entries_file: Path, prefix: str, entry_id: str,
                 title: str | None = None, body: str | None = None,
                 entry_type: str | None = None, priority: str | None = None,
                 due: str | None = None, recur: str | None = None) -> dict | None:
    """Edit an entry's title, body, type, priority, due, and/or recur in place.
    ID, timestamp, state and done_at are preserved. Only the target block is
    rewritten — sibling blocks are left byte-for-byte untouched. Pass a field
    as None to leave it unchanged; pass empty string to clear it."""
    if not entries_file.exists():
        return None
    with _lock(entries_file):
        text = entries_file.read_text(encoding="utf-8", errors="replace")
        sep = rf"\n(?=## (?:{re.escape(prefix)}-\d+|\d{{4}}-\d{{2}}-\d{{2}}))"
        blocks = re.split(sep, text)
        updated = None
        for i in range(1, len(blocks)):
            parsed = _parse_block(blocks[i], prefix)
            if parsed and parsed["id"] == entry_id:
                if title is not None:
                    parsed["title"] = title
                if entry_type is not None:
                    parsed["type"] = entry_type
                if body is not None:
                    parsed["body"] = body
                if priority is not None:
                    parsed["priority"] = priority if priority else None
                if due is not None:
                    parsed["due"] = due if due else None
                if recur is not None:
                    parsed["recur"] = recur if recur else None
                blocks[i] = _entry_text(parsed, prefix)
                updated = parsed
                break
        if updated is None:
            return None
        _write_atomic(entries_file, "\n".join(blocks))
        _cache.pop(str(entries_file), None)
    return updated


def _reap_attachments(entrybox_dir: Path, block_text: str, surviving_text: str = "") -> None:
    """Delete attachment files referenced ONLY by a removed entry block.
    Files still referenced by `surviving_text` (the remaining entries) are
    kept. Best-effort, sandboxed to the project's .entrybox/attachments dir."""
    try:
        att_dir = (entrybox_dir / "attachments").resolve()
    except (OSError, RuntimeError):
        return
    still_referenced = set(re.findall(r"attachments/([A-Za-z0-9._-]+)", surviving_text))
    for ref in set(re.findall(r"attachments/([A-Za-z0-9._-]+)", block_text)):
        if ref in still_referenced:
            continue
        target = (att_dir / ref).resolve()
        try:
            target.relative_to(att_dir)
        except ValueError:
            continue
        if target.is_file():
            try:
                target.unlink()
            except OSError:
                pass


def delete_entry(entries_file: Path, prefix: str, entry_id: str) -> bool:
    if not entries_file.exists():
        return False
    with _lock(entries_file):
        text = entries_file.read_text(encoding="utf-8", errors="replace")
        pattern = rf"\n## {re.escape(entry_id)} · [\s\S]*?(?=\n## (?:{re.escape(prefix)}-\d+|\d{{4}}-\d{{2}}-\d{{2}})|\Z)"
        m = re.search(pattern, text)
        new_text = re.sub(pattern, "", text)
        if new_text == text:
            return False
        _write_atomic(entries_file, new_text)
        if m:
            _reap_attachments(entries_file.parent, m.group(0), new_text)
    return True
