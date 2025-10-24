from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import settings
from middleware import activity_middleware
from db import Base, engine

from routers import public, auth, pages

app = FastAPI(title=settings.APP_TITLE, version=settings.APP_VERSION)

# Static mount robusto (no depende del cwd)
if settings.STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")
else:
    print(f"[INFO] Carpeta 'static' no encontrada en {settings.STATIC_DIR}; /static deshabilitado")

# Middleware
activity_middleware(app)

# Crear tablas al iniciar (no falla la app si no hay DB)
@app.on_event("startup")
def _create_tables():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as ex:
        print(f"[WARN] No se pudieron crear tablas: {ex}")

# Routers
app.include_router(public.router)
app.include_router(auth.router)
app.include_router(pages.router)
