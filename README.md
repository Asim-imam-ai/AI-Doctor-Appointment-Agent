# AI Doctor Appointment Agent

FastAPI backend for doctor discovery, availability, appointment proposals, clinic knowledge retrieval, and patient conversations. Appointment assistance is not medical diagnosis or treatment.

## Architecture

The modular monolith lives in `backend/app`. FastAPI v1 handlers call domain services through dependencies. Domain services depend on repository protocols; Supabase adapters provide the production persistence. LangGraph has separate discovery, availability, booking, cancellation, and rescheduling workflows, with a routing orchestrator for chat. Booking and appointment changes require authenticated, durable approval proposals and PostgreSQL RPC transactions. Knowledge retrieval uses configured OpenAI embeddings and Supabase pgvector.

Notification and reminder application behavior has been removed. Historical notification and reminder tables in the existing Supabase schema are intentionally retained and unused to avoid destructive changes to deployed data.

## Configuration

Copy `backend/.env.example` to a local `.env` and configure the Supabase project URL, server-only service role key, OpenAI API key, and optional LangSmith settings. Never expose `SUPABASE_SERVICE_ROLE_KEY` to a browser or client. Patient endpoints require a Supabase Auth bearer token; knowledge ingestion and document management additionally require a verified `app_metadata.role` of `admin` or `superuser`.

Apply Supabase migrations in order, including `supabase/migrations/003_atomic_appointments_and_proposals.sql`, before enabling appointment mutation endpoints.

## Local development

From the repository root:

```shell
uv sync --directory backend --extra dev
uv run --directory backend uvicorn app.main:app --reload --port 8000
```

Health is public at `http://localhost:8000/api/v1/health`; API docs are at `/docs`. Authenticated calls use `Authorization: Bearer <Supabase access token>`.

```shell
uv run --directory backend pytest -q
uv run --directory backend ruff check app tests
uv run --directory backend ruff format --check app tests
```

## Docker

The Compose build uses `backend/` as its context:

```shell
docker compose up --build
```

Provide runtime secrets through the deployment environment; they are not embedded in the image.

## Data and security notes

- Appointment booking, cancellation, rescheduling, and proposal transitions are implemented as PostgreSQL RPC transactions with row locking and replay protection.
- Patient identity is derived from a validated Supabase Auth bearer token and linked patient profile. API clients cannot select another patient by supplying an ID.
- RAG requires OpenAI embeddings; embedding/provider errors fail the request instead of returning fabricated vectors.
- Historical notification/reminder database objects are not used by the application and are not removed by migrations.
