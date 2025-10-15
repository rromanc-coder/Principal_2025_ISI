from fastapi import Request
from typing import Callable
from db import SessionLocal
from models import Activity

def activity_middleware(app):
    @app.middleware("http")
    async def log_activity(request: Request, call_next: Callable):
        # evita ruido de /static y /health
        if request.url.path.startswith("/static") or request.url.path == "/health":
            return await call_next(request)

        response = await call_next(request)
        try:
            db = SessionLocal()
            ua = request.headers.get("user-agent", "")
            ip = request.client.host if request.client else None
            db.add(Activity(
                user_id=None,
                path=request.url.path,
                method=request.method,
                user_agent=ua,
                remote_ip=ip,
                detail=None
            ))
            db.commit()
        except Exception:
            pass
        finally:
            try: db.close()
            except: pass
        return response
