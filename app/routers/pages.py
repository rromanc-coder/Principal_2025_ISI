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
  <link rel="stylesheet" href="/static/style.css">
</head>
<body class="bg-tech">
  <main class="login-card" role="main">
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
<head><link rel="stylesheet" href="/static/style.css"></head>
<body class="page">
  <div class="container" style="padding:2rem;">
    <h2>Hola __USER__</h2>
    <p>Bienvenido a la app protegida.</p>
    <p><a href="/">Volver al dashboard</a></p>
  </div>
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
</head>
<body class="page">
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

<div class='toolbar'>
  <input id='q' placeholder='Buscar por equipo/asignatura/repositorio' class='input'/>
  <button id='sortLat' class='btn-secondary'>Ordenar por Latencia</button>
  <button id='sortUp'  class='btn-secondary'>Ordenar por Uptime</button>
  <span id='lastTs' class='muted'></span>
</div>

<div class='table-wrap'>
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
