# ============================
# Etapa 1 — Build del frontend (Angular)
# ============================
FROM node:20 AS fe-build
WORKDIR /app/frontend

# Instala dependencias de Angular
COPY frontend/package*.json ./
RUN npm ci

# Copia el código Angular y compila producción
COPY frontend/ ./
# ⚠️ Ajusta el nombre del proyecto si hace falta (ver nota abajo)
RUN npm run build -- --configuration production

# ============================
# Etapa 2 — Backend (FastAPI)
# ============================
FROM python:3.11-slim AS backend
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dependencias del sistema (si necesitas compilar algo)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código backend
COPY . .

# Copia el build de Angular a /app/static
# ⚠️ IMPORTANTE: dentro de /app/frontend/dist/ habrá una carpeta con el nombre
# de tu app Angular (por ejemplo "app-web"). Sustituye <nombre-angular> por ese nombre.
COPY --from=fe-build /app/frontend/dist/<nombre-angular>/ /app/static/

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host","0.0.0.0","--port","8000"]
