# CRYPTO MINING GAME — Backend Dockerfile
# Imagen ligera de Python para la API FastAPI.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias del sistema mínimas (curl para el healthcheck del compose).
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

# DATABASE_URL, SECRET_KEY, ADMIN_* y direcciones de depósito llegan por entorno.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
