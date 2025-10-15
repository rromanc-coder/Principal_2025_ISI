import os, json, asyncio, time
from typing import List, Dict, Any
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import httpx

from collections import deque, defaultdict
import time

# Mantener 60 muestras (~5 min si refrescas cada 5s; cambia el tamaño según prefieras)
HISTORY_WINDOW = 60
_history = defaultdict(lambda: deque(maxlen=HISTORY_WINDOW))  # name -> deque[{"ts":..., "up":0/1, "lat":ms, "err":str|None}]
_last_error = {}  # name -> str

app = FastAPI(title="principal-isi", version="1.3.0")

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

def infer_tag(name: str) -> str:
    """Inferir la materia/etiqueta si no viene en TEAMS_JSON."""
    if not name:
        return "-"
    n = name.lower()
    if n.startswith("equipo"):
        return "PLN"
    if n.startswith("itm"):
        return "ITM"
    return "General"

async def _check_one(client: httpx.AsyncClient, team: Dict[str, Any]) -> Dict[str, Any]:
    name = team.get("name")
    port = int(team.get("port", 0))
    internal_url = f"http://{name}:8000/health"  # red interna Docker
    external_url = f"http://{get_host()}:{port}/" if port else None
    tag = (team.get("tag") or team.get("course") or team.get("materia") or "").strip() or infer_tag(name)

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
        "tag": tag,
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
def update_history(results: List[Dict[str, Any]]) -> None:
    now = time.time()
    for r in results:
        name = r.get("name") or "unknown"
        up = 1 if r.get("status") == "up" else 0
        lat = r.get("latency_ms")
        err = r.get("error")
        _history[name].append({"ts": now, "up": up, "lat": lat, "err": err})
        if err:
            _last_error[name] = err

def uptime_pct(name: str) -> float:
    buf = _history.get(name)
    if not buf:
        return 0.0
    total = len(buf)
    if total == 0:
        return 0.0
    ups = sum(x["up"] for x in buf)
    return round(100.0 * ups / total, 1)

def last_error(name: str) -> str:
    return _last_error.get(name, "")

# -------- API --------
@app.get("/teams")
def teams():
    return {"host": get_host(), "teams": load_teams()}

@app.get("/status")
async def status():
    res = await check_all()
    # actualizar histórico
    update_history(res)
    # enriquecer respuesta con uptime/error
    for r in res:
        n = r.get("name") or ""
        r["uptime_pct"] = uptime_pct(n)
        le = last_error(n)
        if le and not r.get("error"):
            r["error"] = le
    return JSONResponse({"host": get_host(), "results": res, "ts": int(time.time())})
@app.get("/health")
def health():
    return {"status": "ok"}

# -------- Página --------
@app.get("/metrics", response_class=HTMLResponse)
def metrics():
    lines = []
    # Help/Type
    lines.append('# HELP service_up 1 si el servicio está UP, 0 si DOWN')
    lines.append('# TYPE service_up gauge')
    lines.append('# HELP service_latency_ms Latencia de /health en ms (última lectura)')
    lines.append('# TYPE service_latency_ms gauge')
    lines.append('# HELP service_uptime_pct Uptime en % dentro de la ventana local')
    lines.append('# TYPE service_uptime_pct gauge')

    # Últimos resultados (si no hay, intenta inferir con history)
    teams = load_teams()
    names = [t.get("name") for t in teams if t.get("name")]
    for name in names:
        buf = _history.get(name, [])
        if buf:
            last = buf[-1]
            up = last["up"]
            lat = last["lat"] if last["lat"] is not None else float("nan")
        else:
            up, lat = 0, float("nan")
        upct = uptime_pct(name)
        labels = f'service="{name}"'
        lines.append(f'service_up{{{labels}}} {up}')
        lines.append(f'service_latency_ms{{{labels}}} {lat}')
        lines.append(f'service_uptime_pct{{{labels}}} {upct}')
    return "\n".join(lines) + "\n"
    
@app.get("/history")
def history():
    out = {}
    for name, buf in _history.items():
        out[name] = list(buf)  # pequeño, solo últimas N
    return out
    
@app.get("/", response_class=HTMLResponse)
def root():
    host = get_host()
    logos = get_logos()

    # Construimos HTML sin comillas triples ni f-strings
    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='es'>",
        "<head>",
        "<meta charset='utf-8'/>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'/>",
        "<title>Principal ISI - Dashboard</title>",
        "<style>",
        ":root{--bg:#ffffff;--fg:#111827;--muted:#6b7280;--card:#f9fafb;--border:#e5e7eb;",
        "--good-bg:#e6ffed;--good-fg:#046c4e;--good-br:#b7f5c8;",
        "--bad-bg:#ffe6e6;--bad-fg:#8a1f1f;--bad-br:#ffc2c2;}",
        "@media (prefers-color-scheme: dark){:root{--bg:#0b0f14;--fg:#e5e7eb;--muted:#9ca3af;--card:#111827;--border:#1f2937;",
        "--good-bg:#0a2f1e;--good-fg:#a7f3d0;--good-br:#14532d;--bad-bg:#3b0a0a;--bad-fg:#fecaca;--bad-br:#7f1d1d;}img{filter:brightness(0.95) contrast(1.05);}}",
        "body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,\"Helvetica Neue\",Arial;}",
        ".container{max-width:1150px;margin:0 auto;padding:24px;}",
        ".brand{display:grid;gap:12px;align-items:center;justify-items:center;grid-template-columns:120px 1fr 120px;}",
        ".brand .logo{max-height:80px;width:auto;object-fit:contain;}",
        ".titles{text-align:center;}",
        ".titles h1{margin:0;font-size:1.75rem;}",
        ".titles p{margin:4px 0 0;color:var(--muted);}",
        ".card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;margin-top:24px;}",
        "table{width:100%;border-collapse:collapse;}",
        "th,td{border-bottom:1px solid var(--border);padding:10px 8px;text-align:left;}",
        "thead th{background:transparent;font-weight:600;}",
        "tbody tr:nth-child(odd){background:rgba(0,0,0,0.02);}",
        "a{color:inherit;text-decoration:underline;text-underline-offset:2px;}",
        ".pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;vertical-align:middle;}",
        ".up{background:var(--good-bg);color:var(--good-fg);border:1px solid var(--good-br);}",
        ".down{background:var(--bad-bg);color:var(--bad-fg);border:1px solid var(--bad-br);}",
        ".muted{color:var(--muted);font-size:0.9rem;}",
        ".grid{display:grid;gap:16px;grid-template-columns:1fr;}",
        "@media (min-width:900px){.grid{grid-template-columns:1fr;}}",
        "</style>",
        "</head>",
        "<body>",
        "<div class='container'>",
        "<header class='brand'>",
        "<div>__LOGO_UAEMEX__</div>",
        "<div class='titles'>",
        "<h1>Principal_2025_ISI</h1>",
        "<p>WG_HOST: <b>__HOST__</b></p>",
        "</div>",
        "<div>__LOGO_ING__</div>",
        "</header>",
        "<div class='grid'>",
        "<section class='card'>",
        "<h2 style='margin:0 0 12px 0;'>Servicios (estado en vivo)</h2>",
        "<div class='muted' style='margin-bottom:8px;'>Se actualiza cada 5s</div>",
        "<div style='overflow-x:auto;'>",
        "<table id='tbl'>",
        "<thead><tr>",
        "<th>Equipo</th>",
        "<th>Asignatura</th>",
        "<th>Repo</th>",
        "<th>URL</th>",
        "<th>Estado</th>",
        "<th>Latencia</th>",
        "<th>Uptime (ventana)</th>",
        "<th>Último error</th>",
        "</tr></thead>",
        "<tbody id='tbody'><tr><td colspan='6' class='muted'>Cargando...</td></tr></tbody>",
        "</table>",
        "</div>",
        "</section>",
        "</div>",
        "</div>",
        "<script>",
        "function imgTag(url, alt){ if(!url) return ''; const safeAlt = alt || 'logo'; return '<img class=\"logo\" src=\"'+url+'\" alt=\"'+safeAlt+'\" loading=\"lazy\"/>'; }",
        "async function fetchStatus(){",
        " try{",
        "  const r = await fetch('/status');",
        "  if(!r.ok) throw new Error('status '+r.status);",
        "  const data = await r.json();",
        "  const body = document.getElementById('tbody');",
        "  body.innerHTML='';",
        "  for(const row of data.results){",
        "   const tr = document.createElement('tr');",
        "   const tdName=document.createElement('td'); tdName.textContent=row.name||'-'; tr.appendChild(tdName);",
        "   const tdTag=document.createElement('td'); tdTag.textContent=row.tag||'-'; tr.appendChild(tdTag);",
        "   const tdRepo=document.createElement('td');",
        "   if(row.repo){ const a=document.createElement('a'); a.href=row.repo; a.textContent=row.repo; a.target='_blank'; tdRepo.appendChild(a); }",
        "   else{ tdRepo.textContent='-'; }",
        "   tr.appendChild(tdRepo);",
        "   const tdUrl=document.createElement('td');",
        "   if(row.external_url){ const a=document.createElement('a'); a.href=row.external_url; a.textContent=row.external_url; a.target='_blank'; tdUrl.appendChild(a); }",
        "   else{ tdUrl.textContent='-'; }",
        "   tr.appendChild(tdUrl);",
        "   const tdStatus=document.createElement('td');",
        "   const pill=document.createElement('span'); pill.className='pill '+(row.status==='up'?'up':'down');",
        "   pill.textContent=(row.status||'unknown').toUpperCase()+(row.http?' ('+row.http+')':'');",
        "   tdStatus.appendChild(pill);",
        "   if(row.error){ const div=document.createElement('div'); div.className='muted'; div.textContent=row.error; tdStatus.appendChild(div); }",
        "   tr.appendChild(tdStatus);",
        "   const tdLat=document.createElement('td'); tdLat.textContent=(row.latency_ms!=null?row.latency_ms+' ms':'-'); tr.appendChild(tdLat);",
        "   body.appendChild(tr);",
        "  }",
        " }catch(e){ console.error(e); }",
        "}",
        "document.addEventListener('DOMContentLoaded',()=>{",
        " const uaemexDiv=document.querySelectorAll('.brand > div')[0];",
        " const ingDiv=document.querySelectorAll('.brand > div')[2];",
        " uaemexDiv.innerHTML=imgTag('__LOGO_URL_UAEMEX__','Escudo UAEMex');",
        " ingDiv.innerHTML=imgTag('__LOGO_URL_ING__','Escudo Facultad/Ingeniería');",
        "});",
        "fetchStatus(); setInterval(fetchStatus,5000);",
        "</script>",
        "</body>",
        "</html>",
    ]
    html = "\n".join(html_parts)
    # Sustituciones seguras
    html = html.replace("__HOST__", host)
    html = html.replace("__LOGO_URL_UAEMEX__", logos.get("uaemex", ""))
    html = html.replace("__LOGO_URL_ING__", logos.get("ing", ""))
    return html
