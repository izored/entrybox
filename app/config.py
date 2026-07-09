import json
import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger("entrybox")

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = Path(os.getenv("ENTRYBOX_DATA_DIR", str(BASE_DIR / "data")))
THEMES_DIR = BASE_DIR / "themes"
BIND_HOST = os.getenv("ENTRYBOX_BIND", "127.0.0.1")
PORT = int(os.getenv("ENTRYBOX_PORT", "3859"))
WEBHOOK_URL = os.getenv("ENTRYBOX_WEBHOOK_URL", "")
# Optional shared secret. When set, sensitive routes (file read, tree,
# attachment upload) require header X-EntryBox-Token to match.
TOKEN = os.getenv("ENTRYBOX_TOKEN", "")
# Max attachment size (upload + serve). Bump via env for larger files.
MAX_UPLOAD_MB = int(os.getenv("ENTRYBOX_MAX_UPLOAD_MB", "25"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

_STATE_FILE = DATA_DIR / "entrybox.json"

_DEFAULTS = {
    "theme": "dark",
    "booted": False,
    "onboarded": False,
    "ai_tools": ["claude-code"],
    "auto_write_agent_config": True,
    "projects": [],
    "learned_agents": [],
}


def _load() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not _STATE_FILE.exists():
        _STATE_FILE.write_text(json.dumps(_DEFAULTS, indent=2), encoding="utf-8")
        return dict(_DEFAULTS)
    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        for k, v in _DEFAULTS.items():
            data.setdefault(k, v)
        return data
    except Exception:
        # This file holds every project registration — never silently reset
        # it without keeping the evidence recoverable.
        try:
            snapshot = _STATE_FILE.with_name(_STATE_FILE.name + ".corrupt")
            shutil.copy2(_STATE_FILE, snapshot)
            logger.warning("entrybox.json is unreadable — snapshotted to %s and "
                           "falling back to defaults", snapshot)
        except OSError:
            logger.warning("entrybox.json is unreadable and could not be snapshotted")
        return dict(_DEFAULTS)


def _save(data: dict) -> None:
    from app.entries import _write_atomic
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _write_atomic(_STATE_FILE, json.dumps(data, indent=2, ensure_ascii=False))


def get_state() -> dict:
    return _load()


def update_state(patch: dict) -> dict:
    # entrybox.json is read-modify-written by the UI and the CLI concurrently;
    # the same lock discipline the entries files get.
    from app.entries import _lock
    with _lock(_STATE_FILE):
        data = _load()
        data.update(patch)
        _save(data)
    return data
