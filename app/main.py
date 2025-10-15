import os, json, asyncio, time
from typing import List, Dict, Any
from collections import deque, defaultdict

from fastapi import FastAPI, Depends, Response, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import httpx

from db import Base, engine, get_db
from models import User
from schemas import UserCreate, LoginIn, UserOut
from auth import hash_password, verify_password, create_token, get_current_user
from middleware import activity_middleware

app = FastAPI(title="principal-isi", version="1.5.0")

# Static mount (solo si existe)
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
else:
    print("[INFO] Carpeta 'static' no encontrada; /static deshabilitado")

# Middleware de actividad
activity_middleware(app)

# -------- Configuración de histórico para dashboard --------
HISTORY_WINDOW = 60
_history = defaultdict(lambda: deque(maxlen=HISTORY_WINDOW))  # name -> deque[{ts, up, lat, err}]
_last_error = {}  # name -> str

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
    if not name:
        return "-"
    n = name.lower()
    if n.startswith("equipo"): return "PLN"
    if n.startswith("itm"):    return "ITM"
    return "General"

async def _check_one(client: httpx.AsyncClient, team: Dict[str, Any]) -> Dict[str, Any]:
    name = team.get("name")
    port = int(team.get("port", 0))
    internal_url = f"http://{name}:8000/health"  # red interna Docker
    external_url = f"http://{get_host()}:{port}/" if port else None
    tag = (team.get("tag") or team.get("course") or team.get("materia") or "").strip() or infer_tag(name)

    started = time.monotonic()
    status_txt = "down"
    code = None
    err = None
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
    if not buf: return 0.0
    total = len(buf)
    if total == 0: return 0.0
    ups = sum(x["up"] for x in buf)
    return round(100.0 * ups / total, 1)

def last_error(name: str) -> str:
    return _last_error.get(name, "")

# -------- DB: crear tablas al iniciar (con manejo de fallo limpio) --------
@app.on_event("startup")
def _create_tables():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as ex:
        print(f"[WARN] No se pudieron crear tablas: {ex}")

# -------- API: dashboard/monitoring --------
@app.get("/teams")
def teams():
    return {"host": get_host(), "teams": load_teams()}

@app.get("/status")
async def status():
    res = await check_all()
    update_history(res)
    for r in res:
        n = r.get("name") or ""
        r["uptime_pct"] = uptime_pct(n)
        le = last_error(n)
        if le and not r.get("error"):
            r["error"] = le
    return JSONResponse({"host": get_host(), "results": res, "ts": int(time.time())})

@app.get("/history")
def history():
    out = {name: list(buf) for name, buf in _history.items()}
    return out

@app.get("/metrics", response_class=HTMLResponse)
def metrics():
    lines = []
    lines.append('# HELP service_up 1 si el servicio está UP, 0 si DOWN')
    lines.append('# TYPE service_up gauge')
    lines.append('# HELP service_latency_ms Latencia de /health en ms (última lectura)')
    lines.append('# TYPE service_latency_ms gauge')
    lines.append('# HELP service_uptime_pct Uptime en % dentro de la ventana local')
    lines.append('# TYPE service_uptime_pct gauge')

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

@app.get("/diag")
async def diag():
    out = {"ok": True, "errors": [], "internal_checks": []}
    raw = os.getenv("TEAMS_JSON", "[]")
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("TEAMS_JSON no es lista")
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
                    failed.append({ "name": name, "status": r.status_code })
            except Exception as ex:
                failed.append({ "name": name, "error": str(ex) })
    out["internal_checks"] = failed
    return out

@app.get("/health")
def health():
    return {"status": "ok"}

# -------- Auth + App mínima --------
@app.post("/api/register")
def api_register(payload: UserCreate, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Correo ya registrado")
    user = User(email=payload.email, full_name=payload.full_name, password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"ok": True, "user": UserOut.model_validate(user).model_dump()}

@app.post("/api/login")
def api_login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    token = create_token(user.id, user.email)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60*60*12,
        path="/",
        # secure=True,  # habilitar solo si sirves por HTTPS
    )
    return {"ok": True, "user": UserOut.model_validate(user).model_dump()}

@app.post("/api/logout")
def api_logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}

@app.get("/api/me")
def api_me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user).model_dump()

# Página de login simple
@app.get("/login", response_class=HTMLResponse)
def login_form():
    return """
<!DOCTYPE html><html lang="es"><meta charset="utf-8"/>
<body style="font-family: system-ui; margin:2rem;">
  <h2>Iniciar sesión</h2>
  <form id="f" onsubmit="doLogin(event)">
    <div><label>Correo</label><br><input id="email" type="email" required></div>
    <div style="margin-top:8px;"><label>Contraseña</label><br><input id="pass" type="password" required></div>
    <button style="margin-top:12px;">Entrar</button>
  </form>
  <div id="msg" style="color:#c00;margin-top:1rem;"></div>
  <script>
    async function doLogin(e){
      e.preventDefault();
      const email = document.getElementById('email').value;
      const password = document.getElementById('pass').value;
      const r = await fetch('/api/login', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({email, password}),
        credentials: 'same-origin'
      });
      if(r.ok){ location.href = '/app'; }
      else{
        const t = await r.json().catch(()=>({detail:'Error'}));
        document.getElementById('msg').textContent = t.detail || 'Error';
      }
    }
  </script>
</body></html>
"""

# Página protegida (ejemplo)
@app.get("/app", response_class=HTMLResponse)
def app_home(user: User = Depends(get_current_user)):
    return f"""
<!DOCTYPE html><html lang="es"><meta charset="utf-8"/>
<body style="font-family: system-ui; margin:2rem;">
  <h2>Hola {user.full_name or user.email}</h2>
  <p>Bienvenido a la app protegida.</p>
  <p><a href="/">Volver al dashboard</a></p>
</body></html>
"""

# -------- Página principal (dashboard HTML) --------
@app.get("/", response_class=HTMLResponse)
def root():
    host = get_host()
    logos = get_logos()

    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='es'>",
        "<head>",
        "<meta charset='utf-8'/>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'/>",
        "<title>Principal ISI - Dashboard</title>",
        "<link rel='stylesheet' href='/static/styles.css'>",
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
        "button{cursor:pointer;}",
        "</style>",
        "</head>",
        "<body>",
        "<div class='container'>",
        "<header class='brand'>",
        "<div>__LOGO_UAEMEX__</div>",
        "<div class='titles'>",
        "<h1>Principal_2025_ISI</h1>",
        "<p>WG_HOST: <b>__HOST__</b> · <a href='/login'>App (login)</a></p>",
        "</div>",
        "<div>__LOGO_ING__</div>",
        "</header>",

        "<div class='grid'>",
        "<section class='card'>",
        "<h2 style='margin:0 0 12px 0;'>Servicios (estado en vivo)</h2>",
        "<div class='muted' style='margin-bottom:8px;'>Se actualiza cada 5s</div>",

        "<div style='display:flex;gap:12px;align-items:center;margin:8px 0;'>",
        "  <input id='q' placeholder='Buscar por equipo/asignatura/repositorio' ",
        "         style='padding:8px;border:1px solid var(--border);border-radius:8px;flex:1;max-width:360px;'>",
        "  <button id='sortLat' style='padding:8px 12px;border:1px solid var(--border);border-radius:8px;background:var(--card);'>Ordenar por Latencia</button>",
        "  <button id='sortUp'  style='padding:8px 12px;border:1px solid var(--border);border-radius:8px;background:var(--card);'>Ordenar por Uptime</button>",
        "  <span id='lastTs' class='muted'></span>",
        "</div>",

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
        "<tbody id='tbody'><tr><td colspan='8' class='muted'>Cargando...</td></tr></tbody>",
        "</table>",
        "</div>",
        "</section>",
        "</div>",

        "</div>",  # container

        "<script>",
        "function imgTag(url, alt){ if(!url) return ''; const safeAlt = alt || 'logo'; return '<img class=\"logo\" src=\"'+url+'\" alt=\"'+safeAlt+'\" loading=\"lazy\"/>'; }",

        "let lastData = [];",
        "let sortMode = null; // 'lat' | 'up' | null",

        "function renderRows(rows){",
        "  const body = document.getElementById('tbody');",
        "  body.innerHTML='';",
        "  for(const row of rows){",
        "    const tr = document.createElement('tr');",

        "    const tdName=document.createElement('td'); tdName.textContent=row.name||'-'; tr.appendChild(tdName);",
        "    const tdTag=document.createElement('td'); tdTag.textContent=row.tag||'-'; tr.appendChild(tdTag);",

        "    const tdRepo=document.createElement('td');",
        "    if(row.repo){ const a=document.createElement('a'); a.href=row.repo; a.textContent=row.repo; a.target='_blank'; tdRepo.appendChild(a); }",
        "    else{ tdRepo.textContent='-'; }",
        "    tr.appendChild(tdRepo);",

        "    const tdUrl=document.createElement('td');",
        "    if(row.external_url){ const a=document.createElement('a'); a.href=row.external_url; a.textContent=row.external_url; a.target='_blank'; tdUrl.appendChild(a); }",
        "    else{ tdUrl.textContent='-'; }",
        "    tr.appendChild(tdUrl);",

        "    const tdStatus=document.createElement('td');",
        "    const pill=document.createElement('span'); pill.className='pill '+(row.status==='up'?'up':'down');",
        "    pill.textContent=(row.status||'unknown').toUpperCase()+(row.http?' ('+row.http+')':'');",
        "    tdStatus.appendChild(pill);",
        "    tr.appendChild(tdStatus);",

        "    const tdLat=document.createElement('td'); tdLat.textContent=(row.latency_ms!=null?row.latency_ms+' ms':'-'); tr.appendChild(tdLat);",

        "    const tdUptime=document.createElement('td'); tdUptime.textContent=(row.uptime_pct!=null?row.uptime_pct.toFixed(1)+'%':'-'); tr.appendChild(tdUptime);",

        "    const tdErr=document.createElement('td');",
        "    if(row.error){ const e = String(row.error); tdErr.textContent = (e.length>80? e.slice(0,80)+'…': e); } else { tdErr.textContent='-'; }",
        "    tr.appendChild(tdErr);",

        "    body.appendChild(tr);",
        "  }",
        "}",

        "function applyFilters(){",
        "  const q = (document.getElementById('q').value||'').toLowerCase().trim();",
        "  let rows = lastData.slice();",
        "  if(q){",
        "    rows = rows.filter(r =>",
        "      (r.name||'').toLowerCase().includes(q) ||",
        "      (r.tag||'').toLowerCase().includes(q) ||",
        "      (r.repo||'').toLowerCase().includes(q)",
        "    );",
        "  }",
        "  if(sortMode==='lat'){",
        "    rows.sort((a,b)=>(a.latency_ms||1e9) - (b.latency_ms||1e9));",
        "  } else if(sortMode==='up'){",
        "    rows.sort((a,b)=>(b.uptime_pct||0) - (a.uptime_pct||0));",
        "  }",
        "  renderRows(rows);",
        "}",

        "async function fetchStatus(){",
        "  try{",
        "    const r = await fetch('/status');",
        "    if(!r.ok) throw new Error('status '+r.status);",
        "    const data = await r.json();",
        "    lastData = data.results || [];",
        "    const lastTs = document.getElementById('lastTs');",
        "    if(data.ts){ const d = new Date(data.ts*1000); lastTs.textContent = 'Actualizado: '+d.toLocaleTimeString(); }",
        "    applyFilters();",
        "  }catch(e){ console.error(e); }",
        "}",

        "document.addEventListener('DOMContentLoaded',()=>{",
        "  const uaemexDiv=document.querySelectorAll('.brand > div')[0];",
        "  const ingDiv=document.querySelectorAll('.brand > div')[2];",
        "  uaemexDiv.innerHTML=imgTag('__LOGO_URL_UAEMEX__','Escudo UAEMex');",
        "  ingDiv.innerHTML=imgTag('__LOGO_URL_ING__','Escudo Facultad/Ingeniería');",

        "  document.getElementById('q').addEventListener('input', applyFilters);",
        "  document.getElementById('sortLat').addEventListener('click', ()=>{ sortMode = (sortMode==='lat'? null: 'lat'); applyFilters(); });",
        "  document.getElementById('sortUp').addEventListener('click',  ()=>{ sortMode = (sortMode==='up' ? null: 'up');  applyFilters(); });",
        "});",

        "fetchStatus(); setInterval(fetchStatus,5000);",
        "</script>",
        "</body>",
        "</html>",
    ]
    html = "\n".join(html_parts)
    html = html.replace("__HOST__", host)
    html = html.replace("__LOGO_URL_UAEMEX__", logos.get("uaemex", ""))
    html = html.replace("__LOGO_URL_ING__", logos.get("ing", ""))
    return html
