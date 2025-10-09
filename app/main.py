import os, json, asyncio, datetime
from typing import Any, Dict, List
import httpx
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

WG_HOST = os.getenv("WG_HOST", "10.5.20.50")

DEFAULT_TEAMS = [
    {"name": "equipo1", "port": 9001, "repo": "https://github.com/rromanc-coder/equipo1"},
    {"name": "equipo2", "port": 9002, "repo": "https://github.com/rromanc-coder/equipo2"},
    {"name": "equipo3", "port": 9003, "repo": "https://github.com/rromanc-coder/equipo3"},
    {"name": "equipo4", "port": 9004, "repo": "https://github.com/rromanc-coder/equipo4"},
    {"name": "equipo5", "port": 9005, "repo": "https://github.com/rromanc-coder/equipo5"},
    {"name": "equipo6", "port": 9006, "repo": "https://github.com/rromanc-coder/equipo6"},
]

def load_teams():
    raw = os.getenv("TEAMS_JSON", "").strip()
    if not raw:
        return DEFAULT_TEAMS
    try:
        return json.loads(raw)
    except Exception:
        return DEFAULT_TEAMS

TEAMS = load_teams()

app = FastAPI(title="Principal ISI - Dashboard", version="1.0.0")

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
    }
    try:
        r = await client.get(url, timeout=1.5)
        if r.status_code == 200:
            js = r.json()
            data["status"] = "OK"
            data["build"] = js.get("build")
    except Exception:
        pass
    return data

async def gather_status():
    async with httpx.AsyncClient() as client:
        return await asyncio.gather(*(fetch_health(client, t) for t in TEAMS))

@app.get("/")
async def home(request: Request):
    rows = await gather_status()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return templates.TemplateResponse("index.html", {"request": request, "rows": rows, "ts": ts})

@app.get("/health")
def health():
    return {"status": "ok", "teams": len(TEAMS)}
