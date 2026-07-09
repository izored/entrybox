import shutil
from pathlib import Path
from app.config import get_state, update_state
from app.agents import (
    detect_agents_in_project, get_agent, get_all_agents,
    build_annotation, write_annotation, remove_annotation, annotation_status,
    valid_custom_annotation,
)


def get_projects() -> list[dict]:
    return get_state().get("projects", [])


def get_project(project_id: str) -> dict | None:
    return next((p for p in get_projects() if p["id"] == project_id), None)


def project_status(project: dict) -> str:
    root = Path(project["root_dir"])
    if not root.exists():
        return "unreachable"
    entries = Path(project["entries_file"])
    if not entries.exists():
        return "no_entries"
    return "ok"


def register_project(
    project_id: str,
    name: str,
    root_dir: str,
    prefix: str,
    color: str = "#3b9eff",
    agent_ids: list[str] | None = None,
    auto_write: bool = True,
    migrate_from: str | None = None,
    annotations: dict[str, str] | None = None,
) -> tuple[dict, dict[str, str]]:
    from datetime import datetime
    from app.entries import ensure_file

    root = Path(root_dir)
    entrybox_dir = root / ".entrybox"
    entries_file = entrybox_dir / "entries.md"

    entrybox_dir.mkdir(parents=True, exist_ok=True)

    if migrate_from:
        src = Path(migrate_from)
        if src.exists() and not entries_file.exists():
            shutil.copy2(src, entries_file)
    else:
        ensure_file(entries_file, name, prefix)

    project = {
        "id": project_id,
        "name": name,
        "root_dir": str(root_dir),
        "prefix": prefix,
        "entries_file": str(entries_file),
        "color": color,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "active_agents": agent_ids or [],
    }

    state = get_state()
    projects = state.get("projects", [])
    projects = [p for p in projects if p["id"] != project_id]
    projects.append(project)
    update_state({"projects": projects})

    annotation_results: dict[str, str] = {}
    if auto_write and agent_ids:
        for aid in agent_ids:
            agent = get_agent(aid)
            if not agent:
                continue
            cfg_path = root / agent["config_file"]
            # Honor a user-edited block from the UI preview — but only when it
            # still carries exactly one well-formed marker pair, so future
            # updates and removal keep working. Otherwise fall back to the
            # canonical template.
            custom = (annotations or {}).get(aid)
            if custom and valid_custom_annotation(agent, custom):
                annotation = custom
            else:
                annotation = build_annotation(agent, project)
            annotation_results[aid] = write_annotation(agent, project, cfg_path, annotation)

    return project, annotation_results


def unregister_project(project_id: str, remove_annotations: bool = True) -> bool:
    project = get_project(project_id)
    if not project:
        return False

    if remove_annotations:
        root = Path(project["root_dir"])
        for aid in project.get("active_agents", []):
            agent = get_agent(aid)
            if not agent:
                continue
            cfg_path = root / agent["config_file"]
            remove_annotation(agent, cfg_path)

    state = get_state()
    projects = [p for p in state.get("projects", []) if p["id"] != project_id]
    update_state({"projects": projects})
    return True


def update_project_agents(project_id: str, agent_ids: list[str],
                          auto_write: bool = True) -> tuple[dict, dict[str, str]] | None:
    project = get_project(project_id)
    if not project:
        return None

    root = Path(project["root_dir"])
    old_agents = set(project.get("active_agents", []))
    new_agents = set(agent_ids)
    annotation_results: dict[str, str] = {}

    if auto_write:
        for aid in new_agents - old_agents:
            agent = get_agent(aid)
            if agent:
                cfg_path = root / agent["config_file"]
                annotation = build_annotation(agent, project)
                annotation_results[aid] = write_annotation(agent, project, cfg_path, annotation)

        for aid in old_agents - new_agents:
            agent = get_agent(aid)
            if agent:
                cfg_path = root / agent["config_file"]
                removed = remove_annotation(agent, cfg_path)
                annotation_results[aid] = "removed" if removed else "not_removed"

    project["active_agents"] = list(new_agents)
    state = get_state()
    projects = [p if p["id"] != project_id else project for p in state.get("projects", [])]
    update_state({"projects": projects})
    return project, annotation_results


def scan_project_agents(root_dir: str) -> list[str]:
    return detect_agents_in_project(Path(root_dir))


def scan_project_annotations(root_dir: str) -> dict[str, str]:
    """Per-agent annotation state: 'none', 'marked' or 'legacy'.

    'legacy' = an EntryBox block exists in that config file without marker
    tags; registering will adopt it (replace in place, no duplicate)."""
    root = Path(root_dir)
    return {
        agent["id"]: annotation_status(agent, root / agent["config_file"])
        for agent in get_all_agents()
    }
