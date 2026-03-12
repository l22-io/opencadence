FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml .
COPY backend/src/ src/
COPY backend/alembic.ini .
COPY backend/migrations/ migrations/

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn src.main:create_app --factory --host 0.0.0.0 --port 8000"]
