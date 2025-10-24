from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from auth import get_current_user
from models import User
from config import settings

router = APIRouter()

@router.get("/login", response_class=HTMLResponse)
def login_form():
    return """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Iniciar sesión — Principal ISI</title>
  <style>
    :root{
      --bg1:#0b1220; --bg2:#101827; --card-bg:rgba(17,24,39,.6); --card-br:rgba(255,255,255,.08);
      --fg:#e5e7eb; --muted:#9ca3af; --accent:#22d3ee; --accent-2:#8b5cf6; --error:#f87171;
      --focus:0 0 0 4px rgba(34,211,238,.35),0 0 0 1px rgba(34,211,238,.8);
    }
    @media (prefers-color-scheme: light){
      :root{
        --bg1:#e6f0ff; --bg2:#f8fbff; --card-bg:rgba(255,255,255,.75); --card-br:rgba(17,24,39,.08);
        --fg:#0b1220; --muted:#475569; --accent:#0891b2; --accent-2:#7c3aed; --error:#dc2626;
        --focus:0 0 0 4px rgba(8,145,178,.25),0 0 0 1px rgba(8,145,178,.6);
      }
    }

    *{box-sizing:border-box}
    html,body{height:100%}
    body{
      margin:0; color:var(--fg); font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,Arial;
      background: radial-gradient(1200px 800px at 10% -10%, rgba(34,211,238,.18), transparent 60%),
                  radial-gradient(1000px 700px at 110% 20%, rgba(139,92,246,.12), transparent 60%),
                  linear-gradient(160deg, var(--bg1), var(--bg2));
      display:grid; place-items:center; padding:24px;
    }

    .card{
      width:100%; max-width:420px; padding:28px 24px 24px;
      background:var(--card-bg); border:1px solid var(--card-br);
      border-radius:16px; backdrop-filter: blur(12px);
      box-shadow: 0 10px 30px rgba(0,0,0,.25);
      position:relative; overflow:hidden;
    }
    .card::before{
      content:""; position:absolute; inset:-2px;
      background: conic-gradient(from 180deg at 50% 50%, var(--accent), var(--accent-2), var(--accent));
      filter: blur(22px); opacity:.12; z-index:0;
    }
    .inner{ position:relative; z-index:1; }

    .brand{
      display:flex; align-items:center; gap:12px; margin-bottom:18px;
    }
    .brand .logo{
      width:42px; height:42px; border-radius:10px;
      background:linear-gradient(135deg, rgba(34,211,238,.35), rgba(139,92,246,.35));
      display:grid; place-items:center; font-weight:700; color:var(--fg);
      border:1px solid var(--card-br);
    }
    .brand h1{ margin:0; font-size:1.1rem; letter-spacing:.2px; }
    .brand p{ margin:0; font-size:.9rem; color:var(--muted); }

    label{ display:block; font-size:.9rem; margin:12px 0 6px; color:var(--muted); }
    .control{
      display:flex; align-items:center; gap:8px;
      background:rgba(0,0,0,.15); border:1px solid var(--card-br);
      border-radius:12px; padding:10px 12px;
    }
    input[type="email"], input[type="password"]{
      outline:none; border:none; background:transparent; color:var(--fg);
      width:100%; font-size:1rem;
    }
    input::placeholder{ color:rgba(148,163,184,.7); }

    .row{
      display:flex; align-items:center; justify-content:space-between; margin-top:10px;
      gap:12px; flex-wrap:wrap;
    }
    .muted{ color:var(--muted); font-size:.9rem; }

    .btn{
      width:100%; margin-top:16px; padding:12px 14px; font-weight:600; letter-spacing:.2px;
      color:#0b1220; background:linear-gradient(135deg, var(--accent), var(--accent-2));
      border:none; border-radius:12px; cursor:pointer;
      box-shadow: 0 8px 18px rgba(34,211,238,.2), 0 8px 18px rgba(139,92,246,.15);
      transition: transform .06s ease;
    }
    .btn:hover{ transform: translateY(-1px); }
    .btn:active{ transform: translateY(0); }
    .btn[disabled]{ opacity:.6; cursor:not-allowed; }

    .checkbox{ display:flex; align-items:center; gap:8px; }
    .checkbox input{ width:16px; height:16px; }

    .error{ margin-top:10px; color:var(--error); font-weight:600; min-height:1.25rem; }
    .hint{ font-size:.85rem; color:var(--muted); margin-top:10px; }

    .link{ color:var(--accent); text-decoration:none; }
    .link:hover{ text-decoration:underline; text-underline-offset:2px; }

    .right{
      display:flex; align-items:center; gap:8px; font-size:.9rem;
    }
    .toggle{
      background:transparent; border:none; color:var(--muted); cursor:pointer; padding:4px 6px;
    }

    .kbd{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
      font-size:.85rem; padding:2px 6px; border-radius:6px; border:1px solid var(--card-br);
      background:rgba(0,0,0,.15); color:var(--fg);
    }
  </style>
</head>
<body>
  <main class="card" role="main">
    <div class="inner">
      <div class="brand" aria-label="Identidad de la aplicación">
        <div class="logo">IS</div>
        <div>
          <h1>Principal ISI</h1>
          <p>Acceso para equipos de Ingeniería en Sistemas</p>
        </div>
      </div>

      <form id="loginForm" onsubmit="return doLogin(event)" novalidate>
        <label for="email">Correo institucional</label>
        <div class="control">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M3 7l9 6 9-6" stroke="currentColor" stroke-width="1.5"/>
            <rect x="3" y="5" width="18" height="14" rx="2" stroke="currentColor" stroke-width="1.5"/>
          </svg>
          <input id="email" name="email" type="email" inputmode="email" autocomplete="email"
                 placeholder="usuario@uaemex.mx" required aria-required="true"/>
        </div>

        <label for="pass">Contraseña</label>
        <div class="control">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <rect x="4" y="10" width="16" height="9" rx="2" stroke="currentColor" stroke-width="1.5"/>
            <path d="M8 10V8a4 4 0 1 1 8 0v2" stroke="currentColor" stroke-width="1.5"/>
          </svg>
          <input id="pass" name="password" type="password" autocomplete="current-password"
                 placeholder="••••••••" required aria-required="true"/>
          <button class="toggle" type="button" onclick="togglePass()" aria-label="Mostrar u ocultar contraseña">👁️</button>
        </div>

        <div class="row">
          <label class="checkbox">
            <input id="remember" type="checkbox" /> <span class="muted">Recordarme</span>
          </label>
          <div class="right">
            <span class="muted">¿Olvidaste tu contraseña?</span>
          </div>
        </div>

        <button id="btnLogin" class="btn" type="submit">
          Ingresar
        </button>

        <div id="msg" class="error" role="alert" aria-live="polite"></div>
        <p class="hint">Tip: usa <span class="kbd">Tab</span> para moverte entre campos. Seguridad con cookie <em>HttpOnly</em>.</p>
      </form>
    </div>
  </main>

  <script>
    function togglePass(){
      const el = document.getElementById('pass');
      el.type = (el.type === 'password') ? 'text' : 'password';
      el.focus();
    }

    async function doLogin(e){
      e.preventDefault();
      const btn = document.getElementById('btnLogin');
      const msg = document.getElementById('msg');
      const email = document.getElementById('email').value.trim();
      const password = document.getElementById('pass').value;

      msg.textContent = "";
      if(!email || !password){
        msg.textContent = "Completa correo y contraseña.";
        return false;
      }

      btn.disabled = true; btn.textContent = "Ingresando…";
      try{
        const r = await fetch('/api/login', {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({email, password}),
          credentials: 'same-origin'
        });
        if(r.ok){
          location.href = '/app';
        }else{
          const t = await r.json().catch(()=>({detail:'Error de autenticación'}));
          msg.textContent = t.detail || 'Credenciales inválidas';
        }
      }catch(err){
        msg.textContent = 'No se pudo contactar al servidor.';
      }finally{
        btn.disabled = false; btn.textContent = "Ingresar";
      }
      return false;
    }

    // Accesibilidad: submit con Enter sin hacer click
    document.getElementById('loginForm').addEventListener('keyup', (e)=>{
      if(e.key === 'Enter'){ doLogin(e); }
    });
  </script>
</body>
</html>
"""


@router.get("/app", response_class=HTMLResponse)
def app_home(user: User = Depends(get_current_user)):
    html = """
<!DOCTYPE html><html lang="es"><meta charset="utf-8"/>
<body style="font-family: system-ui; margin:2rem;">
  <h2>Hola __USER__</h2>
  <p>Bienvenido a la app protegida.</p>
  <p><a href="/">Volver al dashboard</a></p>
</body></html>
"""
    display_name = (user.full_name or user.email or "").strip()
    html = html.replace("__USER__", display_name)
    return HTMLResponse(html)

@router.get("/", response_class=HTMLResponse)
def root():
    host = settings.WG_HOST
    uaemex = settings.LOGO_UAEMEX_URL.strip()
    ing = settings.LOGO_ING_URL.strip()

    html = """<!DOCTYPE html>
<html lang='es'>
<head>
<meta charset='utf-8'/>
<meta name='viewport' content='width=device-width, initial-scale=1'/>
<title>Principal ISI - Dashboard</title>
<link rel='stylesheet' href='/static/style.css'>
<style>
:root{--bg:#ffffff;--fg:#111827;--muted:#6b7280;--card:#f9fafb;--border:#e5e7eb;
--good-bg:#e6ffed;--good-fg:#046c4e;--good-br:#b7f5c8;
--bad-bg:#ffe6e6;--bad-fg:#8a1f1f;--bad-br:#ffc2c2;}
@media (prefers-color-scheme: dark){:root{--bg:#0b0f14;--fg:#e5e7eb;--muted:#9ca3af;--card:#111827;--border:#1f2937;
--good-bg:#0a2f1e;--good-fg:#a7f3d0;--good-br:#14532d;--bad-bg:#3b0a0a;--bad-fg:#fecaca;--bad-br:#7f1d1d;}img{filter:brightness(0.95) contrast(1.05);}}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,"Helvetica Neue",Arial;}
.container{max-width:1150px;margin:0 auto;padding:24px;}
.brand{display:grid;gap:12px;align-items:center;justify-items:center;grid-template-columns:120px 1fr 120px;}
.brand .logo{max-height:80px;width:auto;object-fit:contain;}
.titles{text-align:center;}
.titles h1{margin:0;font-size:1.75rem;}
.titles p{margin:4px 0 0;color:var(--muted);}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;margin-top:24px;}
table{width:100%;border-collapse:collapse;}
th,td{border-bottom:1px solid var(--border);padding:10px 8px;text-align:left;}
thead th{background:transparent;font-weight:600;}
tbody tr:nth-child(odd){background:rgba(0,0,0,0.02);}
a{color:inherit;text-decoration:underline;text-underline-offset:2px;}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;vertical-align:middle;}
.up{background:var(--good-bg);color:var(--good-fg);border:1px solid var(--good-br);}
.down{background:var(--bad-bg);color:var(--bad-fg);border:1px solid var(--bad-br);}
.muted{color:var(--muted);font-size:0.9rem;}
.grid{display:grid;gap:16px;grid-template-columns:1fr;}
@media (min-width:900px){.grid{grid-template-columns:1fr;}}
button{cursor:pointer;}
</style>
</head>
<body>
<div class='container'>
<header class='brand'>
<div><img class="logo" src="__UAEMEX__" alt="Escudo UAEMex" /></div>
<div class='titles'>
<h1>Principal_2025_ISI</h1>
<p>WG_HOST: <b>__HOST__</b> · <a href='/login'>App (login)</a></p>
</div>
<div><img class="logo" src="__ING__" alt="Escudo Facultad/Ingeniería" /></div>
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
let lastData = [];
let sortMode = null; // 'lat' | 'up' | null

function renderRows(rows){
  const body = document.getElementById('tbody');
  body.innerHTML='';
  for(const row of rows){
    const tr = document.createElement('tr');

    const tdName=document.createElement('td'); tdName.textContent=row.name||'-'; tr.appendChild(tdName);
    const tdTag=document.createElement('td'); tdTag.textContent=row.tag||'-'; tr.appendChild(tdTag);

    const tdRepo=document.createElement('td');
    if(row.repo){ const a=document.createElement('a'); a.href=row.repo; a.textContent=row.repo; a.target='_blank'; tdRepo.appendChild(a); }
    else{ tdRepo.textContent='-'; }
    tr.appendChild(tdRepo);

    const tdUrl=document.createElement('td');
    if(row.external_url){ const a=document.createElement('a'); a.href=row.external_url; a.textContent=row.external_url; a.target='_blank'; tdUrl.appendChild(a); }
    else{ tdUrl.textContent='-'; }
    tr.appendChild(tdUrl);

    const tdStatus=document.createElement('td');
    const pill=document.createElement('span'); pill.className='pill '+(row.status==='up'?'up':'down');
    pill.textContent=(row.status||'unknown').toUpperCase()+(row.http?' ('+row.http+')':'');
    tdStatus.appendChild(pill);
    tr.appendChild(tdStatus);

    const tdLat=document.createElement('td'); tdLat.textContent=(row.latency_ms!=null?row.latency_ms+' ms':'-'); tr.appendChild(tdLat);

    const tdUptime=document.createElement('td'); tdUptime.textContent=(row.uptime_pct!=null?row.uptime_pct.toFixed(1)+'%':'-'); tr.appendChild(tdUptime);

    const tdErr=document.createElement('td');
    if(row.error){ const e = String(row.error); tdErr.textContent = (e.length>80? e.slice(0,80)+'…': e); } else { tdErr.textContent='-'; }
    tr.appendChild(tdErr);

    body.appendChild(tr);
  }
}

function applyFilters(){
  const q = (document.getElementById('q').value||'').toLowerCase().trim();
  let rows = lastData.slice();
  if(q){
    rows = rows.filter(r =>
      (r.name||'').toLowerCase().includes(q) ||
      (r.tag||'').toLowerCase().includes(q) ||
      (r.repo||'').toLowerCase().includes(q)
    );
  }
  if(sortMode==='lat'){
    rows.sort((a,b)=>(a.latency_ms||1e9) - (b.latency_ms||1e9));
  } else if(sortMode==='up'){
    rows.sort((a,b)=>(b.uptime_pct||0) - (a.uptime_pct||0));
  }
  renderRows(rows);
}

async function fetchStatus(){
  try{
    const r = await fetch('/status');
    if(!r.ok) throw new Error('status '+r.status);
    const data = await r.json();
    lastData = data.results || [];
    const lastTs = document.getElementById('lastTs');
    if(data.ts){ const d = new Date(data.ts*1000); lastTs.textContent = 'Actualizado: '+d.toLocaleTimeString(); }
    applyFilters();
  }catch(e){ console.error(e); }
}

document.addEventListener('DOMContentLoaded',()=>{
  document.getElementById('q').addEventListener('input', applyFilters);
  document.getElementById('sortLat').addEventListener('click', ()=>{ sortMode = (sortMode==='lat'? null: 'lat'); applyFilters(); });
  document.getElementById('sortUp').addEventListener('click',  ()=>{ sortMode = (sortMode==='up' ? null: 'up');  applyFilters(); });
});

fetchStatus(); setInterval(fetchStatus,5000);
</script>
</body>
</html>"""
    html = html.replace("__HOST__", host)
    html = html.replace("__UAEMEX__", uaemex)
    html = html.replace("__ING__", ing)
    return HTMLResponse(html)
