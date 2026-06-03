import httpx
from pathlib import Path
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from app.projects import get_project, project_status
from app.entries import (
    VALID_TYPES, VALID_STATES,
    load_entries, add_entry, update_entry_state, update_entry, delete_entry, ensure_file,
)
from app.config import WEBHOOK_URL

router = APIRouter()


def _project_or_404(project_id: str):
    project = get_project(project_id)
    if not project:
        return None, JSONResponse({"error": "project not found"}, status_code=404)
    if project_status(project) == "unreachable":
        return None, JSONResponse({"error": "project root unreachable"}, status_code=503)
    return project, None


async def _fire_webhook(event: str, project: dict, entry: dict, old_state: str | None = None):
    url = project.get("webhook_url") or WEBHOOK_URL
    if not url:
        return
    payload = {"event": event, "project": project["id"], "entry": entry}
    if old_state is not None:
        payload["old_state"] = old_state
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(url, json=payload)
    except Exception:
        pass


@router.get("/api/projects/{project_id}/entries")
async def list_entries(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    project, err = _project_or_404(project_id)
    if err:
        return err
    entries_file = Path(project["entries_file"])
    ensure_file(entries_file, project["name"], project["prefix"])
    all_entries = load_entries(entries_file, project["prefix"])
    total = len(all_entries)
    page = all_entries[offset : offset + limit]
    return {"entries": page, "total": total, "offset": offset, "limit": limit, "project": project}


@router.post("/api/projects/{project_id}/entries")
async def create_entry(project_id: str, body: dict):
    project, err = _project_or_404(project_id)
    if err:
        return err
    title = (body.get("title") or "").strip()
    if not title:
        return JSONResponse({"error": "title required"}, status_code=400)
    entry_type = (body.get("type") or "idea").strip().lower()
    if entry_type not in VALID_TYPES:
        entry_type = "idea"
    text = (body.get("body") or "").strip()

    entries_file = Path(project["entries_file"])
    entry = add_entry(entries_file, project["prefix"], project["name"], title, text, entry_type)
    await _fire_webhook("entry_created", project, entry)
    return {"ok": True, **entry}


@router.patch("/api/projects/{project_id}/entries")
async def patch_entry(project_id: str, body: dict):
    project, err = _project_or_404(project_id)
    if err:
        return err
    entry_id = (body.get("id") or "").strip()
    if not entry_id:
        return JSONResponse({"error": "id required"}, status_code=400)

    entries_file = Path(project["entries_file"])
    entry = None

    # Content edit — title / body / type. A key is only touched if it was sent.
    if body.keys() & {"title", "body", "type"}:
        new_title = body.get("title")
        if new_title is not None:
            new_title = new_title.strip()
            if not new_title:
                return JSONResponse({"error": "title cannot be empty"}, status_code=400)
        new_type = body.get("type")
        if new_type is not None:
            new_type = new_type.strip().lower()
            if new_type not in VALID_TYPES:
                return JSONResponse({"error": f"invalid type, must be one of {sorted(VALID_TYPES)}"}, status_code=400)
        new_body = body.get("body")
        if new_body is not None:
            new_body = new_body.strip()
        entry = update_entry(entries_file, project["prefix"], entry_id,
                             title=new_title, body=new_body, entry_type=new_type)
        if entry is None:
            return JSONResponse({"error": "entry not found"}, status_code=404)
        await _fire_webhook("entry_updated", project, entry)

    # State change — handled separately so it keeps its own webhook + done_at logic.
    new_state = (body.get("state") or "").strip().lower()
    if new_state:
        if new_state not in VALID_STATES:
            return JSONResponse({"error": f"invalid state, must be one of {sorted(VALID_STATES)}"}, status_code=400)
        entry, old_state = update_entry_state(entries_file, project["prefix"], entry_id, new_state)
        if entry is None:
            return JSONResponse({"error": "entry not found"}, status_code=404)
        await _fire_webhook("state_changed", project, entry, old_state)

    if entry is None:
        return JSONResponse({"error": "nothing to update; send state and/or title/body/type"}, status_code=400)
    return {"ok": True, "entry": entry}


@router.delete("/api/projects/{project_id}/entries")
async def remove_entry(project_id: str, body: dict):
    project, err = _project_or_404(project_id)
    if err:
        return err
    entry_id = (body.get("id") or "").strip()
    if not entry_id:
        return JSONResponse({"error": "id required"}, status_code=400)
    entries_file = Path(project["entries_file"])
    ok = delete_entry(entries_file, project["prefix"], entry_id)
    if not ok:
        return JSONResponse({"error": "entry not found"}, status_code=404)
    return {"ok": True}
