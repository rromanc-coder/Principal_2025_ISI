import os, json, asyncio, time
from typing import List, Dict, Any
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import httpx

app = FastAPI(title="principal-isi", version="1.1.0")

# -------- helpers --------
def load_teams() -> List[Dict[str, Any]]:
    raw = os.getenv("TEAMS_JSON", "[]")
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("TEAMS_JSON debe ser lista")
        return data
    except Exception as e:
        print(f"[WARN] TEAMS_JSON inválido: {e}")
        return []

def get_host() -> str:
    return os.getenv("WG_HOST", "localhost")

async def _check_one(client: httpx.AsyncClient, team: Dict[str, Any]) -> Dict[str, Any]:
    name = team.get("name")
    port = int(team.get("port", 0))
    internal_url = f"http://{name}:8000/health"  # dentro de la red de Docker
    external_url = f"http://{get_host()}:{port}/" if port else None

    started = time.monotonic()
    status = "down"
    code = None
    err = None
    try:
        r = await client.get(internal_url, timeout=1.5)
        code = r.status_code
        if r.is_success:
            status = "up"
    except Exception as ex:
        err = str(ex)
    latency_ms = int((time.monotonic() - started) * 1000)
    return {
        "name": name,
        "port": port,
        "repo": team.get("repo"),
        "internal_url": internal_url,
        "external_url": external_url,
        "status": status,
        "http": code,
        "latency_ms": latency_ms,
        "error": err,
    }

async def check_all() -> List[Dict[str, Any]]:
    teams = load_teams()
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[_check_one(client, t) for t in teams])
    return results

# -------- rutas API --------
@app.get("/teams")
def teams():
    return {"host": get_host(), "teams": load_teams()}

@app.get("/status")
async def status():
    res = await check_all()
    return JSONResponse({"host": get_host(), "results": res})

@app.get("/health")
def health():
    return {"status": "ok"}

# -------- página --------
@app.get("/", response_class=HTMLResponse)
def root():
    host = get_host()
    html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8"/>
<title>Principal ISI</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 20px; }}
  table {{ border-collapse: collapse; width: 100%; max-width: 960px; }}
  th, td {{ border: 1px solid #ddd; padding: 8px; }}
  th {{ background: #f3f3f3; text-align: left; }}
  .pill {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px; }}
  .up {{ background:#e6ffed; color:#046c4e; border:1px solid #b7f5c8; }}
  .down {{ background:#ffe6e6; color:#8a1f1f; border:1px solid #ffc2c2; }}
