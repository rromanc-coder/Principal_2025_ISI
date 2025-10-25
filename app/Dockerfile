# ============================
# Etapa 1 — (opcional) Build del frontend Angular si existe
# ============================
FROM node:20 AS fe-build
WORKDIR /app
COPY . .

# Si hay frontend, instala deps (según lockfile disponible) y compila.
# Si NO hay frontend, crea un placeholder para que / sirva algo.
RUN if [ -f frontend/package.json ]; then \
      echo "==> Detectado frontend/"; \
      cd frontend; \
      if [ -f pnpm-lock.yaml ]; then \
        echo "==> Usando pnpm"; corepack enable && pnpm install --frozen-lockfile; \
      elif [ -f yarn.lock ]; then \
        echo "==> Usando yarn"; yarn install --frozen-lockfile; \
      elif [ -f package-lock.json ]; then \
        echo "==> Usando npm ci"; npm ci; \
      else \
        echo "==> Sin lockfile; usando npm install (mejor commitear package-lock.json)"; \
        npm install; \
      fi; \
      npm run build -- --configuration production; \
    else \
      echo "==> No hay frontend: creando placeholder"; \
      mkdir -p frontend/dist/placeholder && \
      printf '<!doctype html><meta charset="utf-8"><title>SPA</title><h1>Frontend no encontrado</h1><p>Agrega app/frontend/ para compilar Angular.</p>' \
        > frontend/dist/placeholder/index.html; \
    fi

# ============================
# Etapa 2 — Backend (FastAPI)
# ============================
FROM python:3.11-slim AS backend
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copia el build del FE (real o placeholder) a /app/static.
# El comodín evita atarte al nombre de carpeta dentro de dist/.
COPY --from=fe-build /app/frontend/dist/*/ /app/static/

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host","0.0.0.0","--port","8000"]
