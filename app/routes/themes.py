from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.theme import list_themes, get_theme, get_active_theme_id, set_active_theme, get_active_theme_vars

router = APIRouter(prefix="/api/themes")


@router.get("")
async def themes_list():
    return {"themes": list_themes(), "active": get_active_theme_id()}


@router.get("/active")
async def active_theme():
    theme_id = get_active_theme_id()
    theme = get_theme(theme_id)
    return {"id": theme_id, "theme": theme, "vars": get_active_theme_vars()}


@router.post("/active")
async def set_theme(body: dict):
    theme_id = (body.get("id") or "").strip()
    if not theme_id:
        return JSONResponse({"error": "id required"}, status_code=400)
    theme = set_active_theme(theme_id)
    if theme is None:
        return JSONResponse({"error": "theme not found"}, status_code=404)
    return {"ok": True, "id": theme_id, "vars": theme.get("vars", {})}


@router.get("/{theme_id}")
async def get_one_theme(theme_id: str):
    theme = get_theme(theme_id)
    if not theme:
        return JSONResponse({"error": "theme not found"}, status_code=404)
    return {"id": theme_id, "theme": theme, "vars": theme.get("vars", {})}
