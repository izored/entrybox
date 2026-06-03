import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = Path(os.getenv("ENTRYBOX_DATA_DIR", str(BASE_DIR / "data")))
THEMES_DIR = BASE_DIR / "themes"
BIND_HOST = os.getenv("ENTRYBOX_BIND", "127.0.0.1")
PORT = int(os.getenv("ENTRYBOX_PORT", "3859"))
WEBHOOK_URL = os.getenv("ENTRYBOX_WEBHOOK_URL", "")
# Optional shared secret. When set, sensitive routes (file read, tree,
# attachment upload) require header X-EntryBox-Token to match.
TOKEN = os.getenv("ENTRYBOX_TOKEN", "")

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
        return dict(_DEFAULTS)


def _save(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_state() -> dict:
    return _load()


def update_state(patch: dict) -> dict:
    data = _load()
    data.update(patch)
    _save(data)
    return data
