.PHONY: install test lint format format-check run docker-build docker-up docker-down

install:
	pip install -e .[dev]

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

format-check:
	ruff format --check .

run:
	uvicorn app.main:app --reload --port 8000

docker-build:
	docker build -t doctor-appointment-agent:latest .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down
