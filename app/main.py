import os, json
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI(title="principal-isi", version="1.0.0")

def load_teams() -> List[Dict[str, Any]]:
    raw = os.getenv("TEAMS_JSON", "[]")
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("TEAMS_JSON debe ser una lista")
        return data
    except Exception as e:
        # No “rompemos” el servicio si hay error, pero lo reportamos
        print(f"[WARN] TEAMS_JSON inválido: {e}")
        return []

def get_host() -> str:
    # Host “público” si lo defines (WireGuard o FQDN)
    return os.getenv("WG_HOST", "localhost")

@app.get("/", response_class=HTMLResponse)
def root():
    host = get_host()
    teams = load_teams()
    rows = "\n".join(
        f'<tr><td>{t.get("name")}</td>'
        f'<td>{t.get("repo","")}</td>'
        f'<td><a href="http://{host}:{t.get("port")}/" target="_blank">http://{host}:{t.get("port")}/</a></td></tr>'
        for t in teams
    )
    html = f"""
    <html>
      <head>
        <title>Principal ISI</title>
        <style>body{{font-family:sans-serif}} table{{border-collapse:collapse}} td,th{{border:1px solid #ccc;padding:6px}}</style>
      </head>
      <body>
        <h1>✅ Principal_2025_ISI</h1>
        <p>WG_HOST: <b>{host}</b></p>
        <h2>Equipos</h2>
        <table>
          <thead><tr><th>Equipo</th><th>Repo</th><th>URL</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
        <p>API: <a href="/teams" target="_blank">/teams</a> · <a href="/health" target="_blank">/health</a> · <a href="/docs" target="_blank">/docs</a></p>
      </body>
    </html>
    """
    return html

@app.get("/teams")
def teams():
    return {"host": get_host(), "teams": load_teams()}

@app.get("/health")
def health():
    return {"app": "principal-isi", "status": "ok"}
