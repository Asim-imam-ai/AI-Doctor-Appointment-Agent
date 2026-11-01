.PHONY: install test lint format format-check run docker-build docker-up docker-down

install:
	uv sync --directory backend --extra dev

test:
	uv run --directory backend pytest -q

lint:
	uv run --directory backend ruff check app tests

format:
	uv run --directory backend ruff format app tests

format-check:
	uv run --directory backend ruff format --check app tests

run:
	uv run --directory backend uvicorn app.main:app --reload --port 8000

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down
