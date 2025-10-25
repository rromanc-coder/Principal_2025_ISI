from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

# ---- importa tu stack existente
from middleware import activity_middleware
from db import Base, engine
from routers import public, auth as auth_router, pages

APP_TITLE = "Principal_2025_ISI"
APP_VERSION = "1.5.0"

app = FastAPI(title=APP_TITLE, version=APP_VERSION)

# ---- estáticos (servir build de Angular)
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
else:
    print(f"[WARN] Directorio de estáticos no encontrado: {STATIC_DIR}")

# ---- middleware + DB init
activity_middleware(app)

@app.on_event("startup")
def _create_tables():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as ex:
        print(f"[WARN] No se pudieron crear tablas: {ex}")

# ---- incluye tus routers API/páginas
app.include_router(public.router)
app.include_router(auth_router.router)
app.include_router(pages.router)

# ---- health
@app.get("/health")
def health():
    return {"status": "ok"}

# ---- fallback SPA (Angular): cualquier ruta no-API devuelve index.html
@app.get("/{full_path:path}", response_class=HTMLResponse)
def spa_fallback(full_path: str):
    if full_path.startswith("api"):
        raise HTTPException(status_code=404)
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>Build Angular no encontrado</h1>", status_code=500)
