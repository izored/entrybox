"""Sandboxed filesystem access scoped to a project's root_dir.

Every file / tree / attachment feature MUST go through resolve_in_root() so a
request can never escape the project directory via `..`, an absolute path, a
drive prefix, or a symlink. This is the single chokepoint for the local
file-read surface — keep it small and well-tested.
"""
import os
import re
from pathlib import Path

# Directories never walked or surfaced in a project file tree.
IGNORE_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules",
    "__pycache__", ".entrybox", ".idea", ".vscode", "dist", "build",
    ".next", ".cache", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "target", ".gradle", ".tox",
}
MAX_TREE_ENTRIES = 4000
# Cap a single file read so a preview can't pull a multi-GB blob into memory.
MAX_READ_BYTES = 512 * 1024


def resolve_in_root(root_dir, relpath: str) -> Path | None:
    """Resolve ``relpath`` beneath ``root_dir``.

    Returns the absolute Path if it stays inside the (symlink-resolved) root,
    otherwise None. ``relpath`` must be relative — absolute or drive-qualified
    inputs are rejected outright.
    """
    if relpath is None:
        return None
    # Windows-shaped absolute inputs must be rejected on every OS: on POSIX,
    # "C:\\x" or "\\\\server\\share" is just a strange relative filename to
    # pathlib, which would silently pass the checks below.
    rp = str(relpath)
    if re.match(r"^[A-Za-z]:", rp) or rp.startswith(("\\\\", "//")):
        return None
    if os.name != "nt" and "\\" in rp:
        return None
    try:
        root = Path(root_dir).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return None
    rel = Path(relpath)
    if rel.is_absolute() or rel.drive or rel.anchor:
        return None
    try:
        target = (root / rel).resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    try:
        target.relative_to(root)
    except ValueError:
        return None
    return target


def build_tree(root_dir, max_entries: int = MAX_TREE_ENTRIES) -> dict | None:
    """Nested dict tree of the project root, skipping IGNORE_DIRS and dotfiles,
    capped at ``max_entries`` total nodes.

    Node shape: ``{"name", "type": "dir"|"file", "path", "children"?}``.
    ``path`` is the POSIX relpath from root (usable as a file_ref).
    """
    try:
        root = Path(root_dir).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return None
    count = 0

    def walk(d: Path) -> list:
        nonlocal count
        items = []
        try:
            children = sorted(d.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except OSError:
            return items
        for p in children:
            if count >= max_entries:
                break
            if p.name.startswith(".") or p.name in IGNORE_DIRS:
                continue
            count += 1
            rel = p.relative_to(root).as_posix()
            if p.is_dir():
                items.append({"name": p.name, "type": "dir", "path": rel, "children": walk(p)})
            else:
                items.append({"name": p.name, "type": "file", "path": rel})
        return items

    return {"name": root.name, "type": "dir", "path": "", "children": walk(root)}
