.PHONY: dev test test-int lint format install seed up down migrate

install:
	cd backend && pip install -e ".[dev]"

dev:
	docker compose -f deploy/docker/docker-compose.yml up -d db redis
	cd backend && uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test:
	cd backend && pytest -v --ignore=tests/integration

test-int:
	cd backend && pytest -v -m integration

lint:
	cd backend && ruff check src tests
	cd backend && ruff format --check src tests
	cd backend && mypy src

format:
	cd backend && ruff check --fix src tests
	cd backend && ruff format src tests

seed:
	cd backend && python -m src.seed

up:
	docker compose -f deploy/docker/docker-compose.yml up -d

down:
	docker compose -f deploy/docker/docker-compose.yml down

migrate:
	cd backend && alembic upgrade head
