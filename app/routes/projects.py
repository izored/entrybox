from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.projects import (
    get_projects, get_project, register_project,
    unregister_project, project_status, scan_project_agents,
    scan_project_annotations, update_project_agents,
)
from app.agents import get_all_agents, build_annotation, get_agent

router = APIRouter(prefix="/api/projects")


@router.get("")
async def list_projects():
    projects = get_projects()
    result = []
    for p in projects:
        result.append({**p, "status": project_status(p)})
    return {"projects": result}


@router.post("")
async def add_project(body: dict):
    name = (body.get("name") or "").strip()
    root_dir = (body.get("root_dir") or "").strip()
    prefix = (body.get("prefix") or "ENTRY").strip().upper()
    project_id = (body.get("id") or prefix.lower()).strip()
    color = body.get("color", "#3b9eff")
    agent_ids = body.get("agent_ids", [])
    auto_write = body.get("auto_write", True)
    migrate_from = body.get("migrate_from")

    if not name or not root_dir:
        return JSONResponse({"error": "name and root_dir required"}, status_code=400)
    if not Path(root_dir).exists():
        return JSONResponse({"error": "root_dir does not exist"}, status_code=400)

    project = register_project(
        project_id=project_id, name=name, root_dir=root_dir, prefix=prefix,
        color=color, agent_ids=agent_ids, auto_write=auto_write, migrate_from=migrate_from,
    )
    return {"ok": True, "project": project}


@router.get("/{project_id}")
async def get_one_project(project_id: str):
    project = get_project(project_id)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {**project, "status": project_status(project)}


@router.delete("/{project_id}")
async def remove_project(project_id: str, body: dict = {}):
    remove_annotations = body.get("remove_annotations", True)
    ok = unregister_project(project_id, remove_annotations=remove_annotations)
    if not ok:
        return JSONResponse({"error": "project not found"}, status_code=404)
    return {"ok": True}


@router.get("/{project_id}/scan-agents")
async def scan_agents(project_id: str):
    project = get_project(project_id)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    found = scan_project_agents(project["root_dir"])
    statuses = scan_project_annotations(project["root_dir"])
    return {
        "found_agent_ids": found,
        "annotation_status": statuses,
        "legacy_agent_ids": [a for a, s in statuses.items() if s == "legacy"],
    }


@router.post("/scan-dir")
async def scan_directory(body: dict):
    root_dir = (body.get("root_dir") or "").strip()
    if not root_dir:
        return JSONResponse({"error": "root_dir required"}, status_code=400)
    if not Path(root_dir).exists():
        return JSONResponse({"error": "directory not found"}, status_code=404)
    found = scan_project_agents(root_dir)
    statuses = scan_project_annotations(root_dir)
    return {
        "found_agent_ids": found,
        "annotation_status": statuses,
        "legacy_agent_ids": [a for a, s in statuses.items() if s == "legacy"],
    }


@router.post("/{project_id}/agents")
async def set_project_agents(project_id: str, body: dict):
    agent_ids = body.get("agent_ids", [])
    auto_write = body.get("auto_write", True)
    project = update_project_agents(project_id, agent_ids, auto_write)
    if project is None:
        return JSONResponse({"error": "project not found"}, status_code=404)
    return {"ok": True, "project": project}


@router.post("/{project_id}/preview-annotation")
async def preview_annotation(project_id: str, body: dict):
    agent_id = (body.get("agent_id") or "").strip()
    host = body.get("host", "localhost")
    port = body.get("port", 3859)
    project = get_project(project_id)
    agent = get_agent(agent_id)
    if not project or not agent:
        return JSONResponse({"error": "project or agent not found"}, status_code=404)
    annotation = build_annotation(agent, project, host, port)
    return {"annotation": annotation, "config_file": agent["config_file"]}
