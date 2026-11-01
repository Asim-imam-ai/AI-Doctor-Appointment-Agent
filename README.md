# AI Doctor Appointment Agent

A production-oriented AI Doctor Appointment Agent built with Python 3.12, FastAPI, Pydantic v2, LangChain, LangGraph, Supabase, and Docker.

> **Disclaimer:** This project is an appointment assistance system and is not a medical diagnosis or treatment system.

## Project Status

- **Phase 1 (Completed):** Foundation + CI Baseline established (FastAPI setup, Pydantic Settings, API versioning, Health checks, Docker, Ruff, pytest, GitHub Actions).
- **Phase 2 (Completed):** Supabase + Domain + Data Layer established (Domain Pydantic models, Supabase migrations with constraints/indexes, Repository layer, Service layer, deterministic tests).
- **Phase 3 (Completed):** Doctor Discovery Agent established (LangGraph workflow, read-only search tools, intent safety boundaries, FastAPI endpoint `/api/v1/doctors/search`, unit & graph test suite).

## Tech Stack

- **Core:** Python 3.12+, FastAPI, Pydantic v2, Pydantic Settings
- **AI & Orchestration:** LangChain, LangGraph, OpenAI, LangSmith
- **Database:** Supabase / PostgreSQL
- **DevOps & Tooling:** Docker, Docker Compose, GitHub Actions, Ruff, pytest

## Project Architecture

```
User → FastAPI → LangGraph → Doctor Discovery Agent → Doctor Search Tool → Doctor Service → Doctor Repository → Supabase
```
For detailed architectural documentation, see [docs/architecture.md](docs/architecture.md).

Workflow entry points are in `app/agents/`, graph wiring in `app/agents/graph/`,
node implementations in `app/agents/nodes/`, and shared state in
`app/agents/state.py`. Tools call deterministic services; repository interfaces
select Supabase or in-memory persistence. Memory and knowledge retrieval live
in `app/memory/` and `app/rag/`. The canonical backend entry point is `app.main:app`.

## Local Development Setup

1. **Clone & Setup Environment:**
   ```bash
   cp .env.example .env
   ```

2. **Install Dependencies:**
   Using pip:
   ```bash
   pip install -e .[dev]
   ```

3. **Run Application:**
   Using uvicorn:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   Or using PowerShell:
   ```powershell
   python -m uvicorn app.main:app --reload --port 8000
   ```

4. **Verify Health Endpoint:**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

5. **Test Doctor Search Endpoint:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/doctors/search -H "Content-Type: application/json" -d "{\"message\": \"Find me a cardiologist\"}"
   ```

6. **Run Tests & Linting:**
   ```bash
   pytest
   ruff check .
   ruff format --check .
   ```

## Docker Setup

Build and run using Docker Compose:
```bash
docker-compose up --build
```
Verify container health:
```bash
curl http://localhost:8000/api/v1/health
```

## Future Phases Roadmap

- Doctor availability search & slot management (Phase 4)
- Appointment booking, rescheduling, and cancellation workflows
- Guardrails & prompt injection / jailbreak protection
- Human-In-The-Loop (HITL) approval mechanism
- Production AWS deployment pipeline
