from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from config import settings
from middleware import activity_middleware
from db import Base, engine

from routers import public, auth as auth_router, pages

app = FastAPI(title=settings.APP_TITLE, version=settings.APP_VERSION)

# Static mount robusto (no depende del cwd)
if settings.STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")
else:
    print(f"[INFO] Carpeta 'static' no encontrada en {settings.STATIC_DIR}; /static deshabilitado")

# Middleware
activity_middleware(app)

# Crear tablas al iniciar (no tumba la app si falla)
@app.on_event("startup")
def _create_tables():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as ex:
        print(f"[WARN] No se pudieron crear tablas: {ex}")

# Routers
app.include_router(public.router)
app.include_router(auth_router.router)
app.include_router(pages.router)
