import os, json, asyncio, datetime
from typing import Any, Dict, List
import httpx
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

WG_HOST = os.getenv("WG_HOST", "10.5.20.50")

# Lista de equipos por env: TEAMS_JSON con objetos {name, port, repo}
# Si no viene, hace fallback a 6 equipos estándar
DEFAULT_TEAMS = [
    {"name": "equipo1", "port": 9001, "repo": "https://github.com/<USER>/equipo1"},
    {"name": "equipo2", "port": 9002, "repo": "https://github.com/<USER>/equipo2"},
    {"name": "equipo3", "port": 9003, "repo": "https://github.com/<USER>/equipo3"},
    {"name": "equipo4", "port": 9004, "repo": "https://github.com/<USER>/equipo4"},
    {"name": "equipo5", "port": 9005, "repo": "https://github.com/<USER>/equipo5"},
    {"name": "equipo6", "port": 9006, "repo": "https://github.com/<USER>/equipo6"},
]

def load_teams() -> List[Dict[str, Any]]:
    raw = os.getenv("TEAMS_JSON", "").strip()
    if not raw:
        return DEFAULT_TEAMS
    try:
        return json.loads(raw)
    except Exception:
        return DEFAULT_TEAMS

TEAMS = load_teams()

app = FastAPI(title="Salas - Dashboard", version="1.0.0")

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

async def fetch_health(client: httpx.AsyncClient, team: Dict[str, Any]) -> Dict[str, Any]:
    url = f"http://{WG_HOST}:{team['port']}/health"
    data = {
        "name": team["name"],
        "repo": team.get("repo"),
        "port": team["port"],
        "api": f"http://{WG_HOST}:{team['port']}",
        "docs": f"http://{WG_HOST}:{team['port']}/docs",
        "status": "DOWN",
        "build": None,
        "error": None,
    }
    try:
        r = await client.get(url, timeout=1.5)
        if r.status_code == 200:
            js = r.json()
            data["status"] = "OK"
            data["build"] = js.get("build")
        else:
            data["error"] = f"HTTP {r.status_code}"
    except Exception as e:
        data["error"] = str(e)
    return data

async def gather_status() -> List[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        return await asyncio.gather(*(fetch_health(client, t) for t in TEAMS))

@app.get("/")
async def home(request: Request):
    rows = await gather_status()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return templates.TemplateResponse("index.html", {"request": request, "rows": rows, "ts": ts})

@app.get("/api/status")
async def api_status():
    rows = await gather_status()
    return {"updated_at": datetime.datetime.now().isoformat(), "teams": rows}

@app.get("/health")
def health():
    return {"status": "ok", "teams": len(TEAMS)}
