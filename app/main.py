import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app import __version__
from app.config import BIND_HOST
from app.routes import entries, projects, agents, themes, config as config_router

BASE_DIR = Path(__file__).parent
logger = logging.getLogger("entrybox")

app = FastAPI(title="EntryBox", docs_url=None, redoc_url=None)

# Lock cross-origin reads to loopback + browser-extension origins. Previously
# "*", which let any website you visited read responses from localhost:3859 —
# unacceptable once file-read/tree/attachment routes exist. Requests with no
# Origin header (CLI, quickdrop via urllib, server-to-server) are unaffected.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(https?://(localhost|127\.0\.0\.1)(:\d+)?|(chrome|moz)-extension://[^/]+)$",
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-EntryBox-Token"],
)

if BIND_HOST not in ("127.0.0.1", "localhost", "::1"):
    logger.warning(
        "EntryBox is bound to %s and is UNAUTHENTICATED. Anyone who can reach "
        "this host can read and write your entries and project files. Set "
        "ENTRYBOX_TOKEN to require a token on sensitive routes.", BIND_HOST,
    )

app.include_router(entries.router)
app.include_router(projects.router)
app.include_router(agents.router)
app.include_router(themes.router)
app.include_router(config_router.router)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/assets", StaticFiles(directory=BASE_DIR.parent / "assets"), name="assets")

@app.get("/health", include_in_schema=False)
async def health():
    return JSONResponse({"status": "ok", "version": __version__})

_INDEX = BASE_DIR / "templates" / "index.html"
_QUICK = BASE_DIR / "templates" / "quick.html"


@app.get("/quick", include_in_schema=False)
async def serve_quick():
    return FileResponse(_QUICK, media_type="text/html")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    return FileResponse(_INDEX, media_type="text/html")
