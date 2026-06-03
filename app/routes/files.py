"""Project file surface: file read (preview / attachment serving), directory
tree, and attachment upload. Every path goes through app.files.resolve_in_root
(sandbox) and every route is token-gated (no-op unless ENTRYBOX_TOKEN is set).

Uploads are base64 JSON, not multipart — avoids a python-multipart dependency
and matches how browser paste / extension captureVisibleTab produce data.
"""
import base64
import re
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, FileResponse

from app.projects import get_project, project_status
from app.files import resolve_in_root, build_tree, MAX_READ_BYTES
from app.security import require_token

router = APIRouter()

ALLOWED_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp",
    ".txt", ".log", ".json", ".csv", ".md", ".har", ".diff", ".patch", ".yml", ".yaml",
}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]")
_CT = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
    ".webp": "image/webp", ".svg": "image/svg+xml", ".bmp": "image/bmp",
    ".txt": "text/plain", ".log": "text/plain", ".md": "text/plain", ".csv": "text/csv",
    ".json": "application/json", ".har": "application/json", ".diff": "text/plain",
    ".patch": "text/plain", ".yml": "text/plain", ".yaml": "text/plain",
}


def _project_or_404(project_id: str):
    project = get_project(project_id)
    if not project:
        return None, JSONResponse({"error": "project not found"}, status_code=404)
    if project_status(project) == "unreachable":
        return None, JSONResponse({"error": "project root unreachable"}, status_code=503)
    return project, None


@router.get("/api/projects/{project_id}/tree", dependencies=[Depends(require_token)])
async def project_tree(project_id: str):
    project, err = _project_or_404(project_id)
    if err:
        return err
    tree = build_tree(project["root_dir"])
    if tree is None:
        return JSONResponse({"error": "project root unreachable"}, status_code=503)
    return {"tree": tree}


@router.get("/api/projects/{project_id}/file", dependencies=[Depends(require_token)])
async def project_file(project_id: str, path: str = Query(...)):
    project, err = _project_or_404(project_id)
    if err:
        return err
    target = resolve_in_root(project["root_dir"], path)
    if target is None or not target.is_file():
        return JSONResponse({"error": "file not found"}, status_code=404)
    if target.stat().st_size > MAX_READ_BYTES:
        return JSONResponse({"error": "file too large to preview"}, status_code=413)
    ct = _CT.get(target.suffix.lower(), "application/octet-stream")
    return FileResponse(target, media_type=ct)


@router.post("/api/projects/{project_id}/attachments", dependencies=[Depends(require_token)])
async def upload_attachment(project_id: str, body: dict):
    project, err = _project_or_404(project_id)
    if err:
        return err
    filename = (body.get("filename") or "").strip()
    data = body.get("data") or ""
    if not data:
        return JSONResponse({"error": "data required (base64)"}, status_code=400)
    if data.startswith("data:"):  # strip data-URL prefix
        comma = data.find(",")
        if comma != -1:
            data = data[comma + 1:]
    try:
        raw = base64.b64decode(data, validate=False)
    except Exception:
        return JSONResponse({"error": "invalid base64"}, status_code=400)
    if not raw:
        return JSONResponse({"error": "empty file"}, status_code=400)
    if len(raw) > MAX_UPLOAD_BYTES:
        return JSONResponse({"error": "file too large (max 10MB)"}, status_code=413)
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return JSONResponse({"error": f"extension not allowed: {ext or '(none)'}"}, status_code=400)
    stem = _SAFE_NAME.sub("_", Path(filename).stem)[:48] or "file"
    name = f"{stem}-{int(time.time() * 1000)}{ext}"
    rel = f".entrybox/attachments/{name}"
    if resolve_in_root(project["root_dir"], rel) is None:
        return JSONResponse({"error": "bad path"}, status_code=400)
    att_dir = Path(project["root_dir"]) / ".entrybox" / "attachments"
    att_dir.mkdir(parents=True, exist_ok=True)
    (att_dir / name).write_bytes(raw)
    return {"ok": True, "ref": f"attachments/{name}", "name": name}
