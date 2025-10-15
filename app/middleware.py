from fastapi import Request
from typing import Callable
from db import SessionLocal
from models import Activity

def activity_middleware(app):
    @app.middleware("http")
    async def log_activity(request: Request, call_next: Callable):
        # opcional: no registrar /static y /health
        if request.url.path.startswith("/static") or request.url.path == "/health":
            return await call_next(request)

        try:
            response = await call_next(request)
        finally:
            try:
                db = SessionLocal()
                ua = request.headers.get("user-agent", "")
                ip = request.client.host if request.client else None
                db.add(Activity(
                    user_id=None,  # Si luego quieres asociar el user, guárdalo en request.state
                    path=request.url.path,
                    method=request.method,
                    user_agent=ua,
                    remote_ip=ip,
                    detail=None
                ))
                db.commit()
                db.close()
            except Exception:
                pass
        return response
