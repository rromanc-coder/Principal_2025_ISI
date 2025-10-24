import json, time, math, asyncio
from typing import List, Dict, Any
import httpx

from . import state

def load_teams(raw: str) -> List[Dict[str, Any]]:
    try:
        data = json.loads(raw or "[]")
        if not isinstance(data, list):
            raise ValueError("TEAMS_JSON debe ser lista")
        return data
    except Exception as e:
        print(f"[WARN] TEAMS_JSON inválido: {e}")
        return []

def infer_tag(name: str) -> str:
    if not name:
        return "-"
    n = name.lower()
    if n.startswith("equipo"): return "PLN"
    if n.startswith("itm"):    return "ITM"
    return "General"

def uptime_pct(name: str) -> float:
    buf = state.history.get(name)
    if not buf: return 0.0
    total = len(buf)
    if total == 0: return 0.0
    ups = sum(x["up"] for x in buf)
    return round(100.0 * ups / total, 1)

def last_err(name: str) -> str:
    return state.last_error.get(name, "")

async def _check_one(client: httpx.AsyncClient, team: Dict[str, Any], wg_host: str) -> Dict[str, Any]:
    name = team.get("name")
    port = int(team.get("port", 0))
    internal_url = f"http://{name}:8000/health"  # red interna Docker
    external_url = f"http://{wg_host}:{port}/" if port else None
    tag = (team.get("tag") or team.get("course") or team.get("materia") or "").strip() or infer_tag(name)

    started = time.monotonic()
    status_txt, code, err = "down", None, None
    try:
        r = await client.get(internal_url, timeout=1.5)
        code = r.status_code
        if r.is_success:
            status_txt = "up"
    except Exception as ex:
        err = str(ex)
    latency_ms = int((time.monotonic() - started) * 1000)

    return {
        "name": name,
        "tag": tag,
        "port": port,
        "repo": team.get("repo"),
        "internal_url": internal_url,
        "external_url": external_url,
        "status": status_txt,
        "http": code,
        "latency_ms": latency_ms,
        "error": err,
    }

async def check_all(wg_host: str, teams_json: str) -> List[Dict[str, Any]]:
    teams = load_teams(teams_json)
    async with httpx.AsyncClient() as client:
        return await asyncio.gather(*[_check_one(client, t, wg_host) for t in teams])

def update_history(results: List[Dict[str, Any]]) -> None:
    now = state.now_ts()
    for r in results:
        name = r.get("name") or "unknown"
        up = 1 if r.get("status") == "up" else 0
        lat = r.get("latency_ms")
        err = r.get("error")
        state.history[name].append({"ts": now, "up": up, "lat": lat, "err": err})
        if err:
            state.last_error[name] = err

def render_metrics(teams_json: str) -> str:
    lines = [
        '# HELP service_up 1 si el servicio está UP, 0 si DOWN',
        '# TYPE service_up gauge',
        '# HELP service_latency_ms Latencia de /health en ms (última lectura)',
        '# TYPE service_latency_ms gauge',
        '# HELP service_uptime_pct Uptime en % dentro de la ventana local',
        '# TYPE service_uptime_pct gauge',
    ]

    teams = load_teams(teams_json)
    names = [t.get("name") for t in teams if t.get("name")]

    for name in names:
        buf = state.history.get(name, [])
        if buf:
            last = buf[-1]
            up = last["up"]
            lat = last["lat"] if last["lat"] is not None else math.nan
        else:
            up, lat = 0, math.nan
        upct = uptime_pct(name)
        labels = f'service="{name}"'
        lines.append(f'service_up{{{labels}}} {up}')
        lines.append(f'service_latency_ms{{{labels}}} {lat}')
        lines.append(f'service_uptime_pct{{{labels}}} {upct}')

    return "\n".join(lines) + "\n"
