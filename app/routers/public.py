from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
import httpx
from typing import Dict, Any
from config import settings
from services import monitor, state

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/teams")
def teams():
    return {"host": settings.WG_HOST, "teams": monitor.load_teams(settings.TEAMS_JSON)}

@router.get("/status")
async def status():
    res = await monitor.check_all(settings.WG_HOST, settings.TEAMS_JSON)
    monitor.update_history(res)
    for r in res:
        n = r.get("name") or ""
        r["uptime_pct"] = monitor.uptime_pct(n)
        le = monitor.last_err(n)
        if le and not r.get("error"):
            r["error"] = le
    return JSONResponse({"host": settings.WG_HOST, "results": res, "ts": int(state.now_ts())})

@router.get("/history")
def history():
    out = {name: list(buf) for name, buf in state.history.items()}
    return out

@router.get("/metrics", response_class=HTMLResponse)
def metrics():
    return monitor.render_metrics(settings.TEAMS_JSON)

@router.get("/diag")
async def diag():
    out = {"ok": True, "errors": [], "internal_checks": []}
    try:
        data = monitor.load_teams(settings.TEAMS_JSON)
    except Exception as e:
        out["ok"] = False
        out["errors"].append(f"TEAMS_JSON inválido: {e}")
        data = []

    failed = []
    async with httpx.AsyncClient() as client:
        for t in data:
            name = t.get("name")
            if not name:
                continue
            try:
                r = await client.get(f"http://{name}:8000/health", timeout=0.8)
                if not r.is_success:
                    failed.append({"name": name, "status": r.status_code})
            except Exception as ex:
                failed.append({"name": name, "error": str(ex)})
    out["internal_checks"] = failed
    return out
