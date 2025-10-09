import os, json, asyncio, time
from typing import List, Dict, Any
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import httpx

app = FastAPI(title="principal-isi", version="1.2.0")

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

def get_logos() -> Dict[str, str]:
    return {
        "uaemex": os.getenv("LOGO_UAEMEX_URL", "").strip(),
        "ing": os.getenv("LOGO_ING_URL", "").strip(),
    }

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
    logos = get_logos()

    html = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Principal ISI</title>
<style>
  :root {
    --bg: #ffffff;
    --fg: #111827;
    --muted: #6b7280;
    --card: #f9fafb;
    --border: #e5e7eb;
    --good-bg: #e6ffed; --good-fg: #046c4e; --good-br: #b7f5c8;
    --bad-bg: #ffe6e6; --bad-fg: #8a1f1f; --bad-br: #ffc2c2;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0b0f14;
      --fg: #e5e7eb;
      --muted: #9ca3af;
      --card: #111827;
      --border: #1f2937;
      --good-bg: #0a2f1e; --good-fg: #a7f3d0; --good-br: #14532d;
      --bad-bg: #3b0a0a; --bad-fg: #fecaca; --bad-br: #7f1d1d;
    }
    img { filter: brightness(0.95) contrast(1.05); }
  }
  body { margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.5 system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, "Helvetica Neue", Arial; }
  .container { max-width: 1050px; margin: 0 auto; padding: 24px; }
  .brand { display: grid; gap: 12px; align-items: center; justify-items: center; grid-template-columns: 120px 1fr 120px; }
  .brand .logo { max-height: 80px; width: auto; object-fit: contain; }
  .titles { text-align: center; }
  .titles h1 { margin: 0; font-size: 1.75rem; }
  .titles p { margin: 4px 0 0; color: var(--muted); }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-top: 24px; }
  table { width
