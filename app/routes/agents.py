import re
from pathlib import PurePosixPath

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.agents import get_all_agents, get_agent, add_learned_agent, remove_learned_agent, BUILT_IN_AGENTS

router = APIRouter(prefix="/api/agents")


def validate_config_file(config_file: str) -> str | None:
    """Return an error message unless config_file is a safe relative path.

    Annotations are written to root_dir / config_file — an absolute path or a
    `..` segment would let a typo in the custom-agent form write outside the
    project root (pathlib: an absolute right operand replaces the root)."""
    if not config_file or len(config_file) > 200:
        return "config_file must be a relative path inside the project"
    if re.match(r"^[A-Za-z]:", config_file):
        return "config_file must be a relative path inside the project"
    p = PurePosixPath(config_file.replace("\\", "/"))
    if p.is_absolute() or ".." in p.parts:
        return "config_file must be a relative path inside the project"
    return None


@router.get("")
async def list_agents():
    return {"agents": get_all_agents()}


@router.post("")
async def add_agent(body: dict):
    name = (body.get("name") or "").strip()
    config_file = (body.get("config_file") or "").strip()
    template = (body.get("template") or "markdown").strip()
    if not name or not config_file:
        return JSONResponse({"error": "name and config_file required"}, status_code=400)
    err = validate_config_file(config_file)
    if err:
        return JSONResponse({"error": err}, status_code=400)
    if template not in ("markdown", "comment"):
        template = "markdown"
    agent = add_learned_agent(name, config_file, template)
    return {"ok": True, "agent": agent}


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    if any(a["id"] == agent_id for a in BUILT_IN_AGENTS):
        return JSONResponse({"error": "cannot remove built-in agents"}, status_code=400)
    ok = remove_learned_agent(agent_id)
    if not ok:
        return JSONResponse({"error": "agent not found"}, status_code=404)
    return {"ok": True}
