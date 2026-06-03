import logging
import os
import re
import shutil
from datetime import datetime
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

# Timestamp fragment: a date with an OPTIONAL " HH:MM". Tolerating a missing
# time keeps hand-written, date-only stamps from being silently dropped — a drop
# made the entry invisible and let its ID number get recycled into a duplicate.
_TS = r"\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?"


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


def _write_atomic(path: Path, text: str, backup: bool = False) -> None:
    """Write via temp-file + atomic rename so a crash mid-write can't truncate
    the entries file. With backup=True, snapshot the prior contents to
    `<file>.bak` first (used for the automatic, unattended migration rewrite)."""
    if backup and path.exists():
        try:
            shutil.copy2(path, path.with_name(path.name + ".bak"))
        except OSError:
            pass
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _parse_block(block: str, prefix: str) -> dict | None:
    block = block.strip()
    pre = re.escape(prefix)

    # With done_at: ## PREFIX-NNNN · ts · type · state · done_at — title
    m = re.match(
        rf"## ({pre}-\d+) · ({_TS}) · (\w+) · (\w+) · ({_TS}) — (.+)\n?([\s\S]*)",
        block,
    )
    if m:
        return {"id": m.group(1), "timestamp": m.group(2), "type": m.group(3),
                "state": m.group(4), "done_at": m.group(5), "title": m.group(6).strip(), "body": m.group(7).strip()}

    # Without done_at: ## PREFIX-NNNN · ts · type · state — title
    m = re.match(
        rf"## ({pre}-\d+) · ({_TS}) · (\w+) · (\w+) — (.+)\n?([\s\S]*)",
        block,
    )
    if m:
        return {"id": m.group(1), "timestamp": m.group(2), "type": m.group(3),
                "state": m.group(4), "done_at": None, "title": m.group(5).strip(), "body": m.group(6).strip()}

    # Transitional (no state): ## PREFIX-NNNN · ts · type — title
    m = re.match(
        rf"## ({pre}-\d+) · ({_TS}) · (\w+) — (.+)\n?([\s\S]*)",
        block,
    )
    if m:
        return {"id": m.group(1), "timestamp": m.group(2), "type": m.group(3),
                "state": "logged", "done_at": None, "title": m.group(4).strip(), "body": m.group(5).strip()}

    # Old format: ## YYYY-MM-DD HH:MM — title
    m = re.match(rf"## ({_TS}) — (.+)\n?([\s\S]*)", block)
    if m:
        return {"id": None, "timestamp": m.group(1), "type": "idea",
                "state": "logged", "done_at": None, "title": m.group(2).strip(), "body": m.group(3).strip()}

    return None


def _entry_text(entry: dict) -> str:
    body = entry.get("body") or ""
    state = entry.get("state") or "logged"
    done_at = entry.get("done_at")
    if state == "done" and done_at:
        header = f"## {entry['id']} · {entry['timestamp']} · {entry['type']} · {state} · {done_at} — {entry['title']}"
    else:
        header = f"## {entry['id']} · {entry['timestamp']} · {entry['type']} · {state} — {entry['title']}"
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
                # Missing ID, or a duplicate of one already kept → fresh ID. The
                # earliest occurrence keeps the number; later collisions move.
                if eid is not None:
                    logger.warning("entrybox: duplicate id %s in %s — reassigning", eid, entries_file)
                entry["id"] = _next_id(existing_ids, prefix)
                existing_ids.append(entry["id"])
            assigned.add(entry["id"])
            # Self-heal: normalise any date-only stamps while we're rewriting.
            entry["timestamp"] = _pad_ts(entry["timestamp"])
            entry["done_at"] = _pad_ts(entry["done_at"])
        body_text = "\n".join(_entry_text(e) for e in entries)
        _write_atomic(entries_file, preamble.rstrip("\n") + "\n\n" + body_text, backup=True)
        mtime = entries_file.stat().st_mtime

    _cache[key] = (mtime, entries)
    return list(reversed(entries))


def add_entry(entries_file: Path, prefix: str, project_name: str, title: str, body: str, entry_type: str) -> dict:
    ensure_file(entries_file, project_name, prefix)
    with _lock(entries_file):
        # Trigger any legacy-format migration/rewrite first…
        load_entries(entries_file, prefix)
        # …then derive the next ID from every PREFIX-NNNN token in the file, so an
        # unparseable block can never cause a number to be handed out twice.
        raw = entries_file.read_text(encoding="utf-8", errors="replace")
        existing_ids = re.findall(rf"{re.escape(prefix)}-\d+", raw)
        new_id = _next_id(existing_ids, prefix)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = {"id": new_id, "timestamp": ts, "type": entry_type, "state": "logged",
                 "done_at": None, "title": title, "body": body}
        with open(entries_file, "a", encoding="utf-8") as f:
            f.write("\n" + _entry_text(entry))
    return entry


def update_entry_state(entries_file: Path, prefix: str, entry_id: str, new_state: str) -> tuple[dict | None, str | None]:
    if not entries_file.exists():
        return None, None
    with _lock(entries_file):
        entries = load_entries(entries_file, prefix)
        entry = next((e for e in entries if e["id"] == entry_id), None)
        if not entry:
            return None, None
        old_state = entry["state"]
        entry["state"] = new_state
        text = entries_file.read_text(encoding="utf-8", errors="replace")
        pattern = rf"(## {re.escape(entry_id)} · [^·]+ · \w+) · \w+(?: · {_TS})? —"
        if new_state == "done":
            done_at = datetime.now().strftime("%Y-%m-%d %H:%M")
            entry["done_at"] = done_at
            replacement = rf"\1 · {new_state} · {done_at} —"
        else:
            entry["done_at"] = None
            replacement = rf"\1 · {new_state} —"
        new_text = re.sub(pattern, replacement, text)
        _write_atomic(entries_file, new_text)
    return entry, old_state


def update_entry(entries_file: Path, prefix: str, entry_id: str,
                 title: str | None = None, body: str | None = None,
                 entry_type: str | None = None) -> dict | None:
    """Edit an entry's title, body, and/or type in place. ID, timestamp, state
    and done_at are preserved. Only the target block is rewritten — sibling
    blocks are left byte-for-byte untouched. Returns the updated entry, or None
    if the ID is not found. Pass a field as None to leave it unchanged."""
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
                blocks[i] = _entry_text(parsed)
                updated = parsed
                break
        if updated is None:
            return None
        _write_atomic(entries_file, "\n".join(blocks))
        _cache.pop(str(entries_file), None)
    return updated


def _reap_attachments(entrybox_dir: Path, block_text: str) -> None:
    """Delete attachment files referenced by a removed entry block. Best-effort,
    sandboxed to the project's .entrybox/attachments dir."""
    try:
        att_dir = (entrybox_dir / "attachments").resolve()
    except (OSError, RuntimeError):
        return
    for ref in set(re.findall(r"attachments/([A-Za-z0-9._-]+)", block_text)):
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
            _reap_attachments(entries_file.parent, m.group(0))
    return True
