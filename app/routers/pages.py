from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from auth import get_current_user
from models import User
from config import settings

router = APIRouter()

@router.get("/login", response_class=HTMLResponse)
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

@router.get("/app", response_class=HTMLResponse)
def app_home(user: User = Depends(get_current_user)):
    return f"""
<!DOCTYPE html><html lang="es"><meta charset="utf-8"/>
<body style="font-family: system-ui; margin:2rem;">
  <h2>Hola {user.full_name or user.email}</h2>
  <p>Bienvenido a la app protegida.</p>
  <p><a href="/">Volver al dashboard</a></p>
</body></html>
"""

@router.get("/", response_class=HTMLResponse)
def root():
    host = settings.WG_HOST
    logos = {
        "uaemex": settings.LOGO_UAEMEX_URL.strip(),
        "ing": settings.LOGO_ING_URL.strip(),
    }

    html = f"""<!DOCTYPE html>
<html lang='es'>
<head>
<meta charset='utf-8'/>
<meta name='viewport' content='width=device-width, initial-scale=1'/>
<title>Principal ISI - Dashboard</title>
<link rel='stylesheet' href='/static/style.css'>
<style>
:root{{--bg:#ffffff;--fg:#111827;--muted:#6b7280;--card:#f9fafb;--border:#e5e7eb;
--good-bg:#e6ffed;--good-fg:#046c4e;--good-br:#b7f5c8;
--bad-bg:#ffe6e6;--bad-fg:#8a1f1f;--bad-br:#ffc2c2;}}
@media (prefers-color-scheme: dark){{:root{{--bg:#0b0f14;--fg:#e5e7eb;--muted:#9ca3af;--card:#111827;--border:#1f2937;
--good-bg:#0a2f1e;--good-fg:#a7f3d0;--good-br:#14532d;--bad-bg:#3b0a0a;--bad-fg:#fecaca;--bad-br:#7f1d1d;}}img{{filter:brightness(0.95) contrast(1.05);}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,"Helvetica Neue",Arial;}}
.container{{max-width:1150px;margin:0 auto;padding:24px;}}
.brand{{display:grid;gap:12px;align-items:center;justify-items:center;grid-template-columns:120px 1fr 120px;}}
.brand .logo{{max-height:80px;width:auto;object-fit:contain;}}
.titles{{text-align:center;}}
.titles h1{{margin:0;font-size:1.75rem;}}
.titles p{{margin:4px 0 0;color:var(--muted);}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;margin-top:24px;}}
table{{width:100%;border-collapse:collapse;}}
th,td{{border-bottom:1px solid var(--border);padding:10px 8px;text-align:left;}}
thead th{{background:transparent;font-weight:600;}}
tbody tr:nth-child(odd){{background:rgba(0,0,0,0.02);}}
a{{color:inherit;text-decoration:underline;text-underline-offset:2px;}}
.pill{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;vertical-align:middle;}}
.up{{background:var(--good-bg);color:var(--good-fg);border:1px solid var(--good-br);}}
.down{{background:var(--bad-bg);color:var(--bad-fg);border:1px solid var(--bad-br);}}
.muted{{color:var(--muted);font-size:0.9rem;}}
.grid{{display:grid;gap:16px;grid-template-columns:1fr;}}
@media (min-width:900px){{.grid{{grid-template-columns:1fr;}}}}
button{{cursor:pointer;}}
</style>
</head>
<body>
<div class='container'>
<header class='brand'>
<div><img class="logo" src="{logos.get('uaemex','')}" alt="Escudo UAEMex" /></div>
<div class='titles'>
<h1>Principal_2025_ISI</h1>
<p>WG_HOST: <b>{host}</b> · <a href='/login'>App (login)</a></p>
</div>
<div><img class="logo" src="{logos.get('ing','')}" alt="Escudo Facultad/Ingeniería" /></div>
</header>

<div class='grid'>
<section class='card'>
<h2 style='margin:0 0 12px 0;'>Servicios (estado en vivo)</h2>
<div class='muted' style='margin-bottom:8px;'>Se actualiza cada 5s</div>

<div style='display:flex;gap:12px;align-items:center;margin:8px 0;'>
  <input id='q' placeholder='Buscar por equipo/asignatura/repositorio'
         style='padding:8px;border:1px solid var(--border);border-radius:8px;flex:1;max-width:360px;'>
  <button id='sortLat' style='padding:8px 12px;border:1px solid var(--border);border-radius:8px;background:var(--card);'>Ordenar por Latencia</button>
  <button id='sortUp'  style='padding:8px 12px;border:1px solid var(--border);border-radius:8px;background:var(--card);'>Ordenar por Uptime</button>
  <span id='lastTs' class='muted'></span>
</div>

<div style='overflow-x:auto;'>
<table id='tbl'>
<thead><tr>
<th>Equipo</th>
<th>Asignatura</th>
<th>Repo</th>
<th>URL</th>
<th>Estado</th>
<th>Latencia</th>
<th>Uptime (ventana)</th>
<th>Último error</th>
</tr></thead>
<tbody id='tbody'><tr><td colspan='8' class='muted'>Cargando...</td></tr></tbody>
</table>
</div>
</section>
</div>

</div> <!-- container -->

<script>
function renderRows(rows){{
  const body = document.getElementById('tbody');
  body.innerHTML='';
  for(const row of rows){{
    const tr = document.createElement('tr');

    const tdName=document.createElement('td'); tdName.textContent=row.name||'-'; tr.appendChild(tdName);
    const tdTag=document.createElement('td'); tdTag.textContent=row.tag||'-'; tr.appendChild(tdTag);

    const tdRepo=document.createElement('td');
    if(row.repo){{ const a=document.createElement('a'); a.href=row.repo; a.textContent=row.repo; a.target='_blank'; tdRepo.appendChild(a); }}
    else{{ tdRepo.textContent='-'; }}
    tr.appendChild(tdRepo);

    const tdUrl=document.createElement('td');
    if(row.external_url){{ const a=document.createElement('a'); a.href=row.external_url; a.textContent=row.external_url; a.target='_blank'; tdUrl.appendChild(a); }}
    else{{ tdUrl.textContent='-'; }}
    tr.appendChild(tdUrl);

    const tdStatus=document.createElement('td');
    const pill=document.createElement('span'); pill.className='pill '+(row.status==='up'?'up':'down');
    pill.textContent=(row.status||'unknown').toUpperCase()+(row.http?' ('+row.http+')':'');
    tdStatus.appendChild(pill);
    tr.appendChild(tdStatus);

    const tdLat=document.createElement('td'); tdLat.textContent=(row.latency_ms!=null?row.latency_ms+' ms':'-'); tr.appendChild(tdLat);

    const tdUptime=document.createElement('td'); tdUptime.textContent=(row.uptime_pct!=null?row.uptime_pct.toFixed(1)+'%':'-'); tr.appendChild(tdUptime);

    const tdErr=document.createElement('td');
    if(row.error){{ const e = String(row.error); tdErr.textContent = (e.length>80? e.slice(0,80)+'…': e); }} else {{ tdErr.textContent='-'; }}
    tr.appendChild(tdErr);

    body.appendChild(tr);
  }}
}}

let lastData = [];
let sortMode = null; // 'lat' | 'up' | null

function applyFilters(){{
  const q = (document.getElementById('q').value||'').toLowerCase().trim();
  let rows = lastData.slice();
  if(q){{
    rows = rows.filter(r =>
      (r.name||'').toLowerCase().includes(q) ||
      (r.tag||'').toLowerCase().includes(q) ||
      (r.repo||'').toLowerCase().includes(q)
    );
  }}
  if(sortMode==='lat'){{
    rows.sort((a,b)=>(a.latency_ms||1e9) - (b.latency_ms||1e9));
  }} else if(sortMode==='up'){{
    rows.sort((a,b)=>(b.uptime_pct||0) - (a.uptime_pct||0));
  }}
  renderRows(rows);
}}

async function fetchStatus(){{
  try{{
    const r = await fetch('/status');
    if(!r.ok) throw new Error('status '+r.status);
    const data = await r.json();
    lastData = data.results || [];
    const lastTs = document.getElementById('lastTs');
    if(data.ts){{ const d = new Date(data.ts*1000); lastTs.textContent = 'Actualizado: '+d.toLocaleTimeString(); }}
    applyFilters();
  }}catch(e){{ console.error(e); }}
}}

document.addEventListener('DOMContentLoaded',()=>{
  document.getElementById('q').addEventListener('input', applyFilters);
  document.getElementById('sortLat').addEventListener('click', ()=>{ sortMode = (sortMode==='lat'? null: 'lat'); applyFilters(); });
  document.getElementById('sortUp').addEventListener('click',  ()=>{ sortMode = (sortMode==='up' ? null: 'up');  applyFilters(); });
});

fetchStatus(); setInterval(fetchStatus,5000);
</script>
</body>
</html>"""
    return html
