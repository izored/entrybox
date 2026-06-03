from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.routes import entries, projects, agents, themes, config as config_router

BASE_DIR = Path(__file__).parent

app = FastAPI(title="EntryBox", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
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
    return JSONResponse({"status": "ok", "version": "1.0.0"})

_INDEX = BASE_DIR / "templates" / "index.html"
_QUICK = BASE_DIR / "templates" / "quick.html"


@app.get("/quick", include_in_schema=False)
async def serve_quick():
    return FileResponse(_QUICK, media_type="text/html")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    return FileResponse(_INDEX, media_type="text/html")
