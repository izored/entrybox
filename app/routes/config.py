from fastapi import APIRouter
from app.config import get_state, update_state

router = APIRouter(prefix="/api/config")


@router.get("")
async def get_config():
    state = get_state()
    return {
        "booted": state.get("booted", False),
        "onboarded": state.get("onboarded", False),
        "theme": state.get("theme", "dark"),
        "ai_tools": state.get("ai_tools", []),
        "auto_write_agent_config": state.get("auto_write_agent_config", True),
    }


@router.patch("")
async def patch_config(body: dict):
    allowed = {"booted", "onboarded", "theme", "ai_tools", "auto_write_agent_config"}
    patch = {k: v for k, v in body.items() if k in allowed}
    update_state(patch)
    return {"ok": True}
