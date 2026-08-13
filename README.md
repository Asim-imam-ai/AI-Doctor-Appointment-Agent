# AI Doctor Appointment Agent

A production-oriented AI Doctor Appointment Agent built with Python 3.12, FastAPI, Pydantic v2, LangChain, LangGraph, Supabase, and Docker.

> **Disclaimer:** This project is an appointment assistance system and is not a medical diagnosis or treatment system.

## Project Status

- **Phase 1 (Completed):** Foundation + CI Baseline established (FastAPI setup, Pydantic Settings, API versioning, Health checks, Docker, Ruff, pytest, GitHub Actions).

## Tech Stack

- **Core:** Python 3.12+, FastAPI, Pydantic v2, Pydantic Settings
- **AI & Orchestration:** LangChain, LangGraph, OpenAI, LangSmith
- **Database:** Supabase / PostgreSQL
- **DevOps & Tooling:** Docker, Docker Compose, GitHub Actions, Ruff, pytest

## Project Architecture

```
User → FastAPI → Guardrails → LangGraph → Agent Nodes → Tools → Services → Repositories → Supabase
```
For detailed architectural documentation, see [docs/architecture.md](docs/architecture.md).

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

5. **Run Tests & Linting:**
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

- Doctor discovery & availability search
- Appointment booking, rescheduling, and cancellation workflows
- LangGraph agent workflow & conversation state checkpointing
- Guardrails & prompt injection / jailbreak protection
- Human-In-The-Loop (HITL) approval mechanism
- Production AWS deployment pipeline
