import json
import re
from pathlib import Path
from app.config import THEMES_DIR, get_state, update_state

# Theme ids map straight to filenames — whitelist the charset so an id like
# "../data/entrybox" can never read JSON outside themes/.
_THEME_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def list_themes() -> list[dict]:
    themes = []
    if not THEMES_DIR.exists():
        return themes
    for f in sorted(THEMES_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            themes.append({"id": f.stem, "name": data.get("name", f.stem), "author": data.get("author", "")})
        except Exception:
            pass
    return themes


def get_theme(theme_id: str) -> dict | None:
    if not theme_id or not _THEME_ID.fullmatch(theme_id):
        return None
    path = THEMES_DIR / f"{theme_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def get_active_theme_id() -> str:
    return get_state().get("theme", "dark")


def set_active_theme(theme_id: str) -> dict | None:
    theme = get_theme(theme_id)
    if not theme:
        return None
    update_state({"theme": theme_id})
    return theme


def get_active_theme_vars() -> dict:
    theme_id = get_active_theme_id()
    theme = get_theme(theme_id) or get_theme("dark") or {}
    return theme.get("vars", {})
