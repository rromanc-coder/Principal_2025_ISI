import os, json, asyncio, time
from typing import List, Dict, Any
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import httpx

app = FastAPI(title="principal-isi", version="1.1.1")

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
    html = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8"/>
<title>Principal ISI</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 20px; }
  table { border-collapse: collapse; width: 100%; max-width: 960px; }
  th, td { border: 1px solid #ddd; padding: 8px; }
  th { background: #f3f3f3; text-align: left; }
  .pill { display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px; }
  .up { background:#e6ffed; color:#046c4e; border:1px solid #b7f5c8; }
  .down { background:#ffe6e6; color:#8a1f1f; border:1px solid #ffc2c2; }
  .muted { color:#666; font-size:12px; }
</style>
</head>
<body>
  <h1>✅ Principal_2025_ISI</h1>
  <p>WG_HOST: <b>__HOST__</b></p>

  <h2>Equipos (estado en vivo)</h2>
  <table id="tbl">
    <thead>
      <tr>
        <th>Equipo</th>
        <th>Repo</th>
        <th>URL</th>
        <th>Estado</th>
        <th>Latencia</th>
      </tr>
    </thead>
    <tbody id="tbody">
      <tr><td colspan="5" class="muted">Cargando...</td></tr>
    </tbody>
  </table>
  <p class="muted">Se actualiza cada 5s</p>

<script>
async function fetchStatus() {
  try {
    const r = await fetch('/status');
    if (!r.ok) throw new Error('status ' + r.status);
    const data = await r.json();
    const body = document.getElementById('tbody');
    body.innerHTML = '';
    for (const row of data.results) {
      const tr = document.createElement('tr');

      const tdName = document.createElement('td');
      tdName.textContent = row.name || '-';
      tr.appendChild(tdName);

      const tdRepo = document.createElement('td');
      if (row.repo) {
        const a = document.createElement('a');
        a.href = row.repo; a.textContent = row.repo; a.target = '_blank';
        tdRepo.appendChild(a);
      } else {
        tdRepo.textContent = '-';
      }
      tr.appendChild(tdRepo);

      const tdUrl = document.createElement('td');
      if (row.external_url) {
        const a = document.createElement('a');
        a.href = row.external_url; a.textContent = row.external_url; a.target = '_blank';
        tdUrl.appendChild(a);
      } else {
        tdUrl.textContent = '-';
      }
      tr.appendChild(tdUrl);

      const tdStatus = document.createElement('td');
      const pill = document.createElement('span');
      pill.className = 'pill ' + (row.status === 'up' ? 'up' : 'down');
      pill.textContent = (row.status || 'unknown').toUpperCase() + (row.http ? ' ('+row.http+')' : '');
      tdStatus.appendChild(pill);
      if (row.error) {
        const div = document.createElement('div');
        div.className = 'muted';
        div.textContent = row.error;
        tdStatus.appendChild(div);
      }
      tr.appendChild(tdStatus);

      const tdLat = document.createElement('td');
      tdLat.textContent = (row.latency_ms != null ? row.latency_ms + ' ms' : '-');
      tr.appendChild(tdLat);

      body.appendChild(tr);
    }
  } catch (e) {
    console.error(e);
  }
}

fetchStatus();
setInterval(fetchStatus, 5000);
</script>
</body>
</html>
"""
    return html.replace("__HOST__", host)
